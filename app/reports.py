"""Durable single-worker queue with request-time snapshots and crash recovery."""
import io
import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from app.db import connect

logger = logging.getLogger(__name__)
font_path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
pdfmetrics.registerFont(TTFont("ReportSans", str(font_path)))


def enqueue(user_id):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        pending = db.execute("SELECT COUNT(*) FROM report_jobs WHERE user_id=? AND status IN ('queued','running')", (user_id,)).fetchone()[0]
        if pending >= 3:
            raise HTTPException(429, "You already have three reports in progress", headers={"Retry-After": "5"})
        rows = db.execute("SELECT company,role,status,applied_on,follow_up_on,notes FROM applications WHERE user_id=? ORDER BY applied_on DESC,id DESC", (user_id,)).fetchall()
        if len(rows) > 2000:
            raise HTTPException(422, "Reports support up to 2,000 applications")
        snapshot = {"generated_at": datetime.now(timezone.utc).isoformat(), "applications": [dict(row) for row in rows]}
        job_id = uuid.uuid4().hex
        db.execute("INSERT INTO report_jobs(id,user_id,status,snapshot) VALUES(?,?,'queued',?)", (job_id, user_id, json.dumps(snapshot)))
    return {"id": job_id, "status": "queued"}


def make_pdf(snapshot):
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = "ReportSans"
    styles.add(ParagraphStyle(name="ReportBody", fontName="ReportSans", fontSize=9, leading=14, spaceAfter=8, splitLongWords=True))
    content = [Paragraph("ApplyTrack | Application progress", styles["Title"]), Spacer(1, 12), Paragraph("Snapshot taken: " + escape(snapshot["generated_at"]), styles["ReportBody"])]
    applications = snapshot["applications"]
    counts = {status: sum(item["status"] == status for item in applications) for status in ["saved", "applied", "interview", "offer", "rejected"]}
    content.extend([Paragraph(f"{len(applications)} applications", styles["Heading1"]), Paragraph(" | ".join(f"{key.title()}: {value}" for key, value in counts.items()), styles["ReportBody"]), Spacer(1, 16)])
    if not applications:
        content.append(Paragraph("No applications yet. Add your first application to start tracking your progress.", styles["ReportBody"]))
    for item in applications:
        content.append(Paragraph(escape(item["company"]) + " / " + escape(item["role"]), styles["Heading2"]))
        content.append(Paragraph(f"Status: {item['status'].title()} | Application date: {item['applied_on']} | Follow-up: {item['follow_up_on'] or 'Not set'}", styles["ReportBody"]))
        if item["notes"]:
            content.append(Paragraph(escape(item["notes"]).replace("\n", "<br/>"), styles["ReportBody"]))
        content.append(Spacer(1, 9))

    def footer(canvas, document):
        canvas.setFont("ReportSans", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(0.65 * inch, 0.4 * inch, "ApplyTrack - personal application report")
        canvas.drawRightString(document.pagesize[0] - 0.65 * inch, 0.4 * inch, f"Page {document.page}")

    document = SimpleDocTemplate(output, title="ApplyTrack application progress", author="ApplyTrack", leftMargin=0.65 * inch, rightMargin=0.65 * inch, topMargin=0.6 * inch, bottomMargin=0.65 * inch)
    document.build(content, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


def recover_jobs():
    # Supported topology: exactly one server process and one worker.
    with connect() as db:
        db.execute("UPDATE report_jobs SET status='queued' WHERE status='running'")


def process_one():
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        job = db.execute("SELECT id,snapshot FROM report_jobs WHERE status='queued' ORDER BY created_at,id LIMIT 1").fetchone()
        if not job:
            return False
        db.execute("UPDATE report_jobs SET status='running' WHERE id=?", (job["id"],))
    try:
        pdf = make_pdf(json.loads(job["snapshot"]))
        with connect() as db:
            db.execute("UPDATE report_jobs SET status='completed',pdf=?,snapshot='{}',finished_at=CURRENT_TIMESTAMP WHERE id=?", (pdf, job["id"]))
    except Exception:
        # Never log user data, credentials, or report content.
        logger.error("PDF generation failed for job %s", job["id"])
        with connect() as db:
            db.execute("UPDATE report_jobs SET status='failed',error='Report generation failed. Please request a new report.',snapshot='{}',finished_at=CURRENT_TIMESTAMP WHERE id=?", (job["id"],))
    return True


class ReportWorker:
    def __init__(self):
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name="applytrack-reports", daemon=True)

    def start(self):
        recover_jobs()
        self.thread.start()

    def run(self):
        while not self.stop_event.is_set():
            try:
                if process_one():
                    continue
            except Exception:
                logger.error("Report worker could not access its queue; retrying")
            self.stop_event.wait(0.5)

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=10)

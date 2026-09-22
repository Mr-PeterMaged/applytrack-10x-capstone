"""Aggregate caching in SQLite: per-user, 60-second TTL, calendar-day guard."""

import json
import time
from datetime import date, timedelta

from app.db import connect


def get_summary(user_id):
    today = date.today()
    with connect() as db:
        # Prevent a writer from invalidating between our read and cache write.
        db.execute("BEGIN IMMEDIATE")
        cached = db.execute(
            "SELECT * FROM summary_cache WHERE user_id=?", (user_id,)
        ).fetchone()
        if (
            cached
            and cached["expires_at"] > time.time()
            and cached["calendar_day"] == today.isoformat()
        ):
            return json.loads(cached["payload"]), "HIT"
        counts = dict.fromkeys(
            ["saved", "applied", "interview", "offer", "rejected"], 0
        )
        for row in db.execute(
            "SELECT status,COUNT(*) AS count FROM applications WHERE user_id=? GROUP BY status",
            (user_id,),
        ):
            counts[row["status"]] = row["count"]
        follow_ups = [
            dict(row)
            for row in db.execute(
                "SELECT id,company,role,follow_up_on FROM applications WHERE user_id=? AND follow_up_on<=? AND status IN ('saved','applied','interview') ORDER BY follow_up_on,id LIMIT 20",
                (user_id, (today + timedelta(days=7)).isoformat()),
            )
        ]
        overdue = db.execute(
            "SELECT COUNT(*) FROM applications WHERE user_id=? AND follow_up_on<? AND status IN ('saved','applied','interview')",
            (user_id, today.isoformat()),
        ).fetchone()[0]
        submitted = sum(counts.values()) - counts["saved"]
        result = {
            "total": sum(counts.values()),
            "by_status": counts,
            "overdue": overdue,
            "follow_ups": follow_ups,
            "response_rate": round(
                (counts["interview"] + counts["offer"] + counts["rejected"])
                / submitted
                * 100,
                1,
            )
            if submitted
            else 0,
            "as_of": today.isoformat(),
        }
        db.execute(
            "INSERT OR REPLACE INTO summary_cache VALUES(?,?,?,?)",
            (user_id, json.dumps(result), time.time() + 60, today.isoformat()),
        )
    return result, "MISS"

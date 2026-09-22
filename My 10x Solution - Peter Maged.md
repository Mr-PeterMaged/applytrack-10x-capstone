# My 10x Solution - Peter Maged

**Project:** ApplyTrack — a personal internship and job application tracker

**Public repository:** https://github.com/Mr-PeterMaged/applytrack-10x-capstone

## What problem am I solving?

Students and early-career job seekers often keep applications in a mixture of spreadsheets, notes, and browser tabs. This makes it easy to forget follow-up dates and difficult to see how their search is progressing. Preparing a weekly update means collecting and counting the same details again.

ApplyTrack gives one person a private workspace for their own application data. It brings applications, follow-up dates, progress counts, and downloadable reports into the same workflow.

**My 10x hypothesis:** reduce preparing a weekly progress report from a hypothetical ten minutes of manual work to under one minute. This is a target to validate with a timed user trial, not a claim that a study has already proven a tenfold improvement.

The core has five features: private accounts; application creation, editing, search and deletion; a progress and follow-up dashboard; PDF reports generated in the background; and repeatable fictional demo data. **Non-goal:** automatically applying to employers or integrating job boards.

## How did I implement the solution?

The system uses Python, FastAPI, SQLite, ReportLab, and a small browser interface. It runs locally at no cost, requires no credit card or API key, and includes only fictional seed data. Passwords are hashed with Argon2id. Session cookies hold random tokens, while the database stores only their hashes. Each protected operation checks the signed-in user's ownership.

When a user requests a report, the API saves a snapshot of their current applications and creates a queued job. A separate worker thread builds the PDF and saves it in the database. The interface checks job progress and offers the download when ready. Interrupted jobs return to the queue after a server restart, and reports remain private to their owner.

**Six original program concepts are implemented; zero swaps:**

| Concept | Implementation |
|---|---|
| API endpoints | Validated HTTP endpoints with appropriate status codes, search and pagination (`app/main.py`, `app/models.py`). |
| Database | SQLite persistence, transactions, foreign keys and indexes; records survive restarts (`app/db.py`). |
| Authentication | Registration, login, expiring sessions, logout revocation and ownership checks (`app/auth.py`). |
| Background jobs | Persistent report queue, atomic job claims, failure states and restart recovery (`app/reports.py`). |
| PDF reporting | Downloadable application summaries and details rendered from a saved snapshot (`app/reports.py`). |
| Caching logic | Per-user aggregate cache with a 60-second lifetime and immediate invalidation after edits (`app/analytics.py`). |

No concepts were substituted, so no swap justification is needed. A deterministic test suite, authentication quotas and Docker support are additional engineering work.

## How to run and review it

Install Python 3.12–3.14, open the repository folder, and run:

```sh
python -m pip install -r requirements.txt
python run.py
```

On Windows, `py` can replace `python`. Alternatively, with Docker installed, run `docker compose up --build`.

Open **http://localhost:8000**, create an account with your own password, and click **Load demo data**. Review the dashboard, edit an application, then select **Reports → Create PDF report → Download PDF**. The README provides the full five-minute demo. Run `python -m pytest -q` for the automated backend checks; optional browser acceptance tests cover the visible workflow and mobile layout.

The supported deployment is one local server process with one worker. There is no paid integration or real job-board data. The PDF font targets English/Latin text; full Arabic PDF typography and a real before/after productivity study remain outside this scope.

**Submission:** the public GitHub repository link plus this overview file. AI assistance was used; the repository includes readable source, tests, and architecture notes for the owner to review and understand before submission.

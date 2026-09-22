# ApplyTrack — project decision (M1)

Students applying for internships often spread application details across spreadsheets, notes, and browser tabs. They lose track of follow-up dates and cannot quickly summarize their progress. Preparing a useful weekly update means manually collecting and counting the same information again.

**Who:** an individual student or early-career job seeker, using their own application data.

**10x claim (target, not a measured result):** reduce preparing a weekly application progress report from a hypothetical ten minutes of manual work to under one minute. A real before/after measurement requires a timed user trial; we do not claim one has occurred.

## Core: five features
1. Register, sign in, and sign out with private per-user data.
2. Create, edit, filter, and delete applications with status, notes, and follow-up dates.
3. View a cached progress summary and upcoming/overdue follow-ups.
4. Request a PDF report, track its background job, and download it.
5. Load fictional demo applications and follow a five-minute browser walkthrough.

## Six original concepts; zero swaps
HTTP API and validation; SQLite persistence; authentication; durable background jobs; PDF reporting; cached aggregate analytics with write invalidation and expiry.

**Non-goal:** applying to employers automatically or integrating real job boards. No paid APIs, LLM, external personal data, or credit card is needed.

**Stack:** Python, FastAPI, SQLite, ReportLab, and a small HTML/CSS/JavaScript interface. One local server runs the API and a single background worker. SQLite stores report jobs and PDF bytes for restart recovery.

## Milestones
- M1: this decision sheet.
- M2: application endpoint → logic → SQLite → response.
- M3: authentication, analytics cache, then report jobs/PDF, each verified.
- M4: seed data, browser interface, documented clean setup, and test suite.
- M5: overview, requirements audit, public repository and portal submission when account access is available.

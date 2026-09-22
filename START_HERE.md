# Start Here — ApplyTrack

ApplyTrack keeps internship and job applications in one place. Track applications, plan follow-ups, review your progress, and download a PDF report.

## Try the application

With Docker running, open a terminal in the project folder and run:

```sh
docker compose up -d --build
```

Open http://localhost:8000, click **Create an account**, and choose your own email address and password. After signing in, click **Load demo data** to add eight fictional applications. On mobile, this button is labeled **Demo**.

Alternatively, with Python 3.12–3.14 installed, run:

```sh
python -m pip install -r requirements.txt
python run.py
```

On Windows, use `py` instead of `python` if needed. Use one startup method at a time. There is no default account or preset password.

## What is implemented?

- An HTTP API with input validation and appropriate response codes.
- SQLite persistence that keeps records after the application closes.
- Registration, sign-in, and private data for each user.
- Background report jobs with recovery after a server restart.
- PDF report generation and download.
- Cached analytics that refresh after data changes.

These are six concepts from the original capstone list, with zero substitutions. The project also includes automated tests, Docker support, and a responsive interface.

## Before submitting

Read the [README](README.md) and [architecture notes](docs/ARCHITECTURE.md). Practice adding and editing an application, then generating a report. The capstone requires you to understand your code, including work completed with AI assistance.

The submission document is [My 10x Solution - Peter Maged.md](My%2010x%20Solution%20-%20Peter%20Maged.md). Submit that document together with the [public GitHub repository link](https://github.com/Mr-PeterMaged/applytrack-10x-capstone) through the internship portal. Do not upload a ZIP or the full codebase. No presentation is required.

**GitHub repository name:** `applytrack-10x-capstone`.

The “10x” improvement is a proposed target, not a measured result. Current PDF reports target English/Latin text; full Arabic typography is outside this version's scope.

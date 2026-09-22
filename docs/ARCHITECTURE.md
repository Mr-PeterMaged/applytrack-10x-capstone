# Architecture and review notes

```text
Browser UI / Swagger
        |
        v
FastAPI: validation -> session lookup -> ownership checks
        |                         |
        v                         v
SQLite applications          report_jobs (snapshot + queued state)
        |                         |
        v                         v
summary_cache                one ReportWorker thread
(user + day + 60s TTL)             |
                                  v
                             ReportLab -> PDF bytes in SQLite
```

## Important invariants

1. The request body never chooses the owner. A validated session selects the user.
2. Every application/report access includes `user_id`; another user's identifier returns 404.
3. Application mutation and cache deletion share one transaction. Cache calculation takes `BEGIN IMMEDIATE` to prevent a stale read being cached after a concurrent writer invalidated it.
4. Reports describe request-time data. Edits made while a job is queued do not change that snapshot.
5. Job claim is atomic; rendering happens after releasing the SQLite write lock. Completion and PDF storage are committed together.
6. One process is a deliberate constraint. At startup, that process can safely put its interrupted `running` jobs back into `queued`. A multi-replica design would need leases and fencing instead.

## Files to read in order

1. `models.py`: API inputs and allowed statuses.
2. `db.py`: schema, constraints and connection lifecycle.
3. `auth.py`: Argon2 verification, token hashing, expiry and quotas.
4. `main.py`: HTTP routes, ownership, response codes and app lifecycle.
5. `analytics.py`: grouping, date rules, cached reuse and invalidation.
6. `reports.py`: snapshot, queue, PDF renderer, recovery and failure handling.
7. `seed.py`, then `tests/`: reproducible examples and adverse cases.
8. `static/app.js`: same-origin fetch, UI state, polling and escaped text rendering.

## Why these choices?

- SQLite makes persistence available without a database service or credit card. Short connections work with FastAPI's threaded synchronous endpoints; foreign keys are enabled on every connection.
- Cookie sessions make the browser workflow simple and let logout revoke a token immediately. Only hashes are stored; there is no signing key to provision. Eight-hour absolute expiry is checked at the boundary.
- Persisting the queue and PDFs in the database keeps backups and restart behavior understandable. It trades off database size; no automatic retention policy is claimed.
- A thread moves CPU/file preparation off the HTTP request path. This is a small local queue, not a distributed task service.
- Server-side escaping in report paragraphs and client-side HTML escaping keep user strings from becoming markup.
- A simple static UI keeps focus on the backend concepts and avoids a separate frontend build process.

## Data model

`users` owns `sessions`, `applications`, `summary_cache`, and `report_jobs` through foreign keys. `auth_attempts` stores expiring IP-based counters. The job snapshot is cleared after completion/failure to avoid keeping duplicate application JSON indefinitely; successful PDFs remain until the database is removed.

## Review questions for the owner

- Why does the summary cache need both invalidation and expiry?
- Why must a report snapshot be stored when the request arrives?
- Why are session tokens hashed even though they are already random?
- What happens if the process stops after a claim but before saving a PDF?
- Why is the one-process restriction necessary for startup recovery?
- How would you add retention and multilingual typography without expanding the core product?

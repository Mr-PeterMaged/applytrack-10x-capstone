"""Only fictional records. Seed is repeatable and refuses to overwrite real data."""
import os
from datetime import date, timedelta
from app.db import connect, initialize


def seed_user(user_id):
    today = date.today()
    samples = [
        ("Northstar Labs", "Backend Engineering Intern", "interview", -12, 1, "Fictional demo. Prepare API design examples for the technical interview."),
        ("Orbit Studio", "Python Developer Intern", "applied", -9, -2, "Fictional demo. Follow up on the application."),
        ("Cedar Systems", "Platform Engineering Intern", "applied", -5, 2, "Fictional demo. Interested in their developer tools team."),
        ("Mosaic Works", "Junior Backend Developer", "offer", -20, None, "Fictional demo. Review the role and learning opportunities."),
        ("Harbor Digital", "Software Engineering Intern", "saved", -1, 4, "Fictional demo. Tailor the portfolio before applying."),
        ("Lumen Research", "Data Engineering Intern", "rejected", -18, None, "Fictional demo. Keep practicing SQL and try again next cycle."),
        ("Juniper Cloud", "API Developer Intern", "interview", -8, 0, "Fictional demo. Review authentication and background jobs."),
        ("Atlas Workshop", "Full Stack Intern", "applied", -3, 5, "Fictional demo. Portfolio link included."),
    ]
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM applications WHERE user_id=? LIMIT 1", (user_id,)).fetchone():
            return 0
        db.executemany("INSERT INTO applications(user_id,company,role,status,applied_on,follow_up_on,notes) VALUES(?,?,?,?,?,?,?)", [
            (user_id, company, role, status, (today + timedelta(days=applied)).isoformat(), (today + timedelta(days=follow)).isoformat() if follow is not None else None, notes)
            for company, role, status, applied, follow, notes in samples
        ])
        db.execute("DELETE FROM summary_cache WHERE user_id=?", (user_id,))
    return len(samples)


def main():
    from app.auth import password_hasher
    from app.models import Credentials
    email, password = os.getenv("DEMO_EMAIL"), os.getenv("DEMO_PASSWORD")
    if not email or not password:
        raise SystemExit("Set DEMO_EMAIL and DEMO_PASSWORD in your environment, or use Load demo data after registering in the browser.")
    credentials = Credentials(email=email, password=password)
    initialize()
    with connect() as db:
        row = db.execute("SELECT * FROM users WHERE email=?", (credentials.email,)).fetchone()
        if row:
            if not password_hasher.verify(credentials.password, row["password_hash"]):
                raise SystemExit("Existing account credentials do not match; no data was changed.")
            user_id = row["id"]
        else:
            user_id = db.execute("INSERT INTO users(email,password_hash) VALUES(?,?)", (credentials.email, password_hasher.hash(credentials.password))).lastrowid
    print(f"Added {seed_user(user_id)} fictional demo applications. Existing application data was preserved.")


if __name__ == "__main__":
    main()

"""Two-command setup: pip install -r requirements.txt, then python run.py."""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(
        f"ApplyTrack: http://localhost:{port} | API docs: http://localhost:{port}/docs"
    )
    uvicorn.run(
        "app.main:app", host=os.getenv("HOST", "127.0.0.1"), port=port, workers=1
    )

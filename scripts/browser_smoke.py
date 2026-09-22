"""Optional browser acceptance check. Uses isolated data and a temporary server."""

import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts"
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as directory, socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        env = {
            **os.environ,
            "APPLYTRACK_DB": str(Path(directory) / "browser.db"),
            "PORT": str(port),
            "HOST": "127.0.0.1",
            "APPLYTRACK_WORKER": "1",
        }
        with (artifacts / "browser-server.log").open("w") as log:
            server = subprocess.Popen(
                [sys.executable, "run.py"], cwd=root, env=env, stdout=log, stderr=log
            )
            try:
                url = f"http://127.0.0.1:{port}"
                for _ in range(100):
                    try:
                        urllib.request.urlopen(url + "/api/health")
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Server failed to start")
                with sync_playwright() as playwright:
                    channel = os.getenv(
                        "BROWSER_CHANNEL", "msedge" if os.name == "nt" else "chromium"
                    )
                    browser = playwright.chromium.launch(channel=channel, headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 1050})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(url)
                    page.screenshot(
                        path=str(artifacts / "login-desktop.png"), full_page=True
                    )
                    page.get_by_role(
                        "button", name="Create an account", exact=True
                    ).click()
                    page.get_by_label("Email address").fill("browser@example.test")
                    password = secrets.token_urlsafe(24)
                    page.get_by_label("Password", exact=True).fill(password)
                    page.get_by_role("button", name="Create account").click()
                    expect(page.locator("#workspace")).to_be_visible()
                    page.locator("#seed-button").click()
                    expect(page.locator("#stat-total")).to_have_text("8")
                    expect(page.locator("#toast")).to_be_hidden(timeout=6000)
                    page.screenshot(
                        path=str(artifacts / "dashboard-desktop.png"), full_page=True
                    )
                    page.get_by_role("button", name="New application").click()
                    page.get_by_label("Company", exact=True).fill("Browser Test Studio")
                    page.get_by_label("Role", exact=True).fill("Backend Intern")
                    page.locator("#application-status").select_option("applied")
                    page.get_by_label("Notes", exact=False).fill(
                        '<script>alert("safe")</script>'
                    )
                    page.get_by_role("button", name="Save application").click()
                    expect(page.locator("#stat-total")).to_have_text("9")
                    page.locator('[data-page="applications"]').click()
                    page.get_by_placeholder("Search company or role…").fill(
                        "Browser Test"
                    )
                    expect(page.locator("#results-count")).to_have_text(
                        "1–1 of 1 applications"
                    )
                    page.get_by_role("button", name="Edit Browser Test Studio").click()
                    page.locator("#application-status").select_option("offer")
                    page.get_by_role("button", name="Save application").click()
                    expect(page.locator("#applications-table .badge")).to_have_text(
                        "Offer"
                    )
                    page.on("dialog", lambda dialog: dialog.accept())
                    page.get_by_role(
                        "button", name="Delete Browser Test Studio"
                    ).click()
                    expect(page.locator("#results-count")).to_have_text(
                        "0 applications"
                    )
                    page.locator('[data-page="reports"]').click()
                    page.get_by_role("button", name="Create PDF report").click()
                    download = page.get_by_role("link", name="Download PDF")
                    expect(download).to_be_visible(timeout=15000)
                    with page.expect_download() as result:
                        download.click()
                    result.value.save_as(str(artifacts / "sample-report.pdf"))
                    assert (
                        (artifacts / "sample-report.pdf")
                        .read_bytes()
                        .startswith(b"%PDF")
                    )
                    expect(page.locator("#toast")).to_be_hidden(timeout=6000)
                    page.screenshot(
                        path=str(artifacts / "reports-desktop.png"), full_page=True
                    )
                    page.locator('[data-page="overview"]').click()
                    page.set_viewport_size({"width": 390, "height": 844})
                    expect(page.locator("#stat-total")).to_have_text("8")
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth"
                    )
                    page.screenshot(
                        path=str(artifacts / "dashboard-mobile.png"), full_page=True
                    )
                    page.get_by_role("button", name="Sign out", exact=True).click()
                    expect(page.locator("#auth-view")).to_be_visible()
                    page.get_by_role("button", name="Sign in", exact=True).click()
                    page.get_by_label("Password", exact=True).fill(password)
                    page.locator("#auth-submit").click()
                    expect(page.locator("#stat-total")).to_have_text("8")
                    assert not errors, errors
                    browser.close()
                    print(
                        "PASS: browser registration, demo, CRUD, search, PDF download, mobile layout, logout/login; no page errors"
                    )
            finally:
                server.terminate()
                server.wait(timeout=15)


if __name__ == "__main__":
    main()

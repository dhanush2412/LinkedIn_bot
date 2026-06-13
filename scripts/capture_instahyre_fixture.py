"""One-off: capture REAL Instahyre HTML fixtures (requires login).

Opens a visible Chrome window. If you are not logged in, log in manually when
prompted, then press Enter. The session cookie is saved to .auth/instahyre.json
so future scrapes reuse it. After capturing, inspect the saved HTML and update
the selectors in jobhunt/scrapers/instahyre.py to match the real DOM, then
re-run the tests.

Run: .\.venv\Scripts\python.exe scripts/capture_instahyre_fixture.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("tests/fixtures/html")
OUT.mkdir(parents=True, exist_ok=True)
AUTH = Path(".auth/instahyre.json")
AUTH.parent.mkdir(exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, channel="chrome",
                                args=["--disable-blink-features=AutomationControlled"])
    ctx_kwargs = {"user_agent": UA, "viewport": {"width": 1366, "height": 768}, "locale": "en-US"}
    if AUTH.exists():
        ctx_kwargs["storage_state"] = str(AUTH)
    ctx = browser.new_context(**ctx_kwargs)
    page = ctx.new_page()
    page.goto("https://www.instahyre.com/candidate/opportunities/")
    print(">>> If you are not logged in, log in now in the opened browser, then press Enter here.")
    input()
    page.wait_for_load_state("networkidle")
    (OUT / "instahyre_list.html").write_text(page.content(), encoding="utf-8")
    print(f"Wrote {OUT / 'instahyre_list.html'}")

    first = page.query_selector("a[href*='/candidate/opportunities/']")
    if first:
        href = first.get_attribute("href")
        full = f"https://www.instahyre.com{href}" if href.startswith("/") else href
        page.goto(full)
        page.wait_for_load_state("networkidle")
        (OUT / "instahyre_job.html").write_text(page.content(), encoding="utf-8")
        print(f"Wrote {OUT / 'instahyre_job.html'}")
    else:
        print("No opportunity link found — check the selector against the real DOM.")

    ctx.storage_state(path=str(AUTH))
    print(f"Saved session to {AUTH}")
    browser.close()

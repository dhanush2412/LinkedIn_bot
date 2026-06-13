"""One-off: capture SimplyHired HTML fixtures for tests.

Runs headed against real Chrome to get past Cloudflare (headless is blocked).

Run: .\.venv\Scripts\python.exe scripts/capture_simplyhired_fixture.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("tests/fixtures/html")
OUT.mkdir(parents=True, exist_ok=True)

SEARCH_URL = "https://www.simplyhired.com/search?q=python+backend&l=remote"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False, channel="chrome",
        args=["--disable-blink-features=AutomationControlled"],
    )
    ctx = browser.new_context(
        user_agent=UA, viewport={"width": 1366, "height": 768}, locale="en-US",
    )
    page = ctx.new_page()
    page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(8000)  # let the Cloudflare JS challenge resolve
    (OUT / "simplyhired_search.html").write_text(page.content(), encoding="utf-8")
    print(f"Wrote {OUT / 'simplyhired_search.html'}")

    first_card = page.query_selector("[data-testid='searchSerpJob'] a")
    if first_card:
        href = first_card.get_attribute("href")
        full = href if href.startswith("http") else f"https://www.simplyhired.com{href}"
        page.goto(full, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(6000)
        (OUT / "simplyhired_job.html").write_text(page.content(), encoding="utf-8")
        print(f"Wrote {OUT / 'simplyhired_job.html'}")
    else:
        print("NO CARD FOUND — Cloudflare may have blocked; try again or solve the challenge.")
    browser.close()

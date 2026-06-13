"""One-off: capture SimplyHired HTML for use as a test fixture.

Run: python scripts/capture_simplyhired_fixture.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("tests/fixtures/html")
OUT.mkdir(parents=True, exist_ok=True)

SEARCH_URL = "https://www.simplyhired.com/search?q=python+backend&l=remote"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(SEARCH_URL, wait_until="networkidle")
    (OUT / "simplyhired_search.html").write_text(page.content(), encoding="utf-8")
    print(f"Wrote {OUT / 'simplyhired_search.html'}")

    first_card = page.query_selector("[data-testid='searchSerpJob'] a")
    if first_card:
        href = first_card.get_attribute("href")
        full = href if href.startswith("http") else f"https://www.simplyhired.com{href}"
        page.goto(full, wait_until="networkidle")
        (OUT / "simplyhired_job.html").write_text(page.content(), encoding="utf-8")
        print(f"Wrote {OUT / 'simplyhired_job.html'}")
    else:
        print("NO CARD FOUND with selector [data-testid='searchSerpJob'] a")
    browser.close()

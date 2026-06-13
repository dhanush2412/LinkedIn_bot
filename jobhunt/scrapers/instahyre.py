"""Instahyre scraper.

IMPORTANT: Instahyre's opportunities are behind a login wall and the site is a
client-rendered SPA, so the selectors below are DEFENSIVE BEST-GUESSES validated
only against synthetic fixtures. After logging in once (the BaseScraper saves the
session cookie to .auth/instahyre.json), capture a real page with
scripts/capture_instahyre_fixture.py and adjust the selectors here to match the
live DOM. Each parse function tries several candidate selectors so minor DOM
differences degrade gracefully rather than returning nothing.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from jobhunt.models import Job, derive_job_id
from jobhunt.scrapers.base import BaseScraper


SOURCE = "instahyre"
BASE = "https://www.instahyre.com"

# Candidate selectors, tried in order. Update after validating against the real DOM.
_TITLE_SELECTORS = "h1, h2, .opportunity-title, .position-title, .job-title, [class*='title']"
_COMPANY_SELECTORS = ".company-name, .company, [class*='company']"
_LOCATION_SELECTORS = ".opportunity-location, .location, [class*='location']"
_DESC_SELECTORS = (
    ".opportunity-description, .job-description, .description, "
    "[class*='description'], [class*='jobDetail']"
)


def parse_opportunities_list(html: str, source_base: str = BASE) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for a in soup.select("a[href*='/candidate/opportunities/'], a.opportunity-link"):
        href = a.get("href", "")
        if not href or href.rstrip("/").endswith("/opportunities"):
            continue
        url = href if href.startswith("http") else urljoin(source_base, href)
        if url in seen:
            continue
        seen.add(url)
        title_el = a.select_one(_TITLE_SELECTORS)
        company_el = a.select_one(_COMPANY_SELECTORS)
        items.append({
            "url": url,
            "title": title_el.get_text(strip=True) if title_el else a.get_text(strip=True)[:80],
            "company": company_el.get_text(strip=True) if company_el else "",
        })
    return items


def parse_opportunity_detail(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one(_TITLE_SELECTORS)
    company = soup.select_one(_COMPANY_SELECTORS)
    location = soup.select_one(_LOCATION_SELECTORS)
    jd = soup.select_one(_DESC_SELECTORS)
    return {
        "title": title.get_text(strip=True) if title else "",
        "company": company.get_text(strip=True) if company else "",
        "location": location.get_text(strip=True) if location else "",
        "jd_text": jd.get_text("\n", strip=True) if jd else "",
    }


def _remote_type(location: str) -> str:
    low = location.lower()
    if "remote" in low:
        return "remote"
    if "hybrid" in low:
        return "hybrid"
    return "onsite"


class InstahyreScraper(BaseScraper):
    name = SOURCE

    def scrape(self, keywords: str = "", max_jobs: int = 30) -> Iterator[Job]:
        page = self.new_page()
        page.goto(f"{BASE}/candidate/opportunities/", wait_until="domcontentloaded", timeout=45000)
        self._human_delay()
        if "/login" in page.url or "Login" in (page.title() or ""):
            print("[instahyre] login required — run `scrape instahyre` once with a "
                  "visible browser and log in; the session is saved to .auth/instahyre.json.")
            return

        items = parse_opportunities_list(page.content())
        if keywords:
            kw = keywords.lower()
            items = [i for i in items if kw in i["title"].lower() or kw in i["company"].lower()]

        for it in items[:max_jobs]:
            try:
                page.goto(it["url"], wait_until="domcontentloaded", timeout=45000)
                self._human_delay()
                d = parse_opportunity_detail(page.content())
                if not d["jd_text"]:
                    continue
                yield Job(
                    job_id=derive_job_id(SOURCE, it["url"]),
                    source=SOURCE,
                    title=d["title"] or it["title"],
                    company=d["company"] or it["company"],
                    location=d.get("location", ""),
                    remote_type=_remote_type(d.get("location", "")),
                    url=it["url"],
                    posted_date="",
                    jd_text=d["jd_text"],
                    scraped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    tailored=False,
                )
            except Exception as e:
                print(f"[instahyre] skipped {it['url']}: {e}")
                continue

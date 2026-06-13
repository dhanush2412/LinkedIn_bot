from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from jobhunt.models import Job, derive_job_id
from jobhunt.scrapers.base import BaseScraper


SOURCE = "simplyhired"
BASE = "https://www.simplyhired.com"


def parse_search_results(html: str, source_base: str = BASE) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    for card in soup.select("[data-testid='searchSerpJob']"):
        link = card.select_one("a[data-testid='searchSerpJobTitle'], a.SerpJob-link, a")
        title_el = card.select_one("[data-testid='searchSerpJobTitle'], h2")
        company_el = card.select_one("[data-testid='companyName'], .SerpJob-company")
        location_el = card.select_one("[data-testid='searchSerpJobLocation'], .SerpJob-location")
        if not link or not title_el:
            continue
        href = link.get("href", "")
        url = href if href.startswith("http") else urljoin(source_base, href)
        cards.append({
            "title": title_el.get_text(strip=True),
            "company": company_el.get_text(strip=True) if company_el else "",
            "location": location_el.get_text(strip=True) if location_el else "",
            "url": url,
        })
    return cards


def parse_job_detail(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("[data-testid='viewJobTitle'], h1")
    company = soup.select_one("[data-testid='viewJobCompanyName'], [data-testid='detailText']")
    jd = soup.select_one(
        "[data-testid='viewJobBodyJobFullDescriptionContent'], .viewjob-jobDescription, .jobBody"
    )
    return {
        "title": title.get_text(strip=True) if title else "",
        "company": company.get_text(strip=True) if company else "",
        "jd_text": jd.get_text("\n", strip=True) if jd else "",
    }


def _remote_type(location: str) -> str:
    if "remote" in location.lower():
        return "remote"
    if "hybrid" in location.lower():
        return "hybrid"
    return "onsite"


class SimplyHiredScraper(BaseScraper):
    name = SOURCE

    def scrape(self, keywords: str, location: str = "remote", max_jobs: int = 30) -> Iterator[Job]:
        page = self.new_page()
        search_url = f"{BASE}/search?q={keywords.replace(' ', '+')}&l={location}"
        page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
        self._human_delay()
        cards = parse_search_results(page.content())

        for card in cards[:max_jobs]:
            try:
                page.goto(card["url"], wait_until="domcontentloaded", timeout=45000)
                self._human_delay()
                detail = parse_job_detail(page.content())
                if not detail["jd_text"]:
                    continue
                yield Job(
                    job_id=derive_job_id(SOURCE, card["url"]),
                    source=SOURCE,
                    title=detail["title"] or card["title"],
                    company=detail["company"] or card["company"],
                    location=card["location"],
                    remote_type=_remote_type(card["location"]),
                    url=card["url"],
                    posted_date="",
                    jd_text=detail["jd_text"],
                    scraped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    tailored=False,
                )
            except Exception as e:
                print(f"[simplyhired] skipped {card['url']}: {e}")
                continue

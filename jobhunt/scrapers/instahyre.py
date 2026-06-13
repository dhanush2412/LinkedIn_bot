"""Instahyre scraper.

Instahyre is a login-walled Angular single-page app. There are NO per-job URLs —
all jobs live on /candidate/opportunities/ and navigation is JS-driven. Critically,
the job card and its "View" button carry ng-click handlers that open an APPLY modal,
so this scraper is strictly READ-ONLY: it parses the rendered HTML of the
opportunities page and NEVER clicks anything (clicking could apply to a job on the
user's behalf).

Because there are no stable per-job URLs, job_id is derived from a slug of the
company + role. The JD text we can safely extract is the company blurb + required
skills shown on the card; the full role description is only behind the apply modal,
which we intentionally do not open. Read the full details on Instahyre before
applying.

Requires a completed Instahyre profile (the site hides opportunities behind
onboarding) and a saved session (.auth/instahyre.json, handled by BaseScraper).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterator

from bs4 import BeautifulSoup

from jobhunt.models import Job, derive_job_id
from jobhunt.scrapers.base import BaseScraper


SOURCE = "instahyre"
BASE = "https://www.instahyre.com"
OPPS_URL = f"{BASE}/candidate/opportunities/?matching=true"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _split_company_role(full_title: str) -> tuple[str, str]:
    """Instahyre titles look like 'Company - Role (Type)'. Split on the first ' - '."""
    if " - " in full_title:
        company, role = full_title.split(" - ", 1)
        return company.strip(), role.strip()
    return "", full_title.strip()


def _extract_skills(card) -> list[str]:
    container = card.select_one(".candidate-opp-keywords, .job-skills")
    if not container:
        return []
    skills: list[str] = []
    for el in container.find_all(True):
        txt = el.get_text(strip=True)
        # keep leaf elements only (no nested element children) to avoid the
        # concatenated parent text "Cloud ComputingDevOpsMonitoringAWS"
        if txt and not el.find(True):
            skills.append(txt)
    # de-dup preserving order
    seen, out = set(), []
    for s in skills:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def parse_opportunities_list(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, str]] = []
    seen_titles: set[str] = set()

    for name_el in soup.select(".employer-job-name"):
        full_title = name_el.get_text(strip=True)
        if not full_title or full_title in seen_titles:
            continue
        seen_titles.add(full_title)

        # climb to the card wrapper that holds location / notes / skills
        card = name_el
        for _ in range(6):
            if card.parent is None:
                break
            card = card.parent
            if card.select_one(".employer-locations") or card.select_one(".employer-notes"):
                break

        company, role = _split_company_role(full_title)
        loc_el = card.select_one(".employer-locations")
        notes_el = card.select_one(".employer-notes")
        location = loc_el.get_text(strip=True) if loc_el else ""
        location = re.sub(r"^Job available in\s*", "", location, flags=re.IGNORECASE)
        company_blurb = notes_el.get_text(" ", strip=True) if notes_el else ""
        skills = _extract_skills(card)

        jd_parts = []
        if company_blurb:
            jd_parts.append(company_blurb)
        if skills:
            jd_parts.append("Key skills: " + ", ".join(skills))
        jd_text = "\n\n".join(jd_parts)

        items.append({
            "title": role or full_title,
            "company": company,
            "location": location,
            "jd_text": jd_text,
            "skills": ", ".join(skills),
        })
    return items


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
        page.goto(OPPS_URL, wait_until="domcontentloaded", timeout=45000)
        self._human_delay()
        url = page.url
        if "/login" in url:
            print("[instahyre] login required — log in once so the session is saved "
                  "to .auth/instahyre.json, then re-run.")
            return
        if "/onboard" in url:
            print("[instahyre] your Instahyre profile/onboarding is incomplete, so no "
                  "opportunities are shown yet. Finish your profile at instahyre.com first.")
            return

        items = parse_opportunities_list(page.content())
        if keywords:
            kw = keywords.lower()
            items = [
                i for i in items
                if kw in i["title"].lower() or kw in i["company"].lower() or kw in i["skills"].lower()
            ]

        for it in items[:max_jobs]:
            if not it["jd_text"]:
                continue
            pseudo_url = f"{BASE}/candidate/opportunities/#{_slug(it['company'] + '-' + it['title'])}"
            yield Job(
                job_id=derive_job_id(SOURCE, pseudo_url),
                source=SOURCE,
                title=it["title"],
                company=it["company"],
                location=it["location"],
                remote_type=_remote_type(it["location"]),
                url=pseudo_url,
                posted_date="",
                jd_text=it["jd_text"],
                scraped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                tailored=False,
            )

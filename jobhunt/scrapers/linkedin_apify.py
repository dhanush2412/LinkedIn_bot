"""LinkedIn job discovery via Apify.

This does NOT use the user's LinkedIn account or browser — it calls Apify's
hosted "LinkedIn Jobs Scraper" actor (curious_coder/linkedin-jobs-scraper), which
scrapes with Apify's own infrastructure. So the user's LinkedIn account carries no
ban risk. Requires APIFY_TOKEN in the environment.

Flow: a LinkedIn job-search URL (the user copies it from their browser) -> Apify
actor -> list of job dicts -> Job objects -> jobs.csv -> tailor (honest), exactly
like the other sources.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from jobhunt.models import Job, derive_job_id


ACTOR_ID = "hKByXkMQaC5Qt9UMN"  # curious_coder/linkedin-jobs-scraper
SOURCE = "linkedin"
RUN_SYNC_URL = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
_MIN_COUNT = 10  # the actor rejects count < 10


def _get_token(token: str | None) -> str:
    token = token or os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_TOKEN not set in environment (.env)")
    return token


def _remote_type(location: str, employment_type: str = "") -> str:
    blob = f"{location} {employment_type}".lower()
    if "remote" in blob:
        return "remote"
    if "hybrid" in blob:
        return "hybrid"
    return "onsite"


def parse_applicants(raw: Any) -> int | None:
    """Normalize Apify's applicantsCount (int, '27', 'Over 100 applicants', '200+')
    to an int, or None when unknown."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    m = re.search(r"\d+", str(raw))
    return int(m.group(0)) if m else None


def parse_apify_jobs(items: list[dict[str, Any]]) -> list[Job]:
    """Map raw Apify dataset items to Job objects. Pure function (no network)."""
    jobs: list[Job] = []
    for it in items:
        link = it.get("link") or it.get("jobUrl") or ""
        title = (it.get("title") or "").strip()
        if not link or not title:
            continue
        location = (it.get("location") or "").strip()
        jd = (it.get("descriptionText") or "").strip()
        n = parse_applicants(it.get("applicantsCount"))
        jobs.append(Job(
            job_id=derive_job_id(SOURCE, link),
            source=SOURCE,
            title=title,
            company=(it.get("companyName") or "").strip(),
            location=location,
            remote_type=_remote_type(location, it.get("employmentType") or ""),
            url=link,
            posted_date=(it.get("postedAt") or "").strip(),
            jd_text=jd,
            scraped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            applicants="" if n is None else str(n),
            tailored=False,
        ))
    return jobs


def fetch_linkedin_jobs(
    search_url: str,
    count: int = 50,
    scrape_company: bool = False,
    token: str | None = None,
    timeout: float = 300.0,
) -> list[dict[str, Any]]:
    """Run the Apify LinkedIn actor synchronously and return raw dataset items."""
    token = _get_token(token)
    payload = {
        "urls": [search_url],
        "count": max(count, _MIN_COUNT),
        "scrapeCompany": scrape_company,
    }
    resp = httpx.post(RUN_SYNC_URL, params={"token": token}, json=payload, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Apify run failed ({resp.status_code}): {resp.text[:300]}")
    return resp.json()


def filter_by_applicants(jobs: list[Job], max_applicants: int | None) -> list[Job]:
    """Keep jobs with a known applicant count <= max_applicants. Jobs whose count
    is unknown ("") are KEPT (benefit of the doubt). No-op when max_applicants is None."""
    if max_applicants is None:
        return jobs
    out = []
    for j in jobs:
        if j.applicants == "":
            out.append(j)
        elif int(j.applicants) <= max_applicants:
            out.append(j)
    return out


def scrape_linkedin(
    search_url: str,
    max_jobs: int = 50,
    token: str | None = None,
    max_applicants: int | None = None,
) -> list[Job]:
    # Apify caps low; over-fetch a bit so the applicant filter still yields enough.
    fetch_count = max_jobs if max_applicants is None else max(max_jobs * 3, max_jobs)
    items = fetch_linkedin_jobs(search_url, count=fetch_count, token=token)
    jobs = parse_apify_jobs(items)
    jobs = filter_by_applicants(jobs, max_applicants)
    return jobs[:max_jobs]

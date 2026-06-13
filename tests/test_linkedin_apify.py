"""Tests for the Apify LinkedIn parser, run against a REAL sample of Apify output
(tests/fixtures/apify_linkedin_sample.json). The network call itself is not tested
here (it costs money + needs a token); the pure mapper is."""
import json
from pathlib import Path
from jobhunt.scrapers.linkedin_apify import parse_apify_jobs, _remote_type
from jobhunt.models import Job

FIXTURE = Path(__file__).parent / "fixtures" / "apify_linkedin_sample.json"


def test_parse_apify_jobs_maps_real_sample():
    items = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jobs = parse_apify_jobs(items)
    assert len(jobs) > 0
    for j in jobs:
        assert isinstance(j, Job)
        assert j.source == "linkedin"
        assert j.title
        assert j.url.startswith("http")
        assert j.job_id and len(j.job_id) == 12


def test_parse_apify_jobs_carries_description_and_company():
    items = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jobs = parse_apify_jobs(items)
    # at least one job should have a non-trivial JD and a company
    assert any(len(j.jd_text) > 50 for j in jobs)
    assert any(j.company for j in jobs)


def test_parse_apify_jobs_skips_items_without_link_or_title():
    items = [
        {"title": "No link", "companyName": "X"},
        {"link": "https://linkedin.com/jobs/view/1", "title": "Good", "companyName": "Y",
         "location": "Remote", "descriptionText": "desc"},
        {"link": "https://linkedin.com/jobs/view/2"},  # no title
    ]
    jobs = parse_apify_jobs(items)
    assert len(jobs) == 1
    assert jobs[0].title == "Good"


def test_remote_type_detection():
    assert _remote_type("Remote, India") == "remote"
    assert _remote_type("Bengaluru (Hybrid)") == "hybrid"
    assert _remote_type("Mumbai, Maharashtra, India") == "onsite"


def test_parse_apify_jobs_dedupes_stable_ids():
    items = json.loads(FIXTURE.read_text(encoding="utf-8"))
    j1 = parse_apify_jobs(items)
    j2 = parse_apify_jobs(items)
    # deterministic job_ids across runs
    assert [j.job_id for j in j1] == [j.job_id for j in j2]

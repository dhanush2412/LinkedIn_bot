"""Tests for the Apify LinkedIn parser, run against a REAL sample of Apify output
(tests/fixtures/apify_linkedin_sample.json). The network call itself is not tested
here (it costs money + needs a token); the pure mapper is."""
import json
from pathlib import Path
from jobhunt.scrapers.linkedin_apify import (
    parse_apify_jobs, _remote_type, parse_applicants, filter_by_applicants,
)
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


def test_parse_applicants_handles_various_formats():
    assert parse_applicants(27) == 27
    assert parse_applicants("27") == 27
    assert parse_applicants("Over 100 applicants") == 100
    assert parse_applicants("200+") == 200
    assert parse_applicants("") is None
    assert parse_applicants(None) is None
    assert parse_applicants("no number") is None


def _job_with_applicants(n: str, jid="x") -> Job:
    return Job(job_id=jid, source="linkedin", title="T", company="C", location="Remote",
               remote_type="remote", url=f"https://x/{jid}", posted_date="", jd_text="d",
               scraped_at="t", applicants=n)


def test_filter_by_applicants_keeps_low_and_unknown():
    jobs = [
        _job_with_applicants("5", "a"),
        _job_with_applicants("150", "b"),
        _job_with_applicants("", "c"),  # unknown — kept
        _job_with_applicants("100", "d"),
    ]
    kept = filter_by_applicants(jobs, max_applicants=100)
    assert sorted(j.job_id for j in kept) == ["a", "c", "d"]  # 150 dropped


def test_filter_by_applicants_none_is_noop():
    jobs = [_job_with_applicants("999", "a")]
    assert filter_by_applicants(jobs, None) == jobs


def test_parse_apify_jobs_reads_applicants_count():
    items = [{
        "link": "https://linkedin.com/jobs/view/1", "title": "Dev", "companyName": "Y",
        "location": "Remote", "descriptionText": "desc", "applicantsCount": 12,
    }]
    jobs = parse_apify_jobs(items)
    assert jobs[0].applicants == "12"

"""Tests for the Instahyre parser, run against a REAL captured opportunities page
(tests/fixtures/html/instahyre_list.html). Instahyre is a login-walled Angular SPA;
the scraper is read-only (never clicks, to avoid accidentally applying).
"""
from pathlib import Path
from jobhunt.scrapers.instahyre import (
    parse_opportunities_list,
    _split_company_role,
    _slug,
)

FIXTURES = Path(__file__).parent / "fixtures" / "html"


def test_parse_opportunities_list_extracts_cards():
    html = (FIXTURES / "instahyre_list.html").read_text(encoding="utf-8")
    items = parse_opportunities_list(html)
    assert len(items) > 0
    for it in items:
        assert it["title"]
        assert "jd_text" in it


def test_parse_opportunities_list_real_job_fields():
    html = (FIXTURES / "instahyre_list.html").read_text(encoding="utf-8")
    items = parse_opportunities_list(html)
    # The captured fixture contains the Zetwerk DevOps Intern opportunity.
    zet = next((i for i in items if "zetwerk" in i["company"].lower()), None)
    assert zet is not None
    assert "DevOps" in zet["title"]
    assert zet["location"]  # e.g. "Bangalore"
    assert len(zet["jd_text"]) > 30
    assert "DevOps" in zet["skills"] or "AWS" in zet["skills"]


def test_split_company_role():
    company, role = _split_company_role("Zetwerk - DevOps Intern (Internship)")
    assert company == "Zetwerk"
    assert role == "DevOps Intern (Internship)"


def test_split_company_role_no_separator():
    company, role = _split_company_role("Backend Engineer")
    assert company == ""
    assert role == "Backend Engineer"


def test_slug_is_url_safe():
    assert _slug("Zetwerk - DevOps Intern (Internship)") == "zetwerk-devops-intern-internship"

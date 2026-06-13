"""Tests for the Instahyre parser.

NOTE: These run against SYNTHETIC fixtures (tests/fixtures/html/instahyre_*.html),
not real captured HTML, because Instahyre requires login. They verify the parsing
LOGIC is sound; the real-world selectors must be validated by capturing a logged-in
page via scripts/capture_instahyre_fixture.py and adjusting instahyre.py to match.
"""
from pathlib import Path
from jobhunt.scrapers.instahyre import parse_opportunities_list, parse_opportunity_detail

FIXTURES = Path(__file__).parent / "fixtures" / "html"


def test_parse_opportunities_list_yields_links():
    html = (FIXTURES / "instahyre_list.html").read_text(encoding="utf-8")
    items = parse_opportunities_list(html)
    assert len(items) > 0
    for it in items:
        assert it["url"].startswith("https://")
        assert it["title"]


def test_parse_opportunities_list_dedupes_urls():
    html = (FIXTURES / "instahyre_list.html").read_text(encoding="utf-8")
    items = parse_opportunities_list(html)
    urls = [it["url"] for it in items]
    assert len(urls) == len(set(urls))


def test_parse_opportunity_detail_extracts_jd():
    html = (FIXTURES / "instahyre_job.html").read_text(encoding="utf-8")
    d = parse_opportunity_detail(html)
    assert d["title"]
    assert d["company"]
    assert len(d["jd_text"]) > 50

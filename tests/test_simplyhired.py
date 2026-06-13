from pathlib import Path
from jobhunt.scrapers.simplyhired import parse_search_results, parse_job_detail

FIXTURES = Path(__file__).parent / "fixtures" / "html"


def test_parse_search_results_returns_job_links():
    html = (FIXTURES / "simplyhired_search.html").read_text(encoding="utf-8")
    cards = parse_search_results(html, source_base="https://www.simplyhired.com")
    assert len(cards) > 0
    for c in cards:
        assert c["title"]
        assert c["company"]
        assert c["url"].startswith("https://")


def test_parse_job_detail_extracts_jd():
    html = (FIXTURES / "simplyhired_job.html").read_text(encoding="utf-8")
    detail = parse_job_detail(html)
    assert detail["title"]
    assert detail["company"]
    assert len(detail["jd_text"]) > 100

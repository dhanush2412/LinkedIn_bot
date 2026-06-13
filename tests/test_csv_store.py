from pathlib import Path
from jobhunt.csv_store import JobsCsv
from jobhunt.models import Job


def _make_job(job_id: str = "abc123", url: str = "https://example.com/job/1") -> Job:
    return Job(
        job_id=job_id,
        source="simplyhired",
        title="Engineer",
        company="Acme",
        location="Remote",
        remote_type="remote",
        url=url,
        posted_date="2026-05-20",
        jd_text="Job description",
        scraped_at="2026-05-23T10:00:00",
        tailored=False,
    )


def test_append_writes_header_on_first_write(tmp_path):
    csv_path = tmp_path / "jobs.csv"
    store = JobsCsv(csv_path)
    store.append([_make_job()])
    content = csv_path.read_text(encoding="utf-8")
    assert "job_id,source,title" in content.splitlines()[0]


def test_append_dedupes_by_job_id(tmp_path):
    csv_path = tmp_path / "jobs.csv"
    store = JobsCsv(csv_path)
    store.append([_make_job("aaa"), _make_job("bbb")])
    inserted = store.append([_make_job("aaa"), _make_job("ccc")])
    assert inserted == 1
    rows = store.read_all()
    assert len(rows) == 3
    assert sorted(j.job_id for j in rows) == ["aaa", "bbb", "ccc"]


def test_read_all_returns_jobs(tmp_path):
    csv_path = tmp_path / "jobs.csv"
    store = JobsCsv(csv_path)
    store.append([_make_job("xyz")])
    rows = store.read_all()
    assert len(rows) == 1
    assert rows[0].job_id == "xyz"
    assert rows[0].tailored is False


def test_mark_tailored_updates_row(tmp_path):
    csv_path = tmp_path / "jobs.csv"
    store = JobsCsv(csv_path)
    store.append([_make_job("xyz")])
    store.mark_tailored("xyz")
    rows = store.read_all()
    assert rows[0].tailored is True


def test_find_by_id_or_url_finds_by_id(tmp_path):
    csv_path = tmp_path / "jobs.csv"
    store = JobsCsv(csv_path)
    store.append([_make_job("xyz", url="https://x.com/j")])
    found = store.find("xyz")
    assert found is not None
    assert found.job_id == "xyz"


def test_find_by_id_or_url_finds_by_url(tmp_path):
    csv_path = tmp_path / "jobs.csv"
    store = JobsCsv(csv_path)
    store.append([_make_job("xyz", url="https://x.com/j")])
    found = store.find("https://x.com/j")
    assert found is not None
    assert found.job_id == "xyz"


def test_find_returns_none_when_missing(tmp_path):
    csv_path = tmp_path / "jobs.csv"
    store = JobsCsv(csv_path)
    assert store.find("nope") is None

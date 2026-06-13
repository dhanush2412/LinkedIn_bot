from pathlib import Path
from jobhunt.csv_store import JobsCsv
from jobhunt.models import Job


def test_append_migrates_old_schema_csv(tmp_path):
    # Simulate a pre-"applicants" CSV (11 columns, no applicants col).
    csv_path = tmp_path / "jobs.csv"
    old_header = ("job_id,source,title,company,location,remote_type,"
                  "url,posted_date,jd_text,scraped_at,tailored")
    csv_path.write_text(
        old_header + "\n"
        "old1,linkedin,Dev,Acme,Remote,remote,https://x/1,,jd,2026-01-01T00:00:00,false\n",
        encoding="utf-8",
    )
    store = JobsCsv(csv_path)
    # Appending a new job should migrate the file to the new schema first.
    store.append([_make_job("new1")])
    rows = store.read_all()
    ids = sorted(j.job_id for j in rows)
    assert ids == ["new1", "old1"]
    # old row gains an empty applicants field, header now includes it
    header_line = csv_path.read_text(encoding="utf-8").splitlines()[0]
    assert "applicants" in header_line
    old = next(j for j in rows if j.job_id == "old1")
    assert old.applicants == ""


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


def test_append_dedupes_within_a_single_batch(tmp_path):
    csv_path = tmp_path / "jobs.csv"
    store = JobsCsv(csv_path)
    inserted = store.append([_make_job("dup"), _make_job("dup"), _make_job("uniq")])
    assert inserted == 2
    rows = store.read_all()
    assert sorted(j.job_id for j in rows) == ["dup", "uniq"]


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

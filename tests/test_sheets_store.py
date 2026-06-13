"""Tests for the Google Sheets mirror. gspread/network are mocked — no real
credentials or sheet needed."""
import sys
import types
from unittest.mock import MagicMock
import pytest

from jobhunt.models import Job
from jobhunt import sheets_store
from jobhunt.sheets_store import HEADER, _row_from_job, is_configured


def _job(job_id="abc123", title="Engineer") -> Job:
    return Job(
        job_id=job_id, source="linkedin", title=title, company="Acme",
        location="Remote", remote_type="remote", url="https://x.com/j/1",
        posted_date="2026-05-20", jd_text="line1\nline2 " + "x" * 500,
        scraped_at="2026-05-23T10:00:00", tailored=False,
    )


def test_is_configured_reads_env(monkeypatch):
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("JOBHUNT_SHEET_ID", raising=False)
    assert is_configured() is False
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", "creds.json")
    monkeypatch.setenv("JOBHUNT_SHEET_ID", "sheet123")
    assert is_configured() is True


def test_row_from_job_matches_header_length():
    row = _row_from_job(_job())
    assert len(row) == len(HEADER)


def test_row_snippet_is_single_line_and_truncated():
    row = _row_from_job(_job())
    snippet = row[HEADER.index("jd_snippet")]
    assert "\n" not in snippet
    assert len(snippet) <= 300


def test_maybe_store_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("JOBHUNT_SHEET_ID", raising=False)
    assert sheets_store.maybe_store() is None


def _install_fake_gspread(monkeypatch, existing_col):
    """Install a fake gspread + google.oauth2 so SheetsStore() works offline."""
    fake_ws = MagicMock()
    # col_values(1) returns header + existing ids; row_values(1) returns header
    fake_ws.row_values.return_value = HEADER
    fake_ws.col_values.return_value = ["job_id"] + existing_col
    fake_sheet = MagicMock()
    fake_sheet.sheet1 = fake_ws
    fake_client = MagicMock()
    fake_client.open_by_key.return_value = fake_sheet

    fake_gspread = types.ModuleType("gspread")
    fake_gspread.authorize = lambda creds: fake_client
    monkeypatch.setitem(sys.modules, "gspread", fake_gspread)

    # fake google.oauth2.service_account.Credentials
    g = types.ModuleType("google")
    oauth2 = types.ModuleType("google.oauth2")
    sa = types.ModuleType("google.oauth2.service_account")
    sa.Credentials = MagicMock()
    sa.Credentials.from_service_account_file = lambda f, scopes: object()
    oauth2.service_account = sa
    g.oauth2 = oauth2
    monkeypatch.setitem(sys.modules, "google", g)
    monkeypatch.setitem(sys.modules, "google.oauth2", oauth2)
    monkeypatch.setitem(sys.modules, "google.oauth2.service_account", sa)
    return fake_ws


def test_append_dedupes_against_existing_sheet_ids(monkeypatch):
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", "creds.json")
    monkeypatch.setenv("JOBHUNT_SHEET_ID", "sheet123")
    fake_ws = _install_fake_gspread(monkeypatch, existing_col=["existing1"])
    store = sheets_store.SheetsStore()
    added = store.append([_job("existing1"), _job("new1"), _job("new2")])
    assert added == 2
    fake_ws.append_rows.assert_called_once()
    rows_written = fake_ws.append_rows.call_args[0][0]
    assert [r[0] for r in rows_written] == ["new1", "new2"]


def test_mark_tailored_updates_matching_row(monkeypatch):
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", "creds.json")
    monkeypatch.setenv("JOBHUNT_SHEET_ID", "sheet123")
    fake_ws = _install_fake_gspread(monkeypatch, existing_col=["aaa", "bbb"])
    store = sheets_store.SheetsStore()
    ok = store.mark_tailored("bbb")
    assert ok is True
    # row 3 (header=1, aaa=2, bbb=3), tailored col index
    args = fake_ws.update_cell.call_args[0]
    assert args[0] == 3
    assert args[2] == "true"


def test_mark_tailored_missing_returns_false(monkeypatch):
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", "creds.json")
    monkeypatch.setenv("JOBHUNT_SHEET_ID", "sheet123")
    _install_fake_gspread(monkeypatch, existing_col=["aaa"])
    store = sheets_store.SheetsStore()
    assert store.mark_tailored("nope") is False

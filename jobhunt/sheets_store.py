"""Optional Google Sheets mirror of the jobs table.

The local CSV (jobs.csv) stays the source of truth that `tailor` reads. When
Google Sheets is configured, every scrape ALSO pushes new jobs to a Google Sheet
so they can be viewed/tracked from a phone or any browser, with an "applied"
column to track progress.

Auth uses a Google service account (no interactive OAuth). Configure via env:
  GOOGLE_SERVICE_ACCOUNT_FILE = path to the service-account JSON key
  JOBHUNT_SHEET_ID            = the target spreadsheet's ID (from its URL)
The target sheet must be shared (Editor) with the service account's email.
"""
from __future__ import annotations

import os

from jobhunt.models import Job


# Columns written to the sheet (header row), in order.
HEADER = [
    "job_id", "source", "title", "company", "location", "remote_type",
    "posted_date", "applicants", "url", "applied", "tailored", "scraped_at", "jd_snippet",
]


def is_configured() -> bool:
    return bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
               and os.environ.get("JOBHUNT_SHEET_ID"))


def _row_from_job(job: Job) -> list[str]:
    snippet = (job.jd_text or "").replace("\n", " ").strip()[:300]
    return [
        job.job_id, job.source, job.title, job.company, job.location,
        job.remote_type, job.posted_date, job.applicants, job.url, "",
        "true" if job.tailored else "false", job.scraped_at, snippet,
    ]


class SheetsStore:
    def __init__(self, sheet_id: str | None = None, creds_file: str | None = None):
        import gspread  # lazy import so the tool runs without the dependency
        from google.oauth2.service_account import Credentials

        sheet_id = sheet_id or os.environ["JOBHUNT_SHEET_ID"]
        creds_file = creds_file or os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
        client = gspread.authorize(creds)
        self._ws = client.open_by_key(sheet_id).sheet1
        self._ensure_header()

    def _ensure_header(self) -> None:
        first = self._ws.row_values(1)
        if first != HEADER:
            if not first:
                self._ws.append_row(HEADER, value_input_option="RAW")
            else:
                self._ws.update([HEADER], "A1")

    def existing_ids(self) -> set[str]:
        col = self._ws.col_values(1)  # column A = job_id (includes header)
        return set(col[1:]) if len(col) > 1 else set()

    def append(self, jobs: list[Job]) -> int:
        existing = self.existing_ids()
        rows = []
        for j in jobs:
            if j.job_id in existing:
                continue
            existing.add(j.job_id)
            rows.append(_row_from_job(j))
        if rows:
            self._ws.append_rows(rows, value_input_option="USER_ENTERED")
        return len(rows)

    def rebuild(self, jobs: list[Job]) -> int:
        """Wipe the sheet and rewrite header + all rows. Use after a schema change
        that misaligns existing rows. NOTE: this clears the 'applied' column too."""
        self._ws.clear()
        self._ws.append_row(HEADER, value_input_option="RAW")
        rows = [_row_from_job(j) for j in jobs]
        if rows:
            self._ws.append_rows(rows, value_input_option="USER_ENTERED")
        return len(rows)

    def mark_tailored(self, job_id: str) -> bool:
        ids = self._ws.col_values(1)
        for idx, val in enumerate(ids):
            if val == job_id:
                row_num = idx + 1
                tailored_col = HEADER.index("tailored") + 1
                self._ws.update_cell(row_num, tailored_col, "true")
                return True
        return False


def maybe_store() -> "SheetsStore | None":
    """Return a SheetsStore if configured and importable, else None (silently)."""
    if not is_configured():
        return None
    try:
        return SheetsStore()
    except Exception as e:  # missing dep, bad creds, network — don't break the CLI
        print(f"[sheets] skipped (not pushing to Google Sheets): {e}")
        return None

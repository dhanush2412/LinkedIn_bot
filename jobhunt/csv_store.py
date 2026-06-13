from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from jobhunt.models import Job


class JobsCsv:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _existing_ids(self) -> set[str]:
        if not self.path.exists():
            return set()
        with self.path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return {row["job_id"] for row in reader}

    def _header_matches(self) -> bool:
        if not self.path.exists():
            return True
        with self.path.open("r", encoding="utf-8", newline="") as f:
            first = f.readline().strip()
        return first == ",".join(Job.CSV_FIELDS)

    def _migrate_if_needed(self) -> None:
        """If the on-disk header differs from the current schema, rewrite the file
        with the new columns (old rows get safe defaults via from_csv_row)."""
        if self.path.exists() and not self._header_matches():
            rows = self.read_all()
            with self.path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=Job.CSV_FIELDS)
                writer.writeheader()
                for j in rows:
                    writer.writerow(j.to_csv_row())

    def append(self, jobs: Iterable[Job]) -> int:
        self._migrate_if_needed()
        existing = self._existing_ids()
        new = []
        for j in jobs:
            if j.job_id in existing:
                continue
            existing.add(j.job_id)  # also dedupe within this batch
            new.append(j)
        if not new:
            return 0
        write_header = not self.path.exists()
        with self.path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=Job.CSV_FIELDS)
            if write_header:
                writer.writeheader()
            for j in new:
                writer.writerow(j.to_csv_row())
        return len(new)

    def read_all(self) -> list[Job]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8", newline="") as f:
            return [Job.from_csv_row(row) for row in csv.DictReader(f)]

    def find(self, job_id_or_url: str) -> Job | None:
        for j in self.read_all():
            if j.job_id == job_id_or_url or j.url == job_id_or_url:
                return j
        return None

    def mark_tailored(self, job_id: str) -> None:
        rows = self.read_all()
        with self.path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=Job.CSV_FIELDS)
            writer.writeheader()
            for j in rows:
                if j.job_id == job_id:
                    j.tailored = True
                writer.writerow(j.to_csv_row())

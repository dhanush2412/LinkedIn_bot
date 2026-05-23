from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any
from urllib.parse import urlparse


def derive_job_id(source: str, url: str) -> str:
    parsed = urlparse(url)
    canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".lower().rstrip("/")
    digest = hashlib.sha1(f"{source}|{canonical}".encode("utf-8")).hexdigest()
    return digest[:12]


@dataclass
class Job:
    job_id: str
    source: str
    title: str
    company: str
    location: str
    remote_type: str
    url: str
    posted_date: str
    jd_text: str
    scraped_at: str
    tailored: bool = False

    CSV_FIELDS = [
        "job_id", "source", "title", "company", "location", "remote_type",
        "url", "posted_date", "jd_text", "scraped_at", "tailored",
    ]

    def to_csv_row(self) -> dict[str, str]:
        d = asdict(self)
        d["tailored"] = "true" if self.tailored else "false"
        return {k: str(d[k]) for k in self.CSV_FIELDS}

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "Job":
        return cls(
            job_id=row["job_id"],
            source=row["source"],
            title=row["title"],
            company=row["company"],
            location=row["location"],
            remote_type=row["remote_type"],
            url=row["url"],
            posted_date=row["posted_date"],
            jd_text=row["jd_text"],
            scraped_at=row["scraped_at"],
            tailored=row["tailored"].lower() == "true",
        )


@dataclass
class CandidateProfile:
    name: str
    email: str
    phone: str
    location: str
    total_years_experience: float
    current_title: str
    current_company: str
    skills: list[str]
    experience: list[dict[str, Any]]
    education: list[dict[str, Any]]
    links: dict[str, str]
    biodata_text: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "CandidateProfile":
        return cls(**data)


@dataclass
class TailoredOutput:
    cover_letter: str
    tailored_resume_md: str
    form_answers: dict[str, str]
    resume_pdf_path: str = ""

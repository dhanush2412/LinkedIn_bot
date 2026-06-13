from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
import fitz  # pymupdf

from jobhunt.models import CandidateProfile


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s\-]{8,}\d")
KNOWN_SKILLS = {
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
    "React", "Vue", "Angular", "Node.js", "FastAPI", "Django", "Flask", "Spring",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform",
    "Git", "Linux", "GraphQL", "REST", "gRPC",
}


def _extract_skills(text: str) -> list[str]:
    # Use lookarounds instead of \b so skills ending in symbols (C++, C#, Node.js)
    # match correctly — \b fails around '+'/'#' because they are non-word chars.
    return sorted({
        s for s in KNOWN_SKILLS
        if re.search(rf"(?<!\w){re.escape(s)}(?!\w)", text, re.IGNORECASE)
    })


def _parse_resume_pdf(path: Path) -> dict[str, Any]:
    doc = fitz.open(str(path))
    try:
        text = "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    name = lines[0] if lines else ""
    email_match = EMAIL_RE.search(text)
    email = email_match.group(0) if email_match else ""
    phone_match = PHONE_RE.search(text)
    phone = phone_match.group(0).strip() if phone_match else ""

    location = ""
    for ln in lines[:5]:
        for city in ("Bengaluru", "Bangalore", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Pune", "Remote"):
            if city in ln:
                location = ln
                break
        if location:
            break

    skills = _extract_skills(text)

    years = 0.0
    yr_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)", text, re.IGNORECASE)
    if yr_match:
        years = float(yr_match.group(1))

    current_title = ""
    current_company = ""
    exp_match = re.search(r"(?:Senior\s+\w+|Software\s+Engineer|Engineer|Developer)[^\n]*?[—\-]\s*([^()\n]+?)\s*\(", text)
    if exp_match:
        current_company = exp_match.group(1).strip()
        title_match = re.search(r"^([^\n]+?)\s*[—\-]\s*" + re.escape(current_company), text, re.MULTILINE)
        if title_match:
            current_title = title_match.group(1).strip()

    links: dict[str, str] = {}
    for kw, key in (("github.com/", "github"), ("linkedin.com/", "linkedin")):
        m = re.search(rf"({kw}[\w\-./]+)", text)
        if m:
            links[key] = "https://" + m.group(1)

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "location": location,
        "total_years_experience": years,
        "current_title": current_title,
        "current_company": current_company,
        "skills": skills,
        "experience": [],
        "education": [],
        "links": links,
    }


def _cache_is_fresh(cache_path: Path, resume_path: Path) -> bool:
    if not cache_path.exists():
        return False
    return cache_path.stat().st_mtime >= resume_path.stat().st_mtime


def load_profile(profile_dir: str | Path) -> CandidateProfile:
    profile_dir = Path(profile_dir)
    resume = profile_dir / "resume.pdf"
    biodata = profile_dir / "biodata.md"
    cache = profile_dir / "parsed.json"

    if not resume.exists():
        raise FileNotFoundError(f"Resume not found at {resume}")

    biodata_text = biodata.read_text(encoding="utf-8") if biodata.exists() else ""

    if _cache_is_fresh(cache, resume):
        parsed = json.loads(cache.read_text(encoding="utf-8"))
        parsed.pop("biodata_text", None)
    else:
        parsed = _parse_resume_pdf(resume)
        cache.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

    return CandidateProfile(biodata_text=biodata_text, **parsed)

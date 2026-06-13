import json
from pathlib import Path
import pytest
from jobhunt.profile_loader import load_profile, _parse_resume_pdf, _extract_skills
from jobhunt.models import CandidateProfile

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_RESUME = FIXTURES / "resumes" / "sample_resume.pdf"
SAMPLE_BIODATA = FIXTURES / "biodata" / "sample_biodata.md"


def test_parse_resume_pdf_extracts_basic_fields():
    parsed = _parse_resume_pdf(SAMPLE_RESUME)
    assert parsed["name"] == "Jane Doe"
    assert parsed["email"] == "jane.doe@example.com"
    assert "9876543210" in parsed["phone"]
    assert "Bengaluru" in parsed["location"]


def test_parse_resume_pdf_extracts_skills():
    parsed = _parse_resume_pdf(SAMPLE_RESUME)
    assert "Python" in parsed["skills"]
    assert "FastAPI" in parsed["skills"]


def test_extract_skills_matches_symbol_skills():
    text = "Languages: Python, C++, C#, Node.js and Go. Frameworks: FastAPI."
    skills = _extract_skills(text)
    assert "C++" in skills
    assert "C#" in skills
    assert "Node.js" in skills
    assert "Python" in skills


def test_extract_skills_does_not_partial_match():
    # "Java" must not match inside "JavaScript"
    skills = _extract_skills("Strong in JavaScript and TypeScript.")
    assert "JavaScript" in skills
    assert "Java" not in skills


def test_load_profile_combines_resume_and_biodata(tmp_path):
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    (profile_dir / "resume.pdf").write_bytes(SAMPLE_RESUME.read_bytes())
    (profile_dir / "biodata.md").write_text(SAMPLE_BIODATA.read_text(encoding="utf-8"), encoding="utf-8")
    profile = load_profile(profile_dir)
    assert isinstance(profile, CandidateProfile)
    assert profile.name == "Jane Doe"
    assert "Salary expectations" in profile.biodata_text
    assert "Python" in profile.skills


def test_load_profile_writes_parsed_cache(tmp_path):
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    (profile_dir / "resume.pdf").write_bytes(SAMPLE_RESUME.read_bytes())
    (profile_dir / "biodata.md").write_text("# biodata", encoding="utf-8")
    load_profile(profile_dir)
    cache = profile_dir / "parsed.json"
    assert cache.exists()
    data = json.loads(cache.read_text(encoding="utf-8"))
    assert data["name"] == "Jane Doe"


def test_load_profile_uses_cache_when_resume_unchanged(tmp_path, mocker):
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    (profile_dir / "resume.pdf").write_bytes(SAMPLE_RESUME.read_bytes())
    (profile_dir / "biodata.md").write_text("# biodata", encoding="utf-8")
    load_profile(profile_dir)
    spy = mocker.spy(__import__("jobhunt.profile_loader", fromlist=["_parse_resume_pdf"]), "_parse_resume_pdf")
    load_profile(profile_dir)
    assert spy.call_count == 0


def test_load_profile_missing_resume_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_profile(tmp_path)

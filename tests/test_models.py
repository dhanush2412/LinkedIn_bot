from jobhunt.models import Job, CandidateProfile, TailoredOutput, derive_job_id


def test_derive_job_id_is_deterministic():
    a = derive_job_id("simplyhired", "https://simplyhired.com/job/abc?utm=x")
    b = derive_job_id("simplyhired", "https://simplyhired.com/job/abc?utm=x")
    assert a == b
    assert len(a) == 12


def test_derive_job_id_strips_query_for_canonicalization():
    a = derive_job_id("simplyhired", "https://simplyhired.com/job/abc?utm=x")
    b = derive_job_id("simplyhired", "https://simplyhired.com/job/abc?utm=y")
    assert a == b


def test_job_id_differs_by_source():
    a = derive_job_id("simplyhired", "https://example.com/job/1")
    b = derive_job_id("instahyre", "https://example.com/job/1")
    assert a != b


def test_job_round_trips_to_csv_row():
    job = Job(
        job_id="abc123def456",
        source="simplyhired",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        remote_type="remote",
        url="https://example.com/job/1",
        posted_date="2026-05-20",
        jd_text="We are hiring...",
        scraped_at="2026-05-23T10:00:00",
        tailored=False,
    )
    row = job.to_csv_row()
    restored = Job.from_csv_row(row)
    assert restored == job


def test_candidate_profile_holds_biodata_text():
    profile = CandidateProfile(
        name="Test User",
        email="t@example.com",
        phone="+91 9999999999",
        location="Bengaluru, IN",
        total_years_experience=4.5,
        current_title="Engineer",
        current_company="Acme",
        skills=["Python", "FastAPI"],
        experience=[],
        education=[],
        links={"github": "https://github.com/x"},
        biodata_text="# About me\n...",
    )
    assert "About me" in profile.biodata_text


def test_candidate_profile_from_json_ignores_unknown_keys():
    data = {
        "name": "X", "email": "x@y.com", "phone": "1", "location": "L",
        "total_years_experience": 1.0, "current_title": "T", "current_company": "C",
        "skills": [], "experience": [], "education": [], "links": {},
        "biodata_text": "b",
        "legacy_field_from_old_version": "should be ignored",
    }
    profile = CandidateProfile.from_json(data)
    assert profile.name == "X"


def test_tailored_output_has_required_fields():
    out = TailoredOutput(
        cover_letter="Dear...",
        tailored_resume_md="# Resume\n...",
        form_answers={"q": "a"},
        resume_pdf_path="output/abc/tailored_resume.pdf",
    )
    assert out.cover_letter
    assert out.form_answers["q"] == "a"

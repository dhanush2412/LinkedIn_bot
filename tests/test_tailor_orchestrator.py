import json
from pathlib import Path
from jobhunt.models import Job, CandidateProfile, TailoredOutput
from jobhunt.tailor.orchestrator import tailor


def _job() -> Job:
    return Job(
        job_id="abc12345", source="simplyhired", title="Backend Engineer",
        company="WidgetCo", location="Remote", remote_type="remote",
        url="https://x.com/j/1", posted_date="", jd_text="Need Python.",
        scraped_at="2026-05-23T10:00:00", tailored=False,
    )


def _profile() -> CandidateProfile:
    return CandidateProfile(
        name="Jane Doe", email="j@x.com", phone="+91 9999999999",
        location="Bengaluru", total_years_experience=4.0,
        current_title="Engineer", current_company="Acme",
        skills=["Python"], experience=[], education=[],
        links={"github": "https://github.com/jane"},
        biodata_text="biodata text here",
    )


def test_tailor_writes_outputs_to_disk(tmp_path, mocker):
    mocker.patch(
        "jobhunt.tailor.orchestrator.call_groq_for_tailoring",
        return_value={
            "cover_letter": "Dear team, ...",
            "tailored_resume_md": "## Summary\nHi.",
            "form_answers": {"q": "a"},
        },
    )
    out = tailor(_job(), _profile(), form_questions=[], output_root=tmp_path)
    assert isinstance(out, TailoredOutput)
    job_dir = tmp_path / "abc12345"
    assert (job_dir / "cover_letter.txt").read_text(encoding="utf-8") == "Dear team, ..."
    assert (job_dir / "form_answers.json").exists()
    assert (job_dir / "tailored_resume.pdf").exists()
    assert out.resume_pdf_path == str(job_dir / "tailored_resume.pdf")


def test_tailor_uses_cache_on_second_call(tmp_path, mocker):
    spy = mocker.patch(
        "jobhunt.tailor.orchestrator.call_groq_for_tailoring",
        return_value={
            "cover_letter": "x", "tailored_resume_md": "## s\nhi", "form_answers": {},
        },
    )
    tailor(_job(), _profile(), form_questions=[], output_root=tmp_path)
    tailor(_job(), _profile(), form_questions=[], output_root=tmp_path)
    assert spy.call_count == 1


def test_tailor_force_bypasses_cache(tmp_path, mocker):
    spy = mocker.patch(
        "jobhunt.tailor.orchestrator.call_groq_for_tailoring",
        return_value={
            "cover_letter": "x", "tailored_resume_md": "## s\nhi", "form_answers": {},
        },
    )
    tailor(_job(), _profile(), form_questions=[], output_root=tmp_path)
    tailor(_job(), _profile(), form_questions=[], output_root=tmp_path, force=True)
    assert spy.call_count == 2

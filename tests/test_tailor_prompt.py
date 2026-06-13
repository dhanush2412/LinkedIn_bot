import json
from jobhunt.models import Job, CandidateProfile
from jobhunt.tailor.prompt import build_messages


def _profile() -> CandidateProfile:
    return CandidateProfile(
        name="Jane Doe", email="j@x.com", phone="+91 9999999999",
        location="Bengaluru", total_years_experience=4.0,
        current_title="Engineer", current_company="Acme",
        skills=["Python", "FastAPI"], experience=[], education=[],
        links={"github": "https://github.com/jane"},
        biodata_text="# About\nI prefer remote work.",
    )


def _job() -> Job:
    return Job(
        job_id="abc123", source="simplyhired", title="Backend Engineer",
        company="WidgetCo", location="Remote", remote_type="remote",
        url="https://x.com/j/1", posted_date="2026-05-20",
        jd_text="We need someone with Python and FastAPI.",
        scraped_at="2026-05-23T10:00:00", tailored=False,
    )


def test_build_messages_returns_system_and_user():
    msgs = build_messages(_job(), _profile(), form_questions=[])
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"


def test_system_prompt_forbids_invention():
    msgs = build_messages(_job(), _profile(), form_questions=[])
    assert "never invent" in msgs[0]["content"].lower() or "do not invent" in msgs[0]["content"].lower()


def test_user_prompt_includes_jd_resume_and_biodata():
    msgs = build_messages(_job(), _profile(), form_questions=[])
    body = msgs[1]["content"]
    assert "Backend Engineer" in body
    assert "WidgetCo" in body
    assert "FastAPI" in body
    assert "About" in body  # biodata header


def test_user_prompt_lists_form_questions_when_given():
    msgs = build_messages(_job(), _profile(), form_questions=["Why are you interested?", "Years of Python?"])
    body = msgs[1]["content"]
    assert "Why are you interested?" in body
    assert "Years of Python?" in body


def test_user_prompt_includes_schema_spec():
    msgs = build_messages(_job(), _profile(), form_questions=[])
    body = msgs[1]["content"]
    assert "cover_letter" in body
    assert "tailored_resume_md" in body
    assert "form_answers" in body

from jobhunt.models import CandidateProfile
from jobhunt.tailor.pdf_render import render_resume_pdf


def _profile() -> CandidateProfile:
    return CandidateProfile(
        name="Jane Doe", email="j@x.com", phone="+91 9999999999",
        location="Bengaluru", total_years_experience=4.0,
        current_title="Engineer", current_company="Acme",
        skills=["Python"], experience=[], education=[],
        links={"github": "https://github.com/jane", "linkedin": "https://linkedin.com/in/jane"},
        biodata_text="",
    )


def test_render_resume_pdf_writes_pdf_file(tmp_path):
    out = tmp_path / "resume.pdf"
    md = "## Summary\nBackend engineer with 4 years.\n\n## Skills\n- Python\n- FastAPI"
    render_resume_pdf(_profile(), md, out)
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"


def test_render_resume_pdf_includes_name_and_contact(tmp_path):
    out = tmp_path / "resume.pdf"
    render_resume_pdf(_profile(), "## Summary\nHi.", out)
    import fitz
    doc = fitz.open(str(out))
    text = "\n".join(p.get_text("text") for p in doc)
    doc.close()
    assert "Jane Doe" in text
    assert "j@x.com" in text
    assert "summary" in text.lower()  # body section present (CSS uppercases the heading)

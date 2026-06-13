from fastapi.testclient import TestClient
from unittest.mock import patch
from jobhunt.models import TailoredOutput
from jobhunt.server import app


def test_health_endpoint():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_tailor_endpoint_returns_output(tmp_path):
    fake_out = TailoredOutput(
        cover_letter="Dear team",
        tailored_resume_md="## Resume",
        form_answers={"Why?": "Because"},
        resume_pdf_path=str(tmp_path / "r.pdf"),
    )
    (tmp_path / "r.pdf").write_bytes(b"%PDF-1.4 test")
    with patch("jobhunt.server._handle_tailor", return_value=fake_out):
        client = TestClient(app)
        r = client.post("/tailor", json={
            "job_url": "https://linkedin.com/jobs/view/123",
            "job_title": "Backend Engineer",
            "company": "Acme",
            "location": "Remote",
            "jd_text": "We need Python.",
            "form_questions": ["Why?"],
        })
    assert r.status_code == 200
    body = r.json()
    assert body["cover_letter"] == "Dear team"
    assert body["form_answers"]["Why?"] == "Because"
    assert body["resume_pdf_url"].endswith("/r.pdf") or body["resume_pdf_url"].endswith("\\r.pdf")


def test_pdf_endpoint_serves_file(tmp_path):
    pdf = tmp_path / "abc123" / "tailored_resume.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 test")
    with patch("jobhunt.server._output_dir", return_value=tmp_path):
        client = TestClient(app)
        r = client.get("/pdf/abc123/tailored_resume.pdf")
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")

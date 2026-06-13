from __future__ import annotations

import json
from pathlib import Path

from jobhunt.models import Job, CandidateProfile, TailoredOutput
from jobhunt.tailor.prompt import build_messages
from jobhunt.tailor.groq_client import call_groq_for_tailoring
from jobhunt.tailor.pdf_render import render_resume_pdf


def _job_dir(output_root: Path, job_id: str) -> Path:
    d = Path(output_root) / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_cached(job_dir: Path) -> TailoredOutput | None:
    cl = job_dir / "cover_letter.txt"
    md = job_dir / "tailored_resume.md"
    pdf = job_dir / "tailored_resume.pdf"
    fa = job_dir / "form_answers.json"
    if cl.exists() and pdf.exists() and md.exists() and fa.exists():
        return TailoredOutput(
            cover_letter=cl.read_text(encoding="utf-8"),
            tailored_resume_md=md.read_text(encoding="utf-8"),
            form_answers=json.loads(fa.read_text(encoding="utf-8")),
            resume_pdf_path=str(pdf),
        )
    return None


def tailor(
    job: Job,
    profile: CandidateProfile,
    form_questions: list[str] | None = None,
    output_root: str | Path = "output",
    force: bool = False,
) -> TailoredOutput:
    output_root = Path(output_root)
    job_dir = _job_dir(output_root, job.job_id)

    if not force:
        cached = _load_cached(job_dir)
        if cached:
            return cached

    messages = build_messages(job, profile, form_questions or [])
    result = call_groq_for_tailoring(messages)

    cover = result["cover_letter"]
    resume_md = result["tailored_resume_md"]
    answers = result.get("form_answers", {})

    (job_dir / "cover_letter.txt").write_text(cover, encoding="utf-8")
    (job_dir / "tailored_resume.md").write_text(resume_md, encoding="utf-8")
    (job_dir / "form_answers.json").write_text(json.dumps(answers, indent=2), encoding="utf-8")

    pdf_path = job_dir / "tailored_resume.pdf"
    render_resume_pdf(profile, resume_md, pdf_path)

    return TailoredOutput(
        cover_letter=cover,
        tailored_resume_md=resume_md,
        form_answers=answers,
        resume_pdf_path=str(pdf_path),
    )

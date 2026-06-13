from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from jobhunt.models import Job, CandidateProfile, TailoredOutput, derive_job_id
from jobhunt.profile_loader import load_profile
from jobhunt.tailor.orchestrator import tailor


app = FastAPI(title="JobHunt local API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class TailorRequest(BaseModel):
    job_url: str
    job_title: str
    company: str
    location: str = ""
    jd_text: str
    form_questions: list[str] = []


class TailorResponse(BaseModel):
    job_id: str
    cover_letter: str
    form_answers: dict[str, str]
    resume_pdf_url: str
    resume_pdf_path: str


def _output_dir() -> Path:
    return Path(os.environ.get("JOBHUNT_OUTPUT_DIR", "./output"))


def _profile_dir() -> Path:
    return Path(os.environ.get("JOBHUNT_PROFILE_DIR", "./profile"))


def _handle_tailor(req: TailorRequest) -> TailoredOutput:
    profile: CandidateProfile = load_profile(_profile_dir())
    job_id = derive_job_id("linkedin", req.job_url)
    job = Job(
        job_id=job_id,
        source="linkedin",
        title=req.job_title,
        company=req.company,
        location=req.location,
        remote_type="onsite",
        url=req.job_url,
        posted_date="",
        jd_text=req.jd_text,
        scraped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        tailored=False,
    )
    return tailor(job, profile, form_questions=req.form_questions, output_root=_output_dir())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tailor", response_model=TailorResponse)
def tailor_endpoint(req: TailorRequest):
    try:
        out = _handle_tailor(req)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=f"Profile not loaded: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    job_id = derive_job_id("linkedin", req.job_url)
    pdf_name = Path(out.resume_pdf_path).name
    return TailorResponse(
        job_id=job_id,
        cover_letter=out.cover_letter,
        form_answers=out.form_answers,
        resume_pdf_url=f"/pdf/{job_id}/{pdf_name}",
        resume_pdf_path=str(out.resume_pdf_path),
    )


@app.get("/pdf/{job_id}/{filename}")
def get_pdf(job_id: str, filename: str):
    if "/" in job_id or "\\" in job_id or ".." in job_id or ".." in filename:
        raise HTTPException(status_code=400, detail="invalid path")
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="only pdf served")
    path = _output_dir() / job_id / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(str(path), media_type="application/pdf")

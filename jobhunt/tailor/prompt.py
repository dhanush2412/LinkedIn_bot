from __future__ import annotations

import json
from jobhunt.models import Job, CandidateProfile


SYSTEM_PROMPT = """You are a job application assistant. You generate tailored \
application materials for one candidate applying to one specific job.

HARD CONSTRAINTS:
1. NEVER invent skills, employers, projects, certifications, or years of experience \
that are not explicitly in the candidate's resume or biodata.
2. If a form question cannot be answered honestly from the available info, set its \
answer to the literal string "NEEDS_HUMAN".
3. Match the job description's vocabulary where the candidate honestly has the \
underlying skill. Do NOT keyword-stuff things they don't have.
4. Match the candidate's voice from their biodata.
5. Return ONLY valid JSON matching the requested schema. No prose around the JSON."""


def build_messages(job: Job, profile: CandidateProfile, form_questions: list[str]) -> list[dict[str, str]]:
    resume_summary = {
        "name": profile.name,
        "current_title": profile.current_title,
        "current_company": profile.current_company,
        "total_years_experience": profile.total_years_experience,
        "skills": profile.skills,
        "links": profile.links,
        "location": profile.location,
    }

    schema = {
        "cover_letter": "string — 150-220 words, addressed to the hiring team, no markdown headers, no salutation cliches",
        "tailored_resume_md": "string — full resume body in markdown, sections in this order: Summary, Skills, Experience, Education. NO contact header (we render that separately).",
        "form_answers": "object — keys are the literal question strings from the input; values are the answer strings, or 'NEEDS_HUMAN' if not honestly answerable",
    }

    user_content = f"""JOB
====
Title: {job.title}
Company: {job.company}
Location: {job.location} ({job.remote_type})
URL: {job.url}

JOB DESCRIPTION
================
{job.jd_text}

CANDIDATE RESUME (parsed)
==========================
{json.dumps(resume_summary, indent=2)}

CANDIDATE BIODATA (raw)
=========================
{profile.biodata_text}

FORM QUESTIONS TO ANSWER
=========================
{json.dumps(form_questions, indent=2) if form_questions else "(none)"}

OUTPUT SCHEMA (return JSON with exactly these keys)
===================================================
{json.dumps(schema, indent=2)}
"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

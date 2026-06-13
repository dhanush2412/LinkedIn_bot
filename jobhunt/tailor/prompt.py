from __future__ import annotations

import json
from jobhunt.models import Job, CandidateProfile


SYSTEM_PROMPT = """You are an expert technical resume writer. You produce sharply \
TAILORED application materials for ONE candidate applying to ONE specific job. \
"Tailored" means the materials visibly speak to THIS job — not a generic profile.

HARD CONSTRAINTS (honesty — never violate):
1. NEVER invent skills, employers, projects, certifications, tools, or years of \
experience that are not explicitly in the candidate's resume or biodata.
2. The Skills section must ONLY contain skills/tools that appear in the candidate's \
resume or biodata. NEVER add a skill just because the job mentions it. If the job \
wants React/Node/AWS/etc. and it is NOT in the candidate's materials, leave it out.
3. If a form question cannot be answered honestly from the available info, set its \
answer to the literal string "NEEDS_HUMAN".
4. Never overstate seniority. If the candidate is a new grad / has ~1 year of \
experience, do not imply senior-level experience.

TAILORING RULES (make it genuinely specific to this job):
5. SUMMARY: 2-3 sentences written FOR THIS ROLE. It MUST start with what the \
candidate IS plus their most job-relevant real skills/experience — NEVER start with \
personality adjectives. \
BANNED openings (and any paraphrase of them): "detail-oriented", "detail-driven", \
"communicative", "innovative", "passionate", "motivated", "results-driven", \
"As a ... software engineer, I bring a strong foundation/background". \
GOOD pattern: "<Role/level> with <real skill A>, <real skill B>, and <real \
project/experience> relevant to <this job's core need>. <One sentence on the most \
relevant real achievement or focus for this role.>" \
Example for a backend job: "Backend-focused software engineer with production \
Python, FastAPI, and REST API experience, plus shipped AI/automation projects. \
Built an LLM automation suite that cut manual effort 70% and a FAISS-based RAG \
system at 88% retrieval accuracy." Mirror that concreteness.
6. SKILLS: list ONLY real skills, but ORDER them so the ones most relevant to this \
job come first. Drop clearly-irrelevant ones if the list is long.
7. EXPERIENCE/PROJECTS: keep the strongest 2-4 real bullets per item, and REWORD \
them to foreground the aspects this job cares about (mirror the JD's vocabulary \
where the candidate genuinely did that work). Lead with the most job-relevant \
role/project. Keep all real metrics (numbers, %).
8. Match the candidate's voice from their biodata.
9. If the candidate is a weak fit (few overlapping skills), still tailor honestly to \
the genuine overlap — do NOT fabricate to bridge the gap.
10. Return ONLY valid JSON matching the requested schema. No prose around the JSON."""


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
        "cover_letter": "string — 150-220 words to the hiring team. Open by connecting the candidate to THIS specific role/company and its top 1-2 needs, cite 1-2 concrete real achievements (with metrics) that match, and close with genuine interest. No salutation cliches, no markdown headers, no generic filler adjectives.",
        "tailored_resume_md": "string — full resume body in markdown, sections in this order: Summary, Skills, Experience, Projects, Education. Follow the TAILORING RULES: a job-specific Summary, skills ordered by relevance to THIS job, and experience/project bullets REWORDED to foreground what this job cares about (keep real metrics). Use '## ' for section headers and '### ' for each role/project title with bullet lists under them. NO contact header (we render that separately).",
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

CANDIDATE RESUME (parsed summary)
==================================
{json.dumps(resume_summary, indent=2)}

CANDIDATE RESUME (full text — use the real experience bullets, projects,
achievements, and metrics from here; keep the strongest, most relevant ones)
============================================================================
{profile.raw_resume_text or "(not available)"}

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

# Job Application Assistant

Local, human-in-the-loop helper that scrapes Instahyre + SimplyHired job listings,
generates AI-tailored resumes and cover letters with Groq, and assists LinkedIn
Easy Apply via a Chrome extension.

See [design spec](docs/superpowers/specs/2026-05-23-job-application-assistant-design.md).

## Setup

1. `python -m venv .venv && .venv\Scripts\activate` (Windows PowerShell)
2. `pip install -r requirements.txt`
3. `playwright install chromium`
4. `copy .env.example .env` and add your Groq API key.
5. `mkdir profile` then put your `resume.pdf` and `biodata.md` inside it.

## Usage

```
python -m jobhunt profile refresh
python -m jobhunt scrape simplyhired --keywords "python backend" --location remote
python -m jobhunt tailor <job_id_or_url>
python -m jobhunt serve
```

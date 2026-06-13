# Job Application Assistant

Local, human-in-the-loop helper that scrapes Instahyre + SimplyHired job listings,
generates AI-tailored resumes and cover letters with Groq, and assists LinkedIn
Easy Apply via a Chrome extension.

See [design spec](docs/superpowers/specs/2026-05-23-job-application-assistant-design.md).

## Setup

1. `python -m venv .venv && .venv\Scripts\activate` (Windows PowerShell)
2. `pip install -r requirements.txt`
3. `playwright install chromium`
4. Install Google Chrome (the desktop browser) if it isn't already. Scrapers
   drive your real Chrome via Playwright's `channel="chrome"` — this is required
   to get past Cloudflare/anti-bot protection on SimplyHired and Instahyre.
5. `copy .env.example .env` and add your Groq API key.
6. `mkdir profile` then put your `resume.pdf` and `biodata.md` inside it.

> **Note on scraping:** Scrapers run **headed** (a visible Chrome window opens)
> by default. Headless scraping is blocked by Cloudflare on these sites. Don't be
> surprised when a browser window pops up during `scrape` — that's expected.

## Usage

```
python -m jobhunt profile refresh
python -m jobhunt scrape simplyhired --keywords "python backend" --location remote
python -m jobhunt tailor <job_id_or_url>
python -m jobhunt serve
```

`scrape` opens a real Chrome window (required to bypass anti-bot). After running,
open `data/jobs.csv`, pick a `job_id`, and run `tailor` on it. Tailored materials
(resume PDF, cover letter, form answers) land in `output/<job_id>/`.

## LinkedIn Easy Apply extension

The extension assists LinkedIn Easy Apply: it fills standard fields and pastes
AI-tailored answers (highlighted yellow). **It never clicks Submit — you always
review and submit yourself.**

1. Start the local server: `python -m jobhunt serve` (keep it running).
2. Chrome → `chrome://extensions` → enable **Developer mode** → **Load unpacked**
   → select the `extension/` folder.
3. Click the JobHunt toolbar icon; the popup should say "Local server: OK".
4. Open a LinkedIn job, click **Easy Apply**, then click the floating
   **🎯 Tailor & Fill** button. Review the side panel + highlighted fields, then
   submit yourself.

## Instahyre note

Instahyre sits behind a login wall, so its scraper selectors ship as defensive
best-guesses validated only against synthetic fixtures. Before relying on it,
log in once and capture real fixtures:

```
python scripts/capture_instahyre_fixture.py
```

then adjust the selectors in `jobhunt/scrapers/instahyre.py` to match the real DOM.

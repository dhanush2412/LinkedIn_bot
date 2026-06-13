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

`scrape simplyhired` / `scrape instahyre` open a real Chrome window (required to
bypass anti-bot). After running, open `data/jobs.csv`, pick a `job_id`, and run
`tailor` on it. Tailored materials (resume PDF, cover letter, form answers) land
in `output/<job_id>/`.

### LinkedIn job discovery (via Apify — no account risk)

`scrape linkedin` pulls jobs from a LinkedIn search **without using your LinkedIn
account or browser** — it calls Apify's hosted LinkedIn scraper, so your account
is never at ban risk. It needs a free `APIFY_TOKEN` in `.env` (sign up at
apify.com → Settings → API tokens; free tier ≈ 5,000 jobs/month).

Two ways to use it:

```
# A) Location cascade (recommended): searches cities in priority order, filling
#    from the most-preferred city first, falling back to the next until full.
python -m jobhunt scrape linkedin --keywords "python developer" --max 20
#    Default cities: Bangalore, Mangalore, Udupi, Hyderabad. Override with:
python -m jobhunt scrape linkedin --keywords "ai engineer" --locations "Bangalore,Pune,Remote" --max 20

# B) Exact search URL: copy a LinkedIn jobs-search URL from your browser.
python -m jobhunt scrape linkedin --url "<LinkedIn jobs-search URL>" --max 25
```

Add `--max-applicants 30` to keep only low-competition jobs (LinkedIn exposes the
applicant count for some listings; jobs with unknown counts are kept). Jobs land in
`data/jobs.csv` (and the Google Sheet, if configured) and tailor like any source.

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

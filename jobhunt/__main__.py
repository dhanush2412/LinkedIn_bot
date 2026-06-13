from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from jobhunt.profile_loader import load_profile
from jobhunt.csv_store import JobsCsv
from jobhunt.tailor.orchestrator import tailor


def _profile_dir() -> Path:
    return Path(os.environ.get("JOBHUNT_PROFILE_DIR", "./profile"))


def _data_dir() -> Path:
    return Path(os.environ.get("JOBHUNT_DATA_DIR", "./data"))


def _output_dir() -> Path:
    return Path(os.environ.get("JOBHUNT_OUTPUT_DIR", "./output"))


def cmd_profile_refresh(_args):
    profile_dir = _profile_dir()
    cache = profile_dir / "parsed.json"
    if cache.exists():
        cache.unlink()
    p = load_profile(profile_dir)
    print(f"Loaded profile for {p.name} ({len(p.skills)} skills, biodata {len(p.biodata_text)} chars)")


def cmd_scrape(args):
    if args.platform == "simplyhired" and not args.keywords:
        print("simplyhired requires --keywords (e.g. --keywords \"python backend\")", file=sys.stderr)
        sys.exit(2)
    if args.platform == "linkedin" and not args.url:
        print("linkedin requires --url (a LinkedIn jobs-search URL copied from your browser)",
              file=sys.stderr)
        sys.exit(2)
    csv = JobsCsv(_data_dir() / "jobs.csv")
    if args.platform == "simplyhired":
        from jobhunt.scrapers.simplyhired import SimplyHiredScraper
        with SimplyHiredScraper(headless=args.headless) as s:
            jobs = list(s.scrape(args.keywords, args.location, max_jobs=args.max))
    elif args.platform == "instahyre":
        from jobhunt.scrapers.instahyre import InstahyreScraper
        with InstahyreScraper(headless=args.headless) as s:
            jobs = list(s.scrape(args.keywords, max_jobs=args.max))
    elif args.platform == "linkedin":
        from jobhunt.scrapers.linkedin_apify import scrape_linkedin
        print("Scraping LinkedIn via Apify (this can take 1-3 minutes)...")
        jobs = scrape_linkedin(args.url, max_jobs=args.max, max_applicants=args.max_applicants)
    else:
        print(f"Unknown platform: {args.platform}", file=sys.stderr)
        sys.exit(2)
    added = csv.append(jobs)
    print(f"Scraped {len(jobs)} jobs; {added} new (after dedup) appended to {csv.path}")

    from jobhunt.sheets_store import maybe_store
    sheet = maybe_store()
    if sheet is not None:
        pushed = sheet.append(jobs)
        print(f"Pushed {pushed} new job(s) to Google Sheets.")


def cmd_tailor(args):
    csv = JobsCsv(_data_dir() / "jobs.csv")
    job = csv.find(args.job)
    if job is None:
        print(f"Job not found in CSV: {args.job}", file=sys.stderr)
        sys.exit(1)
    profile = load_profile(_profile_dir())
    out = tailor(job, profile, form_questions=[], output_root=_output_dir(), force=args.force)
    csv.mark_tailored(job.job_id)
    from jobhunt.sheets_store import maybe_store
    sheet = maybe_store()
    if sheet is not None:
        sheet.mark_tailored(job.job_id)
    print(f"Tailored materials in: {Path(out.resume_pdf_path).parent}")


def cmd_sync_sheet(_args):
    from jobhunt.sheets_store import maybe_store, is_configured
    if not is_configured():
        print("Google Sheets not configured. Set GOOGLE_SERVICE_ACCOUNT_FILE and "
              "JOBHUNT_SHEET_ID in .env.", file=sys.stderr)
        sys.exit(2)
    sheet = maybe_store()
    if sheet is None:
        sys.exit(1)
    jobs = JobsCsv(_data_dir() / "jobs.csv").read_all()
    if _args.rebuild:
        n = sheet.rebuild(jobs)
        print(f"Rebuilt Google Sheet from scratch with {n} job(s). "
              "(NOTE: the 'applied' column was reset.)")
    else:
        pushed = sheet.append(jobs)
        print(f"Synced {len(jobs)} CSV jobs to Google Sheets; {pushed} new row(s) added.")


def cmd_serve(_args):
    import uvicorn
    host = os.environ.get("JOBHUNT_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("JOBHUNT_SERVER_PORT", "7860"))
    uvicorn.run("jobhunt.server:app", host=host, port=port, log_level="info")


def main(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(prog="python -m jobhunt")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prof = sub.add_parser("profile")
    p_prof_sub = p_prof.add_subparsers(dest="profile_cmd", required=True)
    p_prof_refresh = p_prof_sub.add_parser("refresh")
    p_prof_refresh.set_defaults(func=cmd_profile_refresh)

    p_scrape = sub.add_parser("scrape")
    p_scrape.add_argument("platform", choices=["simplyhired", "instahyre", "linkedin"])
    p_scrape.add_argument("--keywords", default="",
                          help="filter keywords; required for simplyhired, optional for instahyre")
    p_scrape.add_argument("--url", default="",
                          help="LinkedIn jobs-search URL (required for linkedin platform)")
    p_scrape.add_argument("--location", default="remote")
    p_scrape.add_argument("--max", type=int, default=30)
    p_scrape.add_argument("--max-applicants", type=int, default=None, dest="max_applicants",
                          help="LinkedIn only: keep only jobs with <= this many applicants "
                               "(less competition). Jobs with unknown counts are kept.")
    p_scrape.add_argument("--headless", action="store_true",
                          help="run browser headless (NOT recommended — Cloudflare blocks headless)")
    p_scrape.set_defaults(func=cmd_scrape)

    p_tailor = sub.add_parser("tailor")
    p_tailor.add_argument("job", help="job_id or URL")
    p_tailor.add_argument("--force", action="store_true")
    p_tailor.set_defaults(func=cmd_tailor)

    p_serve = sub.add_parser("serve")
    p_serve.set_defaults(func=cmd_serve)

    p_sync = sub.add_parser("sync-sheet", help="push all CSV jobs to the configured Google Sheet")
    p_sync.add_argument("--rebuild", action="store_true",
                        help="wipe and rewrite the whole sheet (fixes column misalignment; "
                             "resets the 'applied' column)")
    p_sync.set_defaults(func=cmd_sync_sheet)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

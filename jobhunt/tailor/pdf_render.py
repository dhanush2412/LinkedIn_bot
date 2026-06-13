from __future__ import annotations

from pathlib import Path
import markdown as md_lib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from jobhunt.models import CandidateProfile


_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_resume_html(profile: CandidateProfile, body_md: str) -> str:
    """Render the resume markdown body into a full HTML document string."""
    body_html = md_lib.markdown(body_md, extensions=["extra", "sane_lists"])
    tmpl = _env.get_template("resume.html")
    return tmpl.render(
        name=profile.name,
        email=profile.email,
        phone=profile.phone,
        location=profile.location,
        links=profile.links,
        body_html=body_html,
    )


def render_resume_pdf(profile: CandidateProfile, body_md: str, out_path: str | Path) -> Path:
    """Render the tailored resume to a PDF.

    Uses headless Chromium (via Playwright) to print HTML -> PDF. This avoids
    WeasyPrint's GTK/Pango native-library dependency, which is painful on Windows,
    and gives full Chrome-grade CSS rendering. Playwright is already a project
    dependency (used by the scrapers).
    """
    html_str = render_resume_html(profile, body_md)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html_str, wait_until="load")
            page.pdf(
                path=str(out_path),
                format="Letter",
                print_background=True,
                margin={"top": "0.6in", "bottom": "0.6in", "left": "0.7in", "right": "0.7in"},
            )
        finally:
            browser.close()
    return out_path

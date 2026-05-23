"""Generates a deterministic sample resume PDF for testing the profile loader.

Run once: python scripts/make_test_resume.py
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

OUT = Path("tests/fixtures/resumes/sample_resume.pdf")
OUT.parent.mkdir(parents=True, exist_ok=True)

doc = SimpleDocTemplate(str(OUT), pagesize=letter)
styles = getSampleStyleSheet()
story = [
    Paragraph("Jane Doe", styles["Title"]),
    Paragraph("jane.doe@example.com | +91 9876543210 | Bengaluru, IN", styles["Normal"]),
    Paragraph("github.com/janedoe | linkedin.com/in/janedoe", styles["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>SUMMARY</b>", styles["Heading2"]),
    Paragraph("Backend engineer with 4 years experience in Python and FastAPI.", styles["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>SKILLS</b>", styles["Heading2"]),
    Paragraph("Python, FastAPI, PostgreSQL, Docker, AWS", styles["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>EXPERIENCE</b>", styles["Heading2"]),
    Paragraph("<b>Senior Engineer</b> — Acme Corp (2023 - Present)", styles["Normal"]),
    Paragraph("- Built REST API serving 1M requests/day.", styles["Normal"]),
    Paragraph("- Migrated legacy monolith to microservices.", styles["Normal"]),
    Spacer(1, 8),
    Paragraph("<b>Software Engineer</b> — Startup Inc (2021 - 2023)", styles["Normal"]),
    Paragraph("- Owned billing service.", styles["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>EDUCATION</b>", styles["Heading2"]),
    Paragraph("B.Tech, Computer Science — IIT Madras (2017 - 2021)", styles["Normal"]),
]
doc.build(story)
print(f"Wrote {OUT}")

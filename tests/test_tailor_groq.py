import json
import pytest
from unittest.mock import MagicMock
from jobhunt.tailor.groq_client import call_groq_for_tailoring, parse_or_repair_json


def test_parse_or_repair_returns_dict_on_clean_json():
    raw = '{"cover_letter": "x", "tailored_resume_md": "# r", "form_answers": {}}'
    out = parse_or_repair_json(raw)
    assert out["cover_letter"] == "x"


def test_parse_or_repair_strips_code_fences():
    raw = '```json\n{"cover_letter": "x", "tailored_resume_md": "y", "form_answers": {}}\n```'
    out = parse_or_repair_json(raw)
    assert out["cover_letter"] == "x"


def test_parse_or_repair_extracts_json_from_prose():
    raw = 'Sure! Here is the JSON: {"cover_letter": "x", "tailored_resume_md": "y", "form_answers": {}}'
    out = parse_or_repair_json(raw)
    assert out["cover_letter"] == "x"


def test_parse_or_repair_raises_on_unrepairable():
    with pytest.raises(ValueError):
        parse_or_repair_json("totally not json at all")


def test_call_groq_returns_parsed_dict(mocker):
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content=json.dumps({
        "cover_letter": "Dear team...",
        "tailored_resume_md": "# Resume",
        "form_answers": {"q": "a"},
    })))]
    fake_client.chat.completions.create.return_value = fake_response
    mocker.patch("jobhunt.tailor.groq_client._get_client", return_value=fake_client)

    out = call_groq_for_tailoring([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}])
    assert out["cover_letter"] == "Dear team..."
    assert out["form_answers"]["q"] == "a"


def test_call_groq_falls_back_on_primary_failure(mocker):
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content=json.dumps({
        "cover_letter": "Fallback",
        "tailored_resume_md": "# r",
        "form_answers": {},
    })))]
    call_count = {"n": 0}
    def create_side_effect(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("rate limit")
        return fake_response
    fake_client.chat.completions.create.side_effect = create_side_effect
    mocker.patch("jobhunt.tailor.groq_client._get_client", return_value=fake_client)

    out = call_groq_for_tailoring([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}])
    assert out["cover_letter"] == "Fallback"
    assert call_count["n"] == 2

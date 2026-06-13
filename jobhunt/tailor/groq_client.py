from __future__ import annotations

import json
import os
import re
from groq import Groq


_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment")
        _client = Groq(api_key=api_key)
    return _client


def parse_or_repair_json(raw: str) -> dict:
    """Robust JSON parsing: strip code fences, extract first JSON object."""
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON from LLM output: {raw[:200]!r}")


def _call_once(client: Groq, model: str, messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def call_groq_for_tailoring(messages: list[dict]) -> dict:
    client = _get_client()
    primary = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    fallback = os.environ.get("GROQ_MODEL_FALLBACK", "llama-3.1-8b-instant")

    try:
        raw = _call_once(client, primary, messages)
    except Exception as e:
        print(f"[groq] primary model {primary} failed ({e}); falling back to {fallback}")
        raw = _call_once(client, fallback, messages)

    try:
        return parse_or_repair_json(raw)
    except ValueError:
        repair_messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "Your previous response was not valid JSON. Reply with ONLY the valid JSON object, nothing else."},
        ]
        raw2 = _call_once(client, primary, repair_messages)
        return parse_or_repair_json(raw2)

"""
Layer 3.5 -- pure rendering, zero decision-making. This module never
chooses a route, an officer count, or a risk threshold. It only takes
the already-computed, deterministic playbook JSON from simulation.py /
routing.py / judging.py and turns it into English. That separation is
the entire point of the "Honest AI" pitch.
"""
import os
import json
import re
import time
from groq import Groq


def _strip_markdown(text: str) -> str:
    """Belt-and-suspenders cleanup -- the prompt asks for plain text, but
    LLMs don't always comply. Strip common markdown so it never reaches
    the frontend with literal asterisks or hash marks."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    return text.strip()


load_dotenv_done = False


def _ensure_env_loaded():
    global load_dotenv_done
    if not load_dotenv_done:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv_done = True


_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _ensure_env_loaded()
        api_key = os.environ.get("GROQ_API")
        if not api_key:
            raise RuntimeError(
                "GROQ_API not set. Add GROQ_API=your_key_here to your .env file."
            )
        _client = Groq(api_key=api_key)
    return _client


def _generate_with_retry(prompt: str, max_retries: int = 2) -> str:
    """Try llama-3.3-70b-versatile first; if rate-limited or unavailable,
    fall back to llama-3.1-8b-instant before giving up."""
    client = get_client()
    models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    last_error = None

    for model in models_to_try:
        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0.3,  # low temp = more deterministic, better for briefings
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

    raise RuntimeError(f"Groq unavailable after retries on both models: {last_error}")


def render_playbook_text(playbook: dict) -> str:
    """Turn the full /playbook JSON into a plain-English briefing for a watch commander."""
    prompt = f"""You are writing a short incident briefing for a Bengaluru Traffic Police
watch commander, based on a traffic simulation system's output. Be direct and
operational -- this is read in a control room, not a press release. Cover:
what's blocked, what the network impact is, the diversion route and its ETA,
how many officers are needed and from where, and whether the Judging Panel
approved it or flagged a review. Do not invent any numbers not present in
the JSON below. Plain text only -- no markdown, no asterisks, no headers.
Keep it under 150 words.

Playbook JSON:
{json.dumps(playbook, indent=2)}
"""
    return _strip_markdown(_generate_with_retry(prompt))


def generate_public_advisory(playbook: dict) -> str:
    """Draft-only public advisory text, hard-capped at 160 characters (SMS length)."""
    prompt = f"""Write a single public traffic advisory SMS for Bengaluru commuters,
based on this incident JSON. Plain language, no jargon, no corridor codes --
use the actual road names. State what's blocked and what to do instead.
HARD LIMIT: 160 characters total, no exceptions. Output ONLY the SMS text,
nothing else.

Incident JSON:
{json.dumps(playbook, indent=2)}
"""
    text = _strip_markdown(_generate_with_retry(prompt))
    if len(text) > 160:
        text = text[:157].rsplit(" ", 1)[0] + "..."
    return text
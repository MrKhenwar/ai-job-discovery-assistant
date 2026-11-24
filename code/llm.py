"""Thin wrapper around Gemini. The API key is read from the environment, never stored in files."""
import os
import time

from google import genai
from google.genai import errors, types

MODEL = os.environ.get("MODEL_NAME", "gemini-3.5-flash")
MIN_INTERVAL = float(os.environ.get("LLM_MIN_INTERVAL_SEC", "13"))  # free tier: 5 req/min
_client = None
_last_call = 0.0


def _get_client():
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Set GEMINI_API_KEY in your environment (see .env.example).")
        _client = genai.Client(api_key=key, http_options={"api_version": "v1beta"})
    return _client


def _throttle():
    global _last_call
    wait = MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def call_llm(system: str, user: str, temperature=None) -> str:
    """Send one prompt and return the raw text of the reply."""
    cfg = {}
    if system and system.strip().lower() != "none":
        cfg["system_instruction"] = system
    if temperature is not None:
        cfg["temperature"] = temperature
    for attempt in range(5):
        _throttle()
        try:
            resp = _get_client().models.generate_content(
                model=MODEL,
                contents=user,
                config=types.GenerateContentConfig(**cfg),
            )
            return resp.text or ""
        except errors.ClientError as e:
            if e.code == 429 and attempt < 4:
                time.sleep(15)
                continue
            raise
        except errors.ServerError:
            if attempt < 4:
                time.sleep(10)
                continue
            raise

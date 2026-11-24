"""Thin wrapper around the LLM provider. API keys are read from the environment, never stored in files.

Provider is selected with LLM_PROVIDER=gemini (default) or groq. The product targets Gemini per the
assignment brief; Groq (OpenAI-compatible, free, fast) is supported as a drop-in alternative because
Gemini's free-tier request quota was too restrictive to run the full test suite during development.
"""
import os
import time

import requests
from google import genai
from google.genai import errors, types

PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()
MODEL = os.environ.get("MODEL_NAME", "gemini-3.5-flash-lite" if PROVIDER == "gemini" else "openai/gpt-oss-120b")
MIN_INTERVAL = float(os.environ.get("LLM_MIN_INTERVAL_SEC", "13" if PROVIDER == "gemini" else "0"))
_client = None
_last_call = 0.0


def _get_client():
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Set GEMINI_API_KEY in your environment (see .env.example).")
        _client = genai.Client(api_key=key, http_options={"api_version": "v1beta", "timeout": 45_000})
    return _client


def _throttle():
    global _last_call
    wait = MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def _call_gemini(system, user, temperature):
    cfg = {}
    if system and system.strip().lower() != "none":
        cfg["system_instruction"] = system
    if temperature is not None:
        cfg["temperature"] = temperature
    resp = _get_client().models.generate_content(
        model=MODEL,
        contents=user,
        config=types.GenerateContentConfig(**cfg),
    )
    return resp.text or ""


def _call_groq(system, user, temperature):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("Set GROQ_API_KEY in your environment to use LLM_PROVIDER=groq.")
    messages = []
    if system and system.strip().lower() != "none":
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    payload = {"model": MODEL, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json=payload,
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"] or ""


def call_llm(system: str, user: str, temperature=None) -> str:
    """Send one prompt and return the raw text of the reply."""
    attempts = 8
    for attempt in range(attempts):
        _throttle()
        try:
            if PROVIDER == "groq":
                return _call_groq(system, user, temperature)
            return _call_gemini(system, user, temperature)
        except errors.ClientError as e:
            if e.code == 429 and attempt < attempts - 1:
                time.sleep(20)
                continue
            raise
        except errors.ServerError:
            if attempt < attempts - 1:
                time.sleep(15 * (attempt + 1))
                continue
            raise
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429 and attempt < attempts - 1:
                time.sleep(20)
                continue
            raise
        except Exception:
            # Network hang/timeout from the underlying HTTP client (not a typed API error).
            if attempt < attempts - 1:
                time.sleep(10)
                continue
            raise

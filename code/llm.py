"""Thin wrapper around the LLM provider. API keys are read from the environment, never stored in files.

Provider is selected with LLM_PROVIDER=gemini (default), groq, openrouter, or auto. The deployed product
targets Gemini per the assignment brief. "auto" tries a chain of providers in order and fails over to the
next one on error (rate limit, quota, server error) instead of retrying the same dead provider for a long
time -- useful for bulk test runs, where Gemini/Groq/OpenRouter free tiers each run out at different times.
"""
import os
import time

import requests
from google import genai
from google.genai import errors, types

PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()

# name -> (default model, min seconds between calls on this provider)
PROVIDERS = {
    "gemini": ("gemini-3.5-flash-lite", 13.0),
    "groq": ("openai/gpt-oss-20b", 0.0),
    "openrouter": ("nvidia/nemotron-3-ultra-550b-a55b:free", 0.0),
}
# Order to try in LLM_PROVIDER=auto mode.
AUTO_CHAIN = ["groq", "openrouter", "gemini"]

MODEL = os.environ.get("MODEL_NAME")  # None = use each provider's default below
_client = None
_last_call = {}  # per-provider throttle state, so auto mode doesn't cross-throttle


def _get_client():
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Set GEMINI_API_KEY in your environment (see .env.example).")
        _client = genai.Client(api_key=key, http_options={"api_version": "v1beta", "timeout": 45_000})
    return _client


def _throttle(provider):
    _, min_interval = PROVIDERS[provider]
    last = _last_call.get(provider, 0.0)
    wait = min_interval - (time.monotonic() - last)
    if wait > 0:
        time.sleep(wait)
    _last_call[provider] = time.monotonic()


def _call_gemini(system, user, temperature, model):
    cfg = {}
    if system and system.strip().lower() != "none":
        cfg["system_instruction"] = system
    if temperature is not None:
        cfg["temperature"] = temperature
    resp = _get_client().models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(**cfg),
    )
    return resp.text or ""


_OPENAI_COMPAT_URLS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
}


def _call_openai_compat(provider, system, user, temperature, model):
    url, key_env = _OPENAI_COMPAT_URLS[provider]
    key = os.environ.get(key_env)
    if not key:
        raise RuntimeError(f"Set {key_env} in your environment to use LLM_PROVIDER={provider}.")
    messages = []
    if system and system.strip().lower() != "none":
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    payload = {"model": model, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
    resp = requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=45)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"] or ""


def _call_one(provider, system, user, temperature):
    model = MODEL or PROVIDERS[provider][0]
    if provider == "gemini":
        return _call_gemini(system, user, temperature, model)
    return _call_openai_compat(provider, system, user, temperature, model)


def _call_with_retry(provider, system, user, temperature, attempts):
    """Call one provider, retrying on transient errors. Raises on final failure."""
    for attempt in range(attempts):
        _throttle(provider)
        try:
            return _call_one(provider, system, user, temperature)
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
                time.sleep(10)
                continue
            raise
        except Exception:
            if attempt < attempts - 1:
                time.sleep(10)
                continue
            raise


def call_llm(system: str, user: str, temperature=None) -> str:
    """Send one prompt and return the raw text of the reply.

    LLM_PROVIDER=auto tries each provider in AUTO_CHAIN with a short retry budget and
    moves to the next one on failure; a pinned provider (gemini/groq/openrouter) gets a
    longer retry budget on itself only.
    """
    if PROVIDER == "auto":
        last_exc = None
        for provider in AUTO_CHAIN:
            try:
                return _call_with_retry(provider, system, user, temperature, attempts=2)
            except Exception as e:
                last_exc = e
                continue
        raise last_exc
    return _call_with_retry(PROVIDER, system, user, temperature, attempts=8)

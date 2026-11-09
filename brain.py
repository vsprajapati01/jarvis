#!/usr/bin/env python3
"""
Jarvis brain - multi-provider, free-first.

Providers, in order. All have a free tier, no credit card needed
to get a key. Put keys in a local .env file in the jarvis folder
only - never paste them in chat, never push .env to GitHub
(it is already in .gitignore).

1. Gemini (default) - Google AI Studio, https://aistudio.google.com
   GEMINI_API_KEY=...
   Model: gemini-2.5-flash. Best all-round free brain.
2. Groq - https://console.groq.com
   GROQ_API_KEY=...
   Model: llama-3.3-70b-versatile. Fastest - use this when you
   want the quickest reply.
3. Cerebras - https://cloud.cerebras.ai
   CEREBRAS_API_KEY=...
   Model: llama-3.3-70b. Very fast, 1M free tokens/day.
4. OpenRouter free - https://openrouter.ai
   OPENROUTER_API_KEY=...
   Model: set OPENROUTER_MODEL in .env, default is a free
   Llama model. Free models change often, so check the
   OpenRouter free list if one stops working.

How it works:
- Local commands (time, weather, open chrome, timer, find
  companies, create word/pdf, research...) still run locally
  first - they are faster and free.
- Anything Jarvis does not recognise as a local command is
  sent to the brain as normal conversation. You do NOT need
  a specific command. Just talk: "hey jarvis, how are you?",
  "explain machine learning simply", "what should I do today?"
  Jarvis remembers the last few turns, so follow-ups work:
  "tell me more", "make it shorter", "give an example".
- Switching brains, by voice or text:
    switch brain to groq
    switch brain to gemini
    switch brain to cerebras
    switch brain to openrouter
    list brains
    brain status
  The choice is saved in config.json, so it sticks after a restart.
- If the selected brain is down, rate-limited, or has no key,
  Jarvis automatically falls back to the next brain that has
  a key, and tells you which one answered.
"""
import json
import os
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

SYSTEM_PROMPT = (
    "You are Jarvis, a helpful voice assistant on Vishal's Windows PC. "
    "Talk like a helpful friend, in plain, short, natural language. "
    "Keep answers under 120 words unless he asks for detail. "
    "He is a 24-year-old MS Computer Science student in Gainesville, FL, "
    "applying for data / ML jobs, learning guitar and Power BI. "
    "Never invent facts about his applications, skills or health. "
    "If you do not know something, say so. "
    "If he just wants to chat, chat back - do not force him into a command."
)

# Last few exchanges, kept in memory only, so follow-ups work.
# Cleared when Jarvis restarts. Nothing is written to disk.
_HISTORY = []
MAX_HISTORY_TURNS = 6

PROVIDERS = {
    "gemini": {
        "label": "Gemini (Google)",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",
    },
    "groq": {
        "label": "Groq (fast)",
        "key_env": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
        "url": "https://api.groq.com/openai/v1/chat/completions",
    },
    "cerebras": {
        "label": "Cerebras (fast)",
        "key_env": "CEREBRAS_API_KEY",
        "model": "llama-3.3-70b",
        "url": "https://api.cerebras.ai/v1/chat/completions",
    },
    "openrouter": {
        "label": "OpenRouter (free models)",
        "key_env": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "url": "https://openrouter.ai/api/v1/chat/completions",
    },
}

# Order used for automatic fallback.
FALLBACK_ORDER = ["gemini", "groq", "cerebras", "openrouter"]


def _load_env_file():
    env = {}
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
    return env


_ENV = _load_env_file()


def _get_key(name):
    return os.environ.get(name, "").strip() or _ENV.get(name, "").strip()


def _load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def get_provider():
    cfg = _load_config()
    p = str(cfg.get("brain_provider", "gemini")).lower().strip()
    return p if p in PROVIDERS else "gemini"


def set_provider(name):
    name = name.lower().strip()
    if name not in PROVIDERS:
        return False
    cfg = _load_config()
    cfg["brain_provider"] = name
    _save_config(cfg)
    return True


def list_providers():
    """Return [(name, label, has_key, is_selected), ...]."""
    selected = get_provider()
    out = []
    for name in FALLBACK_ORDER:
        info = PROVIDERS[name]
        out.append((name, info["label"], bool(_get_key(info["key_env"])), name == selected))
    return out


def _post_json(url, body, headers):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers=headers, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _openai_chat(provider, prompt):
    """Call an OpenAI-compatible chat API. Returns (text, error)."""
    info = PROVIDERS[provider]
    key = _get_key(info["key_env"])
    if not key:
        return "", f"no {provider} key"
    model = info["model"]
    if provider == "openrouter":
        model = _ENV.get("OPENROUTER_MODEL", os.environ.get("OPENROUTER_MODEL", "")).strip() or model
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in _HISTORY[-MAX_HISTORY_TURNS:]:
        messages.append({"role": "user", "content": turn[0]})
        messages.append({"role": "assistant", "content": turn[1]})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 600,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/vsprajapati01/jarvis"
        headers["X-Title"] = "Jarvis"
    try:
        data = _post_json(info["url"], body, headers)
        choices = data.get("choices", [])
        if not choices:
            return "", "no answer from " + provider
        text = choices[0].get("message", {}).get("content", "").strip()
        return text, None
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
            msg = detail.get("error", {}).get("message", "") or str(detail)[:200]
        except Exception:
            msg = ""
        if e.code == 429:
            return "", f"{provider} limit reached, try again in a minute. {msg}"
        if e.code in (400, 401, 403):
            return "", f"{provider} key/model problem ({e.code}). Check the key in .env. {msg}"
        return "", f"{provider} error {e.code}. {msg}"
    except Exception as e:
        return "", f"could not reach {provider}: {e}"


def _ask_gemini(prompt):
    key = _get_key("GEMINI_API_KEY")
    if not key:
        return "", "no gemini key"
    messages = []
    for turn in _HISTORY[-MAX_HISTORY_TURNS:]:
        messages.append({"role": "user", "parts": [{"text": turn[0]}]})
        messages.append({"role": "model", "parts": [{"text": turn[1]}]})
    messages.append({"role": "user", "parts": [{"text": prompt}]})
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": messages,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600},
    }
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + key
    try:
        data = _post_json(url, body, {"Content-Type": "application/json"})
        candidates = data.get("candidates", [])
        if not candidates:
            return "", "no answer from gemini"
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        return text, None
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
            msg = detail.get("error", {}).get("message", "")
        except Exception:
            msg = ""
        if e.code == 429:
            return "", "Gemini free limit reached for this minute. Wait a minute and ask again."
        if e.code in (400, 403):
            return "", f"Gemini key problem ({e.code}). Check the key in .env is copied exactly. {msg}"
        return "", f"Gemini error {e.code}. {msg}"
    except Exception as e:
        return "", f"Could not reach Gemini right now: {e}"


def ask_brain(prompt):
    """Ask the selected brain, falling back to any other brain with a key.
    Returns (answer_text, error_message_or_None).
    The answer is prefixed with which brain answered, only when it
    was a fallback, so you know when a switch happened.
    """
    selected = get_provider()
    order = [selected] + [p for p in FALLBACK_ORDER if p != selected]
    errors = []
    for provider in order:
        if provider == "gemini":
            text, err = _ask_gemini(prompt)
        else:
            text, err = _openai_chat(provider, prompt)
        if err is None and text:
            _HISTORY.append((prompt, text))
            if len(_HISTORY) > MAX_HISTORY_TURNS:
                _HISTORY.pop(0)
            if provider != selected:
                text = f"[{PROVIDERS[provider]['label']} answered, {selected} was unavailable] " + text
            return text, None
        errors.append(f"{provider}: {err}")
    # No brain worked.
    configured = [p for p in FALLBACK_ORDER if _get_key(PROVIDERS[p]["key_env"])]
    if not configured:
        return "", (
            "No brain is set up yet. Add a free key to the .env file in the "
            "jarvis folder - GEMINI_API_KEY from aistudio.google.com is the "
            "easiest, or GROQ_API_KEY / CEREBRAS_API_KEY / OPENROUTER_API_KEY. "
            "Local commands still work without a brain."
        )
    return "", "All brains failed. " + "; ".join(errors)


# Backwards compatibility: old code called ask_gemini().
def ask_gemini(prompt):
    return ask_brain(prompt)


def clear_history():
    _HISTORY.clear()

#!/usr/bin/env python3
"""
Jarvis brain - Gemini (free API) as the thinking part.

Setup, on your PC only:
1. Go to https://aistudio.google.com, sign in with your Google account.
2. Get API key -> Create API key -> copy it.
3. In your jarvis folder, create a file called .env with exactly one line:
       GEMINI_API_KEY=your-key-here
   Do NOT paste the key in chat, and do NOT push .env to GitHub.
   It is already in .gitignore, so a git pull / push will never
   upload it. You can delete / revoke the key any time in AI Studio.

How it is used:
- Local commands (time, weather, open chrome, find companies, create
  word/pdf, research, timer...) still run locally first - they are
  faster and free.
- Anything Jarvis does not recognise as a local command is sent to
  Gemini as a question, and Gemini's answer is spoken back.
- Gemini is Google's free-tier model (gemini-2.5-flash). No login
  password is ever used or stored - only the API key above.
- If there is no key, Jarvis says so honestly and still works for
  local commands. If Gemini is rate-limited, Jarvis says so and
  you just wait a minute and ask again.
"""
import json
import os
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL = "gemini-2.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM_PROMPT = (
    "You are Jarvis, a helpful voice assistant on Vishal's Windows PC. "
    "Answer in plain, short, natural language, like a helpful friend. "
    "Keep answers under 120 words unless he asks for detail. "
    "He is a 24-year-old MS Computer Science student in Gainesville, FL, "
    "applying for data / ML jobs, learning guitar and Power BI. "
    "Never invent facts about his applications, skills or health. "
    "If you do not know something, say so."
)


def load_api_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def ask_gemini(prompt):
    """Ask Gemini. Returns (answer_text, error_message_or_None)."""
    key = load_api_key()
    if not key:
        return "", (
            "Gemini brain is not set up yet. Create a .env file in the "
            "jarvis folder with GEMINI_API_KEY=your-key from AI Studio, "
            "then ask me again. Local commands still work without it."
        )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600},
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL + "?key=" + key,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        candidates = data.get("candidates", [])
        if not candidates:
            return "", "Gemini gave no answer. Try again in a moment."
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

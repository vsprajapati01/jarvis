# Jarvis — PC Voice Assistant (v1)

A local-first Jarvis-style voice assistant for your PC, in Python.
Wake word, voice commands, timers, reminders, app opening, weather and notes.
No API key needed for v1.

## What v1 does

- Wake word: say **"Jarvis"**, then a command
- Time and date
- Open Chrome, VS Code, Notepad / TextEdit, Calculator
- Web search: `search python tutorials`
- Weather, no key needed: `weather Gainesville`
- Timer: `timer 5 minutes`
- Reminder: `remind me to drink water in 10 minutes`
- Notes: `note buy milk` (saved to `notes.txt`)
- Text mode, no microphone needed: `python jarvis.py --text`

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
python jarvis.py --text
```

Voice mode (needs a microphone):

```bash
python jarvis.py
```

On Linux, PyAudio may need system packages first:
`sudo apt install portaudio19-dev python3-pyaudio`

## Change it

- Name, voice speed and volume: `config.json`
- Add a command: add a branch in `handle_command()` in `jarvis.py`
- Add an app: add it to the `targets` table in `open_app()` in `jarvis.py`

## Floating orb (v5) — no big window, always listening

```bash
python jarvis_overlay.py
```

A small glowing orb sits on the right edge of your screen, always on
top. No clicking needed: just say "jarvis", the orb glows bright and
pulses while it listens, then say your command. Double-click the orb
to open the full window, drag it anywhere, right-click for Show / Quit.
Say "show window" to open the full app by voice.

## Jarvis v8 — talk normally, the agent loop decides (agent.py)

You do NOT need a specific command anymore. Just talk to Jarvis
normally, like ChatGPT or Gemini, and it decides what to do:

- **Chat:** "how are you?", "explain machine learning simply",
  "how do I learn SQL?" — the brain answers, short and plain,
  step by step for how-to questions. It remembers the last 6
  turns, so "tell me more", "make it shorter" and
  "give me an example" work.
- **Research first:** "research the best data analyst
  certifications", "what is the latest on OPT?" — Jarvis
  searches the web first (research.py), then the brain
  summarises what it found in short plain words, and says
  in plain words which sources it used. It does not answer
  from its own knowledge alone when the facts are current.
  With no brain key, you still get the real search results.
- **Do it on your PC:** "open youtube for me",
  "set a timer for 5 minutes", "make a word document about
  my week", "find companies hiring data analysts",
  "give me my morning briefing" — the loop turns plain
  words into the command Jarvis already knows and runs it.
  Local tasks need no key. No new PC actions are invented:
  if Jarvis cannot do it, it says so.
- **Safety, unchanged:** submit / send / pay / delete /
  shut down / restart / sign in / share personal details
  are critical. Jarvis asks you first, through
  permissions.py ("say yes to go ahead, or no to stop").
  Even after a yes, only the safe part runs — opening the
  site in your own Chrome. The submit / send / pay / delete
  click itself stays yours. Jarvis never stores or types
  a password.

## Transparent HUD (v8) — see-through, high-tech

The orb and the full window have an empty, transparent
background, so you see your Windows desktop behind Jarvis.
Only the HUD parts are visible: the glowing orb, thin neon
rings, text and buttons.

- Orb: `python jarvis_overlay.py` — always on top, transparent
  background, rotating neon rings around the orb. Drag the
  orb itself to move it (the see-through space around it is
  click-through on Windows). `--no-listen` shows the orb
  without the microphone, to check the look.
- Full window: `python jarvis_gui.py` — transparent background
  by default on Windows. The "👁 Transparent HUD" button in
  the sidebar switches back to a solid dark background.
- This uses Windows tkinter `-transparentcolor`. On Linux /
  macOS it is not supported, so the same code falls back to
  a solid dark window instead of crashing.

## Brains (v7) — Gemini, Groq, Cerebras, OpenRouter — all free, switchable

Jarvis now has four free brains, and you can switch between them by voice.
You do NOT need a specific command to talk to Jarvis anymore — just talk
normally. Anything that is not a local command (time, weather, open, timer,
find companies...) goes to the brain, and Jarvis remembers the last few
turns, so follow-ups like "tell me more" work.

1. Copy `.env.example` to `.env` in the jarvis folder.
2. Add at least one free key — Gemini is easiest:
   - Gemini: https://aistudio.google.com — Get API key
   - Groq (fastest): https://console.groq.com — API Keys
   - Cerebras (fast, 1M free tokens/day): https://cloud.cerebras.ai — API Keys
   - OpenRouter (free models): https://openrouter.ai — Keys
   Never paste a key in chat, and never push `.env` — it is in `.gitignore`.
3. Restart the orb or the full app. Then just talk:
   `how are you?`, `explain machine learning simply`, `tell me more`.

Switch brains any time, by voice or text:
```
switch brain to groq
switch brain to gemini
switch brain to cerebras
switch brain to openrouter
list brains
brain status
```
The choice is saved in `config.json`, so it sticks after a restart.
If the brain you picked is down, limited, or has no key, Jarvis
automatically falls back to the next brain that has a key, and tells
you which one answered. `clear chat` starts a fresh conversation.

## Gemini brain (v6) — ask anything, free

Jarvis now has a brain: Google Gemini, free API.
1. Get a free key at https://aistudio.google.com — Get API key, Create API key.
2. In the jarvis folder, copy `.env.example` to `.env` and replace
   `PASTE_YOUR_KEY_HERE` with your key. Never paste the key in chat,
   and never push `.env` — it is in `.gitignore`.
3. Restart the orb or the full app. Then just ask anything:
   `ask what is machine learning`, or any question Jarvis does not
   recognise as a local command. Local commands (time, weather, open,
   find companies...) still run locally first.

## Pass a task from Pax to Jarvis (task queue)

You tell Pax a task in chat, Pax writes it to `tasks.json` in this
repo, and the orb picks it up within about 60 seconds and does it,
while your PC is on and the orb is running. It is a relay, not live
control, so there is a short delay.

Safe through the queue only: time, weather, open/search, find
companies, research, create Word/PDF, note, timer, morning workflow.
The queue can never submit a job, send a message, pay, delete,
shut down, sign in, or share personal details. Those still need
your one-time permission on your PC.

## Desktop app (v2) — window with logo, app manager, PC controls

```bash
pip install -r requirements.txt
python jarvis_gui.py
```

Left sidebar has the lion logo, a Listen button, timer and weather shortcuts.
Type commands in the box, or press Listen and speak. Apps section opens and
closes Chrome, Edge, VS Code, Notepad, Calculator, File Explorer, Paint,
Task Manager, Settings and Spotify. PC controls do volume up/down/mute,
lock, sleep, brightness, shutdown and restart (shutdown/restart ask first).

Build a Windows .exe (must be built on Windows):

```bat
build_exe.bat
```

That makes `dist\Jarvis.exe` with the lion logo as its icon. Double-click
it to run, no Command Prompt needed.

## What is next (v2 ideas)

- Morning briefing (calendar, weather, jobs to apply for)
- Local AI chat with Ollama, if the PC can run it
- Open files and folders by name
- Control music and volume

## Privacy

v1 runs locally. Voice goes to Google speech recognition only in voice
mode; text mode stays fully offline except web search and weather.

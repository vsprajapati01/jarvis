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

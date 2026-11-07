#!/usr/bin/env python3
"""
Jarvis v1 - local-first voice assistant for PC.
Runs on Windows, macOS and Linux. No API key needed for v1.

Voice mode (needs a microphone):
    python jarvis.py
Text mode (no mic needed, good for testing):
    python jarvis.py --text

Say "jarvis" first in voice mode, then a command.
Or clap twice:  python jarvis.py --clap
  Double clap runs the morning workflow, then listens for a command.
In text mode, just type the command.

Commands:
    time / date
    open chrome | open vs code | open notepad | open calculator
    search <something>          - opens a web search
    weather <city>              - uses wttr.in, no key needed
    timer 5 minutes / timer 30 seconds
    remind me to <thing> in 10 minutes
    note <text>                 - saves to notes.txt
    help
    exit / quit
"""
import datetime
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
NOTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.txt")
WAKE_WORD = "jarvis"

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None


def load_config():
    defaults = {"name": "Jarvis", "voice_rate": 175, "voice_volume": 1.0}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                defaults.update(json.load(f))
        except Exception:
            pass
    return defaults


CONFIG = load_config()
_engine = None


def speak(text):
    """Speak out loud if possible, always print so it works anywhere."""
    print(f"{CONFIG['name']}: {text}")
    if pyttsx3 is None:
        return
    global _engine
    try:
        if _engine is None:
            _engine = pyttsx3.init()
            _engine.setProperty("rate", CONFIG["voice_rate"])
            _engine.setProperty("volume", CONFIG["voice_volume"])
        _engine.say(text)
        _engine.runAndWait()
    except Exception:
        pass


def open_website(target):
    """Open a website or search in the user's own Chrome, with their
    logged-in profile. That is the safe way Jarvis 'logs in' - it never
    stores or types a password. If you are already signed in to a site
    in Chrome (Gmail, LinkedIn, YouTube...), it opens signed in.
    If you are not signed in there, Chrome shows that site's normal
    sign-in page and you sign in yourself, once, in Chrome."""
    target = target.strip()
    if not target:
        return "Say it like: open youtube.com, or open gmail."
    if " " in target or "." not in target:
        # A phrase, not a site - search it instead.
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(target))
        return f"Searching for {target}."
    url = target if target.startswith(("http://", "https://")) else "https://" + target
    webbrowser.open(url)
    return f"Opening {url} in your browser."


def open_app(app):
    system = platform.system()
    targets = {
        "chrome": {
            "Windows": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "Darwin": "/Applications/Google Chrome.app",
            "Linux": "google-chrome",
        },
        "vs code": {
            "Windows": "code",
            "Darwin": "code",
            "Linux": "code",
        },
        "notepad": {
            "Windows": "notepad",
            "Darwin": "TextEdit",
            "Linux": "gedit",
        },
        "calculator": {
            "Windows": "calc",
            "Darwin": "Calculator",
            "Linux": "gnome-calculator",
        },
    }
    if app not in targets:
        return f"I don't know how to open {app} yet. Add it in jarvis.py."
    target = targets[app].get(system)
    if not target:
        return f"No {app} shortcut set up for {system} yet."
    try:
        if system == "Darwin" and target.endswith(".app"):
            subprocess.Popen(["open", target])
        elif system == "Windows" and os.path.exists(target):
            subprocess.Popen([target])
        else:
            subprocess.Popen(target, shell=True)
        return f"Opening {app}."
    except Exception as e:
        return f"Could not open {app}: {e}"


def get_weather(city="Gainesville"):
    try:
        url = "https://wttr.in/" + urllib.parse.quote(city) + "?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "jarvis-v1"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        now = data["current_condition"][0]
        return (
            f"Weather in {city}: {now['weatherDesc'][0]['value']}, "
            f"{now['temp_F']}F, feels like {now['FeelsLikeF']}F, "
            f"humidity {now['humidity']}%."
        )
    except Exception:
        return "Sorry, I could not get the weather right now. Check your internet."


def set_timer(seconds, label="Timer"):
    def _run():
        time.sleep(seconds)
        speak(f"{label} done.")

    threading.Thread(target=_run, daemon=True).start()
    if seconds >= 60:
        mins = seconds // 60
        return f"Timer set for {mins} minute{'s' if mins != 1 else ''}."
    return f"Timer set for {seconds} second{'s' if seconds != 1 else ''}."


def parse_duration(text):
    m = re.search(r"(\d+)\s*(hour|minute|min|second|sec)", text)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    if unit.startswith("hour"):
        return n * 3600
    if unit.startswith("min"):
        return n * 60
    return n


def handle_command(command):
    """Return False to quit, True to keep listening."""
    cmd = command.strip().lower()
    if not cmd:
        return True
    if cmd in ("exit", "quit", "goodbye", "stop"):
        speak("Goodbye.")
        return False
    if cmd == "help":
        speak("Try: time, date, open chrome, open youtube.com, go to gmail.com, search python, weather Gainesville, timer 5 minutes, remind me to drink water in 10 minutes, or note buy milk.")
        return True
    # Timer / reminder first: "timer" contains "time", so check it before time.
    if cmd.startswith("timer"):
        seconds = parse_duration(cmd)
        if seconds:
            speak(set_timer(seconds))
        else:
            speak("Say it like: timer 5 minutes.")
        return True
    if cmd.startswith("remind me to"):
        seconds = parse_duration(cmd)
        thing = re.sub(r"remind me to", "", cmd, flags=re.I).strip()
        thing = re.sub(r"in \d+.*$", "", thing).strip()
        if seconds:
            speak(set_timer(seconds, f"Reminder: {thing}"))
            speak(f"Okay, I will remind you to {thing}.")
        else:
            speak("Say it like: remind me to drink water in 10 minutes.")
        return True
    if cmd.startswith("note "):
        note = command.strip()[5:]
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M} - {note}\n")
        speak("Note saved.")
        return True
    if cmd in ("time", "what time is it", "what is the time"):
        speak("It is " + datetime.datetime.now().strftime("%I:%M %p") + ".")
        return True
    if cmd in ("date", "what is the date", "what day is it"):
        speak("Today is " + datetime.datetime.now().strftime("%A, %B %d, %Y") + ".")
        return True
    if cmd.startswith("open "):
        rest = cmd[5:].strip()
        # "open chrome" / "open vs code" are apps; anything else is a website.
        if rest in ("chrome", "vs code", "notepad", "calculator"):
            speak(open_app(rest))
        else:
            speak(open_website(command.strip()[5:].strip()))
        return True
    if cmd.startswith("go to "):
        speak(open_website(command.strip()[6:].strip()))
        return True
    if cmd.startswith("search "):
        query = command.strip()[7:]
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(query))
        speak(f"Searching for {query}.")
        return True
    if cmd.startswith("weather"):
        city = command.strip()[7:].strip() or "Gainesville"
        speak(get_weather(city))
        return True
    speak("I did not understand that. Say help to hear what I can do.")
    return True


def listen_voice():
    if sr is None:
        speak("Voice listening needs the speechrecognition library. Run in text mode instead: python jarvis.py --text")
        return None
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source, timeout=10, phrase_time_limit=10)
    try:
        return r.recognize_google(audio)
    except Exception:
        return ""


def main():
    text_mode = "--text" in sys.argv
    clap_mode = "--clap" in sys.argv
    if text_mode:
        speak(f"Hello, I am {CONFIG['name']}. Type a command, or type help. In text mode, type only - speaking will not work here. For voice, run: python jarvis.py")
    else:
        speak(f"Hello, I am {CONFIG['name']}. Say {WAKE_WORD} to wake me, then say a command. Say help for commands.")
    if text_mode:
        while True:
            try:
                command = input("You: ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not handle_command(command):
                break
        return
    if sr is None:
        print("Install voice support first: pip install -r requirements.txt")
        print("Or run text mode: python jarvis.py --text")
        return
    if clap_mode:
        try:
            from clap_detector import start_clap_detector
            from morning_workflow import run_morning_workflow
            print("Double-clap mode on. Clap twice for the morning workflow.")
            start_clap_detector(run_morning_workflow)
        except Exception as e:
            print(f"Clap mode unavailable: {e}. Falling back to wake word.")
    while True:
        heard = listen_voice()
        if heard is None:
            break
        if not heard:
            continue
        print(f"Heard: {heard}")
        if WAKE_WORD in heard.lower():
            speak("Yes?")
            command = listen_voice()
            if command:
                print(f"Command: {command}")
                if not handle_command(command):
                    break


if __name__ == "__main__":
    main()

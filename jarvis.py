#!/usr/bin/env python3
"""
Jarvis v8 - local-first voice assistant for PC, with an agent loop.
Runs on Windows, macOS and Linux. No API key needed for local tasks.

Voice mode (needs a microphone):
    python jarvis.py
Text mode (no mic needed, good for testing):
    python jarvis.py --text

Talk normally - you do NOT need a specific command. Say "jarvis"
first in voice mode, then just talk: "open youtube for me",
"research the best data analyst certifications", "how do I learn
SQL?", "set a timer for 5 minutes". The agent loop (agent.py)
decides: chat, research first, or run a task on your PC.
Or clap twice:  python jarvis.py --clap
  Double clap runs the morning workflow, then listens for a command.
In text mode, just type.

Local tasks (no key needed):
    time / date
    open chrome | open vs code | open notepad | open calculator
    search <something>          - opens a web search
    weather <city>              - uses wttr.in, no key needed
    timer 5 minutes / timer 30 seconds
    remind me to <thing> in 10 minutes
    note <text>                 - saves to notes.txt
    research <topic>            - searches the web, brain summarises it
    find companies hiring data analysts in USA
    create word / make pdf <title> : <text>
    morning briefing

Critical actions (submit / send / pay / delete / shutdown / sign in /
share personal details) are NEVER done silently - Jarvis asks first
through permissions.py, and even after a yes only the safe part
(opening the site in your own Chrome) runs. The click stays yours.
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
    # --- v8: answer a pending critical-action question first ---
    # The proposal already asked ("say yes to go ahead, or no to
    # stop"), so this yes/no IS the answer - do not ask again.
    if cmd in ("yes", "y", "yeah", "go ahead", "ok", "okay", "do it", "yes please"):
        try:
            from agent import has_pending, confirm_pending
            if has_pending():
                _ok, msg = confirm_pending(answer=True)
                if " __PREP__:" in msg:
                    note, _, prep = msg.partition(" __PREP__:")
                    speak(note.strip())
                    # Safe prep only: open the site in his own Chrome.
                    # The critical click itself is never run here.
                    return handle_command("open " + prep.strip())
                if msg:
                    speak(msg)
                return True
        except Exception:
            pass
        speak("I was not waiting for a yes or no. What do you want me to do?")
        return True
    if cmd in ("no", "nope", "stop that", "cancel", "don't"):
        try:
            from agent import has_pending, cancel_pending
            if has_pending():
                cancel_pending()
                speak("Okay, I stopped. Nothing was sent, submitted, or paid.")
                return True
        except Exception:
            pass
        # No pending question: "stop" means quit (handled below for "stop").
        if cmd == "stop":
            speak("Goodbye.")
            return False
        speak("Okay.")
        return True
    if cmd in ("exit", "quit", "goodbye", "stop"):
        speak("Goodbye.")
        return False
    if cmd == "help":
        speak("Just talk to me normally. Try: time, what is the weather in Tampa, open youtube for me, research the best data analyst certifications, find companies hiring data analysts in USA, create word my notes : hello, make pdf my notes : hello, timer 5 minutes, remind me to drink water in 10 minutes, or note buy milk. Or ask anything - what is machine learning, how do I learn SQL - and my brain will answer, short and plain. Switch brains with: switch brain to groq, switch brain to gemini, switch brain to cerebras, or switch brain to openrouter. Say list brains to see which ones have a key. Critical steps - submit, send, pay, delete, shut down, sign in - always ask you first, and the click stays yours.")
        return True
    # --- brain switching: talk normally, switch for speed / fallback ---
    if cmd.startswith("switch brain to ") or cmd.startswith("use brain "):
        name = cmd.replace("switch brain to ", "").replace("use brain ", "").strip()
        name = {"open router": "openrouter"}.get(name, name)
        try:
            from brain import set_provider, get_provider, list_providers
            if set_provider(name):
                providers = dict((p[0], p) for p in list_providers())
                has_key = providers[name][2]
                if has_key:
                    speak(f"Switched to {providers[name][1]}. Talk to me normally now.")
                else:
                    speak(f"Switched to {providers[name][1]}, but I do not have a key for it yet in .env, so I will fall back to another brain until you add one.")
            else:
                speak("I know gemini, groq, cerebras and openrouter. Say switch brain to groq, for example.")
        except Exception as e:
            speak(f"Could not switch brain: {e}")
        return True
    if cmd in ("list brains", "show brains", "brain status", "which brain"):
        try:
            from brain import list_providers
            parts = []
            for name, label, has_key, selected in list_providers():
                mark = " (current)" if selected else ""
                key = "key saved" if has_key else "no key yet"
                parts.append(f"{label}{mark} - {key}")
            speak("Brains: " + "; ".join(parts) + ". Switch with: switch brain to groq.")
        except Exception as e:
            speak(f"Could not list brains: {e}")
        return True
    if cmd in ("clear chat", "forget chat", "new chat"):
        try:
            from brain import clear_history
            clear_history()
            speak("Okay, fresh chat. What do you want to talk about?")
        except Exception:
            speak("Okay, fresh chat.")
        return True
    if cmd.startswith("talk ") or cmd.startswith("chat ") or cmd.startswith("ask "):
        # "talk <anything>" is just normal conversation - send it to the brain.
        question = command.strip().split(" ", 1)[1].strip() if " " in command.strip() else ""
        if not question:
            speak("I am listening. Just talk to me normally.")
            return True
        try:
            from brain import ask_brain
            answer, err = ask_brain(question)
            speak(err or answer)
        except Exception as e:
            speak(f"Brain unavailable: {e}")
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
    if cmd.startswith("find companies") or cmd.startswith("find jobs"):
        query = command.strip()
        # Drop the "find companies" / "find jobs" prefix, keep the rest.
        query = re.sub(r"^find (companies|jobs)\s*", "", query, flags=re.I).strip()
        if not query:
            speak("Tell me what to find, like: find companies hiring data analysts in USA")
            return True
        speak(f"Searching for {query}. Making a list for you.")
        try:
            from find_companies import find_companies, format_list
            results, filename, err = find_companies(query)
            if err:
                speak(err)
            else:
                speak(format_list(results) + f" Saved to {os.path.basename(filename)}.")
        except Exception as e:
            speak(f"Could not search right now: {e}")
        return True
    if cmd.startswith("create word ") or cmd.startswith("make word "):
        rest = command.strip().split(" ", 2)[2].strip() if len(command.strip().split(" ", 2)) > 2 else ""
        title, _, text = rest.partition(":")
        title, text = title.strip(), (text.strip() or "Created by Jarvis.")
        try:
            from create_docs import make_word
            filename, err = make_word(title, text)
            speak(err or f"Word file saved: {os.path.basename(filename)}")
        except Exception as e:
            speak(f"Could not make the Word file: {e}")
        return True
    if cmd.startswith("make pdf ") or cmd.startswith("create pdf "):
        rest = command.strip().split(" ", 2)[2].strip() if len(command.strip().split(" ", 2)) > 2 else ""
        title, _, text = rest.partition(":")
        title, text = title.strip(), (text.strip() or "Created by Jarvis.")
        try:
            from create_docs import make_pdf
            filename, err = make_pdf(title, text)
            speak(err or f"PDF saved: {os.path.basename(filename)}")
        except Exception as e:
            speak(f"Could not make the PDF: {e}")
        return True
    if cmd.startswith("open gods eye") or cmd.startswith("show gods eye"):
        try:
            from gods_eye import start_gods_eye
            speak(start_gods_eye())
        except Exception as e:
            speak(f"Could not open God's Eye View: {e}")
        return True
    if cmd.startswith("show flights") or cmd.startswith("show ships") or cmd.startswith("show satellites") or cmd.startswith("show earthquakes"):
        try:
            from gods_eye import open_gods_eye
            speak(open_gods_eye() + " Pick that layer in the globe once it loads.")
        except Exception as e:
            speak(f"Could not open God's Eye View: {e}")
        return True
    if cmd.startswith("research "):
        topic = command.strip()[9:].strip()
        try:
            # v8: search first, then the brain summarises what it found
            # in short plain words, naming its sources.
            from agent import research_and_answer
            speak(research_and_answer(topic))
        except Exception as e:
            speak(f"Could not research that right now: {e}")
        return True
    if cmd.startswith("check mail") or cmd.startswith("check my mail"):
        speak("Checking mail needs your Gmail connected to Jarvis first, with Google sign-in, not your password. I have not set that up yet. For now, say open gmail.com and I will open your inbox in Chrome, signed in if you already are there.")
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
    if cmd.startswith("ask ") or cmd.startswith("chat "):
        question = command.strip().split(" ", 1)[1].strip()
        try:
            from brain import ask_brain
            answer, err = ask_brain(question)
            speak(err or answer)
        except Exception as e:
            speak(f"Brain unavailable: {e}")
        return True
    # v8 agent loop: talk normally. The loop decides - chat, research
    # first, run a PC task, or ask first for a critical step.
    # Anything it cannot do as a task is answered by the brain.
    try:
        from agent import route
        if route(command.strip(), handle_command, speak):
            return True
    except Exception as e:
        speak(f"Agent loop unavailable: {e}")
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

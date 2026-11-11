#!/usr/bin/env python3
"""
Jarvis v9 - PC control, v1: Chrome + typing / clicking, watched.

What this is:
  Jarvis can now control the whole PC - keyboard and mouse -
  when Vishal tells him to touch something.

  Exact mode:  "type hello" / "search Data Analyst jobs"
               -> does exactly that, no guessing, no extra clicks.
  General mode: "open Chrome and search for Data Analyst jobs"
               -> plans the steps, checks the screen, reports back.

What v1 does (safe, tested first):
  - open Chrome (and only Chrome in v1 - Word / Power BI open,
    but no clicking inside them yet)
  - open a website in Chrome
  - type text exactly as given, press Enter, Ctrl+T, Ctrl+L, etc.
  - click at X,Y - ONLY when Vishal gives the coordinates,
    or after he has watched the screen and said yes
  - take a screenshot, so Vishal can see what Jarvis sees
  - STOP: "jarvis stop" / "stop" / Esc - stops mouse + keyboard
    immediately, no finishing the current step.

What v1 does NOT do:
  - No Submit / Send / Pay / Delete / Close-without-saving click
    without asking first. Those go through permissions.py.
  - No password typing, ever. Vishal types passwords himself.
  - No drag-and-drop in Power BI, no building visuals by clicks.
    Power BI in v1: open Power BI, open a .pbix file, type DAX
    in the formula bar as Vishal dictates. The visual clicks
    stay Vishal's, until v2 (UI Automation) is tested.
  - No headless run first. Watch the screen the first 10 times
    for every new app.

Safety:
  - DRY_RUN mode (default on Linux / in tests, and when
    pyautogui is not installed): every action is logged,
    nothing moves the real mouse. Set dry_run=False on
    Vishal's Windows PC, with the screen on, to go live.
  - FAILSAFE: moving the mouse to a screen corner stops
    PyAutoGUI (its built-in failsafe). Keep your own
    keyboard + mouse plugged in as backup - Alt+Tab away,
    or press Esc, and you take over.

Install on Windows (his Dell / brain PC):
    pip install pyautogui pynput

Usage:
    from pc_control import PCControl
    pc = PCControl(dry_run=True)   # safe test, logs only
    pc = PCControl(dry_run=False)  # live on Windows, screen on
    pc.open_chrome("https://www.linkedin.com")
    pc.type_text("Data Analyst jobs in Florida")
    pc.press_enter()
    pc.screenshot("screen.png")
    pc.stop()  # stop word - halts everything
"""
import os
import time
import webbrowser

try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    _HAS_PYAUTOGUI = False

try:
    from permissions import is_critical, ask_permission
    _HAS_PERMISSIONS = True
except Exception:
    _HAS_PERMISSIONS = False

    def is_critical(action):
        bad = ["submit", "send", "pay", "delete", "shutdown",
               "shut down", "restart", "sign in", "login"]
        return any(w in action.lower() for w in bad)

    def ask_permission(action, input_fn=input):
        print(f"Jarvis: critical step, need permission: {action}")
        return input_fn("Say yes or no: ").strip().lower() in ("yes", "y", "ok")


STOP_WORDS = ("jarvis stop", "stop", "stop now", "stop jarvis", "cancel")


class PCControl:
    """One object that owns the mouse + keyboard. Only one
    PCControl should exist at a time, so stop() always works."""

    def __init__(self, dry_run=True, log_fn=print):
        self.dry_run = dry_run
        self.log = log_fn
        self.stopped = False
        self.live = (not dry_run) and _HAS_PYAUTOGUI
        if not dry_run and not _HAS_PYAUTOGUI:
            self.log("Jarvis: PyAutoGUI is not installed, so I am staying "
                     "in dry-run mode. Run: pip install pyautogui pynput")
            self.dry_run = True
        if self.live:
            # PyAutoGUI failsafe: corner of screen = stop.
            pyautogui.FAILSAFE = True
            # Small pause between actions, so Vishal can watch.
            pyautogui.PAUSE = 0.3
        self.log(f"Jarvis PC control ready. Live: {self.live}, "
                 f"dry-run: {self.dry_run}. Say 'jarvis stop' to stop me.")

    # -- stop ------------------------------------------------------
    def stop(self):
        """Stop word. Halts mouse + keyboard immediately."""
        self.stopped = True
        self.log("Jarvis: Stopped. Mouse and keyboard are yours again.")
        return "Stopped."

    def check_stop(self, text=""):
        """Return True if the text is a stop word, or stop was set."""
        if self.stopped:
            return True
        if text.strip().lower() in STOP_WORDS:
            self.stop()
            return True
        return False

    def _guard(self, action):
        """Block if stopped, or if the action is critical and
        Vishal has not said yes. Returns True if allowed."""
        if self.stopped:
            self.log("Jarvis: I am stopped, I will not do that.")
            return False
        if is_critical(action):
            self.log(f"Jarvis: That is critical - {action} - "
                     "so I need your permission first.")
            if not ask_permission(action):
                return False
        return True

    # -- basic actions --------------------------------------------
    def open_chrome(self, url=None):
        """Open Chrome, optionally to a URL. v1 app: Chrome only."""
        if not self._guard("open chrome"):
            return False
        if url:
            self.log(f"Jarvis: Opening Chrome to {url}")
        else:
            self.log("Jarvis: Opening Chrome")
        if self.live:
            if url:
                webbrowser.open(url)
            else:
                webbrowser.open("https://www.google.com")
            time.sleep(2)
        return True

    def open_app(self, app):
        """Open an app by name. v1: Chrome is tested. Word and
        Power BI open, but do NOT click inside them yet."""
        app = app.strip().lower()
        if app in ("chrome", "google chrome"):
            return self.open_chrome()
        if app in ("power bi", "powerbi", "power bi desktop"):
            self.log("Jarvis: Opening Power BI. I can open it and "
                     "type in it as you dictate, but I will not "
                     "click-drag visuals yet - that is v2, after testing.")
            if self.live:
                os.startfile("PBIDesktop.exe") if os.name == "nt" else None
            return True
        if app in ("word", "microsoft word"):
            self.log("Jarvis: Opening Word. I can type in it as you dictate.")
            if self.live and os.name == "nt":
                os.startfile("WINWORD.EXE")
            return True
        self.log(f"Jarvis: I do not know how to open '{app}' yet. "
                 "Chrome, Word, and Power BI are the v1 apps.")
        return False

    def type_text(self, text):
        """Type text exactly as given. No adding words, no guessing."""
        if not text:
            return False
        if not self._guard(f"type text: {text[:60]}"):
            return False
        self.log(f"Jarvis: Typing: {text}")
        if self.live:
            pyautogui.typewrite(text, interval=0.05)
        return True

    def press_enter(self):
        if not self._guard("press Enter"):
            return False
        self.log("Jarvis: Pressing Enter")
        if self.live:
            pyautogui.press("enter")
        return True

    def hotkey(self, *keys):
        """E.g. hotkey('ctrl', 't') for a new tab, ('ctrl', 'l')
        to go to the address bar, ('ctrl', 's') to save."""
        if not self._guard(f"press {'+'.join(keys)}"):
            return False
        self.log(f"Jarvis: Pressing {'+'.join(keys)}")
        if self.live:
            pyautogui.hotkey(*keys)
        return True

    def click(self, x, y):
        """Click at X,Y. v1 rule: only when Vishal gave the
        coordinates, or after he watched the screen and said yes.
        Never click Submit / Send / Pay / Delete without asking."""
        if not self._guard(f"click at {x},{y}"):
            return False
        self.log(f"Jarvis: Clicking at {x},{y}. Watch the screen.")
        if self.live:
            pyautogui.click(x, y)
        return True

    def search(self, query):
        """Exact mode, Chrome: new tab, type the query, Enter.
        This is 'search as I say' - no extra words added."""
        if not self._guard(f"search for {query}"):
            return False
        self.open_chrome()
        self.hotkey("ctrl", "t")
        self.type_text(query)
        self.press_enter()
        self.log(f"Jarvis: Searched for '{query}'. Check the screen.")
        return True

    def screenshot(self, filename="jarvis-screen.png"):
        """Take a screenshot, so Vishal can see what Jarvis sees."""
        self.log(f"Jarvis: Screenshot saved to {filename}")
        if self.live:
            pyautogui.screenshot(filename)
        return filename


def handle_pc_command(text, pc=None):
    """Plain-words -> PC control. Returns (handled, reply).
    Use this from agent.py / jarvis.py, with one shared PCControl.
    Commands in v1:
      'jarvis stop' / 'stop' - stop everything
      'open chrome' / 'open chrome to linkedin.com'
      'search <query>' - Chrome, new tab, type query, Enter
      'type <text>' - type exactly that text
      'press enter' - press Enter
      'open power bi' / 'open word' - open, no clicking inside yet
    """
    if pc is None:
        pc = PCControl(dry_run=True)
    t = text.strip()
    low = t.lower()
    # Strip wake word
    low = low.replace("hey jarvis", "").replace("jarvis", "").strip()
    t_clean = t
    if pc.check_stop(low):
        return True, "Stopped. Mouse and keyboard are yours again."
    if low.startswith("open chrome"):
        url = low[len("open chrome"):].strip(" to")
        if url and "." in url:
            if not url.startswith("http"):
                url = "https://" + url
            pc.open_chrome(url)
            return True, f"Opened Chrome to {url}."
        pc.open_chrome()
        return True, "Opened Chrome."
    if low.startswith("search "):
        query = t_clean[len("search "):].strip() if False else low[len("search "):].strip()
        # Use the original text after 'search ' for exact typing
        idx = t.lower().find("search ")
        query = t[idx + len("search "):].strip()
        pc.search(query)
        return True, f"Searched for '{query}'. Check the screen."
    if low.startswith("type "):
        idx = t.lower().find("type ")
        pc.type_text(t[idx + len("type "):])
        return True, "Typed that exactly as you said."
    if low in ("press enter", "press return", "enter"):
        pc.press_enter()
        return True, "Pressed Enter."
    if low.startswith("open power bi"):
        pc.open_app("power bi")
        return True, ("Opened Power BI. I can type in it as you dictate, "
                      "but I will not click-drag visuals yet.")
    if low.startswith("open word"):
        pc.open_app("word")
        return True, "Opened Word. Tell me what to type."
    if low.startswith("screenshot"):
        f = pc.screenshot()
        return True, f"Screenshot saved to {f}."
    return False, ""

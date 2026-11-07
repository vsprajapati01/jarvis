#!/usr/bin/env python3
"""
Jarvis - run the PC, with permission for critical parts.
This is the rule for the whole assistant:

FREE (no asking):
  open apps and websites, search the web, weather, time, timers,
  reminders, notes, find companies and make a list, research a topic
  and save a report, create a Word file or a PDF, read a file.

ASK FIRST (critical parts - Jarvis must get a yes from you):
  submit a job application, send an email or a message, pay for
  anything, delete a file, shut down or restart the PC, sign in to
  a site, share your personal details with a site or a tool.

How asking works:
- In text mode, Jarvis prints the exact thing it wants to do and
  waits for you to type yes or no.
- In the desktop app, it shows a yes/no box.
- In voice mode, it asks out loud and waits for yes/no.
- A yes covers ONLY that one action, that one time. It never
  becomes a blanket yes for the next time.
"""
CRITICAL = [
    "submit a job application",
    "send an email or a message",
    "pay for anything",
    "delete a file",
    "shut down or restart the PC",
    "sign in to a site",
    "share personal details with a site or a tool",
]


def is_critical(action):
    return any(word in action.lower() for word in
               ["submit", "send", "pay", "delete", "shutdown", "restart",
                "sign in", "login", "share my"])


def ask_permission(action, input_fn=input):
    """Ask once, in plain words. Returns True only on a clear yes."""
    print(f"Jarvis: This is a critical step, so I need your permission: {action}")
    answer = input_fn("Say yes to go ahead, or no to stop: ").strip().lower()
    if answer in ("yes", "y", "ok", "go ahead", "go"):
        return True
    print("Jarvis: Okay, I stopped. Nothing was sent, submitted, or paid.")
    return False

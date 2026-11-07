#!/usr/bin/env python3
"""
Jarvis task queue - the bridge between Pax (in chat) and Jarvis (on your PC).

How it works, in plain words:
1. You tell Pax a task here in chat, in your own words.
2. Pax writes that task into tasks.json in your jarvis GitHub repo.
3. Jarvis on your PC checks that file every 60 seconds while the
   orb is running. When it sees a new task, it does it.
4. Jarvis marks the task done, so it never runs twice.

It is NOT live control. It is a relay with a short delay, usually
under a minute, and only while your PC is on and the orb is running.

Safety rules - these are hard limits, not suggestions:
- Only predefined, safe commands are allowed through the queue:
  time, date, weather, open a website/app, search, find companies,
  research, create word/pdf, note, timer, reminder, morning workflow.
- The queue can NEVER do a critical action on its own: no submitting
  a job application, no sending an email or message, no paying,
  no deleting a file, no shutdown/restart, no signing in, no sharing
  personal details. Those still need your one-time permission, on
  your PC, for that one action only.
- A task from the queue is run once, then marked done locally in
  tasks_done.json, so a restart does not re-run it.
"""
import json
import os
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_URL = "https://raw.githubusercontent.com/vsprajapati01/jarvis/main/tasks.json"
DONE_FILE = os.path.join(BASE_DIR, "tasks_done.json")

# Commands the queue is allowed to run. Anything else is refused.
SAFE_PREFIXES = (
    "time", "date", "weather", "open ", "go to ", "search ",
    "find companies", "find jobs", "research ", "create word ",
    "make word ", "make pdf ", "create pdf ", "note ", "timer ",
    "remind me to ", "help", "morning workflow", "show window",
)


def load_done():
    if os.path.exists(DONE_FILE):
        try:
            with open(DONE_FILE, encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_done(done):
    try:
        with open(DONE_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(done), f)
    except Exception:
        pass


def fetch_tasks():
    """Return the task list from GitHub, or [] if offline / empty."""
    try:
        req = urllib.request.Request(TASKS_URL, headers={"User-Agent": "jarvis-task-queue"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        tasks = data.get("tasks", []) if isinstance(data, dict) else data
        return tasks if isinstance(tasks, list) else []
    except Exception:
        return []


def is_safe(task_text):
    cmd = (task_text or "").strip().lower()
    return any(cmd.startswith(p) for p in SAFE_PREFIXES)


def check_for_new_tasks(handle_command, speak):
    """Check once. Run any new safe task. Return a list of task ids done."""
    done = load_done()
    ran = []
    for task in fetch_tasks():
        tid = str(task.get("id", ""))
        text = (task.get("command", "") or "").strip()
        if not tid or tid in done or not text:
            continue
        if not is_safe(text):
            print(f"Task queue: refused unsafe task {tid}: {text}")
            done.add(tid)
            continue
        print(f"Task queue: running {tid}: {text}")
        speak(f"New task from you: {text}")
        try:
            if text.lower() == "morning workflow":
                from morning_workflow import run_morning_workflow
                run_morning_workflow()
            else:
                handle_command(text)
        except Exception as e:
            speak(f"That task failed: {e}")
        done.add(tid)
        ran.append(tid)
    if ran:
        save_done(done)
    return ran

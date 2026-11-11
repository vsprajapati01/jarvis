#!/usr/bin/env python3
"""Jarvis v10 - clean text CLI. No orb, no GUI, no neon, no HUD.

Plain text only. Type a command, get a short answer.
This is the v10 entry point. The old orb / GUI still exist
in jarvis_overlay.py / jarvis_gui.py if you want them, but
v10 does not use them.

Commands:
  build website for <name> in <location> - <description>
      Example: build website for Ember and Salt in Brickell, Miami - A small restaurant. Simple food, deep flavour.
      Then Jarvis asks for menu items, or use "no menu".
  find companies <query>
      Example: find companies hiring data analysts in Florida
  draft email for <business>
      Draft only. Saved to drafts/. Never sent.
  memory
      Show what the team remembers.
  help
  quit / exit

Run:
  python jarvis_v10.py
"""
import sys

from agents import EmailAgent, FinderAgent, WebsiteAgent, run_team
from memory import list_results, list_tasks, recall


def _print(text):
    print(text)


def _ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "quit"


def _build_website(command):
    # "build website for X in Y - description"
    rest = command[len("build website for"):].strip()
    if " - " in rest:
        head, description = rest.split(" - ", 1)
    else:
        head, description = rest, "A small local business."
    if " in " in head:
        name, location = head.rsplit(" in ", 1)
    else:
        name, location = head, ""
    name, location, description = name.strip(), location.strip(), description.strip()
    if not name:
        _print("Tell me the business name, like: build website for Ember and Salt in Brickell, Miami - A small restaurant.")
        return
    _print("Menu items? Type them one per line as: Name | Description | Price")
    _print("Type 'done' when finished, or 'no menu' for none.")
    items = []
    while True:
        line = _ask("menu> ")
        if line.lower() in ("done", "no menu", ""):
            break
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3:
            items.append(tuple(parts))
        else:
            _print("Use: Name | Description | Price")
    contact = _ask("Contact (phone / email, or leave blank)> ")
    result = run_team(name, location, description, items, contact)
    _print(result["website"]["summary"])
    _print("Email draft saved: " + result["email"]["draft"])
    _print("Draft only. Not sent. Read it before you send it yourself.")


def main():
    _print("Jarvis v10 - clean text mode")
    _print("Type 'help' for commands, 'quit' to stop.")
    while True:
        command = _ask("jarvis> ")
        low = command.lower()
        if low in ("quit", "exit", "stop"):
            _print("Done.")
            return 0
        if low == "help":
            _print("build website for <name> in <location> - <description>")
            _print("find companies <query>")
            _print("draft email for <business>")
            _print("memory")
            _print("quit")
            continue
        if low == "memory":
            _print("Tasks:")
            for task in list_tasks():
                _print(f"  {task['id']}. {task['kind']}: {task['detail']} - {task['status']}")
            _print("Last website: " + str(recall("last_website", "none")))
            _print("Business: " + str(recall("business_name", "none")))
            continue
        if low.startswith("build website for"):
            _build_website(command)
            continue
        if low.startswith("find companies"):
            query = command[len("find companies"):].strip()
            result = FinderAgent().run(query)
            _print(result.get("note", ""))
            for name in result.get("names", []):
                _print("  - " + name)
            continue
        if low.startswith("draft email for"):
            business = command[len("draft email for"):].strip()
            folder = recall("last_website", "")
            result = EmailAgent().run(business, folder)
            _print("Draft saved: " + result["draft"])
            _print(result["note"])
            continue
        if not command:
            continue
        _print("I did not understand that. Type 'help'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

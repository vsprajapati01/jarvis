#!/usr/bin/env python3
"""Jarvis v10 - shared memory.

One small JSON file that all v10 agents read and write.
No database, no cloud, no extra dependency.

File: memory.json in the jarvis folder.
Structure:
  {
    "facts": {"business_name": "...", ...},
    "tasks": [{"id": 1, "kind": "website", "status": "done", ...}],
    "results": {"website_for_x": {"path": "...", ...}}
  }
"""
import json
import os
import time

_MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")


def _load():
    if not os.path.exists(_MEMORY_FILE):
        return {"facts": {}, "tasks": [], "results": {}}
    try:
        with open(_MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("facts", {})
        data.setdefault("tasks", [])
        data.setdefault("results", {})
        return data
    except Exception:
        return {"facts": {}, "tasks": [], "results": {}}


def _save(data):
    with open(_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def remember(key, value):
    """Save one fact, e.g. remember('business_name', 'Ember and Salt')."""
    data = _load()
    data["facts"][key] = value
    _save(data)


def recall(key, default=None):
    return _load()["facts"].get(key, default)


def add_task(kind, detail):
    """Record a task. Returns its id."""
    data = _load()
    task_id = len(data["tasks"]) + 1
    data["tasks"].append({
        "id": task_id,
        "kind": kind,
        "detail": detail,
        "status": "open",
        "created": time.strftime("%Y-%m-%d %H:%M"),
    })
    _save(data)
    return task_id


def finish_task(task_id, result_key=None, result=None):
    data = _load()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["status"] = "done"
    if result_key is not None:
        data["results"][result_key] = result
    _save(data)


def list_tasks():
    return _load()["tasks"]


def list_results():
    return _load()["results"]

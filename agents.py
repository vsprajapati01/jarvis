#!/usr/bin/env python3
"""Jarvis v10 - multi-agent, clean and simple.

Three small agents, one shared memory (memory.py).
Each agent does one job, reports back in plain words,
and writes its result to shared memory so the next
agent can use it. No agent sends, submits, pays, or
deletes anything. Email drafts are saved as files only.

Agents:
  1. FinderAgent   - find companies / businesses without a website.
                     Uses research.py when available, otherwise
                     returns the search results as a list to check.
  2. WebsiteAgent  - build a clean website with website_builder.py.
  3. EmailAgent    - draft a short outreach email and save it.
                     Never sends it. Vishal reads, edits, sends.

Usage:
    from agents import run_team
    result = run_team("Ember and Salt", "Brickell, Miami")
"""
import os

from memory import add_task, finish_task, remember


# ------------------------------------------------------------------
# 1. Finder
# ------------------------------------------------------------------

class FinderAgent:
    name = "finder"

    def run(self, query):
        """Find businesses / companies for a query.
        Returns a short list of names to check, not a verified list.
        Jarvis never claims a business has no website unless the
        research actually checked it."""
        task_id = add_task("find", query)
        names = []
        try:
            from research import research as do_research
            summary, _filename, err = do_research(query)
            if err:
                result = {"query": query, "note": err, "names": []}
                finish_task(task_id, "find:" + query, result)
                return result
            # Keep the first few lines as leads to check by hand.
            lines = [ln.strip("- ").strip() for ln in summary.splitlines() if ln.strip()]
            names = lines[:5]
        except Exception as e:
            names = []
            summary = f"Finder could not search right now: {e}"
        result = {"query": query, "names": names, "note": summary if names else "No leads found. Try a narrower query."}
        remember("last_find_query", query)
        finish_task(task_id, "find:" + query, result)
        return result


# ------------------------------------------------------------------
# 2. Website builder
# ------------------------------------------------------------------

class WebsiteAgent:
    name = "website"

    def run(self, name, description, location="", items=None, contact=""):
        from website_builder import build_website
        task_id = add_task("website", name)
        folder, summary = build_website(name, description, location, items, contact)
        remember("business_name", name)
        remember("last_website", folder)
        result = {"name": name, "folder": folder, "summary": summary}
        finish_task(task_id, "website:" + name, result)
        return result


# ------------------------------------------------------------------
# 3. Email drafts - draft only, never send
# ------------------------------------------------------------------

class EmailAgent:
    name = "email"

    def run(self, business_name, website_folder, recipient_name=""):
        task_id = add_task("email", business_name)
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drafts")
        os.makedirs(base, exist_ok=True)
        slug = business_name.lower().replace(" ", "-")
        path = os.path.join(base, f"{slug}.txt")
        greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
        draft = (
            f"{greeting}\n\n"
            f"I built a simple website for {business_name} — a clean, "
            f"one-page site with your menu and location, no clutter.\n\n"
            f"You can preview it here: {website_folder}/index.html\n\n"
            f"If you like it, I can adjust the text, menu, or photos. "
            f"If not, no problem at all.\n\n"
            f"Thanks,\nVishal Prajapati\n"
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(draft)
        result = {"business": business_name, "draft": path, "note": "Draft only. Not sent. Read it, edit it, send it yourself."}
        finish_task(task_id, "email:" + business_name, result)
        return result


# ------------------------------------------------------------------
# Team: finder -> website -> email, in order, one at a time
# ------------------------------------------------------------------

def run_team(business_name, location, description, items=None, contact=""):
    """Run website + email for one business. Finder is separate:
    use FinderAgent first to pick a business, then run_team."""
    website = WebsiteAgent().run(business_name, description, location, items, contact)
    email = EmailAgent().run(business_name, website["folder"])
    return {"website": website, "email": email}

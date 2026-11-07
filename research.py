#!/usr/bin/env python3
"""
Jarvis - research a topic and save a report.
Command:
    research <topic>
    research Anthropic residency program
    research best data analyst certifications 2026

What it does:
- Searches the web (same search as find companies).
- Saves a report to research-<topic>-<date>.md in the jarvis folder,
  with every source link listed, so you can check it yourself.
- Prints a short summary: the top results, in plain words.

It does NOT invent facts. Every point in the report comes from a
real search result, with its link next to it. If the search finds
nothing, it says so instead of making something up.
"""
import datetime
import os
import re

from find_companies import search_web

HERE = os.path.dirname(os.path.abspath(__file__))


def research(topic, count=10):
    topic = topic.strip()
    if not topic:
        return "", "", "Tell me what to research, like: research Anthropic residency program"
    results, err = search_web(topic, count=count)
    if err:
        return "", "", err
    if not results:
        return "", "", f"No results found for '{topic}'. Try different words."
    stamp = datetime.datetime.now().strftime("%Y-%m-%d")
    safe = re.sub(r"[^A-Za-z0-9 _-]+", "", topic).strip().replace(" ", "-").lower() or "research"
    filename = os.path.join(HERE, f"research-{safe}-{stamp}.md")
    lines = [f"# Research: {topic}", "", f"Date: {stamp}", "",
             "Sources are listed with each point. Check them before using anything here.", ""]
    for i, (title, link, snippet) in enumerate(results, 1):
        lines.append(f"## {i}. {title}")
        lines.append("")
        if snippet:
            lines.append(snippet)
            lines.append("")
        lines.append(f"Source: {link}")
        lines.append("")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    summary = [f"Researched '{topic}' - {len(results)} sources, report saved to {os.path.basename(filename)}:"]
    summary += [f"{i}. {title} - {link}" for i, (title, link, _s) in enumerate(results, 1)]
    return "\n".join(summary), filename, ""


if __name__ == "__main__":
    import sys
    topic = " ".join(sys.argv[1:]) or "Anthropic residency program"
    summary, filename, err = research(topic)
    print(err or summary)

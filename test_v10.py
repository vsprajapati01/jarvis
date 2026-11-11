#!/usr/bin/env python3
"""Tests for Jarvis v10. Dry-run only, no network, no sending."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import EmailAgent, WebsiteAgent
from memory import recall


def main():
    # 1. Website builder - clean, one page, no JavaScript
    website = WebsiteAgent().run(
        "Test Cafe",
        "A small test cafe.",
        "Test Street, Gainesville",
        [("Black Coffee", "Hot, black, no sugar.", "$3"),
         ("Toast", "Butter toast.", "$2")],
        "",
    )
    folder, summary = website["folder"], website["summary"]
    index = os.path.join(folder, "index.html")
    assert os.path.exists(index), "index.html missing"
    with open(index, encoding="utf-8") as f:
        html = f.read()
    assert "Test Cafe" in html
    assert "<script" not in html.lower(), "v10 websites must have no JavaScript"
    assert "animation" not in html.lower(), "v10 websites must have no animations"
    print("website ok:", folder)

    # 2. Email draft - saved, never sent
    result = EmailAgent().run("Test Cafe", folder)
    assert os.path.exists(result["draft"]), "email draft missing"
    with open(result["draft"], encoding="utf-8") as f:
        assert "Test Cafe" in f.read()
    print("email draft ok:", result["draft"])

    # 3. Shared memory
    assert recall("business_name") == "Test Cafe"
    assert recall("last_website") == folder
    print("memory ok")
    print("All v10 tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

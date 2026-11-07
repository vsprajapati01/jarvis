#!/usr/bin/env python3
"""
Jarvis - God's Eye View connection.
God's Eye View (Bilawal Sidhu, MIT, open source) is a browser-based
3D globe with LIVE PUBLIC data: aircraft, ships, satellites,
earthquakes, wildfires, traffic, and public cameras.

What it is NOT:
- Not a real spy satellite, and not live video of the Earth.
- Not private surveillance. It forbids tracking named people and
  facial recognition, and Jarvis will not add those either.
- Traffic is simulated, camera positions are estimates, and the
  data can be delayed or wrong - not for navigation or emergencies.

How Jarvis connects it:
1. First time only, on your PC:
     git clone https://github.com/bilawalsidhu/gods-eye-view.git
     cd gods-eye-view
     npm ci
     npm run doctor
   You need Node.js 24.14 or newer, or 26.x. No account, no API key
   to start - flights, satellites, earthquakes, cameras and weather
   work keyless.
2. Then Jarvis starts it and opens it:
     npm run dev   ->  http://localhost:4173
   Jarvis commands:
     open gods eye
     show flights
     show ships
     show satellites
     show earthquakes
"""
import os
import subprocess
import webbrowser

GLOBE_URL = "http://localhost:4173"
REPO_URL = "https://github.com/bilawalsidhu/gods-eye-view.git"
REPO_DIR = os.path.join(os.path.expanduser("~"), "gods-eye-view")


def is_installed():
    return os.path.isdir(REPO_DIR)


def start_gods_eye():
    """Start the local globe server and open it. Returns a status line."""
    if not is_installed():
        return (
            "God's Eye View is not installed yet. First time only, run this in a terminal:\n"
            f"  git clone {REPO_URL}\n"
            "  cd gods-eye-view\n"
            "  npm ci\n"
            "  npm run doctor\n"
            "You need Node.js 24.14 or newer, or 26.x. Then say 'open gods eye' again."
        )
    try:
        subprocess.Popen(["npm", "run", "dev"], cwd=REPO_DIR,
                         shell=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception as e:
        return f"Could not start God's Eye View: {e}"
    webbrowser.open(GLOBE_URL)
    return ("Opening God's Eye View at localhost:4173. "
            "Give it a few seconds to load, then pick Live Contacts, "
            "Space Missions, Environmental, or Explore Manually.")


def open_gods_eye():
    webbrowser.open(GLOBE_URL)
    return "Opening God's Eye View."

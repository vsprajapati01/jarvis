#!/usr/bin/env python3
"""
Jarvis v8 - transparent HUD helper (shared by the orb and the full window).

The idea: the Jarvis window should be see-through, so Vishal can see
his Windows desktop behind it. Only the high-tech HUD parts are
visible - the glowing orb, thin neon rings, text and buttons.

How it works on Windows (tkinter):
    root.attributes("-transparentcolor", "#000001")
Every pixel painted in exactly that colour becomes see-through.
So the window background and every canvas / frame that should
disappear is painted in that colour, and only the HUD drawings
(rings, orb, text, buttons) are painted in other colours.

Important limits, stated honestly:
- "-transparentcolor" works on Windows. It does NOT work on
  Linux or macOS - there it raises TclError, and this helper
  falls back to a normal dark window (with slight -alpha).
  The code checks for that, so the same file runs on all three.
- Pixels made transparent this way are click-through on
  Windows: you can only grab / click the visible HUD parts
  (the orb itself), not the empty space around it.
- Tkinter widgets (buttons, text boxes) cannot be per-pixel
  transparent. They stay as small solid HUD panels, which is
  fine - they are the controls. Only the empty background
  between them disappears.
- Do NOT use a colour from the HUD palette as the key colour.
  The key here is "#000001" (near-black), which no HUD element
  uses, so nothing visible accidentally vanishes.
"""
import os
import tkinter as tk

TRANSPARENT_KEY = "#000001"

# HUD palette (shared so orb and window match).
NEON = "#00e5ff"
NEON_PINK = "#ff2e6e"
NEON_GREEN = "#39ff88"
DARK_BG = "#050a14"
PANEL = "#0b1626"


def make_window_transparent(root, key=TRANSPARENT_KEY):
    """Try to make `key`-coloured pixels see-through.
    Returns True if transparency is active, False if the platform
    does not support it (then the caller should use a solid dark
    background instead). Never raises."""
    try:
        root.attributes("-transparentcolor", key)
        return True
    except Exception:
        # Linux / macOS: -transparentcolor is not supported.
        try:
            root.attributes("-alpha", 0.96)
        except Exception:
            pass
        return False


def load_logo_transparent(path, size):
    """Load logo.png with its black background made transparent,
    so the logo floats on the see-through background instead of
    sitting in a black square. Returns a PhotoImage, or None."""
    try:
        from PIL import Image, ImageTk
        img = Image.open(path).convert("RGBA")
        data = img.getdata()
        new_data = []
        for r, g, b, a in data:
            # Near-black pixels (the logo's background) -> invisible.
            if r < 24 and g < 24 and b < 24:
                new_data.append((r, g, b, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)
        img = img.resize((size, size), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def is_windows():
    import platform
    return platform.system() == "Windows"

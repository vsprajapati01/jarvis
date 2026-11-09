#!/usr/bin/env python3
"""
Jarvis overlay v8 - the small floating icon version, transparent HUD.
No big window, no clicking needed. The background is empty /
see-through, so you see your Windows desktop behind it - only
the glowing orb, thin neon rings, and text are visible.

Run it:
    python jarvis_overlay.py
    python jarvis_overlay.py --no-listen   (test the look without a mic)

What it does:
- A small glowing orb sits on the right edge of your screen, always on top.
- The window background is transparent (Windows: -transparentcolor),
  so the desktop shows through. On Linux / macOS the same code
  falls back to a dark window - transparency is a Windows feature.
- It is always listening for "jarvis" - you never click anything.
- Say "jarvis" and the orb glows bright cyan and pulses, so you know
  it heard you and is listening for your command.
- Say your command, Jarvis does it and speaks, then the orb goes
  back to dim, waiting again.
- Double-click the orb to open the full Jarvis window.
- Right-click the orb for: Show window / Hide / Quit.
- Drag the orb itself to move it (the see-through space around
  the orb is click-through on Windows, so grab the orb, not the
  empty space).

Commands are the same as the full Jarvis: time, weather Gainesville,
open chrome, open youtube.com, find companies hiring data analysts
in USA, create word my notes : hello, research <topic>, and so on.
Say "show window" to open the full app, "hide" to go back to just
the orb.

Hardware note: this uses your laptop's built-in microphone and the
same voice listening Jarvis already uses. No new tech is required
to run it. If the mic struggles to hear you from across the room,
a cheap USB microphone or a headset mic will hear the wake word
far better - that is the only upgrade worth buying, and only if
the built-in mic proves unreliable in your room.
"""
import math
import os
import sys
import threading
import tkinter as tk

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from jarvis import CONFIG, WAKE_WORD, handle_command, listen_voice, speak
from transparent_ui import (
    NEON,
    NEON_PINK,
    TRANSPARENT_KEY,
    load_logo_transparent,
    make_window_transparent,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

IDLE_COLOR = "#0a2a33"
GLOW_COLOR = "#00e5ff"
LISTEN_COLOR = "#ff2e6e"


class Overlay:
    def __init__(self, no_listen=False):
        self.root = tk.Tk()
        self.root.title("Jarvis")
        self.root.overrideredirect(True)          # no title bar, no big window
        self.root.attributes("-topmost", True)    # always on top
        # --- v8 transparent HUD: empty background, desktop shows through.
        # On Windows this makes every TRANSPARENT_KEY pixel see-through.
        # Elsewhere it returns False and we fall back to a dark window.
        self.transparent = make_window_transparent(self.root)
        bg = TRANSPARENT_KEY if self.transparent else "#050a14"
        if not self.transparent:
            self.root.attributes("-alpha", 0.92)
        self.root.configure(bg=bg)
        self.size = 168
        # Right edge, middle of the screen.
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = sw - self.size - 8
        y = sh // 2 - self.size // 2
        self.root.geometry(f"{self.size}x{self.size}+{x}+{y}")
        self.state = "idle"  # idle | listening | working
        self.pulse = 0
        self.pulse_dir = 1
        self.ring_angle = 0.0

        self.canvas = tk.Canvas(self.root, width=self.size, height=self.size,
                                highlightthickness=0, bg=bg)
        self.canvas.pack()
        cx = cy = self.size // 2
        # HUD rings: thin neon outer ring + two rotating arcs.
        self.ring = self.canvas.create_oval(8, 8, self.size - 8, self.size - 8,
                                            outline=NEON, width=2)
        self.arc1 = self.canvas.create_arc(14, 14, self.size - 14, self.size - 14,
                                           start=0, extent=110, style="arc",
                                           outline=NEON, width=3)
        self.arc2 = self.canvas.create_arc(20, 20, self.size - 20, self.size - 20,
                                           start=180, extent=70, style="arc",
                                           outline=NEON_PINK, width=2)
        # Orb: concentric circles, so it glows without a solid box.
        self.orb = self.canvas.create_oval(34, 34, self.size - 34, self.size - 34,
                                           fill=IDLE_COLOR, outline=NEON, width=2)
        self.orb_core = self.canvas.create_oval(cx - 16, cy - 16, cx + 16, cy + 16,
                                                fill=NEON, outline="")
        # Logo in the middle, black background made transparent so it
        # floats on the desktop; otherwise a neon "J".
        self.logo_img = None
        if os.path.exists(LOGO_PATH):
            self.logo_img = load_logo_transparent(LOGO_PATH, 44)
        if self.logo_img is not None:
            self.canvas.create_image(cx, cy, image=self.logo_img)
        else:
            self.canvas.create_text(cx, cy, text="J", font=("Segoe UI", 26, "bold"),
                                    fill="#04121c")
        self.label = self.canvas.create_text(
            cx, self.size - 8, text="", font=("Segoe UI", 8, "bold"),
            fill=NEON)

        # Drag the orb itself to move (transparent space is click-through
        # on Windows). Double-click to open the full window.
        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<Double-Button-1>", lambda e: self.show_window())
        self.canvas.bind("<Button-3>", self._menu)
        self._drag_x = 0
        self._drag_y = 0

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Show full Jarvis window", command=self.show_window)
        self.menu.add_command(label="Hide (orb stays)", command=lambda: None)
        self.menu.add_separator()
        self.menu.add_command(label="Quit Jarvis", command=self.quit)

        self.gui_process = None
        self._animate()
        if no_listen:
            return
        # Always-listening loop in the background, so the orb never freezes.
        threading.Thread(target=self._listen_loop, daemon=True).start()
        # Task queue from Pax: check GitHub every 60 seconds for a new
        # task you sent me in chat. Safe commands only, see task_queue.py.
        threading.Thread(target=self._task_loop, daemon=True).start()

    def _task_loop(self):
        import time
        try:
            from task_queue import check_for_new_tasks
        except Exception:
            return
        while True:
            try:
                check_for_new_tasks(handle_command, speak)
            except Exception:
                pass
            time.sleep(60)

    # -- orb appearance -------------------------------------------------
    def set_state(self, state, text=""):
        self.state = state
        self.root.after(0, self._apply_state, state, text)

    def _apply_state(self, state, text):
        if state == "listening":
            self.canvas.itemconfig(self.orb, fill=LISTEN_COLOR, outline="#ffffff", width=3)
            self.canvas.itemconfig(self.orb_core, fill="#ffffff")
            self.canvas.itemconfig(self.ring, outline="#ffffff")
            self.canvas.itemconfig(self.label, text="LISTENING")
        elif state == "working":
            self.canvas.itemconfig(self.orb, fill="#003a4d", outline=GLOW_COLOR, width=3)
            self.canvas.itemconfig(self.orb_core, fill=GLOW_COLOR)
            self.canvas.itemconfig(self.ring, outline=GLOW_COLOR)
            self.canvas.itemconfig(self.label, text="WORKING")
        else:
            self.canvas.itemconfig(self.orb, fill=IDLE_COLOR, outline=GLOW_COLOR, width=2)
            self.canvas.itemconfig(self.orb_core, fill=GLOW_COLOR)
            self.canvas.itemconfig(self.ring, outline=GLOW_COLOR)
            self.canvas.itemconfig(self.label, text="")

    def _animate(self):
        # Rotating HUD arcs, always turning slowly; faster + pulsing
        # ring when listening, so you can see it is awake.
        self.ring_angle = (self.ring_angle + (6 if self.state == "listening" else 1.5)) % 360
        self.canvas.itemconfig(self.arc1, start=self.ring_angle)
        self.canvas.itemconfig(self.arc2, start=(-self.ring_angle * 1.6) % 360)
        if self.state == "listening":
            self.pulse += self.pulse_dir * 3
            if self.pulse > 12 or self.pulse < 0:
                self.pulse_dir *= -1
            w = 3 + self.pulse // 6
            self.canvas.itemconfig(self.orb, width=w)
            self.canvas.itemconfig(self.ring, width=3)
        else:
            self.canvas.itemconfig(self.ring, width=2)
        self.root.after(120, self._animate)

    # -- window controls ------------------------------------------------
    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag(self, event):
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def show_window(self):
        import subprocess, sys
        try:
            subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "jarvis_gui.py")])
        except Exception as e:
            print(f"Could not open the full window: {e}")

    def quit(self):
        self.root.destroy()

    # -- always listening ----------------------------------------------
    def _listen_loop(self):
        speak("Jarvis overlay ready. Say jarvis, and I will listen.")
        while True:
            try:
                heard = listen_voice()
            except Exception:
                continue
            if heard is None:
                # No voice library / no mic here - wait a bit, don't spin.
                import time as _time
                _time.sleep(1)
                continue
            if not heard:
                continue
            print(f"Heard: {heard}")
            if WAKE_WORD not in heard.lower():
                continue
            # Wake word heard: glow, then listen for the command.
            self.set_state("listening")
            speak("Yes?")
            command = listen_voice()
            if not command:
                self.set_state("idle")
                continue
            print(f"Command: {command}")
            if command.strip().lower() in ("show window", "open window", "show jarvis"):
                self.show_window()
                self.set_state("idle")
                continue
            if command.strip().lower() in ("hide", "go away", "minimise", "minimize"):
                self.set_state("idle")
                continue
            self.set_state("working")
            try:
                keep = handle_command(command)
            except Exception as e:
                speak(f"Sorry, that failed: {e}")
                keep = True
            self.set_state("idle")
            if keep is False:
                self.root.after(0, self.quit)
                return

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    # --no-listen: show the orb without the microphone, so you can
    # check the transparent look on screen without voice running.
    Overlay(no_listen="--no-listen" in sys.argv).run()

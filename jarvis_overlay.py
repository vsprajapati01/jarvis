#!/usr/bin/env python3
"""
Jarvis overlay - the small floating icon version.
No big window, no clicking needed.

Run it:
    python jarvis_overlay.py

What it does:
- A small glowing orb sits on the right edge of your screen, always on top.
- It is always listening for "jarvis" - you never click anything.
- Say "jarvis" and the orb glows bright cyan and pulses, so you know
  it heard you and is listening for your command.
- Say your command, Jarvis does it and speaks, then the orb goes
  back to dim, waiting again.
- Double-click the orb to open the full Jarvis window.
- Right-click the orb for: Show window / Hide / Quit.
- Drag the orb anywhere you want it on the screen edge.

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
import os
import threading
import tkinter as tk

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from jarvis import CONFIG, WAKE_WORD, handle_command, listen_voice, speak

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

IDLE_COLOR = "#0a2a33"
GLOW_COLOR = "#00e5ff"
LISTEN_COLOR = "#ff2e6e"


class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Jarvis")
        self.root.overrideredirect(True)          # no title bar, no big window
        self.root.attributes("-topmost", True)    # always on top
        self.root.attributes("-alpha", 0.92)
        self.size = 96
        # Right edge, middle of the screen.
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = sw - self.size - 8
        y = sh // 2 - self.size // 2
        self.root.geometry(f"{self.size}x{self.size}+{x}+{y}")
        self.state = "idle"  # idle | listening | working
        self.pulse = 0
        self.pulse_dir = 1

        self.canvas = tk.Canvas(self.root, width=self.size, height=self.size,
                                highlightthickness=0, bg="#050a14")
        self.canvas.pack()
        # Orb
        self.orb = self.canvas.create_oval(10, 10, self.size - 10, self.size - 10,
                                           fill=IDLE_COLOR, outline="#00e5ff", width=2)
        # Lion logo in the middle if we have it, otherwise a mic symbol.
        self.logo_img = None
        if PIL_AVAILABLE and os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH).resize((56, 56))
                self.logo_img = ImageTk.PhotoImage(img)
                self.canvas.create_image(self.size // 2, self.size // 2,
                                         image=self.logo_img)
            except Exception:
                self.canvas.create_text(self.size // 2, self.size // 2,
                                        text="🎤", font=("Segoe UI", 28), fill="#00e5ff")
        else:
            self.canvas.create_text(self.size // 2, self.size // 2,
                                    text="🎤", font=("Segoe UI", 28), fill="#00e5ff")
        self.label = self.canvas.create_text(
            self.size // 2, self.size - 6, text="", font=("Segoe UI", 7),
            fill="#00e5ff")

        # Drag to move, double-click to open the full window.
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
        # Always-listening loop in the background, so the orb never freezes.
        threading.Thread(target=self._listen_loop, daemon=True).start()

    # -- orb appearance -------------------------------------------------
    def set_state(self, state, text=""):
        self.state = state
        self.root.after(0, self._apply_state, state, text)

    def _apply_state(self, state, text):
        if state == "listening":
            self.canvas.itemconfig(self.orb, fill=LISTEN_COLOR, outline="#ffffff", width=3)
            self.canvas.itemconfig(self.label, text="LISTENING")
        elif state == "working":
            self.canvas.itemconfig(self.orb, fill="#003a4d", outline=GLOW_COLOR, width=3)
            self.canvas.itemconfig(self.label, text="WORKING")
        else:
            self.canvas.itemconfig(self.orb, fill=IDLE_COLOR, outline=GLOW_COLOR, width=2)
            self.canvas.itemconfig(self.label, text="")

    def _animate(self):
        # Gentle pulse when listening, so you can see it is awake.
        if self.state == "listening":
            self.pulse += self.pulse_dir * 3
            if self.pulse > 12 or self.pulse < 0:
                self.pulse_dir *= -1
            w = 3 + self.pulse // 6
            self.canvas.itemconfig(self.orb, width=w)
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
    Overlay().run()

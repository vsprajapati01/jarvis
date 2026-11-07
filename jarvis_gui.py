#!/usr/bin/env python3
"""
Jarvis Desktop App v3 - AI UI + double-clap wake.
A futuristic AI window: glowing orb, waveform, neon cyan on dark.

Run on Windows:
    pip install -r requirements.txt
    python jarvis_gui.py

Build a .exe on Windows:
    build_exe.bat   ->  dist\\Jarvis.exe

Wake Jarvis in this version:
- Press "👏 Double-clap mode" and clap twice - it runs the morning
  workflow (time, weather, today's focus, top jobs) and then listens.
- Or press "🎤 Listen" and say "jarvis", then your command.
- Or just type in the command box, no mic needed.

Left sidebar: lion logo. Apps open/close. PC controls: volume, lock,
sleep, brightness, shutdown, restart (shutdown/restart ask first).
"""
import io
import contextlib
import math
import os
import random
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jarvis as core
from clap_detector import start_clap_detector
from morning_workflow import run_morning_workflow

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_PNG = os.path.join(HERE, "logo.png")

BG = "#050a14"
PANEL = "#0b1626"
PANEL2 = "#101f33"
NEON = "#00e5ff"
NEON2 = "#ff2e6e"
TEXT = "#e8f6ff"
DIM = "#7fa8c9"

APPS = {
    "Chrome": ("start chrome", "chrome.exe"),
    "Edge": ("start msedge", "msedge.exe"),
    "VS Code": ("code", "Code.exe"),
    "Notepad": ("notepad", "notepad.exe"),
    "Calculator": ("calc", "CalculatorApp.exe"),
    "File Explorer": ("explorer", "explorer.exe"),
    "Paint": ("mspaint", "mspaint.exe"),
    "Task Manager": ("taskmgr", "Taskmgr.exe"),
    "Settings": ("start ms-settings:", None),
    "Spotify": ("start spotify", "Spotify.exe"),
}


def run_cmd(cmd):
    try:
        subprocess.Popen(cmd, shell=True)
        return True
    except Exception:
        return False


class JarvisApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JARVIS  •  AI")
        self.geometry("960x640")
        self.configure(bg=BG)
        try:
            self.iconbitmap(os.path.join(HERE, "logo.ico"))
        except Exception:
            pass
        self.listening = False
        self.clap_on = False
        self.clap_detector = None
        self.orb_phase = 0.0

        # --- sidebar ---
        side = tk.Frame(self, bg=PANEL, width=230)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        self.logo_img = None
        if os.path.exists(LOGO_PNG):
            try:
                from PIL import Image, ImageTk
                img = Image.open(LOGO_PNG).resize((150, 150))
                self.logo_img = ImageTk.PhotoImage(img)
                tk.Label(side, image=self.logo_img, bg=PANEL).pack(pady=(16, 6))
            except Exception:
                tk.Label(side, text="🦁", font=("Segoe UI", 56), bg=PANEL, fg="#ffb347").pack(pady=(16, 6))
        else:
            tk.Label(side, text="🦁", font=("Segoe UI", 56), bg=PANEL, fg="#ffb347").pack(pady=(16, 6))

        tk.Label(side, text="JARVIS", font=("Segoe UI", 24, "bold"), bg=PANEL, fg=NEON).pack()
        tk.Label(side, text="●  AI CORE ONLINE", font=("Segoe UI", 9, "bold"), bg=PANEL, fg="#39ff88").pack(pady=(2, 14))

        # AI orb - pulsing rings, drawn on a canvas
        self.orb = tk.Canvas(side, width=180, height=110, bg=PANEL, highlightthickness=0)
        self.orb.pack(pady=4)
        self.wave = tk.Canvas(side, width=180, height=36, bg=PANEL, highlightthickness=0)
        self.wave.pack(pady=4)

        def neon_btn(parent, text, cmd, bg=NEON, fg="#04121c"):
            return tk.Button(parent, text=text, font=("Segoe UI", 11, "bold"),
                             bg=bg, fg=fg, relief="flat", padx=10, pady=10, command=cmd)

        neon_btn(side, "👏  Double-clap mode", self.toggle_clap).pack(fill="x", padx=16, pady=4)
        neon_btn(side, "🎤  Listen  (say jarvis)", self.listen_voice, bg=NEON2, fg="white").pack(fill="x", padx=16, pady=4)
        neon_btn(side, "☀️  Morning workflow", self.morning, bg=PANEL2, fg=TEXT).pack(fill="x", padx=16, pady=4)
        self.status = tk.Label(side, text="Ready — clap twice, or type below",
                               font=("Segoe UI", 9), bg=PANEL, fg=DIM, wraplength=190)
        self.status.pack(side="bottom", pady=14)
        self._animate_orb()

        # --- main ---
        main = tk.Frame(self, bg=BG)
        main.pack(side="right", fill="both", expand=True, padx=14, pady=12)

        tk.Label(main, text="JARVIS  //  COMMAND", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=NEON, anchor="w").pack(fill="x")
        self.log = tk.Text(main, height=11, bg=PANEL, fg=TEXT, font=("Consolas", 10),
                           wrap="word", relief="flat", insertbackground=NEON)
        self.log.pack(fill="x", pady=(6, 8))
        self.log.insert("end", "JARVIS: Hello. Clap twice for your morning workflow, say 'jarvis' to wake me, or type a command below.\n")
        self.log.config(state="disabled")

        row = tk.Frame(main, bg=BG)
        row.pack(fill="x")
        self.entry = tk.Entry(row, font=("Segoe UI", 11), bg=PANEL, fg=TEXT,
                              insertbackground=NEON, relief="flat")
        self.entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self.send_text())
        tk.Button(row, text="▶  RUN", font=("Segoe UI", 11, "bold"), bg=NEON, fg="#04121c",
                  relief="flat", padx=18, pady=6, command=self.send_text).pack(side="right")

        tk.Label(main, text="APPS  —  open / close", font=("Segoe UI", 11, "bold"),
                 bg=BG, fg=NEON, anchor="w").pack(fill="x", pady=(14, 6))
        apps = tk.Frame(main, bg=BG)
        apps.pack(fill="x")
        for i, name in enumerate(APPS):
            tk.Button(apps, text=f"▶ {name}", font=("Segoe UI", 9), bg=PANEL2, fg=TEXT,
                      relief="flat", padx=8, pady=6,
                      command=lambda n=name: self.open_app(n)).grid(
                          row=i // 5, column=i % 5, padx=3, pady=3, sticky="ew")
        close_row = tk.Frame(main, bg=BG)
        close_row.pack(fill="x", pady=(4, 0))
        tk.Label(close_row, text="Close:", font=("Segoe UI", 9), bg=BG, fg=DIM).pack(side="left")
        for name in APPS:
            if APPS[name][1] is None:
                continue
            tk.Button(close_row, text=name, font=("Segoe UI", 8), bg="#2a1420", fg="#ffb3c2",
                      relief="flat", padx=6, pady=4,
                      command=lambda n=name: self.close_app(n)).pack(side="left", padx=2)

        tk.Label(main, text="PC CONTROLS", font=("Segoe UI", 11, "bold"),
                 bg=BG, fg=NEON, anchor="w").pack(fill="x", pady=(14, 6))
        pc = tk.Frame(main, bg=BG)
        pc.pack(fill="x")
        controls = [
            ("🔊 Vol +", lambda: self.volume(175)),
            ("🔉 Vol −", lambda: self.volume(174)),
            ("🔇 Mute", lambda: self.volume(173)),
            ("🔒 Lock", lambda: run_cmd("rundll32.exe user32.dll,LockWorkStation")),
            ("😴 Sleep", lambda: run_cmd("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")),
            ("🔆 Bright +", lambda: self.brightness(10)),
            ("🔅 Bright −", lambda: self.brightness(-10)),
            ("⏻ Shutdown", self.shutdown),
            ("↻ Restart", self.restart),
        ]
        for i, (label, fn) in enumerate(controls):
            tk.Button(pc, text=label, font=("Segoe UI", 9), bg=PANEL2, fg=TEXT,
                      relief="flat", padx=8, pady=6, command=fn).grid(
                          row=i // 5, column=i % 5, padx=3, pady=3, sticky="ew")

    # --- AI orb / waveform animation ---
    def _animate_orb(self):
        self.orb_phase += 0.12
        c = self.orb
        c.delete("all")
        cx, cy = 90, 55
        for i in range(3):
            r = 22 + i * 12 + math.sin(self.orb_phase + i) * 5
            alpha = 255 - i * 70
            color = "#00e5ff" if i % 2 == 0 else "#ff2e6e"
            c.create_oval(cx - r, cy - r * 0.7, cx + r, cy + r * 0.7,
                          outline=color, width=2)
        c.create_oval(cx - 12, cy - 12, cx + 12, cy + 12, fill=NEON, outline="")
        # waveform bars
        w = self.wave
        w.delete("all")
        for i in range(24):
            h = 6 + abs(math.sin(self.orb_phase * 2 + i * 0.7)) * (22 if self.listening else 10)
            x = 6 + i * 7
            w.create_rectangle(x, 18 - h / 2, x + 4, 18 + h / 2, fill=NEON, outline="")
        self.after(120, self._animate_orb)

    def say(self, text):
        self.log.config(state="normal")
        self.log.insert("end", f"JARVIS: {text}\n")
        self.log.config(state="disabled")
        self.log.see("end")
        self.status.config(text="Ready — clap twice, or type below")
        self.listening = False

    def run_text(self, command):
        self.log.config(state="normal")
        self.log.insert("end", f"You: {command}\n")
        self.log.config(state="disabled")
        self.status.config(text="Working…")
        self.listening = True
        def _work():
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                core.handle_command(command)
            out = buf.getvalue().strip()
            reply = out.replace("JARVIS: ", "", 1).replace("Jarvis: ", "", 1) if out else "Done."
            self.after(0, lambda: self.say(reply))
        threading.Thread(target=_work, daemon=True).start()

    def send_text(self):
        cmd = self.entry.get().strip()
        if not cmd:
            return
        self.entry.delete(0, "end")
        self.run_text(cmd)

    def morning(self):
        self.status.config(text="Morning workflow…")
        self.listening = True
        def _work():
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                text = run_morning_workflow()
            self.after(0, lambda: self.say(text))
        threading.Thread(target=_work, daemon=True).start()

    def _on_double_clap(self):
        # Runs in the detector thread - hand back to the GUI thread.
        self.after(0, self.morning)

    def toggle_clap(self):
        if self.clap_on:
            if self.clap_detector:
                self.clap_detector.stop()
            self.clap_on = False
            self.status.config(text="Double-clap mode OFF")
            self.say("Double-clap mode off.")
            return
        self.clap_detector = start_clap_detector(self._on_double_clap)
        self.clap_on = True
        self.status.config(text="Listening for double clap…")
        self.say("Double-clap mode on. Clap twice and I will run your morning workflow.")

    def listen_voice(self):
        self.status.config(text="Listening… say 'jarvis' first")
        self.listening = True
        self.say("Listening… say 'jarvis', then your command.")
        def _work():
            heard = core.listen_voice()
            if not heard:
                self.after(0, lambda: self.say("I didn't hear anything. Try again."))
                return
            self.after(0, lambda: self.say(f"Heard: {heard}"))
            if "jarvis" in heard.lower():
                self.after(0, lambda: self.say("Yes? Listening for your command…"))
                cmd = core.listen_voice()
                if cmd:
                    self.after(0, lambda: self.run_text(cmd))
        threading.Thread(target=_work, daemon=True).start()

    def open_app(self, name):
        cmd, _ = APPS[name]
        self.say(f"Opening {name}." if run_cmd(cmd) else f"Could not open {name}.")

    def close_app(self, name):
        _, proc = APPS[name]
        if not proc:
            self.say(f"{name} can't be closed from here.")
            return
        run_cmd(f"taskkill /IM {proc} /F")
        self.say(f"Closing {name}.")

    def volume(self, key):
        run_cmd(f'powershell -c "$w = New-Object -ComObject WScript.Shell; $w.SendKeys([char]{key})"')
        self.say("Volume changed.")

    def brightness(self, delta):
        ps = ("$m = Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods; "
              "$b = (Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness; "
              f"$n = [Math]::Max(10, [Math]::Min(100, $b + {delta})); $m.WmiSetBrightness(1, $n)")
        run_cmd(f'powershell -c "{ps}"')
        self.say("Brightness changed.")

    def shutdown(self):
        if messagebox.askyesno("Shutdown", "Shut down this PC now?"):
            run_cmd("shutdown /s /t 5")

    def restart(self):
        if messagebox.askyesno("Restart", "Restart this PC now?"):
            run_cmd("shutdown /r /t 5")


if __name__ == "__main__":
    JarvisApp().mainloop()

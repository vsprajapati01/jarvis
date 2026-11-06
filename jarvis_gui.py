#!/usr/bin/env python3
"""
Jarvis Desktop App v2 - Windows .exe ready.
A window with the lion logo on the left, app manager and PC controls.

Run on Windows:
    pip install -r requirements.txt
    python jarvis_gui.py

Build a .exe on Windows (must be built on Windows, not on Linux/Mac):
    pip install pyinstaller
    build_exe.bat
    -> dist/Jarvis.exe  (double-click to run, logo.ico is the app icon)

In the app:
- Left sidebar: logo, Jarvis name, Listen button, status.
- Middle: command box - type time, date, weather Gainesville, search <thing>,
  timer 5 minutes, remind me to drink water in 10 minutes, note <text>, help.
- Right / bottom: Apps - open and close apps. PC - volume, lock, sleep,
  shutdown, restart, brightness.
"""
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jarvis as core

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_PNG = os.path.join(HERE, "logo.png")

# Windows app shortcuts: name -> (open command, process name to close)
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
    """Run a Windows shell command in the background, return True/False."""
    try:
        subprocess.Popen(cmd, shell=True)
        return True
    except Exception:
        return False


class JarvisApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jarvis")
        self.geometry("900x600")
        self.configure(bg="#14101a")
        try:
            self.iconbitmap(os.path.join(HERE, "logo.ico"))
        except Exception:
            pass

        # --- left sidebar with logo ---
        sidebar = tk.Frame(self, bg="#1e1626", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self.logo_img = None
        if os.path.exists(LOGO_PNG):
            try:
                from PIL import Image, ImageTk
                img = Image.open(LOGO_PNG).resize((160, 160))
                self.logo_img = ImageTk.PhotoImage(img)
                tk.Label(sidebar, image=self.logo_img, bg="#1e1626").pack(pady=(18, 8))
            except Exception:
                tk.Label(sidebar, text="🦁", font=("Segoe UI", 64), bg="#1e1626", fg="#ffb347").pack(pady=(18, 8))
        else:
            tk.Label(sidebar, text="🦁", font=("Segoe UI", 64), bg="#1e1626", fg="#ffb347").pack(pady=(18, 8))

        tk.Label(sidebar, text="JARVIS", font=("Segoe UI", 22, "bold"), bg="#1e1626", fg="white").pack()
        tk.Label(sidebar, text="Your PC assistant", font=("Segoe UI", 10), bg="#1e1626", fg="#c9b8d6").pack(pady=(0, 16))

        tk.Button(sidebar, text="🎤  Listen (voice)", font=("Segoe UI", 11, "bold"),
                  bg="#ff2e6e", fg="white", relief="flat", padx=10, pady=10,
                  command=self.listen_voice).pack(fill="x", padx=16, pady=4)
        tk.Button(sidebar, text="⏱  Timer 5 min", font=("Segoe UI", 10),
                  bg="#2a2133", fg="white", relief="flat", padx=10, pady=8,
                  command=lambda: self.run_text("timer 5 minutes")).pack(fill="x", padx=16, pady=4)
        tk.Button(sidebar, text="🌤  Weather", font=("Segoe UI", 10),
                  bg="#2a2133", fg="white", relief="flat", padx=10, pady=8,
                  command=lambda: self.run_text("weather Gainesville")).pack(fill="x", padx=16, pady=4)
        self.status = tk.Label(sidebar, text="Ready", font=("Segoe UI", 9),
                               bg="#1e1626", fg="#8be08b", wraplength=180)
        self.status.pack(side="bottom", pady=16)

        # --- main area ---
        main = tk.Frame(self, bg="#14101a")
        main.pack(side="right", fill="both", expand=True, padx=12, pady=12)

        tk.Label(main, text="Ask Jarvis", font=("Segoe UI", 13, "bold"),
                 bg="#14101a", fg="white", anchor="w").pack(fill="x")
        self.log = tk.Text(main, height=12, bg="#211a2b", fg="#f0e8f5",
                           font=("Segoe UI", 10), wrap="word", relief="flat")
        self.log.pack(fill="x", pady=(6, 8))
        self.log.insert("end", "Jarvis: Hello, I am Jarvis. Type a command below, or press Listen and speak.\n")
        self.log.config(state="disabled")

        entry_row = tk.Frame(main, bg="#14101a")
        entry_row.pack(fill="x")
        self.entry = tk.Entry(entry_row, font=("Segoe UI", 11), bg="#211a2b", fg="white",
                              insertbackground="white", relief="flat")
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self.send_text())
        tk.Button(entry_row, text="Send", font=("Segoe UI", 11, "bold"),
                  bg="#ff2e6e", fg="white", relief="flat", padx=16, pady=6,
                  command=self.send_text).pack(side="right")

        # --- apps ---
        tk.Label(main, text="Apps — open / close", font=("Segoe UI", 11, "bold"),
                 bg="#14101a", fg="white", anchor="w").pack(fill="x", pady=(14, 6))
        apps_frame = tk.Frame(main, bg="#14101a")
        apps_frame.pack(fill="x")
        for i, name in enumerate(APPS):
            btn = tk.Button(apps_frame, text=f"▶ {name}", font=("Segoe UI", 9),
                            bg="#2a2133", fg="white", relief="flat", padx=8, pady=6,
                            command=lambda n=name: self.open_app(n))
            btn.grid(row=i // 5, column=i % 5, padx=3, pady=3, sticky="ew")
            close = tk.Button(apps_frame, text="✕", font=("Segoe UI", 9),
                              bg="#3a2a33", fg="#ffb3c2", relief="flat", padx=6, pady=6,
                              command=lambda n=name: self.close_app(n))
            close.grid(row=i // 5, column=10, padx=1, pady=3) if False else None
        # close buttons row (one per app, in order)
        close_frame = tk.Frame(main, bg="#14101a")
        close_frame.pack(fill="x", pady=(4, 0))
        tk.Label(close_frame, text="Close:", font=("Segoe UI", 9), bg="#14101a", fg="#c9b8d6").pack(side="left")
        for name in APPS:
            if APPS[name][1] is None:
                continue
            tk.Button(close_frame, text=name, font=("Segoe UI", 8),
                      bg="#3a2a33", fg="#ffb3c2", relief="flat", padx=6, pady=4,
                      command=lambda n=name: self.close_app(n)).pack(side="left", padx=2)

        # --- PC controls ---
        tk.Label(main, text="PC controls", font=("Segoe UI", 11, "bold"),
                 bg="#14101a", fg="white", anchor="w").pack(fill="x", pady=(14, 6))
        pc = tk.Frame(main, bg="#14101a")
        pc.pack(fill="x")
        controls = [
            ("🔊 Volume +", lambda: self.volume(175)),
            ("🔉 Volume −", lambda: self.volume(174)),
            ("🔇 Mute", lambda: self.volume(173)),
            ("🔒 Lock PC", lambda: run_cmd("rundll32.exe user32.dll,LockWorkStation")),
            ("😴 Sleep", lambda: run_cmd("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")),
            ("🔆 Bright +", lambda: self.brightness(10)),
            ("🔅 Bright −", lambda: self.brightness(-10)),
            ("⏻ Shutdown", self.shutdown),
            ("↻ Restart", self.restart),
        ]
        for i, (label, fn) in enumerate(controls):
            tk.Button(pc, text=label, font=("Segoe UI", 9), bg="#2a2133", fg="white",
                      relief="flat", padx=8, pady=6, command=fn).grid(
                          row=i // 5, column=i % 5, padx=3, pady=3, sticky="ew")

    def say(self, text):
        self.log.config(state="normal")
        self.log.insert("end", f"Jarvis: {text}\n")
        self.log.config(state="disabled")
        self.log.see("end")
        self.status.config(text="Ready")

    def run_text(self, command):
        self.log.config(state="normal")
        self.log.insert("end", f"You: {command}\n")
        self.log.config(state="disabled")
        self.status.config(text="Working…")
        # Capture Jarvis's printed reply by running the command handler
        # in a thread, then show the result in the log.
        def _work():
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                core.handle_command(command)
            out = buf.getvalue().strip()
            # handle_command prints "Jarvis: ..." via speak()
            reply = out.replace("Jarvis: ", "", 1) if out.startswith("Jarvis: ") else out
            self.after(0, lambda: self.say(reply or "Done."))
        threading.Thread(target=_work, daemon=True).start()

    def send_text(self):
        cmd = self.entry.get().strip()
        if not cmd:
            return
        self.entry.delete(0, "end")
        self.run_text(cmd)

    def listen_voice(self):
        self.status.config(text="Listening… say 'jarvis' first")
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
        if run_cmd(cmd):
            self.say(f"Opening {name}.")
        else:
            self.say(f"Could not open {name}.")

    def close_app(self, name):
        _, proc = APPS[name]
        if not proc:
            self.say(f"{name} can't be closed from here.")
            return
        run_cmd(f"taskkill /IM {proc} /F")
        self.say(f"Closing {name}.")

    def volume(self, key):
        # Windows virtual key: 173 mute, 174 vol down, 175 vol up
        run_cmd(f'powershell -c "$w = New-Object -ComObject WScript.Shell; $w.SendKeys([char]{key})"')
        self.say("Volume changed.")

    def brightness(self, delta):
        # Windows brightness via WMI, 0-100
        ps = (
            "$m = Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods; "
            "$b = (Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness; "
            f"$n = [Math]::Max(10, [Math]::Min(100, $b + {delta})); "
            "$m.WmiSetBrightness(1, $n)"
        )
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

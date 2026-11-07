#!/usr/bin/env python3
"""
Double-clap detector for Jarvis.
Listens to the microphone and calls `on_double_clap` when it hears
two loud, short sounds (claps) close together, instead of a wake word.

How it works: read mic audio in small chunks, measure loudness (RMS).
A clap is a chunk much louder than the room's background level.
Two claps 0.25-1.0 seconds apart = a double clap.

Needs: PyAudio (already in requirements.txt)
Run alone to test:  python clap_detector.py
  Clap twice, it prints "DOUBLE CLAP!" each time it hears one.
"""
import math
import struct
import threading
import time

try:
    import pyaudio
except ImportError:
    pyaudio = None

CHUNK = 1024
RATE = 16000
# A clap must be this many times louder than background to count.
THRESHOLD_RATIO = 4.0
MIN_GAP = 0.25   # seconds between the two claps
MAX_GAP = 1.0    # seconds between the two claps


def _rms(data):
    if not data:
        return 0.0
    count = len(data) // 2
    samples = struct.unpack(f"<{count}h", data[: count * 2])
    return math.sqrt(sum(s * s for s in samples) / max(count, 1))


class ClapDetector(threading.Thread):
    def __init__(self, on_double_clap, threshold_ratio=THRESHOLD_RATIO):
        super().__init__(daemon=True)
        self.on_double_clap = on_double_clap
        self.threshold_ratio = threshold_ratio
        self.running = True
        self._last_clap = 0.0
        self._background = 0.0

    def stop(self):
        self.running = False

    def run(self):
        if pyaudio is None:
            print("Clap detector needs PyAudio. Run: pip install -r requirements.txt")
            return
        audio = pyaudio.PyAudio()
        try:
            stream = audio.open(format=pyaudio.paInt16, channels=1,
                                rate=RATE, input=True,
                                frames_per_buffer=CHUNK)
        except Exception as e:
            print(f"Could not open microphone for clap detection: {e}")
            return
        print("Clap detector listening… clap twice to wake Jarvis.")
        # Learn the room's background level first (1 second).
        levels = []
        for _ in range(int(RATE / CHUNK)):
            levels.append(_rms(stream.read(CHUNK, exception_on_overflow=False)))
        self._background = max(sum(levels) / max(len(levels), 1), 1.0)

        while self.running:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception:
                break
            level = _rms(data)
            # Slowly adapt to the room getting louder/quieter.
            self._background = 0.98 * self._background + 0.02 * level
            if level > self._background * self.threshold_ratio and level > 800:
                now = time.time()
                gap = now - self._last_clap
                if MIN_GAP <= gap <= MAX_GAP:
                    self._last_clap = 0.0
                    print("DOUBLE CLAP!")
                    try:
                        self.on_double_clap()
                    except Exception as e:
                        print(f"Double-clap action failed: {e}")
                else:
                    self._last_clap = now
                # Ignore the echo/reverb right after a clap.
                time.sleep(0.12)
        stream.stop_stream()
        stream.close()
        audio.terminate()


def start_clap_detector(on_double_clap):
    """Start listening in the background. Returns the detector thread."""
    detector = ClapDetector(on_double_clap)
    detector.start()
    return detector


if __name__ == "__main__":
    def _demo():
        print("DOUBLE CLAP! (demo)")
    d = start_clap_detector(_demo)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        d.stop()
        print("\nStopped.")

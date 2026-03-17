"""Background monitoring threads for system stats, network, media, and input."""

from __future__ import annotations

import platform
import re
import subprocess
import time
from typing import Optional

import psutil
from PyQt5.QtCore import QThread, pyqtSignal


class SystemStatsMonitor(QThread):
    """Monitors CPU, GPU, and RAM usage at regular intervals."""

    stats_updated = pyqtSignal(dict)

    def __init__(self, interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self._interval = interval_ms / 1000.0
        self._running = True

    def run(self):
        # Prime the first cpu_percent call (returns 0.0 on first call)
        psutil.cpu_percent(interval=None)
        while self._running:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            gpu_pct = self._get_gpu_usage()

            self.stats_updated.emit({
                "cpu": cpu,
                "gpu": gpu_pct,
                "ram_used": mem.used / (1024 ** 3),
                "ram_total": mem.total / (1024 ** 3),
                "ram_percent": mem.percent,
            })
            time.sleep(self._interval)

    def _get_gpu_usage(self) -> Optional[float]:
        """Try to read GPU usage. Returns None if unavailable."""
        if platform.system() == "Windows":
            return self._get_gpu_windows()
        return self._get_gpu_linux()

    def _get_gpu_windows(self) -> Optional[float]:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                return float(result.stdout.strip().split("\n")[0])
        except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
            pass
        return None

    def _get_gpu_linux(self) -> Optional[float]:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0:
                return float(result.stdout.strip().split("\n")[0])
        except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
            pass
        return None

    def stop(self):
        self._running = False
        self.wait(2000)


class FPSMonitor(QThread):
    """Tracks overlay rendering FPS by measuring frame intervals."""

    fps_updated = pyqtSignal(int)

    def __init__(self, interval_ms: int = 500, parent=None):
        super().__init__(parent)
        self._interval = interval_ms / 1000.0
        self._running = True
        self._frame_count = 0
        self._last_time = time.perf_counter()

    def tick(self):
        """Call this each time the overlay repaints."""
        self._frame_count += 1

    def run(self):
        while self._running:
            time.sleep(self._interval)
            now = time.perf_counter()
            elapsed = now - self._last_time
            if elapsed > 0:
                fps = int(self._frame_count / elapsed)
                self.fps_updated.emit(fps)
            self._frame_count = 0
            self._last_time = now

    def stop(self):
        self._running = False
        self.wait(2000)


class NetworkMonitor(QThread):
    """Monitors network latency and throughput."""

    net_updated = pyqtSignal(dict)

    PING_TARGETS = ["8.8.8.8", "1.1.1.1"]

    def __init__(self, interval_ms: int = 3000, parent=None):
        super().__init__(parent)
        self._interval = interval_ms / 1000.0
        self._running = True
        self._last_bytes_sent = 0
        self._last_bytes_recv = 0
        self._last_time = 0.0

    def run(self):
        counters = psutil.net_io_counters()
        self._last_bytes_sent = counters.bytes_sent
        self._last_bytes_recv = counters.bytes_recv
        self._last_time = time.perf_counter()

        while self._running:
            ping = self._measure_ping()
            now = time.perf_counter()
            counters = psutil.net_io_counters()
            elapsed = now - self._last_time

            if elapsed > 0:
                upload = (counters.bytes_sent - self._last_bytes_sent) / elapsed
                download = (counters.bytes_recv - self._last_bytes_recv) / elapsed
            else:
                upload = download = 0.0

            self._last_bytes_sent = counters.bytes_sent
            self._last_bytes_recv = counters.bytes_recv
            self._last_time = now

            self.net_updated.emit({
                "ping": ping,
                "upload": upload,
                "download": download,
            })
            time.sleep(self._interval)

    def _measure_ping(self) -> Optional[float]:
        """Ping a reliable DNS server and return latency in ms."""
        for target in self.PING_TARGETS:
            try:
                if platform.system() == "Windows":
                    cmd = ["ping", "-n", "1", "-w", "1000", target]
                    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                else:
                    cmd = ["ping", "-c", "1", "-W", "1", target]
                    flags = 0

                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=3,
                    creationflags=flags,
                )
                if result.returncode == 0:
                    match = re.search(r"time[=<](\d+\.?\d*)", result.stdout)
                    if match:
                        return float(match.group(1))
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        return None

    def stop(self):
        self._running = False
        self.wait(5000)


class MediaDetector(QThread):
    """Detects currently playing media from window titles."""

    media_updated = pyqtSignal(dict)

    # Patterns to match media player window titles
    BROWSER_MEDIA_PATTERN = re.compile(
        r"^(.+?)\s*[-–—]\s*(YouTube|Spotify|SoundCloud|Apple Music|Deezer"
        r"|Tidal|Amazon Music|YouTube Music|Pandora)",
        re.IGNORECASE,
    )
    SPOTIFY_PATTERN = re.compile(r"^(.+?)\s*[-–—]\s*(.+?)$")
    MEDIA_KEYWORDS = [
        "spotify", "youtube", "music", "vlc", "media player",
        "foobar", "winamp", "itunes", "soundcloud", "deezer",
        "tidal", "amazon music", "pandora",
    ]

    def __init__(self, interval_ms: int = 2000, parent=None):
        super().__init__(parent)
        self._interval = interval_ms / 1000.0
        self._running = True

    def run(self):
        while self._running:
            media = self._detect_media()
            self.media_updated.emit(media)
            time.sleep(self._interval)

    def _detect_media(self) -> dict:
        """Scan running process window titles for media info."""
        result = {"playing": False, "title": "", "source": ""}
        try:
            if platform.system() == "Windows":
                return self._detect_windows()
            return self._detect_linux()
        except Exception:
            return result

    def _detect_windows(self) -> dict:
        result = {"playing": False, "title": "", "source": ""}
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            EnumWindows = user32.EnumWindows
            GetWindowTextW = user32.GetWindowTextW
            GetWindowTextLengthW = user32.GetWindowTextLengthW
            IsWindowVisible = user32.IsWindowVisible
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
            )

            titles = []

            def enum_cb(hwnd, _lparam):
                if IsWindowVisible(hwnd):
                    length = GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        GetWindowTextW(hwnd, buf, length + 1)
                        titles.append(buf.value)
                return True

            EnumWindows(WNDENUMPROC(enum_cb), 0)

            for title in titles:
                lower = title.lower()
                # Check for Spotify (format: "Artist - Song - Spotify")
                if "spotify" in lower and " - " in title:
                    parts = title.rsplit(" - ", 1)
                    if len(parts) >= 2 and "spotify" in parts[-1].lower():
                        return {
                            "playing": True,
                            "title": parts[0].strip(),
                            "source": "Spotify",
                        }

                # Check for YouTube / browser media
                match = self.BROWSER_MEDIA_PATTERN.match(title)
                if match:
                    return {
                        "playing": True,
                        "title": match.group(1).strip(),
                        "source": match.group(2).strip(),
                    }

                # Generic media player check
                for kw in self.MEDIA_KEYWORDS:
                    if kw in lower and " - " in title:
                        match = self.SPOTIFY_PATTERN.match(title)
                        if match:
                            return {
                                "playing": True,
                                "title": match.group(1).strip(),
                                "source": kw.title(),
                            }
        except Exception:
            pass
        return result

    def _detect_linux(self) -> dict:
        result = {"playing": False, "title": "", "source": ""}
        try:
            out = subprocess.run(
                ["wmctrl", "-l"], capture_output=True, text=True, timeout=2,
            )
            if out.returncode == 0:
                for line in out.stdout.splitlines():
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        title = parts[3]
                        lower = title.lower()
                        for kw in self.MEDIA_KEYWORDS:
                            if kw in lower and " - " in title:
                                m = self.SPOTIFY_PATTERN.match(title)
                                if m:
                                    return {
                                        "playing": True,
                                        "title": m.group(1).strip(),
                                        "source": kw.title(),
                                    }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return result

    def stop(self):
        self._running = False
        self.wait(3000)


class KeyboardMonitor(QThread):
    """Monitors keyboard input for the WASD + Space key visualizer."""

    key_pressed = pyqtSignal(str, bool)  # key_name, is_pressed

    TRACKED_KEYS = {"w", "a", "s", "d", "space"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._listener = None

    def run(self):
        from pynput import keyboard

        def on_press(key):
            name = self._get_key_name(key)
            if name in self.TRACKED_KEYS:
                self.key_pressed.emit(name, True)

        def on_release(key):
            name = self._get_key_name(key)
            if name in self.TRACKED_KEYS:
                self.key_pressed.emit(name, False)

        self._listener = keyboard.Listener(
            on_press=on_press, on_release=on_release
        )
        self._listener.start()
        while self._running:
            time.sleep(0.1)
        self._listener.stop()

    @staticmethod
    def _get_key_name(key) -> str:
        # Check for space by attribute name to avoid importing Key at call time
        key_name = getattr(key, "name", None)
        if key_name == "space":
            return "space"
        char = getattr(key, "char", None)
        if char:
            return char.lower()
        return ""

    def stop(self):
        self._running = False
        if self._listener:
            self._listener.stop()
        self.wait(2000)

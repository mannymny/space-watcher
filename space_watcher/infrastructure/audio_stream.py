import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional
from ..domain.errors import StartFailed
from .deps import ensure_cmd

@dataclass
class AudioHandles:
    yt: Optional[subprocess.Popen]
    mpv: subprocess.Popen
    ffmpeg: Optional[subprocess.Popen]
    stop: threading.Event
    thread: threading.Thread
    mpv_lock: threading.Lock = field(default_factory=threading.Lock)
    muted: bool = False

class AudioStreamService:
    def __init__(self):
        pass

    def _ensure_deps(self, *, record: bool, log=None):
        ensure_cmd("yt-dlp", log=log)
        ensure_cmd("mpv", log=log)
        if record:
            ensure_cmd("ffmpeg", log=log)

    def start(self, *, url, record, ffmpeg_cmd, guest, cookies, log):
        self._ensure_deps(record=record, log=log)
        mpv = self._start_mpv(muted=False)

        ff = self._start_ffmpeg(ffmpeg_cmd) if record else None

        stop = threading.Event()
        handles = AudioHandles(None, mpv, ff, stop, threading.Thread())
        t = threading.Thread(
            target=self._stream_loop,
            args=(handles, url, guest, cookies, log),
            daemon=True,
        )
        handles.thread = t
        t.start()

        return handles

    def stop(self, h: AudioHandles):
        h.stop.set()
        for p in (h.ffmpeg, h.mpv, h.yt):
            if p and p.poll() is None:
                p.terminate()

    def _start_mpv(self, *, muted: bool):
        volume = "0" if muted else "100"
        cmd = [
            "mpv",
            "--no-video",
            "--no-config",
            "--mute=no",
            f"--volume={volume}",
            "--ao=wasapi",
            "--cache=yes",
            "--demuxer-max-bytes=512MiB",
            "-",
        ]
        device = os.environ.get("SPACE_WATCHER_AUDIO_DEVICE")
        if device:
            cmd.insert(-1, f"--audio-device={device}")
        return subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def _start_ffmpeg(self, ffmpeg_cmd):
        return subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    def _start_yt(self, url, cookies):
        cookies_file = self._find_cookies_file() if cookies else None
        base = [
            "yt-dlp",
            "--retries", "infinite",
            "--fragment-retries", "infinite",
            "--retry-sleep", "1",
            "--hls-use-mpegts",
            "-o", "-",
            url,
        ]
        cmd = (["yt-dlp", "--cookies-from-browser", "edge"] + base[1:]) if cookies else (["yt-dlp", "--no-cookies"] + base[1:])
        if cookies_file:
            cmd = ["yt-dlp", "--cookies", cookies_file] + base[1:]
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def _stream_loop(self, h: AudioHandles, url, guest, cookies, log):
        modes = []
        if guest:
            modes.append(("guest", False))
        if cookies:
            modes.append(("cookies", True))
        if not modes:
            modes.append(("guest", False))

        mode_index = 0
        attempt = 0
        while not h.stop.is_set():
            attempt += 1
            name, use_cookies = modes[min(mode_index, len(modes) - 1)]
            if log:
                extra = ""
                if use_cookies and self._find_cookies_file():
                    extra = " (cookies file)"
                elif use_cookies:
                    extra = " (edge cookies)"
                log(f"Starting audio ({name}){extra} [attempt {attempt}]")
            h.yt = self._start_yt(url, use_cookies)
            start_ts = time.time()
            got_data = False

            while not h.stop.is_set():
                data = h.yt.stdout.read(65536)
                if not data:
                    break
                got_data = True
                with h.mpv_lock:
                    if h.mpv.poll() is not None:
                        h.mpv = self._start_mpv(muted=h.muted)
                    if h.ffmpeg and h.ffmpeg.poll() is not None:
                        h.ffmpeg = self._start_ffmpeg(h.ffmpeg.args)
                    try:
                        if h.mpv.stdin:
                            h.mpv.stdin.write(data)
                            h.mpv.stdin.flush()
                        if h.ffmpeg and h.ffmpeg.stdin:
                            h.ffmpeg.stdin.write(data)
                            h.ffmpeg.stdin.flush()
                    except BrokenPipeError:
                        if h.mpv and h.mpv.poll() is None:
                            h.mpv.terminate()
                        if h.ffmpeg and h.ffmpeg.poll() is None:
                            h.ffmpeg.terminate()

            if h.yt and h.yt.poll() is None:
                h.yt.terminate()

            if h.stop.is_set():
                break

            fast_fail = (time.time() - start_ts) < 5
            if fast_fail and mode_index < len(modes) - 1:
                mode_index += 1

            if not got_data and log:
                log("Audio not ready yet, retrying...")

            # Always retry unless user stopped.
            time.sleep(2.0 if fast_fail else 1.0)

    def toggle_mute(self, h: AudioHandles) -> bool:
        with h.mpv_lock:
            h.muted = not h.muted
            if h.mpv and h.mpv.poll() is None:
                h.mpv.terminate()
            h.mpv = self._start_mpv(muted=h.muted)
        return h.muted

    def _find_cookies_file(self) -> Optional[str]:
        env_path = os.environ.get("SPACE_WATCHER_COOKIES_PATH")
        if env_path and os.path.isfile(env_path):
            return env_path

        candidates = []
        here = os.path.abspath(os.path.dirname(__file__))
        repo_root = os.path.abspath(os.path.join(here, "..", ".."))
        candidates.extend(
            [
                os.path.join(repo_root, "cookies.txt"),
                os.path.join(repo_root, "bin", "cookies.txt"),
            ]
        )

        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
            candidates.extend(
                [
                    os.path.join(base, "cookies.txt"),
                    os.path.join(base, "bin", "cookies.txt"),
                ]
            )
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.extend(
                    [
                        os.path.join(meipass, "cookies.txt"),
                        os.path.join(meipass, "bin", "cookies.txt"),
                    ]
                )

        for p in candidates:
            if os.path.isfile(p):
                return p
        return None

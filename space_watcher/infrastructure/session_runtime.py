import os
import time
from dataclasses import dataclass
from typing import Optional
from ..domain.models import SpaceUrl, RunOptions
from .browser_automation import BrowserAutomationService, BrowserRuntime
from .edge_launcher import EdgeLauncher, EdgeLaunchConfig
from .audio_stream import AudioStreamService, AudioHandles
from .recorder import RecorderService

@dataclass
class SessionRuntime:
    audio: Optional[AudioHandles]
    recording_path: Optional[str]
    browser: Optional[BrowserRuntime]

class SessionOrchestrator:
    def __init__(self, out_dir: str):
        self.audio = AudioStreamService()
        self.recorder = RecorderService(out_dir)
        self.browser = BrowserAutomationService()

    def start(self, space: SpaceUrl, opts: RunOptions, log):
        browser_rt = self.browser.start(space.value, opts, log)
        if browser_rt is None:
            EdgeLauncher.open_mobile_like(
                EdgeLaunchConfig(
                    space.value,
                    opts.mobile_user_agent,
                    opts.rect.width,
                    opts.rect.height,
                    opts.rect.x,
                    opts.rect.y,
                )
            )
            time.sleep(3)
        else:
            if browser_rt.ready:
                browser_rt.ready.wait(timeout=15)

        rec = self.recorder.plan(opts.rect) if opts.record else None

        try:
            audio = self.audio.start(
                url=space.value,
                record=opts.record,
                ffmpeg_cmd=(rec.ffmpeg_cmd if rec else None),
                guest=opts.try_guest_first,
                cookies=opts.allow_cookies_fallback,
                log=log,
            )
        except Exception:
            self.browser.stop(browser_rt)
            raise

        return SessionRuntime(audio, rec.out_path if rec else None, browser_rt)

    def stop(self, rt: SessionRuntime):
        self.audio.stop(rt.audio)
        self.browser.stop(rt.browser)

    def toggle_mute(self, rt: SessionRuntime) -> bool:
        return self.audio.toggle_mute(rt.audio)

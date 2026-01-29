import os
from dataclasses import dataclass
from datetime import datetime
from ..domain.models import WindowRect

@dataclass(frozen=True)
class RecordingPlan:
    out_path: str
    ffmpeg_cmd: list[str]

class RecorderService:
    def __init__(self, out_dir: str):
        self.out_dir = out_dir

    def plan(self, rect: WindowRect) -> RecordingPlan:
        os.makedirs(self.out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = os.path.join(self.out_dir, f"space_{ts}_{rect.width}x{rect.height}.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-f", "aac", "-i", "pipe:0",
            "-f", "gdigrab",
            "-framerate", "30",
            "-offset_x", str(rect.x),
            "-offset_y", str(rect.y),
            "-video_size", f"{rect.width}x{rect.height}",
            "-i", "desktop",
            "-map", "1:v:0", "-map", "0:a:0",
            "-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "128k",
            out,
        ]
        return RecordingPlan(out, cmd)

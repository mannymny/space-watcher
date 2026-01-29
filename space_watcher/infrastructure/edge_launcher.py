import os
import subprocess
from dataclasses import dataclass
from typing import Optional

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "msedge",
]

@dataclass(frozen=True)
class EdgeLaunchConfig:
    url: str
    user_agent: str
    width: int
    height: int
    x: int
    y: int

class EdgeLauncher:
    @staticmethod
    def find_edge() -> Optional[str]:
        for p in EDGE_CANDIDATES:
            if os.path.isabs(p) and os.path.exists(p):
                return p
            if not os.path.isabs(p):
                return p
        return None

    @staticmethod
    def open_mobile_like(cfg: EdgeLaunchConfig):
        edge = EdgeLauncher.find_edge()
        if not edge:
            return
        subprocess.Popen(
            [
                edge,
                f"--user-agent={cfg.user_agent}",
                f"--window-size={cfg.width},{cfg.height}",
                f"--window-position={cfg.x},{cfg.y}",
                "--inprivate",
                "--disable-features=ExternalProtocolDialog,IntentPicker,AppBanners",
                "--mute-audio",
                "--force-dark-mode",
                "--enable-features=WebUIDarkMode,DarkMode",
                "--new-window",
                f"--app={cfg.url}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

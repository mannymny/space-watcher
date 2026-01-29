import os
import re
import shutil
import sys
from ..domain.errors import MissingDependency

def require_cmd(cmd: str) -> str:
    path = shutil.which(cmd)
    if not path:
        raise MissingDependency(f"Missing '{cmd}' in PATH.")
    return path


def ensure_cmd(cmd: str, log=None) -> str:
    path = _find_local_cmd(cmd)
    if path:
        _add_to_path(os.path.dirname(path))
        return path

    path = shutil.which(cmd)
    if path:
        return path

    raise MissingDependency(
        f"Missing '{cmd}'. Place {cmd} in a local bin folder or add it to PATH."
    )


def _exe_name(cmd: str) -> str:
    if os.name == "nt" and not cmd.lower().endswith(".exe"):
        return f"{cmd}.exe"
    return cmd


def _find_local_cmd(cmd: str) -> str | None:
    exe = _exe_name(cmd)
    candidates = []

    env_dir = os.environ.get("SPACE_WATCHER_BIN_DIR")
    if env_dir:
        candidates.append(os.path.join(env_dir, exe))

    env_cmd = os.environ.get(_env_key(cmd))
    if env_cmd:
        candidates.append(env_cmd)

    here = os.path.abspath(os.path.dirname(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    candidates.extend(
        [
            os.path.join(repo_root, "bin", exe),
            os.path.join(repo_root, "vendor", cmd, exe),
        ]
    )

    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        candidates.extend(
            [
                os.path.join(base, exe),
                os.path.join(base, "bin", exe),
            ]
        )
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.extend(
                [
                    os.path.join(meipass, exe),
                    os.path.join(meipass, "bin", exe),
                ]
            )

    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def _env_key(cmd: str) -> str:
    key = re.sub(r"[^A-Z0-9]", "_", cmd.upper())
    return f"SPACE_WATCHER_{key}_PATH"


def _add_to_path(dir_path: str) -> None:
    if not dir_path:
        return
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep) if current else []
    if dir_path not in parts:
        os.environ["PATH"] = dir_path + os.pathsep + current

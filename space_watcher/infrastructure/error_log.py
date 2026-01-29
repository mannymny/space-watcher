import json
import os
import tempfile
import traceback
from datetime import datetime, timezone
from typing import Any, Optional


def _default_log_dir() -> str:
    env_dir = os.environ.get("SPACE_WATCHER_LOG_DIR")
    if env_dir:
        return env_dir

    here = os.path.abspath(os.path.dirname(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    parent = os.path.dirname(repo_root)
    if parent:
        return parent

    return os.path.expanduser("~")


def get_error_log_path() -> str:
    base_dir = _default_log_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(base_dir, f"space_watcher_errors_{ts}.json")


def log_error(
    err: Exception,
    *,
    context: str,
    extra: Optional[dict[str, Any]] = None,
    log_path: Optional[str] = None,
) -> str:
    path = log_path or get_error_log_path()
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "type": type(err).__name__,
        "message": str(err),
        "traceback": "".join(
            traceback.format_exception(type(err), err, err.__traceback__)
        ).strip(),
        "extra": extra or {},
    }
    _append_entry(path, entry)
    return path


def _append_entry(path: str, entry: dict[str, Any]) -> None:
    dir_path = os.path.dirname(path) or "."
    os.makedirs(dir_path, exist_ok=True)
    data: list[dict[str, Any]] = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    data = loaded
        except Exception:
            data = []

    data.append(entry)
    fd, tmp_path = tempfile.mkstemp(prefix="errors_", suffix=".json", dir=dir_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=True, indent=2)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

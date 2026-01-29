import os
import re
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from .error_log import get_error_log_path, log_error

START_WORDS = [
    "Start listening",
    "Comenzar a escuchar",
    "Iniciar escucha",
]
GOT_IT_WORDS = [
    "Got it",
    "Entendido",
    "De acuerdo",
    "OK",
    "Okay",
    "Aceptar",
]
MOBILE_SCALE = 1.0


def _user_data_dir() -> str:
    return tempfile.mkdtemp(prefix="space_watcher_edge_profile_")

_BLOCK_PROTOCOLS_SCRIPT = """
(() => {
  const allowed = new Set(["http:", "https:"]);
  const resolveUrl = (url) => {
    try {
      return new URL(url, window.location.href);
    } catch (e) {
      return null;
    }
  };
  const isAllowed = (url) => {
    const u = resolveUrl(url);
    return !!u && allowed.has(u.protocol);
  };
  const origAssign = window.location.assign.bind(window.location);
  const origReplace = window.location.replace.bind(window.location);
  window.location.assign = (url) => {
    if (isAllowed(url)) return origAssign(url);
  };
  window.location.replace = (url) => {
    if (isAllowed(url)) return origReplace(url);
  };
  const origOpen = window.open.bind(window);
  window.open = (url, ...args) => {
    if (!url || !isAllowed(url)) return null;
    return origOpen(url, ...args);
  };
})();
"""


@dataclass
class BrowserRuntime:
    stop: threading.Event
    thread: threading.Thread
    user_data_dir: str | None = None
    ready: threading.Event | None = None


class BrowserAutomationService:
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or get_error_log_path()

    def start(self, url, opts, log: Optional[Callable[[str], None]] = None) -> Optional[BrowserRuntime]:
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            if log:
                log("Playwright not installed; skipping auto-join.")
            return None

        stop = threading.Event()
        ready = threading.Event()
        user_data_dir = _user_data_dir()

        def run():
            try:
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir,
                        channel="msedge",
                        headless=False,
                        args=[
                            f"--app={url}",
                            f"--window-size={opts.rect.width},{opts.rect.height}",
                            f"--window-position={opts.rect.x},{opts.rect.y}",
                            "--inprivate",
                            "--disable-features=ExternalProtocolDialog,IntentPicker,AppBanners",
                            "--mute-audio",
                            "--force-dark-mode",
                            "--enable-features=WebUIDarkMode,DarkMode",
                            "--no-first-run",
                            "--no-default-browser-check",
                        ],
                        viewport={"width": opts.rect.width, "height": opts.rect.height},
                        user_agent=opts.mobile_user_agent,
                        device_scale_factor=MOBILE_SCALE,
                        is_mobile=True,
                        has_touch=True,
                        screen={"width": opts.rect.width, "height": opts.rect.height},
                        color_scheme="dark",
                    )
                    context.add_init_script(_BLOCK_PROTOCOLS_SCRIPT)
                    page = context.pages[0] if context.pages else context.new_page()
                    if not page.url or page.url == "about:blank":
                        page.goto(url, wait_until="domcontentloaded")

                    if log:
                        log("Opening Space in Edge...")
                    _click_start_listening(page, log)
                    ready.set()
                    _dismiss_got_it_for_a_while(page, stop, log)

                    while not stop.is_set():
                        time.sleep(1)

                    context.close()
            except Exception as e:
                ready.set()
                log_error(e, context="browser_automation", extra={"url": url}, log_path=self.log_path)
                if log:
                    log("Browser automation failed. See errors.json.")

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return BrowserRuntime(stop=stop, thread=thread, user_data_dir=user_data_dir, ready=ready)

    def stop(self, rt: Optional[BrowserRuntime]):
        if not rt:
            return
        rt.stop.set()
        rt.thread.join(timeout=3)
        if rt.user_data_dir and os.path.isdir(rt.user_data_dir):
            try:
                shutil.rmtree(rt.user_data_dir, ignore_errors=True)
            except Exception:
                pass


def _try_click(locator) -> bool:
    try:
        if locator.count() == 0:
            return False
        target = locator.first
        if not target.is_visible():
            return False
        target.click(timeout=800)
        return True
    except Exception:
        return False


def _contains_any_xpath(texts: list[str]) -> str:
    parts = [f"contains(., '{t}')" for t in texts]
    return "//*[" + " or ".join(parts) + "]"


def _click_start_listening(page, log: Optional[Callable[[str], None]]):
    end = time.time() + 30
    start_xpath = _contains_any_xpath(START_WORDS)
    start_re = re.compile(r"(start listening|comenzar a escuchar|iniciar escucha)", re.I)

    while time.time() < end:
        if _try_click(page.get_by_role("button", name=start_re)):
            if log:
                log("Clicked Start listening.")
            return True
        if _try_click(page.locator(f"xpath={start_xpath}")):
            if log:
                log("Clicked Start listening.")
            return True
        time.sleep(0.8)

    if log:
        log("Start listening button not found.")
    return False


def _dismiss_got_it_for_a_while(page, stop: threading.Event, log: Optional[Callable[[str], None]]):
    end = time.time() + 60
    got_it_xpath = _contains_any_xpath(GOT_IT_WORDS)
    got_it_re = re.compile(r"(got it|entendido|de acuerdo|ok|okay|aceptar)", re.I)

    while time.time() < end and not stop.is_set():
        clicked = False
        if _try_click(page.get_by_role("button", name=got_it_re)):
            clicked = True
        elif _try_click(page.locator(f"xpath={got_it_xpath}")):
            clicked = True

        if clicked and log:
            log("Dismissed a modal.")

        time.sleep(0.8 if clicked else 1.2)

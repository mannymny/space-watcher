import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from ..application.use_cases import StartSessionUseCase, StopSessionUseCase
from ..domain.errors import MissingDependency
from ..domain.models import RunOptions, SpaceUrl, WindowRect
from ..domain.validators import is_valid_space_url
from ..infrastructure.error_log import get_error_log_path, log_error
from ..infrastructure.session_runtime import SessionOrchestrator

UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
RECT = WindowRect(0, 0, 360, 780)
OUT = os.path.join(os.path.expanduser("~"), "Desktop", "space_recordings")

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Space-Watcher")
        self._theme()
        self.url = tk.StringVar()
        self.rec = tk.BooleanVar()
        self.status = tk.StringVar(value="Paste a Space link.")

        self.orch = SessionOrchestrator(OUT)
        self.start_uc = StartSessionUseCase(self.orch)
        self.stop_uc = StopSessionUseCase(self.orch)
        self.rt = None
        self.running = False
        self.muted = False

        self._ui()
        self._bind()

    def _theme(self):
        self.colors = {
            "bg": "#0f1115",
            "fg": "#e8e8e8",
            "muted": "#a8b0bf",
            "entry_bg": "#141922",
            "btn_bg": "#1c2433",
            "btn_active": "#273245",
            "btn_disabled": "#1a202c",
        }
        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"])
        style.configure("Muted.TLabel", background=self.colors["bg"], foreground=self.colors["muted"])
        style.configure(
            "TEntry",
            fieldbackground=self.colors["entry_bg"],
            foreground=self.colors["fg"],
            background=self.colors["entry_bg"],
        )
        style.configure(
            "TButton",
            background=self.colors["btn_bg"],
            foreground=self.colors["fg"],
            borderwidth=0,
        )
        style.map(
            "TButton",
            background=[
                ("active", self.colors["btn_active"]),
                ("disabled", self.colors["btn_disabled"]),
            ],
            foreground=[("disabled", self.colors["muted"])],
        )
        style.configure(
            "TCheckbutton",
            background=self.colors["bg"],
            foreground=self.colors["fg"],
        )
        style.map(
            "TCheckbutton",
            background=[("active", self.colors["bg"])],
            foreground=[("active", self.colors["fg"])],
        )

    def _ui(self):
        f = ttk.Frame(self.root, padding=14)
        f.grid()

        ttk.Label(f, text="Space link").grid(sticky="w")
        self.url_entry = tk.Entry(
            f,
            textvariable=self.url,
            width=70,
            bg=self.colors["entry_bg"],
            fg=self.colors["fg"],
            insertbackground=self.colors["fg"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["btn_bg"],
            highlightcolor=self.colors["btn_active"],
        )
        self.url_entry.grid(columnspan=3, pady=6)

        ttk.Checkbutton(f, text="Record 360x780", variable=self.rec).grid(sticky="w")
        self.btn = ttk.Button(f, text="Continue", command=self.start, state="disabled")
        self.btn.grid(row=2, column=2, sticky="e")

        self.stop_btn = ttk.Button(f, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.grid(row=3, column=2, sticky="e")

        ttk.Label(f, textvariable=self.status, wraplength=560, style="Muted.TLabel").grid(
            row=3, columnspan=2, sticky="w"
        )

    def _bind(self):
        self.url.trace_add("write", lambda *_: self._validate())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.url_entry.bind("<Return>", self._on_enter)
        self.root.bind("<Control-m>", self._toggle_mute)

    def _validate(self):
        ok = is_valid_space_url(self.url.get()) and not self.running
        self.btn.configure(state=("normal" if ok else "disabled"))
        return ok

    def _on_enter(self, _event=None):
        if self._validate():
            self.start()

    def _on_close(self):
        self.stop()
        self.root.after(0, self.root.destroy)

    def _toggle_mute(self, _event=None):
        if not self.rt:
            return
        try:
            self.muted = self.orch.toggle_mute(self.rt)
            self.log("Muted" if self.muted else "Unmuted")
        except Exception as e:
            self._report_error("Mute failed", e, "mute_toggle")

    def log(self, m):
        self.root.after(0, lambda: self.status.set(m))

    def _report_error(self, title, err, context, extra=None):
        path = None
        try:
            path = log_error(err, context=context, extra=extra, log_path=get_error_log_path())
        except Exception:
            path = None
        msg = f"{err}"
        if path:
            msg += f"\n\nSaved in:\n{path}"
        self.root.after(0, lambda: messagebox.showerror(title, msg))

    def start(self):
        try:
            space = SpaceUrl(self.url.get())
        except Exception as e:
            self._report_error("Invalid URL", e, "validate_url", {"url": self.url.get()})
            return

        opts = RunOptions(RECT, UA, self.rec.get(), try_guest_first=True, allow_cookies_fallback=False)
        self.running = True
        self.stop_btn.configure(state="normal")
        self.btn.configure(state="disabled")

        def run():
            try:
                self.rt = self.start_uc.execute(space, opts, self.log).runtime
                self.log("Running... Press Stop to finish.")
                while self.running:
                    threading.Event().wait(0.5)
            except MissingDependency as e:
                self._report_error("Missing dependency", e, "missing_dependency")
            except Exception as e:
                self._report_error("Error", e, "start_session")
            finally:
                self.root.after(0, self.stop)

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        try:
            if self.rt:
                self.stop_uc.execute(self.rt)
        except Exception as e:
            self._report_error("Stop failed", e, "stop_session")
        self.running = False
        self.stop_btn.configure(state="disabled")
        self._validate()
        self.status.set("Stopped.")

def run_gui():
    root = tk.Tk()
    App(root)
    root.mainloop()

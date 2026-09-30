"""The NIDA desktop application shell."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog
from typing import Dict, Optional

from nida import Nida
from nida.exceptions import NidaError

from . import demo, history
from .base import ThemedFrame, apply_theme
from .buttons import IconButton
from .panels import HistoryPanel, LookupPanel, display_nin
from .profile import ProfilePanel
from .theme import Theme

APP_TITLE = "NIDA Lookup - Tanzania"


class NidaApp(tk.Tk):
    """Look up a person by National ID, and search your own lookup history."""

    #: status tone -> text colour key
    TONE_TEXT = {"muted": "text_muted", "success": "success",
                 "error": "danger", "warning": "warning", "busy": "accent"}
    #: status tone -> dot colour key
    TONE_DOT = {"muted": "text_faint", "success": "success",
                "error": "danger", "warning": "warning", "busy": "accent"}

    def __init__(self, offline: bool = False) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.theme = Theme()
        self.theme.bind_root(self)
        self.configure(bg=self.theme.bg)

        self.offline = offline
        self.client = Nida(timeout=20)
        self.records: Dict[str, Dict] = history.load()
        self.current_nin: Optional[str] = None
        self._busy = False
        # Worker threads push ("ok", nin, record) / ("error", message) here;
        # the Tk main loop drains it, because Tk is not thread safe.
        self._results: "queue.Queue[tuple]" = queue.Queue()

        self._build()
        self._bind_shortcuts()
        self._drain_results()
        self.history_panel.set_records(self.records)
        self._status("Ready - enter a 20-digit National ID and press Fetch.")
        if offline:
            self._seed_demo()

    # ------------------------------------------------------------------ #
    # construction
    # ------------------------------------------------------------------ #

    def _build(self) -> None:
        header = ThemedFrame(self, self.theme, bg_key="bg")
        header.pack(fill="x", side="top")
        self._build_header(header)

        body = ThemedFrame(self, self.theme, bg_key="bg")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        body.columnconfigure(0, weight=0, minsize=360)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ThemedFrame(body, self.theme, bg_key="bg")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        self.lookup_panel = LookupPanel(left, self.theme, on_fetch=self.fetch)
        self.lookup_panel.grid(row=0, column=0, sticky="ew")

        self.history_panel = HistoryPanel(left, self.theme, on_select=self.show_cached)
        self.history_panel.grid(row=1, column=0, sticky="nsew", pady=(16, 0))

        self.profile_panel = ProfilePanel(body, self.theme, on_save=self.save_image,
                                          on_copy=self.copy_value)
        self.profile_panel.grid(row=0, column=1, sticky="nsew")

        self._build_status_bar()

    def _build_header(self, parent) -> None:
        left = ThemedFrame(parent, self.theme, bg_key="bg")
        left.pack(side="left", padx=20, pady=18)

        mark = ThemedFrame(left, self.theme, bg_key="accent")
        mark.pack(side="left", padx=(0, 12))
        tk.Label(mark, text="NI", bg=self.theme.accent, fg=self.theme.on_accent,
                 font=self.theme.fonts("title"), padx=10, pady=6).pack()

        titles = ThemedFrame(left, self.theme, bg_key="bg")
        titles.pack(side="left")
        tk.Label(titles, text="NIDA Lookup", anchor="w", bg=self.theme.bg,
                 fg=self.theme.text, font=self.theme.fonts("display")).pack(anchor="w")
        tk.Label(titles, anchor="w", bg=self.theme.bg, fg=self.theme.text_muted,
                 font=self.theme.fonts("small"),
                 text="Tanzania National ID - fetch by NIN, search your own history"
                 ).pack(anchor="w")

        right = ThemedFrame(parent, self.theme, bg_key="bg")
        right.pack(side="right", padx=20, pady=18)
        self.demo_badge = tk.Label(right, text="", bg=self.theme.bg,
                                   fg=self.theme.warning,
                                   font=self.theme.fonts("small"))
        self.demo_badge.pack(side="right", padx=(0, 10))
        IconButton(right, self.theme, "\u25D1", command=self.toggle_theme,
                   tooltip="Toggle dark / light theme  (Ctrl+T)").pack(side="right")

    def _build_status_bar(self) -> None:
        bar = ThemedFrame(self, self.theme, bg_key="surface")
        bar.pack(fill="x", side="bottom")
        self.status_dot = tk.Label(bar, text="\u25CF", bg=self.theme.surface,
                                   fg=self.theme.text_faint,
                                   font=self.theme.fonts("small"))
        self.status_dot.pack(side="left", padx=(20, 8), pady=9)
        self.status_label = tk.Label(bar, text="", anchor="w", bg=self.theme.surface,
                                     fg=self.theme.text_muted,
                                     font=self.theme.fonts("small"))
        self.status_label.pack(side="left", fill="x", expand=True)

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-l>", lambda _e: self.lookup_panel.focus())
        self.bind("<Control-t>", lambda _e: self.toggle_theme())
        self.bind("<Control-f>", lambda _e: self.fetch(self.lookup_panel.value()))
        self.bind("<Escape>", lambda _e: self.lookup_panel.clear())

    # ------------------------------------------------------------------ #
    # status bar
    # ------------------------------------------------------------------ #

    def _status(self, message: str, tone: str = "muted") -> None:
        """Update the footer status line."""
        self.status_label.configure(text=message,
                                    fg=getattr(self.theme, self.TONE_TEXT[tone]))
        self.status_dot.configure(fg=getattr(self.theme, self.TONE_DOT[tone]))

    # ------------------------------------------------------------------ #
    # data flow
    # ------------------------------------------------------------------ #

    def fetch(self, nin: str) -> None:
        """Fetch a record by NIN, off the UI thread."""
        if self._busy:
            return
        digits = "".join(ch for ch in str(nin) if ch.isdigit())
        if len(digits) != 20:
            self.lookup_panel.nin_field.set_hint(
                "A National ID has exactly 20 digits.", "danger")
            return
        self._busy = True
        self.lookup_panel.set_busy(True)
        self._status(f"Fetching {display_nin(digits)} ...", "busy")
        threading.Thread(target=self._fetch_worker, args=(digits,),
                         daemon=True).start()

    def _fetch_worker(self, nin: str) -> None:
        """Runs on a background thread; only touches the queue, never Tk."""
        try:
            record = demo.load_demo(nin) if self.offline else self.client.load_user(nin)
        except NidaError as exc:
            self._results.put(("error", str(exc)))
            return
        except Exception as exc:  # last-resort guard: never kill the UI
            self._results.put(("error", f"Unexpected error: {exc}"))
            return
        self._results.put(("ok", nin, record))

    def _drain_results(self) -> None:
        """Apply any finished fetches. Re-armed by the Tk main loop."""
        try:
            while True:
                item = self._results.get_nowait()
                if item[0] == "ok":
                    self._on_success(item[1], item[2])
                else:
                    self._on_error(item[1])
        except queue.Empty:
            pass
        self.after(60, self._drain_results)

    def _on_success(self, nin: str, record: Dict) -> None:
        self._busy = False
        self.lookup_panel.set_busy(False)
        self.current_nin = nin
        self.profile_panel.show_record(nin, record)
        self._remember(nin, record)
        from .profile import lookup

        name = lookup(record, "FULLNAME", default=nin)
        self._status(f"Loaded {name} - saved to your local history.", "success")

    def _on_error(self, message: str) -> None:
        self._busy = False
        self.lookup_panel.set_busy(False)
        self.lookup_panel.nin_field.set_hint(message, "danger")
        self._status(message, "error")

    def _remember(self, nin: str, record: Dict) -> None:
        try:
            history.remember(self.records, nin, record)
        except OSError as exc:
            self._status(f"Fetched, but the history file failed to save: {exc}",
                         "warning")
            return
        self.history_panel.set_records(self.records)

    def show_cached(self, nin: str) -> None:
        """Display a record from the local cache (no images available)."""
        record = self.records.get(nin)
        if not record:
            return
        self.current_nin = nin
        self.lookup_panel.set_value(display_nin(nin))
        self.profile_panel.show_record(nin, record, from_cache=True)
        self._status(
            f"Showing the cached record for {display_nin(nin)}. "
            "Press Ctrl+F to re-fetch it with photos.")

    # ------------------------------------------------------------------ #
    # actions
    # ------------------------------------------------------------------ #

    def save_image(self, field: str, image) -> None:
        """Write a photo/signature to disk."""
        name = f"{self.current_nin or 'nida'}_{field.lower()}.png"
        path = filedialog.asksaveasfilename(
            defaultextension=".png", initialfile=name,
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg")])
        if not path:
            return
        try:
            image.save(path)
        except (OSError, ValueError) as exc:
            self._status(f"Could not save the image: {exc}", "error")
            return
        self._status(f"Saved {field.lower()} to {path}", "success")

    def copy_value(self, value: str) -> None:
        """Copy a field value to the clipboard."""
        self.clipboard_clear()
        self.clipboard_append(value)
        self._status(f"Copied: {value}")

    def toggle_theme(self) -> None:
        """Swap between the dark and light palettes."""
        new_theme = self.theme.swap()
        mapping = self.theme.color_map(new_theme)
        self.theme = new_theme
        self.theme.bind_root(self)
        self.configure(bg=self.theme.bg)
        apply_theme(self, self.theme, mapping)
        self._status(f"Switched to the {self.theme.palette.name} theme.")

    def _seed_demo(self) -> None:
        """Populate the cache with sample records (offline preview mode)."""
        for record in demo.DEMO_RECORDS:
            self.records[record["NIN"]] = {
                k: v for k, v in record.items() if k not in ("PHOTO", "SIGNATURE")}
        self.history_panel.set_records(self.records)
        self.demo_badge.configure(text="\u25CF  demo mode (offline sample data)")
        self._status("Demo mode: records are generated locally, no requests sent.",
                     "warning")


def main(offline: bool = False) -> None:
    """Entry point used by ``app.py``."""
    NidaApp(offline=offline).mainloop()

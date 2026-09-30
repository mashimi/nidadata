"""Left-hand panels: NIDA lookup and local-history search."""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Dict, Optional

from .buttons import Button
from .card import Card
from .containers import ListRow, ScrollFrame
from .fields import Field
from .theme import Theme

# Fields scanned when matching a free-text name query.
_NAME_FIELDS = ("FULLNAME", "FIRSTNAME", "MIDDLENAME", "LASTNAME")


def record_label(record: Dict) -> str:
    """``Amani J. Mwakalinga`` - the friendliest available name."""
    for key in ("FULLNAME", "Firstname", "FirstName"):
        value = record.get(key)
        if value:
            return str(value)
    parts = [record.get(k) for k in ("Firstname", "Middlename", "Lastname")]
    joined = " ".join(str(p) for p in parts if p)
    return joined or "Unnamed record"


def display_nin(nin: str) -> str:
    """``19990512141150000123`` -> ``1999 0512 1411 5000 0123``."""
    digits = "".join(ch for ch in str(nin) if ch.isdigit())
    if len(digits) != 20:
        return str(nin)
    return " ".join(digits[i:i + 4] for i in range(0, 20, 4))


class LookupPanel(Card):
    """Enter a 20-digit National ID and fetch the record."""

    def __init__(self, master, theme: Theme, on_fetch: Callable[[str], None], **kwargs):
        super().__init__(master, theme, title="Look up a person",
                         subtitle="Enter a 20-digit National ID (NIN)", **kwargs)
        self._on_fetch = on_fetch

        self.nin_field = Field(self.body, theme, label="NATIONAL ID",
                               placeholder="1999 0512 1411 5000 0123", mono=True)
        self.nin_field.pack(fill="x")
        self.nin_field.bind_enter(self._submit)
        self.nin_field.input.bind("<KeyRelease>", self._on_key)

        actions = tk.Frame(self.body, bg=self.bg)
        actions.pack(fill="x", pady=(14, 0))
        self.fetch_button = Button(actions, theme, "Fetch record",
                                   command=self._submit, width=150)
        self.fetch_button.pack(side="left")
        self.clear_button = Button(actions, theme, "Clear", variant="ghost",
                                   command=self._clear)
        self.clear_button.pack(side="left", padx=(8, 0))

        self._spinner_job = None

    # -- state ------------------------------------------------------------ #

    def set_busy(self, busy: bool) -> None:
        """Swap the primary button into a loading state while fetching."""
        self.fetch_button.set_enabled(not busy)
        if busy:
            self._spinner_step = 0
            self.fetch_button.set_text("Fetching")
            self._advance_spinner()
        else:
            self.fetch_button.set_text("Fetch record")
            self._stop_spinner()

    def _advance_spinner(self) -> None:
        frames = ("Fetching.   ", "Fetching..  ", "Fetching... ")
        self.fetch_button.set_text(frames[self._spinner_step % len(frames)])
        self._spinner_step += 1
        self._spinner_job = self.after(400, self._advance_spinner)

    def _stop_spinner(self) -> None:
        if self._spinner_job:
            self.after_cancel(self._spinner_job)
            self._spinner_job = None

    def value(self) -> str:
        return self.nin_field.get()

    def set_value(self, value: str) -> None:
        self.nin_field.set(value)
        self.nin_field.input.icursor("end")

    def focus(self) -> None:
        self.nin_field.focus()

    def clear(self) -> None:
        self.nin_field.clear()
        self.nin_field.set_hint("")

    # -- events ----------------------------------------------------------- #

    def _on_key(self, event) -> None:
        if event.keysym in ("Return", "KP_Enter"):
            return
        self.nin_field.set_hint("")

    def _submit(self) -> None:
        raw = self.nin_field.get()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            self.nin_field.set_hint("Enter a National ID first.", "danger")
            return
        if len(digits) != 20:
            self.nin_field.set_hint(
                f"A National ID has 20 digits - you entered {len(digits)}.", "warning")
            return
        self.nin_field.set_hint(f"Looking up {display_nin(digits)}", "accent")
        self._on_fetch(digits)

    def _clear(self) -> None:
        self.clear()
        self.fetch_button.flash("accent", 400)


class HistoryPanel(Card):
    """Search the locally cached records by name.

    NIDA has no name-search endpoint, so this only matches records this
    machine has already fetched - see the panel's subtitle.
    """

    def __init__(self, master, theme: Theme, on_select: Callable[[str], None], **kwargs):
        super().__init__(
            master, theme, title="Search your history",
            subtitle="Matches only records you have fetched on this machine", **kwargs)
        self._on_select = on_select

        self.search_field = Field(self.body, theme, label="NAME",
                                  placeholder="e.g. Amani")
        self.search_field.pack(fill="x")
        self.search_field.bind_enter(lambda: self.refresh())

        self.results = ScrollFrame(self.body, theme)
        self.results.pack(fill="both", expand=True, pady=(12, 0))
        self._records: Dict[str, Dict] = {}

    # -- data ------------------------------------------------------------- #

    def set_records(self, records: Dict[str, Dict]) -> None:
        """Provide the cache to search over."""
        self._records = records
        self.set_badge(f"{len(records)} cached" if records else "empty", "muted")
        self.refresh()

    def refresh(self) -> None:
        """Re-run the current query against the cached records."""
        self.results.clear()
        query = self.search_field.get().lower()
        if not query:
            self._show_placeholder()
            return
        matches = [nin for nin, rec in self._records.items()
                   if self._matches(rec, query)]
        if not matches:
            self._show_empty(query)
            return
        for nin in matches:
            self._add_row(nin, self._records[nin])
        self.set_badge(f"{len(matches)} match{'es' if len(matches) != 1 else ''}",
                       "accent")

    @staticmethod
    def _matches(record: Dict, query: str) -> bool:
        from .profile import lookup

        for key in ("FULLNAME", "Firstname", "Middlename", "Lastname",
                    "NIN", "District", "Region", "Village"):
            value = lookup(record, key)
            if value and query in str(value).lower():
                return True
        return False

    # -- rendering -------------------------------------------------------- #

    def _add_row(self, nin: str, record: Dict) -> None:
        row = ListRow(self.results.inner, self.theme,
                      command=lambda: self._on_select(nin))
        row.pack(fill="x", pady=3)
        text = tk.Frame(row, bg=self.theme.surface)
        text.pack(fill="x", padx=12, pady=9)
        tk.Label(text, text=record_label(record), anchor="w",
                 bg=self.theme.surface, fg=self.theme.text,
                 font=self.theme.fonts("body_bold")).pack(anchor="w")
        from .profile import lookup

        district = lookup(record, "District", default="\u2014")
        tk.Label(text, text=f"{display_nin(nin)}  \u00b7  {district}",
                 anchor="w", bg=self.theme.surface, fg=self.theme.text_faint,
                 font=self.theme.fonts("tiny")).pack(anchor="w", pady=(2, 0))
        row.bind("<Configure>", lambda _e, r=row: r._repaint(), add="+")
        text.bind("<Configure>", lambda _e, r=row: r._repaint(), add="+")

    def _show_placeholder(self) -> None:
        if not self._records:
            self._message("No cached records yet",
                          "Look someone up by National ID first - "
                          "saved records show up here.")
        else:
            self._message("Search by name",
                          f"{len(self._records)} record(s) cached. "
                          "Type a name to filter them.")

    def _show_empty(self, query: str) -> None:
        self.set_badge("no match", "danger")
        self._message(f'No cached record matches "{query}"',
                      "Name search only works for IDs you have already "
                      "fetched on this machine.")

    def _message(self, title: str, detail: str) -> None:
        holder = tk.Frame(self.results.inner, bg=self.theme.surface)
        holder.pack(fill="x", pady=(6, 0))
        tk.Label(holder, text=title, anchor="w", justify="left", wraplength=250,
                 bg=self.theme.surface, fg=self.theme.text_muted,
                 font=self.theme.fonts("small_bold")).pack(anchor="w")
        tk.Label(holder, text=detail, anchor="w", justify="left", wraplength=250,
                 bg=self.theme.surface, fg=self.theme.text_faint,
                 font=self.theme.fonts("tiny")).pack(anchor="w", pady=(3, 0))


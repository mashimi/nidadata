"""Text input with a sunken rounded surface and placeholder support."""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from .base import ThemedFrame
from .draw import send_to_back, round_rect
from .theme import RADIUS_SM, Theme

HINT_TONES = ("muted", "success", "danger", "warning", "accent")


class Field(ThemedFrame):
    """A labelled single-line input.

    ``get()`` returns an empty string while the placeholder is showing, so
    callers never have to special-case it.
    """

    def __init__(self, master, theme: Theme, label: str = "", placeholder: str = "",
                 mono: bool = False, width: int = 26, **kwargs):
        super().__init__(master, theme, bg_key="surface", **kwargs)
        self._placeholder = placeholder
        self._mono = mono
        self._showing_placeholder = False
        self._radius = RADIUS_SM

        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.bg)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.label = tk.Label(self, text=label, anchor="w", bg=self.bg,
                              fg=theme.text_muted, font=theme.fonts("small_bold"))
        self._input_holder = tk.Frame(self, bg=theme.surface_sunken)
        self.input = tk.Entry(
            self._input_holder, bg=theme.surface_sunken, fg=theme.text,
            insertbackground=theme.accent, relief="flat", bd=0,
            highlightthickness=0, width=width,
            font=theme.fonts("mono" if mono else "body"),
        )
        self.hint = tk.Label(self, text="", anchor="w", bg=self.bg,
                             fg=theme.text_faint, font=theme.fonts("tiny"))

        self.label.pack(fill="x")
        self._input_holder.pack(fill="x", pady=(6, 0))
        self.input.pack(fill="x", padx=12, pady=10)
        self.hint.pack(fill="x", pady=(6, 0))

        self.input.bind("<FocusIn>", self._on_focus_in)
        self.input.bind("<FocusOut>", self._on_focus_out)
        for widget in (self, self._input_holder, self.input, self.hint):
            widget.bind("<Configure>", lambda _e: self._repaint())
        self._show_placeholder()

    # -- value ----------------------------------------------------------- #

    def get(self) -> str:
        """Typed text, or ``""`` when only the placeholder is visible."""
        return "" if self._showing_placeholder else self.input.get().strip()

    def set(self, value) -> None:
        self.input.delete(0, tk.END)
        if value is not None and str(value) != "":
            self.input.insert(0, str(value))
            self._showing_placeholder = False
            self.input.configure(fg=self.theme.text)
        else:
            self._show_placeholder()

    def clear(self) -> None:
        self.input.delete(0, tk.END)
        self._show_placeholder()

    def focus(self) -> None:
        self.input.focus_set()

    def bind_enter(self, command: Callable[[], None]) -> None:
        self.input.bind("<Return>", lambda _e: command())

    def set_hint(self, text: str, tone: str = "muted") -> None:
        """Show a small helper / validation message under the input."""
        colors = {"muted": self.theme.text_faint, "success": self.theme.success,
                  "danger": self.theme.danger, "warning": self.theme.warning,
                  "accent": self.theme.accent}
        self.hint.configure(text=text, fg=colors.get(tone, self.theme.text_faint))

    # -- placeholder ----------------------------------------------------- #

    def _show_placeholder(self) -> None:
        if self._placeholder and not self.input.get():
            self.input.insert(0, self._placeholder)
            self.input.configure(fg=self.theme.text_faint)
            self._showing_placeholder = True
        else:
            self._showing_placeholder = False

    def _on_focus_in(self, _e) -> None:
        if self._showing_placeholder:
            self.input.delete(0, tk.END)
            self.input.configure(fg=self.theme.text)
            self._showing_placeholder = False

    def _on_focus_out(self, _e) -> None:
        self._show_placeholder()

    # -- painting -------------------------------------------------------- #

    def _repaint(self) -> None:
        self._canvas.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            return
        top = 30 if self.label.cget("text") else 8
        bottom = 26 if self.hint.cget("text") else 8
        round_rect(self._canvas, 0.5, top, w - 0.5, max(top + 12, h - bottom),
                   self._radius, fill=self.theme.surface_sunken,
                   outline=self.theme.border, width=1)
        send_to_back(self._canvas)

    def on_retheme(self, theme: Theme) -> None:
        self._canvas.configure(bg=self.bg)
        self.label.configure(bg=self.bg, fg=theme.text_muted,
                             font=theme.fonts("small_bold"))
        self._input_holder.configure(bg=theme.surface_sunken)
        self.input.configure(bg=theme.surface_sunken, fg=theme.text,
                             insertbackground=theme.accent,
                             font=theme.fonts("mono" if self._mono else "body"))
        if self._showing_placeholder:
            self.input.configure(fg=theme.text_faint)
        self.hint.configure(bg=self.bg, font=theme.fonts("tiny"))
        self._repaint()

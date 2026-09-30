"""Rounded surface panel with a title, subtitle and status badge."""

from __future__ import annotations

import tkinter as tk

from .base import ThemedFrame
from .draw import send_to_back, draw_shadow, round_rect
from .theme import RADIUS, Theme


class Badge(ThemedFrame):
    """Small rounded pill, e.g. ``MALE`` or ``12 records``."""

    def __init__(self, master, theme: Theme, text: str, bg: str = "", fg: str = "",
                 padx: int = 9, pady: int = 3, **kwargs):
        self._bg_color = bg or theme.surface_alt
        self._fg_color = fg or theme.text_muted
        super().__init__(master, theme, bg_key="surface_alt", **kwargs)
        self._radius = 999
        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self._bg_color)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.label = tk.Label(self, text=text, bg=self._bg_color, fg=self._fg_color,
                              padx=padx, pady=pady, font=theme.fonts("small_bold"))
        self.label.pack()
        for widget in (self, self.label):
            widget.bind("<Configure>", lambda _e: self._repaint())

    def set_text(self, text: str) -> None:
        self.label.configure(text=text)

    def _repaint(self) -> None:
        self._canvas.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w > 1 and h > 1:
            round_rect(self._canvas, 0, 0, w, h, self._radius,
                       fill=self._bg_color, outline="")

    def on_retheme(self, theme: Theme) -> None:
        self._canvas.configure(bg=self._bg_color)
        self.label.configure(bg=self._bg_color, fg=self._fg_color,
                             font=theme.fonts("small_bold"))


class Card(ThemedFrame):
    """A rounded surface panel.

    Put content into ``card.body``; the header, rule and badge are handled
    for you.  Use ``set_badge("text", tone)`` to show a status pill.
    """

    TONES = ("accent", "success", "danger", "muted")

    def __init__(self, master, theme: Theme, title: str = "", subtitle: str = "",
                 padding: int = 18, bg_key: str = "surface", **kwargs):
        super().__init__(master, theme, bg_key=bg_key, **kwargs)
        self._radius = RADIUS
        self._badge_spec = None

        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.bg)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.header = tk.Frame(self, bg=self.bg)
        self.badge_host = tk.Frame(self.header, bg=self.bg)
        self.title_label = tk.Label(self.header, text=title, anchor="w", bg=self.bg,
                                    fg=theme.text, font=theme.fonts("title"))
        self.subtitle_label = tk.Label(self.header, text=subtitle, anchor="w",
                                       bg=self.bg, fg=theme.text_muted,
                                       font=theme.fonts("small"))
        self.rule = tk.Frame(self, height=1, bg=theme.border)
        self.body = tk.Frame(self, bg=self.bg)

        self.badge_host.pack(side="right", anchor="n", padx=(10, 0))
        self.title_label.pack(anchor="w")
        if subtitle:
            self.subtitle_label.pack(anchor="w", pady=(2, 0))
        self.header.pack(fill="x", padx=padding, pady=(padding, 0))
        self.rule.pack(fill="x", padx=padding, pady=(12, 0))
        self.body.pack(fill="both", expand=True, padx=padding, pady=(padding - 2, padding))

        for widget in (self, self.header, self.title_label, self.subtitle_label,
                       self.badge_host, self.body):
            widget.bind("<Configure>", lambda _e: self._repaint())

    def _repaint(self) -> None:
        self._canvas.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            return
        draw_shadow(self._canvas, w, h, self.theme, self._radius)
        round_rect(self._canvas, 0.5, 0.5, w - 0.5, h - 0.5, self._radius,
                   fill=self.bg, outline=self.theme.border, width=1)
        send_to_back(self._canvas)

    def set_badge(self, text: str, tone: str = "accent") -> None:
        """Show a pill in the header; ``text=""`` removes it."""
        for child in self.badge_host.winfo_children():
            child.destroy()
        self._badge_spec = (text, tone) if text else None
        if not text:
            return
        bg, fg = {
            "accent": (self.theme.accent_soft, self.theme.accent),
            "success": (self.theme.success_soft, self.theme.success),
            "danger": (self.theme.danger_soft, self.theme.danger),
            "muted": (self.theme.surface_alt, self.theme.text_muted),
        }[tone]
        Badge(self.badge_host, self.theme, text, bg=bg, fg=fg).pack(side="right")

    def on_retheme(self, theme: Theme) -> None:
        self._canvas.configure(bg=self.bg)
        self.title_label.configure(bg=self.bg, fg=theme.text,
                                   font=theme.fonts("title"))
        self.subtitle_label.configure(bg=self.bg, fg=theme.text_muted,
                                      font=theme.fonts("small"))
        for frame in (self.header, self.badge_host):
            frame.configure(bg=self.bg)
        self.rule.configure(bg=theme.border)
        self.body.configure(bg=self.bg)
        if self._badge_spec:
            self.set_badge(*self._badge_spec)
        self._repaint()

"""Scrollable container, slim scrollbar and hoverable list rows."""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from .base import ThemedFrame
from .draw import send_to_back, round_rect
from .theme import RADIUS_SM, Theme


class Scrollbar(ThemedFrame):
    """Rounded scrollbar that collapses to zero width when idle."""

    def __init__(self, master, theme: Theme, target: tk.Canvas,
                 bg_key: str = "surface", width: int = 10, **kwargs):
        self._bg_key = bg_key
        super().__init__(master, theme, bg_key=bg_key, width=width, **kwargs)
        self.target = target
        self._first, self._last = 0.0, 1.0
        self._dragging = False
        self._drag_offset = 0.0
        self._thumb_width = width
        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.bg)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._canvas.bind("<Configure>", lambda _e: self._draw())
        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

    def set_range(self, first: float, last: float) -> None:
        """Update the thumb position from the target canvas' yview()."""
        self._first, self._last = first, last
        self._draw()

    def _draw(self) -> None:
        self._canvas.delete("all")
        h = self._canvas.winfo_height()
        if h <= 1:
            return
        if self._first <= 0.001 and self._last >= 0.999:
            self.configure(width=0)  # nothing to scroll -> hide
            return
        self.configure(width=self._thumb_width)
        top = self._first * h
        bottom = max(self._last * h, top + 30)
        round_rect(self._canvas, 1, top, max(self._canvas.winfo_width() - 1, 2),
                   bottom, 4, fill=self.theme.border_strong, outline="")

    def _on_press(self, event) -> None:
        h = max(self._canvas.winfo_height(), 1)
        position = event.y / h
        if position < self._first:
            self.target.yview_moveto(max(0.0, self._first - 0.15))
        elif position > self._last:
            self.target.yview_moveto(min(1.0, self._last + 0.02))
        else:
            self._dragging = True
            self._drag_offset = position - self._first
        self._sync()

    def _on_drag(self, event) -> None:
        if not self._dragging:
            return
        h = max(self._canvas.winfo_height(), 1)
        self.target.yview_moveto(max(0.0, min(1.0, event.y / h - self._drag_offset)))
        self._sync()

    def _on_release(self, _e) -> None:
        self._dragging = False

    def _sync(self) -> None:
        self.set_range(*self.target.yview())

    def on_retheme(self, theme: Theme) -> None:
        self._canvas.configure(bg=self.bg)
        self._draw()


class ScrollFrame(ThemedFrame):
    """A vertically scrollable frame; add rows to ``.inner``."""

    def __init__(self, master, theme: Theme, bg_key: str = "surface", **kwargs):
        super().__init__(master, theme, bg_key=bg_key, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.bg)
        self.scrollbar = Scrollbar(self, theme, self.canvas, bg_key=bg_key)
        self.inner = tk.Frame(self.canvas, bg=self.bg)

        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        for widget in (self.canvas, self.inner):
            widget.bind("<MouseWheel>", self._on_wheel, add="+")

    def _on_inner_configure(self, _e) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._sync()

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)
        self._sync()

    def _sync(self) -> None:
        self.scrollbar.set_range(*self.canvas.yview())

    def _on_wheel(self, event) -> None:
        bbox = self.canvas.bbox("all")
        if not bbox or bbox[3] <= self.canvas.winfo_height():
            return
        self.canvas.yview_scroll(-int(event.delta / 60) * 20, "units")
        self._sync()

    def scroll_to_top(self) -> None:
        self.canvas.yview_moveto(0)
        self._sync()

    def clear(self) -> None:
        """Remove every child of the scrollable area."""
        for child in self.inner.winfo_children():
            child.destroy()

    def on_retheme(self, theme: Theme) -> None:
        self.canvas.configure(bg=self.bg)
        self.inner.configure(bg=self.bg)
        self.scrollbar.retheme(theme)


class ListRow(ThemedFrame):
    """A hoverable rounded row, used for search results."""

    def __init__(self, master, theme: Theme, command: Optional[Callable] = None,
                 bg_key: str = "surface", **kwargs):
        super().__init__(master, theme, bg_key=bg_key, cursor="hand2", **kwargs)
        self._command = command
        self._hover = False
        self._radius = RADIUS_SM
        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.bg)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._canvas.bind("<Button-1>", self._clicked)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _clicked(self, _e) -> None:
        if self._command:
            self._command()

    def _on_enter(self, _e) -> None:
        self._hover = True
        self._repaint()

    def _on_leave(self, _e) -> None:
        self._hover = False
        self._repaint()

    def _repaint(self) -> None:
        self._canvas.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            return
        fill = self.theme.surface_alt if self._hover else self.bg
        round_rect(self._canvas, 0, 0, w, h, self._radius, fill=fill, outline="")
        send_to_back(self._canvas)

    def on_retheme(self, theme: Theme) -> None:
        self._canvas.configure(bg=self.bg)
        self._repaint()

"""Base classes for themed widgets."""

from __future__ import annotations

import tkinter as tk

from .theme import Theme


class ThemedFrame(tk.Frame):
    """A ``tk.Frame`` that repaints itself when the theme changes.

    The background colour is looked up by *key* (e.g. ``"surface"``) rather
    than stored, so :meth:`retheme` can resolve it against a new palette.
    """

    def __init__(self, master, theme: Theme, bg_key: str = "surface", **kwargs):
        self.theme = theme
        self._bg_key = bg_key
        super().__init__(master, bg=getattr(theme, bg_key), **kwargs)

    @property
    def bg(self) -> str:
        """Current background colour of this frame."""
        return getattr(self.theme, self._bg_key)

    def retheme(self, theme: Theme) -> None:
        """Swap to a new theme and repaint this widget and its children."""
        self.theme = theme
        self.configure(bg=getattr(theme, self._bg_key))
        self.on_retheme(theme)
        for child in self.winfo_children():
            if isinstance(child, ThemedFrame):
                child.retheme(theme)

    def on_retheme(self, theme: Theme) -> None:
        """Hook for subclasses; called after the background is updated."""


#: Options that hold a colour, per widget class.
_COLOR_OPTIONS = ("bg", "fg", "activebackground", "activeforeground",
                  "insertbackground", "highlightbackground", "selectbackground",
                  "selectforeground", "disabledforeground", "troughcolor")


def recolor(widget: tk.Misc, mapping: dict) -> None:
    """Re-colour a single plain tk widget using ``mapping``."""
    for option in _COLOR_OPTIONS:
        try:
            current = widget.cget(option)
        except tk.TclError:
            continue
        if isinstance(current, str) and current in mapping:
            try:
                widget.configure(**{option: mapping[current]})
            except tk.TclError:
                pass


def apply_theme(widget: tk.Misc, theme: Theme, mapping: dict) -> None:
    """Re-theme an entire widget tree in one pass.

    Custom widgets repaint themselves, while the plain ``tk.Label`` /
    ``tk.Frame`` / ``tk.Entry`` children that panels use purely for layout are
    re-coloured by mapping their old palette entries onto the new ones.  The
    whole tree is visited because custom widgets are usually nested inside
    plain layout frames, so a direct-children walk would miss them.
    """
    if isinstance(widget, ThemedFrame):
        widget.retheme(theme)
    else:
        recolor(widget, mapping)
    for child in widget.winfo_children():
        apply_theme(child, theme, mapping)

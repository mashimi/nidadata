"""Canvas-drawn buttons with hover / press / disabled states."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import Callable, Optional

from .base import ThemedFrame
from .draw import blend, round_rect
from .theme import RADIUS_SM, Theme

VARIANTS = ("primary", "secondary", "ghost", "danger")


class Button(ThemedFrame):
    """A rounded button that sizes itself to its label.

    Variants: ``primary`` (filled accent), ``secondary`` (outlined),
    ``ghost`` (subtle) and ``danger`` (red outline).
    """

    def __init__(self, master, theme: Theme, text: str,
                 command: Optional[Callable] = None, variant: str = "primary",
                 width: Optional[int] = None, icon: str = "", **kwargs):
        super().__init__(master, theme, bg_key="surface", cursor="hand2", **kwargs)
        if variant not in VARIANTS:
            raise ValueError(f"unknown button variant: {variant!r}")
        self.variant = variant
        self.command = command
        self._text = text
        self._icon = icon
        self._hover = False
        self._pressed = False
        self._enabled = True
        self._padx = 18
        self._pady = 10
        self._min_width = width
        self._flash_job = None

        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.bg)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._colors_for(theme)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda _e: self._draw())
        self.update_idletasks()
        self._sync_size()

    # -- colours --------------------------------------------------------- #

    def _colors_for(self, theme: Theme) -> None:
        t = theme
        if self.variant == "primary":
            fill, hover, fg, line = t.accent, t.accent_hover, t.on_accent, t.accent
        elif self.variant == "danger":
            fill = t.danger_soft
            hover = blend(t.danger_soft, t.danger, 0.28)
            fg = line = t.danger
        elif self.variant == "ghost":
            fill, hover = t.surface_alt, blend(t.surface_alt, t.border, 0.7)
            fg, line = t.text_muted, t.border
        else:  # secondary
            fill = t.surface_alt
            hover = blend(t.surface_alt, t.border_strong, 0.55)
            fg, line = t.text, t.border_strong
        if not self._enabled:
            fill = hover = t.surface_alt
            fg, line = t.text_faint, t.border
        self._fill, self._hover_fill, self._fg, self._outline = fill, hover, fg, line

    # -- public state ---------------------------------------------------- #

    def set_text(self, text: str) -> None:
        self._text = text
        self._sync_size()

    def set_icon(self, icon: str) -> None:
        self._icon = icon
        self._sync_size()

    def set_command(self, command: Optional[Callable]) -> None:
        self.command = command

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._colors_for(self.theme)
        self._draw()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def flash(self, tone: str = "success", ms: int = 900) -> None:
        """Briefly tint the button to confirm an action."""
        colors = {"success": self.theme.success, "danger": self.theme.danger,
                  "accent": self.theme.accent}
        self._fill = self._hover_fill = colors.get(tone, self.theme.accent)
        self._draw()
        if self._flash_job:
            self.after_cancel(self._flash_job)
        self._flash_job = self.after(ms, self._end_flash)

    def _end_flash(self) -> None:
        self._flash_job = None
        self._colors_for(self.theme)
        self._draw()

    # -- events ---------------------------------------------------------- #

    def _on_enter(self, _e) -> None:
        if self._enabled:
            self._hover = True
            self._draw()

    def _on_leave(self, _e) -> None:
        self._hover = self._pressed = False
        self._draw()

    def _on_press(self, _e) -> None:
        if self._enabled:
            self._pressed = True
            self._draw()

    def _on_release(self, _e) -> None:
        if self._pressed and self._enabled and self.command:
            self.command()
        self._pressed = False
        self._draw()

    # -- painting -------------------------------------------------------- #

    def _label(self) -> str:
        return f"{self._icon}  {self._text}" if self._icon else self._text

    def _font(self):
        return self.theme.fonts("body_bold")

    def _sync_size(self) -> None:
        font = tkfont.Font(font=self._font())
        width = max(self._min_width or 0, font.measure(self._label()) + self._padx * 2)
        height = font.metrics("linespace") + self._pady * 2
        self.configure(width=width, height=height)
        self._draw()

    def _draw(self) -> None:
        self._canvas.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            return
        fill = self._hover_fill if (self._hover and self._enabled) else self._fill
        dy = 1 if (self._pressed and self._enabled) else 0
        round_rect(self._canvas, 0.5, 0.5, w - 0.5, h - 0.5, RADIUS_SM,
                   fill=fill, outline=self._outline, width=1)
        self._canvas.create_text(w / 2, h / 2 + dy, text=self._label(),
                                 fill=self._fg, font=self._font())

    def on_retheme(self, theme: Theme) -> None:
        self._canvas.configure(bg=self.bg)
        self._colors_for(theme)
        self._sync_size()


class IconButton(Button):
    """Fixed-size square button showing a single glyph."""

    def __init__(self, master, theme: Theme, icon: str, command=None,
                 tooltip: str = "", size: int = 36, **kwargs):
        self._size = size
        super().__init__(master, theme, "", command=command, variant="ghost",
                         width=size, **kwargs)
        self._icon = icon
        self._padx = 0
        self._pady = 0
        self.configure(width=size, height=size)
        self._draw()
        if tooltip:
            Tooltip(self, theme, tooltip)

    def _sync_size(self) -> None:  # a square stays a square
        self.configure(width=self._size, height=self._size)
        self._draw()

    def set_icon(self, icon: str) -> None:
        self._icon = icon
        self._draw()

    def _draw(self) -> None:
        self._canvas.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            return
        fill = self._hover_fill if (self._hover and self._enabled) else self._fill
        round_rect(self._canvas, 0.5, 0.5, w - 0.5, h - 0.5, RADIUS_SM,
                   fill=fill, outline=self._outline, width=1)
        self._canvas.create_text(w / 2, h / 2, text=self._icon, fill=self._fg,
                                 font=self.theme.fonts("body"))


class Tooltip:
    """Hover tooltip bound to any widget."""

    def __init__(self, widget: tk.Widget, theme: Theme, text: str, delay: int = 450):
        self.widget = widget
        self.theme = theme
        self.text = text
        self.delay = delay
        self._job = None
        self._window: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", lambda _e: self._schedule(), add="+")
        widget.bind("<Leave>", lambda _e: self._hide(), add="+")
        widget.bind("<ButtonPress>", lambda _e: self._hide(), add="+")

    def _schedule(self) -> None:
        self._cancel()
        self._job = self.widget.after(self.delay, self._show)

    def _cancel(self) -> None:
        if self._job:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _show(self) -> None:
        if self._window or not self.text:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self._window = tk.Toplevel(self.widget)
        self._window.wm_overrideredirect(True)
        self._window.wm_geometry(f"+{x}+{y}")
        frame = tk.Frame(self._window, bg=self.theme.border_strong)
        frame.pack()
        tk.Label(frame, text=self.text, bg=self.theme.border_strong,
                 fg=self.theme.text, font=self.theme.fonts("small"),
                 padx=8, pady=4).pack()

    def _hide(self) -> None:
        self._cancel()
        if self._window:
            self._window.destroy()
            self._window = None

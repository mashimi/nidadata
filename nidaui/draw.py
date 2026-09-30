"""Low-level drawing helpers shared by the NIDA UI widgets.

Tkinter can only draw rectangles and ovals, so rounded corners are faked
with smoothed polygons.  These helpers keep that trick in one place.
"""

from __future__ import annotations

import tkinter as tk
from typing import Tuple

from .theme import RADIUS, Theme

RGB = Tuple[int, int, int]


def hex_to_rgb(color: str) -> RGB:
    """``"#4f8cff"`` -> ``(79, 140, 255)``."""
    c = color.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def blend(color_a: str, color_b: str, t: float) -> str:
    """Linearly mix two hex colours; ``t=0`` -> a, ``t=1`` -> b."""
    a, b = hex_to_rgb(color_a), hex_to_rgb(color_b)
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def readable_on(color: str) -> str:
    """Return near-black or white - whichever reads better on ``color``."""
    r, g, b = hex_to_rgb(color)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#0b0f16" if luminance > 0.6 else "#ffffff"


def send_to_back(widget: tk.Misc) -> None:
    """Push a widget behind its siblings.

    ``tk.Misc.lower()`` is shadowed on ``Canvas`` (it maps to the canvas
    *item* command, which needs a tag), so the window-level ``lower`` is
    invoked directly here.  Background canvases use ``place``, which stacks
    above ``pack``-managed children, so this is required to keep card
    content visible.
    """
    widget.tk.call("lower", widget._w)


def round_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float,
               radius: int = RADIUS, **kwargs) -> int:
    """Draw a rounded rectangle on ``canvas`` and return the item id."""
    radius = max(0, min(radius, int((y2 - y1) / 2), int((x2 - x1) / 2)))
    points = [
        x1 + radius, y1, x2 - radius, y1,
        x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2,
        x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius,
        x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def draw_shadow(canvas: tk.Canvas, width: int, height: int, theme: Theme,
                radius: int = RADIUS, spread: int = 10) -> None:
    """Soft fake drop shadow under a card (light theme only)."""
    if theme.is_dark:
        return
    steps = 5
    for i in range(steps, 0, -1):
        t = i / (steps + 1)
        round_rect(
            canvas, spread * t, spread * t + 3,
            width - spread * t, height - spread * t + 5,
            radius=radius + spread * t,
            fill=blend(theme.bg, theme.shadow, 0.16 * t), outline="",
        )

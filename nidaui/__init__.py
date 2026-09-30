"""NIDA desktop UI - a small custom widget kit on top of tkinter.

Modules:
    theme      design tokens (palettes, fonts, spacing)
    draw       rounded-rectangle / colour helpers
    base       ThemedFrame
    card       Card and Badge
    buttons    Button, IconButton, Tooltip
    fields     Field (text input)
    containers ScrollFrame, Scrollbar, ListRow
    demo       sample records for offline preview
"""

from .base import ThemedFrame
from .buttons import Button, IconButton, Tooltip
from .card import Badge, Card
from .containers import ListRow, Scrollbar, ScrollFrame
from .fields import Field
from .theme import DARK, LIGHT, PALETTES, FontBook, Palette, Theme

__all__ = [
    "ThemedFrame", "Button", "IconButton", "Tooltip",
    "Badge", "Card", "Field",
    "ListRow", "Scrollbar", "ScrollFrame",
    "Theme", "Palette", "FontBook", "DARK", "LIGHT", "PALETTES",
]

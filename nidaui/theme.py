"""Design tokens (colours, spacing, fonts) for the NIDA desktop app.

Two palettes are available - a modern dark theme (default) and a light
theme.  Every widget pulls its colours from a :class:`Theme` instance so a
theme switch only needs to rebuild the widget tree.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class Palette:
    """A flat set of colours used across the UI."""

    name: str
    bg: str  # window background
    surface: str  # card / panel background
    surface_alt: str  # nested surface, hover row
    surface_sunken: str  # inputs
    border: str  # subtle borders
    border_strong: str  # focused / emphasized borders
    text: str  # primary text
    text_muted: str  # secondary text
    text_faint: str  # tertiary text
    accent: str  # primary action
    accent_hover: str
    accent_soft: str  # tinted accent background
    on_accent: str  # text on accent
    success: str
    success_soft: str
    warning: str
    danger: str
    danger_soft: str
    shadow: str  # card shadow (light theme only)
    scrim: str  # scrollbar trough


DARK = Palette(
    name="dark",
    bg="#0e1117",
    surface="#161b22",
    surface_alt="#1c2330",
    surface_sunken="#0b0f16",
    border="#262d3a",
    border_strong="#3d4757",
    text="#e6edf3",
    text_muted="#9aa7b8",
    text_faint="#6e7b8d",
    accent="#4f8cff",
    accent_hover="#6ea1ff",
    accent_soft="#17233c",
    on_accent="#ffffff",
    success="#3fb950",
    success_soft="#12261a",
    warning="#d29922",
    danger="#f85149",
    danger_soft="#2b1416",
    shadow="#000000",
    scrim="#10151d",
)

LIGHT = Palette(
    name="light",
    bg="#f3f5f9",
    surface="#ffffff",
    surface_alt="#f6f8fc",
    surface_sunken="#eef1f6",
    border="#dfe4ec",
    border_strong="#b9c2d0",
    text="#16202e",
    text_muted="#5b6779",
    text_faint="#8b95a6",
    accent="#2563eb",
    accent_hover="#1d4ed8",
    accent_soft="#e6efff",
    on_accent="#ffffff",
    success="#1a7f37",
    success_soft="#e6f5ea",
    warning="#9a6700",
    danger="#cf222e",
    danger_soft="#fdeceb",
    shadow="#9aa5b5",
    scrim="#e9edf3",
)

PALETTES: Dict[str, Palette] = {"dark": DARK, "light": LIGHT}


@dataclass
class Theme:
    """Active palette + a lazily built :class:`FontBook`."""

    palette: Palette = field(default_factory=lambda: DARK)
    _root: Optional["tk.Misc"] = None
    _fonts: Optional["FontBook"] = None

    def __getattr__(self, item: str):
        # Only called for genuinely missing attributes -> delegate to palette
        palette = object.__getattribute__(self, "palette")
        if hasattr(palette, item):
            return getattr(palette, item)
        raise AttributeError(item)

    @property
    def is_dark(self) -> bool:
        return self.palette.name == "dark"

    @property
    def fonts(self) -> "FontBook":
        if self._fonts is None:
            root = self._root
            if root is None:
                raise RuntimeError("Theme needs a tk root before fonts are used")
            self._fonts = FontBook(root)
        return self._fonts

    def bind_root(self, root: "tk.Misc") -> None:
        self._root = root
        self._fonts = None  # force a rebuild against the new interpreter

    def swap(self) -> "Theme":
        """Return the opposite theme (dark <-> light)."""
        other = LIGHT if self.is_dark else DARK
        return Theme(palette=other, _root=self._root)

    def color_map(self, new: "Theme") -> Dict[str, str]:
        """Map every colour of this palette onto the equivalent in ``new``.

        Used to re-colour plain ``tk.Label`` / ``tk.Entry`` children after a
        theme switch without having to re-apply their styles by hand.  The
        role names are resolved in a fixed order so that palettes sharing a
        value (the light ``surface`` and ``on_accent`` are both ``#ffffff``)
        still map back to the right colour.
        """
        ordered = (
            "bg", "surface", "surface_alt", "surface_sunken", "border",
            "border_strong", "text", "text_muted", "text_faint", "accent",
            "accent_hover", "on_accent", "success", "warning", "danger", "shadow",
        )
        mapping: Dict[str, str] = {}
        for name in ordered:  # first match wins, so listed roles take priority
            if hasattr(new.palette, name):
                mapping.setdefault(getattr(self.palette, name),
                                   getattr(new.palette, name))
        return mapping


# ---------------------------------------------------------------------- #
# Fonts
# ---------------------------------------------------------------------- #

_UI_CANDIDATES = ("Segoe UI Variable Text", "Segoe UI", "Inter", "SF Pro Text",
                  "Helvetica Neue", "DejaVu Sans")
_MONO_CANDIDATES = ("Cascadia Mono", "Consolas", "JetBrains Mono", "SF Mono",
                    "DejaVu Sans Mono")

#  size name -> (size, weight)
TYPE_SCALE = {
    "display": (22, "bold"),
    "title": (14, "bold"),
    "body": (10, "normal"),
    "body_bold": (10, "bold"),
    "small": (9, "normal"),
    "small_bold": (9, "bold"),
    "tiny": (8, "normal"),
    "mono": (11, "normal"),
    "mono_bold": (12, "bold"),
}

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 18, "xl": 26, "xxl": 36}
RADIUS = 12
RADIUS_SM = 8


def pick_family(root, candidates, fallback: str) -> str:
    """Return the first installed font family from ``candidates``."""
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return name
    return fallback


class FontBook:
    """Creates and caches ``tkinter`` fonts for a given family pair."""

    def __init__(self, root) -> None:
        self.root = root
        self.ui = pick_family(root, _UI_CANDIDATES, "TkDefaultFont")
        self.mono = pick_family(root, _MONO_CANDIDATES, "TkFixedFont")
        self._cache: Dict[str, tkfont.Font] = {}

    def __call__(self, style: str) -> tkfont.Font:
        if style not in self._cache:
            size, weight = TYPE_SCALE[style]
            family = self.mono if style.startswith("mono") else self.ui
            self._cache[style] = tkfont.Font(
                root=self.root, family=family, size=size, weight=weight
            )
        return self._cache[style]

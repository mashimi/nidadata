"""Right-hand panel: renders a single person's record."""

from __future__ import annotations

import base64
import datetime
import io
import tkinter as tk
from typing import Callable, Dict, Optional

from PIL import Image, ImageTk

from .buttons import Button
from .card import Badge, Card
from .containers import ScrollFrame
from .panels import display_nin, record_label
from .theme import Theme

#: Preferred raw key -> (friendly label, group) in display order.
FIELD_LAYOUT = [
    ("FULLNAME", "Full name", "Identity"),
    ("GENDER", "Gender", "Identity"),
    ("DATE_OF_BIRTH", "Date of birth", "Identity"),
    ("PLACE_OF_BIRTH", "Place of birth", "Identity"),
    ("NATIONALITY", "Nationality", "Identity"),
    ("NIN", "National ID", "Identity"),
    ("CARDCATEGORY", "Card category", "Card"),
    ("CARDISSUEDATE", "Issued on", "Card"),
    ("EXPIRY_DATE", "Expires on", "Card"),
    ("DISTRICT", "District", "Address"),
    ("REGION", "Region", "Address"),
    ("WARD", "Ward", "Address"),
    ("VILLAGE", "Village", "Address"),
    ("PHONE", "Phone", "Contact"),
    ("OCCUPATION", "Occupation", "Contact"),
]

_LABELS = {raw: label for raw, label, _ in FIELD_LAYOUT}
# Fallback labels for keys the API may return that are not in the layout.
_PRETTY = {
    "FIRSTNAME": "First name", "MIDDLENAME": "Middle name",
    "LASTNAME": "Last name", "DISTRICTCODE": "District code",
    "CARDTYPE": "Card type", "ISSUEDATE": "Issued on",
}
#: Keys that hold image data rather than text.
IMAGE_KEYS = {"photo", "signature"}
GROUP_OF = {raw: group for raw, _, group in FIELD_LAYOUT}


def lookup(record: Dict, *names: str, default=None):
    """Case-insensitive field lookup.

    NIDA's raw payload uses SHOUTING keys while :meth:`Nida.load_user`
    returns capitalised ones, and cached records are stored as text, so a
    plain ``record.get("PHOTO")`` is not reliable.
    """
    lowered = {str(key).lower(): value for key, value in record.items()}
    for name in names:
        if name in record:
            return record[name]
        if str(name).lower() in lowered:
            return lowered[str(name).lower()]
    return default


def friendly_key(key: str) -> str:
    """``DATE_OF_BIRTH`` -> ``Date of birth``."""
    upper = str(key).upper()
    if upper in _LABELS:
        return _LABELS[upper]
    if upper in _PRETTY:
        return _PRETTY[upper]
    return str(key).replace("_", " ").title()


def age_from(dob) -> Optional[int]:
    """Best-effort age from ``YYYY-MM-DD`` (or ``DD/MM/YYYY``) dates."""
    text = str(dob).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            born = datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        today = datetime.date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return None


def shorten(value, limit: int = 160) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def to_photo_ref(value, size):
    """Decode ``value`` to a PIL image, thumbnailed to fit ``size``."""
    image = to_image(value)
    if image is None:
        return None
    display = image.copy()
    display.thumbnail(size)
    if display.mode not in ("RGB", "RGBA", "P"):
        display = display.convert("RGB")
    return ImageTk.PhotoImage(display)


def to_image(value):
    """Return a PIL image from either a PIL image or a base64 string."""
    if isinstance(value, Image.Image):
        return value
    if isinstance(value, str):
        try:
            return Image.open(io.BytesIO(base64.b64decode(value)))
        except Exception:
            return None
    return None


class ProfilePanel(Card):
    """Shows the selected person: photo, signature and every field."""

    PHOTO_SIZE = (150, 184)
    SIGNATURE_SIZE = (250, 88)

    def __init__(self, master, theme: Theme,
                 on_save: Callable[[str, object], None],
                 on_copy: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(master, theme, title="Record", **kwargs)
        self._on_save = on_save
        self._on_copy = on_copy
        self._current: Dict = {}
        self._photo_ref = None
        self._signature_ref = None

        self.photo_label = tk.Label(self.body, text="No photo", width=18, height=9,
                                    bg=theme.surface_sunken, fg=theme.text_faint,
                                    font=theme.fonts("small"))
        self.photo_label.pack()

        self.name_label = tk.Label(self.body, text="Nothing selected", anchor="w",
                                   bg=theme.surface, fg=theme.text,
                                   font=theme.fonts("display"))
        self.nin_label = tk.Label(self.body, text="", anchor="w", bg=theme.surface,
                                  fg=theme.accent, font=theme.fonts("mono"))
        self.name_label.pack(anchor="w", pady=(14, 2))
        self.nin_label.pack(anchor="w")

        self.chips = tk.Frame(self.body, bg=theme.surface)
        self.chips.pack(anchor="w", pady=(10, 0))

        self.details = ScrollFrame(self.body, theme)
        self.details.pack(fill="both", expand=True, pady=(16, 0))

        self.signature_label = tk.Label(self.body, text="No signature",
                                        bg=theme.surface_sunken, fg=theme.text_faint,
                                        font=theme.fonts("small"))
        self.signature_label.pack(pady=(14, 0))

        self.actions = tk.Frame(self.body, bg=theme.surface)
        self.actions.pack(fill="x", pady=(12, 0))
        self.save_photo = Button(self.actions, theme, "Save photo", variant="secondary",
                                 command=lambda: self._save("Photo"))
        self.save_photo.pack(side="left")
        self.save_signature = Button(self.actions, theme, "Save signature",
                                     variant="secondary",
                                     command=lambda: self._save("Signature"))
        self.save_signature.pack(side="left", padx=(8, 0))

        self.show_empty()

    # -- public ----------------------------------------------------------- #

    def show_empty(self, message: str = "Nothing selected") -> None:
        """Reset the panel to its placeholder state."""
        self._current = {}
        self._photo_ref = self._signature_ref = None
        self.set_badge("", "muted")
        self.photo_label.configure(image="", text="No photo", width=18, height=9)
        self.nin_label.configure(text="")
        self.name_label.configure(text=message)
        for chip in self.chips.winfo_children():
            chip.destroy()
        self.signature_label.configure(image="", text="No signature")
        self.details.clear()
        self._set_actions_enabled(False)

    def show_record(self, nin: str, record: Dict, from_cache: bool = False) -> None:
        """Render a fetched (or cached) record."""
        self._current = record
        self.name_label.configure(text=record_label(record))
        self.nin_label.configure(text=display_nin(nin))
        self.set_badge("cached" if from_cache else "live",
                       "muted" if from_cache else "success")
        self._render_chips(record)
        self._render_details(record)
        self._render_images(record)
        self._set_actions_enabled(True)

    # -- rendering -------------------------------------------------------- #

    def _render_chips(self, record: Dict) -> None:
        for chip in self.chips.winfo_children():
            chip.destroy()
        gender = str(lookup(record, "GENDER", default="")).strip().upper()
        if gender in ("M", "MALE"):
            Badge(self.chips, self.theme, "Male", bg=self.theme.accent_soft,
                  fg=self.theme.accent).pack(side="left")
        elif gender in ("F", "FEMALE"):
            Badge(self.chips, self.theme, "Female", bg=self.theme.danger_soft,
                  fg=self.theme.danger).pack(side="left")
        dob = lookup(record, "DATE_OF_BIRTH")
        if dob:
            age = age_from(dob)
            label = f"Age {age}" if age is not None else shorten(dob, 18)
            Badge(self.chips, self.theme, label, bg=self.theme.surface_alt,
                  fg=self.theme.text_muted).pack(side="left", padx=(6, 0))

    def _render_details(self, record: Dict) -> None:
        self.details.clear()
        for raw, value in record.items():
            if str(raw).lower() in IMAGE_KEYS or value in (None, ""):
                continue
            row = tk.Frame(self.details.inner, bg=self.theme.surface)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=friendly_key(raw), anchor="nw", width=18,
                     justify="left", bg=self.theme.surface, fg=self.theme.text_muted,
                     font=self.theme.fonts("small")).pack(side="left")
            shown = shorten(value)
            label = tk.Label(row, text=shown, anchor="w", justify="left",
                             wraplength=320, bg=self.theme.surface, fg=self.theme.text,
                             font=self.theme.fonts("small_bold"))
            label.pack(side="left", fill="x", expand=True)
            if self._on_copy:
                label.bind("<Button-1>", lambda _e, v=shown: self._on_copy(v), add="+")
                label.bind("<Enter>", self._hover_on, add="+")
                label.bind("<Leave>", self._hover_off, add="+")
        self.details.scroll_to_top()

    def _hover_on(self, event) -> None:
        event.widget.configure(cursor="hand2", fg=self.theme.accent)

    def _hover_off(self, event) -> None:
        event.widget.configure(cursor="", fg=self.theme.text)

    def _render_images(self, record: Dict) -> None:
        self._photo_ref = self._signature_ref = None
        photo = to_photo_ref(lookup(record, "PHOTO"), self.PHOTO_SIZE)
        if photo is not None:
            self._photo_ref = photo
            self.photo_label.configure(image=photo, text="", width=0, height=0)
        else:
            self.photo_label.configure(image="", text="No photo", width=18, height=9)
        signature = to_photo_ref(lookup(record, "SIGNATURE"), self.SIGNATURE_SIZE)
        if signature is not None:
            self._signature_ref = signature
            self.signature_label.configure(image=signature, text="")
        else:
            self.signature_label.configure(image="", text="No signature")

    def _set_actions_enabled(self, enabled: bool) -> None:
        self.save_photo.set_enabled(enabled)
        self.save_signature.set_enabled(enabled)

    def _save(self, field: str) -> None:
        """Decode the stored image (PIL or base64) and hand it to the app."""
        image = to_image(lookup(self._current, field))
        if image is not None:
            self._on_save(field, image)

"""Offline sample records so the UI can be previewed without network access.

``python app.py --demo`` seeds the local history with these fake people and
uses them instead of hitting the real NIDA service.
"""

from __future__ import annotations

import base64
import io
from typing import Dict, List

from PIL import Image, ImageDraw

# Synthetic faces/scribbles - deliberately not real people.
_PALETTES = [
    ((214, 226, 245), (120, 150, 190)),
    ((226, 240, 232), (110, 160, 140)),
    ((244, 232, 226), (180, 130, 110)),
    ((232, 228, 244), (140, 125, 185)),
]


def _fake_photo(seed: int, size=(260, 320)) -> Image.Image:
    """Draw a simple avatar placeholder."""
    light, dark = _PALETTES[seed % len(_PALETTES)]
    img = Image.new("RGB", size, light)
    draw = ImageDraw.Draw(img)
    w, h = size
    draw.ellipse([w * 0.28, h * 0.16, w * 0.72, h * 0.60], fill=dark)
    draw.ellipse([w * 0.12, h * 0.62, w * 0.88, h * 1.10], fill=dark)
    return img


def _fake_signature(seed: int, size=(420, 140)) -> Image.Image:
    """Draw a squiggle standing in for a signature."""
    light, dark = _PALETTES[seed % len(_PALETTES)]
    img = Image.new("RGB", size, (250, 250, 250))
    draw = ImageDraw.Draw(img)
    w, h = size
    x, y = w * 0.12, h * 0.62
    for i in range(160):
        x += 2.0
        y += (seed % 5 - 2) * 0.35
        if i % 37 == 0:
            y = h * 0.62
        draw.point((x, y + ((x - w * 0.12) % 22) - 11), fill=dark)
    draw.line([(w * 0.12, h * 0.80), (w * 0.88, h * 0.80)], fill=(200, 200, 205))
    return img


def _b64(img: Image.Image) -> str:
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _record(seed: int, first: str, middle: str, last: str, nin: str,
            dob: str, place: str, gender: str, district: str, region: str,
            ward: str, village: str, phone: str, occupation: str,
            issue: str, expire: str, card: str, district_code: str) -> Dict:
    return {
        "NIN": nin,
        "FULLNAME": f"{first} {middle} {last}".strip(),
        "FIRSTNAME": first,
        "MIDDLENAME": middle,
        "LASTNAME": last,
        "DATE_OF_BIRTH": dob,
        "PLACE_OF_BIRTH": place,
        "GENDER": gender,
        "NATIONALITY": "Tanzanian",
        "CARDCATEGORY": card,
        "CARDISSUEDATE": issue,
        "EXPIRY_DATE": expire,
        "DISTRICT": district,
        "REGION": region,
        "WARD": ward,
        "VILLAGE": village,
        "DISTRICTCODE": district_code,
        "PHONE": phone,
        "OCCUPATION": occupation,
        "PHOTO": _b64(_fake_photo(seed)),
        "SIGNATURE": _b64(_fake_signature(seed)),
    }


DEMO_RECORDS: List[Dict] = [
    _record(0, "Amani", "Jabari", "Mwakalinga", "19990512141150000123",
            "1999-05-12", "Dodoma", "M", "Dodoma Urban", "Dodoma",
            "Kikuu", "Kikuu", "+255 754 112 233", "Accountant",
            "2021-03-14", "2031-03-13", "A", "0201"),
    _record(1, "Neema", "Salvatory", "Kimaro", "20010730451230000456",
            "2001-07-30", "Arusha", "F", "Arusha City", "Arusha",
            "Ndareno", "Ndareno", "+255 712 998 877", "Teacher",
            "2022-08-02", "2032-08-01", "A", "0202"),
    _record(2, "Baraka", "Emmanuel", "Mtemi", "19881120441122000789",
            "1988-11-20", "Mwanza", "M", "Mwanza City", "Mwanza",
            "Nyamagana", "Kisutu", "+255 733 445 566", "Engineer",
            "2020-01-19", "2030-01-18", "B", "0203"),
    _record(3, "Zawadi", "Hamisi", "Mrisho", "19951210223344000901",
            "1995-12-10", "Tanga", "F", "Tanga City", "Tanga",
            "Mabambakisi", "Mabambakisi", "+255 768 221 334", "Nurse",
            "2023-05-30", "2033-05-29", "A", "0204"),
]


def load_demo(nin: str) -> Dict:
    """Return a demo record whose NIN matches ``nin`` (any NIN works)."""
    digits = "".join(ch for ch in str(nin) if ch.isdigit())
    for record in DEMO_RECORDS:
        if record["NIN"] == digits:
            return record
    template = DEMO_RECORDS[int(digits[-2:]) % len(DEMO_RECORDS)]
    copy = dict(template)
    copy["NIN"] = digits
    return copy

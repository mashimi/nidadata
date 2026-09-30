"""nida - fetch Tanzanian National ID (NIDA) holder information.

Usage:
    from nida import load_user
    user = load_user("19990512141150000123")
    print(user.Fullname)
    user.Photo.save("photo.jpg")   # decoded into a PIL image

Raises subclasses of :class:`NidaError` on failure (connection problems,
invalid ID, record not found, unexpected responses).
"""

from __future__ import annotations

import base64
import io
import logging
import re
from typing import Any, Dict as PlainDict, Optional, Union

import requests
from addict import Dict as AttrDict
from PIL import Image

from .exceptions import (
    NidaConnectionError,
    NidaError,
    NidaInvalidIDError,
    NidaNotFoundError,
)

__version__ = "0.2.0"

__all__ = [
    "Nida",
    "load_user",
    "NidaError",
    "NidaConnectionError",
    "NidaInvalidIDError",
    "NidaNotFoundError",
    "__version__",
]

logger = logging.getLogger(__name__)

NIN_LENGTH = 20
NIN_RE = re.compile(r"[^0-9]")
FULL_NIN_RE = re.compile(r"\d{%d}" % NIN_LENGTH)

#: Fields that hold a base64-encoded image.
IMAGE_FIELDS = ("PHOTO", "SIGNATURE")


class Nida:
    """Client for the NIDA online REST service (ors.brela.go.tz)."""

    BASE_URL = "https://ors.brela.go.tz/um/load/load_nida/{}"
    DEFAULT_TIMEOUT = 15

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be a positive number of seconds")
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def load_user(
        self, national_id: Union[str, int], as_json: bool = False
    ) -> Union[AttrDict, PlainDict]:
        """Fetch the information of the holder of ``national_id``.

        Args:
            national_id: 20-digit National Identification Number (NIN).
            as_json: If True, return the raw API payload untouched;
                otherwise return an ``addict.Dict`` with Capitalized keys
                where PHOTO/SIGNATURE are decoded to PIL Images.

        Raises:
            NidaInvalidIDError: the national ID is not 20 digits.
            NidaNotFoundError: NIDA reports no record for the ID.
            NidaConnectionError: the request failed or timed out.
            NidaError: any other unexpected API response.
        """
        national_id = clean_nin(national_id)
        user_data = self._fetch(national_id)
        if as_json:
            return user_data
        return self._preprocess(user_data)

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    def _fetch(self, national_id: str) -> PlainDict:
        try:
            response = requests.post(
                self.BASE_URL.format(national_id),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise NidaConnectionError(
                f"NIDA did not respond within {self.timeout}s."
            ) from exc
        except requests.RequestException as exc:
            raise NidaConnectionError(f"Could not reach NIDA servers: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise NidaError(
                f"NIDA returned a non-JSON response (HTTP {response.status_code})."
            ) from exc

        if not isinstance(payload, dict):
            raise NidaError(f"Unexpected response from NIDA: {payload!r}")

        obj = payload.get("obj") or {}
        result = obj.get("result")
        if result:
            return result

        error = obj.get("error")
        if error:
            raise NidaNotFoundError(str(error))

        raise NidaError(f"Unexpected response from NIDA: {payload!r}")

    @staticmethod
    def _bytes_to_img(image_str: str) -> Optional[Image.Image]:
        try:
            decoded = base64.b64decode(image_str)
            return Image.open(io.BytesIO(decoded))
        except Exception:  # noqa: BLE001 - never let a bad image kill a lookup
            logger.warning("Failed to decode an image from the NIDA response.")
            return None

    @classmethod
    def _preprocess(cls, user_data: PlainDict) -> AttrDict:
        data = dict(user_data)
        for key in IMAGE_FIELDS:
            value = data.get(key)
            if isinstance(value, str):
                data[key] = cls._bytes_to_img(value)
        return AttrDict({key.capitalize(): val for key, val in data.items()})


def clean_nin(national_id: Union[str, int]) -> str:
    """Normalise and validate a National ID, returning 20 digits."""
    if isinstance(national_id, bool) or not isinstance(national_id, (str, int)):
        raise NidaInvalidIDError("National ID must be a string or an integer.")
    cleaned = NIN_RE.sub("", str(national_id))
    if not FULL_NIN_RE.fullmatch(cleaned):
        raise NidaInvalidIDError(
            "National ID must be exactly 20 digits, e.g. '19990512141150000123'."
        )
    return cleaned


def load_user(
    national_id: Union[str, int], as_json: bool = False
) -> Union[AttrDict, PlainDict]:
    """Convenience wrapper: fetch user information for a national ID."""
    return Nida().load_user(national_id, as_json=as_json)

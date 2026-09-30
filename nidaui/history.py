"""History cache - a tiny JSON store for previously fetched records.

Only the text fields are persisted; the base64 photo/signature blobs are
far too large to keep on disk for a convenience feature.
"""

from __future__ import annotations

import json
import os
from typing import Dict

#: Fields never written to disk (large base64 blobs).
SKIP_KEYS = ("Photo", "Signature", "PHOTO", "SIGNATURE")


def history_path() -> str:
    """Location of the cache file, next to the project root."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "nida_history.json")


def load(path: str = None) -> Dict[str, Dict]:
    """Read the cache; a missing or corrupt file yields an empty dict."""
    path = path or history_path()
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save(records: Dict[str, Dict], path: str = None) -> None:
    """Write the cache, stripping image fields."""
    path = path or history_path()
    payload = {
        nin: {k: str(v) for k, v in record.items() if k not in SKIP_KEYS}
        for nin, record in records.items()
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)  # atomic, so a crash can't truncate the cache


def remember(records: Dict[str, Dict], nin: str, record: Dict,
             path: str = None) -> None:
    """Add ``record`` to the in-memory cache and persist it."""
    records[nin] = {k: v for k, v in record.items() if k not in SKIP_KEYS}
    save(records, path)

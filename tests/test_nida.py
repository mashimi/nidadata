"""Unit tests for the nida package - no network access required.

Run with:  python -m pytest -q      (or: python -m unittest discover tests)
"""

from __future__ import annotations

import base64
import io
import unittest

import requests
from PIL import Image

import nida
from nida import Nida, clean_nin
from nida.exceptions import (
    NidaConnectionError,
    NidaError,
    NidaInvalidIDError,
    NidaNotFoundError,
)

VALID_NIN = "19990512141150000123"


def _b64_image(color=(10, 120, 200), size=(20, 24)) -> str:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


PAYLOAD = {
    "obj": {
        "result": {
            "NIN": VALID_NIN,
            "FULLNAME": "Amani Mwakalinga",
            "FIRSTNAME": "Amani",
            "LASTNAME": "Mwakalinga",
            "GENDER": "M",
            "DATE_OF_BIRTH": "1999-05-12",
            "PHOTO": _b64_image(),
            "SIGNATURE": _b64_image((200, 40, 40)),
        }
    }
}


class FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, payload, status_code=200, raise_json=False):
        self._payload = payload
        self.status_code = status_code
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


def _patch_post(testcase, response=None, side_effect=None):
    """Replace ``requests.post`` and record the call arguments.

    ``side_effect`` is an exception instance to raise (or an exception class);
    pass ``response`` for the success case.
    """
    captured = {}

    def _post(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        if side_effect is not None:
            raise side_effect
        return response

    original = requests.post
    requests.post = _post
    testcase.addCleanup(lambda: setattr(requests, "post", original))
    return captured


class TestCleanNin(unittest.TestCase):
    def test_accepts_plain_digits(self):
        self.assertEqual(clean_nin(VALID_NIN), VALID_NIN)

    def test_strips_spaces(self):
        self.assertEqual(clean_nin("1999 0512 1411 5000 0123"), VALID_NIN)

    def test_accepts_int(self):
        self.assertEqual(clean_nin(19990512141150000123), VALID_NIN)

    def test_rejects_wrong_length(self):
        for bad in ("123", "1999051214115000012", VALID_NIN + "0"):
            with self.assertRaises(NidaInvalidIDError):
                clean_nin(bad)

    def test_rejects_non_digits(self):
        with self.assertRaises(NidaInvalidIDError):
            clean_nin("abcdefghijklmnopqrst")

    def test_rejects_wrong_type(self):
        for bad in (None, [], {}, 1.5, True):
            with self.assertRaises(NidaInvalidIDError):
                clean_nin(bad)


class TestNidaClient(unittest.TestCase):
    def setUp(self):
        self.client = Nida(timeout=5)

    def test_load_user_decodes_images(self):
        _patch_post(self, FakeResponse(PAYLOAD))
        user = self.client.load_user(VALID_NIN)
        self.assertEqual(user["Nin"], VALID_NIN)  # keys are Capitalized
        self.assertIsInstance(user["Fullname"], str)
        self.assertIsInstance(user.Photo, Image.Image)
        self.assertIsInstance(user.Signature, Image.Image)
        self.assertEqual(user.Photo.size, (20, 24))

    def test_load_user_as_json_keeps_base64(self):
        _patch_post(self, FakeResponse(PAYLOAD))
        raw = self.client.load_user(VALID_NIN, as_json=True)
        self.assertEqual(raw["PHOTO"], PAYLOAD["obj"]["result"]["PHOTO"])

    def test_request_uses_timeout_and_url(self):
        captured = _patch_post(self, FakeResponse(PAYLOAD))
        self.client.load_user(VALID_NIN)
        self.assertIn(VALID_NIN, captured["args"][0])
        self.assertEqual(captured["kwargs"]["timeout"], 5)
        self.assertNotIn("Content-Length", captured["kwargs"]["headers"])

    def test_invalid_nin_never_hits_network(self):
        def _boom(*args, **kwargs):
            raise AssertionError("should not make a request")

        _patch_post(self, side_effect=AssertionError("should not make a request"))
        with self.assertRaises(NidaInvalidIDError):
            self.client.load_user("123")

    def test_not_found_error(self):
        _patch_post(self, FakeResponse({"obj": {"error": "no such id"}}))
        with self.assertRaises(NidaNotFoundError):
            self.client.load_user(VALID_NIN)

    def test_non_json_response(self):
        _patch_post(self, FakeResponse(None, raise_json=True))
        with self.assertRaises(NidaError):
            self.client.load_user(VALID_NIN)

    def test_unexpected_payload(self):
        _patch_post(self, FakeResponse({"obj": {}}))
        with self.assertRaises(NidaError):
            self.client.load_user(VALID_NIN)

    def test_timeout_becomes_connection_error(self):
        _patch_post(self, side_effect=requests.Timeout())
        with self.assertRaises(NidaConnectionError):
            self.client.load_user(VALID_NIN)

    def test_network_error_becomes_connection_error(self):
        _patch_post(self, side_effect=requests.ConnectionError())
        with self.assertRaises(NidaConnectionError):
            self.client.load_user(VALID_NIN)

    def test_missing_image_keys_do_not_crash(self):
        payload = {"obj": {"result": {"NIN": VALID_NIN, "FULLNAME": "X"}}}
        _patch_post(self, FakeResponse(payload))
        user = self.client.load_user(VALID_NIN)
        self.assertNotIn("Photo", user)

    def test_broken_image_is_ignored(self):
        payload = {"obj": {"result": {"NIN": VALID_NIN, "PHOTO": "not-base64!!"}}}
        _patch_post(self, FakeResponse(payload))
        user = self.client.load_user(VALID_NIN)
        self.assertIsNone(user.Photo)

    def test_invalid_timeout_rejected(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                Nida(timeout=bad)


class TestPackageSurface(unittest.TestCase):
    def test_version_and_exports(self):
        self.assertEqual(nida.__version__, "0.2.0")
        for name in ("Nida", "load_user", "NidaError", "NidaInvalidIDError"):
            self.assertIn(name, nida.__all__)

    def test_module_level_load_user_validates(self):
        with self.assertRaises(NidaInvalidIDError):
            nida.load_user("nope")


if __name__ == "__main__":
    unittest.main()


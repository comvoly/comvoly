from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import auth


class AuthenticationTests(unittest.TestCase):
    def test_password_hash_verification(self) -> None:
        encoded = auth.hash_password("a-secure-owner-password", salt=b"0123456789abcdef")
        self.assertTrue(auth.verify_password("a-secure-owner-password", encoded))
        self.assertFalse(auth.verify_password("the-wrong-password", encoded))
        self.assertNotIn("a-secure-owner-password", encoded)

    def test_short_password_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            auth.hash_password("too-short")

    def test_signed_session_expires_and_rejects_tampering(self) -> None:
        with patch.dict(os.environ, {"COMVOLY_SESSION_SECRET": "test-secret"}):
            token = auth.create_session(now=1_000)
            self.assertTrue(auth.verify_session(token, now=1_001))
            self.assertFalse(auth.verify_session(token, now=1_000 + auth.SESSION_SECONDS + 1))
            self.assertFalse(auth.verify_session(token + "tampered", now=1_001))

    def test_cookie_is_http_only_and_strict(self) -> None:
        header = auth.session_cookie("signed-token")
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=Strict", header)
        self.assertEqual(auth.session_from_cookie("comvoly_session=signed-token"), "signed-token")


if __name__ == "__main__":
    unittest.main()

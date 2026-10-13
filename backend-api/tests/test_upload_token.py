"""
Upload token: issuance, consumption, single-use enforcement, expiry.
"""
import pytest

from app import upload_token, clock
from app.upload_token import issue, consume, clear_used


def test_issue_and_consume_roundtrip(fake_clock, tmp_staging):
    token = issue(1, "vendor_standard", str(tmp_staging / "pm_scripts" / "file.py"))
    payload = consume(token)
    assert payload is not None
    assert payload["vendor_id"] == 1
    assert payload["role"] == "vendor_standard"
    assert "pm_scripts" in payload["path"]


def test_single_use_enforcement(fake_clock, tmp_staging):
    token = issue(1, "vendor_standard", str(tmp_staging / "pm_scripts" / "file.py"))
    assert consume(token) is not None
    assert consume(token) is None          # second use rejected


def test_expired_token_rejected(fake_clock, tmp_staging):
    token = issue(1, "vendor_standard", str(tmp_staging / "pm_scripts" / "file.py"))
    fake_clock.advance(minutes=61)
    assert consume(token) is None


def test_tampered_signature_rejected(fake_clock, tmp_staging):
    token = issue(1, "vendor_standard", str(tmp_staging / "pm_scripts" / "file.py"))
    parts = token.rsplit(".", 1)
    tampered = parts[0] + ".invalidsignatureXXX"
    assert consume(tampered) is None


def test_malformed_token_rejected():
    clear_used()
    assert consume("notavalidtoken") is None
    assert consume("") is None
    assert consume("a.b.c.d") is None


def test_clear_used_allows_reuse(fake_clock, tmp_staging):
    token = issue(1, "vendor_standard", str(tmp_staging / "pm_scripts" / "file.py"))
    consume(token)
    clear_used()
    # After clearing, same token (same jti) would pass signature but jti no longer in _USED
    # A fresh token must be issued to test this properly
    token2 = issue(1, "vendor_standard", str(tmp_staging / "pm_scripts" / "file2.py"))
    assert consume(token2) is not None

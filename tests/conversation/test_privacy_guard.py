# tests/conversation/test_privacy_guard.py
"""
Unit tests for SessionPrivacyGuard (§11, §14).
"""

import pytest
from src.conversation.privacy_guard import SessionPrivacyGuard


def test_redact_aadhaar():
    guard = SessionPrivacyGuard()
    raw = "My Aadhaar number is 9876 5432 1098 please check."
    redacted = guard.redact_pii(raw)
    assert "[REDACTED_AADHAAR]" in redacted
    assert "9876 5432 1098" not in redacted


def test_redact_pan():
    guard = SessionPrivacyGuard()
    raw = "My PAN card is ABCDE1234F."
    redacted = guard.redact_pii(raw)
    assert "[REDACTED_PAN]" in redacted
    assert "ABCDE1234F" not in redacted


def test_redact_bank_account():
    guard = SessionPrivacyGuard()
    raw = "Transfer fine to account 12345678901234."
    redacted = guard.redact_pii(raw)
    assert "[REDACTED_ACCOUNT]" in redacted
    assert "12345678901234" not in redacted

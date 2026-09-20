# tests/auth/test_logging_safety.py
"""
Automated Logging Safety & Secret Leakage Audit Test (§16, §20).
Ensures plaintext passwords, hashes, and raw bearer tokens are never leaked to logs.
"""

import logging
import io
import pytest
from src.auth.auth_provider import PasswordAuthProvider


def test_logging_safety_no_secret_leakage(caplog):
    logger = logging.getLogger("auth_audit_test")
    logger.setLevel(logging.INFO)

    raw_password = "SecretPassword!99"
    email = "secret_user@example.com"

    provider = PasswordAuthProvider()

    # Capture log records during full account lifecycle
    with caplog.at_level(logging.DEBUG):
        user = provider.create_account(email, raw_password)
        auth_user, raw_token = provider.authenticate({"auth_identifier": email, "password": raw_password})
        provider.validate_token(raw_token)
        provider.logout(raw_token)

    logged_text = caplog.text

    # Verify no raw password appears in logged text
    assert raw_password not in logged_text

    # Verify no password hash appears in logged text
    if user.password_hash:
        assert user.password_hash not in logged_text

    # Verify no raw bearer token appears in logged text
    assert raw_token not in logged_text

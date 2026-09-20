# tests/auth/test_password_hashing.py
"""
Unit tests for password hashing module (§12, §20).
"""

import pytest
from src.auth.password_hashing import hash_password, verify_password


def test_hash_password_valid():
    raw_pass = "SecureP@ssw0rd!2026"
    hashed = hash_password(raw_pass)
    assert hashed is not None
    assert "$" in hashed
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_hash_password_salting():
    raw_pass = "SamePassword123"
    hash1 = hash_password(raw_pass)
    hash2 = hash_password(raw_pass)

    # Hashes must differ due to unique per-password random salting
    assert hash1 != hash2
    assert verify_password(raw_pass, hash1) is True
    assert verify_password(raw_pass, hash2) is True


def test_empty_password_rejection():
    with pytest.raises(ValueError):
        hash_password("")

    assert verify_password("", "pbkdf2_sha256$100000$abcd$efgh") is False
    assert verify_password("somepass", "") is False

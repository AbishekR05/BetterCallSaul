# src/auth/password_hashing.py
"""
Secure Password Hashing Wrapper (§12).
Supports bcrypt if installed, falling back to Python standard library hashlib.pbkdf2_hmac
with random 16-byte salt and constant-time string comparison (hmac.compare_digest).
"""

import hmac
import os
import hashlib
from typing import Tuple

try:
    import bcrypt
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False


def hash_password(password: str) -> str:
    """
    Hashes a raw password securely with a per-password random salt.
    Returns a formatted hash string.
    """
    if not password:
        raise ValueError("Password cannot be empty")

    if _BCRYPT_AVAILABLE:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return f"bcrypt${hashed.decode('utf-8')}"
    else:
        # Standard library PBKDF2-HMAC-SHA256 fallback
        salt = os.urandom(16)
        iterations = 100000
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations
        )
        return f"pbkdf2_sha256${iterations}${salt.hex()}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies a raw password against a stored hash string using constant-time comparison.
    Returns True if valid, False otherwise.
    """
    if not password or not stored_hash:
        return False

    try:
        parts = stored_hash.split("$")
        algo = parts[0]

        if algo == "bcrypt":
            if not _BCRYPT_AVAILABLE:
                # If bcrypt was used to hash but bcrypt module is not installed now
                return False
            hash_bytes = parts[1].encode("utf-8")
            return bcrypt.checkpw(password.encode("utf-8"), hash_bytes)

        elif algo == "pbkdf2_sha256":
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            target_key = bytes.fromhex(parts[3])

            computed_key = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                iterations
            )
            return hmac.compare_digest(computed_key, target_key)

        else:
            return False
    except Exception:
        return False

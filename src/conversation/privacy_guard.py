# src/conversation/privacy_guard.py
"""
Session Privacy Guard for Phase 2.7 Conversational Context & Session Memory (§11).
Enforces minimal retention and redacts sensitive PII (PAN, Aadhaar, Account Numbers) before persistence.
"""

import re


class SessionPrivacyGuard:
    """
    Best-effort regex PII redaction guard for session turn persistence.
    """

    # 12-digit Aadhaar pattern (e.g. 1234 5678 9012 or 123456789012)
    AADHAAR_PATTERN = r"\b[2-9]{1}\d{3}\s?\d{4}\s?\d{4}\b"

    # Indian PAN card pattern (e.g. ABCDE1234F)
    PAN_PATTERN = r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"

    # Standard 16-digit credit card pattern
    CARD_PATTERN = r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"

    # Bank Account numbers (9-18 continuous digits preceded by account/a/c)
    ACCOUNT_PATTERN = r"(?i)\b(account|ac|a/c|acc)\s*#?\s*([0-9]{9,18})\b"

    def redact_pii(self, text: str) -> str:
        """
        Redact sensitive PII patterns from input text string.
        """
        if not text:
            return text

        redacted = text
        redacted = re.sub(self.AADHAAR_PATTERN, "[REDACTED_AADHAAR]", redacted)
        redacted = re.sub(self.PAN_PATTERN, "[REDACTED_PAN]", redacted, flags=re.IGNORECASE)
        redacted = re.sub(self.CARD_PATTERN, "[REDACTED_CARD]", redacted)
        redacted = re.sub(self.ACCOUNT_PATTERN, r"\1 [REDACTED_ACCOUNT]", redacted)

        return redacted

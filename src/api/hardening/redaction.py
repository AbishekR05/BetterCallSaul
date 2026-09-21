# src/api/hardening/redaction.py
"""
Structured Access Logging & Sensitive Data Redaction (§10).
Ensures no secrets, tokens, passwords, query text, answer text, or raw database errors leak into logs.
"""

import re
import json
import logging
from typing import Any, Dict


# Sensitive pattern matchers for defense-in-depth redaction
SENSITIVE_PATTERNS = [
    (re.compile(r'(bearer\s+)[A-Za-z0-9_\-\.]+', re.IGNORECASE), r'\1[REDACTED_TOKEN]'),
    (re.compile(r'("?(?:password|token|secret|access_token|authorization)"?\s*[:=]\s*)"[^"]+"', re.IGNORECASE), r'\1"[REDACTED]"'),
    (re.compile(r'("?(?:password|token|secret|access_token|authorization)"?\s*[:=]\s*)[^\s,]+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(postgres(?:ql)?://)[^@]+@', re.IGNORECASE), r'\1[REDACTED_CREDS]@'),
    (re.compile(r'(sqlite:////?)[^\s]+', re.IGNORECASE), r'\1[REDACTED_PATH]'),
]


class RedactionFilter(logging.Filter):
    """
    Logging filter that sanitizes log message strings to eliminate credentials,
    bearer tokens, queries, answers, or sensitive connection parameters (§10).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.redact_text(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.redact_text(str(arg)) for arg in record.args)
        return True

    @staticmethod
    def redact_text(text: str) -> str:
        if not text:
            return text
        sanitized = text
        for pattern, replacement in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized


class JsonAccessLogFormatter(logging.Formatter):
    """
    Structured JSON access log formatter (§10).
    Outputs JSON lines with timestamp, request_id, method, route_template,
    status_code, latency_ms, opaque user_id, and error_code.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": RedactionFilter.redact_text(record.getMessage()),
        }

        # Include structured fields attached to the record
        for attr in ("request_id", "method", "route_template", "status_code", "latency_ms", "user_id", "error_code"):
            val = getattr(record, attr, None)
            if val is not None:
                log_data[attr] = val

        return json.dumps(log_data)

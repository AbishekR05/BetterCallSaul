# src/retrieval/errors.py
"""
Typed Exception hierarchy for Phase 2.3 Legal Retrieval Pipeline.
Ensures fail-closed behavior with clean exception reporting.
"""

class RetrievalError(Exception):
    """Base exception for all retrieval pipeline errors."""
    pass

class QueryValidationError(RetrievalError):
    """Raised when incoming query violates validation rules (e.g. empty/whitespace)."""
    pass

class EmbeddingError(RetrievalError):
    """Raised when query embedding generation fails."""
    pass

class DatabaseTimeoutError(RetrievalError):
    """Raised when PostgreSQL search exceeds wall-clock timeout."""
    pass

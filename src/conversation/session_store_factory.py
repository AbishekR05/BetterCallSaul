# src/conversation/session_store_factory.py
"""
Config-driven Session Store Factory for Phase 2.8 (§9).
Resolves and instantiates the appropriate SessionStore implementation based on configuration.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from src.conversation.session_store import SessionStore, InMemorySessionStore
from src.conversation.persistent_session_store import PersistentSessionStore


def create_session_store(config_path: str = "configs/p28_persistence.yaml") -> SessionStore:
    """
    Factory function instantiating a SessionStore based on YAML configuration.
    """
    path = Path(config_path)
    config: Dict[str, Any] = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    store_cfg = config.get("session_store", {})
    backend = store_cfg.get("backend", "in_memory").lower()

    if backend == "in_memory":
        return InMemorySessionStore()

    postgres_cfg = config.get("postgres", {})
    sqlite_cfg = config.get("sqlite", {})

    return PersistentSessionStore(
        backend=backend,
        db_config=postgres_cfg,
        sqlite_path=sqlite_cfg.get("db_path", "benchmark/phase_2_8/session_db.sqlite")
    )

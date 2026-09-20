# src/conversation/expiration_sweeper.py
"""
Expiration Sweeper for Phase 2.8 (§10, §12).
Executes periodic TTL expiration sweeps and purges expired sessions past retention grace period.
"""

import time
import threading
from typing import Optional
from datetime import datetime, timedelta
from src.conversation.session_store import SessionStore
from src.conversation.persistent_session_store import PersistentSessionStore


class ExpirationSweeper:
    """
    Sweeper job executing lazy and periodic TTL expiration and retention purges.
    """

    def __init__(
        self,
        session_store: SessionStore,
        sweep_interval_seconds: int = 300,
        expired_retention_days: int = 7
    ):
        self.session_store = session_store
        self.sweep_interval = sweep_interval_seconds
        self.retention_days = expired_retention_days
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def run_sweep(self) -> int:
        """
        Executes a single expiration sweep pass.
        Returns count of newly marked expired sessions.
        """
        swept = self.session_store.sweep_expired_sessions()
        self._purge_old_expired_sessions()
        return swept

    def _purge_old_expired_sessions(self) -> int:
        """
        Purges sessions that have been in 'expired' status beyond expired_retention_days.
        """
        if not isinstance(self.session_store, PersistentSessionStore):
            return 0

        cutoff = (datetime.utcnow() - timedelta(days=self.retention_days)).isoformat()
        conn = self.session_store._get_connection()
        schema_prefix = f"{self.session_store.db_config.get('schema', 'session_db')}." if self.session_store.backend == "postgres" else ""

        purged_count = 0
        try:
            if self.session_store.backend == "sqlite":
                with conn:
                    cur = conn.execute("DELETE FROM sessions WHERE status = 'expired' AND expires_at_utc < ?", (cutoff,))
                    purged_count = cur.rowcount
            else:
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM {schema_prefix}sessions WHERE status = 'expired' AND expires_at_utc < %s", (cutoff,))
                    purged_count = cur.rowcount
                conn.commit()
            return purged_count
        except Exception as e:
            print(f"[ExpirationSweeper Warning] Retention purge failed: {e}")
            return 0
        finally:
            conn.close()

    def start_background_sweeper(self):
        """Starts periodic background sweeper loop in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._sweeper_loop, daemon=True)
        self._thread.start()

    def stop_background_sweeper(self):
        """Stops background sweeper loop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _sweeper_loop(self):
        while self._running:
            try:
                self.run_sweep()
            except Exception as e:
                print(f"[ExpirationSweeper Error] Background loop error: {e}")
            time.sleep(self.sweep_interval)

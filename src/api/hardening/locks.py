# src/api/hardening/locks.py
"""
Concurrency & Serialization Safety Controls (§5.7, §7.2).
Provides per-session turn locks and global turn capacity semaphores.
"""

import asyncio
import threading
from typing import Dict, Optional, Tuple
from contextlib import asynccontextmanager

from src.api.errors import SessionBusyError, ServerBusyError


class SessionTurnLock:
    """
    Per-session turn serialization lock (§7.2).
    Ensures at most one turn is in-flight per session_id across the process.
    Prevents interleaved turn ordering and context corruption.
    """

    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock_counts: Dict[str, int] = {}
        self._global_lock = threading.Lock()

    @asynccontextmanager
    async def lock_session(self, session_id: str):
        with self._global_lock:
            if session_id not in self._locks:
                self._locks[session_id] = asyncio.Lock()
                self._lock_counts[session_id] = 0
            session_lock = self._locks[session_id]
            self._lock_counts[session_id] += 1

        # Non-blocking acquire check
        if session_lock.locked():
            with self._global_lock:
                self._lock_counts[session_id] -= 1
                if self._lock_counts[session_id] <= 0:
                    self._locks.pop(session_id, None)
                    self._lock_counts.pop(session_id, None)
            raise SessionBusyError(
                f"Session '{session_id}' has a turn currently in progress. Concurrent turns on the same session are forbidden."
            )

        await session_lock.acquire()
        try:
            yield
        finally:
            session_lock.release()
            with self._global_lock:
                self._lock_counts[session_id] -= 1
                if self._lock_counts[session_id] <= 0:
                    self._locks.pop(session_id, None)
                    self._lock_counts.pop(session_id, None)


class TurnConcurrencySemaphore:
    """
    Global capacity semaphore protecting shared GPU / LLM resources (§5.7).
    Limits active concurrent turn executions to `max_concurrent_turns`.
    Requests beyond capacity wait up to `queue_wait_timeout_s` before yielding 503 server_busy.
    """

    def __init__(self, max_concurrent: int = 2, queue_wait_timeout_s: float = 10.0):
        self.max_concurrent = max_concurrent
        self.queue_wait_timeout_s = queue_wait_timeout_s
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = None):
        wait_timeout = timeout if timeout is not None else self.queue_wait_timeout_s
        sem = self._get_semaphore()

        try:
            await asyncio.wait_for(sem.acquire(), timeout=wait_timeout)
        except asyncio.TimeoutError:
            raise ServerBusyError(
                "Server is experiencing high turn concurrency. Please retry after waiting.",
                retry_after_s=5,
            )

        try:
            yield
        finally:
            sem.release()


_global_session_lock: Optional[SessionTurnLock] = None
_global_turn_semaphore: Optional[TurnConcurrencySemaphore] = None


def get_session_turn_lock() -> SessionTurnLock:
    """Returns singleton SessionTurnLock instance."""
    global _global_session_lock
    if _global_session_lock is None:
        _global_session_lock = SessionTurnLock()
    return _global_session_lock


def get_turn_concurrency_semaphore(max_concurrent: int = 2, queue_wait_timeout_s: float = 10.0) -> TurnConcurrencySemaphore:
    """Returns singleton TurnConcurrencySemaphore instance."""
    global _global_turn_semaphore
    if _global_turn_semaphore is None:
        _global_turn_semaphore = TurnConcurrencySemaphore(
            max_concurrent=max_concurrent,
            queue_wait_timeout_s=queue_wait_timeout_s,
        )
    return _global_turn_semaphore

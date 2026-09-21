from __future__ import annotations

import threading


DEFAULT_STOP_REASON = "User requested stop"


class CancellationToken:
    """
    Thread-safe cancellation state shared across GUI, worker,
    automation suites, test cases, and CommandRunner.

    Design rules:
    - request() is idempotent.
    - The first stop reason is preserved.
    - A token is intended for one task execution only.
    - No Qt dependency is introduced here.
    """

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._reason: str | None = None

    def request(
        self,
        reason: str = DEFAULT_STOP_REASON,
    ) -> None:
        """
        Request cancellation.

        Repeated calls are allowed, but the first reason is kept.
        """
        with self._lock:
            if self._event.is_set():
                return

            self._reason = reason
            self._event.set()

    def is_requested(self) -> bool:
        """
        Return True after cancellation has been requested.
        """
        return self._event.is_set()

    def wait(
        self,
        timeout: float | None = None,
    ) -> bool:
        """
        Wait until cancellation is requested or timeout expires.

        Returns True if cancellation was requested.
        """
        return self._event.wait(timeout)

    @property
    def reason(self) -> str | None:
        """
        Return the preserved cancellation reason.
        """
        with self._lock:
            return self._reason

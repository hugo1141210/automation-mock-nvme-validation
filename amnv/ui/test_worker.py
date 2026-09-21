from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot


class TestWorker(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        task: Callable[[], Any],
    ) -> None:
        super().__init__()
        self._task = task

    @Slot()
    def run(self) -> None:
        try:
            result = self._task()
            self.result.emit(result)

        except Exception:
            self.error.emit(
                traceback.format_exc()
            )

        finally:
            self.finished.emit()

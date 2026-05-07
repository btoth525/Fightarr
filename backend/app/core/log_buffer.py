"""In-memory ring buffer of log records for the System → Logs page.

A custom logging.Handler pushes every formatted log line into a deque(maxlen=N).
The /system/logs endpoint reads from this deque so the UI can display recent
output without us having to tail a file or run a separate log shipping process.
"""

from __future__ import annotations

import contextlib
import logging
from collections import deque
from datetime import UTC, datetime

_BUFFER: deque[dict] = deque(maxlen=2000)


class RingBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Never let logging crash the app
        with contextlib.suppress(Exception):
            _BUFFER.append(
                {
                    "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
            )


def install() -> None:
    """Attach the ring-buffer handler to the root logger."""
    root = logging.getLogger()
    if any(isinstance(h, RingBufferHandler) for h in root.handlers):
        return
    h = RingBufferHandler()
    h.setLevel(logging.INFO)
    root.addHandler(h)


def get_logs(limit: int = 500, level: str | None = None) -> list[dict]:
    """Return the latest log entries, newest last. Optional level filter."""
    items = list(_BUFFER)
    if level:
        wanted = level.upper()
        items = [i for i in items if i["level"] == wanted]
    return items[-limit:]

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields:
            payload.update(extra_fields)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("agentlab")
    root.setLevel(level)
    root.handlers = [handler]
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"agentlab.{name}")

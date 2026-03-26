"""Logging estructurado en JSON para el flujo conversacional.

Emite una línea JSON por evento a stdout (logger "agenda.structured").
Se habilita/deshabilita con ENABLE_STRUCTURED_LOGGING en config.py.
Nunca propaga excepciones: si el logger falla, el flujo continúa.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

import app.config as _config

_logger = logging.getLogger("agenda.structured")
_logger.propagate = False


def _ensure_handler() -> None:
    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)


_ensure_handler()


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def log_conversation_turn(
    *,
    intent: str | None = None,
    parser_source: str | None = None,
    action_status: str | None = None,
    latency_ms: float | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Loggea un turno conversacional completo con campos clave."""
    if not _config.ENABLE_STRUCTURED_LOGGING:
        return
    try:
        record: dict[str, Any] = {
            "ts": _now_iso(),
            "intent": intent or "unknown",
            "parser_source": parser_source or "unknown",
            "action_status": action_status or "unknown",
            "latency_ms": round(latency_ms, 1) if latency_ms is not None else None,
        }
        if extra:
            record.update(extra)
        _logger.info(json.dumps(record, ensure_ascii=False))
    except Exception:
        pass


def log_parser_decision(
    *,
    decision: str,
    reason: str | None = None,
    query_preview: str | None = None,
) -> None:
    """Loggea una decisión del parser híbrido (fallback, preferencia, etc.)."""
    if not _config.ENABLE_STRUCTURED_LOGGING:
        return
    try:
        record: dict[str, Any] = {
            "ts": _now_iso(),
            "event": "parser_decision",
            "decision": decision,
        }
        if reason:
            record["reason"] = reason
        if query_preview:
            record["query_preview"] = query_preview[:80]
        _logger.info(json.dumps(record, ensure_ascii=False))
    except Exception:
        pass

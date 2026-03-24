from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time
import json

from app.db.base import Base
from app.db.models.conversation_state import ConversationState
from app.db.session import SessionLocal
from app.repositories.conversation_state_repository import (
    delete_all_conversation_states,
    delete_conversation_state,
    get_conversation_state_by_key,
    save_conversation_state,
)


class InMemoryTelegramContextStore:
    def __init__(self):
        self._contexts: dict[str, dict] = {}

    def get_context(self, conversation_key: str | int) -> dict:
        return deepcopy(self._contexts.get(str(conversation_key), {}))

    def save_context(self, conversation_key: str | int, context: dict | None, *, metadata: dict | None = None) -> dict:
        key = str(conversation_key)
        previous = deepcopy(self._contexts.get(key, {}))
        normalized = _normalize_context_payload(context, previous_context=previous)
        self._contexts[key] = normalized
        return deepcopy(normalized)

    def clear_context(self, conversation_key: str | int) -> None:
        self._contexts.pop(str(conversation_key), None)

    def clear_all(self) -> None:
        self._contexts.clear()


class PersistentTelegramContextStore:
    def __init__(self, *, session_factory=SessionLocal):
        self.session_factory = session_factory
        self._ensure_schema()

    def get_context(self, conversation_key: str | int) -> dict:
        db = self.session_factory()
        try:
            state = get_conversation_state_by_key(db, str(conversation_key))
            if state is None:
                return {}
            context = _deserialize_json_dict(state.conversation_context_json)
            assistant_memory = _deserialize_json_dict(state.assistant_memory_json)
            if assistant_memory:
                context["assistant_memory"] = assistant_memory
            return deepcopy(context)
        finally:
            db.close()

    def save_context(
        self,
        conversation_key: str | int,
        context: dict | None,
        *,
        metadata: dict | None = None,
    ) -> dict:
        key = str(conversation_key)
        previous = self.get_context(key)
        normalized = _normalize_context_payload(context, previous_context=previous)
        assistant_memory = deepcopy(normalized.get("assistant_memory") or {})
        context_payload = deepcopy(normalized)
        context_payload.pop("assistant_memory", None)
        metadata = metadata or {}

        db = self.session_factory()
        try:
            save_conversation_state(
                db,
                conversation_key=key,
                conversation_context_json=_serialize_json_dict(context_payload),
                assistant_memory_json=_serialize_json_dict(assistant_memory),
                user_id=_normalize_optional_text(metadata.get("user_id")),
                chat_id=_normalize_optional_text(metadata.get("chat_id")),
                chat_type=_normalize_optional_text(metadata.get("chat_type")),
                message_thread_id=_normalize_optional_text(metadata.get("message_thread_id")),
            )
            return deepcopy(normalized)
        finally:
            db.close()

    def clear_context(self, conversation_key: str | int) -> None:
        db = self.session_factory()
        try:
            delete_conversation_state(db, str(conversation_key))
        finally:
            db.close()

    def clear_all(self) -> None:
        db = self.session_factory()
        try:
            delete_all_conversation_states(db)
        finally:
            db.close()

    def _ensure_schema(self) -> None:
        bind = getattr(self.session_factory, "kw", {}).get("bind")
        if bind is not None:
            Base.metadata.create_all(bind=bind, tables=[ConversationState.__table__])


def _normalize_context_payload(context: dict | None, *, previous_context: dict | None) -> dict:
    normalized = deepcopy(context) if isinstance(context, dict) else {}
    previous = previous_context if isinstance(previous_context, dict) else {}
    previous_memory = previous.get("assistant_memory") if isinstance(previous, dict) else None
    current_memory = normalized.get("assistant_memory") if isinstance(normalized, dict) else None
    if isinstance(previous_memory, dict) and not isinstance(current_memory, dict):
        normalized["assistant_memory"] = deepcopy(previous_memory)
    if isinstance(normalized.get("assistant_memory"), dict):
        normalized["assistant_memory"]["debug_mode"] = bool(
            normalized["assistant_memory"].get("debug_mode", False)
        )
    return normalized


def _normalize_optional_text(value) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _serialize_json_dict(value: dict | None) -> str | None:
    payload = _sanitize_jsonable(value if isinstance(value, dict) else {})
    return json.dumps(payload, ensure_ascii=False)


def _deserialize_json_dict(raw_value: str | None) -> dict:
    if not raw_value:
        return {}
    try:
        loaded = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _sanitize_jsonable(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, list):
        return [_sanitize_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_jsonable(item) for key, item in value.items()}
    if hasattr(value, "__dict__"):
        return _sanitize_jsonable(vars(value))
    return str(value)

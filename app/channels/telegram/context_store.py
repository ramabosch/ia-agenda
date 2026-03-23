from __future__ import annotations

from copy import deepcopy


class InMemoryTelegramContextStore:
    def __init__(self):
        self._contexts: dict[str, dict] = {}

    def get_context(self, conversation_key: str | int) -> dict:
        return deepcopy(self._contexts.get(str(conversation_key), {}))

    def save_context(self, conversation_key: str | int, context: dict | None) -> dict:
        key = str(conversation_key)
        previous = deepcopy(self._contexts.get(key, {}))
        normalized = deepcopy(context) if isinstance(context, dict) else {}
        # Preserve assistant_memory across turns unless explicitly replaced.
        previous_memory = previous.get("assistant_memory") if isinstance(previous, dict) else None
        current_memory = normalized.get("assistant_memory") if isinstance(normalized, dict) else None
        if isinstance(previous_memory, dict) and not isinstance(current_memory, dict):
            normalized["assistant_memory"] = deepcopy(previous_memory)
        if isinstance(normalized.get("assistant_memory"), dict):
            normalized["assistant_memory"]["debug_mode"] = bool(
                normalized["assistant_memory"].get("debug_mode", False)
            )
        self._contexts[key] = normalized
        return deepcopy(normalized)

    def clear_context(self, conversation_key: str | int) -> None:
        self._contexts.pop(str(conversation_key), None)

    def clear_all(self) -> None:
        self._contexts.clear()

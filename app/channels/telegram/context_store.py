from __future__ import annotations

from copy import deepcopy


class InMemoryTelegramContextStore:
    def __init__(self):
        self._contexts: dict[str, dict] = {}

    def get_context(self, conversation_key: str | int) -> dict:
        return deepcopy(self._contexts.get(str(conversation_key), {}))

    def save_context(self, conversation_key: str | int, context: dict | None) -> dict:
        normalized = deepcopy(context) if isinstance(context, dict) else {}
        self._contexts[str(conversation_key)] = normalized
        return deepcopy(normalized)

    def clear_context(self, conversation_key: str | int) -> None:
        self._contexts.pop(str(conversation_key), None)

    def clear_all(self) -> None:
        self._contexts.clear()

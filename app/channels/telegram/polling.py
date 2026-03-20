from __future__ import annotations

import os
import re
import time
from typing import Callable

import requests

from app.channels.telegram.adapter import (
    TelegramChannelAdapter,
    extract_telegram_message,
    get_telegram_bot_token,
)


DEFAULT_TELEGRAM_API_BASE = "https://api.telegram.org"


def parse_allowed_chat_ids(raw_value: str | None = None) -> set[str] | None:
    source = raw_value if raw_value is not None else os.getenv("TELEGRAM_ALLOWED_CHAT_IDS")
    if source is None:
        return None
    values = [item.strip() for item in re.split(r"[\s,;]+", source) if item.strip()]
    return set(values) or None


def parse_allowed_user_ids(raw_value: str | None = None) -> set[str] | None:
    source = raw_value if raw_value is not None else os.getenv("TELEGRAM_ALLOWED_USER_IDS")
    if source is None:
        return None
    values = [item.strip() for item in re.split(r"[\s,;]+", source) if item.strip()]
    return set(values) or None


def is_chat_allowed(chat_id: str | int, allowed_chat_ids: set[str] | None) -> bool:
    if not allowed_chat_ids:
        return True
    return str(chat_id) in {str(item) for item in allowed_chat_ids}


def is_user_allowed(user_id: str | int | None, allowed_user_ids: set[str] | None) -> bool:
    if not allowed_user_ids:
        return True
    if user_id in (None, ""):
        return False
    return str(user_id) in {str(item) for item in allowed_user_ids}


def is_telegram_identity_allowed(
    incoming: dict,
    *,
    allowed_chat_ids: set[str] | None,
    allowed_user_ids: set[str] | None,
) -> bool:
    return is_chat_allowed(incoming.get("chat_id"), allowed_chat_ids) and is_user_allowed(
        incoming.get("user_id"),
        allowed_user_ids,
    )


def telegram_api_request(
    session: requests.Session,
    token: str,
    method: str,
    *,
    params: dict | None = None,
    data: dict | None = None,
    timeout_seconds: int = 30,
) -> dict:
    url = f"{DEFAULT_TELEGRAM_API_BASE}/bot{token}/{method}"
    try:
        if data is not None:
            response = session.post(url, data=data, timeout=timeout_seconds)
        else:
            response = session.get(url, params=params, timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Error llamando a Telegram en {method}: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"Telegram devolvio JSON invalido en {method}.") from exc

    if not isinstance(payload, dict) or not payload.get("ok"):
        description = payload.get("description") if isinstance(payload, dict) else "respuesta inesperada"
        raise RuntimeError(f"Telegram devolvio error en {method}: {description}")
    return payload


def get_updates(
    session: requests.Session,
    token: str,
    *,
    offset: int | None = None,
    timeout_seconds: int = 20,
) -> list[dict]:
    params = {"timeout": timeout_seconds}
    if offset is not None:
        params["offset"] = offset
    payload = telegram_api_request(
        session,
        token,
        "getUpdates",
        params=params,
        timeout_seconds=timeout_seconds + 5,
    )
    result = payload.get("result")
    return result if isinstance(result, list) else []


def send_message(
    session: requests.Session,
    token: str,
    *,
    chat_id: str | int,
    text: str,
    timeout_seconds: int = 30,
) -> dict:
    return telegram_api_request(
        session,
        token,
        "sendMessage",
        data={"chat_id": str(chat_id), "text": text},
        timeout_seconds=timeout_seconds,
    )


def process_telegram_update(
    update: dict,
    *,
    adapter: TelegramChannelAdapter,
    session: requests.Session,
    token: str,
    allowed_chat_ids: set[str] | None = None,
    allowed_user_ids: set[str] | None = None,
    timeout_seconds: int = 30,
    logger: Callable[[str], None] | None = print,
) -> dict:
    update_id = update.get("update_id")
    try:
        incoming = extract_telegram_message(update)
    except ValueError as exc:
        _log(logger, f"[telegram] update {update_id}: ignorado ({exc})")
        return {"status": "ignored_non_text", "update_id": update_id, "reason": str(exc)}

    chat_id = incoming["chat_id"]
    user_id = incoming.get("user_id")
    thread_id = incoming.get("message_thread_id")
    conversation_key = incoming.get("conversation_key")
    text = incoming["text"]

    if not is_telegram_identity_allowed(
        incoming,
        allowed_chat_ids=allowed_chat_ids,
        allowed_user_ids=allowed_user_ids,
    ):
        _log(
            logger,
            f"[telegram] update {update_id}: chat {chat_id} user {user_id or 'n/d'} "
            f"thread {thread_id or 'n/d'} ignorado por whitelist",
        )
        return {
            "status": "ignored_whitelist",
            "update_id": update_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "message_thread_id": thread_id,
            "conversation_key": conversation_key,
            "text": text,
        }

    _log(
        logger,
        f"[telegram] update {update_id}: chat {chat_id} user {user_id or 'n/d'} "
        f"thread {thread_id or 'n/d'} key {conversation_key} -> '{text}'",
    )
    result = adapter.handle_update(update)
    send_payload = result["send_message_payload"]
    send_message(
        session,
        token,
        chat_id=send_payload["chat_id"],
        text=send_payload["text"],
        timeout_seconds=timeout_seconds,
    )
    _log(logger, f"[telegram] update {update_id}: respuesta enviada a chat {chat_id}")
    return {
        "status": "sent",
        "update_id": update_id,
        "chat_id": chat_id,
        "user_id": user_id,
        "message_thread_id": thread_id,
        "conversation_key": conversation_key,
        "text": text,
        "intent": (result.get("parsed_query") or {}).get("intent"),
        "action_status": (result.get("audit_trace") or {}).get("action_status"),
    }


def run_polling_loop(
    *,
    adapter: TelegramChannelAdapter | None = None,
    token: str | None = None,
    allowed_chat_ids: set[str] | None = None,
    allowed_user_ids: set[str] | None = None,
    session: requests.Session | None = None,
    poll_timeout_seconds: int = 20,
    idle_sleep_seconds: float = 1.0,
    max_cycles: int | None = None,
    logger: Callable[[str], None] | None = print,
) -> dict:
    bot_token = token or get_telegram_bot_token(required=True)
    current_adapter = adapter or TelegramChannelAdapter()
    current_session = session or requests.Session()
    current_allowed_chat_ids = allowed_chat_ids if allowed_chat_ids is not None else parse_allowed_chat_ids()
    current_allowed_user_ids = allowed_user_ids if allowed_user_ids is not None else parse_allowed_user_ids()
    offset: int | None = None
    cycles = 0
    processed_updates: list[dict] = []

    while True:
        cycles += 1
        try:
            updates = get_updates(
                current_session,
                bot_token,
                offset=offset,
                timeout_seconds=poll_timeout_seconds,
            )
        except Exception as exc:
            _log(logger, f"[telegram] error en getUpdates: {exc}")
            if max_cycles is not None and cycles >= max_cycles:
                break
            time.sleep(idle_sleep_seconds)
            continue

        if not updates:
            if max_cycles is not None and cycles >= max_cycles:
                break
            time.sleep(idle_sleep_seconds)
            continue

        for update in updates:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                offset = update_id + 1
            try:
                result = process_telegram_update(
                    update,
                    adapter=current_adapter,
                    session=current_session,
                    token=bot_token,
                    allowed_chat_ids=current_allowed_chat_ids,
                    allowed_user_ids=current_allowed_user_ids,
                    timeout_seconds=poll_timeout_seconds,
                    logger=logger,
                )
            except Exception as exc:
                result = {
                    "status": "error",
                    "update_id": update_id,
                    "reason": str(exc),
                }
                _log(logger, f"[telegram] update {update_id}: error {exc}")
            processed_updates.append(result)

        if max_cycles is not None and cycles >= max_cycles:
            break

    return {
        "processed_updates": processed_updates,
        "last_offset": offset,
        "allowed_chat_ids": sorted(current_allowed_chat_ids) if current_allowed_chat_ids else None,
        "allowed_user_ids": sorted(current_allowed_user_ids) if current_allowed_user_ids else None,
        "cycles": cycles,
    }


def _log(logger: Callable[[str], None] | None, message: str) -> None:
    if logger:
        logger(message)

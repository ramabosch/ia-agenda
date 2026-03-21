from __future__ import annotations

import os
from copy import deepcopy

from app.channels.telegram.context_store import InMemoryTelegramContextStore
from app.services.conversation_runtime_service import process_conversation_turn
from app.services.llm_parser_service import parse_actions_with_llm
from app.services.assistant_orchestrator_service import AssistantOrchestratorService


def get_telegram_bot_token(*, required: bool = False) -> str | None:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if token:
        return token
    if required:
        raise RuntimeError(
            "Falta TELEGRAM_BOT_TOKEN. Configuralo como variable de entorno para usar Telegram real."
        )
    return None


def build_telegram_conversation_key(
    *,
    chat_id: str | int,
    chat_type: str | None = None,
    user_id: str | int | None = None,
    message_thread_id: str | int | None = None,
) -> str:
    parts = [f"chat:{chat_id}"]
    if chat_type:
        parts.append(f"type:{chat_type}")
    if message_thread_id not in (None, ""):
        parts.append(f"thread:{message_thread_id}")
    elif str(chat_type or "").lower() == "private" and user_id not in (None, ""):
        parts.append(f"user:{user_id}")
    return "|".join(str(part) for part in parts)


def extract_telegram_message(update: dict) -> dict:
    if not isinstance(update, dict):
        raise ValueError("El update de Telegram debe ser un dict.")

    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        raise ValueError("No encontre un mensaje valido dentro del update de Telegram.")

    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    text = message.get("text")
    user_id = sender.get("id")
    chat_type = chat.get("type")
    message_thread_id = message.get("message_thread_id")

    if chat_id in (None, ""):
        raise ValueError("No encontre chat_id dentro del mensaje de Telegram.")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("No encontre texto util para procesar en el mensaje de Telegram.")

    conversation_key = build_telegram_conversation_key(
        chat_id=chat_id,
        chat_type=chat_type,
        user_id=user_id,
        message_thread_id=message_thread_id,
    )
    return {
        "chat_id": str(chat_id),
        "user_id": str(user_id) if user_id not in (None, "") else None,
        "chat_type": chat_type,
        "message_thread_id": str(message_thread_id) if message_thread_id not in (None, "") else None,
        "conversation_key": conversation_key,
        "username": sender.get("username"),
        "first_name": sender.get("first_name"),
        "last_name": sender.get("last_name"),
        "text": text.strip(),
        "message_id": message.get("message_id"),
        "update_id": update.get("update_id"),
    }


def normalize_telegram_user_text(text: str) -> str:
    normalized = (text or "").strip()
    prefixes = (
        "gracias. ",
        "gracias, ",
        "gracias ",
        "ok, ",
        "ok ",
        "dale, ",
        "dale ",
        "perfecto, ",
        "perfecto ",
        "genial, ",
        "genial ",
    )
    lowered = normalized.lower()
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if lowered.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
                lowered = normalized.lower()
                changed = True
                break
    return normalized or text.strip()


def parse_telegram_command(text: str) -> str | None:
    normalized = (text or "").strip()
    if not normalized.startswith("/"):
        return None
    command = normalized.split()[0].lower()
    if command in {"/start", "/help", "/reset", "/status", "/whoami"}:
        return command
    return None


class TelegramChannelAdapter:
    def __init__(
        self,
        *,
        context_store: InMemoryTelegramContextStore | None = None,
        orchestrator: AssistantOrchestratorService | None = None,
        persist_log: bool = True,
    ):
        self.context_store = context_store or InMemoryTelegramContextStore()
        self.orchestrator = orchestrator or AssistantOrchestratorService()
        self.persist_log = persist_log

    def handle_incoming_text(
        self,
        *,
        chat_id: str | int,
        text: str,
        user_id: str | int | None = None,
        chat_type: str | None = None,
        message_thread_id: str | int | None = None,
        conversation_key: str | None = None,
    ) -> dict:
        effective_conversation_key = conversation_key or build_telegram_conversation_key(
            chat_id=chat_id,
            chat_type=chat_type,
            user_id=user_id,
            message_thread_id=message_thread_id,
        )
        command = parse_telegram_command(text)
        if command:
            return self._handle_command(
                chat_id=chat_id,
                user_id=user_id,
                chat_type=chat_type,
                message_thread_id=message_thread_id,
                conversation_key=effective_conversation_key,
                command=command,
            )

        current_context = self.context_store.get_context(effective_conversation_key)
        normalized_text = normalize_telegram_user_text(text)
        parsed_actions = parse_actions_with_llm(normalized_text)

        if parsed_actions:
            command_responses: list[str] = []
            non_command_actions: list[dict] = []
            for action in parsed_actions:
                action_intent = action.get("intent")
                if action_intent == "telegram_channel_command" and action.get("command"):
                    command_result = self._handle_command(
                        chat_id=chat_id,
                        user_id=user_id,
                        chat_type=chat_type,
                        message_thread_id=message_thread_id,
                        conversation_key=effective_conversation_key,
                        command=action.get("command"),
                    )
                    command_responses.append(command_result.get("response_text") or "")
                else:
                    non_command_actions.append(action)

            orchestration = self.orchestrator.execute_actions(
                non_command_actions,
                conversation_context=current_context,
            ) if non_command_actions else {
                "reports": [],
                "conversation_context": current_context,
            }
            updated_context = orchestration.get("conversation_context") or {}
            self.context_store.save_context(effective_conversation_key, updated_context)
            response_text = _build_friendly_telegram_summary(
                reports=orchestration.get("reports") or [],
                command_responses=command_responses,
            )
            if response_text:
                return {
                    "channel": "telegram",
                    "chat_id": str(chat_id),
                    "user_id": str(user_id) if user_id not in (None, "") else None,
                    "chat_type": chat_type,
                    "message_thread_id": str(message_thread_id) if message_thread_id not in (None, "") else None,
                    "conversation_key": effective_conversation_key,
                    "input_text": text,
                    "normalized_input_text": normalized_text,
                    "response_text": response_text,
                    "parsed_query": {
                        "intent": "assistant_orchestration",
                        "actions": parsed_actions,
                        "_parser_source": "llm",
                    },
                    "conversation_context": deepcopy(updated_context),
                    "audit_trace": {},
                    "resolved_references": {},
                    "send_message_payload": {
                        "chat_id": str(chat_id),
                        "text": response_text,
                    },
                }

        result = process_conversation_turn(
            normalized_text,
            conversation_context=current_context,
            persist_log=self.persist_log,
        )
        updated_context = result.get("conversation_context") or {}
        self.context_store.save_context(effective_conversation_key, updated_context)
        return {
            "channel": "telegram",
            "chat_id": str(chat_id),
            "user_id": str(user_id) if user_id not in (None, "") else None,
            "chat_type": chat_type,
            "message_thread_id": str(message_thread_id) if message_thread_id not in (None, "") else None,
            "conversation_key": effective_conversation_key,
            "input_text": text,
            "normalized_input_text": normalized_text,
            "response_text": result["response_text"],
            "parsed_query": result["parsed_query"],
            "conversation_context": deepcopy(updated_context),
            "audit_trace": deepcopy(result.get("audit_trace") or {}),
            "resolved_references": deepcopy(result.get("resolved_references") or {}),
            "send_message_payload": {
                "chat_id": str(chat_id),
                "text": result["response_text"],
            },
        }

    def handle_update(self, update: dict) -> dict:
        incoming = extract_telegram_message(update)
        result = self.handle_incoming_text(
            chat_id=incoming["chat_id"],
            text=incoming["text"],
            user_id=incoming.get("user_id"),
            chat_type=incoming.get("chat_type"),
            message_thread_id=incoming.get("message_thread_id"),
            conversation_key=incoming.get("conversation_key"),
        )
        result["update_id"] = incoming.get("update_id")
        result["message_id"] = incoming.get("message_id")
        return result

    def _handle_command(
        self,
        *,
        chat_id: str | int,
        user_id: str | int | None,
        chat_type: str | None,
        message_thread_id: str | int | None,
        conversation_key: str,
        command: str,
    ) -> dict:
        current_context = self.context_store.get_context(conversation_key)
        if command == "/reset":
            self.context_store.clear_context(conversation_key)
            response_text = "Listo: limpie el contexto de esta conversacion en Telegram. Arrancamos de cero."
            updated_context = {}
        elif command == "/start":
            response_text = (
                "Agenda AI por Telegram ya esta listo. Podes pedirme resumenes, prioridades, friccion, "
                "recomendaciones, vencimientos, agenda personal y acciones conversacionales."
            )
            updated_context = current_context
        elif command in {"/status", "/whoami"}:
            scope = current_context.get("scope") if isinstance(current_context, dict) else None
            entity_name = _context_entity_name(current_context)
            lines = [
                f"chat_id: {chat_id}",
                f"user_id: {user_id or 'n/d'}",
                f"chat_type: {chat_type or 'n/d'}",
                f"message_thread_id: {message_thread_id or 'n/d'}",
                f"conversation_key: {conversation_key}",
            ]
            if scope and entity_name:
                lines.append(f"contexto activo: {scope} -> {entity_name}")
            elif scope:
                lines.append(f"contexto activo: {scope}")
            else:
                lines.append("contexto activo: ninguno")
            response_text = "\n".join(lines)
            updated_context = current_context
        else:
            response_text = (
                "Comandos disponibles:\n"
                "- /start: inicia el canal Telegram\n"
                "- /help: muestra esta ayuda\n"
                "- /reset: limpia solo esta conversacion\n"
                "- /status: muestra ids y contexto actual\n"
                "- /whoami: muestra identidad Telegram de esta conversacion\n\n"
                "Ejemplos:\n"
                "- comentame en que andamos con Cam\n"
                "- que harias ahora\n"
                "- agregame una tarea a cam: hacer revision anual\n"
                "- agendame manana a las 10 una reunion con Cam"
            )
            updated_context = current_context

        return {
            "channel": "telegram",
            "chat_id": str(chat_id),
            "user_id": str(user_id) if user_id not in (None, "") else None,
            "chat_type": chat_type,
            "message_thread_id": str(message_thread_id) if message_thread_id not in (None, "") else None,
            "conversation_key": conversation_key,
            "input_text": command,
            "normalized_input_text": command,
            "channel_command": command,
            "response_text": response_text,
            "parsed_query": {"intent": "telegram_channel_command", "command": command},
            "conversation_context": deepcopy(updated_context),
            "audit_trace": {},
            "resolved_references": {},
            "send_message_payload": {
                "chat_id": str(chat_id),
                "text": response_text,
            },
        }


def _context_entity_name(context: dict | None) -> str | None:
    if not isinstance(context, dict):
        return None
    scope = context.get("scope")
    if scope == "agenda":
        agenda_context = context.get("agenda_context") or {}
        return agenda_context.get("title")
    if scope in {"client", "project", "task"}:
        item = context.get(scope) or {}
        return item.get("name")
    return None


def _build_friendly_telegram_summary(*, reports: list[dict], command_responses: list[str]) -> str:
    lines: list[str] = []
    ok_messages = [report.get("message") for report in reports if report.get("ok") and report.get("message")]
    fail_messages = [report.get("message") for report in reports if not report.get("ok") and report.get("message")]

    if ok_messages:
        lines.append("Listo, avancé con esto:")
        for message in ok_messages:
            lines.append(f"- {message}")
    if fail_messages:
        lines.append("Quedaron pendientes estos puntos:")
        for message in fail_messages:
            lines.append(f"- {message}")
    for command_text in command_responses:
        if command_text:
            lines.append(command_text)
    return "\n".join(lines).strip()

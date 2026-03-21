import json
import re
from typing import Any

import requests

from app.config import (
    LLM_API_KEY,
    LLM_MODEL_NAME,
    LLM_PARSER_URL,
    LLM_TIMEOUT_SECONDS,
)

ALLOWED_INTENTS = {
    "get_active_projects",
    "get_active_clients",
    "get_open_tasks_by_client_name",
    "get_client_summary",
    "get_projects_by_client_name",
    "get_tasks_by_client_name",
    "get_tasks_by_project_name",
    "get_tasks_by_project_and_client",
    "get_tasks_by_status",
    "get_task_summary",
    "get_project_summary",
    "get_blocked_items_summary",
    "get_today_priority_summary",
    "get_overdue_or_stuck_summary",
    "get_client_attention_summary",
    "get_project_attention_summary",
    "get_general_executive_summary",
    "get_operational_summary",
    "get_operational_friction_summary",
    "get_operational_recommendation",
    "get_followup_focus_summary",
    "get_recommendation_explanation",
    "get_filtered_context_summary",
    "get_rephrased_summary",
    "get_client_facing_summary",
    "get_next_actions_summary",
    "get_missing_next_actions_summary",
    "get_followup_needed_summary",
    "get_push_today_summary",
    "get_due_tasks_summary",
    "get_overdue_tasks_summary",
    "get_missing_due_date_summary",
    "create_agenda_item",
    "get_agenda_items_summary",
    "update_agenda_item",
    "delete_agenda_item",
    "compound_query",
    "clarify_entity_reference",
    "create_task",
    "create_followup",
    "add_project_note",
    "update_task_status",
    "add_task_update",
    "add_task_note",
    "update_task_next_action",
    "update_task_last_note",
    "update_task_priority",
    "complete_task_by_name",
    "update_task_priority_by_name",
    "add_task_update_by_name",
    "get_today_activity",
    "get_today_queries",
    "get_today_changes",
    "get_last_interaction",
    "create_client",
    "telegram_channel_command",
    "unknown",
}

EMPTY_PAYLOAD = {
    "intent": "unknown",
    "command": None,
    "client_name": None,
    "project_name": None,
    "task_name": None,
    "task_id": None,
    "project_id": None,
    "content": None,
    "new_status": None,
    "new_priority": None,
    "priority_direction": None,
    "next_action": None,
    "last_note": None,
    "entity_hint": None,
    "expected_scope": None,
    "secondary_descriptor": None,
    "contrast_hint": None,
    "use_previous_candidates": None,
    "recommendation_focus": None,
    "followup_focus": None,
    "filter_mode": None,
    "rephrase_style": None,
    "due_hint": None,
    "time_scope": None,
    "temporal_focus": None,
    "agenda_kind": None,
    "agenda_date_hint": None,
    "agenda_time_hint": None,
    "agenda_title": None,
    "agenda_query_scope": None,
    "agenda_boolean_query": None,
    "agenda_target_title": None,
    "agenda_target_date_hint": None,
    "agenda_target_time_hint": None,
    "agenda_target_kind": None,
    "agenda_use_context": None,
    "agenda_new_date_hint": None,
    "agenda_new_time_hint": None,
}

EXAMPLES_BLOCK = """
Ejemplos correctos:

Usuario: resumime las tareas de cam
JSON:
{
  "intent": "get_tasks_by_client_name",
  "client_name": "cam",
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "recommendation_focus": null
}

Usuario: decime los proyectos de rosario capilar
JSON:
{
  "intent": "get_projects_by_client_name",
  "client_name": "rosario capilar",
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "recommendation_focus": null
}

Usuario: decime las tareas de automatizacion de cam
JSON:
{
  "intent": "get_tasks_by_project_and_client",
  "client_name": "cam",
  "project_name": "automatizacion",
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null
}

Usuario: resumime la tarea dashboard
JSON:
{
  "intent": "get_task_summary",
  "client_name": null,
  "project_name": null,
  "task_name": "dashboard",
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null
}

Usuario: marca onboarding como en progreso
JSON:
{
  "intent": "update_task_status",
  "client_name": null,
  "project_name": null,
  "task_name": "onboarding",
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": "en_progreso",
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null
}

Usuario: subile la prioridad a onboarding
JSON:
{
  "intent": "update_task_priority",
  "client_name": null,
  "project_name": null,
  "task_name": "onboarding",
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": "up",
  "next_action": null,
  "last_note": null
}

Usuario: agrega una nota a onboarding: falta validar con el cliente
JSON:
{
  "intent": "add_task_note",
  "client_name": null,
  "project_name": null,
  "task_name": "onboarding",
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": "falta validar con el cliente",
  "recommendation_focus": null
}

Usuario: deja como proxima accion llamar manana
JSON:
{
  "intent": "update_task_next_action",
  "client_name": null,
  "project_name": null,
  "task_name": "esta tarea",
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": "llamar manana",
  "last_note": null,
  "recommendation_focus": null
}

Usuario: resumime el cliente Dallas
JSON:
{
  "intent": "get_client_summary",
  "client_name": "dallas",
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "recommendation_focus": null
}

Usuario: y sus proyectos?
JSON:
{
  "intent": "get_projects_by_client_name",
  "client_name": "este cliente",
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "recommendation_focus": null
}

Usuario: ponelo en alta
JSON:
{
  "intent": "update_task_priority",
  "client_name": null,
  "project_name": null,
  "task_name": "eso",
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": "alta",
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "recommendation_focus": null
}

Usuario: que esta bloqueado
JSON:
{
  "intent": "get_blocked_items_summary",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "recommendation_focus": null
}

Usuario: que deberia hacer hoy
JSON:
{
  "intent": "get_today_priority_summary",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "recommendation_focus": null
}

Usuario: que cliente necesita atencion primero
JSON:
{
  "intent": "get_client_attention_summary",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "recommendation_focus": null
}

Usuario: que proyecto esta mas trabado
JSON:
{
  "intent": "get_project_attention_summary",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "recommendation_focus": null
}

Usuario: que sigue para este cliente
JSON:
{
  "intent": "get_next_actions_summary",
  "client_name": "este cliente",
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null
}

Usuario: que tareas no tienen proxima accion
JSON:
{
  "intent": "get_missing_next_actions_summary",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null
}

Usuario: que quedo abierto sin seguimiento
JSON:
{
  "intent": "get_followup_needed_summary",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null
}

Usuario: que deberia empujar hoy si o si
JSON:
{
  "intent": "get_push_today_summary",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null
}

Usuario: comentame en que andamos con cam
JSON:
{
  "intent": "get_operational_summary",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "entity_hint": "cam",
  "recommendation_focus": null
}

Usuario: que viene estancado
JSON:
{
  "intent": "get_operational_friction_summary",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "entity_hint": null,
  "recommendation_focus": null
}

Usuario: que me recomendas hacer con cam
JSON:
{
  "intent": "get_operational_recommendation",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "entity_hint": "cam",
  "recommendation_focus": null
}

Usuario: por que esa
JSON:
{
  "intent": "get_recommendation_explanation",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "entity_hint": null,
  "recommendation_focus": null,
  "followup_focus": null,
  "filter_mode": null,
  "rephrase_style": null
}

Usuario: dashboard
JSON:
{
  "intent": "clarify_entity_reference",
  "client_name": null,
  "project_name": null,
  "task_name": null,
  "task_id": null,
  "project_id": null,
  "content": null,
  "new_status": null,
  "new_priority": null,
  "priority_direction": null,
  "next_action": null,
  "last_note": null,
  "entity_hint": "dashboard",
  "recommendation_focus": null
}
""".strip()

SYSTEM_PROMPT = f"""
Sos un parser estricto de lenguaje natural para una agenda operativa.
Tu trabajo es convertir la consulta del usuario en una LISTA JSON valida de acciones.

Reglas:
1. Responde SOLO JSON.
2. No expliques nada.
3. No uses markdown.
4. No incluyas bloques <think>.
5. Si no estas seguro, usa intent = "unknown".
6. Si el usuario nombra una tarea por nombre, completa task_name.
7. Si nombra un cliente, completa client_name.
8. Si nombra un proyecto, completa project_name.
9. No inventes IDs.
10. Si el usuario dice "esta tarea", "este proyecto" o "este cliente", conserva esa referencia textual en task_name, project_name o client_name.
11. Para "subile la prioridad", usa priority_direction = "up".
12. Para notas operativas, usa intent = "add_task_note" y completa last_note.
13. Si hay multiples pedidos en el mismo texto, devolve multiples acciones ordenadas secuencialmente.
14. Usa intent = "create_client" si el usuario pide crear un cliente.
15. Usa intent = "telegram_channel_command" y command en ["/start","/help","/reset","/status","/whoami"] si detectas un comando de canal.

Intentos permitidos:
- get_active_projects
- get_active_clients
- get_open_tasks_by_client_name
- get_client_summary
- get_projects_by_client_name
- get_tasks_by_client_name
- get_tasks_by_project_name
- get_tasks_by_project_and_client
- get_tasks_by_status
- get_task_summary
- get_project_summary
- get_blocked_items_summary
- get_today_priority_summary
- get_overdue_or_stuck_summary
- get_client_attention_summary
- get_project_attention_summary
- get_general_executive_summary
- get_operational_summary
- get_operational_friction_summary
- get_operational_recommendation
- get_next_actions_summary
- get_missing_next_actions_summary
- get_followup_needed_summary
- get_push_today_summary
- get_due_tasks_summary
- get_overdue_tasks_summary
- get_missing_due_date_summary
- compound_query
- clarify_entity_reference
- create_task
- create_followup
- add_project_note
- update_task_status
- add_task_update
- add_task_note
- update_task_next_action
- update_task_last_note
- update_task_priority
- complete_task_by_name
- update_task_priority_by_name
- add_task_update_by_name
- get_today_activity
- get_today_queries
- get_today_changes
- get_last_interaction
- create_client
- telegram_channel_command
- unknown

Formato exacto de salida:
[
  {{
    "intent": "unknown",
    "command": null,
    "client_name": null,
    "project_name": null,
    "task_name": null,
    "task_id": null,
    "project_id": null,
    "content": null,
    "new_status": null,
    "new_priority": null,
    "priority_direction": null,
    "next_action": null,
    "last_note": null,
    "entity_hint": null,
    "recommendation_focus": null,
    "followup_focus": null,
    "filter_mode": null,
    "rephrase_style": null,
    "due_hint": null,
    "time_scope": null,
    "temporal_focus": null,
    "agenda_kind": null,
    "agenda_date_hint": null,
    "agenda_time_hint": null,
    "agenda_title": null
  }}
]

{EXAMPLES_BLOCK}
""".strip()


def _strip_think_blocks(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None


def _extract_first_json_array(text: str) -> str | None:
    start = text.find("[")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        char = text[i]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _clean_model_output(text: str) -> str | None:
    text = text.strip()
    text = _strip_think_blocks(text)
    text = _strip_code_fences(text)
    array_payload = _extract_first_json_array(text)
    if array_payload:
        return array_payload
    return _extract_first_json_object(text)


def _normalize_nullable_string(value):
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    value = value.strip()
    return value if value else None


def _normalize_int_or_none(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _validate_payload_shape(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    clean = dict(EMPTY_PAYLOAD)
    for key in EMPTY_PAYLOAD:
        if key in payload:
            clean[key] = payload[key]

    clean["intent"] = _normalize_nullable_string(clean.get("intent")) or "unknown"
    clean["command"] = _normalize_nullable_string(clean.get("command"))
    clean["client_name"] = _normalize_nullable_string(clean.get("client_name"))
    clean["project_name"] = _normalize_nullable_string(clean.get("project_name"))
    clean["task_name"] = _normalize_nullable_string(clean.get("task_name"))
    clean["content"] = _normalize_nullable_string(clean.get("content"))
    clean["new_status"] = _normalize_nullable_string(clean.get("new_status"))
    clean["new_priority"] = _normalize_nullable_string(clean.get("new_priority"))
    clean["priority_direction"] = _normalize_nullable_string(clean.get("priority_direction"))
    clean["next_action"] = _normalize_nullable_string(clean.get("next_action"))
    clean["last_note"] = _normalize_nullable_string(clean.get("last_note"))
    clean["entity_hint"] = _normalize_nullable_string(clean.get("entity_hint"))
    clean["recommendation_focus"] = _normalize_nullable_string(clean.get("recommendation_focus"))
    clean["followup_focus"] = _normalize_nullable_string(clean.get("followup_focus"))
    clean["filter_mode"] = _normalize_nullable_string(clean.get("filter_mode"))
    clean["rephrase_style"] = _normalize_nullable_string(clean.get("rephrase_style"))
    clean["due_hint"] = _normalize_nullable_string(clean.get("due_hint"))
    clean["time_scope"] = _normalize_nullable_string(clean.get("time_scope"))
    clean["temporal_focus"] = _normalize_nullable_string(clean.get("temporal_focus"))

    clean["task_id"] = _normalize_int_or_none(clean.get("task_id"))
    clean["project_id"] = _normalize_int_or_none(clean.get("project_id"))

    if clean["intent"] not in ALLOWED_INTENTS:
        return None
    if clean["intent"] == "telegram_channel_command":
        if clean.get("command") not in {"/start", "/help", "/reset", "/status", "/whoami"}:
            return None

    return clean


def _is_plural_query(query: str) -> bool:
    q = query.lower()
    return any(word in q for word in [" tareas ", "tareas ", " tareas", " proyectos ", "proyectos ", " proyectos"])


def _mentions_open_only(query: str) -> bool:
    q = query.lower()
    return any(word in q for word in ["abierta", "abiertas", "abierto", "abiertos", "pendiente", "pendientes"])


def _coerce_semantics(payload: dict[str, Any], user_query: str) -> dict[str, Any]:
    q = f" {user_query.strip().lower()} "
    intent = payload["intent"]

    client_name = payload.get("client_name")
    project_name = payload.get("project_name")
    task_name = payload.get("task_name")
    task_id = payload.get("task_id")
    project_id = payload.get("project_id")

    if intent == "clarify_entity_reference":
        if not payload.get("entity_hint"):
            payload["entity_hint"] = task_name or project_name or client_name
        payload["client_name"] = None
        payload["project_name"] = None
        payload["task_name"] = None
        payload["task_id"] = None
        payload["project_id"] = None
        if not payload.get("entity_hint"):
            payload["intent"] = "unknown"

    if intent == "get_operational_summary":
        if not payload.get("entity_hint"):
            payload["entity_hint"] = task_name or project_name or client_name
        if not any([payload.get("entity_hint"), client_name, project_name, task_name, task_id, project_id]):
            payload["intent"] = "unknown"

    if intent == "get_operational_friction_summary":
        if not payload.get("entity_hint"):
            payload["entity_hint"] = task_name or project_name or client_name
        if not any([payload.get("entity_hint"), client_name, project_name, task_name, task_id, project_id]):
            payload["intent"] = "unknown"

    if intent == "get_operational_recommendation":
        if not payload.get("entity_hint"):
            payload["entity_hint"] = task_name or project_name or client_name
        if not any([payload.get("entity_hint"), client_name, project_name, task_name, task_id, project_id]):
            payload["intent"] = "unknown"

    if intent in {"create_task", "create_followup"}:
        if not task_name and not payload.get("entity_hint"):
            payload["intent"] = "unknown"

    if intent == "add_project_note":
        if not payload.get("last_note"):
            payload["intent"] = "unknown"
        if not project_name and not payload.get("entity_hint"):
            payload["project_name"] = "este proyecto"

    if intent == "create_client":
        if not client_name:
            payload["intent"] = "unknown"

    if intent == "telegram_channel_command":
        if payload.get("command") not in {"/start", "/help", "/reset", "/status", "/whoami"}:
            payload["intent"] = "unknown"

    if intent == "compound_query":
        payload["intent"] = "unknown"

    if intent == "get_due_tasks_summary":
        if payload.get("time_scope") not in {"today", "tomorrow", "this_week", "due_items"}:
            payload["intent"] = "unknown"

    if intent == "get_overdue_tasks_summary":
        payload["time_scope"] = "overdue"

    if intent == "get_missing_due_date_summary":
        payload["time_scope"] = None

    if intent == "get_task_summary":
        if not task_id and not task_name:
            if client_name and project_name:
                payload["intent"] = "get_tasks_by_project_and_client"
            elif client_name:
                payload["intent"] = "get_tasks_by_client_name"
            elif project_name:
                payload["intent"] = "get_tasks_by_project_name"
            elif _is_plural_query(q):
                payload["intent"] = "unknown"

    if intent == "get_project_summary":
        if not project_id and not project_name:
            if client_name:
                payload["intent"] = "get_projects_by_client_name"
            else:
                payload["intent"] = "unknown"

    if intent in {
        "get_blocked_items_summary",
        "get_today_priority_summary",
        "get_overdue_or_stuck_summary",
        "get_client_attention_summary",
        "get_project_attention_summary",
        "get_general_executive_summary",
        "get_missing_next_actions_summary",
        "get_followup_needed_summary",
        "get_push_today_summary",
    }:
        payload["client_name"] = None
        payload["project_name"] = None
        payload["task_name"] = None

    if intent == "get_open_tasks_by_client_name":
        if client_name and not _mentions_open_only(q):
            payload["intent"] = "get_tasks_by_client_name"

    if intent == "get_client_summary" and not client_name:
        payload["intent"] = "unknown"

    if intent == "get_tasks_by_status":
        valid_statuses = {"pendiente", "en_progreso", "bloqueada", "hecha"}
        if payload.get("new_status") not in valid_statuses:
            payload["intent"] = "unknown"

    if intent == "get_tasks_by_project_and_client":
        if client_name and not project_name:
            payload["intent"] = "get_tasks_by_client_name"
        elif project_name and not client_name:
            payload["intent"] = "get_tasks_by_project_name"
        elif not client_name and not project_name:
            payload["intent"] = "unknown"

    if intent == "get_tasks_by_project_name" and not project_name:
        if client_name:
            payload["intent"] = "get_tasks_by_client_name"
        else:
            payload["intent"] = "unknown"

    if intent == "get_projects_by_client_name" and not client_name:
        payload["intent"] = "unknown"

    if intent == "update_task_status":
        valid_statuses = {"pendiente", "en_progreso", "bloqueada", "hecha"}
        if payload.get("new_status") not in valid_statuses:
            payload["intent"] = "unknown"
        if not task_id and not task_name:
            payload["task_name"] = "esta tarea"

    if intent == "update_task_priority":
        valid_priorities = {"baja", "media", "alta"}
        if payload.get("new_priority") not in valid_priorities and payload.get("priority_direction") != "up":
            payload["intent"] = "unknown"
        if not task_id and not task_name:
            payload["task_name"] = "esta tarea"

    if intent == "update_task_priority_by_name":
        valid_priorities = {"baja", "media", "alta"}
        if payload.get("new_priority") not in valid_priorities or not task_name:
            payload["intent"] = "unknown"

    if intent == "add_task_update_by_name":
        if not task_name or not payload.get("content"):
            payload["intent"] = "unknown"

    if intent == "add_task_note":
        if not payload.get("last_note"):
            payload["intent"] = "unknown"
        if not task_id and not task_name:
            payload["task_name"] = "esta tarea"

    if intent == "complete_task_by_name" and not task_name:
        payload["intent"] = "unknown"

    if intent == "update_task_next_action":
        if not payload.get("next_action"):
            payload["intent"] = "unknown"
        if not task_id and not task_name:
            payload["task_name"] = "esta tarea"

    return payload


def parse_actions_with_llm(user_query: str) -> list[dict[str, Any]]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    }

    body = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ],
        "temperature": 0,
        "max_tokens": 700,
    }

    try:
        response = requests.post(
            LLM_PARSER_URL,
            headers=headers,
            json=body,
            timeout=LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

        raw_content = data["choices"][0]["message"]["content"]
        cleaned = _clean_model_output(raw_content)
        if not cleaned:
            return []

        parsed = json.loads(cleaned)
        candidates = parsed if isinstance(parsed, list) else [parsed]
        actions: list[dict[str, Any]] = []
        for candidate in candidates:
            validated = _validate_payload_shape(candidate)
            if not validated:
                continue
            validated = _coerce_semantics(validated, user_query)
            validated = _validate_payload_shape(validated)
            if not validated:
                continue
            validated["_parser_source"] = "llm"
            actions.append(validated)
        return actions

    except Exception:
        return []


def parse_query_with_llm(user_query: str) -> dict[str, Any] | None:
    actions = parse_actions_with_llm(user_query)
    for action in actions:
        if action.get("intent") not in (None, "", "unknown"):
            return action
    return actions[0] if actions else None

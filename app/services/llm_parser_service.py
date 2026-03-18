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
    "get_next_actions_summary",
    "get_missing_next_actions_summary",
    "get_followup_needed_summary",
    "get_push_today_summary",
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
    "unknown",
}

EMPTY_PAYLOAD = {
    "intent": "unknown",
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
  "last_note": null
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
  "last_note": null
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
  "last_note": "falta validar con el cliente"
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
  "last_note": null
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
  "last_note": null
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
  "last_note": null
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
  "last_note": null
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
  "last_note": null
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
  "last_note": null
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
  "last_note": null
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
  "last_note": null
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
""".strip()

SYSTEM_PROMPT = f"""
Sos un parser estricto de lenguaje natural para una agenda operativa.
Tu trabajo es convertir la consulta del usuario en UN SOLO JSON valido.

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

Intentos permitidos:
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
- get_next_actions_summary
- get_missing_next_actions_summary
- get_followup_needed_summary
- get_push_today_summary
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
- unknown

Schema exacto:
{{
  "intent": "unknown",
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
}}

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


def _clean_model_output(text: str) -> str | None:
    text = text.strip()
    text = _strip_think_blocks(text)
    text = _strip_code_fences(text)
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
    clean["client_name"] = _normalize_nullable_string(clean.get("client_name"))
    clean["project_name"] = _normalize_nullable_string(clean.get("project_name"))
    clean["task_name"] = _normalize_nullable_string(clean.get("task_name"))
    clean["content"] = _normalize_nullable_string(clean.get("content"))
    clean["new_status"] = _normalize_nullable_string(clean.get("new_status"))
    clean["new_priority"] = _normalize_nullable_string(clean.get("new_priority"))
    clean["priority_direction"] = _normalize_nullable_string(clean.get("priority_direction"))
    clean["next_action"] = _normalize_nullable_string(clean.get("next_action"))
    clean["last_note"] = _normalize_nullable_string(clean.get("last_note"))

    clean["task_id"] = _normalize_int_or_none(clean.get("task_id"))
    clean["project_id"] = _normalize_int_or_none(clean.get("project_id"))

    if clean["intent"] not in ALLOWED_INTENTS:
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


def parse_query_with_llm(user_query: str) -> dict[str, Any] | None:
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
        "max_tokens": 260,
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
            return None

        parsed = json.loads(cleaned)
        validated = _validate_payload_shape(parsed)
        if not validated:
            return None

        validated = _coerce_semantics(validated, user_query)
        validated = _validate_payload_shape(validated)
        if not validated:
            return None

        validated["_parser_source"] = "llm"
        return validated

    except Exception:
        return None

import re


STATUS_MAP = {
    "hecha": "hecha",
    "completada": "hecha",
    "completa": "hecha",
    "cerrada": "hecha",
    "cerra": "hecha",
    "en progreso": "en_progreso",
    "bloqueada": "bloqueada",
    "bloqueado": "bloqueada",
    "pendiente": "pendiente",
}

PRIORITY_WORDS = ("alta", "media", "baja")
CONTEXT_TASK_NAMES = ("esta tarea", "esa tarea", "tarea actual")
CONTEXT_PROJECT_NAMES = ("este proyecto", "ese proyecto", "proyecto actual")
CONTEXT_CLIENT_NAMES = ("este cliente", "ese cliente", "cliente actual")


def parse_user_query(query: str) -> dict:
    normalized = query.strip().lower()

    result = (
        _parse_read_intents(normalized)
        or _parse_task_update_intents(normalized)
        or _parse_today_intents(normalized)
    )
    return result or {"intent": "unknown"}


def _parse_read_intents(normalized: str) -> dict | None:
    if any(
        phrase in normalized
        for phrase in [
            "armame un resumen de proximos pasos",
            "resumen de proximos pasos",
        ]
    ):
        return {"intent": "get_next_actions_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que tareas no tienen proxima accion",
            "que tareas no tienen next action",
            "que esta frenado por falta de next action",
        ]
    ):
        return {"intent": "get_missing_next_actions_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que quedo abierto sin seguimiento",
            "que follow-ups tengo pendientes",
            "que followups tengo pendientes",
            "que habria que definir ahora",
        ]
    ):
        return {"intent": "get_followup_needed_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que deberia empujar hoy si o si",
            "que deberia empujar hoy",
        ]
    ):
        return {"intent": "get_push_today_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que sigue para este cliente",
            "que sigue para ese cliente",
        ]
    ):
        client_name = "este cliente" if "este cliente" in normalized else "ese cliente"
        return {"intent": "get_next_actions_summary", "client_name": client_name}

    if any(
        phrase in normalized
        for phrase in [
            "que sigue en este proyecto",
            "que sigue en ese proyecto",
        ]
    ):
        project_name = "este proyecto" if "este proyecto" in normalized else "ese proyecto"
        return {"intent": "get_next_actions_summary", "project_name": project_name}

    if normalized.startswith("que sigue para "):
        target = normalized.removeprefix("que sigue para ").strip()
        if target:
            return {"intent": "get_next_actions_summary", "client_name": target}

    if any(
        phrase in normalized
        for phrase in [
            "resumime lo mas importante del dia",
            "lo mas importante del dia",
        ]
    ):
        return {"intent": "get_general_executive_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que deberia hacer hoy",
            "que hago hoy",
            "que tengo que hacer hoy",
        ]
    ):
        return {"intent": "get_today_priority_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que esta mas atrasado",
            "que esta mas trabado",
            "que esta atrasado",
        ]
    ):
        return {"intent": "get_overdue_or_stuck_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que cliente necesita atencion primero",
            "que cliente necesita mas atencion",
        ]
    ):
        return {"intent": "get_client_attention_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que proyecto esta mas trabado",
            "que proyecto necesita mas atencion",
            "que proyecto esta peor",
        ]
    ):
        return {"intent": "get_project_attention_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que tareas urgentes tengo abiertas",
            "tareas urgentes abiertas",
            "que urgente tengo abierto",
        ]
    ):
        return {"intent": "get_today_priority_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que esta bloqueado",
            "que hay bloqueado",
        ]
    ):
        return {"intent": "get_blocked_items_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que sigue en general",
            "y que sigue",
            "y el proximo paso",
            "y que habria que hacer ahora",
            "y que es lo mas urgente",
        ]
    ):
        if "urgente" in normalized:
            return {"intent": "get_push_today_summary"}
        return {"intent": "get_next_actions_summary"}

    if any(phrase in normalized for phrase in ["resumime el cliente", "decime el cliente", "mostrame el cliente"]):
        match = re.search(r"cliente\s+(.+)$", normalized)
        if match:
            return {"intent": "get_client_summary", "client_name": match.group(1).strip()}

    if any(phrase in normalized for phrase in ["y sus proyectos", "sus proyectos"]):
        return {"intent": "get_projects_by_client_name", "client_name": "este cliente"}

    if any(phrase in normalized for phrase in ["y en ese proyecto", "en ese proyecto", "en este proyecto"]):
        project_name = "ese proyecto" if "ese proyecto" in normalized else "este proyecto"
        return {"intent": "get_tasks_by_project_name", "project_name": project_name}

    if any(phrase in normalized for phrase in ["que sigue ahi", "que sigue ahI", "que sigue alli"]):
        return {"intent": "get_tasks_by_project_name", "project_name": "ahi"}

    if any(
        phrase in normalized
        for phrase in [
            "que tarea esta bloqueada",
            "que tareas estan bloqueadas",
        ]
    ):
        return {"intent": "get_tasks_by_status", "new_status": "bloqueada"}

    if any(
        phrase in normalized
        for phrase in [
            "clientes activos",
            "mis clientes activos",
            "que clientes tengo activos",
            "mostrame mis clientes activos",
            "decime mis clientes activos",
        ]
    ):
        return {"intent": "get_active_clients"}

    if any(
        phrase in normalized
        for phrase in [
            "que tengo pendiente con",
            "tareas abiertas",
            "que tiene abierto",
            "que hay pendiente con",
            "que tareas tiene",
            "mostrame las tareas de",
            "decime las tareas de",
        ]
    ):
        match = re.search(r"(?:de|tiene|con)\s+(.+)$", normalized)
        return {
            "intent": "get_open_tasks_by_client_name",
            "client_name": match.group(1).strip() if match else None,
        }

    if any(phrase in normalized for phrase in ["que sigue con"]):
        match = re.search(r"(?:que sigue con)\s+(.+)$", normalized)
        return {
            "intent": "get_open_tasks_by_client_name",
            "client_name": match.group(1).strip() if match else None,
        }

    if any(
        phrase in normalized
        for phrase in [
            "resumime la tarea",
            "quiero ver la tarea",
            "mostrame la tarea",
            "decime la tarea",
            "resumen de la tarea",
        ]
    ):
        match = re.search(r"tarea\s+(\d+)", normalized)
        if match:
            return {"intent": "get_task_summary", "task_id": int(match.group(1))}

        match = re.search(r"tarea\s+(.+)$", normalized)
        if match:
            return {"intent": "get_task_summary", "task_name": match.group(1).strip()}

    if normalized.startswith("resumime "):
        target = normalized.removeprefix("resumime ").strip()
        if target and not target.startswith(("el cliente ", "la tarea ", "el proyecto ")):
            return {"intent": "get_task_summary", "task_name": target}

    if any(
        phrase in normalized
        for phrase in [
            "resumime el proyecto",
            "quiero ver el proyecto",
            "mostrame el proyecto",
            "decime el proyecto",
            "resumen del proyecto",
        ]
    ):
        match = re.search(r"proyecto\s+(\d+)", normalized)
        if match:
            return {"intent": "get_project_summary", "project_id": int(match.group(1))}

        match = re.search(r"proyecto\s+(.+)$", normalized)
        if match:
            entity_name = match.group(1).strip()
            return {
                "intent": "get_project_summary",
                "project_name": entity_name,
                "task_name": entity_name,
            }

    if any(phrase in normalized for phrase in ["como va ", "como viene "]):
        match = re.search(r"(?:como va|como viene)\s+(.+)$", normalized)
        if match:
            entity_name = match.group(1).strip()
            return {
                "intent": "get_project_summary",
                "project_name": entity_name,
                "task_name": entity_name,
            }

    if any(p in normalized for p in ["proyectos de", "proyectos del"]):
        match = re.search(r"proyectos\s+(?:de|del)\s+(.+)$", normalized)
        if match:
            return {"intent": "get_projects_by_client_name", "client_name": match.group(1).strip()}

    if any(p in normalized for p in ["tareas de", "tareas del"]):
        match_project_client = re.search(r"tareas\s+de\s+(.+)\s+de\s+(.+)$", normalized)
        if match_project_client:
            return {
                "intent": "get_tasks_by_project_and_client",
                "project_name": match_project_client.group(1).strip(),
                "client_name": match_project_client.group(2).strip(),
            }

        match_client = re.search(r"tareas\s+(?:de|del)\s+(.+)$", normalized)
        if match_client:
            return {"intent": "get_tasks_by_client_name", "client_name": match_client.group(1).strip()}

    if "tareas de proyecto" in normalized:
        match = re.search(r"proyecto\s+(.+)$", normalized)
        if match:
            return {"intent": "get_tasks_by_project_name", "project_name": match.group(1).strip()}

    return None


def _parse_task_update_intents(normalized: str) -> dict | None:
    contextual_payload = _extract_contextual_scope(normalized)

    match = re.search(r"(?:ponelo|ponela)\s+en\s+(alta|media|baja)$", normalized)
    if match:
        return {
            "intent": "update_task_priority",
            "task_name": "eso",
            "new_priority": match.group(1).strip(),
            **contextual_payload,
        }

    match = re.search(r"(?:marcalo|marcala)\s+como\s+(en progreso|completada|completa|hecha|bloqueada|pendiente)$", normalized)
    if match:
        return {
            "intent": "update_task_status",
            "task_name": "eso",
            "new_status": STATUS_MAP.get(match.group(1).strip()),
            **contextual_payload,
        }

    if normalized in ("cerrala", "cerralo"):
        return {
            "intent": "update_task_status",
            "task_name": "eso",
            "new_status": "hecha",
            **contextual_payload,
        }

    match = re.search(r"agregale\s+una?\s*nota\s*:\s*(.+)$", normalized)
    if match:
        return {
            "intent": "add_task_note",
            "task_name": "eso",
            "last_note": match.group(1).strip(),
            **contextual_payload,
        }

    if normalized.startswith("subile la prioridad"):
        return {
            "intent": "update_task_priority",
            "task_name": "eso",
            "priority_direction": "up",
            **contextual_payload,
        }

    match = re.search(
        r"tarea\s+(\d+).*(hecha|completada|en progreso|bloqueada|pendiente)$",
        normalized,
    )
    if match and any(phrase in normalized for phrase in ["marca la tarea", "pone la tarea", "pasa la tarea"]):
        return {
            "intent": "update_task_status",
            "task_id": int(match.group(1)),
            "new_status": STATUS_MAP.get(match.group(2).strip()),
        }

    match = re.search(r"tarea\s+(\d+).*(baja|media|alta)", normalized)
    if match and any(
        phrase in normalized
        for phrase in [
            "cambia la prioridad de la tarea",
            "actualiza la prioridad de la tarea",
            "pone la prioridad de la tarea",
        ]
    ):
        return {
            "intent": "update_task_priority",
            "task_id": int(match.group(1)),
            "new_priority": match.group(2).strip(),
        }

    if "deja como proxima accion" in normalized:
        match = re.search(r"(?:deja)\s+como\s+proxima\s+accion\s+(.+)$", normalized)
        if match:
            return {
                "intent": "update_task_next_action",
                "next_action": match.group(1).strip(),
                "task_name": "esta tarea",
                **contextual_payload,
            }

    if any(phrase in normalized for phrase in ["agrega una nota a", "anota en"]):
        match = re.search(r"(?:agrega|anota)\s+una?\s*nota\s+a\s+(.+?)\s*:\s*(.+)$", normalized)
        if not match:
            match = re.search(r"(?:anota)\s+en\s+(.+?)\s*:\s*(.+)$", normalized)
        if match:
            payload = _split_task_scope(match.group(1).strip(), contextual_payload)
            payload.update(
                {
                    "intent": "add_task_note",
                    "last_note": match.group(2).strip(),
                }
            )
            return payload

    if any(phrase in normalized for phrase in ["bloquea"]):
        match = re.search(r"(?:bloquea)\s+(.+?)(?:\s+porque\s+(.+))?$", normalized)
        if match:
            payload = _split_task_scope(match.group(1).strip(), contextual_payload)
            payload.update(
                {
                    "intent": "update_task_status",
                    "new_status": "bloqueada",
                    "last_note": match.group(2).strip() if match.group(2) else None,
                }
            )
            return payload

    if any(phrase in normalized for phrase in ["cerra", "marca"]):
        match = re.search(
            r"(?:cerra|marca)\s+(.+?)\s+como\s+(en progreso|completada|completa|hecha|bloqueada|pendiente)$",
            normalized,
        )
        if match:
            payload = _split_task_scope(match.group(1).strip(), contextual_payload)
            payload.update(
                {
                    "intent": "update_task_status",
                    "new_status": STATUS_MAP.get(match.group(2).strip()),
                }
            )
            return payload

        match = re.search(r"(?:cerra)\s+(.+)$", normalized)
        if match:
            payload = _split_task_scope(match.group(1).strip(), contextual_payload)
            payload.update({"intent": "update_task_status", "new_status": "hecha"})
            return payload

        match = re.search(r"(?:marca)\s+(.+)\s+como\s+completada$", normalized)
        if match:
            payload = _split_task_scope(match.group(1).strip(), contextual_payload)
            payload.update({"intent": "update_task_status", "new_status": "hecha"})
            return payload

    if any(phrase in normalized for phrase in ["pone", "subile la prioridad a"]):
        match = re.search(r"(?:subile la prioridad a)\s+(.+)$", normalized)
        if match:
            payload = _split_task_scope(match.group(1).strip(), contextual_payload)
            payload.update(
                {
                    "intent": "update_task_priority",
                    "priority_direction": "up",
                }
            )
            return payload

        match = re.search(r"(?:pone)\s+(.+?)\s+en\s+(alta|media|baja)$", normalized)
        if match:
            payload = _split_task_scope(match.group(1).strip(), contextual_payload)
            payload.update(
                {
                    "intent": "update_task_priority",
                    "new_priority": match.group(2).strip(),
                }
            )
            return payload

        match = re.search(
            r"(?:pone)\s+(alta|media|baja)\s+prioridad\s+a\s+la?\s*tarea\s+(.+)$",
            normalized,
        )
        if match:
            payload = _split_task_scope(match.group(2).strip(), contextual_payload)
            payload.update(
                {
                    "intent": "update_task_priority",
                    "new_priority": match.group(1).strip(),
                }
            )
            return payload

    if "prioridad" in normalized:
        match = re.search(r"prioridad\s+de\s+(.+)\s+a\s+(alta|media|baja)", normalized)
        if match:
            payload = _split_task_scope(match.group(1).strip(), contextual_payload)
            payload.update(
                {
                    "intent": "update_task_priority",
                    "new_priority": match.group(2).strip(),
                }
            )
            return payload

    if any(phrase in normalized for phrase in ["actualiza la proxima accion de la tarea", "cambia la proxima accion de la tarea"]):
        match = re.search(r"tarea\s+(\d+)\s*:\s*(.+)$", normalized)
        if match:
            return {
                "intent": "update_task_next_action",
                "task_id": int(match.group(1)),
                "next_action": match.group(2).strip(),
            }

    if any(phrase in normalized for phrase in ["actualiza la ultima nota de la tarea", "cambia la ultima nota de la tarea"]):
        match = re.search(r"tarea\s+(\d+)\s*:\s*(.+)$", normalized)
        if match:
            return {
                "intent": "add_task_note",
                "task_id": int(match.group(1)),
                "last_note": match.group(2).strip(),
            }

    if any(phrase in normalized for phrase in ["agrega un update a la tarea", "suma un update a la tarea", "sumale un update a la tarea", "anade un update a la tarea"]):
        match = re.search(r"tarea\s+(\d+)\s*:\s*(.+)$", normalized)
        if match:
            return {
                "intent": "add_task_update",
                "task_id": int(match.group(1)),
                "content": match.group(2).strip(),
            }

    if "hecha" in normalized or "completada" in normalized:
        match = re.search(r"tarea\s+(.+)$", normalized)
        if match:
            return {
                "intent": "complete_task_by_name",
                "task_name": match.group(1).strip(),
            }

    if "update" in normalized:
        match = re.search(r"update\s+a\s+(.+):\s*(.+)$", normalized)
        if match:
            return {
                "intent": "add_task_update_by_name",
                "task_name": match.group(1).strip(),
                "content": match.group(2).strip(),
            }

    return None


def _parse_today_intents(normalized: str) -> dict | None:
    if any(
        phrase in normalized
        for phrase in [
            "que hice hoy",
            "que hice en el asistente hoy",
        ]
    ):
        return {"intent": "get_today_activity"}

    if any(
        phrase in normalized
        for phrase in [
            "que consulte hoy",
            "que pregunte hoy",
        ]
    ):
        return {"intent": "get_today_queries"}

    if any(
        phrase in normalized
        for phrase in [
            "que cambios hubo hoy",
            "que actualice hoy",
        ]
    ):
        return {"intent": "get_today_changes"}

    if any(
        phrase in normalized
        for phrase in [
            "que le pedi recien al asistente",
            "ultima consulta",
            "que hice recien",
        ]
    ):
        return {"intent": "get_last_interaction"}

    return None


def _extract_contextual_scope(normalized: str) -> dict:
    payload = {}
    for project_name in CONTEXT_PROJECT_NAMES:
        if project_name in normalized:
            payload["project_name"] = project_name
            break

    for client_name in CONTEXT_CLIENT_NAMES:
        if client_name in normalized:
            payload["client_name"] = client_name
            break

    return payload


def _split_task_scope(raw_target: str, contextual_payload: dict) -> dict:
    payload = dict(contextual_payload)
    target = raw_target.strip()

    if target in CONTEXT_TASK_NAMES:
        payload["task_name"] = target
        return payload

    target = re.sub(r"^(la|el)\s+tarea\s+", "", target).strip()
    target = re.sub(r"^(la|el)\s+", "", target).strip()
    target = re.sub(r"^(del|de la)\s+", "", target).strip()

    if " de " in target and "este proyecto" not in target and "ese proyecto" not in target:
        task_name, project_name = target.split(" de ", 1)
        payload["task_name"] = task_name.strip()
        payload["project_name"] = project_name.strip()
        return payload

    payload["task_name"] = target
    return payload

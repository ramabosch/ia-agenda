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
OPEN_ENTITY_TERMS = {
    "dashboard",
    "onboarding",
    "cam",
    "indicadores",
}
GENERIC_ENTITY_TERMS = {
    "cliente",
    "proyecto",
    "tarea",
    "eso",
    "esto",
    "algo",
}
TEMPORAL_DAY_TERMS = ("lunes", "martes", "miercoles", "miércoles", "jueves", "viernes", "sabado", "sábado", "domingo")
AMBIGUOUS_TEMPORAL_TERMS = ("pronto", "mas adelante", "más adelante", "despues", "después", "algun dia", "algún día")


def parse_user_query(query: str) -> dict:
    normalized = query.strip().lower()
    return _parse_user_query_internal(normalized, allow_compound=True)


def _parse_user_query_internal(normalized: str, *, allow_compound: bool) -> dict:
    if allow_compound:
        compound = _parse_compound_intents(normalized)
        if compound:
            return compound

    result = (
        _parse_creation_intents(normalized)
        or _parse_temporal_read_intents(normalized)
        or _parse_read_intents(normalized)
        or _parse_ambiguity_intents(normalized)
        or _parse_task_update_intents(normalized)
        or _parse_today_intents(normalized)
    )
    return result or {"intent": "unknown"}


def _parse_compound_intents(normalized: str) -> dict | None:
    connectors = (
        " y despues decime ",
        " y despuÃ©s decime ",
        " y despues ",
        " y despuÃ©s ",
        " y decime ",
        " y quÃ© ",
        " y que ",
        " pero ",
        " y ",
    )
    prefixes = (
        "decime ",
        "comentame ",
        "comentÃ¡me ",
        "mostrame ",
        "mostrÃ¡me ",
    )

    for connector in connectors:
        if connector not in normalized:
            continue
        first_part, second_part = normalized.split(connector, 1)
        first_part = first_part.strip(" ,.;")
        second_part = second_part.strip(" ,.;")
        for prefix in prefixes:
            if second_part.startswith(prefix):
                second_part = second_part.removeprefix(prefix).strip()
                break

        if second_part in {"urgente", "urgentes", "atrasado", "atrasados", "vencido", "vencidos"}:
            if first_part.startswith("que tengo "):
                second_part = f"que tengo {second_part}"
            elif first_part.startswith("que esta ") or first_part.startswith("que estÃ¡ "):
                second_part = f"que esta {second_part}"
        elif second_part in {"bloqueado", "bloqueada", "bloqueados", "bloqueadas"}:
            second_part = "que esta bloqueado"
        elif second_part == "que sigue":
            second_part = "y que sigue"

        if not first_part or not second_part or first_part == second_part:
            continue

        first_query = _parse_user_query_internal(first_part, allow_compound=False)
        second_query = _parse_user_query_internal(second_part, allow_compound=False)
        if first_query.get("intent") == "unknown" or second_query.get("intent") == "unknown":
            continue

        return {
            "intent": "compound_query",
            "subqueries": [first_query, second_query],
            "compound_parts": [first_part, second_part],
        }

    return None


def _parse_creation_intents(normalized: str) -> dict | None:
    create_task_prefix = r"(?:cre(?:a|á)\s+una|cre(?:a|á)|agreg(?:a|á)\s+una|agreg(?:a|á)|sum(?:a|á)\s+una|sum(?:a|á))"
    create_followup_prefix = r"(?:cre(?:a|á)\s+un|cre(?:a|á)|agreg(?:a|á)\s+un|agreg(?:a|á)|sum(?:a|á)\s+un|sum(?:a|á))"
    priority = "alta" if any(token in normalized for token in ["alta prioridad", "prioridad alta", "urgente"]) else None

    stripped_normalized, due_hint, time_scope = _extract_supported_due_hint(normalized)

    match = re.search(rf"^{create_task_prefix}\s+tarea\s+a\s+(.+?)\s+para\s+(.+)$", stripped_normalized)
    if match:
        payload = {
            "intent": "create_task",
            "client_name": match.group(1).strip(),
            "task_name": match.group(2).strip(),
            "new_priority": priority,
        }
        return _apply_temporal_fields(payload, due_hint, time_scope)

    match = re.search(rf"^{create_task_prefix}\s+tarea\s+en\s+(.+?)(?:\s+para\s+(.+)|\s*:\s*(.+))?$", stripped_normalized)
    if match:
        task_title = (match.group(2) or match.group(3) or "").strip() or None
        target = match.group(1).strip()
        payload = {
            "intent": "create_task",
            "task_name": task_title,
            "new_priority": priority,
        }
        if "proyecto" in target:
            payload["project_name"] = target
        else:
            payload["entity_hint"] = target
        return _apply_temporal_fields(payload, due_hint, time_scope)

    match = re.search(rf"^{create_task_prefix}\s+tarea(?:\s+(?:de\s+)?)?(?:urgente|alta prioridad|prioridad alta)?\s+para\s+(.+)$", stripped_normalized)
    if match:
        payload = {
            "intent": "create_task",
            "task_name": match.group(1).strip(),
            "new_priority": priority,
        }
        return _apply_temporal_fields(payload, due_hint, time_scope)

    match = re.search(rf"^{create_task_prefix}\s+tarea(?:\s+(?:urgente|alta prioridad|prioridad alta))?$", stripped_normalized)
    if match:
        return _apply_temporal_fields(
            {
                "intent": "create_task",
                "task_name": None,
                "new_priority": priority,
            },
            due_hint,
            time_scope,
        )

    if any(phrase in normalized for phrase in ["converti esto en tarea", "convertí esto en tarea", "convierte esto en tarea"]):
        return _apply_temporal_fields({"intent": "create_task", "task_name": "esto"}, due_hint, time_scope)

    match = re.search(rf"^(?:dej(?:a|á)|{create_followup_prefix})\s+follow-?up(?:\s+para\s+(.+))?$", stripped_normalized)
    if match:
        return _apply_temporal_fields({
            "intent": "create_followup",
            "task_name": match.group(1).strip() if match and match.group(1) else None,
            "new_priority": priority,
        }, due_hint, time_scope)

    match = re.search(r"(?:sum(?:a|á)|agreg(?:a|á)|dej(?:a|á))\s+una?\s*nota\s+al\s+proyecto(?:\s+(.+?))?\s*:\s*(.+)$", normalized)
    if match:
        project_name = (match.group(1) or "este proyecto").strip()
        return {
            "intent": "add_project_note",
            "project_name": project_name,
            "last_note": match.group(2).strip(),
        }

    match = re.search(r"^(?:sum(?:a|á)|agreg(?:a|á)|dej(?:a|á))\s+una?\s*nota\s+al\s+proyecto(?:\s+(.+))?$", normalized)
    if match:
        project_name = (match.group(1) or "este proyecto").strip()
        return {
            "intent": "add_project_note",
            "project_name": project_name,
            "last_note": None,
        }

    match = re.search(r"^dej(?:a|á)\s+nota\s*:\s*(.+)$", normalized)
    if match:
        return {
            "intent": "add_task_note",
            "task_name": "esta tarea",
            "last_note": match.group(1).strip(),
        }

    match = re.search(r"^(?:dejame|dejame|dej(?:a|á))\s+una?\s+proxima\s+accion\s+para\s+(.+)$", normalized)
    if match:
        return {
            "intent": "update_task_next_action",
            "task_name": "esta tarea",
            "next_action": match.group(1).strip(),
        }

    return None


def _parse_temporal_read_intents(normalized: str) -> dict | None:
    match = re.search(r"^que tengo hoy con (.+)$", normalized)
    if match:
        return {"intent": "get_due_tasks_summary", "time_scope": "today", "client_name": match.group(1).strip()}

    match = re.search(r"^que tengo para manana con (.+)$", normalized)
    if match:
        return {"intent": "get_due_tasks_summary", "time_scope": "tomorrow", "client_name": match.group(1).strip()}

    if any(phrase in normalized for phrase in ["que vence hoy", "que vence ahora"]):
        payload = {"intent": "get_due_tasks_summary", "time_scope": "today"}
        if normalized.startswith("y "):
            payload["entity_hint"] = "aca"
        return payload

    if any(phrase in normalized for phrase in ["que vence esta semana", "y que vence esta semana"]):
        payload = {"intent": "get_due_tasks_summary", "time_scope": "this_week"}
        if normalized.startswith("y "):
            payload["entity_hint"] = "aca"
        return payload

    if any(phrase in normalized for phrase in ["que vence", "y que vence"]):
        payload = {"intent": "get_due_tasks_summary", "time_scope": "due_items"}
        if normalized.startswith("y "):
            payload["entity_hint"] = "aca"
        return payload

    if any(phrase in normalized for phrase in ["que tengo para manana", "que tengo para mañana", "y para manana", "y para mañana"]):
        payload = {"intent": "get_due_tasks_summary", "time_scope": "tomorrow"}
        if normalized.startswith("y "):
            payload["entity_hint"] = "aca"
        return payload

    if any(phrase in normalized for phrase in ["que follow-ups vencen esta semana", "que followups vencen esta semana"]):
        return {"intent": "get_due_tasks_summary", "time_scope": "this_week", "temporal_focus": "followups"}

    if any(phrase in normalized for phrase in ["que tendria que cerrar esta semana", "que tendría que cerrar esta semana"]):
        return {"intent": "get_due_tasks_summary", "time_scope": "this_week", "temporal_focus": "closing"}

    if any(phrase in normalized for phrase in ["que tengo atrasado", "que esta vencido", "que está vencido", "y que esta atrasado", "y que está atrasado"]):
        payload = {"intent": "get_overdue_tasks_summary", "time_scope": "overdue"}
        if normalized.startswith("y "):
            payload["entity_hint"] = "aca"
        return payload

    if any(phrase in normalized for phrase in ["que no tiene fecha y deberia tenerla", "que no tiene fecha y debería tenerla"]):
        return {"intent": "get_missing_due_date_summary"}

    return None


def _extract_supported_due_hint(normalized: str) -> tuple[str, str | None, str | None]:
    patterns = [
        (r"\s+para\s+hoy$", "hoy", "today"),
        (r"\s+para\s+mañana$", "mañana", "tomorrow"),
        (r"\s+para\s+manana$", "manana", "tomorrow"),
        (r"\s+para\s+esta\s+semana$", "esta semana", "this_week"),
    ]
    for day_name in TEMPORAL_DAY_TERMS:
        patterns.append((rf"\s+para\s+(?:el\s+)?{day_name}$", day_name, "weekday"))

    for pattern, due_hint, time_scope in patterns:
        if re.search(pattern, normalized):
            return re.sub(pattern, "", normalized).strip(), due_hint, time_scope

    for term in AMBIGUOUS_TEMPORAL_TERMS:
        pattern = rf"\s+para\s+{term}$"
        if re.search(pattern, normalized):
            return re.sub(pattern, "", normalized).strip(), term, "ambiguous"

    return normalized, None, None


def _apply_temporal_fields(payload: dict, due_hint: str | None, time_scope: str | None) -> dict:
    if due_hint:
        payload["due_hint"] = due_hint
    if time_scope:
        payload["time_scope"] = time_scope
    return payload


def _parse_ambiguity_intents(normalized: str) -> dict | None:
    if not normalized:
        return None

    match = re.search(r"^resumime\s+lo\s+(?:del|de la|de)\s+(.+)$", normalized)
    if match:
        return {"intent": "clarify_entity_reference", "entity_hint": match.group(1).strip()}

    match = re.search(r"^lo\s+(?:del|de la|de)\s+(.+)$", normalized)
    if match:
        return {"intent": "clarify_entity_reference", "entity_hint": match.group(1).strip()}

    match = re.search(r"^que\s+pasa\s+con\s+(.+)$", normalized)
    if match:
        return {"intent": "clarify_entity_reference", "entity_hint": match.group(1).strip()}

    match = re.search(r"^quiero\s+ver\s+(.+)$", normalized)
    if match:
        return {"intent": "clarify_entity_reference", "entity_hint": match.group(1).strip()}

    match = re.search(r"^actualiza\s+(.+)$", normalized)
    if match:
        return {"intent": "clarify_entity_reference", "entity_hint": match.group(1).strip()}

    match = re.search(r"^quiero\s+avanzar\s+con\s+(.+)$", normalized)
    if match:
        return {"intent": "clarify_entity_reference", "entity_hint": match.group(1).strip()}

    words = [token for token in normalized.replace("?", "").split() if token]
    if len(words) <= 2 and normalized not in {"cerrala", "cerralo"}:
        if normalized in OPEN_ENTITY_TERMS or (len(words) == 1 and len(words[0]) >= 3):
            return {"intent": "clarify_entity_reference", "entity_hint": normalized}

    return None


def _parse_read_intents(normalized: str) -> dict | None:
    if any(
        phrase in normalized
        for phrase in [
            "que me preocuparia",
            "quÃ© me preocuparÃ­a",
        ]
    ) and " de " not in normalized:
        return {"intent": "get_followup_focus_summary", "followup_focus": "friction"}

    if any(
        phrase in normalized
        for phrase in [
            "por que esa",
            "por quÃ© esa",
            "por que eso seria lo primero",
            "por quÃ© eso serÃ­a lo primero",
        ]
    ):
        return {"intent": "get_recommendation_explanation"}

    if any(
        phrase in normalized
        for phrase in [
            "y despues de eso",
            "y despuÃ©s de eso",
        ]
    ):
        return {"intent": "get_followup_focus_summary", "followup_focus": "next_after_recommendation"}

    if any(
        phrase in normalized
        for phrase in [
            "mostrame solo lo critico",
            "mostrame solo lo crÃ­tico",
        ]
    ):
        return {"intent": "get_filtered_context_summary", "filter_mode": "critical"}

    if any(
        phrase in normalized
        for phrase in [
            "y solo lo urgente",
            "solo lo urgente",
        ]
    ):
        return {"intent": "get_filtered_context_summary", "filter_mode": "urgent"}

    if any(
        phrase in normalized
        for phrase in [
            "quiero ver solo tareas bloqueadas",
            "solo tareas bloqueadas",
        ]
    ):
        return {"intent": "get_filtered_context_summary", "filter_mode": "blocked"}

    if any(phrase in normalized for phrase in ["quiero solo riesgos", "solo riesgos"]):
        return {"intent": "get_filtered_context_summary", "filter_mode": "risks"}

    if any(
        phrase in normalized
        for phrase in [
            "quiero solo proximos pasos",
            "solo proximos pasos",
        ]
    ):
        return {"intent": "get_filtered_context_summary", "filter_mode": "next_steps"}

    if "mostrame solo lo importante" in normalized:
        return {"intent": "get_filtered_context_summary", "filter_mode": "important"}

    if any(
        phrase in normalized
        for phrase in [
            "damelo corto",
            "quiero la version resumida",
            "quiero la version corta",
        ]
    ):
        return {"intent": "get_rephrased_summary", "rephrase_style": "short"}

    if any(
        phrase in normalized
        for phrase in [
            "resumimelo en 3 lineas",
            "resumimelo en tres lineas",
            "resumimelo en 3 lÃ­neas",
        ]
    ):
        return {"intent": "get_rephrased_summary", "rephrase_style": "three_lines"}

    if any(phrase in normalized for phrase in ["damelo ejecutivo", "damelo mas ejecutivo"]):
        return {"intent": "get_rephrased_summary", "rephrase_style": "executive"}

    if "damelo tactico" in normalized:
        return {"intent": "get_rephrased_summary", "rephrase_style": "tactical"}

    if "quiero mas detalle" in normalized:
        return {"intent": "get_rephrased_summary", "rephrase_style": "detailed"}

    if any(phrase in normalized for phrase in ["dame solo bullets", "solo bullets"]):
        return {"intent": "get_rephrased_summary", "rephrase_style": "bullets"}

    if "decimelo como para reunion" in normalized:
        return {"intent": "get_rephrased_summary", "rephrase_style": "meeting_ready"}

    if any(
        phrase in normalized
        for phrase in [
            "damelo ejecutivo",
            "damelo mas ejecutivo",
            "dÃ¡melo mÃ¡s ejecutivo",
        ]
    ):
        return {"intent": "get_rephrased_summary", "rephrase_style": "executive"}

    if any(
        phrase in normalized
        for phrase in [
            "explicamelo simple",
            "explicÃ¡melo simple",
        ]
    ):
        return {"intent": "get_rephrased_summary", "rephrase_style": "simple"}

    if any(
        phrase in normalized
        for phrase in [
            "decimelo mas corto",
            "decimelo como para mi",
            "decÃ­melo mÃ¡s corto",
        ]
    ):
        if "como para mi" in normalized:
            return {"intent": "get_rephrased_summary", "rephrase_style": "personal"}
        return {"intent": "get_rephrased_summary", "rephrase_style": "short"}

    if any(
        phrase in normalized
        for phrase in [
            "que le diria al cliente hoy",
            "que le diria al cliente",
            "decimelo como para mandarselo al cliente",
            "quÃ© le dirÃ­a al cliente hoy",
        ]
    ):
        return {"intent": "get_client_facing_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que haria ahora con este cliente",
            "quÃ© harÃ­as ahora con este cliente",
            "que me recomendas hacer con este cliente",
            "quÃ© me recomendÃ¡s hacer con este cliente",
        ]
    ):
        return {"intent": "get_operational_recommendation", "client_name": "este cliente"}

    if any(
        phrase in normalized
        for phrase in [
            "que priorizarias en este proyecto",
            "quÃ© priorizarÃ­as en este proyecto",
            "que priorizarias en ese proyecto",
            "quÃ© priorizarÃ­as en ese proyecto",
        ]
    ):
        project_name = "este proyecto" if "este proyecto" in normalized else "ese proyecto"
        return {"intent": "get_operational_recommendation", "project_name": project_name}

    if any(
        phrase in normalized
        for phrase in [
            "que me recomendas hacer con ",
            "quÃ© me recomendÃ¡s hacer con ",
            "que haria ahora con ",
            "quÃ© harÃ­as ahora con ",
        ]
    ):
        match = re.search(
            r"(?:que me recomendas hacer con|quÃ© me recomendÃ¡s hacer con|que haria ahora con|quÃ© harÃ­as ahora con)\s+(.+)$",
            normalized,
        )
        if match:
            return {"intent": "get_operational_recommendation", "entity_hint": match.group(1).strip()}

    if any(
        phrase in normalized
        for phrase in [
            "que deberia priorizar aca",
            "quÃ© deberÃ­a priorizar acÃ¡",
            "que haria ahora",
            "quÃ© harÃ­as ahora",
        ]
    ):
        return {"intent": "get_operational_recommendation", "entity_hint": "aca"}

    if any(
        phrase in normalized
        for phrase in [
            "que atacaria primero",
            "quÃ© atacarÃ­a primero",
            "que haria primero",
            "qué haría primero",
            "que me conviene empujar primero",
            "quÃ© me conviene empujar primero",
            "si tuvieras que elegir una sola cosa",
            "si tuvieras que elegir una sola cosa, cual seria",
            "si tuvieras que elegir una sola cosa, cuÃ¡l serÃ­a",
        ]
    ):
        return {"intent": "get_operational_recommendation", "recommendation_focus": "general"}

    if any(
        phrase in normalized
        for phrase in [
            "que destraba mas ahora",
            "quÃ© destraba mÃ¡s ahora",
        ]
    ):
        return {"intent": "get_operational_recommendation", "recommendation_focus": "unblock"}

    if any(
        phrase in normalized
        for phrase in [
            "que conviene cerrar hoy",
            "quÃ© conviene cerrar hoy",
        ]
    ):
        return {"intent": "get_operational_recommendation", "recommendation_focus": "close"}

    if any(
        phrase in normalized
        for phrase in [
            "que viene estancado",
            "qué viene estancado",
            "que esta frenado hace mucho",
            "qué está frenado hace mucho",
            "que me preocuparia por atraso",
            "qué me preocuparía por atraso",
            "que tareas estan abiertas hace demasiado",
            "qué tareas están abiertas hace demasiado",
            "que proyecto esta acumulando friccion",
            "qué proyecto está acumulando fricción",
            "donde se nos esta trabando el trabajo",
            "dónde se nos está trabando el trabajo",
            "que esta en progreso hace demasiado",
            "qué está en progreso hace demasiado",
            "que tiene pinta de estar mal seguido",
            "que esta abierto hace mucho sin avances",
            "qué está abierto hace mucho sin avances",
            "y que esta frenado",
            "y qué está frenado",
        ]
    ):
        if "proyecto" in normalized:
            return {"intent": "get_operational_friction_summary", "project_name": "este proyecto"} if "este proyecto" in normalized else {"intent": "get_operational_friction_summary"}
        if "y que esta frenado" in normalized or "y qué está frenado" in normalized:
            return {"intent": "get_operational_friction_summary", "entity_hint": "aca"}
        return {"intent": "get_operational_friction_summary"}

    if any(
        phrase in normalized
        for phrase in [
            "que me preocuparia de este cliente",
            "qué me preocuparía de este cliente",
            "que viene mal aca",
            "qué viene mal acá",
        ]
    ):
        if "cliente" in normalized:
            return {"intent": "get_operational_friction_summary", "client_name": "este cliente"}
        return {"intent": "get_operational_friction_summary", "entity_hint": "aca"}

    if any(
        phrase in normalized
        for phrase in [
            "que me preocuparia de ",
            "qué me preocuparía de ",
        ]
    ):
        match = re.search(r"(?:que me preocuparia de|qué me preocuparía de)\s+(.+)$", normalized)
        if match:
            return {"intent": "get_operational_friction_summary", "entity_hint": match.group(1).strip()}

    if any(
        phrase in normalized
        for phrase in [
            "comentame ",
            "comentáme ",
            "comentame en que andamos con ",
            "comentame en qué andamos con ",
            "dame un resumen operativo de ",
            "que me preocuparia de ",
            "que me preocuparía de ",
            "que esta pasando con ",
            "qué está pasando con ",
            "como estamos con ",
            "cómo estamos con ",
        ]
    ):
        match = re.search(
            r"(?:comentame en que andamos con|comentame en qué andamos con|comentame|comentáme|dame un resumen operativo de|que me preocuparia de|que me preocuparía de|que esta pasando con|qué está pasando con|como estamos con|cómo estamos con)\s+(.+)$",
            normalized,
        )
        if match:
            return {"intent": "get_operational_summary", "entity_hint": match.group(1).strip()}

    if any(
        phrase in normalized
        for phrase in [
            "como viene ",
            "cómo viene ",
        ]
    ):
        match = re.search(r"(?:como viene|cómo viene)\s+(.+)$", normalized)
        if match:
            target = match.group(1).strip()
            if target in {"esto", "aca", "acá"}:
                return {"intent": "get_operational_summary", "entity_hint": target}
            return {"intent": "get_operational_summary", "entity_hint": target}

    if any(
        phrase in normalized
        for phrase in [
            "resumime lo importante de este proyecto",
            "resumime lo importante de ese proyecto",
        ]
    ):
        project_name = "este proyecto" if "este proyecto" in normalized else "ese proyecto"
        return {"intent": "get_operational_summary", "project_name": project_name}

    if any(
        phrase in normalized
        for phrase in [
            "que es lo mas importante aca",
            "qué es lo más importante acá",
            "que es lo mas importante de esta tarea",
            "qué es lo más importante de esta tarea",
            "y como estamos",
            "y cómo estamos",
            "como viene esto",
            "cómo viene esto",
        ]
    ):
        if "esta tarea" in normalized:
            return {"intent": "get_operational_summary", "task_name": "esta tarea"}
        return {"intent": "get_operational_summary", "entity_hint": "aca"}

    if any(
        phrase in normalized
        for phrase in [
            "que me preocuparia de este cliente",
            "qué me preocuparía de este cliente",
            "que esta pasando con este proyecto",
            "qué está pasando con este proyecto",
            "que esta pasando con este cliente",
            "qué está pasando con este cliente",
        ]
    ):
        if "proyecto" in normalized:
            return {"intent": "get_operational_summary", "project_name": "este proyecto"}
        return {"intent": "get_operational_summary", "client_name": "este cliente"}

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
            "que tengo urgente",
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
        if target and " y " not in target and not target.startswith(("el cliente ", "la tarea ", "el proyecto ", "lo ")) and len(target.split()) <= 2:
            return {"intent": "get_operational_summary", "entity_hint": target}
        if target and not target.startswith(("el cliente ", "la tarea ", "el proyecto ", "lo ")):
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

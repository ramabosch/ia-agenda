from app.services.client_service import get_active_clients
from app.services.conversation_service import (
    get_conversations_for_today,
    get_last_conversation,
)
from app.services.project_service import get_project_operational_summary, get_projects_by_client_id
from app.services.reference_resolver import resolve_references
from app.services.task_service import (
    add_task_note_conversational,
    get_open_tasks_by_client_id,
    get_task_operational_summary,
    get_tasks_by_client_id,
    get_tasks_by_project_id,
    update_task_next_action_conversational,
    update_task_priority_conversational,
    update_task_status_conversational,
)
from app.services.task_update_service import create_task_update


REFERENCE_AWARE_INTENTS = {
    "get_open_tasks_by_client_name",
    "get_projects_by_client_name",
    "get_tasks_by_client_name",
    "get_tasks_by_project_name",
    "get_tasks_by_project_and_client",
    "get_task_summary",
    "get_project_summary",
    "complete_task_by_name",
    "update_task_priority_by_name",
    "add_task_update_by_name",
    "update_task_status",
    "update_task_priority",
    "add_task_note",
    "update_task_next_action",
    "update_task_last_note",
}

TASK_UPDATE_INTENTS = {
    "update_task_status",
    "update_task_priority",
    "add_task_note",
    "update_task_next_action",
    "update_task_last_note",
    "complete_task_by_name",
    "update_task_priority_by_name",
}


def build_response_from_query(parsed_query: dict, user_query: str | None = None) -> str:
    intent = parsed_query.get("intent")
    resolved_references = _resolve_if_needed(parsed_query, user_query)

    if intent == "get_active_clients":
        clients = get_active_clients()
        if not clients:
            return "No encontré clientes activos en la agenda."

        lines = ["Tus clientes activos actuales son:"]
        for client in clients:
            lines.append(f"- {client.name}")
        return "\n".join(lines)

    if intent == "get_open_tasks_by_client_name":
        client_message = _require_resolved_entity(
            resolved_references,
            "client",
            "cliente",
            action_text="mirar pendientes",
        )
        if client_message:
            return client_message

        client = resolved_references["client"]["resolved"]
        tasks = get_open_tasks_by_client_id(client["id"])
        if not tasks:
            return f"No encontré tareas abiertas para {client['name']}."

        if _is_next_step_query(user_query):
            lines = [f"Esto es lo que sigue con {client['name']}:"]
            for task in tasks:
                project_name = task.project.name if task.project else "Desconocido"
                lines.append(
                    f"- {task.title} | Proyecto: {project_name} | Próximo paso: {task.next_action or 'Sin próxima acción'} | Última nota: {task.last_note or 'Sin nota'}"
                )
            return "\n".join(lines)

        lines = [f"Estas son las tareas abiertas de {client['name']}:"]
        for task in tasks:
            project_name = task.project.name if task.project else "Desconocido"
            lines.append(
                f"- {task.title} | Estado: {task.status} | Prioridad: {task.priority} | Proyecto: {project_name}"
            )
        return "\n".join(lines)

    if intent == "get_task_summary":
        task_id = parsed_query.get("task_id")
        if task_id:
            summary = get_task_operational_summary(task_id)
            if not summary:
                return f"No encontré una tarea con ID {task_id}."
            return _format_task_summary(summary)

        task_message = _require_resolved_entity(
            resolved_references,
            "task",
            "tarea",
            action_text="resumir",
        )
        if task_message:
            return task_message

        summary = get_task_operational_summary(resolved_references["task"]["resolved"]["id"])
        if not summary:
            return "Encontré la tarea, pero no pude cargar su resumen operativo."
        return _format_task_summary(summary)

    if intent == "get_project_summary":
        project_id = parsed_query.get("project_id")
        if project_id:
            summary = get_project_operational_summary(project_id)
            if not summary:
                return f"No encontré un proyecto con ID {project_id}."
            return _format_project_summary(summary)

        project_message = _require_resolved_entity(
            resolved_references,
            "project",
            "proyecto",
            action_text="resumir",
        )
        if project_message:
            task_fallback = resolved_references.get("task", {}).get("resolved")
            if task_fallback and not resolved_references["task"]["ambiguous"]:
                task_summary = get_task_operational_summary(task_fallback["id"])
                if task_summary:
                    return (
                        "No encontré un proyecto con ese nombre, pero sí encontré una tarea muy parecida.\n\n"
                        + _format_task_summary(task_summary)
                    )
            return project_message

        summary = get_project_operational_summary(resolved_references["project"]["resolved"]["id"])
        if not summary:
            return "Encontré el proyecto, pero no pude cargar su resumen operativo."
        return _format_project_summary(summary)

    if intent == "get_projects_by_client_name":
        client_message = _require_resolved_entity(
            resolved_references,
            "client",
            "cliente",
            action_text="listar proyectos",
        )
        if client_message:
            return client_message

        client = resolved_references["client"]["resolved"]
        projects = get_projects_for_client(client["id"])
        if not projects:
            return f"{client['name']} no tiene proyectos cargados."

        lines = [f"Proyectos de {client['name']}:"]
        for project_summary in projects:
            lines.append(
                f"- {project_summary['project_name']} | Estado: {project_summary['status']} | Abiertas: {project_summary['open_tasks']}/{project_summary['total_tasks']}"
            )
        return "\n".join(lines)

    if intent == "get_tasks_by_client_name":
        client_message = _require_resolved_entity(
            resolved_references,
            "client",
            "cliente",
            action_text="listar tareas",
        )
        if client_message:
            return client_message

        client = resolved_references["client"]["resolved"]
        tasks = get_tasks_by_client_id(client["id"])
        if not tasks:
            return f"{client['name']} no tiene tareas cargadas."

        lines = [f"Tareas de {client['name']}:"]
        for task in tasks:
            project_name = task.project.name if task.project else "Sin proyecto"
            lines.append(f"- {task.title} | {task.status} | {project_name}")
        return "\n".join(lines)

    if intent == "get_tasks_by_project_and_client":
        client_message = _require_resolved_entity(
            resolved_references,
            "client",
            "cliente",
            action_text="ubicar el proyecto",
        )
        if client_message:
            return client_message

        project_message = _require_resolved_entity(
            resolved_references,
            "project",
            "proyecto",
            action_text="listar tareas",
        )
        if project_message:
            return project_message

        project = resolved_references["project"]["resolved"]
        client = resolved_references["client"]["resolved"]
        tasks = get_tasks_by_project_id(project["id"])
        if not tasks:
            return f"El proyecto {project['name']} no tiene tareas."

        lines = [f"Tareas del proyecto {project['name']} ({client['name']}):"]
        for task in tasks:
            lines.append(f"- {task.title} | {task.status} | prioridad {task.priority}")
        return "\n".join(lines)

    if intent == "get_tasks_by_project_name":
        project_message = _require_resolved_entity(
            resolved_references,
            "project",
            "proyecto",
            action_text="listar tareas",
        )
        if project_message:
            return project_message

        project = resolved_references["project"]["resolved"]
        tasks = get_tasks_by_project_id(project["id"])
        if not tasks:
            return f"El proyecto {project['name']} no tiene tareas."

        lines = [f"Tareas del proyecto {project['name']}:"]
        for task in tasks:
            lines.append(f"- {task.title} | {task.status} | prioridad {task.priority}")
        return "\n".join(lines)

    if intent in TASK_UPDATE_INTENTS:
        return _handle_task_update_intent(parsed_query, resolved_references)

    if intent == "add_task_update":
        task_id = parsed_query.get("task_id")
        content = parsed_query.get("content")
        if not content:
            return "No encontré contenido para agregar como update."

        task_update = create_task_update(
            task_id=task_id,
            content=content,
            update_type="manual",
            source="asistente",
        )
        if not task_update:
            return f"No pude agregar el update a la tarea {task_id}."
        return f"Listo. Registré un nuevo update en la tarea {task_id}."

    if intent == "add_task_update_by_name":
        task_message = _require_resolved_entity(
            resolved_references,
            "task",
            "tarea",
            action_text="agregar el update",
        )
        if task_message:
            return task_message

        content = parsed_query.get("content")
        if not content:
            return "No encontré el contenido del update."

        task = resolved_references["task"]["resolved"]
        create_task_update(
            task_id=task["id"],
            content=content,
            update_type="manual",
            source="asistente",
        )
        parsed_query["_update_type"] = "task_update"
        parsed_query["_update_real"] = True
        parsed_query["_update_result"] = {
            "task_id": task["id"],
            "task_title": task["name"],
            "field": "task_update",
            "new_value": content,
        }
        return f"Listo. Agregué un update a la tarea '{task['name']}'."

    if intent == "get_today_activity":
        logs = get_conversations_for_today()
        if not logs:
            return "Hoy todavía no registré actividad en el asistente."

        lines = ["Hoy trabajaste con estas consultas en el asistente:"]
        for log in logs[:10]:
            lines.append(f"- {log.user_input}")
        return "\n".join(lines)

    if intent == "get_today_queries":
        logs = get_conversations_for_today()
        if not logs:
            return "Hoy todavía no hiciste consultas en el asistente."

        lines = ["Estas fueron tus consultas de hoy:"]
        for log in logs[:10]:
            lines.append(f"- {log.user_input}")
        return "\n".join(lines)

    if intent == "get_today_changes":
        logs = get_conversations_for_today()
        if not logs:
            return "Hoy no encontré cambios registrados desde el asistente."

        change_keywords = [
            "update_task_status",
            "add_task_update",
            "add_task_update_by_name",
            "add_task_note",
            "update_task_next_action",
            "update_task_last_note",
            "update_task_priority",
            "update_task_priority_by_name",
            "complete_task_by_name",
        ]
        change_logs = [
            log for log in logs if log.parsed_intent and any(keyword in log.parsed_intent for keyword in change_keywords)
        ]
        if not change_logs:
            return "Hoy no encontré cambios operativos hechos desde el asistente."

        lines = ["Hoy registraste estos cambios desde el asistente:"]
        for log in change_logs[:10]:
            lines.append(f"- {log.user_input}")
        return "\n".join(lines)

    if intent == "get_last_interaction":
        log = get_last_conversation()
        if not log:
            return "Todavía no hay interacciones guardadas en el asistente."

        return "\n".join(
            [
                "Tu última interacción con el asistente fue:",
                f"Consulta: {log.user_input}",
                f"Interpretación: {log.parsed_intent}",
                f"Respuesta: {log.response_output}",
            ]
        )

    return (
        "No entendí esa consulta todavía.\n\n"
        "Probá con ejemplos como:\n"
        "- decime los clientes activos\n"
        "- qué tengo pendiente con CAM\n"
        "- resumime el proyecto CRM\n"
        "- cómo va onboarding\n"
        "- marcá onboarding como en progreso"
    )


def get_projects_for_client(client_id: int) -> list[dict]:
    project_summaries = []
    for project in get_projects_by_client_id(client_id):
        summary = get_project_operational_summary(project.id)
        if summary:
            project_summaries.append(summary)
    return project_summaries


def _handle_task_update_intent(parsed_query: dict, resolved_references: dict) -> str:
    task_message = _require_resolved_entity(
        resolved_references,
        "task",
        "tarea",
        action_text="actualizar",
    )
    if task_message:
        parsed_query["_update_real"] = False
        parsed_query["_update_result"] = {"error": "resolution_failed"}
        return task_message

    task = resolved_references["task"]["resolved"]
    intent = parsed_query.get("intent")

    if intent in {"update_task_status", "complete_task_by_name"}:
        new_status = parsed_query.get("new_status") or "hecha"
        result = update_task_status_conversational(
            task["id"],
            new_status=new_status,
            reason=parsed_query.get("last_note"),
        )
        return _finalize_update_response(parsed_query, "status", result)

    if intent in {"update_task_priority", "update_task_priority_by_name"}:
        result = update_task_priority_conversational(
            task["id"],
            new_priority=parsed_query.get("new_priority"),
            priority_direction=parsed_query.get("priority_direction"),
        )
        return _finalize_update_response(parsed_query, "priority", result)

    if intent in {"add_task_note", "update_task_last_note"}:
        result = add_task_note_conversational(
            task["id"],
            note_content=parsed_query.get("last_note"),
        )
        return _finalize_update_response(parsed_query, "last_note", result)

    if intent == "update_task_next_action":
        result = update_task_next_action_conversational(
            task["id"],
            next_action=parsed_query.get("next_action"),
        )
        return _finalize_update_response(parsed_query, "next_action", result)

    parsed_query["_update_real"] = False
    parsed_query["_update_result"] = {"error": "unsupported_intent"}
    return "Todavía no sé cómo ejecutar esa actualización."


def _finalize_update_response(parsed_query: dict, update_type: str, result: dict) -> str:
    parsed_query["_update_type"] = update_type
    parsed_query["_update_real"] = bool(result.get("updated"))
    parsed_query["_update_result"] = result

    if not result.get("updated"):
        if result.get("error") == "not_found":
            return "No encontré la tarea que querés actualizar."
        if result.get("error") == "invalid_priority":
            return "No pude interpretar la prioridad nueva para esa tarea."
        if result.get("error") == "no_change":
            return (
                f"No hice cambios en '{result.get('task_title', 'la tarea')}'. "
                f"El valor ya era '{result.get('new_value')}'."
            )
        return "No pude aplicar la actualización solicitada."

    field_labels = {
        "status": "estado",
        "priority": "prioridad",
        "last_note": "última nota",
        "next_action": "próxima acción",
    }
    field_label = field_labels.get(result["field"], result["field"])
    old_value = result.get("old_value") or "vacío"
    new_value = result.get("new_value") or "vacío"

    if result["field"] == "status" and old_value == new_value and result.get("reason"):
        return (
            f"Listo. La tarea '{result['task_title']}' sigue en estado '{new_value}', "
            f"y además registré la nota '{result['reason']}'."
        )

    return (
        f"Listo. Actualicé la tarea '{result['task_title']}'. "
        f"Cambió {field_label}: '{old_value}' -> '{new_value}'."
    )


def _resolve_if_needed(parsed_query: dict, user_query: str | None) -> dict:
    intent = parsed_query.get("intent")
    if intent not in REFERENCE_AWARE_INTENTS:
        resolved = {"scope": "none", "confidence": 0.0, "ambiguous": False}
        parsed_query["_resolved_references"] = resolved
        return resolved

    resolved = resolve_references(parsed_query, user_query=user_query)
    parsed_query["_resolved_references"] = resolved
    parsed_query["_resolver_scope"] = resolved.get("scope")
    parsed_query["_resolver_confidence"] = resolved.get("confidence")
    parsed_query["_resolver_ambiguous"] = resolved.get("ambiguous")
    return resolved


def _require_resolved_entity(
    resolved_references: dict,
    scope: str,
    label: str,
    *,
    action_text: str,
) -> str | None:
    result = resolved_references.get(scope) or {}
    resolved = result.get("resolved")

    if result.get("ambiguous"):
        return _format_ambiguity_message(
            f"Encontré varios {label}s posibles para {action_text}.",
            result.get("matches", []),
        )

    if resolved is not None:
        return None

    if result.get("input"):
        normalized = result.get("normalized") or result["input"]
        if result.get("matches"):
            candidates = ", ".join(match["name"] for match in result["matches"][:3])
            return (
                f"No pude resolver con suficiente confianza el {label} '{normalized}'. "
                f"Los candidatos más cercanos son: {candidates}."
            )
        return f"No encontré un {label} que coincida con '{normalized}'."

    if scope in resolved_references.get("context", {}):
        return f"Tenía contexto previo para ese {label}, pero no pude reutilizarlo con confianza."

    return f"No pude identificar a qué {label} te referís."


def _format_ambiguity_message(prefix: str, matches: list[dict]) -> str:
    lines = [prefix, "Podría ser:"]
    for item in matches[:5]:
        lines.append(f"- {item['name']}")
    return "\n".join(lines)


def _format_date(value):
    if not value:
        return "Sin fecha"
    return str(value)


def _format_task_summary(summary: dict) -> str:
    return "\n".join(
        [
            f"Resumen de la tarea {summary['task_id']}:",
            f"Título: {summary['title']}",
            f"Cliente: {summary['client_name']}",
            f"Proyecto: {summary['project_name']}",
            f"Estado actual: {summary['status']}",
            f"Prioridad: {summary['priority']}",
            f"Vence: {_format_date(summary['due_date'])}",
            f"Última nota: {summary['last_note'] or 'Sin nota registrada'}",
            f"Próxima acción: {summary['next_action'] or 'Sin próxima acción definida'}",
            f"Updates registrados: {summary['updates_count']}",
            f"Último update: {summary['latest_update'] or 'No hay updates todavía'}",
        ]
    )


def _format_project_summary(summary: dict) -> str:
    return "\n".join(
        [
            f"Resumen del proyecto {summary['project_name']}:",
            f"Cliente: {summary['client_name']}",
            f"Estado: {summary['status']}",
            f"Descripción: {summary['description'] or 'Sin descripción'}",
            f"Tareas totales: {summary['total_tasks']}",
            f"Tareas abiertas: {summary['open_tasks']}",
            f"En progreso: {summary['in_progress_tasks']}",
            f"Bloqueadas: {summary['blocked_tasks']}",
            f"Hechas: {summary['done_tasks']}",
        ]
    )


def _is_next_step_query(user_query: str | None) -> bool:
    if not user_query:
        return False

    normalized = user_query.strip().lower()
    return "que sigue" in normalized or "qué sigue" in normalized

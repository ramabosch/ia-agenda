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
    get_tasks_by_status,
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
    "get_client_summary",
    "get_tasks_by_status",
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


def build_response_from_query(
    parsed_query: dict,
    user_query: str | None = None,
    conversation_context: dict | None = None,
) -> str:
    intent = parsed_query.get("intent")
    resolved_references = _resolve_if_needed(parsed_query, user_query, conversation_context=conversation_context)

    if intent == "get_active_clients":
        clients = get_active_clients()
        parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
        if not clients:
            return "No encontre clientes activos en la agenda."

        lines = ["Tus clientes activos actuales son:"]
        for client in clients:
            lines.append(f"- {client.name}")
        return "\n".join(lines)

    if intent == "get_client_summary":
        client_message = _require_resolved_entity(resolved_references, "client", "cliente", action_text="resumir")
        if client_message:
            return _abort_with_context(parsed_query, client_message)

        client = resolved_references["client"]["resolved"]
        projects = get_projects_by_client_id(client["id"])
        tasks = get_tasks_by_client_id(client["id"])
        open_tasks = [task for task in tasks if task.status != "hecha"]
        blocked_tasks = [task for task in tasks if task.status == "bloqueada"]

        _remember_context(parsed_query, resolved_references, focus_scope="client", projects=projects)
        return "\n".join(
            [
                f"Resumen del cliente {client['name']}:",
                f"Proyectos: {len(projects)}",
                f"Tareas totales: {len(tasks)}",
                f"Tareas abiertas: {len(open_tasks)}",
                f"Tareas bloqueadas: {len(blocked_tasks)}",
            ]
        )

    if intent == "get_open_tasks_by_client_name":
        client_message = _require_resolved_entity(resolved_references, "client", "cliente", action_text="mirar pendientes")
        if client_message:
            return _abort_with_context(parsed_query, client_message)

        client = resolved_references["client"]["resolved"]
        tasks = get_open_tasks_by_client_id(client["id"])
        if not tasks:
            _remember_context(parsed_query, resolved_references, focus_scope="client")
            return f"No encontre tareas abiertas para {client['name']}."

        _remember_context(parsed_query, resolved_references, focus_scope="client", tasks=tasks)
        if _is_next_step_query(user_query):
            lines = [f"Esto es lo que sigue con {client['name']}:"]
            for task in tasks:
                project_name = task.project.name if task.project else "Desconocido"
                lines.append(
                    f"- {task.title} | Proyecto: {project_name} | Proximo paso: {task.next_action or 'Sin proxima accion'} | Ultima nota: {task.last_note or 'Sin nota'}"
                )
            return "\n".join(lines)

        lines = [f"Estas son las tareas abiertas de {client['name']}:"]
        for task in tasks:
            project_name = task.project.name if task.project else "Desconocido"
            lines.append(f"- {task.title} | Estado: {task.status} | Prioridad: {task.priority} | Proyecto: {project_name}")
        return "\n".join(lines)

    if intent == "get_tasks_by_status":
        status_filter = parsed_query.get("new_status")
        tasks = get_tasks_by_status(status_filter)
        if not tasks:
            parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
            return f"No encontre tareas en estado '{status_filter}'."

        if len(tasks) == 1:
            summary = get_task_operational_summary(tasks[0].id)
            _remember_context(parsed_query, resolved_references, focus_scope="task", tasks=tasks)
            return _format_task_summary(summary)

        parsed_query["_conversation_context"] = {
            **_base_conversation_context(parsed_query, "none"),
            "task_status_filter": status_filter,
        }
        lines = [f"Encontre {len(tasks)} tareas en estado '{status_filter}':"]
        for task in tasks[:10]:
            project_name = task.project.name if task.project else "Sin proyecto"
            lines.append(f"- {task.title} | Proyecto: {project_name}")
        return "\n".join(lines)

    if intent == "get_task_summary":
        task_id = parsed_query.get("task_id")
        if task_id:
            summary = get_task_operational_summary(task_id)
            if not summary:
                return _abort_with_context(parsed_query, f"No encontre una tarea con ID {task_id}.")
            _remember_context_from_summary(parsed_query, summary, "task")
            return _format_task_summary(summary)

        task_message = _require_resolved_entity(resolved_references, "task", "tarea", action_text="resumir")
        if task_message:
            return _abort_with_context(parsed_query, task_message)

        summary = get_task_operational_summary(resolved_references["task"]["resolved"]["id"])
        if not summary:
            return _abort_with_context(parsed_query, "Encontre la tarea, pero no pude cargar su resumen operativo.")
        _remember_context_from_summary(parsed_query, summary, "task")
        return _format_task_summary(summary)

    if intent == "get_project_summary":
        project_id = parsed_query.get("project_id")
        if project_id:
            summary = get_project_operational_summary(project_id)
            if not summary:
                return _abort_with_context(parsed_query, f"No encontre un proyecto con ID {project_id}.")
            _remember_context_from_project_summary(parsed_query, summary)
            return _format_project_summary(summary)

        project_message = _require_resolved_entity(resolved_references, "project", "proyecto", action_text="resumir")
        if project_message:
            task_fallback = resolved_references.get("task", {}).get("resolved")
            if task_fallback and not resolved_references["task"]["ambiguous"]:
                task_summary = get_task_operational_summary(task_fallback["id"])
                if task_summary:
                    _remember_context_from_summary(parsed_query, task_summary, "task")
                    return "No encontre un proyecto con ese nombre, pero si encontre una tarea muy parecida.\n\n" + _format_task_summary(task_summary)
            return _abort_with_context(parsed_query, project_message)

        summary = get_project_operational_summary(resolved_references["project"]["resolved"]["id"])
        if not summary:
            return _abort_with_context(parsed_query, "Encontre el proyecto, pero no pude cargar su resumen operativo.")
        _remember_context_from_project_summary(parsed_query, summary)
        return _format_project_summary(summary)

    if intent == "get_projects_by_client_name":
        client_message = _require_resolved_entity(resolved_references, "client", "cliente", action_text="listar proyectos")
        if client_message:
            return _abort_with_context(parsed_query, client_message)

        client = resolved_references["client"]["resolved"]
        projects = get_projects_for_client(client["id"])
        if not projects:
            _remember_context(parsed_query, resolved_references, focus_scope="client")
            return f"{client['name']} no tiene proyectos cargados."

        _remember_context(parsed_query, resolved_references, focus_scope="client", project_summaries=projects)
        lines = [f"Proyectos de {client['name']}:"]
        for project_summary in projects:
            lines.append(
                f"- {project_summary['project_name']} | Estado: {project_summary['status']} | Abiertas: {project_summary['open_tasks']}/{project_summary['total_tasks']}"
            )
        return "\n".join(lines)

    if intent == "get_tasks_by_client_name":
        client_message = _require_resolved_entity(resolved_references, "client", "cliente", action_text="listar tareas")
        if client_message:
            return _abort_with_context(parsed_query, client_message)

        client = resolved_references["client"]["resolved"]
        tasks = get_tasks_by_client_id(client["id"])
        if not tasks:
            _remember_context(parsed_query, resolved_references, focus_scope="client")
            return f"{client['name']} no tiene tareas cargadas."

        _remember_context(parsed_query, resolved_references, focus_scope="client", tasks=tasks)
        lines = [f"Tareas de {client['name']}:"]
        for task in tasks:
            project_name = task.project.name if task.project else "Sin proyecto"
            lines.append(f"- {task.title} | {task.status} | {project_name}")
        return "\n".join(lines)

    if intent == "get_tasks_by_project_and_client":
        client_message = _require_resolved_entity(resolved_references, "client", "cliente", action_text="ubicar el proyecto")
        if client_message:
            return _abort_with_context(parsed_query, client_message)

        project_message = _require_resolved_entity(resolved_references, "project", "proyecto", action_text="listar tareas")
        if project_message:
            return _abort_with_context(parsed_query, project_message)

        project = resolved_references["project"]["resolved"]
        client = resolved_references["client"]["resolved"]
        tasks = get_tasks_by_project_id(project["id"])
        if not tasks:
            _remember_context(parsed_query, resolved_references, focus_scope="project")
            return f"El proyecto {project['name']} no tiene tareas."

        _remember_context(parsed_query, resolved_references, focus_scope="project", tasks=tasks)
        lines = [f"Tareas del proyecto {project['name']} ({client['name']}):"]
        for task in tasks:
            lines.append(f"- {task.title} | {task.status} | prioridad {task.priority}")
        return "\n".join(lines)

    if intent == "get_tasks_by_project_name":
        project_message = _require_resolved_entity(resolved_references, "project", "proyecto", action_text="listar tareas")
        if project_message:
            return _abort_with_context(parsed_query, project_message)

        project = resolved_references["project"]["resolved"]
        tasks = get_tasks_by_project_id(project["id"])
        if not tasks:
            _remember_context(parsed_query, resolved_references, focus_scope="project")
            return f"El proyecto {project['name']} no tiene tareas."

        _remember_context(parsed_query, resolved_references, focus_scope="project", tasks=tasks)
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
            return _abort_with_context(parsed_query, "No encontre contenido para agregar como update.")

        task_update = create_task_update(task_id=task_id, content=content, update_type="manual", source="asistente")
        if not task_update:
            return _abort_with_context(parsed_query, f"No pude agregar el update a la tarea {task_id}.")
        parsed_query["_update_type"] = "task_update"
        parsed_query["_update_real"] = True
        parsed_query["_update_result"] = {"task_id": task_id, "new_value": content}
        return f"Listo. Registre un nuevo update en la tarea {task_id}."

    if intent == "add_task_update_by_name":
        task_message = _require_resolved_entity(resolved_references, "task", "tarea", action_text="agregar el update")
        if task_message:
            return _abort_with_context(parsed_query, task_message)

        content = parsed_query.get("content")
        if not content:
            return _abort_with_context(parsed_query, "No encontre el contenido del update.")

        task = resolved_references["task"]["resolved"]
        create_task_update(task_id=task["id"], content=content, update_type="manual", source="asistente")
        parsed_query["_update_type"] = "task_update"
        parsed_query["_update_real"] = True
        parsed_query["_update_result"] = {"task_id": task["id"], "task_title": task["name"], "field": "task_update", "new_value": content}
        _remember_context(parsed_query, resolved_references, focus_scope="task")
        return f"Listo. Agregue un update a la tarea '{task['name']}'."

    if intent == "get_today_activity":
        logs = get_conversations_for_today()
        parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
        if not logs:
            return "Hoy todavia no registre actividad en el asistente."

        lines = ["Hoy trabajaste con estas consultas en el asistente:"]
        for log in logs[:10]:
            lines.append(f"- {log.user_input}")
        return "\n".join(lines)

    if intent == "get_today_queries":
        logs = get_conversations_for_today()
        parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
        if not logs:
            return "Hoy todavia no hiciste consultas en el asistente."

        lines = ["Estas fueron tus consultas de hoy:"]
        for log in logs[:10]:
            lines.append(f"- {log.user_input}")
        return "\n".join(lines)

    if intent == "get_today_changes":
        logs = get_conversations_for_today()
        parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
        if not logs:
            return "Hoy no encontre cambios registrados desde el asistente."

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
        change_logs = [log for log in logs if log.parsed_intent and any(keyword in log.parsed_intent for keyword in change_keywords)]
        if not change_logs:
            return "Hoy no encontre cambios operativos hechos desde el asistente."

        lines = ["Hoy registraste estos cambios desde el asistente:"]
        for log in change_logs[:10]:
            lines.append(f"- {log.user_input}")
        return "\n".join(lines)

    if intent == "get_last_interaction":
        log = get_last_conversation()
        parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
        if not log:
            return "Todavia no hay interacciones guardadas en el asistente."

        return "\n".join(
            [
                "Tu ultima interaccion con el asistente fue:",
                f"Consulta: {log.user_input}",
                f"Interpretacion: {log.parsed_intent}",
                f"Respuesta: {log.response_output}",
            ]
        )

    parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
    return (
        "No entendi esa consulta todavia.\n\n"
        "Proba con ejemplos como:\n"
        "- que tengo pendiente con CAM\n"
        "- y en ese proyecto?\n"
        "- resumime onboarding\n"
        "- ponelo en alta"
    )


def get_projects_for_client(client_id: int) -> list[dict]:
    project_summaries = []
    for project in get_projects_by_client_id(client_id):
        summary = get_project_operational_summary(project.id)
        if summary:
            project_summaries.append(summary)
    return project_summaries


def _handle_task_update_intent(parsed_query: dict, resolved_references: dict) -> str:
    task_message = _require_resolved_entity(resolved_references, "task", "tarea", action_text="actualizar")
    if task_message:
        parsed_query["_update_real"] = False
        parsed_query["_update_result"] = {"error": "resolution_failed"}
        return _abort_with_context(parsed_query, task_message)

    task = resolved_references["task"]["resolved"]
    intent = parsed_query.get("intent")

    if intent in {"update_task_status", "complete_task_by_name"}:
        result = update_task_status_conversational(task["id"], new_status=parsed_query.get("new_status") or "hecha", reason=parsed_query.get("last_note"))
        return _finalize_update_response(parsed_query, resolved_references, "status", result)

    if intent in {"update_task_priority", "update_task_priority_by_name"}:
        result = update_task_priority_conversational(task["id"], new_priority=parsed_query.get("new_priority"), priority_direction=parsed_query.get("priority_direction"))
        return _finalize_update_response(parsed_query, resolved_references, "priority", result)

    if intent in {"add_task_note", "update_task_last_note"}:
        result = add_task_note_conversational(task["id"], note_content=parsed_query.get("last_note"))
        return _finalize_update_response(parsed_query, resolved_references, "last_note", result)

    if intent == "update_task_next_action":
        result = update_task_next_action_conversational(task["id"], next_action=parsed_query.get("next_action"))
        return _finalize_update_response(parsed_query, resolved_references, "next_action", result)

    parsed_query["_update_real"] = False
    parsed_query["_update_result"] = {"error": "unsupported_intent"}
    return _abort_with_context(parsed_query, "Todavia no se como ejecutar esa actualizacion.")


def _finalize_update_response(parsed_query: dict, resolved_references: dict, update_type: str, result: dict) -> str:
    parsed_query["_update_type"] = update_type
    parsed_query["_update_real"] = bool(result.get("updated"))
    parsed_query["_update_result"] = result

    if result.get("updated"):
        _remember_context(parsed_query, resolved_references, focus_scope="task")
    else:
        parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, resolved_references.get("scope", "none"))

    if not result.get("updated"):
        if result.get("error") == "not_found":
            return "No encontre la tarea que queres actualizar."
        if result.get("error") == "invalid_priority":
            return "No pude interpretar la prioridad nueva para esa tarea."
        if result.get("error") == "no_change":
            return f"No hice cambios en '{result.get('task_title', 'la tarea')}'. El valor ya era '{result.get('new_value')}'."
        return "No pude aplicar la actualizacion solicitada."

    field_labels = {
        "status": "estado",
        "priority": "prioridad",
        "last_note": "ultima nota",
        "next_action": "proxima accion",
    }
    old_value = result.get("old_value") or "vacio"
    new_value = result.get("new_value") or "vacio"

    if result["field"] == "status" and old_value == new_value and result.get("reason"):
        return f"Listo. La tarea '{result['task_title']}' sigue en estado '{new_value}', y ademas registre la nota '{result['reason']}'."

    return f"Listo. Actualice la tarea '{result['task_title']}'. Cambio {field_labels.get(result['field'], result['field'])}: '{old_value}' -> '{new_value}'."


def _resolve_if_needed(parsed_query: dict, user_query: str | None, conversation_context: dict | None = None) -> dict:
    intent = parsed_query.get("intent")
    if intent not in REFERENCE_AWARE_INTENTS:
        resolved = {"scope": "none", "confidence": 0.0, "ambiguous": False, "source": "none"}
        parsed_query["_resolved_references"] = resolved
        return resolved

    resolved = resolve_references(
        parsed_query,
        user_query=user_query,
        conversation_context=conversation_context,
        allow_global_context=False,
    )
    parsed_query["_resolved_references"] = resolved
    parsed_query["_resolver_scope"] = resolved.get("scope")
    parsed_query["_resolver_source"] = resolved.get("source")
    parsed_query["_resolver_confidence"] = resolved.get("confidence")
    parsed_query["_resolver_ambiguous"] = resolved.get("ambiguous")
    parsed_query["_recent_context_used"] = resolved.get("context", {})
    parsed_query["_context_source"] = resolved.get("context_source", "none")
    parsed_query["_context_isolated"] = resolved.get("context_isolated", False)
    parsed_query["_security_blocked"] = resolved.get("security_blocked", False)
    parsed_query["_security_reason"] = resolved.get("security_reason")
    return resolved


def _require_resolved_entity(resolved_references: dict, scope: str, label: str, *, action_text: str) -> str | None:
    result = resolved_references.get(scope) or {}
    resolved = result.get("resolved")

    if resolved_references.get("security_blocked"):
        return f"No pude identificar con seguridad que {label} queres {action_text} en esta conversacion actual."

    if result.get("ambiguous"):
        return _format_ambiguity_message(f"Encontre varios {label}s posibles para {action_text}.", result.get("matches", []))

    if resolved is not None:
        return None

    if result.get("input"):
        normalized = result.get("normalized") or result["input"]
        if result.get("matches"):
            candidates = ", ".join(match["name"] for match in result["matches"][:3])
            return f"No pude resolver con suficiente confianza el {label} '{normalized}'. Los candidatos mas cercanos son: {candidates}."
        return f"No encontre un {label} que coincida con '{normalized}'."

    if scope in resolved_references.get("context", {}):
        return f"Tenia contexto previo para ese {label}, pero no pude reutilizarlo con confianza."

    return f"No pude identificar a que {label} te referis."


def _format_ambiguity_message(prefix: str, matches: list[dict]) -> str:
    lines = [prefix, "Podria ser:"]
    for item in matches[:5]:
        lines.append(f"- {item['name']}")
    return "\n".join(lines)


def _format_date(value):
    return str(value) if value else "Sin fecha"


def _format_task_summary(summary: dict) -> str:
    return "\n".join(
        [
            f"Resumen de la tarea {summary['task_id']}:",
            f"Titulo: {summary['title']}",
            f"Cliente: {summary['client_name']}",
            f"Proyecto: {summary['project_name']}",
            f"Estado actual: {summary['status']}",
            f"Prioridad: {summary['priority']}",
            f"Vence: {_format_date(summary['due_date'])}",
            f"Ultima nota: {summary['last_note'] or 'Sin nota registrada'}",
            f"Proxima accion: {summary['next_action'] or 'Sin proxima accion definida'}",
            f"Updates registrados: {summary['updates_count']}",
            f"Ultimo update: {summary['latest_update'] or 'No hay updates todavia'}",
        ]
    )


def _format_project_summary(summary: dict) -> str:
    return "\n".join(
        [
            f"Resumen del proyecto {summary['project_name']}:",
            f"Cliente: {summary['client_name']}",
            f"Estado: {summary['status']}",
            f"Descripcion: {summary['description'] or 'Sin descripcion'}",
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
    return "que sigue" in normalized


def _abort_with_context(parsed_query: dict, message: str) -> str:
    parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
    return message


def _remember_context(
    parsed_query: dict,
    resolved_references: dict,
    *,
    focus_scope: str,
    tasks: list | None = None,
    projects: list | None = None,
    project_summaries: list[dict] | None = None,
) -> None:
    context = _base_conversation_context(parsed_query, focus_scope)

    for scope in ("client", "project", "task"):
        item = resolved_references.get(scope, {}).get("resolved")
        if item:
            context[scope] = {"id": item["id"], "name": item["name"]}

    if tasks:
        unique_projects = {(task.project.id, task.project.name) for task in tasks if task.project}
        if len(tasks) == 1:
            task = tasks[0]
            context["task"] = {"id": task.id, "name": task.title}
        if len(unique_projects) == 1:
            project_id, project_name = next(iter(unique_projects))
            context["project"] = {"id": project_id, "name": project_name}

    if projects and len(projects) == 1:
        project = projects[0]
        context["project"] = {"id": project.id, "name": project.name}

    if project_summaries and len(project_summaries) == 1:
        project_summary = project_summaries[0]
        context["project"] = {"id": project_summary["project_id"], "name": project_summary["project_name"]}

    parsed_query["_conversation_context"] = context


def _remember_context_from_summary(parsed_query: dict, summary: dict, focus_scope: str) -> None:
    parsed_query["_conversation_context"] = {
        **_base_conversation_context(parsed_query, focus_scope),
        "client": {"id": summary["client_id"], "name": summary["client_name"]},
        "project": {"id": summary["project_id"], "name": summary["project_name"]},
        "task": {"id": summary["task_id"], "name": summary["title"]},
    }


def _remember_context_from_project_summary(parsed_query: dict, summary: dict) -> None:
    parsed_query["_conversation_context"] = {
        **_base_conversation_context(parsed_query, "project"),
        "client": {"id": summary["client_id"], "name": summary["client_name"]},
        "project": {"id": summary["project_id"], "name": summary["project_name"]},
    }


def _base_conversation_context(parsed_query: dict, scope: str) -> dict:
    return {
        "last_intent": parsed_query.get("intent"),
        "scope": scope,
        "_isolated": True,
        "_source": "current_session",
    }

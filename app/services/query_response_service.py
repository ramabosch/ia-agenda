from app.services.client_service import get_active_clients
from app.services.conversation_service import (
    get_conversations_for_today,
    get_last_conversation,
)
from app.services.project_service import (
    get_executive_project_snapshot,
    get_followup_project_snapshot,
    get_project_operational_summary,
    get_projects_by_client_id,
)
from app.services.reference_resolver import resolve_references
from app.services.task_service import (
    add_task_note_conversational,
    get_executive_task_snapshot,
    get_followup_task_snapshot,
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
    "clarify_entity_reference",
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
    "get_next_actions_summary",
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

EXECUTIVE_INTENTS = {
    "get_blocked_items_summary",
    "get_today_priority_summary",
    "get_overdue_or_stuck_summary",
    "get_client_attention_summary",
    "get_project_attention_summary",
    "get_general_executive_summary",
}

FOLLOWUP_INTENTS = {
    "get_next_actions_summary",
    "get_missing_next_actions_summary",
    "get_followup_needed_summary",
    "get_push_today_summary",
}


def build_response_from_query(
    parsed_query: dict,
    user_query: str | None = None,
    conversation_context: dict | None = None,
) -> str:
    intent = parsed_query.get("intent")
    resolved_references = _resolve_if_needed(parsed_query, user_query, conversation_context=conversation_context)

    if intent == "clarify_entity_reference":
        return _handle_clarification_intent(parsed_query, resolved_references)

    if intent == "get_active_clients":
        clients = get_active_clients()
        parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
        if not clients:
            return "No encontre clientes activos en la agenda."

        lines = ["Tus clientes activos actuales son:"]
        for client in clients:
            lines.append(f"- {client.name}")
        return "\n".join(lines)

    if intent in EXECUTIVE_INTENTS:
        return _handle_executive_intent(parsed_query, user_query, conversation_context)

    if intent in FOLLOWUP_INTENTS:
        return _handle_followup_intent(parsed_query, resolved_references, user_query, conversation_context)

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


def _handle_followup_intent(
    parsed_query: dict,
    resolved_references: dict,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    if parsed_query.get("intent") == "get_next_actions_summary":
        scoped_response = _build_followup_scoped_response(parsed_query, resolved_references)
        if scoped_response:
            return scoped_response

        explicit_scope = None
        if parsed_query.get("task_name"):
            explicit_scope = ("task", "tarea", "seguir")
        elif parsed_query.get("project_name"):
            explicit_scope = ("project", "proyecto", "seguir")
        elif parsed_query.get("client_name"):
            explicit_scope = ("client", "cliente", "seguir")

        if explicit_scope:
            scope_key, label, action_text = explicit_scope
            message = _require_resolved_entity(resolved_references, scope_key, label, action_text=action_text)
            if message:
                return _abort_with_context(parsed_query, message)

        if resolved_references.get("security_blocked"):
            return _abort_with_context(
                parsed_query,
                "No tengo contexto aislado actual para decirte que sigue con seguridad. Si queres, pedi un resumen global de proximos pasos.",
            )

    snapshot = get_followup_task_snapshot()
    project_snapshot = get_followup_project_snapshot()
    client_snapshot = _build_client_followup_snapshot(snapshot)

    parsed_query["_followup_scope"] = "global"
    parsed_query["_followup_heuristic"] = snapshot["heuristic"]
    parsed_query["_followup_entities_with_next_action"] = [item["title"] for item in snapshot["tasks_with_next_action"][:3]]
    parsed_query["_followup_entities_without_next_action"] = [item["title"] for item in snapshot["tasks_without_next_action"][:3]]
    parsed_query["_followup_inference_used"] = False
    parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")

    intent = parsed_query.get("intent")
    if intent == "get_missing_next_actions_summary":
        return _format_missing_next_actions_summary(snapshot, project_snapshot)
    if intent == "get_followup_needed_summary":
        return _format_followup_needed_summary(snapshot, project_snapshot, client_snapshot)
    if intent == "get_push_today_summary":
        return _format_push_today_summary(snapshot)
    return _format_next_actions_summary(snapshot, project_snapshot, client_snapshot)


def _build_followup_scoped_response(parsed_query: dict, resolved_references: dict) -> str | None:
    scope = resolved_references.get("scope")

    if scope == "task" and resolved_references.get("task", {}).get("resolved"):
        summary = get_task_operational_summary(resolved_references["task"]["resolved"]["id"])
        if not summary:
            return _abort_with_context(parsed_query, "Encontre la tarea, pero no pude cargar su seguimiento.")

        _remember_context_from_summary(parsed_query, summary, "task")
        parsed_query["_followup_scope"] = "contextual_task"
        parsed_query["_followup_heuristic"] = ["usa proxima accion explicita si existe", "si no existe, marca falta de seguimiento"]
        parsed_query["_followup_entities_with_next_action"] = [summary["title"]] if summary.get("next_action") else []
        parsed_query["_followup_entities_without_next_action"] = [] if summary.get("next_action") else [summary["title"]]
        parsed_query["_followup_inference_used"] = False

        if summary.get("next_action"):
            return "\n".join(
                [
                    f"Lo que sigue con la tarea {summary['title']} es:",
                    f"- Proximo paso: {summary['next_action']}",
                    f"- Estado: {summary['status']}",
                    f"- Prioridad: {summary['priority']}",
                ]
            )

        return "\n".join(
            [
                f"La tarea {summary['title']} sigue abierta, pero no tiene proxima accion definida.",
                f"- Estado: {summary['status']}",
                f"- Prioridad: {summary['priority']}",
                "- Falta seguimiento claro.",
            ]
        )

    if scope == "project" and resolved_references.get("project", {}).get("resolved"):
        project = resolved_references["project"]["resolved"]
        tasks = get_tasks_by_project_id(project["id"])
        _remember_context(parsed_query, resolved_references, focus_scope="project", tasks=tasks)
        return _format_scoped_followup_list(
            parsed_query,
            scope="project",
            scope_name=project["name"],
            tasks=tasks,
        )

    if scope == "client" and resolved_references.get("client", {}).get("resolved"):
        client = resolved_references["client"]["resolved"]
        tasks = get_open_tasks_by_client_id(client["id"])
        _remember_context(parsed_query, resolved_references, focus_scope="client", tasks=tasks)
        return _format_scoped_followup_list(
            parsed_query,
            scope="client",
            scope_name=client["name"],
            tasks=tasks,
        )

    return None


def _handle_clarification_intent(parsed_query: dict, resolved_references: dict) -> str:
    if resolved_references.get("security_blocked"):
        return _abort_with_context(
            parsed_query,
            "No tengo contexto aislado actual suficiente para interpretar esa referencia corta. Decime el cliente, proyecto o tarea exacta.",
        )

    if resolved_references.get("clarification_needed"):
        return _abort_with_context(parsed_query, _build_clarification_response(resolved_references))

    scope = resolved_references.get("scope")
    if scope == "task" and resolved_references.get("task", {}).get("resolved"):
        summary = get_task_operational_summary(resolved_references["task"]["resolved"]["id"])
        if not summary:
            return _abort_with_context(parsed_query, "Encontre la tarea, pero no pude cargar su resumen operativo.")
        _remember_context_from_summary(parsed_query, summary, "task")
        return _format_task_summary(summary)

    if scope == "project" and resolved_references.get("project", {}).get("resolved"):
        summary = get_project_operational_summary(resolved_references["project"]["resolved"]["id"])
        if not summary:
            return _abort_with_context(parsed_query, "Encontre el proyecto, pero no pude cargar su resumen operativo.")
        _remember_context_from_project_summary(parsed_query, summary)
        return _format_project_summary(summary)

    if scope == "client" and resolved_references.get("client", {}).get("resolved"):
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

    return _abort_with_context(parsed_query, _build_clarification_response(resolved_references))


def _format_scoped_followup_list(parsed_query: dict, *, scope: str, scope_name: str, tasks: list) -> str:
    items = _build_followup_items_from_tasks(tasks)
    open_items = [item for item in items if item["status"] != "hecha"]

    parsed_query["_followup_scope"] = f"contextual_{scope}"
    parsed_query["_followup_heuristic"] = [
        "prioriza bloqueadas sin proxima accion",
        "despues abiertas urgentes sin seguimiento",
        "despues acciones explicitas ya definidas",
    ]
    parsed_query["_followup_entities_with_next_action"] = [item["title"] for item in open_items if item["has_next_action"]][:3]
    parsed_query["_followup_entities_without_next_action"] = [item["title"] for item in open_items if item["missing_next_action"]][:3]
    parsed_query["_followup_inference_used"] = False

    if not open_items:
        if scope == "project":
            return f"En el proyecto {scope_name} no hay tareas abiertas."
        return f"Con {scope_name} no hay tareas abiertas."

    header = (
        f"Lo que sigue para el proyecto {scope_name}:"
        if scope == "project"
        else f"Lo que sigue para {scope_name}:"
    )
    lines = [header]
    for item in open_items[:5]:
        lines.append(_format_followup_item_line(item))
    return "\n".join(lines)


def _handle_executive_intent(parsed_query: dict, user_query: str | None, conversation_context: dict | None) -> str:
    context = conversation_context or {}
    if _should_use_contextual_executive_view(user_query, context):
        response = _build_contextual_executive_response(parsed_query, context)
        if response:
            return response

    snapshot = get_executive_task_snapshot()
    project_snapshot = get_executive_project_snapshot()
    client_snapshot = _build_client_attention_snapshot(snapshot)

    parsed_query["_executive_scope"] = "global"
    parsed_query["_executive_heuristic"] = snapshot["heuristic"]
    parsed_query["_executive_entities"] = {
        "tasks": [item["title"] for item in snapshot["recommended_tasks"][:3]],
        "projects": [item["project_name"] for item in project_snapshot["prioritized_projects"][:3]],
        "clients": [item["client_name"] for item in client_snapshot["prioritized_clients"][:3]],
    }

    intent = parsed_query.get("intent")
    parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")

    if intent == "get_blocked_items_summary":
        return _format_blocked_summary(snapshot, project_snapshot)
    if intent == "get_today_priority_summary":
        return _format_today_priority_summary(snapshot)
    if intent == "get_overdue_or_stuck_summary":
        return _format_overdue_or_stuck_summary(snapshot, project_snapshot)
    if intent == "get_client_attention_summary":
        return _format_client_attention_summary(client_snapshot)
    if intent == "get_project_attention_summary":
        return _format_project_attention_summary(project_snapshot)
    return _format_general_executive_summary(snapshot, project_snapshot, client_snapshot)


def _should_use_contextual_executive_view(user_query: str | None, context: dict) -> bool:
    if not user_query or not context or not context.get("_isolated"):
        return False
    normalized = user_query.strip().lower()
    if "que sigue" not in normalized and "mas urgente" not in normalized and "lo mas urgente" not in normalized:
        return False
    return context.get("scope") in {"task", "project", "client"}


def _build_contextual_executive_response(parsed_query: dict, context: dict) -> str | None:
    scope = context.get("scope")
    parsed_query["_executive_scope"] = f"contextual_{scope}"
    parsed_query["_context_source"] = "current"
    parsed_query["_context_isolated"] = True
    parsed_query["_executive_heuristic"] = ["prioriza siguiente paso dentro del contexto actual"]
    parsed_query["_conversation_context"] = context

    if scope == "task" and context.get("task"):
        summary = get_task_operational_summary(context["task"]["id"])
        if not summary:
            return None
        parsed_query["_executive_entities"] = {"tasks": [summary["title"]]}
        return "\n".join(
            [
                f"En esta conversacion, lo que sigue con la tarea {summary['title']} es:",
                f"- Proxima accion: {summary['next_action'] or 'Sin proxima accion definida'}",
                f"- Estado: {summary['status']}",
                f"- Prioridad: {summary['priority']}",
            ]
        )

    if scope == "project" and context.get("project"):
        tasks = get_tasks_by_project_id(context["project"]["id"])
        open_tasks = [task for task in tasks if task.status != "hecha"]
        prioritized = sorted(open_tasks, key=lambda task: _task_sort_tuple(task))[:3]
        parsed_query["_executive_entities"] = {"project": context["project"]["name"], "tasks": [task.title for task in prioritized]}
        lines = [f"En el proyecto {context['project']['name']}, esto es lo que sigue:"]
        for task in prioritized:
            lines.append(f"- {task.title} | {task.status} | prioridad {task.priority}")
        return "\n".join(lines) if prioritized else f"En el proyecto {context['project']['name']} no hay tareas abiertas."

    if scope == "client" and context.get("client"):
        tasks = get_open_tasks_by_client_id(context["client"]["id"])
        prioritized = sorted(tasks, key=lambda task: _task_sort_tuple(task))[:3]
        parsed_query["_executive_entities"] = {"client": context["client"]["name"], "tasks": [task.title for task in prioritized]}
        lines = [f"Con {context['client']['name']}, lo mas importante ahora es:"]
        for task in prioritized:
            project_name = task.project.name if task.project else "Sin proyecto"
            lines.append(f"- {task.title} | {task.status} | prioridad {task.priority} | Proyecto: {project_name}")
        return "\n".join(lines) if prioritized else f"Con {context['client']['name']} no hay tareas abiertas."

    return None


def _build_client_attention_snapshot(task_snapshot: dict) -> dict:
    clients: dict[int | str, dict] = {}
    for item in task_snapshot["open_tasks"]:
        client_id = item["client_id"] or item["client_name"]
        if client_id not in clients:
            clients[client_id] = {
                "client_id": item["client_id"],
                "client_name": item["client_name"],
                "open_tasks": 0,
                "blocked_tasks": 0,
                "high_priority_open_tasks": 0,
                "overdue_open_tasks": 0,
                "score": 0,
            }

        client = clients[client_id]
        client["open_tasks"] += 1
        client["blocked_tasks"] += int(item["is_blocked"])
        client["high_priority_open_tasks"] += int(item["is_high_priority"])
        client["overdue_open_tasks"] += int(item["is_overdue"])

    for client in clients.values():
        client["score"] = (
            client["blocked_tasks"] * 5
            + client["high_priority_open_tasks"] * 3
            + client["overdue_open_tasks"] * 2
            + client["open_tasks"] * 2
        )

    ranked = sorted(clients.values(), key=lambda item: (-item["score"], item["client_name"]))
    return {
        "clients": list(clients.values()),
        "prioritized_clients": ranked[:5],
        "heuristic": [
            "clientes con mas bloqueos primero",
            "despues mas alta prioridad abierta",
            "despues mas vencidas",
            "despues mayor carga abierta",
        ],
    }


def _build_client_followup_snapshot(task_snapshot: dict) -> dict:
    clients: dict[int | str, dict] = {}
    for item in task_snapshot["open_tasks"]:
        client_id = item["client_id"] or item["client_name"]
        if client_id not in clients:
            clients[client_id] = {
                "client_id": item["client_id"],
                "client_name": item["client_name"],
                "open_tasks": 0,
                "tasks_with_next_action": 0,
                "tasks_without_next_action": 0,
                "blocked_without_next_action": 0,
                "score": 0,
            }

        client = clients[client_id]
        client["open_tasks"] += 1
        client["tasks_with_next_action"] += int(item["has_next_action"])
        client["tasks_without_next_action"] += int(item["missing_next_action"])
        client["blocked_without_next_action"] += int(item["blocked_without_next_action"])

    for client in clients.values():
        client["score"] = (
            client["blocked_without_next_action"] * 5
            + client["tasks_without_next_action"] * 3
            + client["open_tasks"]
        )

    ranked = sorted(clients.values(), key=lambda item: (-item["score"], item["client_name"]))
    return {
        "clients": list(clients.values()),
        "prioritized_clients": ranked[:5],
        "heuristic": [
            "clientes con mas tareas sin seguimiento primero",
            "prioriza bloqueos sin proxima accion",
            "despues mayor carga abierta",
        ],
    }


def _format_blocked_summary(task_snapshot: dict, project_snapshot: dict) -> str:
    blocked_tasks = task_snapshot["blocked_tasks"][:5]
    blocked_projects = [item for item in project_snapshot["prioritized_projects"] if item["blocked_tasks"] > 0][:3]
    if not blocked_tasks:
        return "Hoy no encontre tareas bloqueadas abiertas."

    lines = ["Esto esta bloqueado ahora:"]
    for item in blocked_tasks:
        lines.append(f"- {item['title']} | Cliente: {item['client_name']} | Proyecto: {item['project_name']} | Prioridad: {item['priority']}")
    if blocked_projects:
        lines.append("")
        lines.append("Proyectos mas trabados:")
        for item in blocked_projects:
            lines.append(f"- {item['project_name']} ({item['client_name']}) | Bloqueadas: {item['blocked_tasks']} | Abiertas: {item['open_tasks']}")
    return "\n".join(lines)


def _format_today_priority_summary(task_snapshot: dict) -> str:
    recommended = task_snapshot["recommended_tasks"]
    if not recommended:
        return "Hoy no encontre tareas abiertas para priorizar."

    lines = ["Esto deberias mirar primero hoy:"]
    for item in recommended:
        reason = _task_reason_label(item)
        lines.append(f"- {item['title']} | {reason} | Cliente: {item['client_name']} | Proyecto: {item['project_name']}")
    return "\n".join(lines)


def _format_overdue_or_stuck_summary(task_snapshot: dict, project_snapshot: dict) -> str:
    overdue = task_snapshot["overdue_tasks"][:5]
    stuck_projects = [item for item in project_snapshot["prioritized_projects"] if item["blocked_tasks"] > 0 or item["overdue_open_tasks"] > 0][:3]
    if not overdue and not stuck_projects:
        return "No encontre tareas vencidas ni proyectos claramente trabados."

    lines = ["Lo mas atrasado o trabado ahora es:"]
    for item in overdue:
        lines.append(f"- {item['title']} | Vence: {item['due_date']} | Cliente: {item['client_name']} | Proyecto: {item['project_name']}")
    for item in stuck_projects:
        lines.append(f"- Proyecto {item['project_name']} ({item['client_name']}) | Bloqueadas: {item['blocked_tasks']} | Abiertas: {item['open_tasks']}")
    return "\n".join(lines)


def _format_client_attention_summary(client_snapshot: dict) -> str:
    prioritized = client_snapshot["prioritized_clients"]
    if not prioritized:
        return "No encontre clientes con carga operativa abierta."

    top = prioritized[0]
    lines = [f"El cliente que necesita atencion primero es {top['client_name']}."]
    lines.append(
        f"Tiene {top['open_tasks']} tareas abiertas, {top['blocked_tasks']} bloqueadas y {top['high_priority_open_tasks']} de alta prioridad."
    )
    if len(prioritized) > 1:
        lines.append("")
        lines.append("Despues seguirian:")
        for item in prioritized[1:4]:
            lines.append(f"- {item['client_name']} | Abiertas: {item['open_tasks']} | Bloqueadas: {item['blocked_tasks']}")
    return "\n".join(lines)


def _format_project_attention_summary(project_snapshot: dict) -> str:
    prioritized = project_snapshot["prioritized_projects"]
    if not prioritized:
        return "No encontre proyectos con carga operativa abierta."

    top = prioritized[0]
    lines = [f"El proyecto mas trabado ahora es {top['project_name']} ({top['client_name']})."]
    lines.append(
        f"Tiene {top['open_tasks']} tareas abiertas, {top['blocked_tasks']} bloqueadas y {top['high_priority_open_tasks']} de alta prioridad."
    )
    if len(prioritized) > 1:
        lines.append("")
        lines.append("Otros proyectos a mirar:")
        for item in prioritized[1:4]:
            lines.append(f"- {item['project_name']} ({item['client_name']}) | Abiertas: {item['open_tasks']} | Bloqueadas: {item['blocked_tasks']}")
    return "\n".join(lines)


def _format_general_executive_summary(task_snapshot: dict, project_snapshot: dict, client_snapshot: dict) -> str:
    lines = ["Resumen ejecutivo actual:"]
    lines.append(f"- Tareas abiertas: {len(task_snapshot['open_tasks'])}")
    lines.append(f"- Bloqueadas: {len(task_snapshot['blocked_tasks'])}")
    lines.append(f"- Urgentes: {len(task_snapshot['urgent_tasks'])}")

    if task_snapshot["recommended_tasks"]:
        top_task = task_snapshot["recommended_tasks"][0]
        lines.append(f"- Lo mas urgente: {top_task['title']} ({_task_reason_label(top_task)})")
    if project_snapshot["prioritized_projects"]:
        top_project = project_snapshot["prioritized_projects"][0]
        lines.append(f"- Proyecto mas sensible: {top_project['project_name']} ({top_project['client_name']})")
    if client_snapshot["prioritized_clients"]:
        top_client = client_snapshot["prioritized_clients"][0]
        lines.append(f"- Cliente a mirar primero: {top_client['client_name']}")
    return "\n".join(lines)


def _format_next_actions_summary(task_snapshot: dict, project_snapshot: dict, client_snapshot: dict) -> str:
    lines = ["Resumen de proximos pasos:"]

    explicit_items = task_snapshot["tasks_with_next_action"][:3]
    if explicit_items:
        lines.append("Proximos pasos ya definidos:")
        for item in explicit_items:
            lines.append(_format_followup_item_line(item))

    missing_items = task_snapshot["tasks_without_next_action"][:3]
    if missing_items:
        if explicit_items:
            lines.append("")
        lines.append("Abierto sin seguimiento claro:")
        for item in missing_items:
            lines.append(_format_followup_item_line(item))

    if project_snapshot["prioritized_projects"]:
        lines.append("")
        lines.append("Proyectos a ordenar:")
        for item in project_snapshot["prioritized_projects"][:3]:
            if item["tasks_without_next_action"] <= 0:
                continue
            lines.append(
                f"- {item['project_name']} ({item['client_name']}) | Sin proxima accion: {item['tasks_without_next_action']} | Abiertas: {item['open_tasks']}"
            )

    if client_snapshot["prioritized_clients"]:
        top_client = client_snapshot["prioritized_clients"][0]
        lines.append("")
        lines.append(
            f"Cliente mas expuesto por falta de seguimiento: {top_client['client_name']} ({top_client['tasks_without_next_action']} abiertas sin proxima accion)."
        )

    return "\n".join(lines)


def _format_missing_next_actions_summary(task_snapshot: dict, project_snapshot: dict) -> str:
    missing_items = task_snapshot["tasks_without_next_action"][:5]
    if not missing_items:
        return "No encontre tareas abiertas sin proxima accion definida."

    lines = ["Estas tareas abiertas no tienen proxima accion definida:"]
    for item in missing_items:
        lines.append(_format_followup_item_line(item))

    risky_projects = [item for item in project_snapshot["prioritized_projects"] if item["tasks_without_next_action"] > 0][:3]
    if risky_projects:
        lines.append("")
        lines.append("Proyectos con mas falta de seguimiento:")
        for item in risky_projects:
            lines.append(
                f"- {item['project_name']} ({item['client_name']}) | Sin proxima accion: {item['tasks_without_next_action']}"
            )
    return "\n".join(lines)


def _format_followup_needed_summary(task_snapshot: dict, project_snapshot: dict, client_snapshot: dict) -> str:
    followup_items = task_snapshot["followup_needed_tasks"][:5]
    if not followup_items:
        return "No encontre follow-ups pendientes claros en este momento."

    lines = ["Esto quedo abierto y necesita seguimiento:"]
    for item in followup_items:
        lines.append(_format_followup_item_line(item))

    risky_projects = [item for item in project_snapshot["prioritized_projects"] if item["blocked_without_next_action"] > 0][:3]
    if risky_projects:
        lines.append("")
        lines.append("Proyectos mas frenados por falta de seguimiento:")
        for item in risky_projects:
            lines.append(
                f"- {item['project_name']} ({item['client_name']}) | Bloqueadas sin proxima accion: {item['blocked_without_next_action']}"
            )

    risky_clients = [item for item in client_snapshot["prioritized_clients"] if item["tasks_without_next_action"] > 0][:2]
    if risky_clients:
        lines.append("")
        lines.append("Clientes con trabajo abierto sin seguimiento:")
        for item in risky_clients:
            lines.append(
                f"- {item['client_name']} | Sin proxima accion: {item['tasks_without_next_action']} | Abiertas: {item['open_tasks']}"
            )
    return "\n".join(lines)


def _format_push_today_summary(task_snapshot: dict) -> str:
    push_items = task_snapshot["push_today_tasks"][:5]
    if not push_items:
        return "No encontre tareas abiertas para empujar hoy."

    lines = ["Esto deberias empujar hoy si o si:"]
    for item in push_items:
        lines.append(_format_followup_item_line(item))
    return "\n".join(lines)


def _format_followup_item_line(item: dict) -> str:
    base = f"- {item['title']} | Cliente: {item['client_name']} | Proyecto: {item['project_name']}"
    if item["has_next_action"]:
        return f"{base} | Proximo paso: {item['next_action']}"
    return f"{base} | Falta definir proxima accion"


def _task_reason_label(item: dict) -> str:
    reasons = []
    if item["is_blocked"]:
        reasons.append("bloqueada")
    if item["is_overdue"]:
        reasons.append("vencida")
    elif item["is_due_today"]:
        reasons.append("vence hoy")
    if item["is_high_priority"]:
        reasons.append("alta prioridad")
    if item["is_in_progress"]:
        reasons.append("en progreso")
    return ", ".join(reasons) or item["status"]


def _task_sort_tuple(task) -> tuple:
    blocked = 1 if task.status == "bloqueada" else 0
    due = str(task.due_date) if task.due_date else "9999-12-31"
    high = 1 if task.priority == "alta" else 0
    progress = 1 if task.status == "en_progreso" else 0
    return (-blocked, due, -high, -progress, task.title)


def _build_followup_items_from_tasks(tasks: list) -> list[dict]:
    items = []
    for task in tasks:
        if task.status == "hecha":
            continue

        next_action = (task.next_action or "").strip() or None
        is_blocked = task.status == "bloqueada"
        is_high_priority = task.priority == "alta"
        missing_next_action = not next_action
        item = {
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "project_name": task.project.name if task.project else "Sin proyecto",
            "client_name": task.project.client.name if task.project and task.project.client else "Desconocido",
            "next_action": next_action,
            "has_next_action": bool(next_action),
            "missing_next_action": missing_next_action,
            "blocked_without_next_action": is_blocked and missing_next_action,
            "high_priority_without_next_action": is_high_priority and missing_next_action,
            "is_urgent": is_blocked or is_high_priority,
            "due_date": str(task.due_date) if task.due_date else None,
        }
        items.append(item)

    return sorted(
        items,
        key=lambda item: (
            -int(item["blocked_without_next_action"]),
            -int(item["high_priority_without_next_action"]),
            -int(item["missing_next_action"]),
            -int(item["is_urgent"] and item["has_next_action"]),
            item["due_date"] or "9999-12-31",
            item["title"],
        ),
    )


def _resolve_if_needed(parsed_query: dict, user_query: str | None, conversation_context: dict | None = None) -> dict:
    intent = parsed_query.get("intent")
    if intent not in REFERENCE_AWARE_INTENTS:
        resolved = {
            "scope": "none",
            "confidence": 0.0,
            "ambiguous": False,
            "source": "none",
            "clarification_needed": False,
            "clarification_reason": None,
            "candidate_types": [],
            "clarification_candidates": [],
        }
        parsed_query["_resolved_references"] = resolved
        parsed_query["_resolver_scope"] = "none"
        parsed_query["_resolver_source"] = "none"
        parsed_query["_resolver_confidence"] = 0.0
        parsed_query["_resolver_ambiguous"] = False
        parsed_query["_clarification_needed"] = False
        parsed_query["_clarification_reason"] = None
        parsed_query["_clarification_candidates"] = []
        parsed_query["_candidate_types"] = []
        parsed_query["_used_context_to_disambiguate"] = False
        parsed_query["_recent_context_used"] = {}
        parsed_query["_context_source"] = "none"
        parsed_query["_context_isolated"] = False
        parsed_query["_security_blocked"] = False
        parsed_query["_security_reason"] = None
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
    parsed_query["_clarification_needed"] = resolved.get("clarification_needed", False)
    parsed_query["_clarification_reason"] = resolved.get("clarification_reason")
    parsed_query["_clarification_candidates"] = resolved.get("clarification_candidates", [])
    parsed_query["_candidate_types"] = resolved.get("candidate_types", [])
    parsed_query["_used_context_to_disambiguate"] = resolved.get("used_context_to_disambiguate", False)
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
        return _build_clarification_response(
            resolved_references,
            prefix=f"Encontre varios {label}s posibles para {action_text}.",
        )

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


def _build_clarification_response(resolved_references: dict, prefix: str | None = None) -> str:
    reason = resolved_references.get("clarification_reason")
    candidates = resolved_references.get("clarification_candidates") or []

    if reason == "missing_context":
        return "No tengo contexto aislado actual suficiente para resolver esa referencia. Decime el cliente, proyecto o tarea exacta."

    if reason == "generic_request":
        return (
            "Necesito un poco mas de precision para saber a que te referis.\n"
            "Decime si queres ver un cliente, un proyecto o una tarea concreta."
        )

    if not candidates:
        return (
            "No pude identificar una entidad clara con esa referencia.\n"
            "Proba con el nombre del cliente, proyecto o tarea exacta."
        )

    lines = [prefix or "Necesito que me aclares a que te referis."]
    lines.append("Vi estas coincidencias posibles:")
    for item in candidates[:6]:
        lines.append(f"- {item['name']} ({_scope_label(item['scope'])})")
    lines.append("")
    lines.append("Si queres, te lo puedo resumir, actualizar o mostrar proximos pasos del que elijas.")
    return "\n".join(lines)


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
    return "que sigue" in normalized or "proximo paso" in normalized or "hacer ahora" in normalized


def _scope_label(scope: str) -> str:
    return {
        "client": "cliente",
        "project": "proyecto",
        "task": "tarea",
    }.get(scope, scope)


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

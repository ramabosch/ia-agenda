from datetime import date

from app.services.client_service import get_active_clients
from app.services.conversation_service import (
    get_conversations_for_today,
    get_last_conversation,
)
from app.services.project_service import (
    add_project_note_conversational,
    get_all_projects,
    get_executive_project_snapshot,
    get_followup_project_snapshot,
    get_operational_friction_project_snapshot,
    get_operational_recommendation_project_snapshot,
    get_project_advanced_summary,
    get_project_operational_summary,
    get_projects_by_client_id,
)
from app.services.reference_resolver import resolve_references
from app.services.task_service import (
    add_task_note_conversational,
    build_missing_due_date_snapshot_from_tasks,
    build_temporal_task_snapshot_from_tasks,
    build_client_advanced_summary,
    create_task_conversational,
    build_friction_focus_from_tasks,
    build_recommendation_focus_from_tasks,
    build_task_friction_summary,
    build_task_recommendation_summary,
    build_task_advanced_summary,
    get_executive_task_snapshot,
    get_followup_task_snapshot,
    get_missing_due_date_snapshot,
    get_open_tasks_by_client_id,
    get_operational_friction_snapshot,
    get_operational_recommendation_snapshot,
    get_temporal_task_snapshot,
    get_task_operational_summary,
    get_tasks_by_client_id,
    get_tasks_by_project_id,
    get_tasks_by_status,
    resolve_due_hint,
    update_task_next_action_conversational,
    update_task_priority_conversational,
    update_task_status_conversational,
)
from app.services.task_update_service import create_task_update


REFERENCE_AWARE_INTENTS = {
    "clarify_entity_reference",
    "get_operational_summary",
    "get_operational_friction_summary",
    "get_operational_recommendation",
    "create_task",
    "create_followup",
    "add_project_note",
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

CREATION_INTENTS = {
    "create_task",
    "create_followup",
    "add_project_note",
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

TEMPORAL_INTENTS = {
    "get_due_tasks_summary",
    "get_overdue_tasks_summary",
    "get_missing_due_date_summary",
}

FRICTION_INTENTS = {
    "get_operational_friction_summary",
}

RECOMMENDATION_INTENTS = {
    "get_operational_recommendation",
}

CONTINUITY_INTENTS = {
    "get_followup_focus_summary",
    "get_recommendation_explanation",
    "get_filtered_context_summary",
    "get_rephrased_summary",
    "get_client_facing_summary",
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

    if intent == "get_operational_summary":
        return _handle_operational_summary_intent(
            parsed_query,
            resolved_references,
            user_query=user_query,
            conversation_context=conversation_context,
        )

    if intent in FRICTION_INTENTS:
        return _handle_operational_friction_intent(
            parsed_query,
            resolved_references,
            user_query=user_query,
            conversation_context=conversation_context,
        )

    if intent in RECOMMENDATION_INTENTS:
        return _handle_operational_recommendation_intent(
            parsed_query,
            resolved_references,
            user_query=user_query,
            conversation_context=conversation_context,
        )

    if intent in CONTINUITY_INTENTS:
        return _handle_conversational_continuity_intent(
            parsed_query,
            user_query=user_query,
            conversation_context=conversation_context,
        )

    if intent in CREATION_INTENTS:
        return _handle_creation_intent(
            parsed_query,
            resolved_references,
            conversation_context=conversation_context,
        )

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

    if intent in TEMPORAL_INTENTS:
        return _handle_temporal_intent(
            parsed_query,
            resolved_references,
            user_query=user_query,
            conversation_context=conversation_context,
        )

    if intent == "get_client_summary":
        client_message = _require_resolved_entity(resolved_references, "client", "cliente", action_text="resumir")
        if client_message:
            return _abort_with_context(parsed_query, client_message)

        client = resolved_references["client"]["resolved"]
        projects = get_projects_by_client_id(client["id"])
        tasks = get_tasks_by_client_id(client["id"])
        _remember_context(parsed_query, resolved_references, focus_scope="client", projects=projects)
        advanced_summary = build_client_advanced_summary(client["name"], projects, tasks)
        _attach_operational_summary_debug(parsed_query, advanced_summary)
        return _format_advanced_client_summary(advanced_summary)

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
            advanced_summary = build_task_advanced_summary(summary)
            _attach_operational_summary_debug(parsed_query, advanced_summary)
            return _format_advanced_task_summary(summary, advanced_summary)

        task_message = _require_resolved_entity(resolved_references, "task", "tarea", action_text="resumir")
        if task_message:
            return _abort_with_context(parsed_query, task_message)

        summary = get_task_operational_summary(resolved_references["task"]["resolved"]["id"])
        if not summary:
            return _abort_with_context(parsed_query, "Encontre la tarea, pero no pude cargar su resumen operativo.")
        _remember_context_from_summary(parsed_query, summary, "task")
        advanced_summary = build_task_advanced_summary(summary)
        _attach_operational_summary_debug(parsed_query, advanced_summary)
        return _format_advanced_task_summary(summary, advanced_summary)

    if intent == "get_project_summary":
        project_id = parsed_query.get("project_id")
        if project_id:
            summary = get_project_operational_summary(project_id)
            if not summary:
                return _abort_with_context(parsed_query, f"No encontre un proyecto con ID {project_id}.")
            _remember_context_from_project_summary(parsed_query, summary)
            advanced_summary = get_project_advanced_summary(project_id)
            if not advanced_summary:
                return _format_project_summary(summary)
            _attach_operational_summary_debug(parsed_query, advanced_summary)
            return _format_advanced_project_summary(summary, advanced_summary)

        project_message = _require_resolved_entity(resolved_references, "project", "proyecto", action_text="resumir")
        if project_message:
            task_fallback = resolved_references.get("task", {}).get("resolved")
            if task_fallback and not resolved_references["task"]["ambiguous"]:
                task_summary = get_task_operational_summary(task_fallback["id"])
                if task_summary:
                    _remember_context_from_summary(parsed_query, task_summary, "task")
                    advanced_task = build_task_advanced_summary(task_summary)
                    _attach_operational_summary_debug(parsed_query, advanced_task)
                    return "No encontre un proyecto con ese nombre, pero si encontre una tarea muy parecida.\n\n" + _format_advanced_task_summary(task_summary, advanced_task)
            return _abort_with_context(parsed_query, project_message)

        summary = get_project_operational_summary(resolved_references["project"]["resolved"]["id"])
        if not summary:
            return _abort_with_context(parsed_query, "Encontre el proyecto, pero no pude cargar su resumen operativo.")
        _remember_context_from_project_summary(parsed_query, summary)
        advanced_summary = get_project_advanced_summary(resolved_references["project"]["resolved"]["id"])
        if not advanced_summary:
            return _format_project_summary(summary)
        _attach_operational_summary_debug(parsed_query, advanced_summary)
        return _format_advanced_project_summary(summary, advanced_summary)

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


def _handle_creation_intent(
    parsed_query: dict,
    resolved_references: dict,
    *,
    conversation_context: dict | None,
) -> str:
    parsed_query["_creation_intent"] = parsed_query.get("intent")
    parsed_query["_creation_real"] = False
    parsed_query["_creation_aborted"] = False
    parsed_query["_creation_target_scope"] = "none"
    parsed_query["_creation_fields"] = {
        "task_name": parsed_query.get("task_name"),
        "project_name": parsed_query.get("project_name"),
        "client_name": parsed_query.get("client_name"),
        "last_note": parsed_query.get("last_note"),
        "next_action": parsed_query.get("next_action"),
        "new_priority": parsed_query.get("new_priority"),
        "due_hint": parsed_query.get("due_hint"),
        "time_scope": parsed_query.get("time_scope"),
    }

    if resolved_references.get("clarification_needed"):
        parsed_query["_creation_aborted"] = True
        parsed_query["_creation_result"] = {"error": "clarification_needed"}
        return _abort_with_context(parsed_query, _build_clarification_response(resolved_references))

    intent = parsed_query.get("intent")
    if intent == "add_project_note":
        return _handle_project_note_creation(
            parsed_query,
            resolved_references,
            conversation_context=conversation_context,
        )
    return _handle_task_creation(parsed_query, resolved_references, conversation_context=conversation_context)


def _handle_project_note_creation(
    parsed_query: dict,
    resolved_references: dict,
    *,
    conversation_context: dict | None,
) -> str:
    note_content = (parsed_query.get("last_note") or "").strip()
    if not note_content:
        parsed_query["_creation_aborted"] = True
        parsed_query["_creation_result"] = {"error": "missing_note"}
        return _abort_with_context(parsed_query, "Necesito el contenido de la nota para agregarla al proyecto.")

    project = _resolve_creation_project_target(
        parsed_query,
        resolved_references,
        conversation_context=conversation_context,
    )
    if isinstance(project, str):
        parsed_query["_creation_aborted"] = True
        parsed_query["_creation_result"] = {"error": "project_resolution_failed"}
        return _abort_with_context(parsed_query, project)

    result = add_project_note_conversational(project["id"], note_content)
    parsed_query["_creation_target_scope"] = "project"
    parsed_query["_creation_result"] = result
    parsed_query["_creation_real"] = bool(result.get("updated"))
    if not result.get("updated"):
        parsed_query["_creation_aborted"] = True
        return _abort_with_context(parsed_query, "No pude registrar la nota en ese proyecto.")

    parsed_query["_update_type"] = "project_note"
    parsed_query["_update_real"] = True
    parsed_query["_update_result"] = result
    parsed_query["_conversation_context"] = {
        **_base_conversation_context(parsed_query, "project"),
        "project": {"id": project["id"], "name": project["name"]},
    }
    return f"Listo. Agregue una nota al proyecto '{project['name']}'. Contenido: '{note_content}'."


def _handle_task_creation(
    parsed_query: dict,
    resolved_references: dict,
    *,
    conversation_context: dict | None,
) -> str:
    title = _resolve_created_task_title(parsed_query, conversation_context)
    if not title:
        parsed_query["_creation_aborted"] = True
        parsed_query["_creation_result"] = {"error": "missing_title"}
        return _abort_with_context(parsed_query, "Necesito el nombre o contenido de la tarea para crearla con seguridad.")

    project = _resolve_creation_project_target(
        parsed_query,
        resolved_references,
        conversation_context=conversation_context,
    )
    if isinstance(project, str):
        parsed_query["_creation_aborted"] = True
        parsed_query["_creation_result"] = {"error": "project_resolution_failed"}
        return _abort_with_context(parsed_query, project)

    priority = parsed_query.get("new_priority") or "media"
    next_action = (parsed_query.get("next_action") or "").strip() or None
    note_content = (parsed_query.get("last_note") or "").strip() or None
    temporal_resolution = _resolve_creation_temporal_fields(parsed_query)
    if temporal_resolution.get("error_message"):
        parsed_query["_creation_aborted"] = True
        parsed_query["_creation_result"] = {
            "error": "temporal_resolution_failed",
            "temporal_resolution": temporal_resolution,
        }
        return _abort_with_context(parsed_query, temporal_resolution["error_message"])
    result = create_task_conversational(
        project["id"],
        title,
        priority=priority,
        due_date=temporal_resolution.get("due_date"),
        next_action=next_action,
        last_note=note_content,
    )

    parsed_query["_creation_target_scope"] = "project"
    parsed_query["_creation_result"] = result
    parsed_query["_creation_real"] = bool(result.get("created"))
    if not result.get("created"):
        parsed_query["_creation_aborted"] = True
        return _abort_with_context(parsed_query, "No pude crear la tarea en ese proyecto.")

    parsed_query["_update_type"] = "task_creation"
    parsed_query["_update_real"] = True
    parsed_query["_update_result"] = result
    parsed_query["_conversation_context"] = {
        **_base_conversation_context(parsed_query, "task"),
        "project": {"id": project["id"], "name": project["name"]},
        "task": {"id": result["task_id"], "name": result["task_title"]},
    }

    parts = [
        f"Listo. Cree una tarea nueva: '{result['task_title']}'.",
        f"Proyecto: {project['name']}.",
        f"Prioridad: {result['priority']}.",
    ]
    if next_action:
        parts.append(f"Proxima accion inicial: {next_action}.")
    if temporal_resolution.get("due_date"):
        parts.append(f"Vence: {temporal_resolution['due_date'].isoformat()}.")
    if note_content:
        parts.append(f"Nota inicial: {note_content}.")
    return " ".join(parts)


def _resolve_created_task_title(parsed_query: dict, conversation_context: dict | None) -> str | None:
    raw_title = (parsed_query.get("task_name") or "").strip()
    if raw_title and raw_title not in {"esto", "esta tarea", "esa tarea"}:
        return raw_title

    if parsed_query.get("intent") == "create_followup":
        return "Follow-up"

    context = conversation_context or {}
    if raw_title == "esto":
        snapshot = context.get("response_snapshot") if isinstance(context, dict) else None
        if isinstance(snapshot, dict):
            items = _snapshot_items(snapshot)
            if items:
                return items[0].get("title") or items[0].get("name")
        if context.get("task", {}).get("name"):
            return context["task"]["name"]

    if raw_title in {"esta tarea", "esa tarea"} and context.get("task", {}).get("name"):
        return context["task"]["name"]

    return None


def _resolve_creation_project_target(
    parsed_query: dict,
    resolved_references: dict,
    *,
    conversation_context: dict | None,
) -> dict | str:
    project = resolved_references.get("project", {}).get("resolved")
    if project:
        return project

    if resolved_references.get("project", {}).get("ambiguous"):
        return _build_clarification_response(
            resolved_references,
            prefix="Encontre varios proyectos posibles para crear eso.",
        )

    client = resolved_references.get("client", {}).get("resolved")
    if client:
        projects = get_projects_by_client_id(client["id"])
        if len(projects) == 1:
            return {"id": projects[0].id, "name": projects[0].name}
        if len(projects) > 1:
            names = ", ".join(project.name for project in projects[:3])
            return f"El cliente '{client['name']}' tiene varios proyectos. Decime en cual queres crearlo. Opciones: {names}."

    explicit_project_name = parsed_query.get("project_name")
    if explicit_project_name in {"este proyecto", "ese proyecto"}:
        context = conversation_context or {}
        if isinstance(context, dict) and context.get("_isolated"):
            current_project = context.get("project") or {}
            if current_project.get("id") and current_project.get("name"):
                return {"id": current_project["id"], "name": current_project["name"]}
        return "No tengo un proyecto actual suficientemente claro para crear trabajo ahi."

    projects = get_all_projects()
    if len(projects) == 1:
        return {"id": projects[0].id, "name": projects[0].name}

    return "No tengo un proyecto claro para crear eso. Decime el proyecto o hacelo desde una conversacion ya enfocada en ese proyecto."


def _resolve_creation_temporal_fields(parsed_query: dict) -> dict:
    due_hint = parsed_query.get("due_hint")
    if not due_hint:
        return {
            "due_hint": None,
            "time_scope": None,
            "due_date": None,
            "error_message": None,
            "degraded": False,
        }

    resolved = resolve_due_hint(due_hint, today=date.today())
    error_message = None
    if not resolved.get("resolved"):
        if resolved.get("reason") == "range_requires_concrete_day":
            error_message = "Entiendo el alcance temporal, pero para guardarlo como fecha necesito un dia concreto."
        else:
            error_message = "No pude interpretar esa referencia temporal con suficiente claridad."

    return {
        "due_hint": due_hint,
        "time_scope": resolved.get("time_scope") or parsed_query.get("time_scope"),
        "due_date": resolved.get("due_date"),
        "label": resolved.get("label"),
        "degraded": bool(resolved.get("degraded")),
        "error_message": error_message,
    }


def _handle_temporal_intent(
    parsed_query: dict,
    resolved_references: dict,
    *,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    context = conversation_context or {}
    if _should_use_contextual_temporal_view(user_query, context):
        response = _build_contextual_temporal_response(parsed_query, context)
        if response:
            return response

    intent = parsed_query.get("intent")
    time_scope = parsed_query.get("time_scope")
    temporal_focus = parsed_query.get("temporal_focus")
    parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")

    if intent == "get_missing_due_date_summary":
        snapshot = get_missing_due_date_snapshot()
        _attach_temporal_debug(parsed_query, snapshot, interpretation="missing_due_date")
        return _format_missing_due_date_summary(snapshot)

    if intent == "get_overdue_tasks_summary":
        snapshot = get_temporal_task_snapshot("overdue")
        _attach_temporal_debug(parsed_query, snapshot, interpretation="overdue")
        return _format_temporal_summary(snapshot)

    snapshot = get_temporal_task_snapshot(time_scope or "due_items", temporal_focus=temporal_focus)
    _attach_temporal_debug(parsed_query, snapshot, interpretation=time_scope or "due_items")
    return _format_temporal_summary(snapshot)


def _should_use_contextual_temporal_view(user_query: str | None, context: dict) -> bool:
    if not user_query or not context or not context.get("_isolated"):
        return False
    normalized = user_query.strip().lower()
    return normalized.startswith("y ")


def _build_contextual_temporal_response(parsed_query: dict, context: dict) -> str | None:
    scope = context.get("scope")
    if scope == "task" and context.get("task", {}).get("id"):
        summary = get_task_operational_summary(context["task"]["id"])
        if not summary:
            return None
        tasks = [_summary_to_task_like(summary)]
    elif scope == "project" and context.get("project", {}).get("id"):
        tasks = get_tasks_by_project_id(context["project"]["id"])
    elif scope == "client" and context.get("client", {}).get("id"):
        tasks = get_tasks_by_client_id(context["client"]["id"])
    else:
        return None

    intent = parsed_query.get("intent")
    if intent == "get_missing_due_date_summary":
        snapshot = build_missing_due_date_snapshot_from_tasks(tasks, today=date.today())
        parsed_query["_conversation_context"] = context
        _attach_temporal_debug(parsed_query, snapshot, scope_override=f"contextual_{scope}", interpretation="missing_due_date")
        return _format_missing_due_date_summary(snapshot, scope_label=_context_scope_name(context, scope))

    time_scope = "overdue" if intent == "get_overdue_tasks_summary" else (parsed_query.get("time_scope") or "due_items")
    snapshot = build_temporal_task_snapshot_from_tasks(
        tasks,
        time_scope=time_scope,
        today=date.today(),
        temporal_focus=parsed_query.get("temporal_focus"),
    )
    parsed_query["_conversation_context"] = context
    _attach_temporal_debug(parsed_query, snapshot, scope_override=f"contextual_{scope}", interpretation=time_scope)
    return _format_temporal_summary(snapshot, scope_label=_context_scope_name(context, scope))


def _summary_to_task_like(summary: dict):
    project = type("ProjectLike", (), {})()
    client = type("ClientLike", (), {})()
    client.id = summary.get("client_id")
    client.name = summary.get("client_name")
    project.id = summary.get("project_id")
    project.name = summary.get("project_name")
    project.client = client

    task = type("TaskLike", (), {})()
    task.id = summary.get("task_id")
    task.title = summary.get("title")
    task.project = project
    task.status = summary.get("status")
    task.priority = summary.get("priority")
    task.due_date = summary.get("due_date")
    task.last_note = summary.get("last_note")
    task.next_action = summary.get("next_action")
    task.updates = []
    task.description = summary.get("description")
    task.created_at = summary.get("created_at")
    task.last_updated_at = summary.get("last_updated_at")
    return task


def _context_scope_name(context: dict, scope: str) -> str:
    if scope == "task":
        return context.get("task", {}).get("name") or "esta tarea"
    if scope == "project":
        return context.get("project", {}).get("name") or "este proyecto"
    if scope == "client":
        return context.get("client", {}).get("name") or "este cliente"
    return "este contexto"


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


def _handle_operational_summary_intent(
    parsed_query: dict,
    resolved_references: dict,
    *,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    context = conversation_context or {}
    contextual_scope = _preferred_contextual_summary_scope(user_query, context)
    if contextual_scope:
        scoped_response = _build_contextual_operational_summary(parsed_query, context, contextual_scope)
        if scoped_response:
            return scoped_response

    if resolved_references.get("security_blocked"):
        return _abort_with_context(
            parsed_query,
            "No tengo contexto aislado actual suficiente para resumir eso con seguridad. Decime el cliente, proyecto o tarea exacta.",
        )

    if resolved_references.get("clarification_needed") or resolved_references.get("ambiguous"):
        return _abort_with_context(parsed_query, _build_clarification_response(resolved_references))

    if resolved_references.get("task", {}).get("resolved"):
        task_id = resolved_references["task"]["resolved"]["id"]
        summary = get_task_operational_summary(task_id)
        if not summary:
            return _abort_with_context(parsed_query, "Encontre la tarea, pero no pude cargar su resumen operativo.")
        _remember_context_from_summary(parsed_query, summary, "task")
        advanced_summary = build_task_advanced_summary(summary)
        _attach_operational_summary_debug(parsed_query, advanced_summary)
        return _format_advanced_task_summary(summary, advanced_summary)

    if resolved_references.get("project", {}).get("resolved"):
        project_id = resolved_references["project"]["resolved"]["id"]
        summary = get_project_operational_summary(project_id)
        if not summary:
            return _abort_with_context(parsed_query, "Encontre el proyecto, pero no pude cargar su resumen operativo.")
        advanced_summary = get_project_advanced_summary(project_id)
        _remember_context_from_project_summary(parsed_query, summary)
        if not advanced_summary:
            return _format_project_summary(summary)
        _attach_operational_summary_debug(parsed_query, advanced_summary)
        return _format_advanced_project_summary(summary, advanced_summary)

    if resolved_references.get("client", {}).get("resolved"):
        client = resolved_references["client"]["resolved"]
        projects = get_projects_by_client_id(client["id"])
        tasks = get_tasks_by_client_id(client["id"])
        _remember_context(parsed_query, resolved_references, focus_scope="client", projects=projects)
        advanced_summary = build_client_advanced_summary(client["name"], projects, tasks)
        _attach_operational_summary_debug(parsed_query, advanced_summary)
        return _format_advanced_client_summary(advanced_summary)

    return _abort_with_context(
        parsed_query,
        "No pude identificar con claridad que cliente, proyecto o tarea queres resumir.",
    )


def _preferred_contextual_summary_scope(user_query: str | None, context: dict) -> str | None:
    if not user_query or not context or not context.get("_isolated"):
        return None
    normalized = user_query.strip().lower()
    if not any(
        marker in normalized
        for marker in (
            "aca",
            "acá",
            "esto",
            "como estamos",
            "cómo estamos",
            "como viene esto",
            "cómo viene esto",
            "que es lo mas importante aca",
            "qué es lo más importante acá",
        )
    ):
        return None
    return context.get("scope")


def _build_contextual_operational_summary(parsed_query: dict, context: dict, scope: str) -> str | None:
    if scope == "task" and context.get("task"):
        summary = get_task_operational_summary(context["task"]["id"])
        if not summary:
            return None
        _remember_context_from_summary(parsed_query, summary, "task")
        advanced_summary = build_task_advanced_summary(summary)
        _attach_operational_summary_debug(parsed_query, advanced_summary, scope_override="contextual_task")
        return _format_advanced_task_summary(summary, advanced_summary)

    if scope == "project" and context.get("project"):
        summary = get_project_operational_summary(context["project"]["id"])
        advanced_summary = get_project_advanced_summary(context["project"]["id"])
        if not summary or not advanced_summary:
            return None
        _remember_context_from_project_summary(parsed_query, summary)
        _attach_operational_summary_debug(parsed_query, advanced_summary, scope_override="contextual_project")
        return _format_advanced_project_summary(summary, advanced_summary)

    if scope == "client" and context.get("client"):
        projects = get_projects_by_client_id(context["client"]["id"])
        tasks = get_tasks_by_client_id(context["client"]["id"])
        advanced_summary = build_client_advanced_summary(context["client"]["name"], projects, tasks)
        parsed_query["_conversation_context"] = context
        _attach_operational_summary_debug(parsed_query, advanced_summary, scope_override="contextual_client")
        return _format_advanced_client_summary(advanced_summary)

    return None


def _handle_operational_friction_intent(
    parsed_query: dict,
    resolved_references: dict,
    *,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    context = conversation_context or {}
    contextual_scope = _preferred_contextual_friction_scope(user_query, context)
    if contextual_scope:
        contextual_response = _build_contextual_friction_summary(parsed_query, context, contextual_scope)
        if contextual_response:
            return contextual_response

    if resolved_references.get("security_blocked"):
        return _abort_with_context(
            parsed_query,
            "No tengo contexto aislado actual suficiente para analizar que esta frenado con seguridad. Decime el cliente, proyecto o tarea exacta.",
        )

    if resolved_references.get("clarification_needed") or resolved_references.get("ambiguous"):
        return _abort_with_context(parsed_query, _build_clarification_response(resolved_references))

    if resolved_references.get("task", {}).get("resolved"):
        summary = get_task_operational_summary(resolved_references["task"]["resolved"]["id"])
        if not summary:
            return _abort_with_context(parsed_query, "Encontre la tarea, pero no pude cargar sus senales de friccion.")
        _remember_context_from_summary(parsed_query, summary, "task")
        friction_summary = build_task_friction_summary(summary)
        _attach_friction_debug(parsed_query, friction_summary, scope_override="task")
        return _format_task_friction_summary(summary, friction_summary)

    if resolved_references.get("project", {}).get("resolved"):
        project = resolved_references["project"]["resolved"]
        tasks = get_tasks_by_project_id(project["id"])
        summary = _build_project_friction_summary(project["name"], resolved_references.get("client", {}).get("resolved", {}).get("name") or "Desconocido", tasks)
        _remember_context(parsed_query, resolved_references, focus_scope="project", tasks=tasks)
        _attach_friction_debug(parsed_query, summary, scope_override="project")
        return _format_project_friction_summary(summary)

    if resolved_references.get("client", {}).get("resolved"):
        client = resolved_references["client"]["resolved"]
        tasks = get_tasks_by_client_id(client["id"])
        projects = get_projects_by_client_id(client["id"])
        summary = _build_client_friction_summary(client["name"], projects, tasks)
        _remember_context(parsed_query, resolved_references, focus_scope="client", projects=projects)
        _attach_friction_debug(parsed_query, summary, scope_override="client")
        return _format_client_friction_summary(summary)

    task_snapshot = get_operational_friction_snapshot()
    project_snapshot = get_operational_friction_project_snapshot()
    client_snapshot = _build_client_friction_snapshot(task_snapshot)
    parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
    _attach_friction_debug(
        parsed_query,
        {
            "scope": "global",
            "status_overview": task_snapshot["status_overview"],
            "heuristic": task_snapshot["heuristic"],
            "signals": task_snapshot["friction_tasks"],
            "recommendation": task_snapshot["recommendation"],
        },
        scope_override="global",
    )
    return _format_global_friction_summary(task_snapshot, project_snapshot, client_snapshot)


def _preferred_contextual_friction_scope(user_query: str | None, context: dict) -> str | None:
    if not user_query or not context or not context.get("_isolated"):
        return None
    normalized = user_query.strip().lower()
    if not any(
        marker in normalized
        for marker in (
            "que me preocuparia de este cliente",
            "qué me preocuparía de este cliente",
            "que viene mal aca",
            "qué viene mal acá",
            "y que esta frenado",
            "y qué está frenado",
        )
    ):
        return None
    return context.get("scope")


def _build_contextual_friction_summary(parsed_query: dict, context: dict, scope: str) -> str | None:
    if scope == "task" and context.get("task"):
        summary = get_task_operational_summary(context["task"]["id"])
        if not summary:
            return None
        friction_summary = build_task_friction_summary(summary)
        _remember_context_from_summary(parsed_query, summary, "task")
        _attach_friction_debug(parsed_query, friction_summary, scope_override="contextual_task")
        return _format_task_friction_summary(summary, friction_summary)

    if scope == "project" and context.get("project"):
        tasks = get_tasks_by_project_id(context["project"]["id"])
        summary = _build_project_friction_summary(
            context["project"]["name"],
            context.get("client", {}).get("name", "Desconocido"),
            tasks,
        )
        parsed_query["_conversation_context"] = context
        _attach_friction_debug(parsed_query, summary, scope_override="contextual_project")
        return _format_project_friction_summary(summary)

    if scope == "client" and context.get("client"):
        tasks = get_tasks_by_client_id(context["client"]["id"])
        projects = get_projects_by_client_id(context["client"]["id"])
        summary = _build_client_friction_summary(context["client"]["name"], projects, tasks)
        parsed_query["_conversation_context"] = context
        _attach_friction_debug(parsed_query, summary, scope_override="contextual_client")
        return _format_client_friction_summary(summary)

    return None


def _build_project_friction_summary(project_name: str, client_name: str, tasks: list) -> dict:
    focus = build_friction_focus_from_tasks(tasks)
    open_count = len(focus["open_tasks"])
    return {
        "scope": "project",
        "entity_name": project_name,
        "client_name": client_name,
        "status_overview": (
            f"Hay {open_count} tareas abiertas y {len(focus['friction_tasks'])} con senales de friccion."
            if open_count
            else "No veo tareas abiertas en este proyecto."
        ),
        "signals": focus["friction_tasks"],
        "recommendation": focus["recommendation"],
        "heuristic": focus["heuristic"],
    }


def _build_client_friction_summary(client_name: str, projects: list, tasks: list) -> dict:
    focus = build_friction_focus_from_tasks(tasks)
    open_count = len(focus["open_tasks"])
    return {
        "scope": "client",
        "entity_name": client_name,
        "project_count": len(projects),
        "status_overview": (
            f"Hay {len(projects)} proyectos, {open_count} tareas abiertas y {len(focus['friction_tasks'])} con senales de friccion."
            if open_count
            else f"Hay {len(projects)} proyectos y no veo trabajo abierto con friccion clara."
        ),
        "signals": focus["friction_tasks"],
        "recommendation": focus["recommendation"],
        "heuristic": focus["heuristic"],
    }


def _build_client_friction_snapshot(task_snapshot: dict) -> dict:
    clients = {}
    for item in task_snapshot["friction_tasks"]:
        client_id = item["client_id"]
        if client_id is None:
            continue

        client = clients.setdefault(
            client_id,
            {
                "client_name": item["client_name"],
                "friction_tasks": 0,
                "strong_stall_signals": 0,
                "without_next_action": 0,
                "score": 0,
            },
        )
        client["friction_tasks"] += 1
        client["strong_stall_signals"] += int(item["has_strong_stall_signal"])
        client["without_next_action"] += int(item["missing_next_action"])
        client["score"] = client["strong_stall_signals"] * 5 + client["without_next_action"] * 3 + client["friction_tasks"] * 2

    prioritized = sorted(clients.values(), key=lambda item: (-item["score"], item["client_name"]))
    return {"prioritized_clients": prioritized[:5]}


def _handle_operational_recommendation_intent(
    parsed_query: dict,
    resolved_references: dict,
    *,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    context = conversation_context or {}
    focus = parsed_query.get("recommendation_focus") or _infer_recommendation_focus(user_query)
    contextual_scope = _preferred_contextual_recommendation_scope(user_query, context)
    if contextual_scope:
        contextual_response = _build_contextual_recommendation_response(parsed_query, context, contextual_scope, focus=focus)
        if contextual_response:
            return contextual_response

    if resolved_references.get("security_blocked"):
        return _abort_with_context(
            parsed_query,
            "No tengo contexto aislado actual suficiente para recomendar eso con seguridad. Decime el cliente, proyecto o tarea exacta.",
        )

    if resolved_references.get("clarification_needed") or resolved_references.get("ambiguous"):
        return _abort_with_context(parsed_query, _build_clarification_response(resolved_references))

    if resolved_references.get("task", {}).get("resolved"):
        summary = get_task_operational_summary(resolved_references["task"]["resolved"]["id"])
        if not summary:
            return _abort_with_context(parsed_query, "Encontre la tarea, pero no pude cargar una recomendacion operativa.")
        recommendation_summary = build_task_recommendation_summary(summary, focus=focus)
        _remember_context_from_summary(parsed_query, summary, "task")
        _attach_recommendation_debug(parsed_query, recommendation_summary, scope_override="task")
        return _format_task_recommendation_summary(summary, recommendation_summary)

    if resolved_references.get("project", {}).get("resolved"):
        project = resolved_references["project"]["resolved"]
        tasks = get_tasks_by_project_id(project["id"])
        summary = _build_project_recommendation_summary(
            project_name=project["name"],
            client_name=resolved_references.get("client", {}).get("resolved", {}).get("name") or "Desconocido",
            tasks=tasks,
            focus=focus,
        )
        _remember_context(parsed_query, resolved_references, focus_scope="project", tasks=tasks)
        _attach_recommendation_debug(parsed_query, summary, scope_override="project")
        return _format_scoped_recommendation_summary(summary)

    if resolved_references.get("client", {}).get("resolved"):
        client = resolved_references["client"]["resolved"]
        tasks = get_tasks_by_client_id(client["id"])
        projects = get_projects_by_client_id(client["id"])
        summary = _build_client_recommendation_summary(client["name"], projects, tasks, focus=focus)
        _remember_context(parsed_query, resolved_references, focus_scope="client", projects=projects)
        _attach_recommendation_debug(parsed_query, summary, scope_override="client")
        return _format_scoped_recommendation_summary(summary)

    snapshot = get_operational_recommendation_snapshot(focus=focus)
    project_snapshot = get_operational_recommendation_project_snapshot(focus=focus)
    client_snapshot = _build_client_recommendation_snapshot(snapshot)
    parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
    _attach_recommendation_debug(
        parsed_query,
        {
            "scope": "global",
            "status_overview": snapshot["status_overview"],
            "heuristic": snapshot["heuristic"],
            "recommendations": snapshot["recommendations"],
            "recommendation": snapshot["recommendation"],
        },
        scope_override="global",
    )
    return _format_global_recommendation_summary(snapshot, project_snapshot, client_snapshot, focus=focus)


def _infer_recommendation_focus(user_query: str | None) -> str:
    if not user_query:
        return "general"
    normalized = user_query.strip().lower()
    if "destraba" in normalized:
        return "unblock"
    if "cerrar hoy" in normalized or "conviene cerrar" in normalized:
        return "close"
    return "general"


def _preferred_contextual_recommendation_scope(user_query: str | None, context: dict) -> str | None:
    if not user_query or not context or not context.get("_isolated"):
        return None
    normalized = user_query.strip().lower()
    if not any(
        marker in normalized
        for marker in (
            "que haria ahora",
            "quÃ© harÃ­as ahora",
            "que priorizarias aca",
            "quÃ© priorizarÃ­as acÃ¡",
            "que priorizarias en este proyecto",
            "quÃ© priorizarÃ­as en este proyecto",
            "que priorizarias en ese proyecto",
            "quÃ© priorizarÃ­as en ese proyecto",
            "que haria ahora con este cliente",
            "quÃ© harÃ­as ahora con este cliente",
            "que deberia priorizar aca",
            "quÃ© deberÃ­a priorizar acÃ¡",
            "que atacaria primero",
            "quÃ© atacarÃ­a primero",
        )
    ):
        return None
    return context.get("scope")


def _build_contextual_recommendation_response(parsed_query: dict, context: dict, scope: str, *, focus: str) -> str | None:
    if scope == "task" and context.get("task"):
        summary = get_task_operational_summary(context["task"]["id"])
        if not summary:
            return None
        recommendation_summary = build_task_recommendation_summary(summary, focus=focus)
        _remember_context_from_summary(parsed_query, summary, "task")
        _attach_recommendation_debug(parsed_query, recommendation_summary, scope_override="contextual_task")
        return _format_task_recommendation_summary(summary, recommendation_summary)

    if scope == "project" and context.get("project"):
        tasks = get_tasks_by_project_id(context["project"]["id"])
        summary = _build_project_recommendation_summary(
            project_name=context["project"]["name"],
            client_name=context.get("client", {}).get("name", "Desconocido"),
            tasks=tasks,
            focus=focus,
        )
        parsed_query["_conversation_context"] = context
        _attach_recommendation_debug(parsed_query, summary, scope_override="contextual_project")
        return _format_scoped_recommendation_summary(summary)

    if scope == "client" and context.get("client"):
        tasks = get_tasks_by_client_id(context["client"]["id"])
        projects = get_projects_by_client_id(context["client"]["id"])
        summary = _build_client_recommendation_summary(context["client"]["name"], projects, tasks, focus=focus)
        parsed_query["_conversation_context"] = context
        _attach_recommendation_debug(parsed_query, summary, scope_override="contextual_client")
        return _format_scoped_recommendation_summary(summary)

    return None


def _build_project_recommendation_summary(project_name: str, client_name: str, tasks: list, *, focus: str) -> dict:
    recommendation = build_recommendation_focus_from_tasks(tasks, focus=focus)
    open_count = len(recommendation["open_tasks"])
    return {
        "scope": "project",
        "entity_name": project_name,
        "client_name": client_name,
        "status_overview": (
            f"Hay {open_count} tareas abiertas y priorice donde veo mas impacto dentro de este proyecto."
            if open_count
            else "No veo tareas abiertas en este proyecto para recomendar."
        ),
        "recommendations": recommendation["recommendations"],
        "heuristic": recommendation["heuristic"],
        "recommendation": recommendation["recommendation"],
    }


def _build_client_recommendation_summary(client_name: str, projects: list, tasks: list, *, focus: str) -> dict:
    recommendation = build_recommendation_focus_from_tasks(tasks, focus=focus)
    open_count = len(recommendation["open_tasks"])
    return {
        "scope": "client",
        "entity_name": client_name,
        "project_count": len(projects),
        "status_overview": (
            f"Hay {len(projects)} proyectos y {open_count} tareas abiertas. Priorice donde veo mas impacto con este cliente."
            if open_count
            else f"Hay {len(projects)} proyectos, pero no veo trabajo abierto para recomendar con {client_name}."
        ),
        "recommendations": recommendation["recommendations"],
        "heuristic": recommendation["heuristic"],
        "recommendation": recommendation["recommendation"],
    }


def _build_client_recommendation_snapshot(task_snapshot: dict) -> dict:
    clients: dict[int | str, dict] = {}
    for item in task_snapshot["recommendations"]:
        client_id = item["client_id"] or item["client_name"]
        if client_id not in clients:
            clients[client_id] = {
                "client_id": item["client_id"],
                "client_name": item["client_name"],
                "top_recommendation": item["title"],
                "score": item["recommendation_score"],
                "reasons": item["recommendation_reasons"],
            }
    ranked = sorted(clients.values(), key=lambda item: (-item["score"], item["client_name"]))
    return {"prioritized_clients": ranked[:5]}


def _handle_conversational_continuity_intent(
    parsed_query: dict,
    *,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    context = conversation_context or {}
    snapshot = context.get("response_snapshot") if isinstance(context, dict) else None

    parsed_query["_continuity_type"] = parsed_query.get("intent")
    parsed_query["_continuity_used_context"] = bool(context.get("_isolated"))
    parsed_query["_continuity_used_recommendation"] = bool(snapshot and snapshot.get("recommendations"))
    parsed_query["_continuity_filter_mode"] = parsed_query.get("filter_mode")
    parsed_query["_continuity_rephrase_style"] = parsed_query.get("rephrase_style")
    parsed_query["_adaptive_output_mode"] = parsed_query.get("rephrase_style")
    parsed_query["_adaptive_filter_mode"] = parsed_query.get("filter_mode")
    parsed_query["_adaptive_snapshot_reused"] = bool(snapshot)
    parsed_query["_adaptive_degraded"] = False
    parsed_query["_adaptive_transform_type"] = "continuity"
    parsed_query["_context_source"] = "current" if context.get("_isolated") else "none"
    parsed_query["_context_isolated"] = bool(context.get("_isolated"))
    parsed_query["_recent_context_used"] = context if context.get("_isolated") else {}

    if not context or not context.get("_isolated"):
        return _abort_with_context(
            parsed_query,
            "No tengo contexto aislado actual para continuar esa conversacion con seguridad.",
        )

    if parsed_query.get("intent") == "get_followup_focus_summary":
        followup_focus = parsed_query.get("followup_focus")
        if followup_focus == "friction":
            response = _build_contextual_friction_summary(parsed_query, context, context.get("scope"))
            if response:
                return response
            return _abort_with_context(parsed_query, "No pude reutilizar el contexto actual para profundizar en lo que preocupa.")

        if followup_focus == "next_after_recommendation":
            if not snapshot or not snapshot.get("recommendations"):
                return _abort_with_context(
                    parsed_query,
                    "No tengo una recomendacion previa clara en esta conversacion actual para decirte que iria despues.",
                )
            response = _format_next_recommendation_followup(snapshot)
            _store_response_snapshot(
                parsed_query,
                {
                    **snapshot,
                    "response_kind": "followup_next_recommendation",
                    "status_overview": snapshot.get("status_overview"),
                    "recommendation": response,
                },
            )
            return response

    if parsed_query.get("intent") == "get_recommendation_explanation":
        if not snapshot or not snapshot.get("recommendations"):
            return _abort_with_context(
                parsed_query,
                "No tengo una recomendacion previa clara en esta conversacion actual para explicarte por que seria la primera.",
            )
        response = _format_recommendation_explanation(snapshot)
        _store_response_snapshot(
            parsed_query,
            {
                **snapshot,
                "response_kind": "recommendation_explanation",
                "recommendation": response,
            },
        )
        return response

    if parsed_query.get("intent") == "get_filtered_context_summary":
        if not snapshot:
            return _abort_with_context(
                parsed_query,
                "No tengo una respuesta previa clara en esta conversacion actual para filtrarla.",
            )
        response, filtered_snapshot = _format_filtered_context_summary(snapshot, parsed_query.get("filter_mode"))
        parsed_query["_adaptive_degraded"] = bool(filtered_snapshot.get("degraded"))
        parsed_query["_adaptive_transform_type"] = filtered_snapshot.get("transform_type", "filtered")
        _store_response_snapshot(parsed_query, filtered_snapshot)
        return response

    if parsed_query.get("intent") == "get_rephrased_summary":
        if not snapshot:
            return _abort_with_context(
                parsed_query,
                "No tengo una respuesta previa clara en esta conversacion actual para reformularla.",
            )
        response, rephrased_snapshot = _format_rephrased_summary(snapshot, parsed_query.get("rephrase_style"))
        parsed_query["_adaptive_degraded"] = bool(rephrased_snapshot.get("degraded"))
        parsed_query["_adaptive_transform_type"] = rephrased_snapshot.get("transform_type", "rephrased")
        _store_response_snapshot(parsed_query, rephrased_snapshot)
        return response

    if parsed_query.get("intent") == "get_client_facing_summary":
        if not snapshot:
            return _abort_with_context(
                parsed_query,
                "No tengo una respuesta previa clara en esta conversacion actual para traducirla a una version para cliente.",
            )
        response, client_snapshot = _format_client_facing_summary(context, snapshot)
        parsed_query["_adaptive_output_mode"] = "client_facing"
        parsed_query["_adaptive_degraded"] = bool(client_snapshot.get("degraded"))
        parsed_query["_adaptive_transform_type"] = client_snapshot.get("transform_type", "client_facing")
        _store_response_snapshot(parsed_query, client_snapshot)
        return response

    return _abort_with_context(parsed_query, "No pude interpretar ese follow-up conversacional con seguridad.")


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

    resolver_payload = parsed_query
    if intent in {"create_task", "create_followup"}:
        resolver_payload = dict(parsed_query)
        resolver_payload.pop("task_name", None)
        if not any([resolver_payload.get("project_name"), resolver_payload.get("client_name"), resolver_payload.get("entity_hint")]):
            context = conversation_context or {}
            if isinstance(context, dict) and context.get("_isolated"):
                if context.get("project", {}).get("name"):
                    resolver_payload["project_name"] = context["project"]["name"]
                elif context.get("client", {}).get("name"):
                    resolver_payload["client_name"] = context["client"]["name"]

    resolved = resolve_references(
        resolver_payload,
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


def _format_advanced_task_summary(summary: dict, advanced_summary: dict) -> str:
    lines = [f"Resumen de la tarea {summary['task_id']}:"]
    lines.append(f"Titulo: {summary['title']}")
    lines.append(f"Cliente: {summary['client_name']}")
    lines.append(f"Proyecto: {summary['project_name']}")
    lines.append(f"Estado general: {advanced_summary['status_overview']}")
    _append_operational_sections(lines, advanced_summary)
    return "\n".join(lines)


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


def _format_advanced_project_summary(summary: dict, advanced_summary: dict) -> str:
    lines = [f"Resumen del proyecto {summary['project_name']}:"]
    lines.append(f"Cliente: {summary['client_name']}")
    lines.append(f"Estado general: {advanced_summary['status_overview']}")
    _append_operational_sections(lines, advanced_summary)
    return "\n".join(lines)


def _format_advanced_client_summary(advanced_summary: dict) -> str:
    lines = [f"Resumen del cliente {advanced_summary['entity_name']}:"]
    lines.append(f"Estado general: {advanced_summary['status_overview']}")
    _append_operational_sections(lines, advanced_summary)
    return "\n".join(lines)


def _format_task_friction_summary(summary: dict, friction_summary: dict) -> str:
    lines = [f"Lo que me preocuparia de la tarea {summary['title']}:"] 
    lines.append(f"Estado general: {friction_summary['status_overview']}")
    _append_friction_sections(lines, friction_summary)
    return "\n".join(lines)


def _format_project_friction_summary(summary: dict) -> str:
    lines = [f"Lo que me preocuparia del proyecto {summary['entity_name']}:"] 
    lines.append(f"Estado general: {summary['status_overview']}")
    _append_friction_sections(lines, summary)
    return "\n".join(lines)


def _format_client_friction_summary(summary: dict) -> str:
    lines = [f"Lo que me preocuparia de {summary['entity_name']}:"] 
    lines.append(f"Estado general: {summary['status_overview']}")
    _append_friction_sections(lines, summary)
    return "\n".join(lines)


def _format_global_friction_summary(task_snapshot: dict, project_snapshot: dict, client_snapshot: dict) -> str:
    lines = ["Lo que hoy muestra mas estancamiento o friccion es:"]
    lines.append(f"Estado general: {task_snapshot['status_overview']}")

    if task_snapshot["friction_tasks"]:
        lines.append("Tareas destacadas por friccion:")
        for item in task_snapshot["friction_tasks"][:5]:
            lines.append(_format_friction_item(item))

    if project_snapshot["prioritized_projects"]:
        lines.append("Proyectos con mas friccion:")
        for item in project_snapshot["prioritized_projects"][:3]:
            lines.append(
                f"- {item['project_name']} ({item['client_name']}) | Friccion: {item['friction_tasks']} | Bloqueadas: {item['blocked_tasks']} | Sin next_action: {item['without_next_action']}"
            )

    if client_snapshot["prioritized_clients"]:
        lines.append("Clientes que merecen atencion:")
        for item in client_snapshot["prioritized_clients"][:3]:
            lines.append(
                f"- {item['client_name']} | Friccion: {item['friction_tasks']} | Senales fuertes: {item['strong_stall_signals']}"
            )

    lines.append(f"Recomendacion: {task_snapshot['recommendation']}")
    return "\n".join(lines)


def _format_task_recommendation_summary(summary: dict, recommendation_summary: dict) -> str:
    lines = [f"Lo que yo haria con la tarea {summary['title']}:"] 
    lines.append(f"Estado general: {recommendation_summary['status_overview']}")
    _append_recommendation_sections(lines, recommendation_summary)
    return "\n".join(lines)


def _format_scoped_recommendation_summary(summary: dict) -> str:
    scope = summary.get("scope")
    entity_name = summary.get("entity_name")
    if scope == "project":
        lines = [f"Lo que priorizaria en el proyecto {entity_name}:"] 
    else:
        lines = [f"Lo que yo haria con {entity_name}:"] 
    lines.append(f"Estado general: {summary['status_overview']}")
    _append_recommendation_sections(lines, summary)
    return "\n".join(lines)


def _format_global_recommendation_summary(task_snapshot: dict, project_snapshot: dict, client_snapshot: dict, *, focus: str) -> str:
    if focus == "unblock":
        lines = ["Lo que yo atacaria primero para destrabar mas ahora es:"]
    elif focus == "close":
        lines = ["Lo que mas conviene empujar para cerrar hoy es:"]
    else:
        lines = ["Lo que yo haria primero ahora es:"]

    lines.append(f"Estado general: {task_snapshot['status_overview']}")
    _append_recommendation_sections(lines, task_snapshot)

    if project_snapshot["prioritized_projects"]:
        lines.append("Proyectos donde pondria foco despues:")
        for item in project_snapshot["prioritized_projects"][:2]:
            lines.append(
                f"- {item['project_name']} ({item['client_name']}) | Score: {item['score']} | Mejor foco: {item['top_recommendation'] or 'Sin tarea dominante'}"
            )

    if client_snapshot["prioritized_clients"]:
        top_client = client_snapshot["prioritized_clients"][0]
        lines.append(
            f"Cliente donde veo mas impacto operativo: {top_client['client_name']} ({top_client['top_recommendation']})."
        )

    return "\n".join(lines)


def _format_temporal_summary(snapshot: dict, scope_label: str | None = None) -> str:
    items = snapshot.get("matched_items") or []
    time_scope = snapshot.get("time_scope")
    temporal_focus = snapshot.get("temporal_focus")
    scope_prefix = f" dentro de {scope_label}" if scope_label else ""
    label = {
        "today": "vence hoy",
        "tomorrow": "tenes para mañana",
        "this_week": "vence esta semana",
        "overdue": "esta vencido",
        "due_items": "tiene fecha cargada",
    }.get(time_scope, "entra en ese corte temporal")

    if not items:
        followup_note = " en tareas tipo follow-up" if temporal_focus == "followups" else ""
        return f"No veo tareas abiertas que {label}{followup_note}{scope_prefix}."

    lines = [f"Esto es lo que {label}{scope_prefix}:"]
    for item in items[:8]:
        lines.append(
            f"- {item['title']} | Vence: {item['due_date'] or 'Sin fecha'} | Cliente: {item['client_name']} | Proyecto: {item['project_name']}"
        )
    return "\n".join(lines)


def _format_missing_due_date_summary(snapshot: dict, scope_label: str | None = None) -> str:
    items = snapshot.get("missing_due_items") or []
    scope_prefix = f" dentro de {scope_label}" if scope_label else ""
    if not items:
        return f"No veo tareas abiertas sin fecha que hoy merezcan una fecha{scope_prefix}."

    lines = [f"Estas tareas no tienen fecha y hoy merecerian una{scope_prefix}:"]
    for item in items[:8]:
        lines.append(_format_snapshot_item(item))
    return "\n".join(lines)


def _format_next_recommendation_followup(snapshot: dict) -> str:
    recommendations = snapshot.get("recommendations") or []
    if len(recommendations) < 2:
        return "Despues de eso, no veo una segunda jugada claramente mas fuerte con los datos actuales."

    second = recommendations[1]
    reasons = ", ".join(second.get("recommendation_reasons", [])) or "impacto operativo"
    lines = [f"Despues de eso, iria con '{second['title']}'."]
    lines.append(f"Porque: {reasons}.")
    if second.get("has_next_action") and second.get("next_action"):
        lines.append(f"Proximo paso: {second['next_action']}.")
    elif second.get("missing_next_action"):
        lines.append("Antes de empujarla, definiria una proxima accion concreta.")
    return "\n".join(lines)


def _format_recommendation_explanation(snapshot: dict) -> str:
    top = (snapshot.get("recommendations") or [None])[0]
    if not top:
        return "No tengo una recomendacion previa concreta para explicar."

    reasons = top.get("recommendation_reasons", [])
    lines = [f"Te dije primero '{top['title']}' por estas razones:"]
    for reason in reasons[:4]:
        lines.append(f"- {reason}")
    if top.get("has_next_action") and top.get("next_action"):
        lines.append(f"Ademas, ya tiene un siguiente paso claro: {top['next_action']}.")
    elif top.get("missing_next_action"):
        lines.append("Y como no tiene proxima accion clara, ordenarla ayuda a bajar friccion rapido.")
    return "\n".join(lines)


def _format_filtered_context_summary(snapshot: dict, filter_mode: str | None) -> tuple[str, dict]:
    items = _snapshot_items(snapshot)
    filtered = [item for item in items if _matches_snapshot_filter(item, filter_mode)]
    label = {
        "critical": "solo lo critico",
        "urgent": "solo lo urgente",
        "blocked": "solo las bloqueadas",
        "risks": "solo los riesgos",
        "next_steps": "solo los proximos pasos",
        "important": "solo lo importante",
    }.get(filter_mode, "este filtro")

    filtered_snapshot = {
        **snapshot,
        "response_kind": "filtered_summary",
        "filter_mode": filter_mode,
        "transform_type": "filtered",
        "items": filtered[:5],
        "highlights": filtered[:5],
        "blockers": [item for item in filtered if item.get("is_blocked")][:5],
        "next_steps": [item for item in filtered if item.get("has_next_action") or item.get("next_action")][:5],
        "degraded": False,
    }

    if not filtered:
        filtered_snapshot["degraded"] = True
        return (f"En el contexto actual no veo elementos que entren en {label}.", filtered_snapshot)

    lines = [f"Te muestro {label} dentro del contexto actual:"]
    for item in filtered[:5]:
        lines.append(_format_snapshot_item(item))
    return "\n".join(lines), filtered_snapshot


def _format_rephrased_summary(snapshot: dict, rephrase_style: str | None) -> tuple[str, dict]:
    entity_name = snapshot.get("entity_name") or "este contexto"
    recommendation = snapshot.get("recommendation") or "No veo una recomendacion principal fuerte con los datos actuales."
    top_items = _snapshot_items(snapshot)[:2]
    top_line = _format_snapshot_item(top_items[0]) if top_items else "- No veo un punto dominante."

    if rephrase_style == "three_lines":
        lines = [
            f"Resumen rapido de {entity_name}: {snapshot.get('status_overview') or 'sin cambios fuertes.'}",
            top_line,
            f"Cierre: {recommendation}",
        ]
        return "\n".join(lines[:3])

    if rephrase_style == "executive":
        lines = [
            f"Version ejecutiva de {entity_name}:",
            f"- Estado: {snapshot.get('status_overview') or 'Sin señal dominante.'}",
            f"- Foco: {top_line.removeprefix('- ')}",
            f"- Decision: {recommendation}",
        ]
        return "\n".join(lines)

    if rephrase_style == "simple":
        lines = [
            f"En simple: con {entity_name}, lo principal es esto.",
            top_line,
            f"Lo que haria es: {recommendation}",
        ]
        return "\n".join(lines)

    lines = [
        f"En corto: {snapshot.get('status_overview') or 'No veo un cambio fuerte.'}",
        f"Principal foco: {top_line.removeprefix('- ')}",
    ]
    return "\n".join(lines)


def _format_client_facing_summary(context: dict, snapshot: dict) -> str:
    entity_name = snapshot.get("entity_name") or context.get(context.get("scope", ""), {}).get("name") or "el tema actual"
    top_items = _snapshot_items(snapshot)[:2]
    lines = [f"Si hoy se lo dijera al cliente sobre {entity_name}, diria algo asi:"]
    lines.append("- Estamos siguiendo los puntos prioritarios y hoy el foco principal esta en ordenar lo mas sensible.")
    if top_items:
        lines.append(f"- El punto mas importante hoy es {top_items[0].get('title', 'el foco principal')} y ya estamos sobre eso.")
    if snapshot.get("recommendation"):
        lines.append(f"- Proximo movimiento interno: {snapshot['recommendation']}")
    return "\n".join(lines)


def _snapshot_brief_points(snapshot: dict, *, include_recommendation: bool = False) -> list[str]:
    points: list[str] = []
    overview = snapshot.get("status_overview")
    if overview:
        points.append(f"- Estado: {overview}")

    top_items = _snapshot_items(snapshot)[:3]
    for item in top_items[:2]:
        points.append(_format_snapshot_item(item))

    next_steps = snapshot.get("next_steps") or []
    if next_steps:
        points.append(f"- Proximo paso: {_format_snapshot_item(next_steps[0]).removeprefix('- ')}")

    if include_recommendation and snapshot.get("recommendation"):
        points.append(f"- Recomendacion: {snapshot['recommendation']}")

    return points


def _format_filtered_context_summary(snapshot: dict, filter_mode: str | None) -> tuple[str, dict]:
    items = _snapshot_items(snapshot)
    filtered = [item for item in items if _matches_snapshot_filter(item, filter_mode)]
    label = {
        "critical": "solo lo critico",
        "urgent": "solo lo urgente",
        "blocked": "solo las bloqueadas",
        "risks": "solo los riesgos",
        "next_steps": "solo los proximos pasos",
        "important": "solo lo importante",
    }.get(filter_mode, "este filtro")

    filtered_snapshot = {
        **snapshot,
        "response_kind": "filtered_summary",
        "filter_mode": filter_mode,
        "transform_type": "filtered",
        "items": filtered[:5],
        "highlights": filtered[:5],
        "blockers": [item for item in filtered if item.get("is_blocked")][:5],
        "next_steps": [item for item in filtered if item.get("has_next_action") or item.get("next_action")][:5],
        "degraded": False,
    }

    if not filtered:
        filtered_snapshot["degraded"] = True
        return (f"En el contexto actual no veo elementos que entren en {label}.", filtered_snapshot)

    lines = [f"Te muestro {label} dentro del contexto actual:"]
    for item in filtered[:5]:
        lines.append(_format_snapshot_item(item))
    return "\n".join(lines), filtered_snapshot


def _format_rephrased_summary(snapshot: dict, rephrase_style: str | None) -> tuple[str, dict]:
    entity_name = snapshot.get("entity_name") or "este contexto"
    recommendation = snapshot.get("recommendation") or "No veo una recomendacion principal fuerte con los datos actuales."
    top_items = _snapshot_items(snapshot)[:3]
    top_line = _format_snapshot_item(top_items[0]) if top_items else "- No veo un punto dominante."
    overview = snapshot.get("status_overview") or "No veo un cambio fuerte."
    blockers = snapshot.get("blockers") or []
    next_steps = snapshot.get("next_steps") or []
    highlights = snapshot.get("highlights") or top_items
    degraded = False

    if rephrase_style == "three_lines":
        lines = [
            f"Resumen rapido de {entity_name}: {snapshot.get('status_overview') or 'sin cambios fuertes.'}",
            top_line,
            f"Cierre: {recommendation}",
        ]
        response = "\n".join(lines[:3])
    elif rephrase_style == "executive":
        lines = [
            f"Version ejecutiva de {entity_name}:",
            f"- Estado: {snapshot.get('status_overview') or 'Sin senal dominante.'}",
            f"- Foco: {top_line.removeprefix('- ')}",
            f"- Decision: {recommendation}",
        ]
        response = "\n".join(lines)
    elif rephrase_style == "tactical":
        lines = [f"Version tactica de {entity_name}:"]
        lines.append(f"- Estado: {overview}")
        if blockers:
            lines.append(f"- Riesgo principal: {_format_snapshot_item(blockers[0]).removeprefix('- ')}")
        if next_steps:
            lines.append(f"- Proximo paso: {_format_snapshot_item(next_steps[0]).removeprefix('- ')}")
        else:
            lines.append("- Proximo paso: no veo uno explicito; conviene definirlo antes de seguir.")
            degraded = True
        lines.append(f"- Prioridad operativa: {recommendation}")
        response = "\n".join(lines)
    elif rephrase_style == "detailed":
        lines = [f"Version con mas detalle de {entity_name}:"]
        lines.append(f"- Estado general: {overview}")
        if highlights:
            lines.append("- Lo mas importante:")
            for item in highlights[:3]:
                lines.append(_format_snapshot_item(item))
        if blockers:
            lines.append("- Riesgos detectados:")
            for item in blockers[:3]:
                lines.append(_format_snapshot_item(item))
        else:
            lines.append("- Riesgos detectados: no veo uno dominante en la respuesta previa.")
            degraded = True
        if next_steps:
            lines.append("- Proximos pasos:")
            for item in next_steps[:3]:
                lines.append(_format_snapshot_item(item))
        else:
            lines.append("- Proximos pasos: no veo uno explicito en la respuesta previa.")
            degraded = True
        lines.append(f"- Recomendacion: {recommendation}")
        response = "\n".join(lines)
    elif rephrase_style == "bullets":
        points = _snapshot_brief_points(snapshot)
        if not points:
            degraded = True
            points = ["- No veo suficiente material estructurado para reformularlo en bullets."]
        response = "\n".join(points[:5])
    elif rephrase_style == "meeting_ready":
        lines = [f"Version para reunion sobre {entity_name}:"]
        lines.extend(_snapshot_brief_points(snapshot, include_recommendation=True)[:4])
        response = "\n".join(lines)
    elif rephrase_style == "personal":
        lines = [f"Para vos sobre {entity_name}:"]
        lines.append(f"- Lo principal ahora es {top_line.removeprefix('- ')}")
        if next_steps:
            lines.append(f"- Lo siguiente que haria es {_format_snapshot_item(next_steps[0]).removeprefix('- ')}")
        else:
            lines.append("- Lo siguiente que haria es definir un proximo paso claro antes de mover mas cosas.")
            degraded = True
        lines.append(f"- Mi lectura operativa: {recommendation}")
        response = "\n".join(lines)
    elif rephrase_style == "simple":
        lines = [
            f"En simple: con {entity_name}, lo principal es esto.",
            top_line,
            f"Lo que haria es: {recommendation}",
        ]
        response = "\n".join(lines)
    else:
        lines = [
            f"En corto: {overview}",
            f"Principal foco: {top_line.removeprefix('- ')}",
        ]
        response = "\n".join(lines)

    rephrased_snapshot = {
        **snapshot,
        "response_kind": "rephrased_summary",
        "transform_type": "rephrased",
        "rephrase_style": rephrase_style or "short",
        "degraded": degraded,
        "recommendation": recommendation,
    }
    return response, rephrased_snapshot


def _format_client_facing_summary(context: dict, snapshot: dict) -> tuple[str, dict]:
    entity_name = snapshot.get("entity_name") or context.get(context.get("scope", ""), {}).get("name") or "el tema actual"
    top_items = _snapshot_items(snapshot)[:2]
    lines = [f"Si hoy se lo dijera al cliente sobre {entity_name}, diria algo asi:"]
    lines.append(f"- Estado general: {snapshot.get('status_overview') or 'Seguimos el tema y el foco esta en lo mas sensible.'}")
    if top_items:
        lines.append(f"- El punto mas importante hoy es {top_items[0].get('title', 'el foco principal')}.")
    degraded = False
    if snapshot.get("next_steps"):
        next_item = snapshot["next_steps"][0]
        lines.append(f"- Proximo paso interno: {next_item.get('next_action') or next_item.get('title', 'seguir el punto principal')}.")
    else:
        lines.append("- Proximo paso interno: no veo uno explicito en la respuesta previa.")
        degraded = True
    client_snapshot = {
        **snapshot,
        "response_kind": "client_facing_summary",
        "transform_type": "client_facing",
        "degraded": degraded,
        "recommendation": snapshot.get("recommendation"),
    }
    return "\n".join(lines), client_snapshot


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


def _append_operational_sections(lines: list[str], advanced_summary: dict) -> None:
    if advanced_summary.get("important_pending"):
        lines.append("Pendientes importantes:")
        for item in advanced_summary["important_pending"][:3]:
            lines.append(_format_operational_item(item))

    if advanced_summary.get("risk_items"):
        lines.append("Bloqueos o riesgos:")
        for item in advanced_summary["risk_items"][:3]:
            lines.append(_format_operational_item(item))

    attention_items = advanced_summary.get("attention_items") or []
    if attention_items:
        lines.append("Merece atencion:")
        for item in attention_items[:3]:
            lines.append(_format_operational_item(item))

    next_steps = advanced_summary.get("next_steps") or []
    if next_steps:
        lines.append("Proximos pasos relevantes:")
        for item in next_steps[:3]:
            lines.append(_format_operational_item(item))
    else:
        lines.append("Proximos pasos relevantes: no veo un proximo paso explicito en los datos actuales.")

    recommendation = advanced_summary.get("recommendation")
    if recommendation:
        lines.append(f"Recomendacion: {recommendation}")


def _append_friction_sections(lines: list[str], summary: dict) -> None:
    signals = summary.get("signals") or []
    if signals:
        lines.append("Senales de friccion:")
        for item in signals[:4]:
            lines.append(_format_friction_item(item))
    else:
        lines.append("Senales de friccion: no veo una senal fuerte con los datos actuales.")

    recommendation = summary.get("recommendation")
    if recommendation:
        lines.append(f"Recomendacion: {recommendation}")


def _append_recommendation_sections(lines: list[str], summary: dict) -> None:
    recommendations = summary.get("recommendations") or []
    if recommendations:
        lines.append("Recomendaciones concretas:")
        labels = ("Primero", "Como segunda opcion", "Como tercera opcion")
        for index, item in enumerate(recommendations[:3]):
            lines.append(_format_recommendation_item(item, prefix=labels[index]))
    else:
        lines.append("Recomendaciones concretas: no veo una recomendacion fuerte con los datos actuales.")

    recommendation = summary.get("recommendation")
    if recommendation:
        lines.append(f"Recomendacion principal: {recommendation}")


def _format_recommendation_item(item: dict, prefix: str) -> str:
    reasons = ", ".join(item.get("recommendation_reasons", [])) or "impacto operativo"
    line = f"- {prefix}: {item['title']}"
    if item.get("project_name") and item.get("project_name") != "Sin proyecto":
        line += f" | Proyecto: {item['project_name']}"
    if item.get("client_name") and item.get("client_name") != "Desconocido":
        line += f" | Cliente: {item['client_name']}"
    line += f" | Porque: {reasons}"
    if item.get("has_next_action") and item.get("next_action"):
        line += f" | Proximo paso: {item['next_action']}"
    elif item.get("missing_next_action"):
        line += " | Recomendacion conservadora: definir proxima accion"
    return line


def _format_snapshot_item(item: dict) -> str:
    title = item.get("title") or item.get("name") or "item"
    line = f"- {title}"
    if item.get("project_name") and item.get("project_name") != "Sin proyecto":
        line += f" | Proyecto: {item['project_name']}"
    if item.get("client_name") and item.get("client_name") != "Desconocido":
        line += f" | Cliente: {item['client_name']}"
    reasons = item.get("recommendation_reasons") or item.get("friction_signals") or []
    if reasons:
        line += f" | {'; '.join(reasons[:3])}"
    elif item.get("status") or item.get("priority"):
        line += f" | Estado: {item.get('status', 'n/d')} | Prioridad: {item.get('priority', 'n/d')}"
    if item.get("has_next_action") and item.get("next_action"):
        line += f" | Proximo paso: {item['next_action']}"
    elif item.get("missing_next_action"):
        line += " | Sin proxima accion definida"
    return line


def _snapshot_items(snapshot: dict) -> list[dict]:
    items = []
    for key in ("recommendations", "blockers", "highlights", "items", "signals", "next_steps"):
        values = snapshot.get(key) or []
        for item in values:
            if isinstance(item, dict):
                items.append(item)
    deduped: list[dict] = []
    seen: set[tuple] = set()
    for item in items:
        key = (
            item.get("task_id"),
            item.get("title"),
            item.get("project_name"),
            item.get("client_name"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _matches_snapshot_filter(item: dict, filter_mode: str | None) -> bool:
    if filter_mode == "blocked":
        return bool(item.get("is_blocked")) or "bloqueada" in " ".join(item.get("friction_signals", []))
    if filter_mode == "risks":
        return bool(
            item.get("is_blocked")
            or item.get("has_strong_stall_signal")
            or item.get("friction_signals")
            or item.get("is_overdue")
        )
    if filter_mode == "next_steps":
        return bool(item.get("has_next_action") or item.get("next_action"))
    if filter_mode == "urgent":
        return bool(item.get("is_urgent") or item.get("is_overdue") or item.get("is_due_today") or item.get("is_high_priority") or item.get("is_blocked"))
    if filter_mode == "critical":
        return bool(
            item.get("is_blocked")
            or item.get("is_high_priority")
            or item.get("is_overdue")
            or item.get("has_strong_stall_signal")
            or item.get("recommendation_score", 0) >= 120
        )
    if filter_mode == "important":
        return bool(
            item.get("is_blocked")
            or item.get("is_high_priority")
            or item.get("is_overdue")
            or item.get("recommendation_score", 0) >= 90
            or item.get("has_next_action")
        )
    return True


def _format_operational_item(item) -> str:
    if isinstance(item, str):
        return f"- {item}"

    reason = _operational_reason_label(item)
    line = f"- {item['title']}"
    if item.get("project_name") and item.get("project_name") != "Sin proyecto":
        line += f" | Proyecto: {item['project_name']}"
    if item.get("client_name") and item.get("client_name") != "Desconocido":
        line += f" | Cliente: {item['client_name']}"
    if reason:
        line += f" | {reason}"
    if item.get("has_next_action") and item.get("next_action"):
        line += f" | Proximo paso: {item['next_action']}"
    elif item.get("missing_next_action"):
        line += " | Sin proxima accion definida"
    return line


def _format_friction_item(item) -> str:
    if isinstance(item, str):
        return f"- {item}"
    signals = ", ".join(item.get("friction_signals", [])) or "friccion probable"
    line = f"- {item['title']}"
    if item.get("project_name") and item.get("project_name") != "Sin proyecto":
        line += f" | Proyecto: {item['project_name']}"
    if item.get("client_name") and item.get("client_name") != "Desconocido":
        line += f" | Cliente: {item['client_name']}"
    line += f" | Senales: {signals}"
    return line


def _operational_reason_label(item: dict) -> str:
    reasons = []
    if item.get("is_blocked"):
        reasons.append("bloqueada")
    if item.get("is_high_priority"):
        reasons.append("alta prioridad")
    if item.get("is_overdue"):
        reasons.append("vencida")
    if item.get("is_due_today"):
        reasons.append("vence hoy")
    return ", ".join(reasons)


def _abort_with_context(parsed_query: dict, message: str) -> str:
    parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
    return message


def _attach_operational_summary_debug(parsed_query: dict, advanced_summary: dict, scope_override: str | None = None) -> None:
    parsed_query["_summary_scope"] = scope_override or advanced_summary.get("scope")
    parsed_query["_summary_heuristic"] = advanced_summary.get("heuristic", [])
    parsed_query["_summary_highlights"] = [_debug_summary_item(item) for item in advanced_summary.get("important_pending", [])[:3]]
    parsed_query["_summary_blockers"] = [_debug_summary_item(item) for item in advanced_summary.get("risk_items", [])[:3]]
    parsed_query["_summary_next_steps"] = [_debug_summary_item(item) for item in advanced_summary.get("next_steps", [])[:3]]
    parsed_query["_summary_recommendation"] = advanced_summary.get("recommendation")
    _store_response_snapshot(
        parsed_query,
        {
            "response_kind": "summary",
            "scope": scope_override or advanced_summary.get("scope"),
            "entity_name": advanced_summary.get("entity_name"),
            "status_overview": advanced_summary.get("status_overview"),
            "highlights": advanced_summary.get("important_pending", [])[:3],
            "blockers": advanced_summary.get("risk_items", [])[:3],
            "next_steps": advanced_summary.get("next_steps", [])[:3],
            "recommendation": advanced_summary.get("recommendation"),
            "items": advanced_summary.get("attention_items", [])[:3],
        },
    )


def _attach_friction_debug(parsed_query: dict, summary: dict, scope_override: str | None = None) -> None:
    parsed_query["_friction_scope"] = scope_override or summary.get("scope")
    parsed_query["_friction_heuristic"] = summary.get("heuristic", [])
    parsed_query["_friction_signals"] = [_debug_summary_item(item) for item in summary.get("signals", [])[:5]]
    parsed_query["_friction_entities"] = [_debug_summary_item(item) for item in summary.get("signals", [])[:5]]
    parsed_query["_friction_recommendation"] = summary.get("recommendation")
    _store_response_snapshot(
        parsed_query,
        {
            "response_kind": "friction",
            "scope": scope_override or summary.get("scope"),
            "entity_name": summary.get("entity_name"),
            "status_overview": summary.get("status_overview"),
            "signals": summary.get("signals", [])[:5],
            "blockers": summary.get("signals", [])[:5],
            "recommendation": summary.get("recommendation"),
            "items": summary.get("signals", [])[:5],
        },
    )


def _attach_recommendation_debug(parsed_query: dict, summary: dict, scope_override: str | None = None) -> None:
    parsed_query["_recommendation_scope"] = scope_override or summary.get("scope")
    parsed_query["_recommendation_heuristic"] = summary.get("heuristic", [])
    parsed_query["_recommendation_candidates"] = [_debug_summary_item(item) for item in summary.get("recommendations", [])[:3]]
    parsed_query["_recommendation_reasons"] = [item.get("recommendation_reasons", []) for item in summary.get("recommendations", [])[:3]]
    parsed_query["_recommendation_result"] = summary.get("recommendation")
    _store_response_snapshot(
        parsed_query,
        {
            "response_kind": "recommendation",
            "scope": scope_override or summary.get("scope"),
            "entity_name": summary.get("entity_name"),
            "status_overview": summary.get("status_overview"),
            "recommendations": summary.get("recommendations", [])[:3],
            "recommendation": summary.get("recommendation"),
            "items": summary.get("recommendations", [])[:3],
        },
    )


def _attach_temporal_debug(
    parsed_query: dict,
    snapshot: dict,
    *,
    interpretation: str,
    scope_override: str | None = None,
) -> None:
    items = snapshot.get("matched_items") or snapshot.get("missing_due_items") or []
    parsed_query["_temporal_interpretation"] = interpretation
    parsed_query["_temporal_scope"] = scope_override or snapshot.get("time_scope")
    parsed_query["_temporal_result"] = {
        "time_scope": snapshot.get("time_scope"),
        "temporal_focus": snapshot.get("temporal_focus"),
        "today": snapshot.get("today"),
    }
    parsed_query["_temporal_degraded"] = bool(snapshot.get("degraded"))
    parsed_query["_temporal_due_items"] = [_debug_summary_item(item) for item in items[:5]]
    parsed_query["_temporal_missing_due_items"] = [_debug_summary_item(item) for item in snapshot.get("missing_due_items", [])[:5]]
    _store_response_snapshot(
        parsed_query,
        {
            "response_kind": "temporal",
            "scope": scope_override or "none",
            "entity_name": snapshot.get("entity_name"),
            "status_overview": f"Temporal: {snapshot.get('time_scope') or interpretation}",
            "items": items[:5],
            "highlights": items[:5],
            "next_steps": [item for item in items if item.get("has_next_action")][:3],
            "blockers": [item for item in items if item.get("is_blocked")][:3],
            "recommendation": None,
        },
    )


def _debug_summary_item(item):
    if isinstance(item, str):
        return item
    return {
        "title": item.get("title"),
        "client_name": item.get("client_name"),
        "project_name": item.get("project_name"),
        "next_action": item.get("next_action"),
        "status": item.get("status"),
        "priority": item.get("priority"),
        "friction_signals": item.get("friction_signals"),
    }


def _store_response_snapshot(parsed_query: dict, snapshot: dict) -> None:
    parsed_query["_response_snapshot"] = snapshot
    context = parsed_query.get("_conversation_context")
    if not isinstance(context, dict):
        context = _base_conversation_context(parsed_query, snapshot.get("scope", "none"))
    context["response_snapshot"] = snapshot
    context["last_response_kind"] = snapshot.get("response_kind")
    parsed_query["_conversation_context"] = context


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

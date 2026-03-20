from datetime import date, datetime

from app.services.client_service import get_active_clients
from app.services.conversation_service import (
    get_conversations_for_today,
    get_last_conversation,
)
from app.services.agenda_service import (
    create_agenda_item_conversational,
    delete_agenda_item_conversational,
    get_all_agenda_items,
    get_agenda_items_between_dates,
    get_agenda_items_for_date,
    resolve_agenda_date_hint,
    resolve_agenda_time_hint,
    update_agenda_item_conversational,
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
    "compound_query",
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

AUDIT_INTENTS = {
    "get_audit_trace_summary",
}

AGENDA_CREATION_INTENTS = {
    "create_agenda_item",
}

AGENDA_UPDATE_INTENTS = {
    "update_agenda_item",
}

AGENDA_DELETE_INTENTS = {
    "delete_agenda_item",
}

AGENDA_QUERY_INTENTS = {
    "get_agenda_items_summary",
}

UNSAFE_COMPOUND_INTENTS = CREATION_INTENTS | TASK_UPDATE_INTENTS | {
    "add_task_update",
    "add_task_update_by_name",
}


def build_response_from_query(
    parsed_query: dict,
    user_query: str | None = None,
    conversation_context: dict | None = None,
) -> str:
    parsed_query["_last_user_query"] = user_query
    intent = parsed_query.get("intent")
    if intent == "compound_query":
        return _handle_compound_query(
            parsed_query,
            user_query=user_query,
            conversation_context=conversation_context,
        )

    if intent in AGENDA_CREATION_INTENTS:
        return _handle_agenda_creation_intent(parsed_query, conversation_context=conversation_context)

    if intent in AGENDA_UPDATE_INTENTS:
        return _handle_agenda_update_intent(
            parsed_query,
            user_query=user_query,
            conversation_context=conversation_context,
        )

    if intent in AGENDA_DELETE_INTENTS:
        return _handle_agenda_delete_intent(
            parsed_query,
            user_query=user_query,
            conversation_context=conversation_context,
        )

    if intent in AGENDA_QUERY_INTENTS:
        return _handle_agenda_query_intent(
            parsed_query,
            user_query=user_query,
            conversation_context=conversation_context,
        )

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

    if intent in AUDIT_INTENTS:
        return _handle_audit_trace_intent(
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

    if intent == "get_active_projects":
        projects = [project for project in get_all_projects() if getattr(project, "status", None) == "activo"]
        parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "none")
        if not projects:
            return "No encontre proyectos activos en este momento."

        lines = ["Estos son los proyectos activos que veo hoy:"]
        for project in projects[:10]:
            client_name = getattr(getattr(project, "client", None), "name", None) or "Desconocido"
            lines.append(f"- {project.name} | Cliente: {client_name} | Estado: {project.status}")
        return "\n".join(lines)

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
        return f"Listo: registre un update nuevo en la tarea {task_id}."

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
        return f"Listo: agregue un update a la tarea '{task['name']}'."

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


def _handle_agenda_creation_intent(parsed_query: dict, *, conversation_context: dict | None) -> str:
    title = (parsed_query.get("agenda_title") or "").strip()
    if not title:
        return _abort_with_context(parsed_query, "Necesito el contenido del evento o recordatorio para agendarlo.")

    date_resolution = resolve_agenda_date_hint(parsed_query.get("agenda_date_hint"), today=date.today())
    if not date_resolution.get("resolved"):
        return _abort_with_context(parsed_query, "Necesito una fecha clara para agendar eso con seguridad.")
    if date_resolution.get("scope") == "this_week":
        return _abort_with_context(parsed_query, "Puedo guardar agenda personal con un dia concreto. Decime que dia de la semana queres usar.")

    time_hint = parsed_query.get("agenda_time_hint")
    time_resolution = resolve_agenda_time_hint(time_hint)
    if time_hint and not time_resolution.get("resolved"):
        return _abort_with_context(parsed_query, "No pude interpretar la hora con suficiente claridad.")

    kind = parsed_query.get("agenda_kind") or "event"
    result = create_agenda_item_conversational(
        title,
        scheduled_date=date_resolution["target_date"],
        scheduled_time=time_resolution.get("scheduled_time"),
        kind=kind,
    )
    if not result.get("created"):
        return _abort_with_context(parsed_query, "No pude guardar ese item de agenda.")

    parsed_query["_conversation_context"] = {
        **_base_conversation_context(parsed_query, "agenda"),
        "agenda_context": {
            "query_scope": "created_item",
            "agenda_item_id": result["agenda_item_id"],
            "anchor_date": result["scheduled_date"].isoformat(),
            "anchor_time": result["scheduled_time"].strftime("%H:%M") if result.get("scheduled_time") else None,
            "kind": result["kind"],
            "title": result["title"],
        },
    }

    kind_label = "recordatorio" if result["kind"] == "reminder" else "evento"
    parts = [
        f"Listo: guarde el {kind_label} '{result['title']}'.",
        f"Fecha: {result['scheduled_date'].isoformat()}.",
    ]
    if result.get("scheduled_time"):
        parts.append(f"Hora: {result['scheduled_time'].strftime('%H:%M')}.")
    response = " ".join(parts)
    _set_audit_trace(
        parsed_query,
        user_query=parsed_query.get("_last_user_query"),
        response=response,
        action_status="executed",
        action_type=f"agenda_{result['kind']}",
        affected_entity={"scope": "agenda", "id": result["agenda_item_id"], "name": result["title"]},
    )
    return response


def _handle_agenda_update_intent(
    parsed_query: dict,
    *,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    target = _resolve_agenda_target(parsed_query, conversation_context=conversation_context)
    if target.get("status") != "resolved":
        return _respond_for_agenda_target_resolution(parsed_query, target, action_text="reprogramar")

    current_item = target["item"]
    new_date_hint = parsed_query.get("agenda_new_date_hint")
    new_time_hint = parsed_query.get("agenda_new_time_hint")

    resolved_date = current_item.scheduled_date
    if new_date_hint:
        date_resolution = resolve_agenda_date_hint(new_date_hint, today=date.today())
        if not date_resolution.get("resolved") or not date_resolution.get("target_date"):
            return _abort_with_context(parsed_query, "Necesito una fecha nueva clara para reprogramar eso.")
        resolved_date = date_resolution["target_date"]

    if new_time_hint is None:
        resolved_time = current_item.scheduled_time
    else:
        time_resolution = resolve_agenda_time_hint(new_time_hint)
        if not time_resolution.get("resolved"):
            return _abort_with_context(parsed_query, "Necesito una hora nueva clara para reprogramar eso.")
        resolved_time = time_resolution.get("scheduled_time")

    if resolved_date == current_item.scheduled_date and resolved_time == current_item.scheduled_time:
        return _abort_with_context(parsed_query, "No vi un cambio real de fecha u hora para aplicar en la agenda.")

    result = update_agenda_item_conversational(
        current_item.id,
        scheduled_date=resolved_date,
        scheduled_time=resolved_time,
    )
    if not result.get("updated"):
        return _abort_with_context(parsed_query, "No pude reprogramar ese item de agenda.")

    parsed_query["_conversation_context"] = _build_agenda_item_context(
        parsed_query,
        result,
        query_scope="updated_item",
    )
    response = (
        f"Listo: reprograme '{result['title']}'. "
        f"Nueva fecha: {result['scheduled_date'].isoformat()}. "
        f"Nueva hora: {result['scheduled_time'].strftime('%H:%M') if result.get('scheduled_time') else 'sin hora'}."
    )
    _set_audit_trace(
        parsed_query,
        user_query=user_query,
        response=response,
        action_status="executed",
        action_type="agenda_update",
        affected_entity={"scope": "agenda", "id": result["agenda_item_id"], "name": result["title"]},
    )
    return response


def _handle_agenda_delete_intent(
    parsed_query: dict,
    *,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    target = _resolve_agenda_target(parsed_query, conversation_context=conversation_context)
    if target.get("status") != "resolved":
        return _respond_for_agenda_target_resolution(parsed_query, target, action_text="borrar")

    current_item = target["item"]
    result = delete_agenda_item_conversational(current_item.id)
    if not result.get("deleted"):
        return _abort_with_context(parsed_query, "No pude borrar ese item de agenda.")

    parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, "agenda")
    response = f"Listo: elimine '{result['title']}' de tu agenda."
    _set_audit_trace(
        parsed_query,
        user_query=user_query,
        response=response,
        action_status="executed",
        action_type="agenda_delete",
        affected_entity={"scope": "agenda", "id": result["agenda_item_id"], "name": result["title"]},
    )
    return response


def _resolve_agenda_target(parsed_query: dict, *, conversation_context: dict | None) -> dict:
    context = conversation_context or {}
    agenda_context = context.get("agenda_context") if isinstance(context, dict) and context.get("_isolated") else {}
    all_items = get_all_agenda_items()

    if parsed_query.get("agenda_use_context") and isinstance(agenda_context, dict):
        context_item_id = agenda_context.get("agenda_item_id")
        context_title = agenda_context.get("title")
        context_date = agenda_context.get("anchor_date")
        context_time = agenda_context.get("anchor_time")
        for item in all_items:
            if context_item_id and str(item.id) == str(context_item_id):
                return {"status": "resolved", "item": item}
            if context_title and item.title.lower() == str(context_title).lower():
                if not context_date or item.scheduled_date.isoformat() == context_date:
                    if not context_time or (
                        item.scheduled_time and item.scheduled_time.strftime("%H:%M") == context_time
                    ):
                        return {"status": "resolved", "item": item}

    target_title = (parsed_query.get("agenda_target_title") or "").strip().lower()
    target_kind = parsed_query.get("agenda_target_kind")
    target_date_hint = parsed_query.get("agenda_target_date_hint")
    target_time_hint = parsed_query.get("agenda_target_time_hint")

    target_date = None
    if target_date_hint:
        date_resolution = resolve_agenda_date_hint(target_date_hint, today=date.today())
        if date_resolution.get("resolved"):
            target_date = date_resolution.get("target_date")

    target_time = None
    if target_time_hint:
        time_resolution = resolve_agenda_time_hint(target_time_hint)
        if time_resolution.get("resolved"):
            target_time = time_resolution.get("scheduled_time")

    candidates = []
    for item in all_items:
        score = 0
        if target_kind and getattr(item, "kind", None) != target_kind:
            continue
        if target_title:
            normalized_title = str(getattr(item, "title", "")).lower()
            if target_title == normalized_title:
                score += 5
            elif target_title in normalized_title:
                score += 3
            else:
                continue
        if target_date:
            if getattr(item, "scheduled_date", None) == target_date:
                score += 3
            else:
                continue
        if target_time:
            if getattr(item, "scheduled_time", None) == target_time:
                score += 2
            else:
                continue
        if score > 0:
            candidates.append((score, item))

    candidates.sort(key=lambda entry: (-entry[0], entry[1].scheduled_date, entry[1].scheduled_time or datetime.max.time(), entry[1].id))
    if not candidates:
        return {"status": "not_found"}

    best_score = candidates[0][0]
    best_items = [item for score, item in candidates if score == best_score]
    if len(best_items) == 1:
        return {"status": "resolved", "item": best_items[0]}

    return {"status": "ambiguous", "candidates": best_items[:4]}


def _respond_for_agenda_target_resolution(parsed_query: dict, resolution: dict, *, action_text: str) -> str:
    status = resolution.get("status")
    if status == "not_found":
        return _abort_with_context(parsed_query, f"No encontre un evento o recordatorio claro para {action_text}.")

    candidates = resolution.get("candidates") or []
    if candidates:
        lines = [f"Encontre mas de un item posible para {action_text}. Decime cual de estos queres tocar:"]
        for item in candidates[:4]:
            lines.append(f"- {_format_agenda_item_label(item)}")
        return _abort_with_context(parsed_query, "\n".join(lines))

    return _abort_with_context(parsed_query, f"No tengo contexto suficiente para {action_text} ese item de agenda.")


def _build_agenda_item_context(parsed_query: dict, item_data, *, query_scope: str) -> dict:
    if isinstance(item_data, dict):
        agenda_item_id = item_data.get("agenda_item_id")
        title = item_data.get("title")
        scheduled_date = item_data.get("scheduled_date")
        scheduled_time = item_data.get("scheduled_time")
        kind = item_data.get("kind")
    else:
        agenda_item_id = getattr(item_data, "id", None)
        title = getattr(item_data, "title", None)
        scheduled_date = getattr(item_data, "scheduled_date", None)
        scheduled_time = getattr(item_data, "scheduled_time", None)
        kind = getattr(item_data, "kind", None)

    return {
        **_base_conversation_context(parsed_query, "agenda"),
        "agenda_context": {
            "query_scope": query_scope,
            "agenda_item_id": agenda_item_id,
            "anchor_date": scheduled_date.isoformat() if scheduled_date else None,
            "anchor_time": scheduled_time.strftime("%H:%M") if scheduled_time else None,
            "kind": kind,
            "title": title,
        },
    }


def _format_agenda_item_label(item) -> str:
    kind_label = "recordatorio" if getattr(item, "kind", None) == "reminder" else "evento"
    time_label = item.scheduled_time.strftime("%H:%M") if getattr(item, "scheduled_time", None) else "sin hora"
    return f"{item.title} | {kind_label} | {item.scheduled_date.isoformat()} | {time_label}"


def _handle_agenda_query_intent(
    parsed_query: dict,
    *,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    context = conversation_context or {}
    query_scope = parsed_query.get("agenda_query_scope") or "today"
    today = date.today()
    now = datetime.now()

    if query_scope == "after_current":
        agenda_context = context.get("agenda_context") if isinstance(context, dict) and context.get("_isolated") else {}
        anchor_date = agenda_context.get("anchor_date") if isinstance(agenda_context, dict) else None
        anchor_time = agenda_context.get("anchor_time") if isinstance(agenda_context, dict) else None
        target_date = date.fromisoformat(anchor_date) if anchor_date else today
        items = get_agenda_items_for_date(target_date)
        after_time = resolve_agenda_time_hint(anchor_time).get("scheduled_time") if anchor_time else now.time().replace(second=0, microsecond=0)
        filtered = [item for item in items if item.scheduled_time and item.scheduled_time > after_time]
        parsed_query["_agenda_items_for_context"] = filtered
        parsed_query["_conversation_context"] = _build_agenda_context(
            parsed_query,
            query_scope="after_current",
            target_date=target_date,
            anchor_time=after_time.strftime("%H:%M"),
        )
        return _format_agenda_summary_response(
            parsed_query,
            filtered,
            heading=f"Esto te queda despues de las {after_time.strftime('%H:%M')}:",
            empty_message="No te queda nada mas agendado despues de esa hora.",
        )

    date_hint = parsed_query.get("agenda_date_hint") or "hoy"
    date_resolution = resolve_agenda_date_hint(date_hint, today=today)
    if not date_resolution.get("resolved"):
        return _abort_with_context(parsed_query, "No pude ubicar esa fecha en la agenda con suficiente claridad.")

    if query_scope == "this_week":
        items = get_agenda_items_between_dates(date_resolution["start_date"], date_resolution["end_date"])
        parsed_query["_agenda_items_for_context"] = items
        parsed_query["_conversation_context"] = _build_agenda_context(
            parsed_query,
            query_scope="this_week",
            target_date=date_resolution["start_date"],
            anchor_time=None,
        )
        return _format_agenda_summary_response(
            parsed_query,
            items,
            heading="Esto tenes en agenda esta semana:",
            empty_message="No tenes nada agendado para esta semana.",
            include_date=True,
        )

    target_date = date_resolution["target_date"]
    items = get_agenda_items_for_date(target_date)

    if query_scope == "rest_of_day":
        filtered = [item for item in items if item.scheduled_time is None or item.scheduled_time >= now.time()]
        parsed_query["_agenda_items_for_context"] = filtered
        parsed_query["_conversation_context"] = _build_agenda_context(
            parsed_query,
            query_scope="rest_of_day",
            target_date=target_date,
            anchor_time=now.strftime("%H:%M"),
        )
        return _format_agenda_summary_response(
            parsed_query,
            filtered,
            heading="Esto te queda del dia:",
            empty_message="No te queda nada mas en agenda para hoy.",
        )

    if query_scope == "at_time":
        time_resolution = resolve_agenda_time_hint(parsed_query.get("agenda_time_hint"))
        if not time_resolution.get("resolved") or not time_resolution.get("scheduled_time"):
            return _abort_with_context(parsed_query, "Necesito una hora clara para revisar la agenda en ese momento.")
        target_time = time_resolution["scheduled_time"]
        filtered = [item for item in items if item.scheduled_time == target_time]
        parsed_query["_agenda_items_for_context"] = filtered
        parsed_query["_conversation_context"] = _build_agenda_context(
            parsed_query,
            query_scope="at_time",
            target_date=target_date,
            anchor_time=target_time.strftime("%H:%M"),
        )
        return _format_agenda_summary_response(
            parsed_query,
            filtered,
            heading=f"A las {target_time.strftime('%H:%M')} tenes esto:",
            empty_message=f"No tenes nada agendado a las {target_time.strftime('%H:%M')}.",
        )

    parsed_query["_agenda_items_for_context"] = items
    parsed_query["_conversation_context"] = _build_agenda_context(
        parsed_query,
        query_scope=query_scope,
        target_date=target_date,
        anchor_time=None,
    )
    if parsed_query.get("agenda_boolean_query"):
        if items:
            return _format_agenda_summary_response(
                parsed_query,
                items,
                heading=f"Si, para {date_resolution['label']} tenes esto:",
                empty_message=f"No, para {date_resolution['label']} no tenes nada agendado.",
            )
        return _format_agenda_summary_response(
            parsed_query,
            [],
            heading=f"Si, para {date_resolution['label']} tenes esto:",
            empty_message=f"No, para {date_resolution['label']} no tenes nada agendado.",
        )

    heading = {
        "today": "Esto tenes en agenda para hoy:",
        "tomorrow": "Esto tenes en agenda para mañana:",
    }.get(query_scope, "Esto tenes en agenda:")
    empty_message = {
        "today": "No tenes nada agendado para hoy.",
        "tomorrow": "No tenes nada agendado para mañana.",
    }.get(query_scope, "No encontre nada agendado para ese dia.")
    return _format_agenda_summary_response(parsed_query, items, heading=heading, empty_message=empty_message)


def _build_agenda_context(parsed_query: dict, *, query_scope: str, target_date: date, anchor_time: str | None) -> dict:
    context = {
        **_base_conversation_context(parsed_query, "agenda"),
        "agenda_context": {
            "query_scope": query_scope,
            "anchor_date": target_date.isoformat(),
            "anchor_time": anchor_time,
        },
    }
    items = parsed_query.get("_agenda_items_for_context") or []
    if isinstance(items, list) and len(items) == 1:
        item = items[0]
        context["agenda_context"]["agenda_item_id"] = getattr(item, "id", None)
        context["agenda_context"]["title"] = getattr(item, "title", None)
        context["agenda_context"]["kind"] = getattr(item, "kind", None)
    return context


def _format_agenda_summary_response(
    parsed_query: dict,
    items: list,
    *,
    heading: str,
    empty_message: str,
    include_date: bool = False,
) -> str:
    if not items:
        response = empty_message
        parsed_query["_agenda_items_for_context"] = []
        _set_audit_trace(
            parsed_query,
            user_query=parsed_query.get("_last_user_query"),
            response=response,
            action_status="informational",
            action_type="agenda_query",
        )
        return response

    lines = [heading]
    parsed_query["_agenda_items_for_context"] = list(items)
    for item in items:
        time_label = item.scheduled_time.strftime("%H:%M") if item.scheduled_time else "Sin hora"
        kind_label = "Recordatorio" if getattr(item, "kind", "event") == "reminder" else "Evento"
        if include_date:
            lines.append(f"- {item.scheduled_date.isoformat()} | {time_label} | {kind_label} | {item.title}")
        else:
            lines.append(f"- {time_label} | {kind_label} | {item.title}")

    response = "\n".join(lines)
    _set_audit_trace(
        parsed_query,
        user_query=parsed_query.get("_last_user_query"),
        response=response,
        action_status="informational",
        action_type="agenda_query",
    )
    return response


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
            return "No encontre una tarea clara para actualizar."
        if result.get("error") == "invalid_priority":
            return "No pude interpretar la prioridad nueva para esa tarea."
        if result.get("error") == "no_change":
            return f"No hice cambios en '{result.get('task_title', 'la tarea')}'. Ya estaba en '{result.get('new_value')}'."
        return "No pude aplicar ese cambio en la tarea."

    field_labels = {
        "status": "estado",
        "priority": "prioridad",
        "last_note": "ultima nota",
        "next_action": "proxima accion",
    }
    old_value = result.get("old_value") or "vacio"
    new_value = result.get("new_value") or "vacio"

    if result["field"] == "status" and old_value == new_value and result.get("reason"):
        response = f"Listo: la tarea '{result['task_title']}' sigue en estado '{new_value}' y ademas deje la nota '{result['reason']}'."
    else:
        response = f"Listo: actualice la tarea '{result['task_title']}'. {field_labels.get(result['field'], result['field']).capitalize()}: '{old_value}' -> '{new_value}'."

    _set_audit_trace(
        parsed_query,
        user_query=parsed_query.get("_last_user_query"),
        response=response,
        action_status="executed" if result.get("updated") else "degraded",
    )
    return response


def _handle_compound_query(
    parsed_query: dict,
    *,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    subqueries = parsed_query.get("subqueries") or []
    raw_parts = parsed_query.get("compound_parts") or []
    current_context = conversation_context or {}
    sections: list[str] = []
    resolved_parts: list[str] = []
    degraded_parts: list[str] = []
    reused_snapshot = False
    partial_clarification = False

    for index, subquery in enumerate(subqueries[:2]):
        raw_part = raw_parts[index] if index < len(raw_parts) else None
        sub_intent = subquery.get("intent")
        label = "Primero" if index == 0 else "Despues"

        if sub_intent in UNSAFE_COMPOUND_INTENTS:
            degraded_parts.append(sub_intent or "unknown")
            sections.append(
                f"{label}:\nNo ejecute la parte de accion dentro de este pedido compuesto. "
                "Si queres hacer ese cambio, mandamelo en un mensaje separado."
            )
            continue

        snapshot_before = bool((current_context or {}).get("response_snapshot"))
        response = build_response_from_query(
            subquery,
            user_query=raw_part,
            conversation_context=current_context,
        )
        next_context = subquery.get("_conversation_context") or current_context
        if index > 0 and snapshot_before:
            reused_snapshot = True
        current_context = next_context

        if _is_degraded_compound_part(subquery, response):
            degraded_parts.append(sub_intent or "unknown")
        else:
            resolved_parts.append(sub_intent or "unknown")
        if subquery.get("_clarification_needed"):
            partial_clarification = True
        sections.append(f"{label}:\n{response}")

    parsed_query["_conversation_context"] = current_context if current_context else _base_conversation_context(parsed_query, "none")
    parsed_query["_compound_primary_intent"] = subqueries[0].get("intent") if subqueries else None
    parsed_query["_compound_secondary_intent"] = subqueries[1].get("intent") if len(subqueries) > 1 else None
    parsed_query["_compound_resolved_parts"] = resolved_parts
    parsed_query["_compound_degraded_parts"] = degraded_parts
    parsed_query["_compound_reused_snapshot"] = reused_snapshot
    parsed_query["_compound_partial_clarification"] = partial_clarification
    response = _format_compound_response(sections, degraded_parts=degraded_parts)
    _set_audit_trace(
        parsed_query,
        user_query=user_query,
        response=response,
        action_status="degraded" if degraded_parts else "informational",
        action_type="compound_query",
        reason=", ".join(degraded_parts) if degraded_parts else None,
    )
    return response


def _is_degraded_compound_part(parsed_query: dict, response: str) -> bool:
    if parsed_query.get("_clarification_needed"):
        return True
    if parsed_query.get("_security_blocked"):
        return True
    if parsed_query.get("_adaptive_degraded"):
        return True
    if parsed_query.get("_temporal_degraded"):
        return True

    lowered = response.lower()
    return any(
        marker in lowered
        for marker in (
            "no pude",
            "no tengo",
            "necesito",
            "aclares",
            "decime el proyecto",
            "decime el cliente",
        )
    )


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
        return _abort_with_context(parsed_query, "Necesito el contenido de la nota para dejarla en el proyecto.")

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
        return _abort_with_context(parsed_query, "No pude dejar la nota en ese proyecto.")

    parsed_query["_update_type"] = "project_note"
    parsed_query["_update_real"] = True
    parsed_query["_update_result"] = result
    parsed_query["_conversation_context"] = {
        **_base_conversation_context(parsed_query, "project"),
        "project": {"id": project["id"], "name": project["name"]},
    }
    response = f"Listo: agregue una nota al proyecto '{project['name']}'. Nota: '{note_content}'."
    _set_audit_trace(
        parsed_query,
        user_query=parsed_query.get("_last_user_query"),
        response=response,
        action_status="executed",
        action_type="project_note",
        affected_entity={"scope": "project", "id": project["id"], "name": project["name"]},
    )
    return response


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
        f"Listo: cree la tarea nueva '{result['task_title']}'.",
        f"Proyecto: {project['name']}.",
        f"Prioridad: {result['priority']}.",
    ]
    if next_action:
        parts.append(f"Proxima accion inicial: {next_action}.")
    if temporal_resolution.get("due_date"):
        parts.append(f"Vence: {temporal_resolution['due_date'].isoformat()}.")
    if note_content:
        parts.append(f"Nota inicial: {note_content}.")
    response = " ".join(parts)
    _set_audit_trace(
        parsed_query,
        user_query=parsed_query.get("_last_user_query"),
        response=response,
        action_status="executed",
        action_type=parsed_query.get("intent"),
        affected_entity={"scope": "task", "id": result["task_id"], "name": result["task_title"]},
    )
    return response


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

    scoped_response = _build_resolved_temporal_response(parsed_query, resolved_references)
    if scoped_response:
        return scoped_response

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


def _build_resolved_temporal_response(parsed_query: dict, resolved_references: dict) -> str | None:
    if resolved_references.get("clarification_needed") or resolved_references.get("security_blocked"):
        return None

    scope = resolved_references.get("scope")
    if scope == "task" and resolved_references.get("task", {}).get("resolved", {}).get("id"):
        summary = get_task_operational_summary(resolved_references["task"]["resolved"]["id"])
        if not summary:
            return None
        tasks = [_summary_to_task_like(summary)]
        scope_label = resolved_references["task"]["resolved"]["name"]
    elif scope == "project" and resolved_references.get("project", {}).get("resolved", {}).get("id"):
        tasks = get_tasks_by_project_id(resolved_references["project"]["resolved"]["id"])
        scope_label = resolved_references["project"]["resolved"]["name"]
    elif scope == "client" and resolved_references.get("client", {}).get("resolved", {}).get("id"):
        tasks = get_tasks_by_client_id(resolved_references["client"]["resolved"]["id"])
        scope_label = resolved_references["client"]["resolved"]["name"]
    else:
        return None

    intent = parsed_query.get("intent")
    parsed_query["_conversation_context"] = _base_conversation_context(parsed_query, scope)
    if resolved_references.get(scope, {}).get("resolved"):
        parsed_query["_conversation_context"][scope] = {
            "id": resolved_references[scope]["resolved"]["id"],
            "name": resolved_references[scope]["resolved"]["name"],
        }

    if intent == "get_missing_due_date_summary":
        snapshot = build_missing_due_date_snapshot_from_tasks(tasks, today=date.today())
        _attach_temporal_debug(parsed_query, snapshot, scope_override=f"contextual_{scope}", interpretation="missing_due_date")
        return _format_missing_due_date_summary(snapshot, scope_label=scope_label)

    time_scope = "overdue" if intent == "get_overdue_tasks_summary" else (parsed_query.get("time_scope") or "due_items")
    snapshot = build_temporal_task_snapshot_from_tasks(
        tasks,
        time_scope=time_scope,
        today=date.today(),
        temporal_focus=parsed_query.get("temporal_focus"),
    )
    _attach_temporal_debug(parsed_query, snapshot, scope_override=f"contextual_{scope}", interpretation=time_scope)
    return _format_temporal_summary(snapshot, scope_label=scope_label)


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
                _safe_context_message("decirte que sigue", "Si queres, pedi un resumen global de proximos pasos."),
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
            _safe_context_message("interpretar esa referencia corta", "Decime el cliente, proyecto o tarea exacta."),
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
            _safe_context_message("resumir eso", "Decime el cliente, proyecto o tarea exacta."),
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
        "No pude ubicar con claridad que cliente, proyecto o tarea queres resumir.",
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
            "como venimos con esto",
            "como venimos aca",
            "que onda con esto",
            "que onda aca",
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
            _safe_context_message("analizar que esta frenado", "Decime el cliente, proyecto o tarea exacta."),
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

    if (
        parsed_query.get("entity_hint") == "aca"
        and not contextual_scope
        and not any(resolved_references.get(scope, {}).get("resolved") for scope in ("task", "project", "client"))
    ):
        return _abort_with_context(
            parsed_query,
            _safe_context_message("recomendar qué haría ahora", "Primero decime el cliente, proyecto o tarea exacta."),
        )

    if resolved_references.get("security_blocked"):
        return _abort_with_context(
            parsed_query,
            _safe_context_message("recomendar eso", "Decime el cliente, proyecto o tarea exacta."),
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
            "que harias ahora",
            "y ahora que",
            "que conviene",
            "que deberia hacer primero",
            "si fueras yo, que harias",
            "si fueras yo que harias",
            "que me recomendarias hacer ahora",
            "que me recomendarías hacer ahora",
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
            "que haria primero",
            "qué haría primero",
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
            _safe_context_message("continuar esa conversacion"),
        )

    if parsed_query.get("intent") == "get_followup_focus_summary":
        followup_focus = parsed_query.get("followup_focus")
        if followup_focus == "friction":
            response = _build_contextual_friction_summary(parsed_query, context, context.get("scope"))
            if response:
                return response
            return _abort_with_context(parsed_query, "No pude reaprovechar el contexto actual para profundizar en lo que preocupa.")

        if followup_focus == "next_after_recommendation":
            if not snapshot or not snapshot.get("recommendations"):
                return _abort_with_context(
                    parsed_query,
                    "No tengo una recomendacion previa clara en esta conversacion actual para decirte que vendria despues.",
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
                "No tengo una recomendacion previa clara en esta conversacion actual para explicarte por que iria primero.",
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
                "No tengo una respuesta previa clara en esta conversacion actual para filtrarla mejor.",
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
                "No tengo una respuesta previa clara en esta conversacion actual para reformularla mejor.",
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
                "No tengo una respuesta previa clara en esta conversacion actual para llevarla a una version para cliente.",
            )
        response, client_snapshot = _format_client_facing_summary(context, snapshot)
        parsed_query["_adaptive_output_mode"] = "client_facing"
        parsed_query["_adaptive_degraded"] = bool(client_snapshot.get("degraded"))
        parsed_query["_adaptive_transform_type"] = client_snapshot.get("transform_type", "client_facing")
        _store_response_snapshot(parsed_query, client_snapshot)
        return response

    return _abort_with_context(parsed_query, "No pude interpretar ese follow-up con suficiente claridad.")


def _handle_audit_trace_intent(
    parsed_query: dict,
    *,
    user_query: str | None,
    conversation_context: dict | None,
) -> str:
    trace = _get_recent_audit_trace(conversation_context)
    if not trace:
        return _abort_with_context(parsed_query, "No tengo una traza reciente y segura en esta conversacion para auditar ese turno.")

    focus = parsed_query.get("audit_focus") or "recent"
    parsed_query["_audit_focus"] = focus
    parsed_query["_audit_source"] = "current_context"
    parsed_query["_audit_trace"] = trace
    parsed_query["_conversation_context"] = {
        **_base_conversation_context(parsed_query, trace.get("scope") or "none"),
        "audit_trace": trace,
    }

    if focus == "resolution":
        return _format_audit_resolution(trace)
    if focus == "blocked":
        return _format_audit_blocked(trace)
    if focus == "understood":
        return _format_audit_understood(trace)
    if focus == "action":
        return _format_audit_action(trace)
    if focus == "decision_reason":
        return _format_audit_reason(trace)
    return _format_audit_recent(trace)


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
        parsed_query["_expected_scope"] = parsed_query.get("expected_scope")
        parsed_query["_secondary_descriptor"] = parsed_query.get("secondary_descriptor")
        parsed_query["_used_previous_candidates"] = False
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
    parsed_query["_expected_scope"] = parsed_query.get("expected_scope")
    parsed_query["_secondary_descriptor"] = parsed_query.get("secondary_descriptor")
    parsed_query["_used_previous_candidates"] = bool(parsed_query.get("use_previous_candidates")) and bool((conversation_context or {}).get("clarification_candidates"))
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
    candidate_types = resolved_references.get("candidate_types") or []

    if reason == "missing_context":
        return _safe_context_message("resolver esa referencia", "Decime el cliente, proyecto o tarea exacta.")

    if reason == "generic_request":
        return (
            "Necesito un poco mas de precision para ubicarlo bien.\n"
            "Decime si queres ver un cliente, un proyecto o una tarea concreta."
        )

    if not candidates:
        return (
            "No pude ubicar una entidad clara con esa referencia.\n"
            "Proba con el nombre exacto del cliente, proyecto o tarea."
        )

    if len(candidate_types) == 1:
        lines = [prefix or f"Necesito que me aclares cual {_scope_label(candidate_types[0])} queres ver."]
    else:
        lines = [prefix or "Necesito que me aclares un poco mas a que te referis."]
    lines.append("Estas son las coincidencias posibles que mejor matchean:")
    for item in candidates[:4]:
        detail_parts = [_scope_label(item["scope"])]
        if item.get("client_name"):
            detail_parts.append(f"cliente: {item['client_name']}")
        if item.get("project_name"):
            detail_parts.append(f"proyecto: {item['project_name']}")
        lines.append(f"- {item['name']} ({' | '.join(detail_parts)})")
    lines.append("")
    lines.append("Si queres, te lo puedo resumir, marcar lo que preocupa o mostrar proximos pasos del que elijas.")
    return "\n".join(lines)


def _format_ambiguity_message(prefix: str, matches: list[dict]) -> str:
    lines = [prefix, "Podria ser:"]
    for item in matches[:5]:
        lines.append(f"- {item['name']}")
    return "\n".join(lines)


def _safe_context_message(action: str, suggestion: str | None = None) -> str:
    message = f"No tengo contexto aislado actual para {action} con seguridad."
    if suggestion:
        return f"{message} {suggestion}"
    return message


def _format_compound_response(sections: list[str], *, degraded_parts: list[str]) -> str:
    response = "\n\n".join(sections)
    if not degraded_parts or len(degraded_parts) == len(sections):
        return response
    return f"Pude resolver una parte del pedido y la otra la deje aclarada.\n\n{response}"


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
            f"- {item.get('title', 'item')} | Vence: {item.get('due_date') or 'Sin fecha'} | Cliente: {item.get('client_name', 'Desconocido')} | Proyecto: {item.get('project_name', 'Sin proyecto')}"
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
    important_pending = _dedupe_operational_items(advanced_summary.get("important_pending") or [])
    risk_items = _dedupe_operational_items(
        advanced_summary.get("risk_items") or [],
        seen=_operational_seen_keys(important_pending),
    )
    attention_items = _dedupe_operational_items(
        advanced_summary.get("attention_items") or [],
        seen=_operational_seen_keys(important_pending + risk_items),
    )
    next_steps = _dedupe_operational_items(
        advanced_summary.get("next_steps") or [],
        seen=_operational_seen_keys(important_pending + risk_items + attention_items),
    )

    if important_pending:
        lines.append("Pendientes importantes:")
        for item in important_pending[:3]:
            lines.append(_format_operational_item(item))

    if risk_items:
        lines.append("Bloqueos o riesgos:")
        for item in risk_items[:3]:
            lines.append(_format_operational_item(item))
    elif advanced_summary.get("risk_items"):
        lines.append("Bloqueos o riesgos: ya quedaron integrados arriba en las tareas destacadas.")

    if attention_items:
        lines.append("Merece atencion:")
        for item in attention_items[:3]:
            lines.append(_format_operational_item(item))
    elif advanced_summary.get("attention_items"):
        lines.append("Merece atencion: ya quedo sintetizado arriba para evitar repeticion.")

    if next_steps:
        lines.append("Proximos pasos relevantes:")
        for item in next_steps[:3]:
            lines.append(_format_operational_item(item))
    elif advanced_summary.get("next_steps"):
        lines.append("Proximos pasos relevantes: ya quedaron integrados arriba en las tareas destacadas.")
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


def _operational_item_key(item) -> tuple:
    if isinstance(item, str):
        return ("text", item)
    return (
        item.get("task_id"),
        item.get("title"),
        item.get("project_name"),
        item.get("client_name"),
    )


def _operational_seen_keys(items: list) -> set[tuple]:
    return {_operational_item_key(item) for item in items}


def _dedupe_operational_items(items: list, *, seen: set[tuple] | None = None) -> list:
    seen_keys = set(seen or set())
    deduped = []
    for item in items:
        key = _operational_item_key(item)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(item)
    return deduped


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


def _set_audit_trace(
    parsed_query: dict,
    *,
    user_query: str | None,
    response: str,
    action_status: str,
    action_type: str | None = None,
    affected_entity: dict | None = None,
    reason: str | None = None,
    summary: str | None = None,
) -> None:
    resolved = parsed_query.get("_resolved_references", {}) or {}
    trace = {
        "user_query": user_query,
        "intent": parsed_query.get("intent"),
        "sub_intents": [item.get("intent") for item in parsed_query.get("subqueries", [])[:2]],
        "scope": parsed_query.get("_resolver_scope") or parsed_query.get("_summary_scope") or parsed_query.get("_friction_scope") or parsed_query.get("_recommendation_scope") or parsed_query.get("_temporal_scope") or parsed_query.get("_followup_scope") or parsed_query.get("_executive_scope") or resolved.get("scope") or "none",
        "resolved_entities": _audit_resolved_entities(resolved),
        "candidates": parsed_query.get("_clarification_candidates", []),
        "clarification_needed": bool(parsed_query.get("_clarification_needed")),
        "action_type": action_type or _infer_audit_action_type(parsed_query),
        "action_status": action_status,
        "affected_entity": affected_entity or _infer_audit_affected_entity(parsed_query, resolved),
        "reason": reason or _infer_audit_reason(parsed_query),
        "summary": summary or _shorten_text(response),
    }
    parsed_query["_audit_trace"] = trace

    context = parsed_query.get("_conversation_context")
    if not isinstance(context, dict):
        context = _base_conversation_context(parsed_query, trace["scope"])
    context["audit_trace"] = trace
    parsed_query["_conversation_context"] = context


def _audit_resolved_entities(resolved: dict) -> dict:
    items = {}
    for scope in ("client", "project", "task"):
        item = (resolved.get(scope) or {}).get("resolved")
        if item:
            items[scope] = item
    return items


def _infer_audit_action_type(parsed_query: dict) -> str:
    if parsed_query.get("_creation_real"):
        return parsed_query.get("_creation_intent") or "create"
    if parsed_query.get("_update_real"):
        return parsed_query.get("_update_type") or "update"
    if parsed_query.get("_clarification_needed"):
        return "clarification"
    if parsed_query.get("_security_blocked"):
        return "blocked"
    if parsed_query.get("_adaptive_degraded") or parsed_query.get("_temporal_degraded") or parsed_query.get("_creation_aborted"):
        return "degraded"
    return "informational"


def _infer_audit_affected_entity(parsed_query: dict, resolved: dict) -> dict | None:
    if parsed_query.get("_creation_result"):
        result = parsed_query["_creation_result"]
        if isinstance(result, dict):
            if result.get("task_id") or result.get("task_title"):
                return {"scope": "task", "id": result.get("task_id"), "name": result.get("task_title")}
            if result.get("project_id") or result.get("project_name"):
                return {"scope": "project", "id": result.get("project_id"), "name": result.get("project_name")}
    if parsed_query.get("_update_result"):
        result = parsed_query["_update_result"]
        if isinstance(result, dict):
            if result.get("task_id") or result.get("task_title"):
                return {"scope": "task", "id": result.get("task_id"), "name": result.get("task_title")}
    for scope in ("task", "project", "client"):
        item = (resolved.get(scope) or {}).get("resolved")
        if item:
            return {"scope": scope, "id": item.get("id"), "name": item.get("name")}
    return None


def _infer_audit_reason(parsed_query: dict) -> str | None:
    snapshot = parsed_query.get("_response_snapshot")
    if isinstance(snapshot, dict):
        recommendations = snapshot.get("recommendations") or []
        if recommendations:
            top = recommendations[0]
            title = top.get("title") or "esa recomendacion"
            reasons = top.get("recommendation_reasons") or []
            if reasons:
                return f"priorice '{title}' porque " + ", ".join(reasons[:3])
            if top.get("missing_next_action"):
                return f"priorice '{title}' porque necesitaba ordenar una proxima accion clara"

    creation_result = parsed_query.get("_creation_result")
    if isinstance(creation_result, dict) and creation_result.get("error"):
        creation_error = creation_result.get("error")
    else:
        creation_error = None

    compound_degraded = parsed_query.get("_compound_degraded_parts")
    if isinstance(compound_degraded, list) and compound_degraded:
        compound_reason = ", ".join(str(item) for item in compound_degraded)
    else:
        compound_reason = None

    return (
        parsed_query.get("_security_reason")
        or parsed_query.get("_clarification_reason")
        or creation_error
        or compound_reason
    )


def _shorten_text(response: str | None, *, max_lines: int = 3) -> str:
    if not response:
        return ""
    lines = [line.strip() for line in str(response).splitlines() if line.strip()]
    return " ".join(lines[:max_lines])


def _get_recent_audit_trace(conversation_context: dict | None) -> dict | None:
    context = conversation_context or {}
    if isinstance(context, dict) and context.get("_isolated") and isinstance(context.get("audit_trace"), dict):
        return context["audit_trace"]
    return None


def _friendly_audit_entity_name(trace: dict) -> str | None:
    affected = trace.get("affected_entity") or {}
    if affected.get("name"):
        return affected["name"]

    resolved = trace.get("resolved_entities") or {}
    for scope in ("task", "project", "client"):
        item = resolved.get(scope) or {}
        if item.get("name"):
            return item["name"]
    return None


def _friendly_audit_summary(trace: dict) -> str:
    intent = trace.get("intent")
    entity_name = _friendly_audit_entity_name(trace)

    if intent == "get_operational_summary":
        if entity_name:
            return f"Recien te resumi el estado de {entity_name}."
        return "Recien te resumi el estado general."
    if intent == "get_followup_focus_summary":
        if entity_name:
            return f"Recien te marque lo que mas me preocuparia de {entity_name}."
        return "Recien te marque el foco de preocupacion principal."
    if intent == "get_operational_recommendation":
        if entity_name:
            return f"Recien te recomende por donde avanzaria con {entity_name}."
        return "Recien te recomende cual seria la mejor jugada ahora."
    if intent == "get_agenda_items_summary":
        return "Recien te mostre tu agenda personal."
    if intent == "get_due_tasks_summary":
        return "Recien te mostre los vencimientos mas relevantes."
    if intent == "get_overdue_tasks_summary":
        return "Recien te mostre lo que quedo atrasado."
    if intent == "get_audit_trace_summary":
        return "Recien repase lo ultimo que hice en la conversacion."
    return ""


def _friendly_audit_action_label(trace: dict) -> str:
    action_type = trace.get("action_type") or ""
    affected = trace.get("affected_entity") or {}
    affected_name = affected.get("name")

    if action_type in {"create_task", "create_followup"} and affected_name:
        return f"Recien agregue la tarea nueva '{affected_name}'."
    if action_type in {"agenda_event", "agenda_reminder"} and affected_name:
        return f"Recien guarde '{affected_name}' en tu agenda."
    if action_type == "agenda_update" and affected_name:
        return f"Recien reprograme '{affected_name}' en tu agenda."
    if action_type == "agenda_delete" and affected_name:
        return f"Recien elimine '{affected_name}' de tu agenda."
    if action_type == "description" and affected_name:
        return f"Recien actualice el proyecto '{affected_name}'."
    if action_type == "status" and affected_name:
        return f"Recien actualice la tarea '{affected_name}'."
    if action_type == "priority" and affected_name:
        return f"Recien cambie la prioridad de '{affected_name}'."
    if action_type == "next_action" and affected_name:
        return f"Recien deje la proxima accion de '{affected_name}'."
    if action_type == "last_note" and affected_name:
        return f"Recien deje una nota en '{affected_name}'."
    if affected_name:
        return f"Recien hice un cambio sobre '{affected_name}'."
    return "Recien ejecute un cambio operativo."


def _friendly_audit_understood_label(trace: dict) -> str:
    intent = trace.get("intent")
    entity_name = _friendly_audit_entity_name(trace)

    if intent == "get_operational_summary":
        target = f"sobre {entity_name}" if entity_name else "sobre ese tema"
        return f"Entendi que querias un resumen operativo {target}."
    if intent == "get_followup_focus_summary":
        target = f"de {entity_name}" if entity_name else "de ese frente"
        return f"Entendi que querias el foco de preocupacion {target}."
    if intent == "get_operational_recommendation":
        target = f"con {entity_name}" if entity_name else "en este contexto"
        return f"Entendi que querias una recomendacion operativa {target}."
    if intent in {"create_task", "create_followup"}:
        return "Entendi que querias crear trabajo nuevo."
    if intent == "create_agenda_item":
        return "Entendi que querias guardar un evento o recordatorio personal."
    if intent in {"update_agenda_item", "delete_agenda_item"}:
        return "Entendi que querias cambiar un item de tu agenda personal."
    if intent == "get_agenda_items_summary":
        return "Entendi que querias revisar tu agenda personal."
    if intent == "get_due_tasks_summary":
        return "Entendi que querias ver vencimientos."
    if intent == "get_overdue_tasks_summary":
        return "Entendi que querias ver que quedo atrasado."
    return "Entendi el pedido y lo baje a una accion o lectura operativa concreta."


def _format_audit_recent(trace: dict) -> str:
    action_status = trace.get("action_status") or "informational"
    if action_status == "executed":
        base = _friendly_audit_action_label(trace)
        summary = trace.get("summary") or ""
        return f"{base} {summary}".strip()
    if action_status == "blocked":
        return (
            f"Recién te respondí sin ejecutar cambios. Lo frené por {trace.get('reason') or 'seguridad'}. "
            f"{trace.get('summary') or ''}"
        ).strip()
    if action_status == "degraded":
        return (
            f"Recién te respondí de forma parcial. Motivo: {trace.get('reason') or 'falta de contexto o precisión'}. "
            f"{trace.get('summary') or ''}"
        ).strip()

    friendly = _friendly_audit_summary(trace)
    if friendly:
        extra = trace.get("summary") or ""
        if extra and extra not in friendly:
            return f"{friendly} {extra}".strip()
        return friendly
    return f"Recién te respondí esa consulta. {trace.get('summary') or ''}".strip()


def _format_audit_resolution(trace: dict) -> str:
    resolved = trace.get("resolved_entities") or {}
    if not resolved:
        return "En el ultimo turno no llegue a resolver una entidad clara."
    parts = []
    for scope in ("client", "project", "task"):
        item = resolved.get(scope)
        if item:
            parts.append(f"{_scope_label(scope)} {item.get('name')}")
    if len(parts) == 1:
        return f"En el ultimo turno resolví {parts[0]}."
    return "En el ultimo turno resolví " + ", ".join(parts[:-1]) + f" y {parts[-1]}."


def _format_audit_blocked(trace: dict) -> str:
    if trace.get("action_status") != "blocked":
        return "En el ultimo turno no quedo nada bloqueado por seguridad."
    candidates = trace.get("candidates") or []
    lines = [f"En el ultimo turno frene la accion por {trace.get('reason') or 'seguridad'}."]
    if candidates:
        lines.append("Estos eran los candidatos mas probables:")
        for item in candidates[:4]:
            lines.append(f"- {item.get('name')} ({_scope_label(item.get('scope'))})")
    return "\n".join(lines)


def _format_audit_understood(trace: dict) -> str:
    parts = [_friendly_audit_understood_label(trace)]
    if trace.get("sub_intents"):
        parts.append("Además, lo resolví en dos partes compatibles dentro del mismo turno.")
    if trace.get("resolved_entities"):
        parts.append(_format_audit_resolution(trace))
    elif trace.get("candidates"):
        parts.append("No resolví una entidad única; quedé entre varios candidatos y por eso no avancé solo.")
    return " ".join(parts)


def _format_audit_action(trace: dict) -> str:
    if trace.get("action_status") != "executed":
        return "En el ultimo turno no ejecute una accion operativa."
    return _friendly_audit_action_label(trace)


def _format_audit_reason(trace: dict) -> str:
    reason = trace.get("reason")
    if reason:
        return f"La razon principal fue esta: {reason}."
    return f"La razon operativa mas clara que deje fue: {trace.get('summary')}"


def _abort_with_context(parsed_query: dict, message: str) -> str:
    context = _base_conversation_context(parsed_query, "none")
    clarification_candidates = parsed_query.get("_clarification_candidates") or []
    if clarification_candidates:
        context["clarification_candidates"] = clarification_candidates
        context["clarification_reason"] = parsed_query.get("_clarification_reason")
        if parsed_query.get("expected_scope"):
            context["clarification_expected_scope"] = parsed_query.get("expected_scope")
        elif parsed_query.get("_candidate_types") and len(parsed_query["_candidate_types"]) == 1:
            context["clarification_expected_scope"] = parsed_query["_candidate_types"][0]
    parsed_query["_conversation_context"] = context
    action_status = "blocked" if parsed_query.get("_security_blocked") or parsed_query.get("_clarification_needed") else "degraded"
    _set_audit_trace(
        parsed_query,
        user_query=parsed_query.get("_last_user_query"),
        response=message,
        action_status=action_status,
    )
    return message


def _attach_operational_summary_debug(parsed_query: dict, advanced_summary: dict, scope_override: str | None = None) -> None:
    important_pending = _dedupe_operational_items(advanced_summary.get("important_pending", []))
    risk_items = _dedupe_operational_items(advanced_summary.get("risk_items", []), seen=_operational_seen_keys(important_pending))
    attention_items = _dedupe_operational_items(advanced_summary.get("attention_items", []), seen=_operational_seen_keys(important_pending + risk_items))
    next_steps = _dedupe_operational_items(advanced_summary.get("next_steps", []), seen=_operational_seen_keys(important_pending + risk_items + attention_items))

    parsed_query["_summary_scope"] = scope_override or advanced_summary.get("scope")
    parsed_query["_summary_heuristic"] = advanced_summary.get("heuristic", [])
    parsed_query["_summary_highlights"] = [_debug_summary_item(item) for item in important_pending[:3]]
    parsed_query["_summary_blockers"] = [_debug_summary_item(item) for item in risk_items[:3]]
    parsed_query["_summary_next_steps"] = [_debug_summary_item(item) for item in next_steps[:3]]
    parsed_query["_summary_recommendation"] = advanced_summary.get("recommendation")
    _store_response_snapshot(
        parsed_query,
        {
            "response_kind": "summary",
            "scope": scope_override or advanced_summary.get("scope"),
            "entity_name": advanced_summary.get("entity_name"),
            "status_overview": advanced_summary.get("status_overview"),
            "highlights": important_pending[:3],
            "blockers": risk_items[:3],
            "next_steps": next_steps[:3],
            "recommendation": advanced_summary.get("recommendation"),
            "items": attention_items[:3],
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
    _set_audit_trace(
        parsed_query,
        user_query=parsed_query.get("_last_user_query"),
        response=snapshot.get("status_overview") or snapshot.get("recommendation") or snapshot.get("response_kind") or "",
        action_status="executed" if parsed_query.get("_creation_real") or parsed_query.get("_update_real") else "informational",
    )


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

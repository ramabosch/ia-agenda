from datetime import date, timedelta

from app.db.session import SessionLocal
from app.repositories import task_repository, task_update_repository
from app.schemas.enums import TaskPriority


WEEKDAY_INDEX = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}


def create_task(
    project_id: int,
    title: str,
    description: str | None = None,
    priority: str = "media",
    due_date: date | None = None,
    last_note: str | None = None,
    next_action: str | None = None,
):
    db = SessionLocal()
    try:
        return task_repository.create_task(
            db,
            project_id,
            title,
            description,
            priority,
            due_date,
            last_note,
            next_action,
        )
    finally:
        db.close()


def get_all_tasks():
    db = SessionLocal()
    try:
        return task_repository.get_all_tasks(db)
    finally:
        db.close()


def create_task_conversational(
    project_id: int,
    title: str,
    *,
    priority: str = "media",
    description: str | None = None,
    due_date: date | None = None,
    last_note: str | None = None,
    next_action: str | None = None,
):
    db = SessionLocal()
    try:
        task = task_repository.create_task(
            db,
            project_id,
            title.strip(),
            description,
            priority,
            due_date,
            last_note,
            next_action,
        )
        return {
            "created": True,
            "task_id": task.id,
            "task_title": task.title,
            "project_id": task.project_id,
            "field": "task",
            "priority": task.priority,
            "next_action": task.next_action,
            "last_note": task.last_note,
            "task": task,
        }
    finally:
        db.close()


def get_all_tasks_with_relations():
    db = SessionLocal()
    try:
        return task_repository.get_all_tasks_with_relations(db)
    finally:
        db.close()


def get_tasks_by_project(project_id: int):
    db = SessionLocal()
    try:
        return task_repository.get_tasks_by_project(db, project_id)
    finally:
        db.close()


def get_tasks_by_status(status: str):
    db = SessionLocal()
    try:
        return task_repository.get_tasks_by_status(db, status)
    finally:
        db.close()


def get_overdue_tasks(today: date):
    db = SessionLocal()
    try:
        return task_repository.get_overdue_tasks(db, today)
    finally:
        db.close()


def get_tasks_due_today(today: date):
    db = SessionLocal()
    try:
        return task_repository.get_tasks_due_today(db, today)
    finally:
        db.close()


def resolve_due_hint(due_hint: str | None, *, today: date | None = None) -> dict:
    today = today or date.today()
    normalized = _normalize_temporal_text(due_hint)
    if not normalized:
        return {
            "resolved": False,
            "time_scope": None,
            "due_hint": due_hint,
            "due_date": None,
            "label": None,
            "degraded": False,
            "reason": "missing_due_hint",
        }

    if normalized == "hoy":
        return {
            "resolved": True,
            "time_scope": "today",
            "due_hint": due_hint,
            "due_date": today,
            "label": "hoy",
            "degraded": False,
            "reason": None,
        }

    if normalized == "manana":
        return {
            "resolved": True,
            "time_scope": "tomorrow",
            "due_hint": due_hint,
            "due_date": today + timedelta(days=1),
            "label": "mañana",
            "degraded": False,
            "reason": None,
        }

    if normalized in WEEKDAY_INDEX:
        target_weekday = WEEKDAY_INDEX[normalized]
        days_ahead = (target_weekday - today.weekday()) % 7
        due_date = today + timedelta(days=days_ahead)
        return {
            "resolved": True,
            "time_scope": "weekday",
            "due_hint": due_hint,
            "due_date": due_date,
            "label": normalized,
            "degraded": False,
            "reason": None,
        }

    if normalized == "esta semana":
        return {
            "resolved": False,
            "time_scope": "this_week",
            "due_hint": due_hint,
            "due_date": None,
            "label": "esta semana",
            "degraded": True,
            "reason": "range_requires_concrete_day",
        }

    return {
        "resolved": False,
        "time_scope": "ambiguous",
        "due_hint": due_hint,
        "due_date": None,
        "label": due_hint,
        "degraded": True,
        "reason": "unsupported_due_hint",
    }


def update_task_status(task_id: int, new_status: str):
    db = SessionLocal()
    try:
        return task_repository.update_task_status(db, task_id, new_status)
    finally:
        db.close()


def get_task_by_id(task_id: int):
    db = SessionLocal()
    try:
        return task_repository.get_task_by_id(db, task_id)
    finally:
        db.close()


def update_task_context(
    task_id: int,
    last_note: str | None = None,
    next_action: str | None = None,
):
    db = SessionLocal()
    try:
        return task_repository.update_task_context(db, task_id, last_note, next_action)
    finally:
        db.close()

def update_task_main_fields(
    task_id: int,
    title: str,
    description: str | None,
    priority: str,
    due_date: date | None,
):
    db = SessionLocal()
    try:
        return task_repository.update_task_main_fields(
            db,
            task_id,
            title,
            description,
            priority,
            due_date,
        )
    finally:
        db.close()

def get_open_tasks_by_client_id(client_id: int):
    db = SessionLocal()
    try:
        return task_repository.get_open_tasks_by_client_id(db, client_id)
    finally:
        db.close()

def get_task_operational_summary(task_id: int):
    db = SessionLocal()
    try:
        task = task_repository.get_task_by_id(db, task_id)

        if not task:
            return None

        updates = task.updates if task.updates else []
        latest_update = updates[0].content if updates else None

        project = _safe_related(task, "project")
        client = _safe_related(project, "client")

        return {
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date,
            "last_note": task.last_note,
            "next_action": task.next_action,
            "last_updated_at": task.last_updated_at,
            "project_id": project.id if project else None,
            "project_name": project.name if project else "Desconocido",
            "client_id": client.id if client else None,
            "client_name": client.name if client else "Desconocido",
            "updates_count": len(updates),
            "latest_update": latest_update,
        }
    finally:
        db.close()

def update_task_priority(task_id: int, new_priority: str):
    db = SessionLocal()
    try:
        return task_repository.update_task_priority(db, task_id, new_priority)
    finally:
        db.close()

def get_tasks_by_client_id(client_id: int):
    db = SessionLocal()
    try:
        return task_repository.get_tasks_by_client_id(db, client_id)
    finally:
        db.close()


def get_tasks_by_project_id(project_id: int):
    db = SessionLocal()
    try:
        return task_repository.get_tasks_by_project_id(db, project_id)
    finally:
        db.close()

def get_task_by_name(name: str):
    db = SessionLocal()
    try:
        return task_repository.get_task_by_name(db, name)
    finally:
        db.close()

def search_tasks_by_name(name: str, limit: int = 5):
    db = SessionLocal()
    try:
        return task_repository.search_tasks_by_name(db, name, limit)
    finally:
        db.close()


def search_tasks_by_name_and_client_id(name: str, client_id: int, limit: int = 5):
    db = SessionLocal()
    try:
        return task_repository.search_tasks_by_name_and_client_id(db, name, client_id, limit)
    finally:
        db.close()


def update_task_status_conversational(task_id: int, new_status: str, reason: str | None = None):
    db = SessionLocal()
    try:
        task = task_repository.get_task_by_id(db, task_id)
        if not task:
            return {"updated": False, "error": "not_found"}

        old_status = task.status
        if old_status == new_status and not reason:
            return {
                "updated": False,
                "error": "no_change",
                "task_id": task.id,
                "task_title": task.title,
                "field": "status",
                "old_value": old_status,
                "new_value": new_status,
            }

        updated_task = task
        if old_status != new_status:
            updated_task = task_repository.update_task_status(db, task_id, new_status)

        if reason:
            updated_task = task_repository.update_task_context(db, task_id, last_note=reason)

        _register_assistant_update(
            db,
            task_id=task_id,
            content=_build_update_content(
                "estado",
                old_status,
                new_status,
                extra=f"Motivo: {reason}" if reason else None,
            ),
        )

        return {
            "updated": True,
            "task_id": updated_task.id,
            "task_title": updated_task.title,
            "field": "status",
            "old_value": old_status,
            "new_value": updated_task.status,
            "task": updated_task,
            "reason": reason,
        }
    finally:
        db.close()


def update_task_priority_conversational(
    task_id: int,
    new_priority: str | None = None,
    priority_direction: str | None = None,
):
    db = SessionLocal()
    try:
        task = task_repository.get_task_by_id(db, task_id)
        if not task:
            return {"updated": False, "error": "not_found"}

        old_priority = task.priority
        resolved_priority = new_priority or _resolve_relative_priority(old_priority, priority_direction)
        if not resolved_priority:
            return {"updated": False, "error": "invalid_priority"}

        if old_priority == resolved_priority:
            return {
                "updated": False,
                "error": "no_change",
                "task_id": task.id,
                "task_title": task.title,
                "field": "priority",
                "old_value": old_priority,
                "new_value": resolved_priority,
            }

        updated_task = task_repository.update_task_priority(db, task_id, resolved_priority)
        _register_assistant_update(
            db,
            task_id=task_id,
            content=_build_update_content("prioridad", old_priority, resolved_priority),
        )

        return {
            "updated": True,
            "task_id": updated_task.id,
            "task_title": updated_task.title,
            "field": "priority",
            "old_value": old_priority,
            "new_value": updated_task.priority,
            "task": updated_task,
        }
    finally:
        db.close()


def add_task_note_conversational(task_id: int, note_content: str):
    db = SessionLocal()
    try:
        task = task_repository.get_task_by_id(db, task_id)
        if not task:
            return {"updated": False, "error": "not_found"}

        old_note = task.last_note
        updated_task = task_repository.update_task_context(db, task_id, last_note=note_content)
        _register_assistant_update(
            db,
            task_id=task_id,
            content=f"Nota registrada: {note_content}",
        )

        return {
            "updated": True,
            "task_id": updated_task.id,
            "task_title": updated_task.title,
            "field": "last_note",
            "old_value": old_note,
            "new_value": updated_task.last_note,
            "task": updated_task,
        }
    finally:
        db.close()


def update_task_next_action_conversational(task_id: int, next_action: str):
    db = SessionLocal()
    try:
        task = task_repository.get_task_by_id(db, task_id)
        if not task:
            return {"updated": False, "error": "not_found"}

        old_value = task.next_action
        updated_task = task_repository.update_task_context(db, task_id, next_action=next_action)
        _register_assistant_update(
            db,
            task_id=task_id,
            content=_build_update_content("próxima acción", old_value, next_action),
        )

        return {
            "updated": True,
            "task_id": updated_task.id,
            "task_title": updated_task.title,
            "field": "next_action",
            "old_value": old_value,
            "new_value": updated_task.next_action,
            "task": updated_task,
        }
    finally:
        db.close()


def _register_assistant_update(db, task_id: int, content: str):
    task_update_repository.create_task_update(
        db,
        task_id=task_id,
        content=content,
        update_type="assistant_update",
        source="asistente",
    )


def _build_update_content(field_name: str, old_value: str | None, new_value: str | None, extra: str | None = None):
    parts = [
        f"{field_name.capitalize()}: {old_value or 'vacío'} -> {new_value or 'vacío'}",
    ]
    if extra:
        parts.append(extra)
    return " | ".join(parts)


def _resolve_relative_priority(current_priority: str, priority_direction: str | None) -> str | None:
    if priority_direction != "up":
        return None

    ordered = [
        TaskPriority.LOW.value,
        TaskPriority.MEDIUM.value,
        TaskPriority.HIGH.value,
    ]
    if current_priority not in ordered:
        return None

    current_index = ordered.index(current_priority)
    return ordered[min(current_index + 1, len(ordered) - 1)]


def get_executive_task_snapshot(today: date | None = None) -> dict:
    today = today or date.today()
    tasks = get_all_tasks_with_relations()

    items = [_serialize_task_for_executive(task, today) for task in tasks]
    open_items = [item for item in items if item["status"] != "hecha"]
    blocked_items = [item for item in open_items if item["status"] == "bloqueada"]
    urgent_items = [item for item in open_items if item["is_urgent"]]
    overdue_items = [item for item in open_items if item["is_overdue"]]

    ranked_items = sorted(open_items, key=_task_rank_key)

    return {
        "today": today.isoformat(),
        "tasks": items,
        "open_tasks": open_items,
        "blocked_tasks": blocked_items,
        "urgent_tasks": urgent_items,
        "overdue_tasks": overdue_items,
        "recommended_tasks": ranked_items[:5],
        "heuristic": [
            "bloqueadas primero",
            "despues vencidas o para hoy",
            "despues prioridad alta",
            "despues en progreso",
            "despues pendientes relevantes",
        ],
    }


def get_followup_task_snapshot(today: date | None = None) -> dict:
    today = today or date.today()
    tasks = get_all_tasks_with_relations()

    items = [_serialize_task_for_executive(task, today) for task in tasks]
    open_items = [item for item in items if item["status"] != "hecha"]
    with_next_action = [item for item in open_items if item["has_next_action"]]
    without_next_action = [item for item in open_items if item["missing_next_action"]]
    blocked_without_next_action = [item for item in open_items if item["blocked_without_next_action"]]
    followup_needed = [item for item in open_items if item["needs_followup"]]
    push_today = sorted(open_items, key=_followup_rank_key)

    return {
        "today": today.isoformat(),
        "tasks": items,
        "open_tasks": open_items,
        "tasks_with_next_action": with_next_action,
        "tasks_without_next_action": without_next_action,
        "blocked_without_next_action": blocked_without_next_action,
        "followup_needed_tasks": followup_needed,
        "push_today_tasks": push_today[:5],
        "heuristic": [
            "bloqueadas sin proxima accion primero",
            "despues urgentes o de alta prioridad sin seguimiento",
            "despues tareas urgentes con proxima accion explicita",
            "si falta next_action se marca falta de seguimiento",
        ],
    }


def get_temporal_task_snapshot(
    time_scope: str,
    *,
    today: date | None = None,
    temporal_focus: str | None = None,
) -> dict:
    today = today or date.today()
    tasks = get_all_tasks_with_relations()
    return build_temporal_task_snapshot_from_tasks(
        tasks,
        time_scope=time_scope,
        today=today,
        temporal_focus=temporal_focus,
    )


def build_temporal_task_snapshot_from_tasks(
    tasks: list,
    *,
    time_scope: str,
    today: date | None = None,
    temporal_focus: str | None = None,
) -> dict:
    today = today or date.today()
    items = [_serialize_task_for_executive(task, today) for task in tasks]
    open_items = [item for item in items if item["status"] != "hecha"]

    matched_items = [item for item in open_items if _matches_temporal_scope(item, time_scope=time_scope, today=today)]
    if temporal_focus == "followups":
        matched_items = [item for item in matched_items if _is_followup_like(item)]
    elif temporal_focus == "closing":
        matched_items = [item for item in matched_items if not item["is_blocked"]]

    matched_items = sorted(matched_items, key=_temporal_rank_key)

    return {
        "today": today.isoformat(),
        "time_scope": time_scope,
        "temporal_focus": temporal_focus,
        "tasks": items,
        "open_tasks": open_items,
        "matched_items": matched_items[:10],
        "heuristic": _build_temporal_heuristic(time_scope, temporal_focus),
        "degraded": False,
    }


def get_missing_due_date_snapshot(today: date | None = None) -> dict:
    today = today or date.today()
    tasks = get_all_tasks_with_relations()
    return build_missing_due_date_snapshot_from_tasks(tasks, today=today)


def build_missing_due_date_snapshot_from_tasks(tasks: list, *, today: date | None = None) -> dict:
    today = today or date.today()
    items = [_serialize_task_for_executive(task, today) for task in tasks]
    open_items = [item for item in items if item["status"] != "hecha"]
    missing_due_items = [item for item in open_items if _should_have_due_date(item)]
    missing_due_items = sorted(missing_due_items, key=_missing_due_rank_key)

    return {
        "today": today.isoformat(),
        "tasks": items,
        "open_tasks": open_items,
        "missing_due_items": missing_due_items[:10],
        "heuristic": [
            "solo tareas abiertas sin fecha",
            "prioriza bloqueadas, alta prioridad o con proxima accion",
            "si no hay senales operativas, no exige fecha",
        ],
        "degraded": False,
    }


def build_operational_focus_from_tasks(tasks: list, today: date | None = None) -> dict:
    today = today or date.today()
    items = [_serialize_task_for_executive(task, today) for task in tasks]
    open_items = [item for item in items if item["status"] != "hecha"]
    prioritized_items = sorted(open_items, key=_operational_summary_rank_key)
    blocked_items = [item for item in prioritized_items if item["is_blocked"]]
    risky_items = [
        item
        for item in prioritized_items
        if item["is_blocked"] or item["is_overdue"] or item["high_priority_without_next_action"]
    ]
    attention_items = [
        item
        for item in prioritized_items
        if item["missing_next_action"] or item["is_high_priority"] or item["is_overdue"]
    ]
    next_steps = [item for item in prioritized_items if item["has_next_action"]]

    return {
        "today": today.isoformat(),
        "tasks": items,
        "open_tasks": open_items,
        "prioritized_tasks": prioritized_items[:5],
        "important_pending": prioritized_items[:3],
        "blocked_items": blocked_items[:3],
        "risk_items": risky_items[:3],
        "attention_items": attention_items[:3],
        "next_steps": next_steps[:3],
        "status_overview": _build_tasks_status_overview(open_items, blocked_items),
        "recommendation": _build_tasks_recommendation(prioritized_items),
        "heuristic": [
            "bloqueadas arriba",
            "despues alta prioridad y vencidas",
            "despues abiertas sin proxima accion",
            "si falta dato, no se inventa",
        ],
    }


def build_task_advanced_summary(summary: dict) -> dict:
    due_date = summary.get("due_date")
    status = summary.get("status")
    priority = summary.get("priority")
    next_action = (summary.get("next_action") or "").strip() or None
    last_note = (summary.get("last_note") or "").strip() or None
    is_open = status != "hecha"
    is_blocked = status == "bloqueada"
    is_high_priority = priority == TaskPriority.HIGH.value

    pending_items = []
    risk_items = []
    next_steps = []

    if is_blocked:
        risk_items.append("La tarea esta bloqueada.")
    if is_high_priority:
        pending_items.append("Tiene prioridad alta.")
    if due_date and is_open:
        pending_items.append(f"Vence: {due_date}.")
    if last_note:
        pending_items.append(f"Ultima nota operativa: {last_note}")
    if next_action:
        next_steps.append(f"Proximo paso explicito: {next_action}")
    elif is_open:
        risk_items.append("No tiene proxima accion definida.")

    recommendation = _build_task_recommendation(
        is_open=is_open,
        is_blocked=is_blocked,
        is_high_priority=is_high_priority,
        next_action=next_action,
    )

    status_parts = [f"Estado: {status}.", f"Prioridad: {priority}."]
    if due_date and is_open:
        status_parts.append(f"Vence: {due_date}.")
    if not due_date and is_open:
        status_parts.append("No veo fecha de vencimiento cargada.")

    return {
        "scope": "task",
        "entity_name": summary.get("title"),
        "status_overview": " ".join(status_parts),
        "important_pending": pending_items[:3],
        "risk_items": risk_items[:3],
        "attention_items": pending_items[:3],
        "next_steps": next_steps[:3],
        "recommendation": recommendation,
        "heuristic": [
            "bloqueos primero",
            "despues prioridad y vencimiento",
            "si falta next_action se marca la falta de seguimiento",
        ],
    }


def build_client_advanced_summary(client_name: str, projects: list, tasks: list, today: date | None = None) -> dict:
    focus = build_operational_focus_from_tasks(tasks, today=today)
    project_count = len(projects)
    open_count = len(focus["open_tasks"])
    blocked_count = len(focus["blocked_items"])

    status_overview = (
        f"Hay {project_count} proyectos, {open_count} tareas abiertas y {blocked_count} bloqueadas."
        if open_count
        else f"Hay {project_count} proyectos y no veo tareas abiertas en este momento."
    )

    return {
        "scope": "client",
        "entity_name": client_name,
        "status_overview": status_overview,
        "important_pending": focus["important_pending"],
        "risk_items": focus["risk_items"],
        "attention_items": focus["attention_items"],
        "next_steps": focus["next_steps"],
        "recommendation": focus["recommendation"],
        "heuristic": focus["heuristic"],
        "project_count": project_count,
        "open_tasks_count": open_count,
        "blocked_tasks_count": blocked_count,
    }


def get_operational_friction_snapshot(today: date | None = None) -> dict:
    today = today or date.today()
    tasks = get_all_tasks_with_relations()
    return build_friction_focus_from_tasks(tasks, today=today)


def build_friction_focus_from_tasks(tasks: list, today: date | None = None) -> dict:
    today = today or date.today()
    items = [_serialize_task_for_executive(task, today) for task in tasks]
    open_items = [item for item in items if item["status"] != "hecha"]
    friction_items = [item for item in open_items if item["friction_score"] > 0]
    stalled_items = [item for item in friction_items if item["has_strong_stall_signal"]]
    probable_items = [item for item in friction_items if not item["has_strong_stall_signal"]]
    prioritized = sorted(friction_items, key=_friction_rank_key)

    return {
        "today": today.isoformat(),
        "tasks": items,
        "open_tasks": open_items,
        "friction_tasks": prioritized[:5],
        "stalled_tasks": stalled_items[:5],
        "probable_friction_tasks": probable_items[:5],
        "strong_temporal_signals": [item for item in friction_items if item["has_temporal_signal"]][:5],
        "heuristic": [
            "riesgo alto: bloqueada, vieja o alta prioridad sin next_action",
            "friccion media: en progreso vieja o abierta sin seguimiento",
            "si falta dato temporal se habla de friccion probable, no de atraso exacto",
        ],
        "status_overview": _build_friction_status_overview(open_items, friction_items, stalled_items),
        "recommendation": _build_friction_recommendation(prioritized),
    }


def build_task_friction_summary(summary: dict, today: date | None = None) -> dict:
    today = today or date.today()
    due_date = summary.get("due_date")
    created_at = summary.get("created_at")
    last_updated_at = summary.get("last_updated_at")
    status = summary.get("status")
    priority = summary.get("priority")
    next_action = (summary.get("next_action") or "").strip() or None

    age_days = _days_since(created_at, today)
    update_days = _days_since(last_updated_at, today)
    is_open = status != "hecha"
    is_blocked = status == "bloqueada"
    is_in_progress = status == "en_progreso"
    is_high_priority = priority == TaskPriority.HIGH.value
    has_temporal_signal = age_days is not None or update_days is not None or bool(due_date)
    old_reference = update_days if update_days is not None else age_days
    is_old_open = is_open and old_reference is not None and old_reference >= 14
    is_old_blocked = is_blocked and old_reference is not None and old_reference >= 7
    is_stale_in_progress = is_in_progress and old_reference is not None and old_reference >= 7
    missing_next_action = is_open and not next_action

    signals = _build_friction_signals(
        is_blocked=is_blocked,
        is_old_blocked=is_old_blocked,
        is_stale_in_progress=is_stale_in_progress,
        is_old_open=is_old_open,
        is_high_priority=is_high_priority,
        missing_next_action=missing_next_action,
        has_temporal_signal=has_temporal_signal,
    )

    recommendation = _build_task_friction_recommendation(
        is_old_blocked=is_old_blocked,
        is_blocked=is_blocked,
        is_stale_in_progress=is_stale_in_progress,
        is_high_priority=is_high_priority,
        missing_next_action=missing_next_action,
        next_action=next_action,
        has_temporal_signal=has_temporal_signal,
    )

    overview = "No veo señales claras de friccion en esta tarea."
    if signals:
        overview = "Veo señales de friccion en esta tarea."
    if is_old_blocked or is_stale_in_progress or is_old_open:
        overview = "Hay señales de estancamiento o atraso probable en esta tarea."
    elif signals and not has_temporal_signal:
        overview = "Veo friccion probable, pero no puedo afirmar atraso exacto con los datos actuales."

    return {
        "scope": "task",
        "entity_name": summary.get("title"),
        "status_overview": overview,
        "signals": signals[:4],
        "highlights": signals[:3],
        "recommendation": recommendation,
        "heuristic": [
            "bloqueos viejos y progreso estancado pesan mas",
            "alta prioridad sin next_action sube friccion",
            "sin dato temporal solo se habla de friccion probable",
        ],
    }


def get_operational_recommendation_snapshot(today: date | None = None, focus: str = "general") -> dict:
    today = today or date.today()
    tasks = get_all_tasks_with_relations()
    return build_recommendation_focus_from_tasks(tasks, today=today, focus=focus)


def build_recommendation_focus_from_tasks(tasks: list, today: date | None = None, focus: str = "general") -> dict:
    today = today or date.today()
    items = [_serialize_task_for_executive(task, today) for task in tasks]
    open_items = [item for item in items if item["status"] != "hecha"]

    ranked_items = [_decorate_recommendation_item(item, focus=focus) for item in open_items]
    if focus == "close":
        ranked_items = [item for item in ranked_items if not item["is_blocked"]]

    ranked_items = sorted(ranked_items, key=_recommendation_rank_key)
    top_recommendations = ranked_items[:3]

    if not top_recommendations and open_items:
        fallback = _decorate_recommendation_item(open_items[0], focus=focus, conservative_only=True)
        top_recommendations = [fallback]

    return {
        "today": today.isoformat(),
        "focus": focus,
        "tasks": items,
        "open_tasks": open_items,
        "recommendations": top_recommendations,
        "status_overview": _build_recommendation_status_overview(open_items, top_recommendations, focus),
        "heuristic": _build_recommendation_heuristic(focus),
        "recommendation": _build_recommendation_summary(top_recommendations, focus),
    }


def build_task_recommendation_summary(summary: dict, today: date | None = None, focus: str = "general") -> dict:
    today = today or date.today()
    item = _serialize_task_summary_for_recommendation(summary, today)
    recommendation_item = _decorate_recommendation_item(item, focus=focus, allow_zero=True)

    return {
        "scope": "task",
        "entity_name": summary.get("title"),
        "status_overview": _build_recommendation_status_overview([item], [recommendation_item], focus),
        "recommendations": [recommendation_item],
        "heuristic": _build_recommendation_heuristic(focus),
        "recommendation": recommendation_item["recommendation_text"],
    }


def _serialize_task_for_executive(task, today: date) -> dict:
    project = _safe_related(task, "project")
    client = _safe_related(project, "client")
    due_date = task.due_date
    status = task.status
    priority = task.priority
    next_action = (task.next_action or "").strip() or None
    is_open = status != "hecha"
    is_blocked = status == "bloqueada"
    is_high_priority = priority == TaskPriority.HIGH.value
    is_in_progress = status == "en_progreso"
    is_due_today = bool(due_date and due_date == today and is_open)
    is_overdue = bool(due_date and due_date < today and is_open)
    is_urgent = is_blocked or is_overdue or is_due_today or is_high_priority
    has_next_action = bool(next_action)
    missing_next_action = is_open and not has_next_action
    blocked_without_next_action = is_blocked and missing_next_action
    high_priority_without_next_action = is_high_priority and missing_next_action
    created_at = getattr(task, "created_at", None)
    last_updated_at = getattr(task, "last_updated_at", None)
    age_days = _days_since(created_at, today)
    update_days = _days_since(last_updated_at, today)
    old_reference = update_days if update_days is not None else age_days
    is_old_open = is_open and old_reference is not None and old_reference >= 14
    is_old_blocked = is_blocked and old_reference is not None and old_reference >= 7
    is_stale_in_progress = is_in_progress and old_reference is not None and old_reference >= 7
    has_temporal_signal = age_days is not None or update_days is not None or bool(due_date)
    needs_followup = is_open and (
        blocked_without_next_action
        or high_priority_without_next_action
        or (is_overdue and missing_next_action)
        or (is_in_progress and missing_next_action)
    )
    friction_signals = _build_friction_signals(
        is_blocked=is_blocked,
        is_old_blocked=is_old_blocked,
        is_stale_in_progress=is_stale_in_progress,
        is_old_open=is_old_open,
        is_high_priority=is_high_priority,
        missing_next_action=missing_next_action,
        has_temporal_signal=has_temporal_signal,
    )
    friction_score = _task_friction_score(
        is_old_blocked=is_old_blocked,
        is_blocked=is_blocked,
        is_stale_in_progress=is_stale_in_progress,
        is_old_open=is_old_open,
        is_high_priority=is_high_priority,
        missing_next_action=missing_next_action,
        has_temporal_signal=has_temporal_signal,
    )

    return {
        "task_id": task.id,
        "title": task.title,
        "status": status,
        "priority": priority,
        "due_date": str(due_date) if due_date else None,
        "due_date_value": due_date,
        "last_note": task.last_note,
        "next_action": next_action,
        "project_id": project.id if project else None,
        "project_name": project.name if project else "Sin proyecto",
        "client_id": client.id if client else None,
        "client_name": client.name if client else "Desconocido",
        "created_at": created_at,
        "last_updated_at": last_updated_at,
        "age_days": age_days,
        "days_since_update": update_days,
        "has_temporal_signal": has_temporal_signal,
        "is_blocked": is_blocked,
        "is_due_today": is_due_today,
        "is_overdue": is_overdue,
        "is_high_priority": is_high_priority,
        "is_in_progress": is_in_progress,
        "is_urgent": is_urgent,
        "has_next_action": has_next_action,
        "missing_next_action": missing_next_action,
        "blocked_without_next_action": blocked_without_next_action,
        "high_priority_without_next_action": high_priority_without_next_action,
        "is_old_open": is_old_open,
        "is_old_blocked": is_old_blocked,
        "is_stale_in_progress": is_stale_in_progress,
        "has_strong_stall_signal": is_old_blocked or is_stale_in_progress or is_old_open,
        "needs_followup": needs_followup,
        "friction_signals": friction_signals,
        "friction_score": friction_score,
        "score": _task_priority_score(
            is_blocked=is_blocked,
            is_overdue=is_overdue,
            is_due_today=is_due_today,
            is_high_priority=is_high_priority,
            is_in_progress=is_in_progress,
        ),
    }


def _task_priority_score(
    *,
    is_blocked: bool,
    is_overdue: bool,
    is_due_today: bool,
    is_high_priority: bool,
    is_in_progress: bool,
) -> int:
    score = 0
    if is_blocked:
        score += 100
    if is_overdue:
        score += 80
    if is_due_today:
        score += 60
    if is_high_priority:
        score += 40
    if is_in_progress:
        score += 20
    return score


def _matches_temporal_scope(item: dict, *, time_scope: str, today: date) -> bool:
    due_value = item.get("due_date_value")
    if item.get("status") == "hecha":
        return False
    if time_scope == "today":
        return bool(due_value and due_value == today)
    if time_scope == "tomorrow":
        return bool(due_value and due_value == today + timedelta(days=1))
    if time_scope == "this_week":
        week_end = today + timedelta(days=(6 - today.weekday()))
        return bool(due_value and today <= due_value <= week_end)
    if time_scope == "overdue":
        return bool(due_value and due_value < today)
    if time_scope == "due_items":
        return bool(due_value)
    return False


def _is_followup_like(item: dict) -> bool:
    title = (item.get("title") or "").strip().lower()
    return bool(item.get("has_next_action") or title.startswith("follow-up") or title.startswith("follow up"))


def _should_have_due_date(item: dict) -> bool:
    return bool(
        item.get("status") != "hecha"
        and not item.get("due_date_value")
        and (
            item.get("is_blocked")
            or item.get("is_high_priority")
            or item.get("has_next_action")
            or item.get("needs_followup")
            or item.get("is_in_progress")
        )
    )


def _build_temporal_heuristic(time_scope: str, temporal_focus: str | None) -> list[str]:
    scope_label = {
        "today": "vence hoy",
        "tomorrow": "vence mañana",
        "this_week": "vence esta semana",
        "overdue": "esta vencido",
        "due_items": "tiene fecha cargada",
    }.get(time_scope, "tiene senal temporal")
    heuristics = [
        f"solo tareas abiertas que {scope_label}",
        "prioriza bloqueadas, vencidas y alta prioridad",
    ]
    if temporal_focus == "followups":
        heuristics.append("acota a tareas tipo follow-up o con proxima accion")
    if temporal_focus == "closing":
        heuristics.append("prioriza lo que podria empujarse para cierre")
    return heuristics


def _temporal_rank_key(item: dict) -> tuple:
    due_sort = item["due_date"] or "9999-12-31"
    return (
        -int(item["is_overdue"]),
        -int(item["is_due_today"]),
        -int(item["is_blocked"]),
        -int(item["is_high_priority"]),
        due_sort,
        item["client_name"],
        item["project_name"],
        item["title"],
    )


def _missing_due_rank_key(item: dict) -> tuple:
    return (
        -int(item["is_blocked"]),
        -int(item["is_high_priority"]),
        -int(item["has_next_action"]),
        -int(item["needs_followup"]),
        -int(item["is_in_progress"]),
        item["client_name"],
        item["project_name"],
        item["title"],
    )


def _task_rank_key(item: dict) -> tuple:
    due_sort = item["due_date"] or "9999-12-31"
    return (
        -item["score"],
        due_sort,
        item["client_name"],
        item["project_name"],
        item["title"],
    )


def _followup_rank_key(item: dict) -> tuple:
    due_sort = item["due_date"] or "9999-12-31"
    return (
        -int(item["blocked_without_next_action"]),
        -int(item["is_overdue"] and item["missing_next_action"]),
        -int(item["high_priority_without_next_action"]),
        -int(item["missing_next_action"]),
        -int(item["is_urgent"] and item["has_next_action"]),
        due_sort,
        item["client_name"],
        item["project_name"],
        item["title"],
    )


def _operational_summary_rank_key(item: dict) -> tuple:
    due_sort = item["due_date"] or "9999-12-31"
    return (
        -int(item["is_blocked"]),
        -int(item["is_high_priority"]),
        -int(item["is_overdue"]),
        -int(item["missing_next_action"]),
        due_sort,
        item["project_name"],
        item["title"],
    )


def _friction_rank_key(item: dict) -> tuple:
    due_sort = item["due_date"] or "9999-12-31"
    return (
        -item["friction_score"],
        -int(item["has_temporal_signal"]),
        due_sort,
        item["client_name"],
        item["project_name"],
        item["title"],
    )


def _build_tasks_status_overview(open_items: list[dict], blocked_items: list[dict]) -> str:
    if not open_items:
        return "No veo tareas abiertas en este momento."

    high_priority_count = len([item for item in open_items if item["is_high_priority"]])
    parts = [f"Hay {len(open_items)} tareas abiertas."]
    if blocked_items:
        parts.append(f"{len(blocked_items)} estan bloqueadas.")
    if high_priority_count:
        parts.append(f"{high_priority_count} tienen prioridad alta.")
    return " ".join(parts)


def _build_tasks_recommendation(prioritized_items: list[dict]) -> str:
    if not prioritized_items:
        return "No veo una accion urgente para empujar ahora."

    top = prioritized_items[0]
    if top["is_blocked"]:
        return f"Primero destrabaria '{top['title']}', porque hoy es el mayor freno operativo."
    if top["missing_next_action"]:
        return f"Definiria una proxima accion concreta para '{top['title']}' antes de seguir sumando pendientes."
    if top["has_next_action"]:
        return f"Empujaria '{top['title']}' con este siguiente paso: {top['next_action']}."
    return f"Miraria primero '{top['title']}' por prioridad operativa."


def _build_friction_status_overview(open_items: list[dict], friction_items: list[dict], stalled_items: list[dict]) -> str:
    if not open_items:
        return "No veo trabajo abierto con señales de friccion."

    parts = [f"Hay {len(open_items)} tareas abiertas."]
    if friction_items:
        parts.append(f"{len(friction_items)} muestran friccion operativa.")
    if stalled_items:
        parts.append(f"{len(stalled_items)} tienen senales mas fuertes de estancamiento.")
    return " ".join(parts)


def _build_friction_recommendation(prioritized_items: list[dict]) -> str:
    if not prioritized_items:
        return "No veo un foco claro de friccion para empujar ahora."

    top = prioritized_items[0]
    if top["is_old_blocked"]:
        return f"Primero destrabaria '{top['title']}', porque combina bloqueo y senal temporal de atraso."
    if top["is_stale_in_progress"]:
        return f"Revisaria '{top['title']}', porque lleva demasiado en progreso sin una senal clara de avance."
    if top["high_priority_without_next_action"]:
        return f"Definiria una proxima accion concreta para '{top['title']}', porque sigue prioritaria pero mal seguida."
    if top["missing_next_action"]:
        return f"Ordenaria el seguimiento de '{top['title']}' antes de que siga acumulando friccion."
    return f"Miraria '{top['title']}' como principal foco de friccion probable."


def _build_task_recommendation(
    *,
    is_open: bool,
    is_blocked: bool,
    is_high_priority: bool,
    next_action: str | None,
) -> str:
    if not is_open:
        return "No requiere empuje inmediato porque ya esta cerrada."
    if is_blocked:
        return "La prioridad operativa es destrabarla antes de seguir avanzando."
    if next_action:
        return f"Yo empujaria este proximo paso: {next_action}."
    if is_high_priority:
        return "Definiria una proxima accion concreta hoy, porque sigue siendo prioritaria."
    return "Definiria el siguiente paso mas concreto antes de mover otras cosas."


def _build_task_friction_recommendation(
    *,
    is_old_blocked: bool,
    is_blocked: bool,
    is_stale_in_progress: bool,
    is_high_priority: bool,
    missing_next_action: bool,
    next_action: str | None,
    has_temporal_signal: bool,
) -> str:
    if is_old_blocked:
        return "La prioridad seria destrabarla cuanto antes: ya hay senal de bloqueo sostenido."
    if is_blocked:
        return "La prioridad seria destrabarla; hoy es una fuente clara de friccion."
    if is_stale_in_progress:
        return "Yo revisaria si sigue bien encarada o si necesita redefinicion, porque parece demasiado tiempo en progreso."
    if is_high_priority and missing_next_action:
        return "Definiria una proxima accion concreta hoy, porque sigue prioritaria pero sin seguimiento claro."
    if missing_next_action and not has_temporal_signal:
        return "Veo friccion probable por falta de seguimiento, aunque no puedo afirmar atraso exacto."
    if next_action:
        return f"El proximo paso existente es '{next_action}', asi que revisaria por que no se esta moviendo."
    return "La miraria de cerca, pero con los datos actuales no puedo afirmar un atraso fuerte."


def _task_friction_score(
    *,
    is_old_blocked: bool,
    is_blocked: bool,
    is_stale_in_progress: bool,
    is_old_open: bool,
    is_high_priority: bool,
    missing_next_action: bool,
    has_temporal_signal: bool,
) -> int:
    score = 0
    if is_old_blocked:
        score += 100
    elif is_blocked:
        score += 70
    if is_stale_in_progress:
        score += 75
    if is_old_open:
        score += 55
    if is_high_priority and missing_next_action:
        score += 60
    elif missing_next_action:
        score += 30
    if not has_temporal_signal and score > 0:
        score -= 10
    return max(score, 0)


def _build_friction_signals(
    *,
    is_blocked: bool,
    is_old_blocked: bool,
    is_stale_in_progress: bool,
    is_old_open: bool,
    is_high_priority: bool,
    missing_next_action: bool,
    has_temporal_signal: bool,
) -> list[str]:
    signals: list[str] = []
    if is_old_blocked:
        signals.append("bloqueada hace tiempo")
    elif is_blocked:
        signals.append("bloqueada")
    if is_stale_in_progress:
        signals.append("en progreso hace demasiado")
    if is_old_open:
        signals.append("abierta hace bastante sin cierre")
    if is_high_priority and missing_next_action:
        signals.append("alta prioridad sin proxima accion")
    elif missing_next_action:
        signals.append("sin proxima accion clara")
    if signals and not has_temporal_signal and any(signal in signals for signal in ("sin proxima accion clara", "alta prioridad sin proxima accion")):
        signals.append("friccion probable sin evidencia temporal fuerte")
    return signals


def _days_since(value, today: date) -> int | None:
    if value is None:
        return None
    if isinstance(value, date) and not hasattr(value, "hour"):
        return (today - value).days
    try:
        return (today - value.date()).days
    except Exception:
        return None


def _normalize_temporal_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    normalized = normalized.replace("el ", "").strip()
    return normalized


def _safe_related(entity, attr: str):
    if entity is None:
        return None
    try:
        return getattr(entity, attr, None)
    except Exception:
        return None


def _serialize_task_summary_for_recommendation(summary: dict, today: date) -> dict:
    due_date = summary.get("due_date")
    if due_date:
        due_date = str(due_date)
    next_action = (summary.get("next_action") or "").strip() or None
    status = summary.get("status")
    priority = summary.get("priority")
    is_open = status != "hecha"
    is_blocked = status == "bloqueada"
    is_high_priority = priority == TaskPriority.HIGH.value
    is_in_progress = status == "en_progreso"
    due_value = summary.get("due_date")
    is_due_today = bool(due_value and due_value == today and is_open)
    is_overdue = bool(due_value and due_value < today and is_open)
    created_at = summary.get("created_at")
    last_updated_at = summary.get("last_updated_at")
    age_days = _days_since(created_at, today)
    update_days = _days_since(last_updated_at, today)
    old_reference = update_days if update_days is not None else age_days
    is_old_open = is_open and old_reference is not None and old_reference >= 14
    is_old_blocked = is_blocked and old_reference is not None and old_reference >= 7
    is_stale_in_progress = is_in_progress and old_reference is not None and old_reference >= 7
    has_temporal_signal = age_days is not None or update_days is not None or bool(due_value)
    missing_next_action = is_open and not next_action
    blocked_without_next_action = is_blocked and missing_next_action
    high_priority_without_next_action = is_high_priority and missing_next_action
    friction_signals = _build_friction_signals(
        is_blocked=is_blocked,
        is_old_blocked=is_old_blocked,
        is_stale_in_progress=is_stale_in_progress,
        is_old_open=is_old_open,
        is_high_priority=is_high_priority,
        missing_next_action=missing_next_action,
        has_temporal_signal=has_temporal_signal,
    )

    return {
        "task_id": summary.get("task_id"),
        "title": summary.get("title"),
        "status": status,
        "priority": priority,
        "due_date": due_date,
        "last_note": summary.get("last_note"),
        "next_action": next_action,
        "project_id": summary.get("project_id"),
        "project_name": summary.get("project_name") or "Sin proyecto",
        "client_id": summary.get("client_id"),
        "client_name": summary.get("client_name") or "Desconocido",
        "created_at": created_at,
        "last_updated_at": last_updated_at,
        "age_days": age_days,
        "days_since_update": update_days,
        "has_temporal_signal": has_temporal_signal,
        "is_blocked": is_blocked,
        "is_due_today": is_due_today,
        "is_overdue": is_overdue,
        "is_high_priority": is_high_priority,
        "is_in_progress": is_in_progress,
        "is_urgent": is_blocked or is_overdue or is_due_today or is_high_priority,
        "has_next_action": bool(next_action),
        "missing_next_action": missing_next_action,
        "blocked_without_next_action": blocked_without_next_action,
        "high_priority_without_next_action": high_priority_without_next_action,
        "is_old_open": is_old_open,
        "is_old_blocked": is_old_blocked,
        "is_stale_in_progress": is_stale_in_progress,
        "has_strong_stall_signal": is_old_blocked or is_stale_in_progress or is_old_open,
        "needs_followup": blocked_without_next_action or high_priority_without_next_action,
        "friction_signals": friction_signals,
        "friction_score": _task_friction_score(
            is_old_blocked=is_old_blocked,
            is_blocked=is_blocked,
            is_stale_in_progress=is_stale_in_progress,
            is_old_open=is_old_open,
            is_high_priority=is_high_priority,
            missing_next_action=missing_next_action,
            has_temporal_signal=has_temporal_signal,
        ),
        "score": _task_priority_score(
            is_blocked=is_blocked,
            is_overdue=is_overdue,
            is_due_today=is_due_today,
            is_high_priority=is_high_priority,
            is_in_progress=is_in_progress,
        ),
    }


def _decorate_recommendation_item(item: dict, *, focus: str, conservative_only: bool = False, allow_zero: bool = False) -> dict:
    score = _task_recommendation_score(item, focus=focus, conservative_only=conservative_only)
    reasons = _build_task_recommendation_reasons(item, focus=focus, conservative_only=conservative_only)
    if score <= 0 and not allow_zero:
        score = 5
    recommendation_text = _build_task_recommendation_text(item, reasons, focus=focus, conservative_only=conservative_only)
    decorated = dict(item)
    decorated["recommendation_score"] = score
    decorated["recommendation_reasons"] = reasons
    decorated["recommendation_text"] = recommendation_text
    return decorated


def _task_recommendation_score(item: dict, *, focus: str, conservative_only: bool = False) -> int:
    if conservative_only:
        return 5

    score = 0
    if focus == "unblock":
        score += 150 if item["is_old_blocked"] else 0
        score += 120 if item["blocked_without_next_action"] else 0
        score += 95 if item["is_blocked"] else 0
        score += 50 if item["is_high_priority"] else 0
        score += 35 if item["missing_next_action"] else 0
        score += 25 if item["friction_score"] > 0 else 0
        return score

    if focus == "close":
        score += 90 if item["has_next_action"] else 0
        score += 70 if item["is_high_priority"] else 0
        score += 60 if item["is_overdue"] or item["is_due_today"] else 0
        score += 35 if item["is_old_open"] else 0
        score -= 90 if item["is_blocked"] else 0
        score -= 40 if item["missing_next_action"] else 0
        return score

    score += 150 if item["is_old_blocked"] else 0
    score += 125 if item["blocked_without_next_action"] else 0
    score += 110 if item["is_blocked"] else 0
    score += 100 if item["is_overdue"] else 0
    score += 75 if item["is_due_today"] else 0
    score += 85 if item["high_priority_without_next_action"] else 0
    score += 65 if item["is_stale_in_progress"] else 0
    score += 55 if item["is_high_priority"] else 0
    score += 40 if item["is_old_open"] else 0
    score += 35 if item["missing_next_action"] else 0
    score += 25 if item["has_next_action"] else 0
    return score


def _build_task_recommendation_reasons(item: dict, *, focus: str, conservative_only: bool = False) -> list[str]:
    if conservative_only:
        return ["no veo una senal fuerte, asi que iria por una recomendacion conservadora"]

    reasons: list[str] = []
    if item["is_old_blocked"]:
        reasons.append("esta bloqueada hace tiempo")
    elif item["blocked_without_next_action"]:
        reasons.append("esta bloqueada y sin proxima accion")
    elif item["is_blocked"]:
        reasons.append("esta bloqueada")

    if item["is_overdue"]:
        reasons.append("esta vencida")
    elif item["is_due_today"]:
        reasons.append("vence hoy")

    if item["high_priority_without_next_action"]:
        reasons.append("es de alta prioridad y no tiene proxima accion")
    elif item["is_high_priority"]:
        reasons.append("es de alta prioridad")

    if item["is_stale_in_progress"]:
        reasons.append("lleva demasiado en progreso")
    elif item["is_old_open"]:
        reasons.append("lleva bastante abierta")

    if focus == "close" and item["has_next_action"]:
        reasons.append("ya tiene un siguiente paso concreto para empujar cierre")
    elif item["has_next_action"]:
        reasons.append("ya tiene un siguiente paso claro")
    elif item["missing_next_action"]:
        reasons.append("le falta seguimiento concreto")

    if not reasons:
        reasons.append("merece atencion operativa con los datos actuales")

    return reasons[:4]


def _build_task_recommendation_text(item: dict, reasons: list[str], *, focus: str, conservative_only: bool = False) -> str:
    reasons_text = ", ".join(reasons)
    if conservative_only:
        return f"Iria primero por '{item['title']}', pero de forma conservadora: {reasons_text}."
    if focus == "unblock":
        return f"Recomiendo atacar '{item['title']}' para destrabar trabajo, porque {reasons_text}."
    if focus == "close":
        return f"Conviene empujar '{item['title']}' para intentar cerrarla hoy, porque {reasons_text}."
    return f"Recomiendo empezar por '{item['title']}', porque {reasons_text}."


def _recommendation_rank_key(item: dict) -> tuple:
    due_sort = item["due_date"] or "9999-12-31"
    return (
        -item["recommendation_score"],
        -int(item["has_next_action"]),
        due_sort,
        item["client_name"],
        item["project_name"],
        item["title"],
    )


def _build_recommendation_status_overview(open_items: list[dict], recommendations: list[dict], focus: str) -> str:
    if not open_items:
        return "No veo trabajo abierto para recomendar ahora."
    if not recommendations:
        return "Veo trabajo abierto, pero no una recomendacion fuerte con los datos actuales."

    if focus == "unblock":
        return f"Hay {len(open_items)} tareas abiertas y la recomendacion prioriza donde mas destrabe veo."
    if focus == "close":
        return f"Hay {len(open_items)} tareas abiertas y la recomendacion prioriza lo mas cerrable con sentido operativo."
    return f"Hay {len(open_items)} tareas abiertas y priorice donde veo mas impacto operativo inmediato."


def _build_recommendation_summary(recommendations: list[dict], focus: str) -> str:
    if not recommendations:
        return "Iria por una recomendacion conservadora: definir el siguiente paso mas concreto antes de mover otras cosas."
    top = recommendations[0]
    if focus == "unblock":
        return f"Yo intentaria destrabar primero '{top['title']}', porque hoy parece la jugada con mas impacto."
    if focus == "close":
        return f"Hoy intentaria cerrar '{top['title']}', porque es la opcion mas empujable con los datos actuales."
    return f"Si tuviera que elegir una sola cosa, iria primero por '{top['title']}'."


def _build_recommendation_heuristic(focus: str) -> list[str]:
    if focus == "unblock":
        return [
            "bloqueadas y bloqueadas viejas primero",
            "despues alta prioridad sin proxima accion",
            "despues otros focos de friccion que destraban trabajo",
        ]
    if focus == "close":
        return [
            "prioriza tareas no bloqueadas con siguiente paso claro",
            "despues urgencia y prioridad",
            "sin dato de esfuerzo se mantiene una recomendacion conservadora",
        ]
    return [
        "bloqueadas criticas primero",
        "despues vencidas o alta prioridad sin proxima accion",
        "despues progreso estancado o abiertas viejas",
        "si faltan datos, se baja a recomendacion conservadora",
    ]

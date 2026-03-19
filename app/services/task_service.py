from datetime import date

from app.db.session import SessionLocal
from app.repositories import task_repository, task_update_repository
from app.schemas.enums import TaskPriority


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
            "project_id": task.project.id if task.project else None,
            "project_name": task.project.name if task.project else "Desconocido",
            "client_id": task.project.client.id if task.project and task.project.client else None,
            "client_name": task.project.client.name if task.project and task.project.client else "Desconocido",
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


def _serialize_task_for_executive(task, today: date) -> dict:
    project = task.project
    client = project.client if project else None
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
    needs_followup = is_open and (
        blocked_without_next_action
        or high_priority_without_next_action
        or (is_overdue and missing_next_action)
        or (is_in_progress and missing_next_action)
    )

    return {
        "task_id": task.id,
        "title": task.title,
        "status": status,
        "priority": priority,
        "due_date": str(due_date) if due_date else None,
        "last_note": task.last_note,
        "next_action": next_action,
        "project_id": project.id if project else None,
        "project_name": project.name if project else "Sin proyecto",
        "client_id": client.id if client else None,
        "client_name": client.name if client else "Desconocido",
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
        "needs_followup": needs_followup,
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

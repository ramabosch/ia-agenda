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

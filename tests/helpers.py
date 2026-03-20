from __future__ import annotations

from datetime import date, datetime, time
from types import SimpleNamespace


def make_client(client_id: int, name: str):
    return SimpleNamespace(id=client_id, name=name)


def make_project(project_id: int, name: str, client, *, status: str = "activo", description: str | None = None):
    return SimpleNamespace(
        id=project_id,
        name=name,
        client=client,
        client_id=client.id if client else None,
        status=status,
        description=description,
        tasks=[],
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )


def make_task(
    task_id: int,
    title: str,
    project,
    *,
    status: str = "pendiente",
    priority: str = "media",
    due_date=None,
    last_note: str | None = None,
    next_action: str | None = None,
    created_at=None,
    last_updated_at=None,
):
    task = SimpleNamespace(
        id=task_id,
        title=title,
        project=project,
        project_id=project.id if project else None,
        status=status,
        priority=priority,
        due_date=due_date,
        last_note=last_note,
        next_action=next_action,
        updates=[],
        description=None,
        created_at=created_at or datetime(2026, 1, 1, 12, 0, 0),
        last_updated_at=last_updated_at,
    )
    if project is not None:
        project.tasks.append(task)
    return task


def make_task_summary(task, *, updates_count: int = 0, latest_update: str | None = None):
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
        "created_at": task.created_at,
        "project_id": task.project.id if task.project else None,
        "project_name": task.project.name if task.project else "Desconocido",
        "client_id": task.project.client.id if task.project and task.project.client else None,
        "client_name": task.project.client.name if task.project and task.project.client else "Desconocido",
        "updates_count": updates_count,
        "latest_update": latest_update,
    }


def make_project_summary(project):
    total_tasks = len(project.tasks)
    open_tasks = len([task for task in project.tasks if task.status != "hecha"])
    blocked_tasks = len([task for task in project.tasks if task.status == "bloqueada"])
    in_progress_tasks = len([task for task in project.tasks if task.status == "en_progreso"])
    done_tasks = len([task for task in project.tasks if task.status == "hecha"])
    return {
        "project_id": project.id,
        "project_name": project.name,
        "client_id": project.client.id if project.client else None,
        "client_name": project.client.name if project.client else "Desconocido",
        "status": project.status,
        "description": project.description,
        "total_tasks": total_tasks,
        "open_tasks": open_tasks,
        "done_tasks": done_tasks,
        "blocked_tasks": blocked_tasks,
        "in_progress_tasks": in_progress_tasks,
    }


def make_conversation_log(parsed_query: dict, *, user_input: str = "consulta previa", response_output: str = "respuesta previa"):
    return SimpleNamespace(
        user_input=user_input,
        parsed_intent=str(parsed_query),
        response_output=response_output,
    )


def make_agenda_item(
    agenda_item_id: int,
    title: str,
    scheduled_date: date,
    *,
    scheduled_time: time | None = None,
    kind: str = "event",
    note: str | None = None,
):
    return SimpleNamespace(
        id=agenda_item_id,
        title=title,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        kind=kind,
        note=note,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )

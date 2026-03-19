from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload

from app.db.models.task import Task

from app.db.models.project import Project


def create_task(
    db: Session,
    project_id: int,
    title: str,
    description: str | None = None,
    priority: str = "media",
    due_date: date | None = None,
    last_note: str | None = None,
    next_action: str | None = None,
) -> Task:
    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        priority=priority,
        due_date=due_date,
        last_note=last_note,
        next_action=next_action,
        last_updated_at=datetime.utcnow() if last_note or next_action else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_tasks_by_project(db: Session, project_id: int) -> list[Task]:
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .filter(Task.project_id == project_id)
        .order_by(Task.id.desc())
        .all()
    )


def get_all_tasks(db: Session) -> list[Task]:
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .order_by(Task.id.desc())
        .all()
    )


def get_all_tasks_with_relations(db: Session) -> list[Task]:
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .order_by(Task.created_at.desc())
        .all()
    )


def get_tasks_by_status(db: Session, status: str) -> list[Task]:
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .filter(Task.status == status)
        .order_by(Task.id.desc())
        .all()
    )


def get_overdue_tasks(db: Session, today: date) -> list[Task]:
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .filter(Task.due_date.is_not(None))
        .filter(Task.due_date < today)
        .filter(Task.status != "hecha")
        .order_by(Task.due_date.asc())
        .all()
    )


def get_tasks_due_today(db: Session, today: date) -> list[Task]:
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .filter(Task.due_date == today)
        .filter(Task.status != "hecha")
        .order_by(Task.id.desc())
        .all()
    )


def update_task_status(db: Session, task_id: int, new_status: str) -> Task | None:
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        return None

    task.status = new_status
    task.last_updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


def get_task_by_id(db: Session, task_id: int) -> Task | None:
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client), joinedload(Task.updates))
        .filter(Task.id == task_id)
        .first()
    )


def update_task_context(
    db: Session,
    task_id: int,
    last_note: str | None = None,
    next_action: str | None = None,
) -> Task | None:
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        return None

    if last_note is not None:
        task.last_note = last_note

    if next_action is not None:
        task.next_action = next_action

    task.last_updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task)
    return task

def update_task_main_fields(
    db: Session,
    task_id: int,
    title: str,
    description: str | None,
    priority: str,
    due_date: date | None,
) -> Task | None:
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        return None

    task.title = title
    task.description = description
    task.priority = priority
    task.due_date = due_date
    task.last_updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task)
    return task

def get_open_tasks_by_client_id(db: Session, client_id: int) -> list[Task]:
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .join(Task.project)
        .filter(Task.project.has(client_id=client_id))
        .filter(Task.status != "hecha")
        .order_by(Task.id.desc())
        .all()
    )

def update_task_priority(db: Session, task_id: int, new_priority: str) -> Task | None:
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        return None

    task.priority = new_priority
    task.last_updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task)
    return task

def get_tasks_by_client_id(db: Session, client_id: int):
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .join(Project)
        .filter(Project.client_id == client_id)
        .order_by(Task.created_at.desc())
        .all()
    )


def get_tasks_by_project_id(db: Session, project_id: int):
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .filter(Task.project_id == project_id)
        .order_by(Task.created_at.desc())
        .all()
    )

def get_task_by_name(db: Session, name: str):
    search = f"%{name.strip()}%"
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .filter(Task.title.ilike(search))
        .order_by(Task.created_at.desc())
        .first()
    )


def search_tasks_by_name(db: Session, name: str, limit: int = 5):
    search = f"%{name.strip()}%"
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .filter(Task.title.ilike(search))
        .order_by(Task.created_at.desc())
        .limit(limit)
        .all()
    )


def search_tasks_by_name_and_client_id(db: Session, name: str, client_id: int, limit: int = 5):
    search = f"%{name.strip()}%"
    return (
        db.query(Task)
        .options(joinedload(Task.project).joinedload(Project.client))
        .join(Project)
        .filter(Project.client_id == client_id)
        .filter(Task.title.ilike(search))
        .order_by(Task.created_at.desc())
        .limit(limit)
        .all()
    )

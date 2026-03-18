from sqlalchemy.orm import Session

from app.db.models.task_update import TaskUpdate


def create_task_update(
    db: Session,
    task_id: int,
    content: str,
    update_type: str = "manual",
    source: str = "ui",
) -> TaskUpdate:
    task_update = TaskUpdate(
        task_id=task_id,
        content=content,
        update_type=update_type,
        source=source,
    )
    db.add(task_update)
    db.commit()
    db.refresh(task_update)
    return task_update


def get_updates_by_task(db: Session, task_id: int) -> list[TaskUpdate]:
    return (
        db.query(TaskUpdate)
        .filter(TaskUpdate.task_id == task_id)
        .order_by(TaskUpdate.created_at.desc())
        .all()
    )
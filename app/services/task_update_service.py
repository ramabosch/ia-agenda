from app.db.session import SessionLocal
from app.repositories import task_update_repository


def create_task_update(
    task_id: int,
    content: str,
    update_type: str = "manual",
    source: str = "ui",
):
    db = SessionLocal()
    try:
        return task_update_repository.create_task_update(db, task_id, content, update_type, source)
    finally:
        db.close()


def get_updates_by_task(task_id: int):
    db = SessionLocal()
    try:
        return task_update_repository.get_updates_by_task(db, task_id)
    finally:
        db.close()
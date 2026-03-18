from app.db.session import SessionLocal
from app.repositories import project_repository


def create_project(client_id: int, name: str, description: str | None = None):
    db = SessionLocal()
    try:
        return project_repository.create_project(db, client_id, name, description)
    finally:
        db.close()


def get_all_projects():
    db = SessionLocal()
    try:
        return project_repository.get_all_projects(db)
    finally:
        db.close()


def get_projects_by_client(client_id: int):
    db = SessionLocal()
    try:
        return project_repository.get_projects_by_client(db, client_id)
    finally:
        db.close()


def get_project_by_id(project_id: int):
    db = SessionLocal()
    try:
        return project_repository.get_project_by_id(db, project_id)
    finally:
        db.close()

def get_project_operational_summary(project_id: int):
    db = SessionLocal()
    try:
        project = project_repository.get_project_with_tasks(db, project_id)

        if not project:
            return None

        total_tasks = len(project.tasks)
        open_tasks = len([t for t in project.tasks if t.status != "hecha"])
        done_tasks = len([t for t in project.tasks if t.status == "hecha"])
        blocked_tasks = len([t for t in project.tasks if t.status == "bloqueada"])
        in_progress_tasks = len([t for t in project.tasks if t.status == "en_progreso"])

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
    finally:
        db.close()

def get_projects_by_client_id(client_id: int):
    db = SessionLocal()
    try:
        return project_repository.get_projects_by_client_id(db, client_id)
    finally:
        db.close()


def get_project_by_name_and_client(name: str, client_id: int):
    db = SessionLocal()
    try:
        return project_repository.get_project_by_name_and_client(db, name, client_id)
    finally:
        db.close()


def get_project_by_name(name: str):
    db = SessionLocal()
    try:
        return project_repository.get_project_by_name(db, name)
    finally:
        db.close()

def search_projects_by_name(name: str, limit: int = 5):
    db = SessionLocal()
    try:
        return project_repository.search_projects_by_name(db, name, limit)
    finally:
        db.close()


def search_projects_by_name_and_client_id(name: str, client_id: int, limit: int = 5):
    db = SessionLocal()
    try:
        return project_repository.search_projects_by_name_and_client_id(db, name, client_id, limit)
    finally:
        db.close()
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


def get_all_projects_with_tasks():
    db = SessionLocal()
    try:
        return project_repository.get_all_projects_with_tasks(db)
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


def get_executive_project_snapshot() -> dict:
    projects = get_all_projects_with_tasks()
    items = []

    for project in projects:
        open_tasks = [task for task in project.tasks if task.status != "hecha"]
        blocked_tasks = [task for task in open_tasks if task.status == "bloqueada"]
        high_priority_open = [task for task in open_tasks if task.priority == "alta"]
        overdue_open = [task for task in open_tasks if getattr(task, "due_date", None)]
        overdue_open = [task for task in overdue_open if task.due_date and task.status != "hecha"]

        score = (
            len(blocked_tasks) * 5
            + len(high_priority_open) * 3
            + len(open_tasks) * 2
            + len(overdue_open) * 2
        )

        items.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "client_id": project.client.id if project.client else None,
                "client_name": project.client.name if project.client else "Desconocido",
                "status": project.status,
                "open_tasks": len(open_tasks),
                "blocked_tasks": len(blocked_tasks),
                "high_priority_open_tasks": len(high_priority_open),
                "overdue_open_tasks": len(overdue_open),
                "score": score,
            }
        )

    ranked = sorted(
        [item for item in items if item["open_tasks"] > 0],
        key=lambda item: (-item["score"], item["project_name"]),
    )

    return {
        "projects": items,
        "prioritized_projects": ranked[:5],
        "heuristic": [
            "mas bloqueadas pesa mas",
            "despues mas alta prioridad abierta",
            "despues mayor acumulacion abierta",
            "despues vencimientos abiertos",
        ],
    }

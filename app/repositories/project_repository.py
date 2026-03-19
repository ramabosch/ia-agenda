from sqlalchemy.orm import Session, joinedload

from app.db.models.project import Project
from app.db.models.task import Task


def create_project(db: Session, client_id: int, name: str, description: str | None = None) -> Project:
    project = Project(client_id=client_id, name=name, description=description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_projects_by_client(db: Session, client_id: int) -> list[Project]:
    return (
        db.query(Project)
        .options(joinedload(Project.client))
        .filter(Project.client_id == client_id)
        .order_by(Project.id.desc())
        .all()
    )


def get_all_projects(db: Session) -> list[Project]:
    return db.query(Project).options(joinedload(Project.client)).order_by(Project.id.desc()).all()


def get_all_projects_with_tasks(db: Session) -> list[Project]:
    return (
        db.query(Project)
        .options(joinedload(Project.client), joinedload(Project.tasks))
        .order_by(Project.created_at.desc())
        .all()
    )


def get_project_by_id(db: Session, project_id: int) -> Project | None:
    return db.query(Project).filter(Project.id == project_id).first()

def get_project_with_tasks(db: Session, project_id: int) -> Project | None:
    return (
        db.query(Project)
        .options(joinedload(Project.client), joinedload(Project.tasks))
        .filter(Project.id == project_id)
        .first()
    )

def get_projects_by_client_id(db: Session, client_id: int):
    return (
        db.query(Project)
        .options(joinedload(Project.client))
        .filter(Project.client_id == client_id)
        .order_by(Project.created_at.desc())
        .all()
    )


def get_project_by_name_and_client(db: Session, name: str, client_id: int):
    search = f"%{name.strip()}%"
    return (
        db.query(Project)
        .filter(Project.client_id == client_id)
        .filter(Project.name.ilike(search))
        .order_by(Project.name.asc())
        .first()
    )


def get_project_by_name(db: Session, name: str):
    search = f"%{name.strip()}%"
    return (
        db.query(Project)
        .filter(Project.name.ilike(search))
        .order_by(Project.name.asc())
        .first()
    )

def search_projects_by_name(db: Session, name: str, limit: int = 5):
    search = f"%{name.strip()}%"
    return (
        db.query(Project)
        .filter(Project.name.ilike(search))
        .order_by(Project.created_at.desc())
        .limit(limit)
        .all()
    )


def search_projects_by_name_and_client_id(db: Session, name: str, client_id: int, limit: int = 5):
    search = f"%{name.strip()}%"
    return (
        db.query(Project)
        .filter(Project.client_id == client_id)
        .filter(Project.name.ilike(search))
        .order_by(Project.created_at.desc())
        .limit(limit)
        .all()
    )

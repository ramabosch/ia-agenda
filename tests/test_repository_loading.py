import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models.client import Client
from app.db.models.project import Project
from app.db.models.task import Task
from datetime import date, timedelta

from app.repositories.project_repository import get_all_projects, search_projects_by_name
from app.repositories.task_repository import get_all_tasks, get_overdue_tasks, get_tasks_by_status
from app.services.task_service import build_friction_focus_from_tasks, build_recommendation_focus_from_tasks


class RepositoryLoadingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_get_all_tasks_keeps_project_and_client_accessible_after_session_close(self):
        db: Session = self.SessionLocal()
        client = Client(name="CAM")
        db.add(client)
        db.flush()

        project = Project(client_id=client.id, name="Dashboard")
        db.add(project)
        db.flush()

        task = Task(project_id=project.id, title="Indicadores del dashboard")
        db.add(task)
        db.commit()
        db.close()

        db = self.SessionLocal()
        tasks = get_all_tasks(db)
        db.close()

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].project.name, "Dashboard")
        self.assertEqual(tasks[0].project.client.name, "CAM")

    def test_get_all_projects_keeps_client_accessible_after_session_close(self):
        db: Session = self.SessionLocal()
        client = Client(name="CAM")
        db.add(client)
        db.flush()

        project = Project(client_id=client.id, name="Dashboard")
        db.add(project)
        db.commit()
        db.close()

        db = self.SessionLocal()
        projects = get_all_projects(db)
        db.close()

        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].name, "Dashboard")
        self.assertEqual(projects[0].client.name, "CAM")

    def test_search_projects_by_name_keeps_client_accessible_after_session_close(self):
        db: Session = self.SessionLocal()
        client = Client(name="CAM")
        db.add(client)
        db.flush()

        project = Project(client_id=client.id, name="Dashboard comercial")
        db.add(project)
        db.commit()
        db.close()

        db = self.SessionLocal()
        projects = search_projects_by_name(db, "dashboard")
        db.close()

        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].client.name, "CAM")

    def test_friction_and_recommendation_builders_support_detached_tasks(self):
        db: Session = self.SessionLocal()
        client = Client(name="CAM")
        db.add(client)
        db.flush()

        project = Project(client_id=client.id, name="Dashboard")
        db.add(project)
        db.flush()

        old_blocked = Task(
            project_id=project.id,
            title="Resolver API",
            status="bloqueada",
            priority="alta",
            due_date=date.today() - timedelta(days=2),
        )
        old_blocked.created_at = date.today() - timedelta(days=20)
        old_blocked.last_updated_at = date.today() - timedelta(days=10)
        db.add(old_blocked)
        db.commit()
        db.close()

        db = self.SessionLocal()
        tasks = get_tasks_by_status(db, "bloqueada")
        db.close()

        friction = build_friction_focus_from_tasks(tasks, today=date.today())
        recommendation = build_recommendation_focus_from_tasks(tasks, today=date.today())

        self.assertEqual(friction["friction_tasks"][0]["title"], "Resolver API")
        self.assertEqual(recommendation["recommendations"][0]["title"], "Resolver API")


if __name__ == "__main__":
    unittest.main()

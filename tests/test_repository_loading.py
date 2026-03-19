import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models.client import Client
from app.db.models.project import Project
from app.db.models.task import Task
from app.repositories.project_repository import get_all_projects
from app.repositories.task_repository import get_all_tasks


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


if __name__ == "__main__":
    unittest.main()

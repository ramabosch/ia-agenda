import unittest
from datetime import date
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from app.services.task_service import get_executive_task_snapshot
from tests.helpers import make_client, make_project, make_task


class ExecutiveBehaviorTests(unittest.TestCase):
    def test_task_snapshot_prioritizes_blocked_first(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver bloqueo API", project, status="bloqueada", priority="alta")
        progress = make_task(101, "Disenar flujo", project, status="en_progreso", priority="alta")

        with patch("app.services.task_service.get_all_tasks_with_relations", return_value=[progress, blocked]):
            snapshot = get_executive_task_snapshot(today=date(2026, 3, 18))

        self.assertEqual(snapshot["recommended_tasks"][0]["title"], "Resolver bloqueo API")
        self.assertEqual(snapshot["blocked_tasks"][0]["title"], "Resolver bloqueo API")

    def test_blocked_summary_query_returns_spanish_response(self):
        task_snapshot = {
            "heuristic": ["bloqueadas primero"],
            "recommended_tasks": [{"title": "Resolver bloqueo API", "project_name": "Dashboard", "client_name": "CAM"}],
            "blocked_tasks": [
                {
                    "title": "Resolver bloqueo API",
                    "project_name": "Dashboard",
                    "client_name": "CAM",
                    "priority": "alta",
                }
            ],
            "open_tasks": [],
            "urgent_tasks": [],
        }
        project_snapshot = {
            "prioritized_projects": [
                {"project_name": "Dashboard", "client_name": "CAM", "blocked_tasks": 1, "open_tasks": 2}
            ]
        }

        with patch("app.services.query_response_service.get_executive_task_snapshot", return_value=task_snapshot), patch(
            "app.services.query_response_service.get_executive_project_snapshot",
            return_value=project_snapshot,
        ):
            parsed = parse_user_query("que esta bloqueado")
            response = build_response_from_query(parsed, user_query="que esta bloqueado", conversation_context={})

        self.assertIn("esto esta bloqueado ahora", response.lower())
        self.assertIn("resolver bloqueo api", response.lower())
        self.assertEqual(parsed.get("_executive_scope"), "global")

    def test_client_attention_query_prioritizes_top_client(self):
        task_snapshot = {
            "heuristic": ["bloqueadas primero"],
            "recommended_tasks": [{"title": "Resolver bloqueo API", "project_name": "Dashboard", "client_name": "CAM"}],
            "open_tasks": [
                {
                    "client_id": 1,
                    "client_name": "CAM",
                    "project_name": "Dashboard",
                    "is_blocked": True,
                    "is_high_priority": True,
                    "is_overdue": False,
                },
                {
                    "client_id": 1,
                    "client_name": "CAM",
                    "project_name": "Dashboard",
                    "is_blocked": False,
                    "is_high_priority": True,
                    "is_overdue": False,
                },
                {
                    "client_id": 2,
                    "client_name": "Dallas",
                    "project_name": "CRM",
                    "is_blocked": False,
                    "is_high_priority": False,
                    "is_overdue": False,
                },
            ],
            "blocked_tasks": [],
            "urgent_tasks": [],
        }

        with patch("app.services.query_response_service.get_executive_task_snapshot", return_value=task_snapshot), patch(
            "app.services.query_response_service.get_executive_project_snapshot",
            return_value={"prioritized_projects": []},
        ):
            parsed = parse_user_query("que cliente necesita atencion primero")
            response = build_response_from_query(parsed, user_query="que cliente necesita atencion primero", conversation_context={})

        self.assertIn("el cliente que necesita atencion primero es cam", response.lower())
        self.assertEqual(parsed.get("_executive_scope"), "global")


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from app.services.task_service import build_friction_focus_from_tasks
from tests.helpers import make_client, make_project, make_task, make_task_summary


class FrictionBehaviorTests(unittest.TestCase):
    def test_friction_detects_old_blocked_task(self):
        today = date(2026, 3, 18)
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(
            100,
            "Resolver bloqueo API",
            project,
            status="bloqueada",
            priority="alta",
            created_at=datetime(2026, 3, 1, 10, 0, 0),
            last_updated_at=datetime(2026, 3, 2, 10, 0, 0),
        )

        snapshot = build_friction_focus_from_tasks([task], today=today)

        self.assertEqual(snapshot["friction_tasks"][0]["title"], "Resolver bloqueo API")
        self.assertIn("bloqueada", snapshot["friction_tasks"][0]["friction_signals"])
        self.assertTrue(
            any(
                signal in snapshot["friction_tasks"][0]["friction_signals"]
                for signal in ("bloqueada hace tiempo", "friccion probable sin evidencia temporal fuerte")
            )
        )

    def test_friction_flags_high_priority_without_next_action(self):
        today = date(2026, 3, 18)
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(100, "Definir indicadores", project, priority="alta", next_action=None)

        snapshot = build_friction_focus_from_tasks([task], today=today)

        self.assertIn("alta prioridad sin proxima accion", snapshot["friction_tasks"][0]["friction_signals"])

    def test_project_with_many_open_tasks_accumulates_friction(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        old_blocked = make_task(
            100,
            "Resolver API",
            project,
            status="bloqueada",
            created_at=datetime(2026, 3, 1, 10, 0, 0),
            last_updated_at=datetime(2026, 3, 2, 10, 0, 0),
        )
        no_followup = make_task(101, "Definir copy", project, priority="alta")
        parsed = parse_user_query("que proyecto esta acumulando friccion")

        project_snapshot = {
            "prioritized_projects": [
                {
                    "project_name": "Dashboard",
                    "client_name": "CAM",
                    "friction_tasks": 2,
                    "blocked_tasks": 1,
                    "without_next_action": 2,
                }
            ]
        }

        with patch("app.services.query_response_service.get_operational_friction_snapshot", return_value=build_friction_focus_from_tasks([old_blocked, no_followup], today=date(2026, 3, 18))), patch(
            "app.services.query_response_service.get_operational_friction_project_snapshot",
            return_value=project_snapshot,
        ), patch(
            "app.services.query_response_service._build_client_friction_snapshot",
            return_value={"prioritized_clients": []},
        ):
            response = build_response_from_query(parsed, user_query="que proyecto esta acumulando friccion", conversation_context={})

        self.assertIn("proyectos con mas friccion", response.lower())
        self.assertIn("dashboard", response.lower())

    def test_client_with_accumulation_uses_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(
            100,
            "Resolver API",
            project,
            status="bloqueada",
            priority="alta",
            created_at=datetime(2026, 3, 1, 10, 0, 0),
            last_updated_at=datetime(2026, 3, 2, 10, 0, 0),
        )
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.query_response_service.get_tasks_by_client_id", return_value=[blocked]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ):
            parsed = parse_user_query("que me preocuparia de este cliente")
            response = build_response_from_query(parsed, user_query="que me preocuparia de este cliente", conversation_context=context)

        self.assertIn("lo que me preocuparia de cam", response.lower())
        self.assertEqual(parsed.get("_friction_scope"), "contextual_client")

    def test_friction_keeps_clarification_on_ambiguous_input(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(100, "Dashboard indicadores", project)

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[task],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[],
        ):
            parsed = parse_user_query("que me preocuparia de dashboard")
            response = build_response_from_query(parsed, user_query="que me preocuparia de dashboard", conversation_context={})

        self.assertIn("aclares", response.lower())

    def test_without_temporal_data_does_not_invent_exact_delay(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(100, "Definir indicadores", project, priority="alta", next_action=None)
        task.created_at = None
        task.last_updated_at = None
        summary = make_task_summary(task)

        friction_summary = {
            "scope": "task",
            "entity_name": task.title,
            "status_overview": "Veo friccion probable, pero no puedo afirmar atraso exacto con los datos actuales.",
            "signals": ["alta prioridad sin proxima accion", "friccion probable sin evidencia temporal fuerte"],
            "recommendation": "Definiria una proxima accion concreta hoy, porque sigue prioritaria pero sin seguimiento claro.",
            "heuristic": ["sin dato temporal solo se habla de friccion probable"],
        }

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[],
        ), patch(
            "app.services.query_response_service.get_task_operational_summary",
            return_value=summary,
        ), patch(
            "app.services.query_response_service.build_task_friction_summary",
            return_value=friction_summary,
        ):
            parsed = parse_user_query("que me preocuparia de definir indicadores")
            response = build_response_from_query(parsed, user_query="que me preocuparia de definir indicadores", conversation_context={})

        self.assertIn("no puedo afirmar atraso exacto", response.lower())
        self.assertIn("friccion probable", response.lower())


if __name__ == "__main__":
    unittest.main()

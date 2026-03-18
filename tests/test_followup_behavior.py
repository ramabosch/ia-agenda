import unittest
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_task, make_task_summary


class FollowupBehaviorTests(unittest.TestCase):
    def test_next_actions_for_current_client_uses_context(self):
        client = make_client(2, "CAM")
        project = make_project(20, "Dashboard", client)
        task = make_task(200, "Resolver integracion", project, priority="alta", next_action="Llamar al proveedor")
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_open_tasks_by_client_id",
            return_value=[task],
        ):
            parsed = parse_user_query("que sigue para este cliente")
            response = build_response_from_query(parsed, user_query="que sigue para este cliente", conversation_context=context)

        self.assertIn("lo que sigue para cam", response.lower())
        self.assertIn("llamar al proveedor", response.lower())
        self.assertEqual(parsed.get("_followup_scope"), "contextual_client")

    def test_missing_next_actions_summary_marks_followup_gap(self):
        task_snapshot = {
            "heuristic": ["bloqueadas sin proxima accion primero"],
            "open_tasks": [],
            "tasks_with_next_action": [],
            "tasks_without_next_action": [
                {
                    "title": "Preparar propuesta",
                    "client_name": "CAM",
                    "project_name": "Comercial",
                    "has_next_action": False,
                }
            ],
            "followup_needed_tasks": [],
            "push_today_tasks": [],
        }
        project_snapshot = {
            "prioritized_projects": [
                {"project_name": "Comercial", "client_name": "CAM", "tasks_without_next_action": 1}
            ]
        }

        with patch("app.services.query_response_service.get_followup_task_snapshot", return_value=task_snapshot), patch(
            "app.services.query_response_service.get_followup_project_snapshot",
            return_value=project_snapshot,
        ):
            parsed = parse_user_query("que tareas no tienen proxima accion")
            response = build_response_from_query(parsed, user_query="que tareas no tienen proxima accion", conversation_context={})

        self.assertIn("no tienen proxima accion definida", response.lower())
        self.assertIn("preparar propuesta", response.lower())

    def test_followup_needed_summary_marks_open_without_followup(self):
        task_snapshot = {
            "heuristic": ["bloqueadas sin proxima accion primero"],
            "open_tasks": [],
            "tasks_with_next_action": [],
            "tasks_without_next_action": [],
            "followup_needed_tasks": [
                {
                    "title": "Esperar aprobacion",
                    "client_name": "Dallas",
                    "project_name": "CRM",
                    "has_next_action": False,
                }
            ],
            "push_today_tasks": [],
        }
        project_snapshot = {
            "prioritized_projects": [
                {"project_name": "CRM", "client_name": "Dallas", "blocked_without_next_action": 1}
            ]
        }
        client_snapshot = {
            "prioritized_clients": [
                {"client_name": "Dallas", "tasks_without_next_action": 1, "open_tasks": 1}
            ]
        }

        with patch("app.services.query_response_service.get_followup_task_snapshot", return_value=task_snapshot), patch(
            "app.services.query_response_service.get_followup_project_snapshot",
            return_value=project_snapshot,
        ), patch(
            "app.services.query_response_service._build_client_followup_snapshot",
            return_value=client_snapshot,
        ):
            parsed = parse_user_query("que quedo abierto sin seguimiento")
            response = build_response_from_query(parsed, user_query="que quedo abierto sin seguimiento", conversation_context={})

        self.assertIn("necesita seguimiento", response.lower())
        self.assertIn("esperar aprobacion", response.lower())

    def test_push_today_summary_uses_priority_and_next_action(self):
        task_snapshot = {
            "heuristic": ["bloqueadas sin proxima accion primero"],
            "open_tasks": [],
            "tasks_with_next_action": [],
            "tasks_without_next_action": [],
            "followup_needed_tasks": [],
            "push_today_tasks": [
                {
                    "title": "Resolver integracion",
                    "client_name": "CAM",
                    "project_name": "Dashboard",
                    "has_next_action": True,
                    "next_action": "Llamar al proveedor",
                },
                {
                    "title": "Definir mensaje comercial",
                    "client_name": "Dallas",
                    "project_name": "Comercial",
                    "has_next_action": False,
                },
            ],
        }

        with patch("app.services.query_response_service.get_followup_task_snapshot", return_value=task_snapshot), patch(
            "app.services.query_response_service.get_followup_project_snapshot",
            return_value={"prioritized_projects": []},
        ):
            parsed = parse_user_query("que deberia empujar hoy si o si")
            response = build_response_from_query(parsed, user_query="que deberia empujar hoy si o si", conversation_context={})

        self.assertIn("deberias empujar hoy si o si", response.lower())
        self.assertIn("llamar al proveedor", response.lower())
        self.assertIn("falta definir proxima accion", response.lower())

    def test_contextual_y_que_sigue_uses_safe_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(100, "Resolver integracion", project, next_action="Enviar correo")
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.query_response_service.get_open_tasks_by_client_id", return_value=[task]):
            parsed = parse_user_query("y que sigue?")
            response = build_response_from_query(parsed, user_query="y que sigue?", conversation_context=context)

        self.assertIn("lo que sigue para cam", response.lower())
        self.assertIn("enviar correo", response.lower())

    def test_y_que_sigue_without_context_does_not_invent(self):
        parsed = parse_user_query("y que sigue?")
        response = build_response_from_query(parsed, user_query="y que sigue?", conversation_context={})
        self.assertIn("contexto aislado actual", response.lower())

    def test_task_with_explicit_next_action_uses_it(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Onboarding", client)
        task = make_task(100, "Onboarding", project, next_action="Enviar checklist")
        summary = make_task_summary(task)
        context = {
            "_isolated": True,
            "scope": "task",
            "task": {"id": task.id, "name": task.title},
        }

        with patch("app.services.query_response_service.get_task_operational_summary", return_value=summary):
            parsed = parse_user_query("y que sigue?")
            response = build_response_from_query(parsed, user_query="y que sigue?", conversation_context=context)

        self.assertIn("proximo paso: enviar checklist", response.lower())
        self.assertFalse(parsed.get("_followup_inference_used", True))

    def test_task_without_next_action_marks_missing_followup(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Onboarding", client)
        task = make_task(100, "Onboarding", project, next_action=None)
        summary = make_task_summary(task)
        context = {
            "_isolated": True,
            "scope": "task",
            "task": {"id": task.id, "name": task.title},
        }

        with patch("app.services.query_response_service.get_task_operational_summary", return_value=summary):
            parsed = parse_user_query("y que sigue?")
            response = build_response_from_query(parsed, user_query="y que sigue?", conversation_context=context)

        self.assertIn("no tiene proxima accion definida", response.lower())
        self.assertIn("falta seguimiento", response.lower())


if __name__ == "__main__":
    unittest.main()

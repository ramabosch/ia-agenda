import unittest
from datetime import date
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_task


class CompoundQueryBehaviorTests(unittest.TestCase):
    def test_summary_and_recommendation_are_answered_in_order(self):
        client = make_client(1, "Cam")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver API", project, status="bloqueada", priority="alta")
        parsed = parse_user_query("resumime Cam y decime que haria primero")

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[],
        ), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[],
        ), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=[blocked],
        ):
            response = build_response_from_query(parsed, user_query="resumime Cam y decime que haria primero", conversation_context={})

        self.assertIn("Primero:", response)
        self.assertIn("Despues:", response)
        self.assertIn("Cam", response)
        self.assertEqual(parsed.get("_compound_primary_intent"), "get_operational_summary")
        self.assertEqual(parsed.get("_compound_secondary_intent"), "get_operational_recommendation")
        self.assertIn("get_operational_summary", parsed.get("_compound_resolved_parts", []))

    def test_summary_and_next_steps_reuse_snapshot_within_same_turn(self):
        client = make_client(1, "Cam")
        project = make_project(10, "CRM", client)
        task = make_task(100, "Definir copy", project, next_action="Cerrar copy con marketing")
        project_summary = {
            "project_id": project.id,
            "project_name": project.name,
            "client_id": client.id,
            "client_name": client.name,
            "status": "activo",
            "description": None,
            "total_tasks": 1,
            "open_tasks": 1,
            "done_tasks": 0,
            "blocked_tasks": 0,
            "in_progress_tasks": 0,
        }
        advanced_summary = {
            "scope": "project",
            "project_id": project.id,
            "entity_name": project.name,
            "client_id": client.id,
            "client_name": client.name,
            "status_overview": "Hay 1 tarea abierta en este proyecto.",
            "important_pending": [
                {
                    "title": task.title,
                    "project_name": project.name,
                    "client_name": client.name,
                    "status": task.status,
                    "priority": task.priority,
                    "has_next_action": True,
                    "next_action": task.next_action,
                }
            ],
            "risk_items": [],
            "attention_items": [],
            "next_steps": [
                {
                    "title": task.title,
                    "project_name": project.name,
                    "client_name": client.name,
                    "status": task.status,
                    "priority": task.priority,
                    "has_next_action": True,
                    "next_action": task.next_action,
                }
            ],
            "recommendation": "Empujaria el siguiente paso ya definido.",
            "heuristic": ["prioriza lo abierto con siguiente paso"],
        }
        parsed = parse_user_query("comentame CRM y despues decime que sigue")

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[],
        ), patch(
            "app.services.query_response_service.get_project_operational_summary",
            return_value=project_summary,
        ), patch(
            "app.services.query_response_service.get_project_advanced_summary",
            return_value=advanced_summary,
        ), patch(
            "app.services.query_response_service.get_tasks_by_project_id",
            return_value=[task],
        ):
            response = build_response_from_query(parsed, user_query="comentame CRM y despues decime que sigue", conversation_context={})

        self.assertIn("Primero:", response)
        self.assertIn("Despues:", response)
        self.assertIn("CRM", response)
        self.assertTrue(parsed.get("_compound_reused_snapshot"))

    def test_friction_and_client_message_can_be_combined(self):
        client = make_client(1, "Cam")
        project = make_project(10, "Dashboard", client)
        task = make_task(100, "Resolver API", project, status="bloqueada", priority="alta")
        parsed = parse_user_query("que me preocuparia de Cam y que le diria al cliente")

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[],
        ), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[],
        ), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=[task],
        ):
            response = build_response_from_query(parsed, user_query="que me preocuparia de Cam y que le diria al cliente", conversation_context={})

        self.assertIn("Primero:", response)
        self.assertIn("Despues:", response)
        self.assertIn("cliente", response.lower())
        self.assertTrue(parsed.get("_compound_reused_snapshot"))

    def test_safe_part_and_degraded_part_are_both_reported(self):
        parsed = parse_user_query("por que esa y que vence hoy")
        temporal_snapshot = {
            "today": date(2026, 3, 19).isoformat(),
            "time_scope": "today",
            "temporal_focus": None,
            "matched_items": [
                {
                    "title": "Cerrar copy",
                    "project_name": "CRM",
                    "client_name": "Cam",
                    "status": "pendiente",
                    "priority": "alta",
                    "is_blocked": False,
                    "has_next_action": True,
                    "next_action": "Validar con marketing",
                }
            ],
            "missing_due_items": [],
            "degraded": False,
        }

        with patch("app.services.query_response_service.get_temporal_task_snapshot", return_value=temporal_snapshot):
            response = build_response_from_query(parsed, user_query="por que esa y que vence hoy", conversation_context={})

        self.assertIn("Primero:", response)
        self.assertIn("Despues:", response)
        self.assertIn("no tengo contexto aislado actual", response.lower())
        self.assertIn("get_recommendation_explanation", parsed.get("_compound_degraded_parts", []))
        self.assertIn("get_due_tasks_summary", parsed.get("_compound_resolved_parts", []))

    def test_ambiguous_first_part_keeps_partial_clarification(self):
        client = make_client(1, "Cam")
        project = make_project(10, "Dashboard", client)
        task = make_task(100, "Dashboard indicadores", project)
        parsed = parse_user_query("comentame dashboard y despues decime que sigue")

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[task],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[],
        ):
            response = build_response_from_query(parsed, user_query="comentame dashboard y despues decime que sigue", conversation_context={})

        self.assertIn("aclares", response.lower())
        self.assertTrue(parsed.get("_compound_partial_clarification"))
        self.assertTrue(parsed.get("_compound_degraded_parts"))

    def test_compound_query_never_executes_creation(self):
        parsed = parse_user_query("que vence hoy y crea una tarea para revisar indicadores")
        temporal_snapshot = {
            "today": date(2026, 3, 19).isoformat(),
            "time_scope": "today",
            "temporal_focus": None,
            "matched_items": [],
            "missing_due_items": [],
            "degraded": False,
        }

        with patch("app.services.query_response_service.get_temporal_task_snapshot", return_value=temporal_snapshot), patch(
            "app.services.query_response_service.create_task_conversational",
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="que vence hoy y crea una tarea para revisar indicadores", conversation_context={})

        create_mock.assert_not_called()
        self.assertIn("no ejecute la parte de accion", response.lower())
        self.assertIn("create_task", parsed.get("_compound_degraded_parts", []))


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_task, make_task_summary


class OperationalSummaryBehaviorTests(unittest.TestCase):
    def test_client_operational_summary_is_prioritized_and_human(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver bloqueo API", project, status="bloqueada", priority="alta")
        needs_definition = make_task(101, "Definir indicadores", project, priority="alta")
        next_step = make_task(102, "Cerrar copy", project, next_action="Validar copy final")

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=[blocked, needs_definition, next_step],
        ):
            parsed = parse_user_query("comentame en que andamos con Cam")
            response = build_response_from_query(parsed, user_query="comentame en que andamos con Cam", conversation_context={})

        self.assertIn("resumen del cliente cam", response.lower())
        self.assertIn("estado general", response.lower())
        self.assertIn("bloqueos o riesgos", response.lower())
        self.assertIn("resolver bloqueo api", response.lower())
        self.assertIn("recomendacion", response.lower())
        self.assertEqual(parsed.get("_summary_scope"), "client")

    def test_project_operational_summary_uses_project_snapshot(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        advanced = {
            "scope": "project",
            "entity_name": "Dashboard",
            "status_overview": "Hay 2 tareas abiertas en este proyecto. 1 estan bloqueadas.",
            "important_pending": [
                {"title": "Resolver indicadores", "project_name": "Dashboard", "client_name": "CAM", "is_blocked": True}
            ],
            "risk_items": [
                {"title": "Resolver indicadores", "project_name": "Dashboard", "client_name": "CAM", "is_blocked": True}
            ],
            "attention_items": [],
            "next_steps": [],
            "recommendation": "Primero destrabaria 'Resolver indicadores', porque hoy es el mayor freno operativo.",
            "heuristic": ["bloqueadas arriba"],
        }
        summary = {
            "project_id": 10,
            "project_name": "Dashboard",
            "client_id": 1,
            "client_name": "CAM",
            "status": "activo",
            "description": None,
            "total_tasks": 2,
            "open_tasks": 2,
            "done_tasks": 0,
            "blocked_tasks": 1,
            "in_progress_tasks": 1,
        }

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[],
        ), patch(
            "app.services.query_response_service.get_project_operational_summary",
            return_value=summary,
        ), patch(
            "app.services.query_response_service.get_project_advanced_summary",
            return_value=advanced,
        ):
            parsed = parse_user_query("como viene dashboard")
            response = build_response_from_query(parsed, user_query="como viene dashboard", conversation_context={})

        self.assertIn("resumen del proyecto dashboard", response.lower())
        self.assertIn("resolver indicadores", response.lower())
        self.assertIn("no veo un proximo paso explicito", response.lower())

    def test_operational_summary_reduces_repetition_across_sections(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        repeated = {
            "task_id": 100,
            "title": "Resolver indicadores",
            "project_name": "Dashboard",
            "client_name": "CAM",
            "is_blocked": True,
            "is_high_priority": True,
            "missing_next_action": True,
            "has_next_action": False,
            "next_action": None,
        }
        advanced = {
            "scope": "project",
            "entity_name": "Dashboard",
            "status_overview": "Hay 1 tarea abierta en este proyecto.",
            "important_pending": [repeated],
            "risk_items": [repeated],
            "attention_items": [repeated],
            "next_steps": [repeated],
            "recommendation": "Primero destrabaria 'Resolver indicadores'.",
            "heuristic": ["bloqueadas arriba"],
        }
        summary = {
            "project_id": 10,
            "project_name": "Dashboard",
            "client_id": 1,
            "client_name": "CAM",
            "status": "activo",
            "description": None,
            "total_tasks": 1,
            "open_tasks": 1,
            "done_tasks": 0,
            "blocked_tasks": 1,
            "in_progress_tasks": 0,
        }

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[],
        ), patch(
            "app.services.query_response_service.get_project_operational_summary",
            return_value=summary,
        ), patch(
            "app.services.query_response_service.get_project_advanced_summary",
            return_value=advanced,
        ):
            parsed = parse_user_query("como viene dashboard")
            response = build_response_from_query(parsed, user_query="como viene dashboard", conversation_context={})

        self.assertLessEqual(response.lower().count("resolver indicadores"), 3)

    def test_task_operational_summary_uses_explicit_next_action_when_present(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(100, "Indicadores del dashboard", project, status="en_progreso", priority="alta", next_action="Validar metricas")
        summary = make_task_summary(task)

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[],
        ), patch(
            "app.services.query_response_service.get_task_operational_summary",
            return_value=summary,
        ):
            parsed = parse_user_query("como estamos con indicadores del dashboard")
            response = build_response_from_query(parsed, user_query="como estamos con indicadores del dashboard", conversation_context={})

        self.assertIn("resumen de la tarea", response.lower())
        self.assertIn("proximo paso explicito: validar metricas", response.lower())
        self.assertIn("yo empujaria este proximo paso", response.lower())

    def test_contextual_summary_followup_uses_safe_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        context = {
            "_isolated": True,
            "scope": "project",
            "project": {"id": project.id, "name": project.name},
            "client": {"id": client.id, "name": client.name},
        }
        advanced = {
            "scope": "project",
            "entity_name": "Dashboard",
            "status_overview": "Hay 1 tarea abierta en este proyecto.",
            "important_pending": [
                {"title": "Resolver indicadores", "project_name": "Dashboard", "client_name": "CAM", "is_high_priority": True}
            ],
            "risk_items": [],
            "attention_items": [],
            "next_steps": [],
            "recommendation": "Definiria una proxima accion concreta para 'Resolver indicadores' antes de seguir sumando pendientes.",
            "heuristic": ["bloqueadas arriba"],
        }
        summary = {
            "project_id": 10,
            "project_name": "Dashboard",
            "client_id": 1,
            "client_name": "CAM",
            "status": "activo",
            "description": None,
            "total_tasks": 1,
            "open_tasks": 1,
            "done_tasks": 0,
            "blocked_tasks": 0,
            "in_progress_tasks": 1,
        }

        with patch("app.services.query_response_service.get_project_operational_summary", return_value=summary), patch(
            "app.services.query_response_service.get_project_advanced_summary",
            return_value=advanced,
        ):
            parsed = parse_user_query("que es lo mas importante aca")
            response = build_response_from_query(parsed, user_query="que es lo mas importante aca", conversation_context=context)

        self.assertIn("resumen del proyecto dashboard", response.lower())
        self.assertEqual(parsed.get("_summary_scope"), "contextual_project")

    def test_ambiguous_operational_summary_keeps_clarification(self):
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
            parsed = parse_user_query("como viene dashboard")
            response = build_response_from_query(parsed, user_query="como viene dashboard", conversation_context={})

        self.assertIn("aclares", response.lower())
        self.assertIn("dashboard", response.lower())


if __name__ == "__main__":
    unittest.main()

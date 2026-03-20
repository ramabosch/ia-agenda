import unittest
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_task


class ResponseUxBehaviorTests(unittest.TestCase):
    def test_create_confirmation_is_clear_and_direct(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        create_result = {
            "created": True,
            "task_id": 200,
            "task_title": "definir metricas",
            "project_id": project.id,
            "priority": "media",
            "next_action": None,
            "last_note": None,
        }
        parsed = parse_user_query("agrega una tarea a Cam para definir metricas")

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.create_task_conversational",
            return_value=create_result,
        ):
            response = build_response_from_query(parsed, user_query="agrega una tarea a Cam para definir metricas", conversation_context={})

        self.assertIn("listo:", response.lower())
        self.assertIn("cree la tarea", response.lower())
        self.assertIn("dashboard", response.lower())
        self.assertIn("prioridad: media", response.lower())

    def test_update_confirmation_is_clear_and_direct(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Marketing", client)
        task = make_task(101, "Formulario de contacto", project)
        parsed = parse_user_query("cerra la del formulario")
        context = {"_isolated": True, "scope": "project", "project": {"id": project.id, "name": project.name}}
        update_result = {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "status",
            "old_value": "pendiente",
            "new_value": "hecha",
            "task": task,
        }

        with patch("app.services.reference_resolver.get_tasks_by_project_id", return_value=[task]), patch(
            "app.services.query_response_service.update_task_status_conversational",
            return_value=update_result,
        ):
            response = build_response_from_query(parsed, user_query="cerra la del formulario", conversation_context=context)

        self.assertIn("listo:", response.lower())
        self.assertIn("actualice la tarea", response.lower())
        self.assertIn("estado:", response.lower())

    def test_clarification_is_more_legible(self):
        client = make_client(1, "CAM")
        sales = make_project(10, "Dashboard ventas", client)
        commercial = make_project(11, "Dashboard comercial", client)
        parsed = {"intent": "clarify_entity_reference", "entity_hint": "dashboard", "expected_scope": "project"}

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[sales, commercial],
        ), patch("app.services.reference_resolver.get_all_tasks", return_value=[]):
            response = build_response_from_query(parsed, user_query="dashboard", conversation_context={})

        self.assertTrue(
            "estas son las opciones que mejor matchean" in response.lower()
            or "estas son las coincidencias posibles que mejor matchean" in response.lower()
        )
        self.assertIn("dashboard ventas", response.lower())
        self.assertIn("cliente: cam", response.lower())

    def test_compound_partial_degradation_is_explained(self):
        parsed = parse_user_query("por que esa y que vence hoy")
        temporal_snapshot = {
            "today": "2026-03-19",
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

        self.assertIn("pude resolver una parte del pedido", response.lower())
        self.assertIn("primero:", response.lower())
        self.assertIn("despues:", response.lower())

    def test_missing_safe_context_message_stays_clear(self):
        parsed = parse_user_query("por que esa")
        response = build_response_from_query(parsed, user_query="por que esa", conversation_context={})
        self.assertIn("no tengo contexto aislado actual", response.lower())
        self.assertIn("con seguridad", response.lower())

    def test_audit_response_is_conversational(self):
        trace = {
            "intent": "get_operational_summary",
            "action_status": "informational",
            "summary": "Resumen del cliente CAM",
            "resolved_entities": {"client": {"name": "CAM"}},
        }
        context = {"_isolated": True, "scope": "client", "audit_trace": trace}
        parsed = parse_user_query("que hiciste recien")

        response = build_response_from_query(parsed, user_query="que hiciste recien", conversation_context=context)

        self.assertIn("recien te resumi", response.lower())
        self.assertIn("cam", response.lower())
        self.assertNotIn("get_operational_summary", response.lower())


if __name__ == "__main__":
    unittest.main()

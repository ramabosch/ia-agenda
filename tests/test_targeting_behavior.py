import unittest
from unittest.mock import patch

from app.services.query_response_service import build_response_from_query
from app.services.reference_resolver import resolve_references
from tests.helpers import make_client, make_project, make_task


class FineTargetingBehaviorTests(unittest.TestCase):
    def test_resolves_project_by_type_descriptor_and_client(self):
        client = make_client(1, "Cam")
        sales = make_project(10, "Dashboard ventas", client)
        commercial = make_project(11, "Dashboard comercial", client)

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.reference_resolver.get_projects_by_client_id",
            return_value=[sales, commercial],
        ), patch("app.services.reference_resolver.get_all_tasks", return_value=[]):
            resolved = resolve_references(
                {
                    "intent": "get_operational_summary",
                    "project_name": "dashboard ventas",
                    "client_name": "cam",
                    "expected_scope": "project",
                    "secondary_descriptor": "ventas",
                },
                user_query="comentame el proyecto de dashboard ventas de Cam",
                conversation_context={},
            )

        self.assertEqual(resolved["scope"], "project")
        self.assertEqual(resolved["project"]["resolved"]["id"], 10)
        self.assertFalse(resolved["clarification_needed"])

    def test_prefers_expected_type_over_superficial_cross_scope_match(self):
        client = make_client(1, "Cam")
        project = make_project(10, "Dashboard ventas", client)
        task = make_task(101, "Dashboard ventas", project)

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[project],
        ), patch("app.services.reference_resolver.get_all_tasks", return_value=[task]):
            resolved = resolve_references(
                {
                    "intent": "clarify_entity_reference",
                    "entity_hint": "dashboard ventas",
                    "expected_scope": "project",
                    "secondary_descriptor": "ventas",
                },
                user_query="quiero ver el dashboard ventas",
                conversation_context={},
            )

        self.assertEqual(resolved["scope"], "project")
        self.assertEqual(resolved["project"]["resolved"]["id"], 10)
        self.assertFalse(resolved["clarification_needed"])

    def test_uses_previous_candidates_with_descriptor_followup(self):
        client = make_client(1, "Cam")
        sales = make_project(10, "Dashboard ventas", client)
        commercial = make_project(11, "Dashboard comercial", client)
        context = {
            "_isolated": True,
            "scope": "none",
            "clarification_expected_scope": "project",
            "clarification_candidates": [
                {"id": 10, "name": "Dashboard ventas", "scope": "project", "confidence": 0.93, "client_name": "Cam"},
                {"id": 11, "name": "Dashboard comercial", "scope": "project", "confidence": 0.92, "client_name": "Cam"},
            ],
        }

        with patch("app.services.reference_resolver.get_all_projects", return_value=[sales, commercial]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[],
        ), patch("app.services.reference_resolver.get_all_clients", return_value=[client]):
            resolved = resolve_references(
                {
                    "intent": "clarify_entity_reference",
                    "entity_hint": "ventas",
                    "secondary_descriptor": "ventas",
                    "use_previous_candidates": True,
                },
                user_query="el de ventas",
                conversation_context=context,
            )

        self.assertEqual(resolved["project"]["resolved"]["id"], 10)
        self.assertFalse(resolved["clarification_needed"])

    def test_not_the_other_reuses_previous_candidates(self):
        client = make_client(1, "Cam")
        sales = make_project(10, "Dashboard ventas", client)
        commercial = make_project(11, "Dashboard comercial", client)
        context = {
            "_isolated": True,
            "scope": "none",
            "clarification_expected_scope": "project",
            "clarification_candidates": [
                {"id": 10, "name": "Dashboard ventas", "scope": "project", "confidence": 0.93, "client_name": "Cam"},
                {"id": 11, "name": "Dashboard comercial", "scope": "project", "confidence": 0.92, "client_name": "Cam"},
            ],
        }

        with patch("app.services.reference_resolver.get_all_projects", return_value=[sales, commercial]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[],
        ), patch("app.services.reference_resolver.get_all_clients", return_value=[client]):
            resolved = resolve_references(
                {
                    "intent": "clarify_entity_reference",
                    "use_previous_candidates": True,
                    "contrast_hint": "exclude_other",
                },
                user_query="no el otro",
                conversation_context=context,
            )

        self.assertEqual(resolved["project"]["resolved"]["id"], 10)
        self.assertFalse(resolved["clarification_needed"])

    def test_in_dashboard_comercial_reuses_previous_candidates(self):
        client = make_client(1, "Cam")
        sales = make_project(10, "Dashboard ventas", client)
        commercial = make_project(11, "Dashboard comercial", client)
        context = {
            "_isolated": True,
            "scope": "none",
            "clarification_expected_scope": "project",
            "clarification_candidates": [
                {"id": 10, "name": "Dashboard ventas", "scope": "project", "confidence": 0.93, "client_name": "Cam"},
                {"id": 11, "name": "Dashboard comercial", "scope": "project", "confidence": 0.92, "client_name": "Cam"},
            ],
        }

        with patch("app.services.reference_resolver.get_all_projects", return_value=[sales, commercial]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[],
        ), patch("app.services.reference_resolver.get_all_clients", return_value=[client]):
            resolved = resolve_references(
                {
                    "intent": "clarify_entity_reference",
                    "entity_hint": "dashboard comercial",
                    "use_previous_candidates": True,
                },
                user_query="en dashboard comercial",
                conversation_context=context,
            )

        self.assertEqual(resolved["project"]["resolved"]["id"], 11)
        self.assertFalse(resolved["clarification_needed"])

    def test_specific_clarification_lists_typed_candidates(self):
        client = make_client(1, "Cam")
        sales = make_project(10, "Dashboard ventas", client)
        commercial = make_project(11, "Dashboard comercial", client)

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[sales, commercial],
        ), patch("app.services.reference_resolver.get_all_tasks", return_value=[]):
            parsed = {
                "intent": "clarify_entity_reference",
                "entity_hint": "dashboard",
                "expected_scope": "project",
            }
            response = build_response_from_query(parsed, user_query="dashboard", conversation_context={})

        self.assertIn("cual proyecto queres", response.lower())
        self.assertIn("dashboard ventas", response.lower())
        self.assertIn("cliente: cam", response.lower())

    def test_create_is_blocked_when_targeting_stays_ambiguous(self):
        client = make_client(1, "Cam")
        sales = make_project(10, "Dashboard ventas", client)
        commercial = make_project(11, "Dashboard comercial", client)

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[sales, commercial],
        ), patch("app.services.reference_resolver.get_all_tasks", return_value=[]), patch(
            "app.services.query_response_service.create_task_conversational"
        ) as create_task_mock:
            parsed = {
                "intent": "create_task",
                "project_name": "dashboard",
                "task_name": "revisar indicadores",
                "expected_scope": "project",
            }
            response = build_response_from_query(
                parsed,
                user_query="agrega una tarea al proyecto de dashboard: revisar indicadores",
                conversation_context={},
            )

        create_task_mock.assert_not_called()
        self.assertIn("coincidencias posibles", response.lower())


if __name__ == "__main__":
    unittest.main()

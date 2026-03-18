import unittest
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_task, make_task_summary


class ClarificationBehaviorTests(unittest.TestCase):
    def test_unique_open_reference_resolves_normally(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Operaciones", client)
        task = make_task(100, "Onboarding comercial", project)
        summary = make_task_summary(task)

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]), patch(
            "app.services.query_response_service.get_task_operational_summary",
            return_value=summary,
        ):
            parsed = parse_user_query("onboarding")
            response = build_response_from_query(parsed, user_query="onboarding", conversation_context={})

        self.assertIn("resumen de la tarea", response.lower())
        self.assertIn("onboarding comercial", response.lower())

    def test_ambiguous_dashboard_requests_clarification(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(101, "Dashboard indicadores", project)

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[task],
        ):
            parsed = parse_user_query("dashboard")
            response = build_response_from_query(parsed, user_query="dashboard", conversation_context={})

        self.assertIn("aclares", response.lower())
        self.assertIn("dashboard", response.lower())
        self.assertIn("proyecto", response.lower())
        self.assertIn("tarea", response.lower())

    def test_generic_open_input_requests_precision(self):
        parsed = parse_user_query("lo del cliente")
        response = build_response_from_query(parsed, user_query="lo del cliente", conversation_context={})
        self.assertIn("mas de precision", response.lower())

    def test_context_can_reduce_ambiguity_for_generic_client_reference(self):
        client = make_client(2, "Cam")
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[],
        ), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[],
        ), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=[],
        ):
            parsed = parse_user_query("lo del cliente")
            response = build_response_from_query(parsed, user_query="lo del cliente", conversation_context=context)

        self.assertIn("resumen del cliente cam", response.lower())
        self.assertTrue(parsed.get("_used_context_to_disambiguate"))


if __name__ == "__main__":
    unittest.main()

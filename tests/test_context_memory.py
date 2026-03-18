import unittest
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_project_summary, make_task, make_task_summary


class ContextMemoryTests(unittest.TestCase):
    def test_task_summary_then_priority_update_uses_current_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Onboarding", client)
        task = make_task(100, "Onboarding", project, priority="media", next_action="Enviar propuesta")
        summary = make_task_summary(task)
        update_result = {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "priority",
            "old_value": "media",
            "new_value": "alta",
            "task": task,
        }

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]), patch(
            "app.services.query_response_service.get_task_operational_summary",
            return_value=summary,
        ), patch(
            "app.services.query_response_service.update_task_priority_conversational",
            return_value=update_result,
        ) as update_mock:
            first = parse_user_query("resumime onboarding")
            first_response = build_response_from_query(first, user_query="resumime onboarding", conversation_context={})
            context = first.get("_conversation_context", {})

            second = parse_user_query("ponelo en alta")
            second_response = build_response_from_query(second, user_query="ponelo en alta", conversation_context=context)

        self.assertIn("resumen de la tarea", first_response.lower())
        self.assertEqual(context.get("task", {}).get("name"), "Onboarding")
        self.assertIn("actualice la tarea", second_response.lower())
        update_mock.assert_called_once()

    def test_client_summary_then_projects_follow_up_uses_isolated_context(self):
        client = make_client(2, "Dallas")
        project = make_project(20, "Implementacion CRM", client)
        task = make_task(200, "Configurar pipeline", project)
        project_summary = make_project_summary(project)

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=[task],
        ), patch(
            "app.services.query_response_service.get_project_operational_summary",
            return_value=project_summary,
        ):
            first = parse_user_query("resumime el cliente Dallas")
            first_response = build_response_from_query(first, user_query="resumime el cliente Dallas", conversation_context={})
            context = first.get("_conversation_context", {})

            second = parse_user_query("y sus proyectos?")
            second_response = build_response_from_query(second, user_query="y sus proyectos?", conversation_context=context)

        self.assertIn("resumen del cliente dallas", first_response.lower())
        self.assertEqual(context.get("client", {}).get("name"), "Dallas")
        self.assertIn("proyectos de dallas", second_response.lower())

    def test_new_conversation_does_not_inherit_previous_context(self):
        client = make_client(2, "Dallas")

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]):
            parsed = parse_user_query("y sus proyectos?")
            response = build_response_from_query(parsed, user_query="y sus proyectos?", conversation_context={})

        self.assertIn("conversacion actual", response.lower())
        self.assertFalse(parsed.get("_context_isolated", False))


if __name__ == "__main__":
    unittest.main()


import unittest
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_task


class UpdateSafetyTests(unittest.TestCase):
    def test_close_without_context_does_not_update(self):
        parsed = parse_user_query("cerrala")

        with patch("app.services.query_response_service.update_task_status_conversational") as update_mock:
            response = build_response_from_query(parsed, user_query="cerrala", conversation_context={})

        self.assertIn("conversacion actual", response.lower())
        update_mock.assert_not_called()
        self.assertFalse(parsed.get("_update_real", True))

    def test_partial_close_does_not_update_when_ambiguous(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Marketing", client)
        first = make_task(101, "Formulario de contacto", project)
        second = make_task(102, "Formulario de leads", project)
        parsed = parse_user_query("cerra la del formulario")
        context = {
            "_isolated": True,
            "scope": "project",
            "project": {"id": project.id, "name": project.name},
        }

        with patch("app.services.reference_resolver.get_tasks_by_project_id", return_value=[first, second]), patch(
            "app.services.query_response_service.update_task_status_conversational"
        ) as update_mock:
            response = build_response_from_query(parsed, user_query="cerra la del formulario", conversation_context=context)

        self.assertIn("varios", response.lower())
        update_mock.assert_not_called()
        self.assertFalse(parsed.get("_update_real", True))

    def test_partial_close_updates_when_match_is_clear(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Marketing", client)
        task = make_task(101, "Formulario de contacto", project)
        parsed = parse_user_query("cerra la del formulario")
        context = {
            "_isolated": True,
            "scope": "project",
            "project": {"id": project.id, "name": project.name},
        }
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
        ) as update_mock:
            response = build_response_from_query(parsed, user_query="cerra la del formulario", conversation_context=context)

        self.assertIn("actualice la tarea", response.lower())
        update_mock.assert_called_once()
        self.assertTrue(parsed.get("_update_real"))


if __name__ == "__main__":
    unittest.main()

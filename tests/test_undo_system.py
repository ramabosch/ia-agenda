import unittest
from unittest.mock import patch

from app.services.conversation_runtime_service import process_conversation_turn
from tests.helpers import make_client, make_project, make_task


class UndoSystemTests(unittest.TestCase):
    def test_undo_recent_task_creation_uses_last_action_trace(self):
        cam = make_client(1, "Cam")
        project = make_project(10, "Dashboard comercial", cam)

        created_result = {
            "created": True,
            "task_id": 501,
            "task_title": "hacer revision anual",
            "project_id": 10,
            "priority": "media",
            "next_action": None,
            "last_note": None,
        }
        deleted_result = {
            "deleted": True,
            "task_id": 501,
            "task_title": "hacer revision anual",
            "project_id": 10,
        }

        with patch("app.services.reference_resolver.get_all_clients", return_value=[cam]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.create_task_conversational",
            return_value=created_result,
        ), patch(
            "app.services.query_response_service.delete_task_conversational",
            return_value=deleted_result,
        ) as delete_mock:
            first = process_conversation_turn("agregame una tarea a Cam: hacer revision anual", conversation_context={})
            second = process_conversation_turn("cancela lo de recien", conversation_context=first["conversation_context"])

        self.assertEqual(first["conversation_context"]["last_action_trace"]["undo_type"], "delete_task")
        delete_mock.assert_called_once_with(501)
        self.assertIn("elimine la tarea", second["response_text"].lower())
        self.assertNotIn("last_action_trace", second["conversation_context"])

    def test_undo_recent_agenda_creation_uses_last_action_trace(self):
        created_result = {
            "created": True,
            "agenda_item_id": 801,
            "title": "reunion con cam",
            "scheduled_date": __import__("datetime").date(2026, 3, 22),
            "scheduled_time": __import__("datetime").time(10, 0),
            "kind": "event",
        }
        deleted_result = {
            "deleted": True,
            "agenda_item_id": 801,
            "title": "reunion con cam",
            "scheduled_date": __import__("datetime").date(2026, 3, 22),
            "scheduled_time": __import__("datetime").time(10, 0),
            "kind": "event",
        }

        with patch(
            "app.services.query_response_service.create_agenda_item_conversational",
            return_value=created_result,
        ), patch(
            "app.services.query_response_service.delete_agenda_item_conversational",
            return_value=deleted_result,
        ) as delete_mock:
            first = process_conversation_turn("agendame manana a las 10 una reunion con Cam", conversation_context={})
            second = process_conversation_turn("cancela lo de recien", conversation_context=first["conversation_context"])

        self.assertEqual(first["conversation_context"]["last_action_trace"]["undo_type"], "delete_agenda_item")
        delete_mock.assert_called_once_with(801)
        self.assertIn("cancele 'reunion con cam'", second["response_text"].lower())
        self.assertNotIn("last_action_trace", second["conversation_context"])

    def test_undo_recent_task_status_update_restores_previous_value(self):
        cam = make_client(1, "Cam")
        project = make_project(10, "Dashboard comercial", cam)
        task = make_task(101, "Definir metricas", project, status="pendiente")

        updated_result = {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "status",
            "old_value": "pendiente",
            "new_value": "hecha",
            "task": task,
        }
        restored_result = {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "status",
            "old_value": "hecha",
            "new_value": "pendiente",
            "task": task,
        }
        context = {
            "_isolated": True,
            "scope": "task",
            "task": {"id": task.id, "name": task.title},
            "project": {"id": project.id, "name": project.name},
        }

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]), patch(
            "app.services.query_response_service.update_task_status_conversational",
            side_effect=[updated_result, restored_result],
        ) as status_mock:
            first = process_conversation_turn("cerrala", conversation_context=context)
            second = process_conversation_turn("cancela lo de recien", conversation_context=first["conversation_context"])

        self.assertEqual(first["conversation_context"]["last_action_trace"]["undo_type"], "restore_task_status")
        self.assertEqual(status_mock.call_count, 2)
        self.assertIn("restaure el estado", second["response_text"].lower())
        self.assertIn("pendiente", second["response_text"].lower())

    def test_undo_recent_task_priority_update_restores_previous_value(self):
        cam = make_client(1, "Cam")
        project = make_project(10, "Dashboard comercial", cam)
        task = make_task(101, "Definir metricas", project, priority="media")

        updated_result = {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "priority",
            "old_value": "media",
            "new_value": "alta",
            "task": task,
        }
        restored_result = {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "priority",
            "old_value": "alta",
            "new_value": "media",
            "task": task,
        }
        context = {
            "_isolated": True,
            "scope": "task",
            "task": {"id": task.id, "name": task.title},
            "project": {"id": project.id, "name": project.name},
        }

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]), patch(
            "app.services.query_response_service.update_task_priority_conversational",
            side_effect=[updated_result, restored_result],
        ) as priority_mock:
            first = process_conversation_turn("ponelo en alta", conversation_context=context)
            second = process_conversation_turn("cancela lo de recien", conversation_context=first["conversation_context"])

        self.assertEqual(first["conversation_context"]["last_action_trace"]["undo_type"], "restore_task_priority")
        self.assertEqual(priority_mock.call_count, 2)
        self.assertIn("restaure la prioridad", second["response_text"].lower())
        self.assertIn("media", second["response_text"].lower())


if __name__ == "__main__":
    unittest.main()

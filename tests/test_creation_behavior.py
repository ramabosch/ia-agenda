import unittest
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_task


class CreationBehaviorTests(unittest.TestCase):
    def test_create_task_with_clear_target(self):
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
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="agrega una tarea a Cam para definir metricas", conversation_context={})

        create_mock.assert_called_once_with(project.id, "definir metricas", priority="media", next_action=None, last_note=None)
        self.assertIn("cree una tarea nueva", response.lower())
        self.assertIn("dashboard", response.lower())
        self.assertTrue(parsed.get("_creation_real"))

    def test_create_task_using_safe_project_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        create_result = {
            "created": True,
            "task_id": 201,
            "task_title": "definir metricas",
            "project_id": project.id,
            "priority": "media",
            "next_action": None,
            "last_note": None,
        }
        parsed = parse_user_query("agrega una tarea en este proyecto: definir metricas")
        context = {
            "_isolated": True,
            "scope": "project",
            "project": {"id": project.id, "name": project.name},
        }

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.query_response_service.create_task_conversational",
            return_value=create_result,
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="agrega una tarea en este proyecto: definir metricas", conversation_context=context)

        create_mock.assert_called_once()
        self.assertIn("dashboard", response.lower())
        self.assertEqual(parsed.get("_creation_target_scope"), "project")

    def test_create_high_priority_task(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        create_result = {
            "created": True,
            "task_id": 202,
            "task_title": "revisar indicadores",
            "project_id": project.id,
            "priority": "alta",
            "next_action": None,
            "last_note": None,
        }
        parsed = parse_user_query("crea una tarea alta prioridad para revisar indicadores")

        with patch("app.services.query_response_service.get_all_projects", return_value=[project]), patch(
            "app.services.query_response_service.create_task_conversational",
            return_value=create_result,
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="crea una tarea alta prioridad para revisar indicadores", conversation_context={})

        create_mock.assert_called_once_with(project.id, "revisar indicadores", priority="alta", next_action=None, last_note=None)
        self.assertIn("prioridad: alta", response.lower())

    def test_add_project_note(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        update_result = {
            "updated": True,
            "project_id": project.id,
            "project_name": project.name,
            "field": "description",
            "old_value": None,
            "new_value": "Nota operativa",
        }
        parsed = parse_user_query("suma una nota al proyecto: falta validacion")
        context = {
            "_isolated": True,
            "scope": "project",
            "project": {"id": project.id, "name": project.name},
        }

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.query_response_service.add_project_note_conversational",
            return_value=update_result,
        ) as note_mock:
            response = build_response_from_query(parsed, user_query="suma una nota al proyecto: falta validacion", conversation_context=context)

        note_mock.assert_called_once_with(project.id, "falta validacion")
        self.assertIn("agregue una nota al proyecto", response.lower())

    def test_project_note_without_content_aborts_clearly(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        parsed = parse_user_query("suma una nota al proyecto")
        context = {
            "_isolated": True,
            "scope": "project",
            "project": {"id": project.id, "name": project.name},
        }

        with patch("app.services.query_response_service.add_project_note_conversational") as note_mock:
            response = build_response_from_query(parsed, user_query="suma una nota al proyecto", conversation_context=context)

        note_mock.assert_not_called()
        self.assertIn("contenido de la nota", response.lower())
        self.assertTrue(parsed.get("_creation_aborted"))

    def test_add_task_note_and_set_next_action_reuse_existing_update_flow(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(101, "Definir metricas", project)
        context = {
            "_isolated": True,
            "scope": "task",
            "task": {"id": task.id, "name": task.title},
            "project": {"id": project.id, "name": project.name},
        }

        note_result = {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "last_note",
            "old_value": None,
            "new_value": "falta validacion del cliente",
            "task": task,
        }
        next_result = {
            "updated": True,
            "task_id": task.id,
            "task_title": task.title,
            "field": "next_action",
            "old_value": None,
            "new_value": "manana",
            "task": task,
        }

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]), patch(
            "app.services.query_response_service.add_task_note_conversational",
            return_value=note_result,
        ) as note_mock, patch(
            "app.services.query_response_service.update_task_next_action_conversational",
            return_value=next_result,
        ) as next_mock:
            note_parsed = parse_user_query("deja nota: falta validacion del cliente")
            note_response = build_response_from_query(note_parsed, user_query="deja nota: falta validacion del cliente", conversation_context=context)

            next_parsed = parse_user_query("dejame una proxima accion para manana")
            next_response = build_response_from_query(next_parsed, user_query="dejame una proxima accion para manana", conversation_context=context)

        note_mock.assert_called_once_with(task.id, note_content="falta validacion del cliente")
        next_mock.assert_called_once_with(task.id, next_action="manana")
        self.assertIn("actualice la tarea", note_response.lower())
        self.assertIn("proxima accion", next_response.lower())

    def test_ambiguous_create_does_not_create(self):
        client = make_client(1, "CAM")
        project_a = make_project(10, "Dashboard", client)
        project_b = make_project(11, "Analytics", client)
        parsed = parse_user_query("agrega una tarea a Cam para definir metricas")

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project_a, project_b],
        ), patch(
            "app.services.query_response_service.create_task_conversational",
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="agrega una tarea a Cam para definir metricas", conversation_context={})

        create_mock.assert_not_called()
        self.assertIn("varios proyectos", response.lower())
        self.assertFalse(parsed.get("_creation_real", True))

    def test_without_context_does_not_invent_creation_target(self):
        project_a = make_project(10, "Dashboard", make_client(1, "CAM"))
        project_b = make_project(11, "Analytics", make_client(2, "Dallas"))
        parsed = parse_user_query("crea una tarea para revisar indicadores")

        with patch("app.services.query_response_service.get_all_projects", return_value=[project_a, project_b]), patch(
            "app.services.query_response_service.create_task_conversational",
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="crea una tarea para revisar indicadores", conversation_context={})

        create_mock.assert_not_called()
        self.assertIn("no tengo un proyecto claro", response.lower())

    def test_converti_esto_en_tarea_uses_safe_snapshot(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        create_result = {
            "created": True,
            "task_id": 203,
            "task_title": "Resolver bloqueo API",
            "project_id": project.id,
            "priority": "media",
            "next_action": None,
            "last_note": None,
        }
        context = {
            "_isolated": True,
            "scope": "project",
            "project": {"id": project.id, "name": project.name},
            "response_snapshot": {
                "response_kind": "summary",
                "scope": "project",
                "entity_name": project.name,
                "highlights": [{"title": "Resolver bloqueo API", "status": "bloqueada", "priority": "alta"}],
            },
        }
        parsed = parse_user_query("converti esto en tarea")

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.query_response_service.create_task_conversational",
            return_value=create_result,
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="converti esto en tarea", conversation_context=context)

        create_mock.assert_called_once_with(project.id, "Resolver bloqueo API", priority="media", next_action=None, last_note=None)
        self.assertIn("resolver bloqueo api", response.lower())


if __name__ == "__main__":
    unittest.main()

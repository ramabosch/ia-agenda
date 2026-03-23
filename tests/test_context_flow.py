import unittest
from unittest.mock import patch

from app.services.conversation_runtime_service import process_conversation_turn
from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_task


class ContextFlowTests(unittest.TestCase):
    def test_three_turn_dialog_keeps_rosario_capilar_without_renaming_it(self):
        rosario = make_client(1, "Rosario Capilar")
        project = make_project(10, "Campana invierno", rosario)
        task = make_task(
            100,
            "Definir promo estacional",
            project,
            status="en_progreso",
            priority="alta",
            next_action="Confirmar piezas",
        )

        with patch("app.services.reference_resolver.get_all_clients", return_value=[rosario]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=[task],
        ):
            first = process_conversation_turn("comentame en que andamos con Rosario Capilar", conversation_context={})
            second = process_conversation_turn(
                "que me preocuparia",
                conversation_context=first["conversation_context"],
            )
            third = process_conversation_turn(
                "y de eso que hay?",
                conversation_context=second["conversation_context"],
            )

        self.assertEqual(first["conversation_context"].get("client", {}).get("name"), "Rosario Capilar")
        self.assertEqual(second["conversation_context"].get("client", {}).get("name"), "Rosario Capilar")
        self.assertEqual(third["conversation_context"].get("client", {}).get("name"), "Rosario Capilar")
        self.assertIn("rosario", third["response_text"].lower())
        self.assertTrue(third["conversation_context"].get("recent_entities"))

    def test_vague_followup_without_context_asks_for_clarification(self):
        result = process_conversation_turn("y de eso que hay?", conversation_context={})

        self.assertIn("contexto aislado actual", result["response_text"].lower())
        self.assertEqual(result["conversation_context"].get("scope"), "none")

    def test_other_action_proposes_probable_repeated_action(self):
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": 1, "name": "Cam"},
            "clarification_candidates": [
                {"id": 1, "name": "Cam", "scope": "client", "confidence": 0.95},
                {"id": 2, "name": "Instituto CAM", "scope": "client", "confidence": 0.94},
            ],
            "last_action_trace": {
                "undo_type": "delete_task",
                "action_type": "create_task",
                "entity_id": 501,
                "entity_name": "hacer revision anual",
                "proposal_text": "hacer revision anual",
            },
        }

        result = process_conversation_turn("hacelo para el otro tambien", conversation_context=context)

        self.assertIn("instituto cam", result["response_text"].lower())
        self.assertIn("cree 'hacer revision anual'", result["response_text"].lower())

    def test_other_summary_uses_alternative_recent_candidate(self):
        cam = make_client(1, "Cam")
        ventas = make_project(10, "Dashboard ventas", cam)
        comercial = make_project(11, "Dashboard comercial", cam)

        with patch("app.services.reference_resolver.get_all_clients", return_value=[cam]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[ventas, comercial],
        ), patch("app.services.reference_resolver.get_all_tasks", return_value=[]), patch(
            "app.services.query_response_service.get_project_operational_summary",
            side_effect=[
                {
                    "project_id": 10,
                    "project_name": "Dashboard ventas",
                    "client_id": 1,
                    "client_name": "Cam",
                    "status": "activo",
                    "description": "Ventas",
                    "total_tasks": 2,
                    "open_tasks": 2,
                    "done_tasks": 0,
                    "blocked_tasks": 0,
                    "in_progress_tasks": 1,
                },
                {
                    "project_id": 11,
                    "project_name": "Dashboard comercial",
                    "client_id": 1,
                    "client_name": "Cam",
                    "status": "activo",
                    "description": "Comercial",
                    "total_tasks": 3,
                    "open_tasks": 3,
                    "done_tasks": 0,
                    "blocked_tasks": 1,
                    "in_progress_tasks": 1,
                },
            ],
        ):
            first = process_conversation_turn("dashboard", conversation_context={})
            second = process_conversation_turn(
                "el de ventas",
                conversation_context=first["conversation_context"],
            )
            third = process_conversation_turn(
                "y de lo otro?",
                conversation_context=second["conversation_context"],
            )

        self.assertIn("dashboard comercial", third["response_text"].lower())
        self.assertEqual(third["conversation_context"].get("project", {}).get("name"), "Dashboard comercial")

    def test_vague_literal_is_intercepted_before_literal_update(self):
        task = make_task(10, "Definir metricas", make_project(50, "Dashboard", make_client(1, "Cam")))
        context = {
            "_isolated": True,
            "scope": "task",
            "task": {"id": 10, "name": "Definir metricas"},
            "recent_entities": [
                {"scope": "task", "id": 10, "name": "Definir metricas"},
                {"scope": "task", "id": 11, "name": "Revisar backlog"},
            ],
        }
        parsed = parse_user_query("bajale la prioridad a la otra")
        parsed["_parser_source"] = "llm"

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]):
            result = build_response_from_query(
                parsed,
                user_query="bajale la prioridad a la otra",
                conversation_context=context,
            )

        self.assertEqual(parsed["intent"], "expand_context")
        self.assertEqual(parsed["expand_mode"], "other_entity_summary")
        self.assertIn("precision", result.lower())

    def test_ordinal_followup_executes_pending_close_action(self):
        client = make_client(1, "Cam")
        project = make_project(10, "Inbox", client)
        first_task = make_task(101, "Comprar cafe", project)
        second_task = make_task(102, "Revisar cables", project)
        context = {
            "_isolated": True,
            "scope": "none",
            "clarification_candidates": [
                {"id": first_task.id, "name": first_task.title, "scope": "task", "confidence": 0.95},
                {"id": second_task.id, "name": second_task.title, "scope": "task", "confidence": 0.94},
            ],
            "pending_action": {
                "intent": "update_task_status",
                "new_status": "hecha",
            },
        }

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[first_task, second_task]), patch(
            "app.services.query_response_service.update_task_status_conversational",
            return_value={
                "updated": True,
                "task_id": first_task.id,
                "task_title": first_task.title,
                "field": "status",
                "old_value": "pendiente",
                "new_value": "hecha",
                "task": first_task,
            },
        ):
            result = process_conversation_turn("la primera", conversation_context=context)

        self.assertIn("comprar cafe", result["response_text"].lower())
        self.assertIn("actualice la tarea", result["response_text"].lower())


if __name__ == "__main__":
    unittest.main()

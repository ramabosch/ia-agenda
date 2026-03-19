import unittest
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_conversation_log, make_project, make_task


class AuditBehaviorTests(unittest.TestCase):
    def test_informational_turn_leaves_trace(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        tasks = [make_task(100, "Definir indicadores", project, priority="alta")]

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch("app.services.query_response_service.get_tasks_by_client_id", return_value=tasks):
            parsed = parse_user_query("comentame en que andamos con Cam")
            build_response_from_query(parsed, user_query="comentame en que andamos con Cam", conversation_context={})

        trace = parsed.get("_audit_trace", {})
        self.assertEqual(trace.get("action_status"), "informational")
        self.assertEqual(trace.get("intent"), "get_operational_summary")
        self.assertIn("client", trace.get("resolved_entities", {}))

    def test_update_turn_leaves_executed_trace(self):
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
            build_response_from_query(parsed, user_query="cerra la del formulario", conversation_context=context)

        trace = parsed.get("_audit_trace", {})
        self.assertEqual(trace.get("action_status"), "executed")
        self.assertEqual(trace.get("action_type"), "status")
        self.assertEqual(trace.get("affected_entity", {}).get("name"), "Formulario de contacto")

    def test_create_turn_leaves_affected_entity_trace(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        parsed = parse_user_query("agrega una tarea a Cam para definir metricas")
        create_result = {
            "created": True,
            "task_id": 200,
            "task_title": "definir metricas",
            "project_id": project.id,
            "priority": "media",
            "next_action": None,
            "last_note": None,
        }

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.create_task_conversational",
            return_value=create_result,
        ):
            build_response_from_query(parsed, user_query="agrega una tarea a Cam para definir metricas", conversation_context={})

        trace = parsed.get("_audit_trace", {})
        self.assertEqual(trace.get("action_status"), "executed")
        self.assertEqual(trace.get("affected_entity", {}).get("name"), "definir metricas")

    def test_clarification_turn_leaves_candidates_trace(self):
        client = make_client(1, "CAM")
        sales = make_project(10, "Dashboard ventas", client)
        commercial = make_project(11, "Dashboard comercial", client)
        parsed = {"intent": "clarify_entity_reference", "entity_hint": "dashboard", "expected_scope": "project"}

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[sales, commercial],
        ), patch("app.services.reference_resolver.get_all_tasks", return_value=[]):
            build_response_from_query(parsed, user_query="dashboard", conversation_context={})

        trace = parsed.get("_audit_trace", {})
        self.assertEqual(trace.get("action_status"), "blocked")
        self.assertTrue(trace.get("clarification_needed"))
        self.assertGreaterEqual(len(trace.get("candidates", [])), 2)

    def test_degraded_turn_leaves_reason(self):
        parsed = parse_user_query("por que esa")
        response = build_response_from_query(parsed, user_query="por que esa", conversation_context={})

        trace = parsed.get("_audit_trace", {})
        self.assertIn("no tengo contexto", response.lower())
        self.assertEqual(trace.get("action_status"), "degraded")

    def test_audit_followup_que_hiciste_recien_works(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        tasks = [make_task(100, "Definir indicadores", project, priority="alta")]

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch("app.services.query_response_service.get_tasks_by_client_id", return_value=tasks):
            first = parse_user_query("comentame en que andamos con Cam")
            build_response_from_query(first, user_query="comentame en que andamos con Cam", conversation_context={})
            context = first.get("_conversation_context", {})

            second = parse_user_query("que hiciste recien")
            response = build_response_from_query(second, user_query="que hiciste recien", conversation_context=context)

        self.assertIn("recien respondi", response.lower())

    def test_audit_followup_por_que_elegiste_esa_uses_recent_trace(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver bloqueo API", project, status="bloqueada", priority="alta")
        context = {"_isolated": True, "scope": "client", "client": {"id": client.id, "name": client.name}}

        with patch("app.services.query_response_service.get_projects_by_client_id", return_value=[project]), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=[blocked],
        ):
            first = parse_user_query("que haria ahora con este cliente")
            build_response_from_query(first, user_query="que haria ahora con este cliente", conversation_context=context)
            second = parse_user_query("por que elegiste esa")
            response = build_response_from_query(second, user_query="por que elegiste esa", conversation_context=first.get("_conversation_context", {}))

        self.assertIn("razon", response.lower())
        self.assertIn("resolver bloqueo api", response.lower())

    def test_without_recent_trace_does_not_invent_audit(self):
        parsed = parse_user_query("que resolviste")
        response = build_response_from_query(parsed, user_query="que resolviste", conversation_context={})
        self.assertIn("no tengo una traza reciente", response.lower())

    def test_compound_query_leaves_reasonable_trace(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        tasks = [make_task(100, "Resolver bloqueo API", project, status="bloqueada", priority="alta")]

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch("app.services.query_response_service.get_tasks_by_client_id", return_value=tasks):
            parsed = parse_user_query("resumime Cam y decime que haria primero")
            build_response_from_query(parsed, user_query="resumime Cam y decime que haria primero", conversation_context={})

        trace = parsed.get("_audit_trace", {})
        self.assertEqual(trace.get("action_type"), "compound_query")
        self.assertEqual(len([item for item in trace.get("sub_intents", []) if item]), 2)

    def test_audit_followup_does_not_reuse_last_saved_log(self):
        trace = {
            "user_query": "comentame en que andamos con Cam",
            "intent": "get_operational_summary",
            "action_status": "informational",
            "summary": "Resumen del cliente CAM",
        }
        log = make_conversation_log({"_audit_trace": trace})
        parsed = parse_user_query("que hiciste recien")

        with patch("app.services.query_response_service.get_last_conversation", return_value=log):
            response = build_response_from_query(parsed, user_query="que hiciste recien", conversation_context={})

        self.assertIn("no tengo una traza reciente", response.lower())


if __name__ == "__main__":
    unittest.main()

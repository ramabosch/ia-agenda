import unittest
from unittest.mock import patch

from app.services.reference_resolver import resolve_references
from tests.helpers import make_client, make_conversation_log, make_project, make_task


class ResolverBehaviorTests(unittest.TestCase):
    def test_resolves_explicit_task_reference(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Onboarding", client)
        task = make_task(100, "Onboarding clientes", project)

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]):
            resolved = resolve_references(
                {"intent": "get_task_summary", "task_name": "onboarding clientes"},
                user_query="resumime onboarding clientes",
                conversation_context={},
            )

        self.assertEqual(resolved["scope"], "task")
        self.assertEqual(resolved["task"]["resolved"]["id"], 100)
        self.assertEqual(resolved["task"]["source"], "explicit")

    def test_resolves_partial_reference_when_clear(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Marketing", client)
        task = make_task(101, "Formulario de contacto", project)

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]):
            resolved = resolve_references(
                {"intent": "get_task_summary", "task_name": "formulario"},
                user_query="resumime formulario",
                conversation_context={},
            )

        self.assertEqual(resolved["task"]["resolved"]["id"], 101)
        self.assertFalse(resolved["task"]["ambiguous"])

    def test_marks_ambiguous_partial_reference(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Marketing", client)
        first = make_task(101, "Formulario de contacto", project)
        second = make_task(102, "Formulario de leads", project)

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[first, second]):
            resolved = resolve_references(
                {"intent": "get_task_summary", "task_name": "formulario"},
                user_query="resumime formulario",
                conversation_context={},
            )

        self.assertTrue(resolved["task"]["ambiguous"])
        self.assertIsNone(resolved["task"]["resolved"])
        self.assertTrue(resolved["clarification_needed"])

    def test_cross_scope_matches_trigger_clarification(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(101, "Dashboard KPIs", project)

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[task],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[client],
        ):
            resolved = resolve_references(
                {"intent": "clarify_entity_reference", "entity_hint": "dashboard"},
                user_query="dashboard",
                conversation_context={},
            )

        self.assertTrue(resolved["clarification_needed"])
        self.assertEqual(resolved["clarification_reason"], "cross_scope_ambiguity")
        self.assertIn("project", resolved["candidate_types"])
        self.assertIn("task", resolved["candidate_types"])

    def test_uses_isolated_recent_context(self):
        client = make_client(2, "Dallas")
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]):
            resolved = resolve_references(
                {"intent": "get_projects_by_client_name", "client_name": "este cliente"},
                user_query="y sus proyectos?",
                conversation_context=context,
            )

        self.assertEqual(resolved["client"]["resolved"]["name"], "Dallas")
        self.assertTrue(resolved["context_isolated"])
        self.assertEqual(resolved["context_source"], "current")

    def test_does_not_inherit_old_global_context_by_default(self):
        old_context = {
            "intent": "get_client_summary",
            "_conversation_context": {
                "_isolated": True,
                "scope": "client",
                "client": {"id": 2, "name": "Dallas"},
            },
        }
        log = make_conversation_log(old_context)

        with patch("app.services.reference_resolver.get_last_conversation", return_value=log):
            resolved = resolve_references(
                {"intent": "get_projects_by_client_name", "client_name": "este cliente"},
                user_query="y sus proyectos?",
                conversation_context={},
                allow_global_context=False,
            )

        self.assertTrue(resolved["security_blocked"])
        self.assertIsNone(resolved["client"]["resolved"])
        self.assertEqual(resolved["context_source"], "none")

    def test_updates_are_more_conservative_than_queries(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Onboarding", client)
        task = make_task(100, "Onboarding clientes", project)

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]):
            read_resolved = resolve_references(
                {"intent": "get_task_summary", "task_name": "boarding"},
                user_query="resumime boarding",
                conversation_context={},
            )
            update_resolved = resolve_references(
                {"intent": "update_task_status", "task_name": "boarding"},
                user_query="cerra boarding",
                conversation_context={},
            )

        self.assertEqual(read_resolved["task"]["resolved"]["id"], 100)
        self.assertIsNone(update_resolved["task"]["resolved"])

    def test_generic_open_reference_requests_precision(self):
        resolved = resolve_references(
            {"intent": "clarify_entity_reference", "entity_hint": "cliente"},
            user_query="lo del cliente",
            conversation_context={},
        )
        self.assertTrue(resolved["clarification_needed"])
        self.assertEqual(resolved["clarification_reason"], "generic_request")


if __name__ == "__main__":
    unittest.main()

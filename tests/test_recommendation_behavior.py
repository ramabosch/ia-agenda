import unittest
from datetime import date, datetime
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from app.services.task_service import build_recommendation_focus_from_tasks
from tests.helpers import make_client, make_project, make_task, make_task_summary


class RecommendationBehaviorTests(unittest.TestCase):
    def test_recommendation_prioritizes_blocked_high_priority_without_next_action(self):
        today = date(2026, 3, 18)
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(
            100,
            "Resolver bloqueo API",
            project,
            status="bloqueada",
            priority="alta",
            created_at=datetime(2026, 3, 1, 10, 0, 0),
            last_updated_at=datetime(2026, 3, 2, 10, 0, 0),
        )
        secondary = make_task(101, "Cerrar copy", project, status="pendiente", next_action="Validar copy final")

        snapshot = build_recommendation_focus_from_tasks([blocked, secondary], today=today)

        self.assertEqual(snapshot["recommendations"][0]["title"], "Resolver bloqueo API")
        self.assertIn("bloqueada", " ".join(snapshot["recommendations"][0]["recommendation_reasons"]))

    def test_recommendation_mentions_old_open_attention(self):
        today = date(2026, 3, 18)
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        old_open = make_task(
            100,
            "Definir indicadores",
            project,
            status="pendiente",
            priority="media",
            created_at=datetime(2026, 2, 20, 10, 0, 0),
            last_updated_at=datetime(2026, 2, 21, 10, 0, 0),
        )

        snapshot = build_recommendation_focus_from_tasks([old_open], today=today)

        joined_reasons = " ".join(snapshot["recommendations"][0]["recommendation_reasons"])
        self.assertTrue(
            "lleva bastante abierta" in joined_reasons or "le falta seguimiento concreto" in joined_reasons
        )

    def test_project_recommendation_uses_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver API", project, status="bloqueada", priority="alta")
        follow = make_task(101, "Definir copy", project, priority="alta")
        context = {
            "_isolated": True,
            "scope": "project",
            "project": {"id": project.id, "name": project.name},
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.query_response_service.get_tasks_by_project_id", return_value=[blocked, follow]):
            parsed = parse_user_query("que priorizarias en este proyecto")
            response = build_response_from_query(parsed, user_query="que priorizarias en este proyecto", conversation_context=context)

        self.assertIn("lo que priorizaria en el proyecto dashboard", response.lower())
        self.assertEqual(parsed.get("_recommendation_scope"), "contextual_project")

    def test_client_recommendation_with_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver API", project, status="bloqueada", priority="alta")
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.query_response_service.get_tasks_by_client_id", return_value=[blocked]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ):
            parsed = parse_user_query("que haria ahora con este cliente")
            response = build_response_from_query(parsed, user_query="que haria ahora con este cliente", conversation_context=context)

        self.assertIn("lo que yo haria con cam", response.lower())
        self.assertIn("porque", response.lower())
        self.assertEqual(parsed.get("_recommendation_scope"), "contextual_client")

    def test_natural_recommendation_followup_uses_safe_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver API", project, status="bloqueada", priority="alta")
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.query_response_service.get_tasks_by_client_id", return_value=[blocked]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ):
            parsed = parse_user_query("que me recomendarias hacer ahora")
            response = build_response_from_query(parsed, user_query="que me recomendarias hacer ahora", conversation_context=context)

        self.assertIn("lo que yo haria con cam", response.lower())
        self.assertEqual(parsed.get("_recommendation_scope"), "contextual_client")

    def test_loose_recommendation_followup_uses_safe_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver API", project, status="bloqueada", priority="alta")
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.query_response_service.get_tasks_by_client_id", return_value=[blocked]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ):
            parsed = parse_user_query("y ahora que")
            response = build_response_from_query(parsed, user_query="y ahora que", conversation_context=context)

        self.assertIn("lo que yo haria con cam", response.lower())
        self.assertEqual(parsed.get("_recommendation_scope"), "contextual_client")

    def test_if_i_were_you_phrase_uses_safe_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver API", project, status="bloqueada", priority="alta")
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.query_response_service.get_tasks_by_client_id", return_value=[blocked]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ):
            parsed = parse_user_query("si fueras yo, que harias")
            response = build_response_from_query(parsed, user_query="si fueras yo, que harias", conversation_context=context)

        self.assertIn("lo que yo haria con cam", response.lower())
        self.assertEqual(parsed.get("_recommendation_scope"), "contextual_client")

    def test_natural_recommendation_followup_without_context_does_not_invent(self):
        parsed = parse_user_query("que harias ahora")
        response = build_response_from_query(parsed, user_query="que harias ahora", conversation_context={})
        self.assertIn("no tengo contexto aislado actual", response.lower())
        self.assertIn("cliente, proyecto o tarea exacta", response.lower())

    def test_loose_recommendation_without_context_does_not_invent(self):
        parsed = parse_user_query("que conviene")
        response = build_response_from_query(parsed, user_query="que conviene", conversation_context={})
        self.assertIn("no tengo contexto aislado actual", response.lower())
        self.assertIn("cliente, proyecto o tarea exacta", response.lower())

    def test_ambiguous_recommendation_keeps_clarification(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(100, "Dashboard indicadores", project)

        with patch("app.services.reference_resolver.get_all_projects", return_value=[project]), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[task],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[],
        ):
            parsed = parse_user_query("que me recomendas hacer con dashboard")
            response = build_response_from_query(parsed, user_query="que me recomendas hacer con dashboard", conversation_context={})

        self.assertIn("aclares", response.lower())

    def test_conservative_recommendation_when_data_is_sparse(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(100, "Revisar formulario", project, priority="media", next_action=None)
        task.created_at = None
        task.last_updated_at = None
        summary = make_task_summary(task)

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[],
        ), patch(
            "app.services.query_response_service.get_task_operational_summary",
            return_value=summary,
        ):
            parsed = parse_user_query("que me recomendas hacer con revisar formulario")
            response = build_response_from_query(parsed, user_query="que me recomendas hacer con revisar formulario", conversation_context={})

        self.assertIn("recomendacion conservadora", response.lower())

    def test_recommendation_never_updates(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        task = make_task(100, "Resolver API", project, status="bloqueada", priority="alta")

        with patch("app.services.reference_resolver.get_all_tasks", return_value=[task]), patch(
            "app.services.reference_resolver.get_all_projects",
            return_value=[],
        ), patch(
            "app.services.reference_resolver.get_all_clients",
            return_value=[],
        ), patch(
            "app.services.query_response_service.update_task_status_conversational",
        ) as update_mock, patch(
            "app.services.query_response_service.get_task_operational_summary",
            return_value=make_task_summary(task),
        ):
            parsed = parse_user_query("que me recomendas hacer con resolver api")
            build_response_from_query(parsed, user_query="que me recomendas hacer con resolver api", conversation_context={})

        update_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_task


class DrilldownBehaviorTests(unittest.TestCase):
    def _build_client_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver bloqueo API", project, status="bloqueada", priority="alta")
        urgent = make_task(101, "Definir indicadores", project, status="pendiente", priority="alta")
        regular = make_task(102, "Ajustar copy", project, status="pendiente", priority="media", next_action="Revisar copy final")
        return client, project, [blocked, urgent, regular]

    def test_summary_then_que_me_preocuparia_uses_same_context(self):
        client, project, tasks = self._build_client_context()

        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=tasks,
        ):
            first = parse_user_query("comentame en que andamos con Cam")
            first_response = build_response_from_query(first, user_query="comentame en que andamos con Cam", conversation_context={})
            context = first.get("_conversation_context", {})

            second = parse_user_query("que me preocuparia")
            second_response = build_response_from_query(second, user_query="que me preocuparia", conversation_context=context)

        self.assertIn("resumen del cliente cam", first_response.lower())
        self.assertIn("lo que me preocuparia de cam", second_response.lower())
        self.assertEqual(second.get("_friction_scope"), "contextual_client")

    def test_recommendation_then_por_que_esa_explains_choice(self):
        client, project, tasks = self._build_client_context()
        seed_context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.query_response_service.get_projects_by_client_id", return_value=[project]), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=tasks,
        ):
            first = parse_user_query("que haria ahora con este cliente")
            build_response_from_query(first, user_query="que haria ahora con este cliente", conversation_context=seed_context)
            context = first.get("_conversation_context", {})

            second = parse_user_query("por que esa")
            response = build_response_from_query(second, user_query="por que esa", conversation_context=context)

        self.assertIn("te dije primero", response.lower())
        self.assertIn("resolver bloqueo api", response.lower())
        self.assertTrue(second.get("_continuity_used_recommendation"))

    def test_recommendation_then_y_despues_de_eso_returns_second_option(self):
        client, project, tasks = self._build_client_context()
        seed_context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": client.id, "name": client.name},
        }

        with patch("app.services.query_response_service.get_projects_by_client_id", return_value=[project]), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=tasks,
        ):
            first = parse_user_query("que haria ahora con este cliente")
            build_response_from_query(first, user_query="que haria ahora con este cliente", conversation_context=seed_context)
            context = first.get("_conversation_context", {})

            second = parse_user_query("y despues de eso?")
            response = build_response_from_query(second, user_query="y despues de eso?", conversation_context=context)

        self.assertIn("despues de eso", response.lower())
        self.assertIn("definir indicadores", response.lower())

    def test_filter_only_critical(self):
        client, project, tasks = self._build_client_context()
        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=tasks,
        ):
            first = parse_user_query("comentame en que andamos con Cam")
            build_response_from_query(first, user_query="comentame en que andamos con Cam", conversation_context={})
            context = first.get("_conversation_context", {})

            second = parse_user_query("mostrame solo lo critico")
            response = build_response_from_query(second, user_query="mostrame solo lo critico", conversation_context=context)

        self.assertIn("solo lo critico", response.lower())
        self.assertIn("resolver bloqueo api", response.lower())

    def test_filter_only_urgent(self):
        client, project, tasks = self._build_client_context()
        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=tasks,
        ):
            first = parse_user_query("comentame en que andamos con Cam")
            build_response_from_query(first, user_query="comentame en que andamos con Cam", conversation_context={})
            context = first.get("_conversation_context", {})

            second = parse_user_query("y solo lo urgente")
            response = build_response_from_query(second, user_query="y solo lo urgente", conversation_context=context)

        self.assertIn("solo lo urgente", response.lower())
        self.assertIn("resolver bloqueo api", response.lower())

    def test_filter_only_blocked(self):
        client, project, tasks = self._build_client_context()
        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=tasks,
        ):
            first = parse_user_query("comentame en que andamos con Cam")
            build_response_from_query(first, user_query="comentame en que andamos con Cam", conversation_context={})
            context = first.get("_conversation_context", {})

            second = parse_user_query("quiero ver solo tareas bloqueadas")
            response = build_response_from_query(second, user_query="quiero ver solo tareas bloqueadas", conversation_context=context)

        self.assertIn("solo las bloqueadas", response.lower())
        self.assertIn("resolver bloqueo api", response.lower())
        self.assertNotIn("ajustar copy", response.lower())

    def test_rephrase_three_lines(self):
        client, project, tasks = self._build_client_context()
        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=tasks,
        ):
            first = parse_user_query("comentame en que andamos con Cam")
            build_response_from_query(first, user_query="comentame en que andamos con Cam", conversation_context={})
            context = first.get("_conversation_context", {})

            second = parse_user_query("resumimelo en 3 lineas")
            response = build_response_from_query(second, user_query="resumimelo en 3 lineas", conversation_context=context)

        self.assertLessEqual(len([line for line in response.splitlines() if line.strip()]), 3)

    def test_rephrase_executive_and_simple(self):
        client, project, tasks = self._build_client_context()
        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=tasks,
        ):
            first = parse_user_query("comentame en que andamos con Cam")
            build_response_from_query(first, user_query="comentame en que andamos con Cam", conversation_context={})
            context = first.get("_conversation_context", {})

            executive = parse_user_query("damelo mas ejecutivo")
            executive_response = build_response_from_query(executive, user_query="damelo mas ejecutivo", conversation_context=context)

            simple = parse_user_query("explicamelo simple")
            simple_response = build_response_from_query(simple, user_query="explicamelo simple", conversation_context=context)

        self.assertIn("version ejecutiva", executive_response.lower())
        self.assertIn("en simple", simple_response.lower())

    def test_client_facing_summary(self):
        client, project, tasks = self._build_client_context()
        with patch("app.services.reference_resolver.get_all_clients", return_value=[client]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=tasks,
        ):
            first = parse_user_query("comentame en que andamos con Cam")
            build_response_from_query(first, user_query="comentame en que andamos con Cam", conversation_context={})
            context = first.get("_conversation_context", {})

            second = parse_user_query("que le diria al cliente hoy")
            response = build_response_from_query(second, user_query="que le diria al cliente hoy", conversation_context=context)

        self.assertIn("si hoy se lo dijera al cliente", response.lower())

    def test_without_context_does_not_invent_recommendation_explanation(self):
        parsed = parse_user_query("por que esa")
        response = build_response_from_query(parsed, user_query="por que esa", conversation_context={})
        self.assertIn("no tengo contexto aislado actual", response.lower())

    def test_ambiguous_input_still_clarifies(self):
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


if __name__ == "__main__":
    unittest.main()

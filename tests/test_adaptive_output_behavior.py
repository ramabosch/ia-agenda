import unittest
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_client, make_project, make_task


class AdaptiveOutputBehaviorTests(unittest.TestCase):
    def _build_client_context(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        blocked = make_task(100, "Resolver bloqueo API", project, status="bloqueada", priority="alta")
        urgent = make_task(
            101,
            "Definir indicadores",
            project,
            status="pendiente",
            priority="alta",
            next_action="Confirmar definiciones con producto",
        )
        regular = make_task(
            102,
            "Ajustar copy",
            project,
            status="pendiente",
            priority="media",
            next_action="Revisar copy final",
        )
        return client, project, [blocked, urgent, regular]

    def _build_summary_context(self):
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
        return first.get("_conversation_context", {})

    def test_previous_response_then_damelo_corto(self):
        context = self._build_summary_context()
        parsed = parse_user_query("damelo corto")
        response = build_response_from_query(parsed, user_query="damelo corto", conversation_context=context)
        self.assertIn("en corto", response.lower())
        self.assertTrue(parsed.get("_adaptive_snapshot_reused"))

    def test_previous_response_then_damelo_ejecutivo(self):
        context = self._build_summary_context()
        parsed = parse_user_query("damelo ejecutivo")
        response = build_response_from_query(parsed, user_query="damelo ejecutivo", conversation_context=context)
        self.assertIn("version ejecutiva", response.lower())

    def test_previous_response_then_damelo_tactico(self):
        context = self._build_summary_context()
        parsed = parse_user_query("damelo tactico")
        response = build_response_from_query(parsed, user_query="damelo tactico", conversation_context=context)
        self.assertIn("version tactica", response.lower())
        self.assertIn("prioridad operativa", response.lower())

    def test_previous_response_then_quiero_mas_detalle(self):
        context = self._build_summary_context()
        parsed = parse_user_query("quiero mas detalle")
        response = build_response_from_query(parsed, user_query="quiero mas detalle", conversation_context=context)
        self.assertIn("version con mas detalle", response.lower())
        self.assertIn("lo mas importante", response.lower())

    def test_previous_response_then_only_risks(self):
        context = self._build_summary_context()
        parsed = parse_user_query("quiero solo riesgos")
        response = build_response_from_query(parsed, user_query="quiero solo riesgos", conversation_context=context)
        self.assertIn("solo los riesgos", response.lower())
        self.assertIn("resolver bloqueo api", response.lower())

    def test_previous_response_then_only_next_steps(self):
        context = self._build_summary_context()
        parsed = parse_user_query("quiero solo proximos pasos")
        response = build_response_from_query(parsed, user_query="quiero solo proximos pasos", conversation_context=context)
        self.assertIn("solo los proximos pasos", response.lower())
        self.assertIn("definir indicadores", response.lower())

    def test_previous_response_then_only_bullets(self):
        context = self._build_summary_context()
        parsed = parse_user_query("dame solo bullets")
        response = build_response_from_query(parsed, user_query="dame solo bullets", conversation_context=context)
        lines = [line for line in response.splitlines() if line.strip()]
        self.assertTrue(lines)
        self.assertTrue(all(line.startswith("-") for line in lines))

    def test_previous_response_then_client_and_meeting_versions(self):
        context = self._build_summary_context()

        client_parsed = parse_user_query("decimelo como para mandarselo al cliente")
        client_response = build_response_from_query(
            client_parsed,
            user_query="decimelo como para mandarselo al cliente",
            conversation_context=context,
        )

        meeting_parsed = parse_user_query("decimelo como para reunion")
        meeting_response = build_response_from_query(
            meeting_parsed,
            user_query="decimelo como para reunion",
            conversation_context=context,
        )

        self.assertIn("si hoy se lo dijera al cliente", client_response.lower())
        self.assertIn("version para reunion", meeting_response.lower())

    def test_without_context_does_not_invent_adaptive_output(self):
        parsed = parse_user_query("damelo ejecutivo")
        response = build_response_from_query(parsed, user_query="damelo ejecutivo", conversation_context={})
        self.assertIn("no tengo contexto aislado actual", response.lower())

    def test_insufficient_snapshot_degrades_safely(self):
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": 1, "name": "CAM"},
            "response_snapshot": {
                "response_kind": "operational_summary",
                "scope": "client",
                "entity_name": "CAM",
                "status_overview": "Seguimiento abierto",
                "highlights": [{"title": "Definir indicadores", "status": "pendiente", "priority": "alta"}],
                "blockers": [],
                "next_steps": [],
                "recommendation": "Ordenar foco.",
            },
        }
        parsed = parse_user_query("quiero solo proximos pasos")
        response = build_response_from_query(parsed, user_query="quiero solo proximos pasos", conversation_context=context)
        self.assertIn("no veo elementos", response.lower())
        self.assertTrue(parsed.get("_adaptive_degraded"))


if __name__ == "__main__":
    unittest.main()

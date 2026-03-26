"""Tests para Sesión 61 — BUG 1, BUG 2, BUG 3.

BUG 1: agenda_time_hint con prefijo "a las" no se parseaba.
BUG 2: "lunes que viene" (sin "el") no matcheaba en _parse_next_weekday.
BUG 3: get_open_tasks_by_client_name con client_name=null pedía clarificación
       en lugar de devolver todas las tareas abiertas.
"""

import unittest
from datetime import date, time, timedelta
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# BUG 1 — normalize_time_hint strips "a las / las / a la / la" prefixes
# ---------------------------------------------------------------------------

class NormalizeTimeHintTests(unittest.TestCase):
    """normalize_time_hint: función pura que remueve prefijos de tiempo."""

    def _normalize(self, raw):
        from app.services.agenda_service import normalize_time_hint
        return normalize_time_hint(raw)

    def test_a_las_prefix_stripped(self):
        self.assertEqual(self._normalize("a las 17:00"), "17:00")

    def test_las_prefix_stripped(self):
        self.assertEqual(self._normalize("las 9:00"), "9:00")

    def test_a_la_prefix_stripped(self):
        self.assertEqual(self._normalize("a la 1:00"), "1:00")

    def test_la_prefix_stripped(self):
        self.assertEqual(self._normalize("la 10:30"), "10:30")

    def test_plain_time_unchanged(self):
        self.assertEqual(self._normalize("17:00"), "17:00")

    def test_plain_time_9_unchanged(self):
        self.assertEqual(self._normalize("9:00"), "9:00")

    def test_none_returns_none(self):
        self.assertIsNone(self._normalize(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(self._normalize(""))

    def test_tilde_insensitive_a_las(self):
        # after normalization accents are stripped
        result = self._normalize("a las 18:00")
        self.assertEqual(result, "18:00")


class ResolveTimeHintWithPrefixTests(unittest.TestCase):
    """resolve_agenda_time_hint acepta hints con prefijo 'a las'."""

    def _resolve(self, hint):
        from app.services.agenda_service import resolve_agenda_time_hint
        return resolve_agenda_time_hint(hint)

    def test_a_las_17_resolves(self):
        result = self._resolve("a las 17:00")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["scheduled_time"], time(17, 0))

    def test_a_la_1_resolves(self):
        result = self._resolve("a la 1:00")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["scheduled_time"], time(1, 0))

    def test_las_9_resolves(self):
        result = self._resolve("las 9:00")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["scheduled_time"], time(9, 0))

    def test_plain_17_still_resolves(self):
        result = self._resolve("17:00")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["scheduled_time"], time(17, 0))

    def test_plain_9_still_resolves(self):
        result = self._resolve("9:00")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["scheduled_time"], time(9, 0))

    def test_18hs_still_resolves(self):
        result = self._resolve("18hs")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["scheduled_time"], time(18, 0))

    def test_none_hint_resolves_to_no_time(self):
        result = self._resolve(None)
        self.assertTrue(result["resolved"])
        self.assertIsNone(result["scheduled_time"])


# ---------------------------------------------------------------------------
# BUG 2 — _parse_next_weekday funciona con y sin artículo "el"
# ---------------------------------------------------------------------------

class ParseNextWeekdayTests(unittest.TestCase):
    """_parse_next_weekday: 'X que viene' y 'el X que viene' deben funcionar."""

    def _parse(self, hint):
        from app.services.agenda_service import _parse_next_weekday
        import unicodedata
        normalized = unicodedata.normalize("NFKD", hint.strip().lower())
        normalized = "".join(c for c in normalized if not unicodedata.combining(c))
        return _parse_next_weekday(normalized)

    # Con artículo "el"
    def test_el_lunes_que_viene(self):
        self.assertEqual(self._parse("el lunes que viene"), 0)

    def test_el_martes_que_viene(self):
        self.assertEqual(self._parse("el martes que viene"), 1)

    def test_el_miercoles_que_viene(self):
        self.assertEqual(self._parse("el miércoles que viene"), 2)

    def test_el_jueves_que_viene(self):
        self.assertEqual(self._parse("el jueves que viene"), 3)

    def test_el_viernes_que_viene(self):
        self.assertEqual(self._parse("el viernes que viene"), 4)

    def test_el_sabado_que_viene(self):
        self.assertEqual(self._parse("el sábado que viene"), 5)

    def test_el_domingo_que_viene(self):
        self.assertEqual(self._parse("el domingo que viene"), 6)

    # Sin artículo "el"
    def test_lunes_que_viene_sin_el(self):
        self.assertEqual(self._parse("lunes que viene"), 0)

    def test_martes_que_viene_sin_el(self):
        self.assertEqual(self._parse("martes que viene"), 1)

    def test_miercoles_que_viene_sin_el(self):
        self.assertEqual(self._parse("miércoles que viene"), 2)

    def test_jueves_que_viene_sin_el(self):
        self.assertEqual(self._parse("jueves que viene"), 3)

    def test_viernes_que_viene_sin_el(self):
        self.assertEqual(self._parse("viernes que viene"), 4)

    def test_sabado_que_viene_sin_el(self):
        self.assertEqual(self._parse("sábado que viene"), 5)

    def test_domingo_que_viene_sin_el(self):
        self.assertEqual(self._parse("domingo que viene"), 6)

    # Casos que no deben matchear
    def test_lunes_solo_no_matches(self):
        self.assertIsNone(self._parse("lunes"))

    def test_empty_no_matches(self):
        self.assertIsNone(self._parse(""))


class ResolveDateHintNextWeekdayTests(unittest.TestCase):
    """resolve_agenda_date_hint resuelve 'X que viene' con y sin 'el'."""

    def setUp(self):
        self.today = date(2026, 3, 24)  # martes

    def _resolve(self, hint):
        from app.services.agenda_service import resolve_agenda_date_hint
        return resolve_agenda_date_hint(hint, today=self.today)

    def test_lunes_que_viene_sin_el(self):
        result = self._resolve("lunes que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 30))

    def test_el_lunes_que_viene_con_el(self):
        result = self._resolve("el lunes que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 30))

    def test_viernes_que_viene_sin_el(self):
        result = self._resolve("viernes que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 27))

    def test_el_viernes_que_viene_con_el(self):
        result = self._resolve("el viernes que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 27))

    def test_miercoles_que_viene_sin_el(self):
        result = self._resolve("miércoles que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 25))


# ---------------------------------------------------------------------------
# BUG 3 — get_open_tasks_by_client_name con client_name=null devuelve todo
# ---------------------------------------------------------------------------

class OpenTasksNullClientNameTests(unittest.TestCase):
    """BUG 3: intent=get_open_tasks_by_client_name + client_name=None → todas."""

    def _make_task(self, title, status="abierta", project_name="Inbox", client_name=None):
        task = MagicMock()
        task.title = title
        task.status = status
        task.priority = "normal"
        task.project = MagicMock()
        task.project.name = project_name
        if client_name:
            task.project.client = MagicMock()
            task.project.client.name = client_name
        else:
            task.project.client = None
        return task

    def test_null_client_returns_all_open_tasks(self):
        from app.services.query_response_service import build_response_from_query

        tasks = [
            self._make_task("Revisión propuesta", client_name="CAM"),
            self._make_task("Entrega informe", client_name="Rosario"),
        ]
        parsed = {"intent": "get_open_tasks_by_client_name", "client_name": None}
        with patch("app.services.query_response_service.get_all_open_tasks", return_value=tasks):
            response = build_response_from_query(parsed, user_query="qué tareas tengo")

        self.assertIn("Revisión propuesta", response)
        self.assertIn("Entrega informe", response)
        self.assertNotIn("no pude identificar", response.lower())

    def test_null_client_no_tasks_friendly_message(self):
        from app.services.query_response_service import build_response_from_query

        parsed = {"intent": "get_open_tasks_by_client_name", "client_name": None}
        with patch("app.services.query_response_service.get_all_open_tasks", return_value=[]):
            response = build_response_from_query(parsed, user_query="decime las tareas")

        self.assertIn("No encontré", response)

    def test_null_client_response_includes_client_and_project(self):
        from app.services.query_response_service import build_response_from_query

        tasks = [self._make_task("Tarea X", project_name="Proyecto Alpha", client_name="CAM")]
        parsed = {"intent": "get_open_tasks_by_client_name", "client_name": None}
        with patch("app.services.query_response_service.get_all_open_tasks", return_value=tasks):
            response = build_response_from_query(parsed, user_query="decime las tareas que tengo")

        self.assertIn("CAM", response)
        self.assertIn("Proyecto Alpha", response)

    def test_explicit_client_still_filters_by_client(self):
        from app.services.query_response_service import build_response_from_query

        parsed = {"intent": "get_open_tasks_by_client_name", "client_name": "cam"}
        resolved_client = {"id": 1, "name": "CAM"}
        mock_refs = {"client": {"resolved": resolved_client, "ambiguous": False}}
        tasks = [self._make_task("Tarea CAM", client_name="CAM")]

        with patch("app.services.query_response_service.resolve_references", return_value=mock_refs), \
             patch("app.services.query_response_service.get_open_tasks_by_client_id", return_value=tasks):
            response = build_response_from_query(parsed, user_query="qué tareas tengo de cam")

        self.assertIn("Tarea CAM", response)
        self.assertIn("CAM", response)

    def test_get_all_open_tasks_repository_method_exists(self):
        """Verificar que task_repository expone get_all_open_tasks."""
        from app.repositories import task_repository
        self.assertTrue(
            hasattr(task_repository, "get_all_open_tasks"),
            "task_repository.get_all_open_tasks debe existir",
        )


if __name__ == "__main__":
    unittest.main()

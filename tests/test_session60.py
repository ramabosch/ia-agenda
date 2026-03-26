"""Tests para Sesión 60 — BUG 1, BUG 2 y FEATURE de temporalidad relativa extendida."""

import unittest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


class HybridParserBug1Tests(unittest.TestCase):
    """BUG 1: rules=unknown no debe ganarle a LLM con intent válido."""

    def _make_llm_action(self, intent, **kwargs):
        base = {
            "intent": intent,
            "client_name": None,
            "project_name": None,
            "task_name": None,
        }
        base.update(kwargs)
        return base

    def test_rules_unknown_llm_valid_llm_wins(self):
        """'qué tareas tengo' → rules devuelven unknown, LLM devuelve intent válido → LLM gana."""
        from app.services.hybrid_parser_service import parse_user_query_hybrid

        llm_action = self._make_llm_action("get_open_tasks_by_client_name")
        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[llm_action]):
            result = parse_user_query_hybrid("qué tareas tengo")

        self.assertEqual(result["intent"], "get_open_tasks_by_client_name")
        self.assertNotEqual(result["intent"], "unknown")

    def test_rules_unknown_llm_valid_short_query_llm_wins(self):
        """Query de 3 palabras con rules=unknown y LLM válido → LLM debe ganar (no silenciado por _is_short_or_follow_up)."""
        from app.services.hybrid_parser_service import parse_user_query_hybrid

        llm_action = self._make_llm_action("get_active_projects")
        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[llm_action]):
            result = parse_user_query_hybrid("que proyectos hay")

        self.assertNotEqual(result["intent"], "unknown")

    def test_rules_valid_and_llm_valid_rules_still_preferred_for_short_update(self):
        """Comportamiento existente: rules=update_task_status + query corta → rules ganan."""
        from app.services.hybrid_parser_service import parse_user_query_hybrid

        llm_action = self._make_llm_action("get_task_summary", task_name="otra cosa")
        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[llm_action]):
            result = parse_user_query_hybrid("cerrala")

        self.assertEqual(result["intent"], "update_task_status")
        self.assertEqual(result["_parser_source"], "rules")

    def test_rules_unknown_llm_unknown_rules_fallback(self):
        """Ambos desconocen → rules fallback normal, sin error."""
        from app.services.hybrid_parser_service import parse_user_query_hybrid

        llm_action = self._make_llm_action("unknown")
        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[llm_action]):
            result = parse_user_query_hybrid("qué tareas tengo")

        self.assertIn("intent", result)
        self.assertEqual(result.get("_parser_source"), "rules")

    def test_rules_unknown_llm_valid_parser_decision_llm_accepted(self):
        """Cuando LLM gana sobre rules=unknown, _parser_decision debe ser llm_accepted."""
        from app.services.hybrid_parser_service import parse_user_query_hybrid

        llm_action = self._make_llm_action("get_open_tasks_by_client_name")
        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[llm_action]):
            result = parse_user_query_hybrid("qué tareas tengo")

        self.assertEqual(result.get("_parser_decision"), "llm_accepted")


class HybridParserBug2Tests(unittest.TestCase):
    """BUG 2: el LLM debe llamarse exactamente 1 vez por request."""

    def test_llm_called_exactly_once(self):
        """parse_actions_with_llm se llama exactamente 1 vez por request."""
        from app.services.hybrid_parser_service import parse_user_query_hybrid

        llm_action = {
            "intent": "get_open_tasks_by_client_name",
            "client_name": None,
            "project_name": None,
            "task_name": None,
        }
        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[llm_action]) as mock_llm:
            parse_user_query_hybrid("qué tareas tengo")

        self.assertEqual(mock_llm.call_count, 1, f"Se esperaba 1 llamada al LLM, se hicieron {mock_llm.call_count}")

    def test_llm_called_exactly_once_for_rules_dominated_query(self):
        """Incluso cuando las reglas dominan, parse_actions_with_llm se llama solo 1 vez."""
        from app.services.hybrid_parser_service import parse_user_query_hybrid

        llm_action = {"intent": "get_task_summary"}
        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[llm_action]) as mock_llm:
            parse_user_query_hybrid("Agenda una reunion con CAM para manana a las 10:00")

        self.assertEqual(mock_llm.call_count, 1)

    def test_llm_called_exactly_once_for_short_query(self):
        """Consulta corta → sigue siendo 1 sola llamada al LLM."""
        from app.services.hybrid_parser_service import parse_user_query_hybrid

        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[]) as mock_llm:
            parse_user_query_hybrid("cerrala")

        self.assertEqual(mock_llm.call_count, 1)

    def test_result_identical_single_vs_double_call(self):
        """El resultado con 1 llamada es funcionalmente equivalente al anterior comportamiento."""
        from app.services.hybrid_parser_service import parse_user_query_hybrid

        llm_action = {
            "intent": "get_open_tasks_by_client_name",
            "client_name": None,
            "project_name": None,
            "task_name": None,
        }
        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[llm_action]):
            result = parse_user_query_hybrid("qué tareas tengo")

        self.assertEqual(result["intent"], "get_open_tasks_by_client_name")
        self.assertIn("_actions", result)


class AgendaRelativeDateTests(unittest.TestCase):
    """FEATURE: temporalidad relativa extendida en agenda."""

    def setUp(self):
        self.today = date(2026, 3, 24)  # martes

    def _resolve(self, hint):
        from app.services.agenda_service import resolve_agenda_date_hint
        return resolve_agenda_date_hint(hint, today=self.today)

    # --- pasado mañana ---

    def test_pasado_manana_resolves_to_today_plus_2(self):
        result = self._resolve("pasado mañana")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=2))
        self.assertEqual(result["scope"], "day_after_tomorrow")

    def test_pasado_manana_sin_tilde_resolves(self):
        result = self._resolve("pasado manana")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=2))

    # --- dentro de N días ---

    def test_dentro_de_3_dias_resolves(self):
        result = self._resolve("dentro de 3 días")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=3))

    def test_dentro_de_4_dias_sin_tilde(self):
        result = self._resolve("dentro de 4 dias")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=4))

    def test_dentro_de_un_dia(self):
        result = self._resolve("dentro de un dia")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=1))

    # --- en N días ---

    def test_en_5_dias(self):
        result = self._resolve("en 5 días")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=5))

    def test_en_cuatro_dias(self):
        result = self._resolve("en cuatro dias")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=4))

    # --- en una / dos semanas ---

    def test_en_una_semana_resolves_to_today_plus_7(self):
        result = self._resolve("en una semana")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=7))

    def test_en_dos_semanas_resolves_to_today_plus_14(self):
        result = self._resolve("en dos semanas")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=14))

    def test_en_1_semana_resolves(self):
        result = self._resolve("en 1 semana")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=7))

    def test_en_2_semanas_resolves(self):
        result = self._resolve("en 2 semanas")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=14))

    # --- la semana que viene → lunes siguiente ---

    def test_la_semana_que_viene_resolves_to_next_monday(self):
        result = self._resolve("la semana que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["scope"], "next_week")
        # today is Tuesday 2026-03-24; next Monday = 2026-03-30
        self.assertEqual(result["start_date"], date(2026, 3, 30))

    # --- el X que viene ---

    def test_el_lunes_que_viene(self):
        # today is Tuesday 2026-03-24; next Monday = 2026-03-30
        result = self._resolve("el lunes que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 30))

    def test_el_miercoles_que_viene(self):
        # today is Tuesday 2026-03-24; next Wednesday = 2026-03-25
        result = self._resolve("el miércoles que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 25))

    def test_el_viernes_que_viene(self):
        # today is Tuesday 2026-03-24; next Friday = 2026-03-27
        result = self._resolve("el viernes que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 27))

    # --- hints existentes no se rompen ---

    def test_hoy_still_works(self):
        result = self._resolve("hoy")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today)

    def test_manana_still_works(self):
        result = self._resolve("mañana")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=1))

    def test_esta_semana_still_works(self):
        result = self._resolve("esta semana")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["scope"], "this_week")

    def test_viernes_plain_still_works(self):
        # today is Tuesday 2026-03-24; next Friday = 2026-03-27
        result = self._resolve("viernes")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 27))

    def test_dentro_de_una_semana_still_works(self):
        result = self._resolve("dentro de una semana")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], self.today + timedelta(days=7))

    def test_empty_hint_returns_unresolved(self):
        result = self._resolve(None)
        self.assertFalse(result["resolved"])
        self.assertEqual(result["error"], "missing_date")

    def test_unknown_hint_returns_unresolved(self):
        result = self._resolve("cuando pueda")
        self.assertFalse(result["resolved"])
        self.assertEqual(result["error"], "unsupported_date")

    # --- "X que viene" sin "el" (BUG de sesión 61) ---

    def test_lunes_que_viene_sin_el(self):
        """El LLM suele omitir el artículo: 'lunes que viene' debe resolver igual que 'el lunes que viene'."""
        result = self._resolve("lunes que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 30))  # próximo lunes

    def test_viernes_que_viene_sin_el(self):
        result = self._resolve("viernes que viene")
        self.assertTrue(result["resolved"])
        self.assertEqual(result["target_date"], date(2026, 3, 27))

    # --- "a las HH:MM" como agenda_time_hint (BUG de sesión 61) ---


class AgendaTimeHintNormalizationTests(unittest.TestCase):
    """Fix: agenda_time_hint con prefijo 'a las' debe resolverse correctamente."""

    def _resolve_time(self, hint):
        from app.services.agenda_service import resolve_agenda_time_hint
        return resolve_agenda_time_hint(hint)

    def test_a_las_prefix_stripped(self):
        result = self._resolve_time("a las 17:00")
        self.assertTrue(result["resolved"])
        from datetime import time
        self.assertEqual(result["scheduled_time"], time(17, 0))

    def test_a_las_hour_only(self):
        result = self._resolve_time("a las 18")
        self.assertTrue(result["resolved"])
        from datetime import time
        self.assertEqual(result["scheduled_time"], time(18, 0))

    def test_las_prefix_stripped(self):
        result = self._resolve_time("las 9:30")
        self.assertTrue(result["resolved"])
        from datetime import time
        self.assertEqual(result["scheduled_time"], time(9, 30))

    def test_plain_time_still_works(self):
        result = self._resolve_time("17:00")
        self.assertTrue(result["resolved"])
        from datetime import time
        self.assertEqual(result["scheduled_time"], time(17, 0))

    def test_time_with_hs_still_works(self):
        result = self._resolve_time("18hs")
        self.assertTrue(result["resolved"])
        from datetime import time
        self.assertEqual(result["scheduled_time"], time(18, 0))


class OpenTasksNullClientTests(unittest.TestCase):
    """Fix: get_open_tasks_by_client_name con client_name=null devuelve todas las tareas abiertas."""

    def _make_task(self, title, status="abierta", project_name="Inbox", client_name=None):
        task = MagicMock()
        task.title = title
        task.status = status
        task.priority = "normal"
        if project_name:
            task.project = MagicMock()
            task.project.name = project_name
            if client_name:
                task.project.client = MagicMock()
                task.project.client.name = client_name
            else:
                task.project.client = None
        else:
            task.project = None
        return task

    def test_null_client_returns_all_open_tasks(self):
        from app.services.query_response_service import build_response_from_query

        tasks = [
            self._make_task("Tarea A", client_name="Cam"),
            self._make_task("Tarea B", client_name="Rosario"),
        ]
        parsed = {
            "intent": "get_open_tasks_by_client_name",
            "client_name": None,
        }
        with patch("app.services.query_response_service.get_all_open_tasks", return_value=tasks):
            response = build_response_from_query(parsed, user_query="qué tareas tengo")

        self.assertIn("Tarea A", response)
        self.assertIn("Tarea B", response)
        self.assertNotIn("no pude identificar", response.lower())

    def test_null_client_no_tasks_returns_friendly_message(self):
        from app.services.query_response_service import build_response_from_query

        parsed = {
            "intent": "get_open_tasks_by_client_name",
            "client_name": None,
        }
        with patch("app.services.query_response_service.get_all_open_tasks", return_value=[]):
            response = build_response_from_query(parsed, user_query="qué tareas tengo")

        self.assertIn("No encontré", response)

    def test_explicit_client_still_uses_client_filter(self):
        """Cuando hay client_name, el comportamiento anterior no cambia."""
        from app.services.query_response_service import build_response_from_query
        from unittest.mock import patch, MagicMock

        parsed = {
            "intent": "get_open_tasks_by_client_name",
            "client_name": "cam",
        }
        resolved_client = {"id": 1, "name": "Cam"}
        mock_refs = {"client": {"resolved": resolved_client}}
        tasks = [self._make_task("Tarea de Cam", client_name="Cam")]

        with patch("app.services.query_response_service.resolve_references", return_value=mock_refs), \
             patch("app.services.query_response_service.get_open_tasks_by_client_id", return_value=tasks):
            response = build_response_from_query(parsed, user_query="qué tareas tengo con cam")

        self.assertIn("Tarea de Cam", response)
        self.assertIn("Cam", response)


if __name__ == "__main__":
    unittest.main()

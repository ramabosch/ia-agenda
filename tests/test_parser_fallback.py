"""Tests para el fallback robusto del parser híbrido (Task 3 - Sesión 59)."""

import json
import logging
import unittest
from unittest.mock import patch, MagicMock


class ParserFallbackTests(unittest.TestCase):
    """Verifica que el parser híbrido maneja correctamente resultados inválidos del LLM."""

    # ------------------------------------------------------------------
    # LLM devuelve JSON vacío → fallback a reglas
    # ------------------------------------------------------------------

    def test_llm_returns_empty_list_falls_back_to_rules(self):
        """Si parse_actions_with_llm devuelve [], se usa el parser de reglas."""
        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[]):
            from app.services.hybrid_parser_service import parse_user_query_hybrid
            result = parse_user_query_hybrid("que proyectos hay activos")

        self.assertEqual(result.get("_parser_source"), "rules")

    def test_llm_returns_empty_list_result_has_valid_intent(self):
        """Al hacer fallback a reglas, el resultado debe tener un intent coherente."""
        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[]):
            from app.services.hybrid_parser_service import parse_user_query_hybrid
            result = parse_user_query_hybrid("que proyectos hay activos")

        self.assertIn("intent", result)
        self.assertIsNotNone(result["intent"])

    # ------------------------------------------------------------------
    # LLM devuelve intent desconocido → fallback a reglas
    # ------------------------------------------------------------------

    def test_llm_returns_unknown_intent_falls_back_to_rules(self):
        """Si el LLM devuelve intent='unknown', se usa el parser de reglas."""
        unknown_action = {
            "intent": "unknown",
            "_parser_source": "llm",
            "client_name": None,
            "project_name": None,
            "task_name": None,
            "task_id": None,
            "project_id": None,
            "content": None,
            "new_status": None,
            "new_priority": None,
            "priority_direction": None,
            "next_action": None,
            "last_note": None,
            "entity_hint": None,
            "expected_scope": None,
            "secondary_descriptor": None,
            "contrast_hint": None,
            "use_previous_candidates": None,
            "expand_mode": None,
            "recommendation_focus": None,
            "followup_focus": None,
            "filter_mode": None,
            "rephrase_style": None,
            "due_hint": None,
            "time_scope": None,
            "temporal_focus": None,
            "agenda_kind": None,
            "agenda_date_hint": None,
            "agenda_time_hint": None,
            "agenda_title": None,
            "agenda_query_scope": None,
            "agenda_boolean_query": None,
            "agenda_target_title": None,
            "agenda_target_date_hint": None,
            "agenda_target_time_hint": None,
            "agenda_target_kind": None,
            "agenda_use_context": None,
            "agenda_new_date_hint": None,
            "agenda_new_time_hint": None,
            "command": None,
        }

        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[unknown_action]):
            from app.services.hybrid_parser_service import parse_user_query_hybrid
            result = parse_user_query_hybrid("que proyectos hay activos")

        self.assertEqual(result.get("_parser_source"), "rules")

    # ------------------------------------------------------------------
    # LLM lanza excepción → fallback a reglas, sin propagación
    # ------------------------------------------------------------------

    def test_llm_exception_does_not_propagate(self):
        """Una excepción en el LLM no debe llegar al usuario."""
        from app.services.llm_parser_service import parse_actions_with_llm

        with patch("requests.post", side_effect=ConnectionError("timeout")):
            try:
                result = parse_actions_with_llm("crear tarea de prueba")
            except Exception as exc:
                self.fail(f"parse_actions_with_llm propagó excepción: {exc}")

        self.assertEqual(result, [])

    def test_llm_timeout_falls_back_gracefully(self):
        """Un timeout del LLM retorna [] sin excepción."""
        import requests as req_module

        with patch("requests.post", side_effect=req_module.Timeout("timeout")):
            from app.services.llm_parser_service import parse_actions_with_llm
            result = parse_actions_with_llm("listar tareas")

        self.assertIsInstance(result, list)

    def test_llm_json_decode_error_returns_empty(self):
        """Si el LLM devuelve JSON malformado, se retorna [] sin excepción."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        # "[not valid json]" pasa _clean_model_output pero falla json.loads
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "[not valid json]"}}]
        }

        with patch("requests.post", return_value=mock_response):
            from app.services.llm_parser_service import parse_actions_with_llm
            result = parse_actions_with_llm("crea una tarea")

        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # Fallback completo: mensaje genérico al usuario
    # ------------------------------------------------------------------

    def test_process_turn_returns_fallback_message_on_total_failure(self):
        """Si todo falla en process_conversation_turn, el usuario recibe el mensaje genérico."""
        from app.services.conversation_runtime_service import process_conversation_turn, _FALLBACK_RESPONSE

        def explode(*args, **kwargs):
            raise RuntimeError("todo roto")

        with patch("app.services.conversation_runtime_service.parse_user_query_hybrid", side_effect=explode):
            result = process_conversation_turn("hola")

        self.assertEqual(result["response_text"], _FALLBACK_RESPONSE)

    def test_process_turn_fallback_does_not_raise(self):
        """process_conversation_turn nunca debe propagar excepciones al caller."""
        from app.services.conversation_runtime_service import process_conversation_turn

        with patch("app.services.conversation_runtime_service.build_response_from_query",
                   side_effect=ValueError("error en build")):
            with patch("app.services.conversation_runtime_service.parse_user_query_hybrid",
                       return_value={"intent": "get_active_projects", "_parser_source": "rules"}):
                try:
                    result = process_conversation_turn("listar proyectos")
                except Exception as exc:
                    self.fail(f"process_conversation_turn propagó excepción: {exc}")

        self.assertIn("response_text", result)

    def test_process_turn_fallback_preserves_original_context(self):
        """Al fallar, el contexto original debe devolverse sin modificaciones."""
        from app.services.conversation_runtime_service import process_conversation_turn

        ctx = {"_isolated": True, "recent_entities": [{"scope": "task", "id": 1, "name": "algo"}]}

        with patch("app.services.conversation_runtime_service.parse_user_query_hybrid",
                   side_effect=RuntimeError("boom")):
            result = process_conversation_turn("algo", conversation_context=ctx)

        self.assertEqual(result["conversation_context"], ctx)

    # ------------------------------------------------------------------
    # Logging de fallback
    # ------------------------------------------------------------------

    def test_llm_exception_logs_fallback_reason(self):
        """Una excepción del LLM debe loggear la razón del fallback."""
        from app.services.structured_logger import _logger
        captured = _CapturingHandler()
        _logger.addHandler(captured)

        try:
            with patch("app.config.ENABLE_STRUCTURED_LOGGING", True):
                with patch("requests.post", side_effect=ConnectionError("down")):
                    from app.services.llm_parser_service import parse_actions_with_llm
                    parse_actions_with_llm("test query")
        finally:
            _logger.removeHandler(captured)

        fallback_logs = [
            json.loads(r) for r in captured.records
            if "parser_decision" in r and "llm_fallback" in r
        ]
        self.assertGreater(len(fallback_logs), 0, "Debe haber al menos un log de fallback")
        reasons = [r.get("reason") for r in fallback_logs]
        self.assertIn("llm_exception", reasons)

    def test_llm_empty_response_logs_reason(self):
        """Si el LLM devuelve output vacío, debe loggear la razón."""
        from app.services.structured_logger import _logger
        captured = _CapturingHandler()
        _logger.addHandler(captured)

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}]
        }

        try:
            with patch("app.config.ENABLE_STRUCTURED_LOGGING", True):
                with patch("requests.post", return_value=mock_response):
                    from app.services.llm_parser_service import parse_actions_with_llm
                    parse_actions_with_llm("test")
        finally:
            _logger.removeHandler(captured)

        fallback_logs = [
            json.loads(r) for r in captured.records
            if "parser_decision" in r
        ]
        self.assertGreater(len(fallback_logs), 0)


class _CapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.format(record))


if __name__ == "__main__":
    unittest.main()

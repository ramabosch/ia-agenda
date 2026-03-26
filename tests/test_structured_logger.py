"""Tests para el logging estructurado (Task 1 - Sesión 59)."""

import json
import logging
import unittest
from unittest.mock import patch


class StructuredLoggerTests(unittest.TestCase):
    def setUp(self):
        # Capturar mensajes del logger sin contaminar stdout
        from app.services.structured_logger import _logger

        self._handler = _CapturingHandler()
        _logger.addHandler(self._handler)
        self._logger_ref = _logger

    def tearDown(self):
        self._logger_ref.removeHandler(self._handler)

    # ------------------------------------------------------------------
    # log_conversation_turn
    # ------------------------------------------------------------------

    def test_log_conversation_turn_emits_required_fields(self):
        """El log debe contener ts, intent, parser_source, action_status, latency_ms."""
        from app.services.structured_logger import log_conversation_turn

        with patch("app.config.ENABLE_STRUCTURED_LOGGING", True):
            log_conversation_turn(
                intent="create_task",
                parser_source="rules",
                action_status="ok",
                latency_ms=45.0,
            )

        self.assertEqual(len(self._handler.records), 1)
        record = json.loads(self._handler.records[0])

        self.assertIn("ts", record)
        self.assertEqual(record["intent"], "create_task")
        self.assertEqual(record["parser_source"], "rules")
        self.assertEqual(record["action_status"], "ok")
        self.assertAlmostEqual(record["latency_ms"], 45.0, delta=0.5)

    def test_log_conversation_turn_ts_is_iso_format(self):
        """El timestamp debe estar en formato ISO 8601 con Z al final."""
        from app.services.structured_logger import log_conversation_turn

        with patch("app.config.ENABLE_STRUCTURED_LOGGING", True):
            log_conversation_turn(
                intent="get_active_projects",
                parser_source="llm",
                action_status="read",
                latency_ms=120.0,
            )

        record = json.loads(self._handler.records[0])
        ts = record["ts"]
        self.assertTrue(ts.endswith("Z"), f"Timestamp no termina en Z: {ts}")
        # Debe tener al menos fecha y hora
        self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_log_conversation_turn_disabled_emits_nothing(self):
        """Con ENABLE_STRUCTURED_LOGGING=False no debe emitirse nada."""
        from app.services.structured_logger import log_conversation_turn

        with patch("app.config.ENABLE_STRUCTURED_LOGGING", False):
            log_conversation_turn(
                intent="create_task",
                parser_source="rules",
                action_status="ok",
                latency_ms=10.0,
            )

        self.assertEqual(len(self._handler.records), 0)

    def test_log_conversation_turn_extra_fields_included(self):
        """Los campos extra opcionales deben aparecer en el JSON."""
        from app.services.structured_logger import log_conversation_turn

        with patch("app.config.ENABLE_STRUCTURED_LOGGING", True):
            log_conversation_turn(
                intent="update_task_status",
                parser_source="rules",
                action_status="executed",
                latency_ms=30.0,
                extra={"task_id": 7},
            )

        record = json.loads(self._handler.records[0])
        self.assertEqual(record["task_id"], 7)

    # ------------------------------------------------------------------
    # log_parser_decision
    # ------------------------------------------------------------------

    def test_log_parser_decision_emits_event_field(self):
        """log_parser_decision debe emitir event=parser_decision."""
        from app.services.structured_logger import log_parser_decision

        with patch("app.config.ENABLE_STRUCTURED_LOGGING", True):
            log_parser_decision(
                decision="rules_fallback",
                reason="llm_empty_response",
                query_preview="crea una tarea",
            )

        self.assertEqual(len(self._handler.records), 1)
        record = json.loads(self._handler.records[0])
        self.assertEqual(record["event"], "parser_decision")
        self.assertEqual(record["decision"], "rules_fallback")
        self.assertEqual(record["reason"], "llm_empty_response")

    def test_log_parser_decision_disabled_emits_nothing(self):
        """Con ENABLE_STRUCTURED_LOGGING=False, log_parser_decision no emite nada."""
        from app.services.structured_logger import log_parser_decision

        with patch("app.config.ENABLE_STRUCTURED_LOGGING", False):
            log_parser_decision(decision="rules_fallback", reason="llm_exception")

        self.assertEqual(len(self._handler.records), 0)

    def test_logger_does_not_raise_on_broken_data(self):
        """El logger nunca debe propagar excepciones aunque los datos sean raros."""
        from app.services.structured_logger import log_conversation_turn

        with patch("app.config.ENABLE_STRUCTURED_LOGGING", True):
            # latency_ms=None es válido
            try:
                log_conversation_turn(
                    intent=None,
                    parser_source=None,
                    action_status=None,
                    latency_ms=None,
                )
            except Exception as exc:
                self.fail(f"log_conversation_turn lanzó excepción: {exc}")


class _CapturingHandler(logging.Handler):
    """Handler que acumula mensajes en memoria para los tests."""

    def __init__(self):
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.format(record))


if __name__ == "__main__":
    unittest.main()

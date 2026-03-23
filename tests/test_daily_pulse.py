import unittest
from datetime import date, time
from unittest.mock import patch

from app.services.query_response_service import build_response_from_query
from tests.helpers import make_agenda_item


class DailyPulseTests(unittest.TestCase):
    def test_daily_pulse_consolidates_agenda_urgent_tasks_and_inbox(self):
        today_value = date.today()
        agenda_items = [
            make_agenda_item(1, "reunion con Cam", today_value, scheduled_time=time(10, 0), kind="event"),
        ]
        overdue_items = [
            {"task_id": 11, "title": "cerrar presupuesto", "project_name": "Inbox", "due_date": "2026-03-20"},
        ]
        due_today_items = [
            {"task_id": 12, "title": "llamar a Rosario Capilar", "project_name": "Ventas", "due_date": today_value.isoformat()},
        ]
        parsed = {"intent": "get_daily_pulse"}
        context = {"channel_identity": {"channel": "telegram", "telegram_id": 6043652463}}

        with patch("app.services.query_response_service.get_agenda_items_for_date", return_value=agenda_items) as agenda_mock, patch(
            "app.services.query_response_service.get_temporal_task_snapshot",
            side_effect=[
                {"matched_items": overdue_items},
                {"matched_items": due_today_items},
            ],
        ) as temporal_mock, patch(
            "app.services.query_response_service.count_pending_inbox_tasks",
            return_value=3,
        ):
            response = build_response_from_query(parsed, user_query="que hay para hoy", conversation_context=context)

        agenda_mock.assert_called_once_with(today_value)
        self.assertEqual(temporal_mock.call_count, 2)
        self.assertIn("Hola Tu Nombre", response)
        self.assertIn("reunion con Cam", response)
        self.assertIn("cerrar presupuesto", response)
        self.assertIn("3 temas pendientes", response)

    def test_daily_pulse_does_not_mix_items_outside_today(self):
        parsed = {"intent": "get_daily_pulse"}

        with patch("app.services.query_response_service.get_agenda_items_for_date", return_value=[]), patch(
            "app.services.query_response_service.get_temporal_task_snapshot",
            side_effect=[
                {"matched_items": []},
                {"matched_items": []},
            ],
        ), patch(
            "app.services.query_response_service.count_pending_inbox_tasks",
            return_value=0,
        ):
            response = build_response_from_query(parsed, user_query="resumen de hoy", conversation_context={})

        self.assertIn("Sin eventos", response)
        self.assertIn("Sin tareas urgentes", response)
        self.assertNotIn("manana", response.lower())

    def test_new_session_greeting_uses_first_agenda_item(self):
        today_value = date.today()
        agenda_items = [
            make_agenda_item(2, "la reunion", today_value, scheduled_time=time(10, 0), kind="event"),
        ]
        parsed = {"intent": "unknown"}
        context = {
            "_new_session": True,
            "channel_identity": {"channel": "telegram", "telegram_id": 6043652463},
        }

        with patch("app.services.query_response_service.get_agenda_items_for_date", return_value=agenda_items):
            response = build_response_from_query(parsed, user_query="hola", conversation_context=context)

        self.assertIn("Hola de nuevo, Tu Nombre", response)
        self.assertIn("10:00", response)
        self.assertIn("la reunion", response)


if __name__ == "__main__":
    unittest.main()

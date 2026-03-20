import unittest
from datetime import date, datetime, time
from unittest.mock import patch

from app.services.query_response_service import build_response_from_query
from app.services.query_parser_service import parse_user_query
from tests.helpers import make_agenda_item


class AgendaBehaviorTests(unittest.TestCase):
    def test_create_event_for_tomorrow_at_ten(self):
        parsed = parse_user_query("agendame manana a las 10 una reunion con Cam")

        with patch(
            "app.services.query_response_service.create_agenda_item_conversational",
            return_value={
                "created": True,
                "agenda_item_id": 1,
                "title": "reunion con cam",
                "scheduled_date": date(2026, 3, 21),
                "scheduled_time": time(10, 0),
                "kind": "event",
                "note": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "tomorrow",
                "target_date": date(2026, 3, 21),
                "start_date": date(2026, 3, 21),
                "end_date": date(2026, 3, 21),
                "label": "manana",
                "error": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_time_hint",
            return_value={
                "resolved": True,
                "scheduled_time": time(10, 0),
                "label": "10:00",
                "error": None,
            },
        ):
            response = build_response_from_query(parsed, user_query="agendame manana a las 10 una reunion con Cam")

        self.assertIn("guarde el evento", response.lower())
        self.assertIn("10:00", response)
        self.assertEqual(parsed["_conversation_context"]["scope"], "agenda")
        self.assertEqual(parsed["_audit_trace"]["action_status"], "executed")

    def test_create_reminder_for_tomorrow(self):
        parsed = parse_user_query("recordame manana revisar indicadores")

        with patch(
            "app.services.query_response_service.create_agenda_item_conversational",
            return_value={
                "created": True,
                "agenda_item_id": 2,
                "title": "revisar indicadores",
                "scheduled_date": date(2026, 3, 21),
                "scheduled_time": None,
                "kind": "reminder",
                "note": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "tomorrow",
                "target_date": date(2026, 3, 21),
                "start_date": date(2026, 3, 21),
                "end_date": date(2026, 3, 21),
                "label": "manana",
                "error": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_time_hint",
            return_value={
                "resolved": True,
                "scheduled_time": None,
                "label": None,
                "error": None,
            },
        ):
            response = build_response_from_query(parsed, user_query="recordame manana revisar indicadores")

        self.assertIn("recordatorio", response.lower())
        self.assertNotIn("hora:", response.lower())

    def test_create_event_for_friday_at_sixteen(self):
        parsed = parse_user_query("agendame para el viernes a las 16 llamar a Rosario Capilar")

        with patch(
            "app.services.query_response_service.create_agenda_item_conversational",
            return_value={
                "created": True,
                "agenda_item_id": 3,
                "title": "llamar a rosario capilar",
                "scheduled_date": date(2026, 3, 27),
                "scheduled_time": time(16, 0),
                "kind": "event",
                "note": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "weekday",
                "target_date": date(2026, 3, 27),
                "start_date": date(2026, 3, 27),
                "end_date": date(2026, 3, 27),
                "label": "viernes",
                "error": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_time_hint",
            return_value={
                "resolved": True,
                "scheduled_time": time(16, 0),
                "label": "16:00",
                "error": None,
            },
        ):
            response = build_response_from_query(parsed, user_query="agendame para el viernes a las 16 llamar a Rosario Capilar")

        self.assertIn("16:00", response)
        self.assertIn("llamar a rosario capilar", response.lower())

    def test_query_today_agenda(self):
        parsed = parse_user_query("que tengo para hoy")
        items = [make_agenda_item(1, "reunion con cam", date(2026, 3, 20), scheduled_time=time(10, 0))]

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "today",
                "target_date": date(2026, 3, 20),
                "start_date": date(2026, 3, 20),
                "end_date": date(2026, 3, 20),
                "label": "hoy",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_for_date", return_value=items):
            response = build_response_from_query(parsed, user_query="que tengo para hoy")

        self.assertIn("agenda para hoy", response.lower())
        self.assertIn("reunion con cam", response.lower())
        self.assertEqual(parsed["_conversation_context"]["scope"], "agenda")

    def test_query_tomorrow_agenda_boolean(self):
        parsed = parse_user_query("tengo algo manana")
        items = [make_agenda_item(2, "dentista", date(2026, 3, 21), scheduled_time=time(18, 0))]

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "tomorrow",
                "target_date": date(2026, 3, 21),
                "start_date": date(2026, 3, 21),
                "end_date": date(2026, 3, 21),
                "label": "manana",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_for_date", return_value=items):
            response = build_response_from_query(parsed, user_query="tengo algo manana")

        self.assertIn("si, para", response.lower())
        self.assertIn("dentista", response.lower())

    def test_query_this_week_agenda(self):
        parsed = parse_user_query("que tengo esta semana")
        items = [
            make_agenda_item(3, "dentista", date(2026, 3, 21), scheduled_time=time(18, 0)),
            make_agenda_item(4, "llamar a rosario capilar", date(2026, 3, 22), scheduled_time=time(16, 0)),
        ]

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "this_week",
                "target_date": None,
                "start_date": date(2026, 3, 20),
                "end_date": date(2026, 3, 22),
                "label": "esta semana",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_between_dates", return_value=items):
            response = build_response_from_query(parsed, user_query="que tengo esta semana")

        self.assertIn("esta semana", response.lower())
        self.assertIn("2026-03-21", response)
        self.assertIn("2026-03-22", response)

    def test_query_rest_of_day(self):
        parsed = parse_user_query("que me queda del dia")
        items = [
            make_agenda_item(5, "reunion con cam", date(2026, 3, 20), scheduled_time=time(10, 0)),
            make_agenda_item(6, "dentista", date(2026, 3, 20), scheduled_time=time(18, 0)),
        ]

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 3, 20, 12, 0)

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "today",
                "target_date": date(2026, 3, 20),
                "start_date": date(2026, 3, 20),
                "end_date": date(2026, 3, 20),
                "label": "hoy",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_for_date", return_value=items), patch(
            "app.services.query_response_service.datetime",
            new=FixedDateTime,
        ):
            response = build_response_from_query(parsed, user_query="que me queda del dia")

        self.assertIn("te queda del dia", response.lower())
        self.assertIn("dentista", response.lower())
        self.assertNotIn("reunion con cam", response.lower())

    def test_query_after_current_uses_agenda_context(self):
        parsed = parse_user_query("que tengo despues")
        items = [
            make_agenda_item(7, "reunion con cam", date(2026, 3, 20), scheduled_time=time(10, 0)),
            make_agenda_item(8, "dentista", date(2026, 3, 20), scheduled_time=time(18, 0)),
        ]
        context = {
            "_isolated": True,
            "scope": "agenda",
            "agenda_context": {
                "query_scope": "at_time",
                "anchor_date": "2026-03-20",
                "anchor_time": "10:00",
            },
        }

        with patch("app.services.query_response_service.get_agenda_items_for_date", return_value=items):
            response = build_response_from_query(parsed, user_query="que tengo despues", conversation_context=context)

        self.assertIn("despues de las 10:00", response.lower())
        self.assertIn("dentista", response.lower())
        self.assertNotIn("reunion con cam", response.lower())

    def test_missing_date_or_invalid_time_does_not_invent(self):
        parsed_missing_date = parse_user_query("agendame revisar indicadores")
        parsed_invalid_time = {
            "intent": "create_agenda_item",
            "agenda_kind": "event",
            "agenda_date_hint": "manana",
            "agenda_time_hint": "99hs",
            "agenda_title": "reunion",
        }

        response_missing_date = build_response_from_query(parsed_missing_date, user_query="agendame revisar indicadores")

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "tomorrow",
                "target_date": date(2026, 3, 21),
                "start_date": date(2026, 3, 21),
                "end_date": date(2026, 3, 21),
                "label": "manana",
                "error": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_time_hint",
            return_value={
                "resolved": False,
                "scheduled_time": None,
                "label": None,
                "error": "invalid_time",
            },
        ):
            response_invalid_time = build_response_from_query(parsed_invalid_time, user_query="agendame manana 99hs reunion")

        self.assertIn("fecha clara", response_missing_date.lower())
        self.assertIn("hora", response_invalid_time.lower())

    def test_personal_agenda_is_not_confused_with_project_task_creation(self):
        parsed = parse_user_query("recordame manana revisar indicadores")
        self.assertEqual(parsed["intent"], "create_agenda_item")
        self.assertNotEqual(parsed["intent"], "create_task")

    def test_delete_clear_agenda_item(self):
        parsed = parse_user_query("cancela el recordatorio de revisar indicadores")
        item = make_agenda_item(11, "revisar indicadores", date(2026, 3, 21), kind="reminder")

        with patch("app.services.query_response_service.get_all_agenda_items", return_value=[item]), patch(
            "app.services.query_response_service.delete_agenda_item_conversational",
            return_value={
                "deleted": True,
                "agenda_item_id": 11,
                "title": "revisar indicadores",
                "scheduled_date": date(2026, 3, 21),
                "scheduled_time": None,
                "kind": "reminder",
                "note": None,
            },
        ):
            response = build_response_from_query(parsed, user_query="cancela el recordatorio de revisar indicadores")

        self.assertIn("elimin", response.lower())
        self.assertIn("revisar indicadores", response.lower())
        self.assertEqual(parsed["_audit_trace"]["action_status"], "executed")

    def test_reschedule_agenda_item_time(self):
        parsed = parse_user_query("cambia la reunion de manana de las 11 a las 12")
        item = make_agenda_item(12, "reunion", date(2026, 3, 21), scheduled_time=time(11, 0))

        with patch("app.services.query_response_service.get_all_agenda_items", return_value=[item]), patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "tomorrow",
                "target_date": date(2026, 3, 21),
                "start_date": date(2026, 3, 21),
                "end_date": date(2026, 3, 21),
                "label": "manana",
                "error": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_time_hint",
            side_effect=[
                {"resolved": True, "scheduled_time": time(11, 0), "label": "11:00", "error": None},
                {"resolved": True, "scheduled_time": time(12, 0), "label": "12:00", "error": None},
            ],
        ), patch(
            "app.services.query_response_service.update_agenda_item_conversational",
            return_value={
                "updated": True,
                "agenda_item_id": 12,
                "title": "reunion",
                "scheduled_date": date(2026, 3, 21),
                "scheduled_time": time(12, 0),
                "kind": "event",
                "note": None,
            },
        ):
            response = build_response_from_query(parsed, user_query="cambia la reunion de manana de las 11 a las 12")

        self.assertIn("reprogram", response.lower())
        self.assertIn("12:00", response)

    def test_reschedule_agenda_item_date_and_time(self):
        parsed = parse_user_query("reprograma el dentista para el viernes a las 18")
        item = make_agenda_item(13, "dentista", date(2026, 3, 21), scheduled_time=time(10, 0))

        with patch("app.services.query_response_service.get_all_agenda_items", return_value=[item]), patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "weekday",
                "target_date": date(2026, 3, 27),
                "start_date": date(2026, 3, 27),
                "end_date": date(2026, 3, 27),
                "label": "viernes",
                "error": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_time_hint",
            return_value={"resolved": True, "scheduled_time": time(18, 0), "label": "18:00", "error": None},
        ), patch(
            "app.services.query_response_service.update_agenda_item_conversational",
            return_value={
                "updated": True,
                "agenda_item_id": 13,
                "title": "dentista",
                "scheduled_date": date(2026, 3, 27),
                "scheduled_time": time(18, 0),
                "kind": "event",
                "note": None,
            },
        ):
            response = build_response_from_query(parsed, user_query="reprograma el dentista para el viernes a las 18")

        self.assertIn("2026-03-27", response)
        self.assertIn("18:00", response)

    def test_reschedule_with_context_target(self):
        parsed = parse_user_query("pasa eso para manana")
        items = [make_agenda_item(14, "dentista", date(2026, 3, 20), scheduled_time=time(15, 0))]
        context = {
            "_isolated": True,
            "scope": "agenda",
            "agenda_context": {
                "agenda_item_id": 14,
                "title": "dentista",
                "anchor_date": "2026-03-20",
                "anchor_time": "15:00",
            },
        }

        with patch("app.services.query_response_service.get_all_agenda_items", return_value=items), patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "tomorrow",
                "target_date": date(2026, 3, 21),
                "start_date": date(2026, 3, 21),
                "end_date": date(2026, 3, 21),
                "label": "manana",
                "error": None,
            },
        ), patch(
            "app.services.query_response_service.update_agenda_item_conversational",
            return_value={
                "updated": True,
                "agenda_item_id": 14,
                "title": "dentista",
                "scheduled_date": date(2026, 3, 21),
                "scheduled_time": time(15, 0),
                "kind": "event",
                "note": None,
            },
        ):
            response = build_response_from_query(parsed, user_query="pasa eso para manana", conversation_context=context)

        self.assertIn("dentista", response.lower())
        self.assertIn("2026-03-21", response)

    def test_agenda_target_ambiguity_does_not_mutate(self):
        parsed = parse_user_query("cancela el recordatorio de revisar indicadores")
        items = [
            make_agenda_item(15, "revisar indicadores", date(2026, 3, 21), kind="reminder"),
            make_agenda_item(16, "revisar indicadores", date(2026, 3, 22), kind="reminder"),
        ]

        with patch("app.services.query_response_service.get_all_agenda_items", return_value=items), patch(
            "app.services.query_response_service.delete_agenda_item_conversational"
        ) as delete_mock:
            response = build_response_from_query(parsed, user_query="cancela el recordatorio de revisar indicadores")

        delete_mock.assert_not_called()
        self.assertIn("mas de un item posible", response.lower())


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date, datetime, time
from unittest.mock import patch

from app.services.conversation_runtime_service import process_conversation_turn
from app.services.query_response_service import build_response_from_query
from app.services.query_parser_service import parse_user_query
from tests.helpers import make_agenda_item


class AgendaBehaviorTests(unittest.TestCase):
    def test_runtime_prefers_rules_when_llm_drops_agenda_title(self):
        llm_result = {
            "intent": "create_agenda_item",
            "agenda_kind": "event",
            "agenda_date_hint": "manana",
            "agenda_time_hint": "10:00",
            "agenda_title": None,
            "_parser_source": "llm",
        }

        with patch("app.services.hybrid_parser_service.parse_actions_with_llm", return_value=[llm_result]), patch(
            "app.services.query_response_service.create_agenda_item_conversational",
            return_value={
                "created": True,
                "agenda_item_id": 99,
                "title": "reunion con cam",
                "scheduled_date": date.today().fromordinal(date.today().toordinal() + 1),
                "scheduled_time": time(10, 0),
                "kind": "event",
                "note": None,
            },
        ) as create_mock:
            result = process_conversation_turn("Agenda una reunion con CAM para manana a las 10:00", conversation_context={})

        self.assertEqual(result["parsed_query"]["_parser_source"], "rules")
        self.assertEqual(result["parsed_query"]["agenda_title"], "reunion con cam")
        self.assertIn("guarde el evento", result["response_text"].lower())
        self.assertNotIn("contenido", result["response_text"].lower())
        self.assertEqual(create_mock.call_args.args[0], "reunion con cam")

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

    def test_create_event_with_accented_manana_resolves_without_clarification(self):
        parsed = {
            "intent": "create_agenda_item",
            "agenda_kind": "event",
            "agenda_date_hint": "mañana",
            "agenda_time_hint": "17:00",
            "agenda_title": "reunion con cam",
        }

        with patch(
            "app.services.query_response_service.create_agenda_item_conversational",
            return_value={
                "created": True,
                "agenda_item_id": 11,
                "title": "reunion con cam",
                "scheduled_date": date.today().fromordinal(date.today().toordinal() + 1),
                "scheduled_time": time(17, 0),
                "kind": "event",
                "note": None,
            },
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="Agendá reunión con CAM mañana 17:00")

        self.assertIn("guarde el evento", response.lower())
        self.assertNotIn("fecha clara", response.lower())
        self.assertEqual(create_mock.call_args.kwargs["scheduled_date"], date.today().fromordinal(date.today().toordinal() + 1))

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

    def test_create_event_uses_content_when_agenda_title_is_missing(self):
        parsed = {
            "intent": "create_agenda_item",
            "agenda_kind": "event",
            "agenda_date_hint": "dentro de una semana",
            "agenda_time_hint": "17:00",
            "agenda_title": None,
            "content": "reunion con alimentos",
        }

        with patch(
            "app.services.query_response_service.create_agenda_item_conversational",
            return_value={
                "created": True,
                "agenda_item_id": 12,
                "title": "reunion con alimentos",
                "scheduled_date": date.today().fromordinal(date.today().toordinal() + 7),
                "scheduled_time": time(17, 0),
                "kind": "event",
                "note": None,
            },
        ) as create_mock:
            response = build_response_from_query(
                parsed,
                user_query="agendá una reunion con alimentos para dentro de una semana a las 17:00",
            )

        self.assertIn("guarde el evento", response.lower())
        self.assertNotIn("contenido", response.lower())
        self.assertEqual(create_mock.call_args.args[0], "reunion con alimentos")

    def test_create_event_for_relative_week(self):
        parsed = parse_user_query("agendá una reunion con alimentos para dentro de una semana a las 17:00")

        with patch(
            "app.services.query_response_service.create_agenda_item_conversational",
            return_value={
                "created": True,
                "agenda_item_id": 13,
                "title": "reunion con alimentos",
                "scheduled_date": date(2026, 3, 30),
                "scheduled_time": time(17, 0),
                "kind": "event",
                "note": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "relative_weeks",
                "target_date": date(2026, 3, 30),
                "start_date": date(2026, 3, 30),
                "end_date": date(2026, 3, 30),
                "label": "dentro de una semana",
                "error": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_time_hint",
            return_value={
                "resolved": True,
                "scheduled_time": time(17, 0),
                "label": "17:00",
                "error": None,
            },
        ):
            response = build_response_from_query(
                parsed,
                user_query="agendá una reunion con alimentos para dentro de una semana a las 17:00",
            )

        self.assertIn("guarde el evento", response.lower())
        self.assertIn("17:00", response)

    def test_create_reminder_for_two_weeks(self):
        parsed = parse_user_query("recordame dentro de dos semanas revisar indicadores")

        with patch(
            "app.services.query_response_service.create_agenda_item_conversational",
            return_value={
                "created": True,
                "agenda_item_id": 14,
                "title": "revisar indicadores",
                "scheduled_date": date(2026, 4, 2),
                "scheduled_time": None,
                "kind": "reminder",
                "note": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "relative_weeks",
                "target_date": date(2026, 4, 2),
                "start_date": date(2026, 4, 2),
                "end_date": date(2026, 4, 2),
                "label": "dentro de dos semanas",
                "error": None,
            },
        ):
            response = build_response_from_query(parsed, user_query="recordame dentro de dos semanas revisar indicadores")

        self.assertIn("recordatorio", response.lower())

    def test_create_event_for_relative_days(self):
        parsed = parse_user_query("agendá una llamada con Cam en 10 dias a las 11")

        with patch(
            "app.services.query_response_service.create_agenda_item_conversational",
            return_value={
                "created": True,
                "agenda_item_id": 15,
                "title": "llamada con cam",
                "scheduled_date": date(2026, 4, 1),
                "scheduled_time": time(11, 0),
                "kind": "event",
                "note": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "relative_days",
                "target_date": date(2026, 4, 1),
                "start_date": date(2026, 4, 1),
                "end_date": date(2026, 4, 1),
                "label": "en 10 dias",
                "error": None,
            },
        ), patch(
            "app.services.query_response_service.resolve_agenda_time_hint",
            return_value={
                "resolved": True,
                "scheduled_time": time(11, 0),
                "label": "11:00",
                "error": None,
            },
        ):
            response = build_response_from_query(parsed, user_query="agendá una llamada con Cam en 10 dias a las 11")

        self.assertIn("11:00", response)

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

    def test_query_next_days_agenda(self):
        parsed = parse_user_query("que tengo en los proximos dias")
        items = [
            make_agenda_item(16, "llamada con cam", date(2026, 3, 24), scheduled_time=time(11, 0)),
            make_agenda_item(17, "dentista", date(2026, 3, 25), scheduled_time=time(18, 0)),
        ]

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "next_days",
                "target_date": None,
                "start_date": date(2026, 3, 24),
                "end_date": date(2026, 3, 30),
                "label": "los proximos dias",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_between_dates", return_value=items):
            response = build_response_from_query(parsed, user_query="que tengo en los proximos dias")

        self.assertIn("proximos dias", response.lower())
        self.assertIn("llamada con cam", response.lower())

    def test_query_next_week_agenda(self):
        parsed = parse_user_query("que tengo la semana que viene")
        items = [make_agenda_item(18, "reunion de planning", date(2026, 3, 30), scheduled_time=time(17, 0))]

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "next_week",
                "target_date": None,
                "start_date": date(2026, 3, 30),
                "end_date": date(2026, 4, 5),
                "label": "la semana que viene",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_between_dates", return_value=items):
            response = build_response_from_query(parsed, user_query="que tengo la semana que viene")

        self.assertIn("semana que viene", response.lower())
        self.assertIn("reunion de planning", response.lower())

    def test_query_two_weeks_target_agenda(self):
        parsed = parse_user_query("que tengo dentro de dos semanas")
        items = [make_agenda_item(19, "seguimiento", date(2026, 4, 2), scheduled_time=time(15, 0))]

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "relative_weeks",
                "target_date": date(2026, 4, 2),
                "start_date": date(2026, 4, 2),
                "end_date": date(2026, 4, 2),
                "label": "dentro de dos semanas",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_for_date", return_value=items):
            response = build_response_from_query(parsed, user_query="que tengo dentro de dos semanas")

        self.assertIn("dentro de dos semanas", response.lower())
        self.assertIn("seguimiento", response.lower())

    def test_query_future_horizon_agenda(self):
        parsed = parse_user_query("que se viene")
        items = [make_agenda_item(20, "reunion trimestral", date(2026, 4, 15), scheduled_time=time(9, 0))]

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "future_horizon",
                "target_date": None,
                "start_date": date(2026, 3, 24),
                "end_date": date(2026, 4, 22),
                "label": "mas adelante",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_between_dates", return_value=items):
            response = build_response_from_query(parsed, user_query="que se viene")

        self.assertIn("mas adelante", response.lower())
        self.assertIn("reunion trimestral", response.lower())

    def test_create_event_for_next_week_requires_concrete_day(self):
        parsed = parse_user_query("agendá una reunion para la semana que viene")
        response = build_response_from_query(parsed, user_query="agendá una reunion para la semana que viene")

        self.assertIn("dia concreto", response.lower())

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

    def test_agenda_list_then_show_first_uses_recent_candidates(self):
        listed_items = [
            make_agenda_item(21, "reunion con cam", date(2026, 3, 20), scheduled_time=time(10, 0)),
            make_agenda_item(22, "dentista", date(2026, 3, 20), scheduled_time=time(18, 0)),
        ]
        first_turn = parse_user_query("que tengo para hoy")

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
        ), patch("app.services.query_response_service.get_agenda_items_for_date", return_value=listed_items):
            build_response_from_query(first_turn, user_query="que tengo para hoy")

        second_turn = parse_user_query("mostrame la primera")
        response = build_response_from_query(
            second_turn,
            user_query="mostrame la primera",
            conversation_context=first_turn["_conversation_context"],
        )

        self.assertIn("reunion con cam", response.lower())
        self.assertEqual(second_turn["_conversation_context"]["agenda_context"]["agenda_item_id"], 21)

    def test_agenda_list_then_delete_first_uses_recent_candidates(self):
        listed_items = [
            make_agenda_item(31, "reunion con cam", date(2026, 3, 20), scheduled_time=time(10, 0)),
            make_agenda_item(32, "dentista", date(2026, 3, 20), scheduled_time=time(18, 0)),
        ]
        first_turn = parse_user_query("que tengo para hoy")

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
        ), patch("app.services.query_response_service.get_agenda_items_for_date", return_value=listed_items):
            build_response_from_query(first_turn, user_query="que tengo para hoy")

        second_turn = parse_user_query("borra la primera")
        with patch(
            "app.services.query_response_service.delete_agenda_item_conversational",
            return_value={"deleted": True, "agenda_item_id": 31, "title": "reunion con cam"},
        ) as delete_mock:
            response = build_response_from_query(
                second_turn,
                user_query="borra la primera",
                conversation_context=first_turn["_conversation_context"],
            )

        delete_mock.assert_called_once_with(31)
        self.assertIn("borre 'reunion con cam'", response.lower())

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

import unittest
from datetime import date, time, timedelta
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from tests.helpers import make_agenda_item, make_client, make_project, make_task


class FuturePlanningBehaviorTests(unittest.TestCase):
    def test_next_days_combines_agenda_and_tasks_in_order(self):
        today_value = date.today()
        tomorrow = today_value + timedelta(days=1)
        in_three_days = today_value + timedelta(days=3)
        client = make_client(1, "Cam")
        project = make_project(10, "Automatizacion", client)
        agenda_items = [
            make_agenda_item(1, "reunion con cam", tomorrow, scheduled_time=time(10, 0)),
            make_agenda_item(2, "dentista", in_three_days, scheduled_time=time(16, 0)),
        ]
        tasks = [
            make_task(20, "revisar indicadores", project, due_date=tomorrow),
        ]
        parsed = parse_user_query("que tengo en los proximos dias")

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "next_days",
                "target_date": None,
                "start_date": tomorrow,
                "end_date": today_value + timedelta(days=7),
                "label": "los proximos dias",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_between_dates", return_value=agenda_items), patch(
            "app.services.query_response_service.get_tasks_due_between_dates",
            return_value=tasks,
        ):
            response = build_response_from_query(parsed, user_query="que tengo en los proximos dias")

        self.assertIn("Esto se viene en los proximos dias", response)
        self.assertIn("reunion con cam", response.lower())
        self.assertIn("revisar indicadores", response.lower())
        self.assertIn("dentista", response.lower())
        self.assertLess(response.index("reunion con cam"), response.index("revisar indicadores"))
        self.assertLess(response.index("revisar indicadores"), response.index("dentista"))

    def test_next_days_can_render_only_agenda(self):
        today_value = date.today()
        tomorrow = today_value + timedelta(days=1)
        agenda_items = [make_agenda_item(3, "llamada con alimentos", tomorrow, scheduled_time=time(11, 0))]
        parsed = parse_user_query("que tengo en los proximos dias")

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "next_days",
                "target_date": None,
                "start_date": tomorrow,
                "end_date": today_value + timedelta(days=7),
                "label": "los proximos dias",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_between_dates", return_value=agenda_items), patch(
            "app.services.query_response_service.get_tasks_due_between_dates",
            return_value=[],
        ):
            response = build_response_from_query(parsed, user_query="que tengo en los proximos dias")

        self.assertIn("llamada con alimentos", response.lower())
        self.assertNotIn(" | Tarea | ", response)

    def test_next_days_can_render_only_tasks(self):
        today_value = date.today()
        tomorrow = today_value + timedelta(days=1)
        client = make_client(2, "Alimentos")
        project = make_project(20, "Inbox", client)
        tasks = [make_task(30, "follow-up cliente alimentos", project, due_date=tomorrow)]
        parsed = parse_user_query("que tengo en los proximos dias")

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "next_days",
                "target_date": None,
                "start_date": tomorrow,
                "end_date": today_value + timedelta(days=7),
                "label": "los proximos dias",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_between_dates", return_value=[]), patch(
            "app.services.query_response_service.get_tasks_due_between_dates",
            return_value=tasks,
        ):
            response = build_response_from_query(parsed, user_query="que tengo en los proximos dias")

        self.assertIn("follow-up cliente alimentos", response.lower())
        self.assertIn("Tarea", response)

    def test_future_horizon_splits_near_and_later_sections(self):
        today_value = date.today()
        agenda_items = [
            make_agenda_item(4, "reunion con cam", today_value + timedelta(days=2), scheduled_time=time(10, 0)),
            make_agenda_item(5, "reunion con alimentos", today_value + timedelta(days=12), scheduled_time=time(17, 0)),
        ]
        parsed = parse_user_query("que se viene")

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "future_horizon",
                "target_date": None,
                "start_date": today_value + timedelta(days=1),
                "end_date": today_value + timedelta(days=30),
                "label": "mas adelante",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_between_dates", return_value=agenda_items), patch(
            "app.services.query_response_service.get_tasks_due_between_dates",
            return_value=[],
        ):
            response = build_response_from_query(parsed, user_query="que se viene")

        self.assertIn("Proximos dias:", response)
        self.assertIn("Mas adelante:", response)
        self.assertIn("reunion con cam", response.lower())
        self.assertIn("reunion con alimentos", response.lower())

    def test_empty_future_planning_is_clear(self):
        today_value = date.today()
        parsed = parse_user_query("que se viene")

        with patch(
            "app.services.query_response_service.resolve_agenda_date_hint",
            return_value={
                "resolved": True,
                "scope": "future_horizon",
                "target_date": None,
                "start_date": today_value + timedelta(days=1),
                "end_date": today_value + timedelta(days=30),
                "label": "mas adelante",
                "error": None,
            },
        ), patch("app.services.query_response_service.get_agenda_items_between_dates", return_value=[]), patch(
            "app.services.query_response_service.get_tasks_due_between_dates",
            return_value=[],
        ):
            response = build_response_from_query(parsed, user_query="que se viene")

        self.assertEqual(response, "No tenes compromisos proximos.")


if __name__ == "__main__":
    unittest.main()

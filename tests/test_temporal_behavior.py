import unittest
from datetime import date, datetime
from unittest.mock import patch

from app.services.query_parser_service import parse_user_query
from app.services.query_response_service import build_response_from_query
from app.services.task_service import (
    build_missing_due_date_snapshot_from_tasks,
    build_temporal_task_snapshot_from_tasks,
)
from tests.helpers import make_client, make_project, make_task


class TemporalBehaviorTests(unittest.TestCase):
    def test_create_task_for_tomorrow(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        create_result = {
            "created": True,
            "task_id": 301,
            "task_title": "revisar indicadores",
            "project_id": project.id,
            "priority": "media",
            "next_action": None,
            "last_note": None,
        }
        parsed = parse_user_query("crea una tarea para revisar indicadores para manana")

        with patch("app.services.query_response_service.get_all_projects", return_value=[project]), patch(
            "app.services.query_response_service.resolve_due_hint",
            return_value={
                "resolved": True,
                "time_scope": "tomorrow",
                "due_date": date(2026, 3, 20),
                "label": "mañana",
                "degraded": False,
                "reason": None,
            },
        ), patch(
            "app.services.query_response_service.create_task_conversational",
            return_value=create_result,
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="crea una tarea para revisar indicadores para manana", conversation_context={})

        create_mock.assert_called_once_with(
            project.id,
            "revisar indicadores",
            priority="media",
            due_date=date(2026, 3, 20),
            next_action=None,
            last_note=None,
        )
        self.assertIn("2026-03-20", response)

    def test_create_task_for_today(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        create_result = {
            "created": True,
            "task_id": 302,
            "task_title": "revisar backlog",
            "project_id": project.id,
            "priority": "alta",
            "next_action": None,
            "last_note": None,
        }
        parsed = parse_user_query("agrega una tarea urgente para revisar backlog para hoy")

        with patch("app.services.query_response_service.get_all_projects", return_value=[project]), patch(
            "app.services.query_response_service.resolve_due_hint",
            return_value={
                "resolved": True,
                "time_scope": "today",
                "due_date": date(2026, 3, 19),
                "label": "hoy",
                "degraded": False,
                "reason": None,
            },
        ), patch(
            "app.services.query_response_service.create_task_conversational",
            return_value=create_result,
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="agrega una tarea urgente para revisar backlog para hoy", conversation_context={})

        create_mock.assert_called_once_with(
            project.id,
            "revisar backlog",
            priority="alta",
            due_date=date(2026, 3, 19),
            next_action=None,
            last_note=None,
        )
        self.assertIn("prioridad: alta", response.lower())

    def test_create_followup_for_friday(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        create_result = {
            "created": True,
            "task_id": 303,
            "task_title": "Follow-up",
            "project_id": project.id,
            "priority": "media",
            "next_action": None,
            "last_note": None,
        }
        parsed = parse_user_query("deja follow-up para el viernes")

        with patch("app.services.query_response_service.get_all_projects", return_value=[project]), patch(
            "app.services.query_response_service.resolve_due_hint",
            return_value={
                "resolved": True,
                "time_scope": "weekday",
                "due_date": date(2026, 3, 20),
                "label": "viernes",
                "degraded": False,
                "reason": None,
            },
        ), patch(
            "app.services.query_response_service.create_task_conversational",
            return_value=create_result,
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="deja follow-up para el viernes", conversation_context={})

        create_mock.assert_called_once_with(
            project.id,
            "Follow-up",
            priority="media",
            due_date=date(2026, 3, 20),
            next_action=None,
            last_note=None,
        )
        self.assertIn("follow-up", response.lower())

    def test_due_today_snapshot(self):
        today = date(2026, 3, 19)
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        due_today = make_task(1, "Enviar reporte", project, due_date=today, priority="alta")
        due_tomorrow = make_task(2, "Preparar demo", project, due_date=date(2026, 3, 20))
        snapshot = build_temporal_task_snapshot_from_tasks([due_today, due_tomorrow], time_scope="today", today=today)

        self.assertEqual(len(snapshot["matched_items"]), 1)
        self.assertEqual(snapshot["matched_items"][0]["title"], "Enviar reporte")

    def test_overdue_query_returns_overdue_work(self):
        snapshot = {
            "today": "2026-03-19",
            "time_scope": "overdue",
            "temporal_focus": None,
            "matched_items": [
                {
                    "title": "Cerrar pendientes",
                    "due_date": "2026-03-18",
                    "client_name": "CAM",
                    "project_name": "Dashboard",
                    "is_blocked": False,
                    "has_next_action": False,
                }
            ],
            "missing_due_items": [],
            "degraded": False,
        }
        parsed = parse_user_query("que tengo atrasado")

        with patch("app.services.query_response_service.get_temporal_task_snapshot", return_value=snapshot):
            response = build_response_from_query(parsed, user_query="que tengo atrasado", conversation_context={})

        self.assertIn("cerrar pendientes", response.lower())
        self.assertIn("2026-03-18", response)

    def test_tomorrow_query_returns_due_tomorrow(self):
        today = date(2026, 3, 19)
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        due_tomorrow = make_task(1, "Llamar cliente", project, due_date=date(2026, 3, 20), next_action="confirmar horario")
        snapshot = build_temporal_task_snapshot_from_tasks([due_tomorrow], time_scope="tomorrow", today=today)

        self.assertEqual(snapshot["matched_items"][0]["title"], "Llamar cliente")

    def test_missing_due_date_snapshot(self):
        today = date(2026, 3, 19)
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        missing_due = make_task(1, "Definir alcance", project, priority="alta", next_action="pedir validacion")
        no_signal = make_task(2, "Leer idea", project, priority="baja")
        snapshot = build_missing_due_date_snapshot_from_tasks([missing_due, no_signal], today=today)

        self.assertEqual(len(snapshot["missing_due_items"]), 1)
        self.assertEqual(snapshot["missing_due_items"][0]["title"], "Definir alcance")

    def test_ambiguous_temporal_creation_degrades_safely(self):
        client = make_client(1, "CAM")
        project = make_project(10, "Dashboard", client)
        parsed = parse_user_query("crea una tarea para revisar indicadores para pronto")

        with patch("app.services.query_response_service.get_all_projects", return_value=[project]), patch(
            "app.services.query_response_service.create_task_conversational",
        ) as create_mock:
            response = build_response_from_query(parsed, user_query="crea una tarea para revisar indicadores para pronto", conversation_context={})

        create_mock.assert_not_called()
        self.assertIn("referencia temporal", response.lower())

    def test_without_support_does_not_invent_temporal_logic(self):
        parsed = {"intent": "get_due_tasks_summary", "time_scope": "this_week", "temporal_focus": "followups"}
        snapshot = {
            "today": "2026-03-19",
            "time_scope": "this_week",
            "temporal_focus": "followups",
            "matched_items": [],
            "missing_due_items": [],
            "degraded": False,
        }
        with patch("app.services.query_response_service.get_temporal_task_snapshot", return_value=snapshot):
            response = build_response_from_query(parsed, user_query="que follow-ups vencen esta semana", conversation_context={})

        self.assertIn("no veo tareas abiertas", response.lower())


if __name__ == "__main__":
    unittest.main()

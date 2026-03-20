import unittest
from unittest.mock import patch

from app.channels.telegram.adapter import (
    TelegramChannelAdapter,
    build_telegram_conversation_key,
    extract_telegram_message,
    get_telegram_bot_token,
)
from app.channels.telegram.context_store import InMemoryTelegramContextStore
from tests.helpers import make_client, make_project, make_task


class TelegramChannelTests(unittest.TestCase):
    def test_help_command_does_not_go_through_core_runtime(self):
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )

        with patch("app.channels.telegram.adapter.process_conversation_turn") as runtime_mock:
            result = adapter.handle_incoming_text(chat_id="chat-help", text="/help")

        runtime_mock.assert_not_called()
        self.assertEqual(result["parsed_query"]["intent"], "telegram_channel_command")
        self.assertEqual(result["channel_command"], "/help")
        self.assertIn("/reset", result["response_text"])

    def test_reset_command_clears_only_current_chat_context(self):
        store = InMemoryTelegramContextStore()
        adapter = TelegramChannelAdapter(
            context_store=store,
            persist_log=False,
        )
        key_a = build_telegram_conversation_key(chat_id="chat-a", chat_type="private", user_id="11")
        key_b = build_telegram_conversation_key(chat_id="chat-b", chat_type="private", user_id="22")
        store.save_context(key_a, {"_isolated": True, "scope": "client", "client": {"id": 1, "name": "Cam"}})
        store.save_context(key_b, {"_isolated": True, "scope": "client", "client": {"id": 2, "name": "Dallas"}})

        result = adapter.handle_incoming_text(chat_id="chat-a", user_id="11", chat_type="private", text="/reset")

        self.assertIn("limpie el contexto", result["response_text"].lower())
        self.assertEqual(store.get_context(key_a), {})
        self.assertEqual(store.get_context(key_b).get("client", {}).get("name"), "Dallas")

    def test_chat_a_does_not_contaminate_chat_b_context(self):
        cam = make_client(1, "Cam")
        dallas = make_client(2, "Dallas")
        cam_project = make_project(10, "Dashboard comercial", cam)
        dallas_project = make_project(20, "CRM Dallas", dallas)
        cam_task = make_task(100, "Definir metricas", cam_project, priority="alta", next_action="Confirmar KPI")
        dallas_task = make_task(200, "Ordenar backlog", dallas_project)
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )

        with patch("app.services.reference_resolver.get_all_clients", return_value=[cam, dallas]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            side_effect=lambda client_id: [cam_project] if client_id == cam.id else [dallas_project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            side_effect=lambda client_id: [cam_task] if client_id == cam.id else [dallas_task],
        ):
            first = adapter.handle_incoming_text(chat_id="chat-a", text="comentame en que andamos con Cam")
            second = adapter.handle_incoming_text(chat_id="chat-b", text="que me preocuparia")

        self.assertEqual(first["conversation_context"].get("client", {}).get("name"), "Cam")
        self.assertIn("contexto aislado actual", second["response_text"].lower())
        self.assertNotIn("client", second["conversation_context"])

    def test_same_chat_keeps_multi_turn_continuity(self):
        cam = make_client(1, "Cam")
        project = make_project(10, "Dashboard comercial", cam)
        task = make_task(100, "Definir metricas", project, status="bloqueada", priority="alta", next_action="Confirmar KPI")
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )

        with patch("app.services.reference_resolver.get_all_clients", return_value=[cam]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=[task],
        ):
            first = adapter.handle_incoming_text(chat_id="chat-cam", text="comentame en que andamos con Cam")
            second = adapter.handle_incoming_text(chat_id="chat-cam", text="que me preocuparia")

        self.assertEqual(first["conversation_context"].get("client", {}).get("name"), "Cam")
        self.assertTrue(second["parsed_query"].get("_continuity_used_context", False))
        self.assertIn("cam", second["response_text"].lower())

    def test_adapter_uses_shared_core_runtime(self):
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )
        mocked_result = {
            "response_text": "respuesta telegram",
            "parsed_query": {"intent": "get_operational_summary"},
            "conversation_context": {"_isolated": True, "scope": "client"},
            "audit_trace": {"action_status": "informational"},
            "resolved_references": {},
        }

        with patch("app.channels.telegram.adapter.process_conversation_turn", return_value=mocked_result) as runtime_mock:
            result = adapter.handle_incoming_text(chat_id="telegram-1", text="hola")

        runtime_mock.assert_called_once_with(
            "hola",
            conversation_context={},
            persist_log=False,
        )
        self.assertEqual(result["response_text"], "respuesta telegram")

    def test_adapter_normalizes_polite_telegram_prefixes_before_using_core(self):
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )
        mocked_result = {
            "response_text": "ok",
            "parsed_query": {"intent": "create_task"},
            "conversation_context": {"_isolated": True, "scope": "project"},
            "audit_trace": {"action_status": "executed"},
            "resolved_references": {},
        }

        with patch("app.channels.telegram.adapter.process_conversation_turn", return_value=mocked_result) as runtime_mock:
            result = adapter.handle_incoming_text(
                chat_id="telegram-2",
                text="Gracias. Agregame una tarea a cam: hacer revision anual",
            )

        runtime_mock.assert_called_once_with(
            "Agregame una tarea a cam: hacer revision anual",
            conversation_context={},
            persist_log=False,
        )
        self.assertEqual(result["normalized_input_text"], "Agregame una tarea a cam: hacer revision anual")

    def test_status_command_shows_identity_and_conversation_key(self):
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )
        conversation_key = build_telegram_conversation_key(
            chat_id="999",
            chat_type="supergroup",
            user_id="123",
            message_thread_id="77",
        )
        adapter.context_store.save_context(
            conversation_key,
            {"_isolated": True, "scope": "agenda", "agenda_context": {"title": "reunion con cam"}},
        )

        result = adapter.handle_incoming_text(
            chat_id="999",
            user_id="123",
            chat_type="supergroup",
            message_thread_id="77",
            text="/status",
        )

        self.assertEqual(result["channel_command"], "/status")
        self.assertIn("conversation_key", result["response_text"])
        self.assertIn("message_thread_id: 77", result["response_text"])
        self.assertIn(conversation_key, result["response_text"])

    def test_adapter_supports_personal_agenda_creation(self):
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )
        mocked_result = {
            "response_text": "Listo: guarde el recordatorio 'revisar indicadores'. Fecha: 2026-03-21.",
            "parsed_query": {"intent": "create_agenda_item"},
            "conversation_context": {"_isolated": True, "scope": "agenda", "agenda_context": {"anchor_date": "2026-03-21"}},
            "audit_trace": {"action_status": "executed", "action_type": "agenda_reminder"},
            "resolved_references": {},
        }

        with patch("app.channels.telegram.adapter.process_conversation_turn", return_value=mocked_result) as runtime_mock:
            result = adapter.handle_incoming_text(
                chat_id="telegram-agenda",
                text="Recordame manana revisar indicadores",
            )

        runtime_mock.assert_called_once_with(
            "Recordame manana revisar indicadores",
            conversation_context={},
            persist_log=False,
        )
        self.assertEqual(result["parsed_query"]["intent"], "create_agenda_item")
        self.assertEqual(result["conversation_context"]["scope"], "agenda")
        self.assertIn("recordatorio", result["response_text"].lower())

    def test_without_previous_context_starts_clean(self):
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )

        response = adapter.handle_incoming_text(chat_id="chat-new", text="que me preocuparia")

        self.assertIn("contexto aislado actual", response["response_text"].lower())
        self.assertEqual(response["conversation_context"].get("scope"), "none")

    def test_missing_token_fails_clearly(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TELEGRAM_BOT_TOKEN"):
                get_telegram_bot_token(required=True)

    def test_handle_update_returns_response_and_updated_context(self):
        cam = make_client(1, "Cam")
        project = make_project(10, "Dashboard comercial", cam)
        task = make_task(100, "Definir metricas", project, next_action="Confirmar KPI")
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )
        update = {
            "update_id": 9001,
            "message": {
                "message_id": 77,
                "chat": {"id": 12345, "type": "private"},
                "from": {"id": 987},
                "text": "comentame en que andamos con Cam",
            },
        }

        with patch("app.services.reference_resolver.get_all_clients", return_value=[cam]), patch(
            "app.services.query_response_service.get_projects_by_client_id",
            return_value=[project],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=[task],
        ):
            result = adapter.handle_update(update)

        self.assertEqual(result["chat_id"], "12345")
        self.assertEqual(result["message_id"], 77)
        self.assertEqual(result["update_id"], 9001)
        self.assertEqual(result["user_id"], "987")
        self.assertTrue(result["response_text"])
        self.assertTrue(result["conversation_context"].get("_isolated"))
        self.assertTrue(result["audit_trace"])
        self.assertEqual(result["send_message_payload"]["chat_id"], "12345")

    def test_extract_telegram_message_includes_identity_and_thread(self):
        payload = extract_telegram_message(
            {
                "update_id": 12,
                "message": {
                    "message_id": 55,
                    "chat": {"id": -1001, "type": "supergroup"},
                    "from": {"id": 42, "username": "rami"},
                    "message_thread_id": 9,
                    "text": "hola",
                },
            }
        )

        self.assertEqual(payload["chat_id"], "-1001")
        self.assertEqual(payload["user_id"], "42")
        self.assertEqual(payload["message_thread_id"], "9")
        self.assertIn("thread:9", payload["conversation_key"])

    def test_extract_telegram_message_rejects_missing_text(self):
        with self.assertRaisesRegex(ValueError, "texto util"):
            extract_telegram_message({"message": {"chat": {"id": 1}}})


if __name__ == "__main__":
    unittest.main()

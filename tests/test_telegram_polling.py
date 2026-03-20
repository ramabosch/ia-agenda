import unittest
from unittest.mock import Mock, patch

import requests

from app.channels.telegram import TelegramChannelAdapter
from app.channels.telegram.context_store import InMemoryTelegramContextStore
from app.channels.telegram.polling import (
    parse_allowed_chat_ids,
    parse_allowed_user_ids,
    process_telegram_update,
    run_polling_loop,
    telegram_api_request,
)


class _FakeResponse:
    def __init__(self, payload, *, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, *, get_payloads=None, post_payloads=None):
        self.get_payloads = list(get_payloads or [])
        self.post_payloads = list(post_payloads or [{"ok": True, "result": {"message_id": 1}}])
        self.get_calls = []
        self.post_calls = []

    def get(self, url, params=None, timeout=None):
        self.get_calls.append({"url": url, "params": params, "timeout": timeout})
        payload = self.get_payloads.pop(0) if self.get_payloads else {"ok": True, "result": []}
        return _FakeResponse(payload)

    def post(self, url, data=None, timeout=None):
        self.post_calls.append({"url": url, "data": data, "timeout": timeout})
        payload = self.post_payloads.pop(0) if self.post_payloads else {"ok": True, "result": {"message_id": 1}}
        return _FakeResponse(payload)


class TelegramPollingTests(unittest.TestCase):
    def test_parse_allowed_chat_ids(self):
        allowed = parse_allowed_chat_ids("12345, 999 \n777;888")
        self.assertEqual(allowed, {"12345", "999", "777", "888"})

    def test_parse_allowed_user_ids(self):
        allowed = parse_allowed_user_ids("11, 22 \n33;44")
        self.assertEqual(allowed, {"11", "22", "33", "44"})

    def test_whitelist_filters_unauthorized_chat(self):
        session = _FakeSession()
        adapter = Mock()
        logs = []
        update = {
            "update_id": 1,
            "message": {"message_id": 10, "chat": {"id": 555}, "from": {"id": 111}, "text": "hola"},
        }

        result = process_telegram_update(
            update,
            adapter=adapter,
            session=session,
            token="dummy-token",
            allowed_chat_ids={"999"},
            logger=logs.append,
        )

        self.assertEqual(result["status"], "ignored_whitelist")
        adapter.handle_update.assert_not_called()
        self.assertEqual(session.post_calls, [])
        self.assertTrue(any("ignorado por whitelist" in line for line in logs))

    def test_whitelist_filters_unauthorized_user(self):
        session = _FakeSession()
        adapter = Mock()
        logs = []
        update = {
            "update_id": 9,
            "message": {"message_id": 10, "chat": {"id": 555, "type": "private"}, "from": {"id": 222}, "text": "hola"},
        }

        result = process_telegram_update(
            update,
            adapter=adapter,
            session=session,
            token="dummy-token",
            allowed_user_ids={"111"},
            logger=logs.append,
        )

        self.assertEqual(result["status"], "ignored_whitelist")
        adapter.handle_update.assert_not_called()
        self.assertTrue(any("user 222" in line for line in logs))

    def test_update_without_text_is_ignored_safely(self):
        session = _FakeSession()
        adapter = Mock()
        logs = []
        update = {"update_id": 2, "message": {"chat": {"id": 555}}}

        result = process_telegram_update(
            update,
            adapter=adapter,
            session=session,
            token="dummy-token",
            logger=logs.append,
        )

        self.assertEqual(result["status"], "ignored_non_text")
        adapter.handle_update.assert_not_called()
        self.assertEqual(session.post_calls, [])
        self.assertTrue(any("ignorado" in line for line in logs))

    def test_missing_token_error_is_clear(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TELEGRAM_BOT_TOKEN"):
                run_polling_loop(
                    adapter=Mock(),
                    session=_FakeSession(),
                    logger=None,
                    max_cycles=1,
                )

    def test_polling_loop_uses_current_adapter(self):
        adapter = Mock()
        adapter.handle_update.return_value = {
            "send_message_payload": {"chat_id": "123", "text": "respuesta"},
            "parsed_query": {"intent": "get_operational_summary"},
            "audit_trace": {"action_status": "informational"},
        }
        session = _FakeSession(
            get_payloads=[
                {
                    "ok": True,
                    "result": [
                        {
                            "update_id": 100,
                            "message": {"message_id": 77, "chat": {"id": 123, "type": "private"}, "from": {"id": 321}, "text": "hola"},
                        }
                    ],
                }
            ]
        )

        with patch.dict("os.environ", {}, clear=True):
            result = run_polling_loop(
                adapter=adapter,
                token="dummy-token",
                session=session,
                max_cycles=1,
                logger=None,
            )

        adapter.handle_update.assert_called_once()
        self.assertEqual(result["processed_updates"][0]["status"], "sent")
        self.assertEqual(result["last_offset"], 101)
        self.assertEqual(session.post_calls[0]["data"]["chat_id"], "123")

    def test_polling_keeps_context_isolated_between_chats(self):
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )
        session = _FakeSession(
            get_payloads=[
                {
                    "ok": True,
                    "result": [
                        {"update_id": 200, "message": {"message_id": 1, "chat": {"id": 1, "type": "private"}, "from": {"id": 1}, "text": "hola"}},
                        {"update_id": 201, "message": {"message_id": 2, "chat": {"id": 2, "type": "private"}, "from": {"id": 2}, "text": "hola"}},
                        {"update_id": 202, "message": {"message_id": 3, "chat": {"id": 1, "type": "private"}, "from": {"id": 1}, "text": "seguimos"}},
                    ],
                }
            ]
        )

        def runtime_side_effect(user_query, *, conversation_context, persist_log):
            if user_query == "hola":
                return {
                    "response_text": "ok",
                    "parsed_query": {"intent": "get_operational_summary"},
                    "conversation_context": {"_isolated": True, "scope": "client", "marker": "hola"},
                    "audit_trace": {"action_status": "informational"},
                    "resolved_references": {},
                }
            return {
                "response_text": "seguimos ok",
                "parsed_query": {"intent": "get_followup_focus_summary"},
                "conversation_context": {
                    "_isolated": True,
                    "scope": "client",
                    "marker": conversation_context.get("marker"),
                },
                "audit_trace": {"action_status": "informational"},
                "resolved_references": {},
            }

        with patch("app.channels.telegram.adapter.process_conversation_turn", side_effect=runtime_side_effect) as runtime_mock, patch.dict("os.environ", {}, clear=True):
            result = run_polling_loop(
                adapter=adapter,
                token="dummy-token",
                session=session,
                max_cycles=1,
                logger=None,
            )

        self.assertEqual(len(result["processed_updates"]), 3)
        first_context = runtime_mock.call_args_list[0].kwargs["conversation_context"]
        second_context = runtime_mock.call_args_list[1].kwargs["conversation_context"]
        third_context = runtime_mock.call_args_list[2].kwargs["conversation_context"]
        self.assertEqual(first_context, {})
        self.assertEqual(second_context, {})
        self.assertEqual(third_context.get("marker"), "hola")

    def test_polling_keeps_context_isolated_between_threads(self):
        adapter = TelegramChannelAdapter(
            context_store=InMemoryTelegramContextStore(),
            persist_log=False,
        )
        session = _FakeSession(
            get_payloads=[
                {
                    "ok": True,
                    "result": [
                        {
                            "update_id": 300,
                            "message": {
                                "message_id": 1,
                                "chat": {"id": -100, "type": "supergroup"},
                                "from": {"id": 10},
                                "message_thread_id": 7,
                                "text": "hola",
                            },
                        },
                        {
                            "update_id": 301,
                            "message": {
                                "message_id": 2,
                                "chat": {"id": -100, "type": "supergroup"},
                                "from": {"id": 10},
                                "message_thread_id": 8,
                                "text": "hola",
                            },
                        },
                        {
                            "update_id": 302,
                            "message": {
                                "message_id": 3,
                                "chat": {"id": -100, "type": "supergroup"},
                                "from": {"id": 10},
                                "message_thread_id": 7,
                                "text": "seguimos",
                            },
                        },
                    ],
                }
            ]
        )

        def runtime_side_effect(user_query, *, conversation_context, persist_log):
            return {
                "response_text": "ok",
                "parsed_query": {"intent": "get_operational_summary"},
                "conversation_context": {"_isolated": True, "scope": "client", "marker": conversation_context.get("marker", user_query)},
                "audit_trace": {"action_status": "informational"},
                "resolved_references": {},
            }

        with patch("app.channels.telegram.adapter.process_conversation_turn", side_effect=runtime_side_effect) as runtime_mock, patch.dict("os.environ", {}, clear=True):
            run_polling_loop(
                adapter=adapter,
                token="dummy-token",
                session=session,
                max_cycles=1,
                logger=None,
            )

        first_context = runtime_mock.call_args_list[0].kwargs["conversation_context"]
        second_context = runtime_mock.call_args_list[1].kwargs["conversation_context"]
        third_context = runtime_mock.call_args_list[2].kwargs["conversation_context"]
        self.assertEqual(first_context, {})
        self.assertEqual(second_context, {})
        self.assertEqual(third_context.get("marker"), "hola")

    def test_telegram_api_request_surfaces_api_error(self):
        session = _FakeSession(get_payloads=[{"ok": False, "description": "bad request"}])

        with self.assertRaisesRegex(RuntimeError, "bad request"):
            telegram_api_request(
                session,
                "dummy-token",
                "getUpdates",
                timeout_seconds=1,
            )


if __name__ == "__main__":
    unittest.main()

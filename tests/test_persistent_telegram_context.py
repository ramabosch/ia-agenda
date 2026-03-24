import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.channels.telegram.adapter import TelegramChannelAdapter, build_telegram_conversation_key
from app.channels.telegram.context_store import PersistentTelegramContextStore
from app.db.base import Base
from app.repositories.conversation_state_repository import get_conversation_state_by_key
from tests.helpers import make_client, make_project, make_task


class PersistentTelegramContextTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "telegram_context.db"
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.store = PersistentTelegramContextStore(session_factory=self.SessionLocal)

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_store_persists_context_and_recovers_after_restart(self):
        conversation_key = build_telegram_conversation_key(chat_id="777", chat_type="private", user_id="42")
        context = {
            "_isolated": True,
            "scope": "client",
            "client": {"id": 1, "name": "Cam"},
            "assistant_memory": {"debug_mode": True},
            "candidate_entities": [{"scope": "task", "id": 10, "name": "Comprar cafe"}],
        }

        self.store.save_context(
            conversation_key,
            context,
            metadata={
                "chat_id": "777",
                "user_id": "42",
                "chat_type": "private",
                "message_thread_id": None,
            },
        )

        restarted_store = PersistentTelegramContextStore(session_factory=self.SessionLocal)
        restored = restarted_store.get_context(conversation_key)

        self.assertEqual(restored.get("client", {}).get("name"), "Cam")
        self.assertTrue(restored.get("assistant_memory", {}).get("debug_mode"))
        self.assertEqual(restored.get("candidate_entities")[0]["name"], "Comprar cafe")

        db = self.SessionLocal()
        try:
            state = get_conversation_state_by_key(db, conversation_key)
            self.assertIsNotNone(state)
            self.assertEqual(state.chat_id, "777")
            self.assertEqual(state.user_id, "42")
            self.assertEqual(state.chat_type, "private")
        finally:
            db.close()

    def test_store_does_not_mix_two_conversation_keys(self):
        key_a = build_telegram_conversation_key(chat_id="chat-a", chat_type="private", user_id="11")
        key_b = build_telegram_conversation_key(chat_id="chat-b", chat_type="private", user_id="22")

        self.store.save_context(key_a, {"_isolated": True, "scope": "client", "client": {"id": 1, "name": "Cam"}})
        self.store.save_context(key_b, {"_isolated": True, "scope": "client", "client": {"id": 2, "name": "Dallas"}})

        restarted_store = PersistentTelegramContextStore(session_factory=self.SessionLocal)
        self.assertEqual(restarted_store.get_context(key_a).get("client", {}).get("name"), "Cam")
        self.assertEqual(restarted_store.get_context(key_b).get("client", {}).get("name"), "Dallas")

    def test_reset_command_clears_persisted_state_for_conversation(self):
        adapter = TelegramChannelAdapter(context_store=self.store, persist_log=False)
        conversation_key = build_telegram_conversation_key(chat_id="999", chat_type="private", user_id="55")
        self.store.save_context(
            conversation_key,
            {
                "_isolated": True,
                "scope": "client",
                "client": {"id": 1, "name": "Cam"},
                "assistant_memory": {"debug_mode": True},
            },
            metadata={"chat_id": "999", "user_id": "55", "chat_type": "private"},
        )

        adapter.handle_incoming_text(
            chat_id="999",
            user_id="55",
            chat_type="private",
            text="/reset",
            conversation_key=conversation_key,
        )

        restarted_store = PersistentTelegramContextStore(session_factory=self.SessionLocal)
        self.assertEqual(restarted_store.get_context(conversation_key), {})
        db = self.SessionLocal()
        try:
            self.assertIsNone(get_conversation_state_by_key(db, conversation_key))
        finally:
            db.close()

    def test_debug_mode_persists_across_restart(self):
        adapter = TelegramChannelAdapter(context_store=self.store, persist_log=False)
        conversation_key = build_telegram_conversation_key(chat_id="555", chat_type="private", user_id="88")

        result = adapter.handle_incoming_text(
            chat_id="555",
            user_id="88",
            chat_type="private",
            text="/debug",
            conversation_key=conversation_key,
        )

        self.assertIn("modo debug activado", result["response_text"].lower())
        restarted_store = PersistentTelegramContextStore(session_factory=self.SessionLocal)
        restored = restarted_store.get_context(conversation_key)
        self.assertTrue(restored.get("assistant_memory", {}).get("debug_mode"))

    def test_ordinal_flow_survives_store_restart(self):
        agenda_ai = make_client(9, "Agenda AI")
        inbox = make_project(30, "Inbox", agenda_ai)
        first_task = make_task(301, "Comprar cafe", inbox)
        second_task = make_task(302, "Revisar stock", inbox)

        adapter = TelegramChannelAdapter(context_store=self.store, persist_log=False)

        with patch("app.services.reference_resolver.get_all_clients", return_value=[agenda_ai]), patch(
            "app.services.query_response_service.get_open_tasks_by_client_id",
            return_value=[first_task, second_task],
        ), patch(
            "app.services.query_response_service.get_tasks_by_client_id",
            return_value=[first_task, second_task],
        ), patch(
            "app.services.reference_resolver.get_all_tasks",
            return_value=[first_task, second_task],
        ), patch(
            "app.services.query_response_service.update_task_status_conversational",
            return_value={
                "updated": True,
                "task_id": first_task.id,
                "task_title": first_task.title,
                "field": "status",
                "old_value": "pendiente",
                "new_value": "hecha",
                "task": first_task,
            },
        ):
            first = adapter.handle_incoming_text(
                chat_id="100",
                user_id="500",
                chat_type="private",
                text="decime las tareas de agenda ai",
            )

            restarted_adapter = TelegramChannelAdapter(
                context_store=PersistentTelegramContextStore(session_factory=self.SessionLocal),
                persist_log=False,
            )
            second = restarted_adapter.handle_incoming_text(
                chat_id="100",
                user_id="500",
                chat_type="private",
                text="Cerra la primera.",
            )

        self.assertEqual(len(first["conversation_context"].get("candidate_entities") or []), 2)
        self.assertIn("comprar cafe", second["response_text"].lower())
        self.assertEqual(second["conversation_context"].get("task", {}).get("name"), "Comprar cafe")


if __name__ == "__main__":
    unittest.main()

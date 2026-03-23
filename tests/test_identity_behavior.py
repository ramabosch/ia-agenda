import unittest

from app.services.query_response_service import build_response_from_query


class IdentityBehaviorTests(unittest.TestCase):
    def test_who_am_i_uses_identity_service_profile(self):
        parsed = {"intent": "unknown"}
        context = {
            "channel_identity": {
                "channel": "telegram",
                "telegram_id": 6043652463,
                "chat_id": "777",
            }
        }

        response = build_response_from_query(parsed, user_query="¿Quién soy?", conversation_context=context)

        self.assertIn("Tu Nombre", response)
        self.assertIn("Admin", response)
        self.assertIn("ART", response)

    def test_unknown_response_is_personalized_when_identity_exists(self):
        parsed = {"intent": "unknown"}
        context = {
            "channel_identity": {
                "channel": "telegram",
                "telegram_id": 6043652463,
                "chat_id": "777",
            }
        }

        response = build_response_from_query(parsed, user_query="algo re raro", conversation_context=context)

        self.assertIn("Hola Tu Nombre", response)
        self.assertIn("no entendi esa consulta", response.lower())


if __name__ == "__main__":
    unittest.main()

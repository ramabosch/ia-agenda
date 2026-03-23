from __future__ import annotations


ADMIN_TELEGRAM_ID = 6043652463


class IdentityService:
    def get_user_profile(self, telegram_id: int) -> dict:
        normalized_id = int(telegram_id)
        if normalized_id == ADMIN_TELEGRAM_ID:
            return {
                "telegram_id": normalized_id,
                "name": "Tu Nombre",
                "location": "Rosario",
                "role": "Admin",
                "timezone": "ART",
            }

        return {
            "telegram_id": normalized_id,
            "name": "Companero",
            "location": None,
            "role": "Companero",
            "timezone": None,
        }

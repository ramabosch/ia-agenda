import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.channels.telegram.adapter import TelegramChannelAdapter, get_telegram_bot_token


def main():
    parser = argparse.ArgumentParser(
        description="Simulador local del canal Telegram para Agenda AI.",
    )
    parser.add_argument(
        "--chat-id",
        default="demo-chat",
        help="Identificador del chat para aislar el contexto conversacional.",
    )
    parser.add_argument(
        "--message",
        action="append",
        required=True,
        help="Mensaje a procesar. Repetilo para simular varios turnos en el mismo chat.",
    )
    parser.add_argument(
        "--require-token",
        action="store_true",
        help="Falla claro si TELEGRAM_BOT_TOKEN no esta configurado.",
    )
    args = parser.parse_args()

    if args.require_token:
        get_telegram_bot_token(required=True)

    adapter = TelegramChannelAdapter(persist_log=False)
    turns = []

    for message in args.message:
        result = adapter.handle_incoming_text(chat_id=args.chat_id, text=message)
        parsed = result.get("parsed_query") or {}
        turns.append(
            {
                "input": message,
                "response_text": result["response_text"],
                "intent": parsed.get("intent"),
                "scope": (result.get("conversation_context") or {}).get("scope"),
                "action_status": (result.get("audit_trace") or {}).get("action_status"),
                "context_keys": sorted((result.get("conversation_context") or {}).keys()),
            }
        )

    print(
        json.dumps(
            {
                "channel": "telegram_simulator",
                "chat_id": str(args.chat_id),
                "turn_count": len(turns),
                "turns": turns,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

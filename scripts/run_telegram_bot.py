from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.channels.telegram import TelegramChannelAdapter
from app.channels.telegram.adapter import get_telegram_bot_token
from app.channels.telegram.polling import (
    parse_allowed_chat_ids,
    parse_allowed_user_ids,
    run_polling_loop,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Runner local de polling real para el bot de Telegram de Agenda AI.",
    )
    parser.add_argument(
        "--poll-timeout",
        type=int,
        default=int(os.getenv("TELEGRAM_POLL_TIMEOUT_SECONDS", "20")),
        help="Timeout largo de getUpdates en segundos.",
    )
    parser.add_argument(
        "--idle-sleep",
        type=float,
        default=float(os.getenv("TELEGRAM_IDLE_SLEEP_SECONDS", "1")),
        help="Pausa corta entre ciclos sin updates o despues de errores.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Hace un solo ciclo de polling y sale. Util para smoke local.",
    )
    args = parser.parse_args()

    token = get_telegram_bot_token(required=True)
    allowed_chat_ids = parse_allowed_chat_ids()
    allowed_user_ids = parse_allowed_user_ids()

    print("[telegram] iniciando bot en modo polling")
    print(f"[telegram] poll timeout: {args.poll_timeout}s | idle sleep: {args.idle_sleep}s")
    if allowed_chat_ids:
        print(f"[telegram] whitelist activa para chats: {', '.join(sorted(allowed_chat_ids))}")
    else:
        print("[telegram] whitelist no configurada; se aceptaran mensajes de cualquier chat")
    if allowed_user_ids:
        print(f"[telegram] whitelist activa para usuarios: {', '.join(sorted(allowed_user_ids))}")
    else:
        print("[telegram] whitelist de usuarios no configurada; se aceptaran mensajes de cualquier usuario")

    try:
        run_polling_loop(
            adapter=TelegramChannelAdapter(persist_log=True),
            token=token,
            allowed_chat_ids=allowed_chat_ids,
            allowed_user_ids=allowed_user_ids,
            poll_timeout_seconds=args.poll_timeout,
            idle_sleep_seconds=args.idle_sleep,
            max_cycles=1 if args.once else None,
        )
    except KeyboardInterrupt:
        print("[telegram] bot detenido por teclado")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Contexto técnico del proyecto (Agenda AI)

## 1) Estructura de archivos (foco bot + core)

- `run.py`: entrypoint de la app Streamlit (Dashboard, Clientes, Proyectos, Tareas, Consultas IA, Asistente).
- `scripts/run_telegram_bot.py`: entrypoint del bot Telegram real (polling).
- `scripts/run_telegram_simulator.py`: simulador local del canal Telegram.
- `app/channels/telegram/adapter.py`: extracción/normalización de mensaje, comandos de canal y enrutamiento al runtime.
- `app/channels/telegram/polling.py`: integración con Telegram Bot API (`getUpdates`, `sendMessage`), whitelist y loop de polling.
- `app/channels/telegram/context_store.py`: almacenamiento de contexto en memoria por conversación.
- `app/services/conversation_runtime_service.py`: orquestación de un turno conversacional.
- `app/services/query_parser_service.py`: parser por reglas.
- `app/services/hybrid_parser_service.py`: parser híbrido reglas + LLM.
- `app/services/llm_parser_service.py`: integración con endpoint LLM compatible chat completions.
- `app/services/query_response_service.py`: armado de respuesta final.
- `app/services/*_service.py`: lógica de negocio (clientes, proyectos, tareas, agenda, conversación, updates).
- `app/repositories/*.py`: capa de acceso a datos.
- `app/db/*`: bootstrap SQLAlchemy y modelos.
- `app/config.py`: configuración de DB y del parser IA local.

---

## 2) Archivo principal (main.py/app.py) y entrypoints reales

No existe `main.py` ni `app.py` en el repositorio.

Entrypoints actuales:

1. **UI principal**: `run.py`
   - Ejecuta `init_db()`.
   - Configura Streamlit.
   - Muestra navegación lateral y renderiza páginas.

2. **Bot Telegram real**: `scripts/run_telegram_bot.py`
   - Lee argumentos (`--poll-timeout`, `--idle-sleep`, `--once`).
   - Obtiene token con `get_telegram_bot_token(required=True)`.
   - Lee whitelist de chats/usuarios.
   - Inicia `run_polling_loop(...)` con `TelegramChannelAdapter`.

---

## 3) Esquema de base de datos (SQLAlchemy)

### Bootstrap

- `app/db/base.py`: define `Base(DeclarativeBase)`.
- `app/db/session.py`: crea `engine` y `SessionLocal`.
- `app/db/__init__.py`: `init_db()` ejecuta `Base.metadata.create_all(bind=engine)`.
- Base por defecto: SQLite en `data/agenda.db`.

### Tablas y relaciones

1. **`clients`** (`app/db/models/client.py`)
   - Campos: `id`, `name`, `company`, `notes`, `created_at`
   - Relación: `Client 1-N Project`

2. **`projects`** (`app/db/models/project.py`)
   - Campos: `id`, `client_id` (FK `clients.id`), `name`, `description`, `status`, `created_at`
   - Relación: `Project 1-N Task`

3. **`tasks`** (`app/db/models/task.py`)
   - Campos: `id`, `project_id` (FK `projects.id`), `title`, `description`, `status`, `priority`,
     `due_date`, `last_note`, `next_action`, `last_updated_at`, `created_at`, `updated_at`
   - Relación: `Task 1-N TaskUpdate`

4. **`task_updates`** (`app/db/models/task_update.py`)
   - Campos: `id`, `task_id` (FK `tasks.id`), `content`, `update_type`, `source`, `created_at`

5. **`agenda_items`** (`app/db/models/agenda_item.py`)
   - Campos: `id`, `title`, `scheduled_date`, `scheduled_time`, `kind`, `note`, `created_at`
   - Independiente (sin FK).

6. **`conversation_logs`** (`app/db/models/conversation_log.py`)
   - Campos: `id`, `user_input`, `parsed_intent`, `response_output`, `created_at`
   - Independiente (sin FK).

---

## 4) Manejo de token y seguridad en Telegram

### Token

- Se toma de variable de entorno: `TELEGRAM_BOT_TOKEN`.
- Función clave: `get_telegram_bot_token(required=True)` en `app/channels/telegram/adapter.py`.
  - Si hay valor: lo retorna.
  - Si falta y `required=True`: lanza `RuntimeError`.
- El token no se persiste en base ni en código de negocio.

### Whitelist de acceso

- `TELEGRAM_ALLOWED_CHAT_IDS`: lista de chat IDs permitidos.
- `TELEGRAM_ALLOWED_USER_IDS`: lista de user IDs permitidos.
- Parseo en `parse_allowed_chat_ids()` y `parse_allowed_user_ids()` (`polling.py`).
- Validación por update en `is_telegram_identity_allowed(...)`.

### Operación del polling

- `run_polling_loop(...)`:
  - Resuelve token (env).
  - Consulta updates con `getUpdates`.
  - Procesa cada update.
  - Responde con `sendMessage`.
- Config de ciclo:
  - `TELEGRAM_POLL_TIMEOUT_SECONDS`
  - `TELEGRAM_IDLE_SLEEP_SECONDS`

---

## 5) Flujo técnico del mensaje Telegram (end-to-end)

1. `scripts/run_telegram_bot.py` inicia el loop.
2. `app/channels/telegram/polling.py` obtiene updates desde Telegram API.
3. `process_telegram_update(...)` extrae mensaje con `extract_telegram_message(...)`.
4. Se aplica whitelist (chat/user).
5. `TelegramChannelAdapter.handle_update(...)` enruta:
   - Si comando (`/start`, `/help`, `/reset`, `/status`, `/whoami`) responde por `_handle_command(...)`.
   - Si texto normal: llama `process_conversation_turn(...)`.
6. Se actualiza contexto conversacional en `InMemoryTelegramContextStore`.
7. Se devuelve payload y se envía respuesta por `sendMessage`.

---

## 6) Configuración relevante

En `app/config.py`:

- `DATABASE_URL` -> SQLite local (`data/agenda.db`)
- `USE_LLM_PARSER`
- `LLM_PARSER_URL`
- `LLM_API_KEY`
- `LLM_MODEL_NAME`
- `LLM_TIMEOUT_SECONDS`

En entorno Telegram:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_CHAT_IDS`
- `TELEGRAM_ALLOWED_USER_IDS`
- `TELEGRAM_POLL_TIMEOUT_SECONDS`
- `TELEGRAM_IDLE_SLEEP_SECONDS`

---

## 7) Código clave consolidado

```python
# scripts/run_telegram_bot.py
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
from app.channels.telegram.polling import parse_allowed_chat_ids, parse_allowed_user_ids, run_polling_loop

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--poll-timeout", type=int, default=int(os.getenv("TELEGRAM_POLL_TIMEOUT_SECONDS", "20")))
    parser.add_argument("--idle-sleep", type=float, default=float(os.getenv("TELEGRAM_IDLE_SLEEP_SECONDS", "1")))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    token = get_telegram_bot_token(required=True)
    allowed_chat_ids = parse_allowed_chat_ids()
    allowed_user_ids = parse_allowed_user_ids()

    run_polling_loop(
        adapter=TelegramChannelAdapter(persist_log=True),
        token=token,
        allowed_chat_ids=allowed_chat_ids,
        allowed_user_ids=allowed_user_ids,
        poll_timeout_seconds=args.poll_timeout,
        idle_sleep_seconds=args.idle_sleep,
        max_cycles=1 if args.once else None,
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


# app/channels/telegram/adapter.py (token + routing)
def get_telegram_bot_token(*, required: bool = False) -> str | None:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if token:
        return token
    if required:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN. Configuralo como variable de entorno para usar Telegram real.")
    return None

def parse_telegram_command(text: str) -> str | None:
    normalized = (text or "").strip()
    if not normalized.startswith("/"):
        return None
    command = normalized.split()[0].lower()
    if command in {"/start", "/help", "/reset", "/status", "/whoami"}:
        return command
    return None

class TelegramChannelAdapter:
    def handle_incoming_text(self, *, chat_id, text, user_id=None, chat_type=None, message_thread_id=None, conversation_key=None):
        command = parse_telegram_command(text)
        if command:
            return self._handle_command(...)
        result = process_conversation_turn(text.strip(), conversation_context=current_context, persist_log=self.persist_log)
        self.context_store.save_context(effective_conversation_key, result.get("conversation_context") or {})
        return {"send_message_payload": {"chat_id": str(chat_id), "text": result["response_text"]}}


# app/channels/telegram/polling.py (loop + whitelist + API)
def parse_allowed_chat_ids(raw_value: str | None = None) -> set[str] | None:
    source = raw_value if raw_value is not None else os.getenv("TELEGRAM_ALLOWED_CHAT_IDS")
    if source is None:
        return None
    values = [item.strip() for item in re.split(r"[\\s,;]+", source) if item.strip()]
    return set(values) or None

def parse_allowed_user_ids(raw_value: str | None = None) -> set[str] | None:
    source = raw_value if raw_value is not None else os.getenv("TELEGRAM_ALLOWED_USER_IDS")
    if source is None:
        return None
    values = [item.strip() for item in re.split(r"[\\s,;]+", source) if item.strip()]
    return set(values) or None

def run_polling_loop(...):
    bot_token = token or get_telegram_bot_token(required=True)
    updates = get_updates(...)
    result = process_telegram_update(...)
    send_message(...)


# app/config.py
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "agenda.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

USE_LLM_PARSER = True
LLM_PARSER_URL = "http://127.0.0.1:1234/v1/chat/completions"
LLM_API_KEY = "local-key"
LLM_MODEL_NAME = "qwen2.5-7b-instruct"
LLM_TIMEOUT_SECONDS = 30


# app/db/__init__.py + app/db/session.py + modelos (resumen)
from app.db.base import Base
from app.db.session import engine
def init_db() -> None:
    Base.metadata.create_all(bind=engine)

# tablas:
# clients(id, name, company, notes, created_at)
# projects(id, client_id -> clients.id, name, description, status, created_at)
# tasks(id, project_id -> projects.id, title, description, status, priority, due_date, last_note, next_action, last_updated_at, created_at, updated_at)
# task_updates(id, task_id -> tasks.id, content, update_type, source, created_at)
# agenda_items(id, title, scheduled_date, scheduled_time, kind, note, created_at)
# conversation_logs(id, user_input, parsed_intent, response_output, created_at)
```


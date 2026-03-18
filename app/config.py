from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "agenda.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"

# =========================
# Parser híbrido con IA local
# =========================

USE_LLM_PARSER = True

# Pegá acá la URL exacta de tu servidor local compatible con chat completions
LLM_PARSER_URL = "http://127.0.0.1:1234/v1/chat/completions"

# Si tu servidor no requiere API key real, dejá un valor dummy
LLM_API_KEY = "local-key"

# Pegá acá el nombre exacto del modelo cargado en tu servidor local
LLM_MODEL_NAME = "qwen2.5-7b-instruct"

LLM_TIMEOUT_SECONDS = 30
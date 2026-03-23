# Agenda AI - Workspace Rules

## Proyecto
Este repo es `Agenda AI`, un asistente IA local para:
- clientes
- proyectos
- tareas
- agenda personal
- Telegram
- trazabilidad/auditoría

## Stack
- Python
- Streamlit
- SQLAlchemy + SQLite
- Telegram polling
- PowerShell
- unittest + acceptance runner

## Reglas obligatorias
- Reutilizar el core actual.
- No crear arquitecturas paralelas.
- No inventar contexto ni acciones.
- No ejecutar create/update bajo ambigüedad.
- Mantener contexto Telegram aislado por `chat_id`.
- Mantener agenda personal separada de tareas operativas.

## Variables de entorno y nombres esperados
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_CHAT_IDS`
- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- `AIDER_MODEL`
- `AIDER_TEST_CMD`
- `AIDER_LINT_CMD`

## Flujo correcto
- Web y Telegram usan el mismo runtime compartido.
- Cualquier cambio debe respetar `scripts/validate.ps1`.
- Si toca conversación real, correr smoke acceptance.
- Si toca Telegram, no depender de `st.session_state`.

## Seguridad
- No hardcodear secretos.
- No commitear credenciales.
- Si falta contexto seguro, responder claro y no inventar.
- Si hay múltiples candidatos, pedir clarificación específica.

## Calidad
- Cambios pequeños y testeables.
- Agregar tests si se modifica parser, targeting, Telegram o UX importante.
- Mantener respuestas claras, no demasiado técnicas para el usuario final.
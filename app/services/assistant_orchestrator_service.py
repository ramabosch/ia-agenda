from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable
import logging

from app.db.session import SessionLocal
from app.repositories import agenda_repository, client_repository, task_repository
from app.services.agenda_service import resolve_agenda_date_hint, resolve_agenda_time_hint

CONTEXT_CLIENT_VALUES = {"este cliente", "ese cliente", "cliente actual"}
CONTEXT_TASK_VALUES = {"esta tarea", "esa tarea", "tarea actual", "eso"}
logger = logging.getLogger(__name__)


class AssistantOrchestratorService:
    def __init__(
        self,
        *,
        session_factory: Callable[[], Any] = SessionLocal,
        client_repo=client_repository,
        task_repo=task_repository,
        agenda_repo=agenda_repository,
    ) -> None:
        self._session_factory = session_factory
        self._client_repo = client_repo
        self._task_repo = task_repo
        self._agenda_repo = agenda_repo

    def execute_actions(self, actions: list[dict], *, conversation_context: dict | None = None) -> dict:
        print(f"[DEBUG ORCHESTRATOR] Actions received: {actions}")
        memory = self._extract_memory(conversation_context)
        reports: list[dict] = []

        db = self._session_factory()
        try:
            for idx, raw_action in enumerate(actions, start=1):
                action = self._apply_contextual_defaults(raw_action, memory)
                logger.info("assistant_orchestrator action_start index=%s intent=%s payload=%s", idx, action.get("intent"), action)
                try:
                    report = self._execute_one(db, action)
                except Exception as exc:
                    logger.exception("assistant_orchestrator action_exception index=%s intent=%s", idx, action.get("intent"))
                    report = {
                        "intent": action.get("intent") or "unknown",
                        "ok": False,
                        "message": f"Fallo interno ejecutando accion ({exc}).",
                        "technical_error": str(exc),
                    }
                reports.append(report)
                self._refresh_memory(memory, report, action)
        finally:
            db.close()

        return {
            "reports": reports,
            "conversation_context": self._merge_memory(conversation_context, memory),
        }

    def _execute_one(self, db, action: dict) -> dict:
        intent = action.get("intent")
        if intent == "create_client":
            name = (action.get("client_name") or action.get("content") or "").strip()
            if not name:
                return {"intent": intent, "ok": False, "message": "No pude crear el cliente: faltó el nombre."}
            existing = self._client_repo.get_client_by_name(db, name)
            if existing:
                return {"intent": intent, "ok": True, "client_name": existing.name, "message": f"El cliente {existing.name} ya existía."}
            try:
                created = self._client_repo.create_client(db, name=name)
            except Exception as exc:
                logger.exception("assistant_orchestrator db_error create_client name=%s", name)
                return {
                    "intent": intent,
                    "ok": False,
                    "message": f"No pude crear el cliente {name}.",
                    "technical_error": str(exc),
                }
            return {"intent": intent, "ok": True, "client_name": created.name, "client_id": created.id, "message": f"Creé el cliente {created.name}."}

        if intent == "create_agenda_item":
            title = (action.get("agenda_title") or action.get("content") or "").strip()
            if not title:
                return {"intent": intent, "ok": False, "message": "No pude agendar: faltó el título."}
            client_name = (action.get("client_name") or "").strip() or None
            if client_name:
                client = self._client_repo.get_client_by_name(db, client_name)
                if not client:
                    return {
                        "intent": intent,
                        "ok": False,
                        "message": "No pude agendar la reunión porque no encontré al cliente.",
                        "technical_error": f"client_not_found:{client_name}",
                    }
            date_info = resolve_agenda_date_hint(action.get("agenda_date_hint"))
            if not date_info.get("resolved") or not date_info.get("target_date"):
                return {"intent": intent, "ok": False, "message": "No pude agendar: necesito una fecha concreta."}
            time_info = resolve_agenda_time_hint(action.get("agenda_time_hint"))
            scheduled_time = time_info.get("target_time") if time_info.get("resolved") else None
            try:
                item = self._agenda_repo.create_agenda_item(
                    db,
                    title=title,
                    scheduled_date=date_info["target_date"],
                    scheduled_time=scheduled_time,
                    kind=(action.get("agenda_kind") or "event"),
                )
            except Exception as exc:
                logger.exception("assistant_orchestrator db_error create_agenda_item title=%s", title)
                return {
                    "intent": intent,
                    "ok": False,
                    "message": "No pude agendar la reunión por un error al guardar en la base.",
                    "technical_error": str(exc),
                }
            return {
                "intent": intent,
                "ok": True,
                "agenda_item_id": item.id,
                "agenda_title": item.title,
                "message": f"Agendé '{item.title}' para {date_info.get('label') or item.scheduled_date}.",
            }

        if intent == "update_agenda_item":
            all_items = self._agenda_repo.get_all_agenda_items(db)
            target_id = memory_agenda_id = None
            target_title = (action.get("agenda_target_title") or "").strip() or None
            target_date_hint = action.get("agenda_target_date_hint")
            target_time_hint = action.get("agenda_target_time_hint")
            use_context = bool(action.get("agenda_use_context"))

            if use_context:
                memory_agenda_id = action.get("agenda_item_id") or action.get("_agenda_item_id")
            if not memory_agenda_id:
                memory_agenda_id = action.get("memory_agenda_item_id")

            if memory_agenda_id:
                target_id = int(memory_agenda_id)

            if target_id is None and target_title:
                matches = [item for item in all_items if target_title.lower() in (item.title or "").lower()]
                if target_date_hint:
                    date_info = resolve_agenda_date_hint(target_date_hint)
                    if date_info.get("resolved") and date_info.get("target_date"):
                        matches = [item for item in matches if item.scheduled_date == date_info["target_date"]]
                if target_time_hint:
                    time_info = resolve_agenda_time_hint(target_time_hint)
                    if time_info.get("resolved"):
                        matches = [item for item in matches if item.scheduled_time == time_info.get("target_time")]
                if matches:
                    target_id = matches[0].id

            if target_id is None:
                return {
                    "intent": intent,
                    "ok": False,
                    "message": "No pude actualizar la agenda porque no encontré el evento objetivo.",
                    "technical_error": "agenda_target_not_found",
                }

            new_date = None
            new_time = None
            if action.get("agenda_new_date_hint"):
                new_date_info = resolve_agenda_date_hint(action.get("agenda_new_date_hint"))
                if not new_date_info.get("resolved") or not new_date_info.get("target_date"):
                    return {
                        "intent": intent,
                        "ok": False,
                        "message": "No pude actualizar la agenda: la nueva fecha no es válida.",
                        "technical_error": "invalid_agenda_new_date_hint",
                    }
                new_date = new_date_info["target_date"]
            if action.get("agenda_new_time_hint"):
                new_time_info = resolve_agenda_time_hint(action.get("agenda_new_time_hint"))
                if not new_time_info.get("resolved"):
                    return {
                        "intent": intent,
                        "ok": False,
                        "message": "No pude actualizar la agenda: la nueva hora no es válida.",
                        "technical_error": "invalid_agenda_new_time_hint",
                    }
                new_time = new_time_info.get("target_time")

            try:
                updated_item = self._agenda_repo.update_agenda_item(
                    db,
                    target_id,
                    scheduled_date=new_date,
                    scheduled_time=new_time,
                )
            except Exception as exc:
                logger.exception("assistant_orchestrator db_error update_agenda_item id=%s", target_id)
                return {
                    "intent": intent,
                    "ok": False,
                    "message": "No pude actualizar la agenda por un error al guardar en la base.",
                    "technical_error": str(exc),
                }

            if not updated_item:
                return {
                    "intent": intent,
                    "ok": False,
                    "message": "No pude actualizar la agenda porque el evento no existe.",
                    "technical_error": f"agenda_item_not_found:{target_id}",
                }

            return {
                "intent": intent,
                "ok": True,
                "agenda_item_id": updated_item.id,
                "agenda_title": updated_item.title,
                "message": f"Actualicé la agenda: '{updated_item.title}'.",
            }

        if intent in {"complete_task_by_name", "update_task_status"}:
            status = action.get("new_status") or "hecha"
            task_name = (action.get("task_name") or "").strip()
            if not task_name:
                return {"intent": intent, "ok": False, "message": "No pude actualizar la tarea: faltó referencia."}
            task = self._task_repo.get_task_by_name(db, task_name)
            if not task:
                return {"intent": intent, "ok": False, "message": f"No encontré la tarea '{task_name}'."}
            try:
                updated = self._task_repo.update_task_status(db, task.id, status)
            except Exception as exc:
                logger.exception("assistant_orchestrator db_error update_task_status task=%s", task_name)
                return {
                    "intent": intent,
                    "ok": False,
                    "message": f"No pude actualizar la tarea '{task_name}' por un error en base.",
                    "technical_error": str(exc),
                }
            if not updated:
                return {"intent": intent, "ok": False, "message": f"No pude actualizar la tarea '{task_name}'."}
            return {
                "intent": intent,
                "ok": True,
                "task_id": updated.id,
                "task_name": updated.title,
                "new_status": updated.status,
                "message": f"Marqué '{updated.title}' como {updated.status}.",
            }

        return {"intent": intent or "unknown", "ok": False, "message": "No ejecuté esa acción todavía."}

    def _extract_memory(self, conversation_context: dict | None) -> dict:
        if not isinstance(conversation_context, dict):
            return {}
        memory = conversation_context.get("assistant_memory")
        return deepcopy(memory) if isinstance(memory, dict) else {}

    def _merge_memory(self, conversation_context: dict | None, memory: dict) -> dict:
        base = deepcopy(conversation_context) if isinstance(conversation_context, dict) else {}
        base["assistant_memory"] = deepcopy(memory)
        return base

    def _apply_contextual_defaults(self, action: dict, memory: dict) -> dict:
        normalized = deepcopy(action)
        client_name = normalized.get("client_name")
        if client_name in CONTEXT_CLIENT_VALUES:
            normalized["client_name"] = memory.get("last_client_name")
            logger.info(
                "assistant_orchestrator memory_client_reference placeholder=%s resolved=%s",
                client_name,
                normalized.get("client_name"),
            )
        elif not client_name and memory.get("last_client_name"):
            normalized["client_name"] = memory.get("last_client_name")
            logger.info(
                "assistant_orchestrator memory_client_fallback resolved=%s intent=%s",
                normalized.get("client_name"),
                normalized.get("intent"),
            )
        else:
            logger.info(
                "assistant_orchestrator memory_client_missing intent=%s",
                normalized.get("intent"),
            )

        task_name = normalized.get("task_name")
        if task_name in CONTEXT_TASK_VALUES:
            normalized["task_name"] = memory.get("last_task_name")

        agenda_title = normalized.get("agenda_title")
        if isinstance(agenda_title, str) and memory.get("last_client_name"):
            normalized["agenda_title"] = (
                agenda_title.replace("ese cliente", memory["last_client_name"])
                .replace("este cliente", memory["last_client_name"])
            )
        if normalized.get("agenda_use_context"):
            normalized["memory_agenda_item_id"] = memory.get("last_agenda_item_id")
        return normalized

    def _refresh_memory(self, memory: dict, report: dict, action: dict) -> None:
        if not report.get("ok"):
            return
        if report.get("client_name"):
            memory["last_client_name"] = report["client_name"]
        elif action.get("client_name"):
            memory["last_client_name"] = action["client_name"]

        if report.get("task_name"):
            memory["last_task_name"] = report["task_name"]
        elif action.get("task_name"):
            memory["last_task_name"] = action["task_name"]
        if report.get("agenda_item_id"):
            memory["last_agenda_item_id"] = report["agenda_item_id"]
        if report.get("agenda_title"):
            memory["last_agenda_title"] = report["agenda_title"]

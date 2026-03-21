from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from app.db.session import SessionLocal
from app.repositories import agenda_repository, client_repository, task_repository
from app.services.agenda_service import resolve_agenda_date_hint, resolve_agenda_time_hint

CONTEXT_CLIENT_VALUES = {"este cliente", "ese cliente", "cliente actual"}
CONTEXT_TASK_VALUES = {"esta tarea", "esa tarea", "tarea actual", "eso"}


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
        memory = self._extract_memory(conversation_context)
        reports: list[dict] = []

        db = self._session_factory()
        try:
            for raw_action in actions:
                action = self._apply_contextual_defaults(raw_action, memory)
                report = self._execute_one(db, action)
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
            created = self._client_repo.create_client(db, name=name)
            return {"intent": intent, "ok": True, "client_name": created.name, "client_id": created.id, "message": f"Creé el cliente {created.name}."}

        if intent == "create_agenda_item":
            title = (action.get("agenda_title") or action.get("content") or "").strip()
            if not title:
                return {"intent": intent, "ok": False, "message": "No pude agendar: faltó el título."}
            date_info = resolve_agenda_date_hint(action.get("agenda_date_hint"))
            if not date_info.get("resolved") or not date_info.get("target_date"):
                return {"intent": intent, "ok": False, "message": "No pude agendar: necesito una fecha concreta."}
            time_info = resolve_agenda_time_hint(action.get("agenda_time_hint"))
            scheduled_time = time_info.get("target_time") if time_info.get("resolved") else None
            item = self._agenda_repo.create_agenda_item(
                db,
                title=title,
                scheduled_date=date_info["target_date"],
                scheduled_time=scheduled_time,
                kind=(action.get("agenda_kind") or "event"),
            )
            return {
                "intent": intent,
                "ok": True,
                "agenda_item_id": item.id,
                "agenda_title": item.title,
                "message": f"Agendé '{item.title}' para {date_info.get('label') or item.scheduled_date}.",
            }

        if intent in {"complete_task_by_name", "update_task_status"}:
            status = action.get("new_status") or "hecha"
            task_name = (action.get("task_name") or "").strip()
            if not task_name:
                return {"intent": intent, "ok": False, "message": "No pude actualizar la tarea: faltó referencia."}
            task = self._task_repo.get_task_by_name(db, task_name)
            if not task:
                return {"intent": intent, "ok": False, "message": f"No encontré la tarea '{task_name}'."}
            updated = self._task_repo.update_task_status(db, task.id, status)
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

        task_name = normalized.get("task_name")
        if task_name in CONTEXT_TASK_VALUES:
            normalized["task_name"] = memory.get("last_task_name")

        agenda_title = normalized.get("agenda_title")
        if isinstance(agenda_title, str) and memory.get("last_client_name"):
            normalized["agenda_title"] = (
                agenda_title.replace("ese cliente", memory["last_client_name"])
                .replace("este cliente", memory["last_client_name"])
            )
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

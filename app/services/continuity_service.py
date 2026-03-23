from __future__ import annotations

import unicodedata
from typing import Any, Callable


class ContinuityService:
    def __init__(
        self,
        *,
        abort_with_context: Callable[[dict, str], str],
        base_conversation_context: Callable[[dict, str], dict],
        resolve_if_needed: Callable[[dict, str | None], dict],
        handle_operational_summary_intent: Callable[[dict, dict, str | None, dict], str],
        set_audit_trace: Callable[[dict, str | None, str, str, str, dict | None], None],
        store_response_snapshot: Callable[[dict, dict], None],
        format_next_recommendation_followup: Callable[[dict], str],
        delete_agenda_item: Callable[[int], dict],
        delete_task: Callable[[int], dict],
        restore_task_priority: Callable[[int, str | None, str | None], dict],
        restore_task_status: Callable[[int, str, str | None], dict],
        restore_task_note: Callable[[int, str | None], dict],
        restore_project_description: Callable[[int, str | None], dict],
        safe_context_message: Callable[[str, str | None], str],
    ) -> None:
        self._abort_with_context = abort_with_context
        self._base_conversation_context = base_conversation_context
        self._resolve_if_needed = resolve_if_needed
        self._handle_operational_summary_intent = handle_operational_summary_intent
        self._set_audit_trace = set_audit_trace
        self._store_response_snapshot = store_response_snapshot
        self._format_next_recommendation_followup = format_next_recommendation_followup
        self._delete_agenda_item = delete_agenda_item
        self._delete_task = delete_task
        self._restore_task_priority = restore_task_priority
        self._restore_task_status = restore_task_status
        self._restore_task_note = restore_task_note
        self._restore_project_description = restore_project_description
        self._safe_context_message = safe_context_message

    def intercept_vague_terms(self, parsed_query: dict) -> dict:
        if not isinstance(parsed_query, dict):
            return parsed_query

        intent = parsed_query.get("intent")
        if intent in {None, "", "unknown", "expand_context"}:
            return parsed_query

        interceptable_intents = {
            "clarify_entity_reference",
            "get_operational_summary",
            "get_operational_friction_summary",
            "get_operational_recommendation",
            "get_task_summary",
            "get_project_summary",
            "get_client_summary",
            "update_task_status",
            "update_task_priority",
            "add_task_note",
            "update_task_next_action",
            "update_task_last_note",
            "complete_task_by_name",
            "update_task_priority_by_name",
        }
        if intent not in interceptable_intents:
            return parsed_query
        if parsed_query.get("_parser_source") != "llm":
            return parsed_query

        vague_other_terms = {"la otra", "el otro", "lo otro", "otra", "otro"}
        vague_recent_terms = {"eso", "esto", "lo de recien", "lo de recién", "lo anterior"}
        target_fields = ("task_name", "project_name", "client_name", "entity_hint")

        for field in target_fields:
            raw_value = parsed_query.get(field)
            normalized_value = _normalize_vague_term(raw_value)
            if normalized_value in vague_other_terms:
                parsed_query["_intercepted_intent"] = parsed_query.get("intent")
                parsed_query["intent"] = "expand_context"
                parsed_query["expand_mode"] = "other_entity_summary"
                parsed_query["contrast_hint"] = "prefer_other"
                return parsed_query
            if normalized_value in vague_recent_terms:
                parsed_query["_intercepted_intent"] = parsed_query.get("intent")
                parsed_query["intent"] = "expand_context"
                parsed_query["expand_mode"] = "recent_entity_summary"
                return parsed_query

        return parsed_query

    def handle_expansion(
        self,
        parsed_query: dict,
        *,
        user_query: str | None,
        conversation_context: dict | None,
    ) -> str:
        context = conversation_context or {}
        snapshot = context.get("response_snapshot") if isinstance(context, dict) else None

        if not context or not context.get("_isolated"):
            return self._abort_with_context(
                parsed_query,
                self._safe_context_message("continuar esa conversacion"),
            )

        expand_mode = parsed_query.get("expand_mode")
        if expand_mode == "recent_entity_summary":
            return self._handle_recent_entity_summary(
                parsed_query,
                user_query=user_query,
                conversation_context=context,
            )
        if expand_mode == "more_recommendations":
            return self._handle_more_recommendations(parsed_query, snapshot=snapshot)
        if expand_mode == "other_entity_action":
            return self._handle_other_entity_action(
                parsed_query,
                user_query=user_query,
                conversation_context=context,
            )
        if expand_mode == "other_entity_summary":
            return self._handle_other_entity_summary(
                parsed_query,
                user_query=user_query,
                conversation_context=context,
            )
        if expand_mode == "undo_recent_action":
            return self._handle_recent_undo_intent(
                parsed_query,
                user_query=user_query,
                conversation_context=context,
            )
        return self._abort_with_context(parsed_query, "No pude interpretar ese follow-up con suficiente claridad.")

    def _handle_recent_entity_summary(
        self,
        parsed_query: dict,
        *,
        user_query: str | None,
        conversation_context: dict,
    ) -> str:
        context = conversation_context or {}
        focus_scope = context.get("scope")
        if isinstance(focus_scope, str) and focus_scope.startswith("contextual_"):
            focus_scope = focus_scope.removeprefix("contextual_")
        if focus_scope not in {"client", "project", "task"}:
            focus_scope = context.get("clarification_expected_scope") or "none"

        synthetic_query = dict(parsed_query)
        synthetic_query["intent"] = "get_operational_summary"
        synthetic_query["expected_scope"] = focus_scope
        synthetic_query.pop("entity_hint", None)
        if focus_scope == "client":
            synthetic_query["client_name"] = "este cliente"
        elif focus_scope == "project":
            synthetic_query["project_name"] = "este proyecto"
        elif focus_scope == "task":
            synthetic_query["task_name"] = "esta tarea"
        else:
            synthetic_query["entity_hint"] = "aca"

        resolved = self._resolve_if_needed(
            synthetic_query,
            user_query,
            conversation_context=context,
        )
        if focus_scope in {"client", "project", "task"}:
            for other_scope in ("client", "project", "task"):
                if other_scope == focus_scope:
                    continue
                if isinstance(resolved.get(other_scope), dict):
                    resolved[other_scope]["resolved"] = None
            resolved["scope"] = focus_scope

        if resolved.get("scope") == "none":
            return self._abort_with_context(
                parsed_query,
                "No tengo una entidad reciente suficientemente clara en esta conversacion para seguir por ahi.",
            )

        response = self._handle_operational_summary_intent(
            synthetic_query,
            resolved,
            user_query=user_query,
            conversation_context=context,
        )
        self._sync_synthetic_artifacts(parsed_query, synthetic_query)
        current_context = parsed_query.get("_conversation_context")
        if isinstance(current_context, dict):
            for scope in ("client", "project", "task"):
                if not current_context.get(scope) and context.get(scope):
                    current_context[scope] = dict(context[scope])
        return response

    def _handle_more_recommendations(self, parsed_query: dict, *, snapshot: dict | None) -> str:
        if not snapshot or not snapshot.get("recommendations"):
            return self._abort_with_context(
                parsed_query,
                "No tengo una recomendacion previa clara en esta conversacion actual para decirte que mas haria.",
            )
        response = self._format_next_recommendation_followup(snapshot)
        self._store_response_snapshot(
            parsed_query,
            {
                **snapshot,
                "response_kind": "followup_next_recommendation",
                "status_overview": snapshot.get("status_overview"),
                "recommendation": response,
            },
        )
        return response

    def _handle_other_entity_action(
        self,
        parsed_query: dict,
        *,
        user_query: str | None,
        conversation_context: dict,
    ) -> str:
        context = conversation_context or {}
        other_resolution = self._resolve_other_context_candidate(context)
        if other_resolution.get("status") == "ambiguous":
            options = other_resolution.get("candidates") or []
            lines = ["Veo mas de una alternativa posible para 'el otro'. Decime cual queres:"]
            for item in options[:4]:
                lines.append(f"- {item['name']} ({item['scope']})")
            return self._abort_with_context(parsed_query, "\n".join(lines))

        other_candidate = other_resolution.get("candidate")
        if not other_candidate:
            return self._abort_with_context(
                parsed_query,
                "No tengo claro cual seria 'el otro' en esta conversacion actual. Decimelo mas concreto.",
            )

        parsed_query["_conversation_context"] = {
            **self._base_conversation_context(parsed_query, other_candidate["scope"]),
            other_candidate["scope"]: {
                "id": other_candidate.get("id"),
                "name": other_candidate.get("name"),
            },
            "recent_entities": list(context.get("recent_entities") or []),
        }
        response = self._build_other_entity_action_prompt(context, other_candidate)
        self._set_audit_trace(
            parsed_query,
            user_query=user_query,
            response=response,
            action_status="informational",
            action_type="clarification",
            affected_entity={
                "scope": other_candidate["scope"],
                "id": other_candidate.get("id"),
                "name": other_candidate.get("name"),
            },
        )
        return response

    def _handle_other_entity_summary(
        self,
        parsed_query: dict,
        *,
        user_query: str | None,
        conversation_context: dict,
    ) -> str:
        context = conversation_context or {}
        other_resolution = self._resolve_other_context_candidate(context)
        if other_resolution.get("status") == "ambiguous":
            options = other_resolution.get("candidates") or []
            lines = ["Veo mas de una alternativa posible para 'lo otro'. Decime cual queres resumir:"]
            for item in options[:4]:
                lines.append(f"- {item['name']} ({item['scope']})")
            return self._abort_with_context(parsed_query, "\n".join(lines))

        other_candidate = other_resolution.get("candidate")
        if not other_candidate:
            return self._abort_with_context(
                parsed_query,
                "No tengo claro a que otra entidad te referis en esta conversacion actual.",
            )

        synthetic_query = dict(parsed_query)
        synthetic_query["intent"] = "get_operational_summary"
        synthetic_query["expected_scope"] = other_candidate["scope"]
        if other_candidate["scope"] == "client":
            synthetic_query["client_name"] = other_candidate["name"]
        elif other_candidate["scope"] == "project":
            synthetic_query["project_name"] = other_candidate["name"]
        elif other_candidate["scope"] == "task":
            synthetic_query["task_name"] = other_candidate["name"]

        resolved = self._resolve_if_needed(
            synthetic_query,
            user_query,
            conversation_context=context,
        )
        response = self._handle_operational_summary_intent(
            synthetic_query,
            resolved,
            user_query=user_query,
            conversation_context=context,
        )
        self._sync_synthetic_artifacts(parsed_query, synthetic_query)
        return response

    def _handle_recent_undo_intent(
        self,
        parsed_query: dict,
        *,
        user_query: str | None,
        conversation_context: dict,
    ) -> str:
        last_action = (conversation_context or {}).get("last_action_trace") or {}
        if not last_action:
            return self._abort_with_context(
                parsed_query,
                "No tengo una accion reciente reversible y segura en esta conversacion.",
            )

        entity = last_action.get("entity") or {}
        payload = last_action.get("payload") or {}
        undo_operation = last_action.get("undo_operation") or {}
        undo_type = undo_operation.get("type") or last_action.get("undo_type")
        entity_id = (
            undo_operation.get("entity_id")
            if undo_operation.get("entity_id") is not None
            else entity.get("id", last_action.get("entity_id"))
        )
        entity_name = entity.get("name") or last_action.get("entity_name") or "eso"
        previous_value = payload.get("previous_value", last_action.get("previous_value"))

        if undo_type == "delete_agenda_item" and entity_id:
            result = self._delete_agenda_item(int(entity_id))
            if not result.get("deleted"):
                return self._abort_with_context(parsed_query, "No pude cancelar ese item reciente de agenda.")
            parsed_query["_conversation_context"] = self._base_conversation_context(parsed_query, "agenda")
            response = f"Listo: cancele '{result['title']}' de tu agenda."
            self._set_audit_trace(
                parsed_query,
                user_query=user_query,
                response=response,
                action_status="executed",
                action_type="agenda_delete",
                affected_entity={"scope": "agenda", "id": result["agenda_item_id"], "name": result["title"]},
            )
            return response

        if undo_type == "delete_task" and entity_id:
            result = self._delete_task(int(entity_id))
            if not result.get("deleted"):
                return self._abort_with_context(parsed_query, "No pude deshacer esa tarea reciente.")
            parsed_query["_conversation_context"] = self._base_conversation_context(parsed_query, "task")
            response = f"Listo: elimine la tarea '{result['task_title']}' que acababa de crear."
            self._set_audit_trace(
                parsed_query,
                user_query=user_query,
                response=response,
                action_status="executed",
                action_type="task_delete",
                affected_entity={"scope": "task", "id": result["task_id"], "name": result["task_title"]},
            )
            return response

        if undo_type == "restore_task_status" and entity_id:
            result = self._restore_task_status(int(entity_id), previous_value, None)
            if not result.get("updated"):
                return self._abort_with_context(parsed_query, "No pude restaurar el estado anterior de esa tarea.")
            parsed_query["_conversation_context"] = {
                **self._base_conversation_context(parsed_query, "task"),
                "task": {"id": result["task_id"], "name": result["task_title"]},
            }
            response = f"Listo, restaure el estado de '{result['task_title']}' a '{result['new_value']}'."
            self._set_audit_trace(
                parsed_query,
                user_query=user_query,
                response=response,
                action_status="executed",
                action_type="task_status_restore",
                affected_entity={"scope": "task", "id": result["task_id"], "name": result["task_title"]},
            )
            return response

        if undo_type == "restore_task_priority" and entity_id:
            result = self._restore_task_priority(int(entity_id), previous_value, None)
            if not result.get("updated"):
                return self._abort_with_context(parsed_query, "No pude restaurar la prioridad anterior de esa tarea.")
            parsed_query["_conversation_context"] = {
                **self._base_conversation_context(parsed_query, "task"),
                "task": {"id": result["task_id"], "name": result["task_title"]},
            }
            response = f"Listo, restaure la prioridad de '{result['task_title']}' a '{result['new_value']}'."
            self._set_audit_trace(
                parsed_query,
                user_query=user_query,
                response=response,
                action_status="executed",
                action_type="task_priority_restore",
                affected_entity={"scope": "task", "id": result["task_id"], "name": result["task_title"]},
            )
            return response

        if undo_type == "restore_task_note" and entity_id:
            result = self._restore_task_note(int(entity_id), previous_value)
            if not result.get("updated"):
                return self._abort_with_context(parsed_query, "No pude revertir la ultima nota de esa tarea.")
            parsed_query["_conversation_context"] = {
                **self._base_conversation_context(parsed_query, "task"),
                "task": {"id": result["task_id"], "name": result["task_title"]},
            }
            response = f"Listo: reverti la nota reciente en '{result['task_title']}'."
            self._set_audit_trace(
                parsed_query,
                user_query=user_query,
                response=response,
                action_status="executed",
                action_type="task_note_restore",
                affected_entity={"scope": "task", "id": result["task_id"], "name": result["task_title"]},
            )
            return response

        if undo_type == "restore_project_description" and entity_id:
            result = self._restore_project_description(int(entity_id), previous_value)
            if not result.get("updated"):
                return self._abort_with_context(parsed_query, "No pude revertir la ultima nota de ese proyecto.")
            parsed_query["_conversation_context"] = {
                **self._base_conversation_context(parsed_query, "project"),
                "project": {"id": result["project_id"], "name": result["project_name"]},
            }
            response = f"Listo: reverti la nota reciente en el proyecto '{result['project_name']}'."
            self._set_audit_trace(
                parsed_query,
                user_query=user_query,
                response=response,
                action_status="executed",
                action_type="project_note_restore",
                affected_entity={"scope": "project", "id": result["project_id"], "name": result["project_name"]},
            )
            return response

        return self._abort_with_context(
            parsed_query,
            f"Detecte la ultima accion sobre '{entity_name}', pero no la puedo deshacer de forma segura desde aca.",
        )

    def _resolve_other_context_candidate(self, context: dict) -> dict:
        current_scope = context.get("scope")
        current_item = context.get(current_scope) if current_scope in {"client", "project", "task"} else {}
        current_id = (current_item or {}).get("id")

        candidates: list[dict[str, Any]] = []
        clarification_candidates = context.get("clarification_candidates") or []
        if current_scope in {"client", "project", "task"}:
            for item in clarification_candidates:
                if item.get("scope") != current_scope:
                    continue
                if current_id is None or item.get("id") != current_id:
                    candidates.append(
                        {"scope": item.get("scope"), "id": item.get("id"), "name": item.get("name")}
                    )

        for item in context.get("recent_entities") or []:
            if item.get("scope") != current_scope:
                continue
            if current_id is None or item.get("id") != current_id:
                candidates.append(
                    {"scope": item.get("scope"), "id": item.get("id"), "name": item.get("name")}
                )

        if not candidates:
            fallback_candidates: list[dict[str, Any]] = []
            for item in context.get("recent_entities") or []:
                if current_id is not None and item.get("id") == current_id and item.get("scope") == current_scope:
                    continue
                if item.get("scope") in {"client", "project", "task"} and item.get("name"):
                    fallback_candidates.append(
                        {"scope": item.get("scope"), "id": item.get("id"), "name": item.get("name")}
                    )
            candidates = fallback_candidates

        unique: list[dict[str, Any]] = []
        seen: set[tuple[str | None, str | None]] = set()
        for item in candidates:
            key = (item.get("scope"), str(item.get("id")) if item.get("id") is not None else item.get("name"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        if not unique:
            return {"status": "none", "candidate": None, "candidates": []}
        if len(unique) > 1:
            return {"status": "ambiguous", "candidate": None, "candidates": unique[:4]}
        return {"status": "resolved", "candidate": unique[0], "candidates": unique[:1]}

    def _build_other_entity_action_prompt(self, context: dict, other_candidate: dict) -> str:
        last_action = (context or {}).get("last_action_trace") or {}
        if not last_action:
            return (
                f"Tomo '{other_candidate['name']}' como la otra entidad de esta conversacion. "
                "Decime la accion exacta que queres repetir ahi y la hago con seguridad."
            )

        proposal = self._describe_repeated_action(last_action, other_candidate)
        if proposal:
            return proposal
        return (
            f"Tomo '{other_candidate['name']}' como la otra entidad de esta conversacion. "
            "Decime la accion exacta que queres repetir ahi y la hago con seguridad."
        )

    @staticmethod
    def _describe_repeated_action(last_action: dict, other_candidate: dict) -> str | None:
        payload = last_action.get("payload") or {}
        undo_operation = last_action.get("undo_operation") or {}
        undo_type = undo_operation.get("type") or last_action.get("undo_type")
        proposal_text = str(payload.get("proposal_text", last_action.get("proposal_text")) or "").strip()
        if undo_type == "delete_task" and proposal_text:
            return (
                f"Entendido: tomo '{other_candidate['name']}' como la otra entidad. "
                f"Queres que tambien cree '{proposal_text}' ahi?"
            )
        if undo_type == "restore_task_note" and proposal_text:
            return (
                f"Entendido: tomo '{other_candidate['name']}' como la otra entidad. "
                f"Queres que tambien deje la nota '{proposal_text}' ahi?"
            )
        if undo_type == "restore_project_description" and proposal_text:
            return (
                f"Entendido: tomo '{other_candidate['name']}' como la otra entidad. "
                f"Queres que tambien agregue esa nota ahi?"
            )
        return None

    @staticmethod
    def _sync_synthetic_artifacts(target_query: dict, source_query: dict) -> None:
        for key in (
            "_conversation_context",
            "_audit_trace",
            "_resolved_references",
            "_response_snapshot",
            "_summary_scope",
        ):
            if key in source_query:
                target_query[key] = source_query[key]


def _normalize_vague_term(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))

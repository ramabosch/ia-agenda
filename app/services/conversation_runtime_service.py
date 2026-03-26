from __future__ import annotations

import time
from copy import deepcopy

from app.services.conversation_service import save_conversation
from app.services.hybrid_parser_service import parse_user_query_hybrid
from app.services.input_normalizer import normalize_input
from app.services.query_response_service import build_response_from_query
from app.services.structured_logger import log_conversation_turn

_FALLBACK_RESPONSE = "No entendí bien eso. ¿Podés reformularlo?"


def process_conversation_turn(
    user_query: str,
    *,
    conversation_context: dict | None = None,
    persist_log: bool = False,
) -> dict:
    t_start = time.monotonic()
    try:
        current_context = deepcopy(conversation_context) if isinstance(conversation_context, dict) else {}
        if not current_context:
            current_context = {"_new_session": True}
        elif not current_context.get("_isolated"):
            current_context["_new_session"] = True

        # Normalizar solo para parsing; el original se preserva para respuestas y DB
        normalized_query = normalize_input(user_query)
        parsed_query = parse_user_query_hybrid(normalized_query)

        response_text = build_response_from_query(
            parsed_query,
            user_query=user_query,
            conversation_context=current_context,
        )
        updated_context = deepcopy(parsed_query.get("_conversation_context") or {})
        updated_context = _merge_short_term_context(
            previous_context=current_context,
            updated_context=updated_context,
            parsed_query=parsed_query,
        )
        audit_trace = deepcopy(parsed_query.get("_audit_trace") or {})
        resolved_references = deepcopy(parsed_query.get("_resolved_references") or {})

        if persist_log:
            save_conversation(
                user_input=user_query,
                parsed_intent=str(parsed_query),
                response_output=response_text,
            )

        latency_ms = (time.monotonic() - t_start) * 1000
        log_conversation_turn(
            intent=parsed_query.get("intent"),
            parser_source=parsed_query.get("_parser_source"),
            action_status=(audit_trace.get("action_status") or "read"),
            latency_ms=latency_ms,
        )

        return {
            "user_query": user_query,
            "response_text": response_text,
            "parsed_query": parsed_query,
            "conversation_context": updated_context,
            "audit_trace": audit_trace,
            "resolved_references": resolved_references,
        }

    except Exception:
        latency_ms = (time.monotonic() - t_start) * 1000
        log_conversation_turn(
            intent="unknown",
            parser_source="error",
            action_status="error",
            latency_ms=latency_ms,
        )
        return {
            "user_query": user_query,
            "response_text": _FALLBACK_RESPONSE,
            "parsed_query": {},
            "conversation_context": conversation_context or {},
            "audit_trace": {},
            "resolved_references": {},
        }


def _merge_short_term_context(
    *,
    previous_context: dict,
    updated_context: dict,
    parsed_query: dict,
) -> dict:
    if not isinstance(updated_context, dict) or not updated_context.get("_isolated"):
        return updated_context

    previous_recent = list((previous_context or {}).get("recent_entities") or [])
    collected_recent = _collect_recent_entities(updated_context, parsed_query)
    merged_recent: list[dict] = []
    seen: set[tuple[str | None, str | None]] = set()

    for item in collected_recent + previous_recent:
        scope = item.get("scope")
        identifier = str(item.get("id")) if item.get("id") is not None else item.get("name")
        key = (scope, identifier)
        if not scope or not identifier or key in seen:
            continue
        seen.add(key)
        merged_recent.append(
            {
                "scope": scope,
                "id": item.get("id"),
                "name": item.get("name"),
            }
        )
        if len(merged_recent) >= 8:
            break

    if merged_recent:
        updated_context["recent_entities"] = merged_recent
    elif "recent_entities" in updated_context:
        updated_context.pop("recent_entities", None)

    if not updated_context.get("clarification_candidates") and previous_context.get("clarification_candidates"):
        updated_context["clarification_candidates"] = deepcopy(previous_context.get("clarification_candidates"))
    if not updated_context.get("clarification_expected_scope") and previous_context.get("clarification_expected_scope"):
        updated_context["clarification_expected_scope"] = previous_context.get("clarification_expected_scope")
    if not updated_context.get("candidate_entities") and previous_context.get("candidate_entities"):
        updated_context["candidate_entities"] = deepcopy(previous_context.get("candidate_entities"))
    if not updated_context.get("candidate_entity_type") and previous_context.get("candidate_entity_type"):
        updated_context["candidate_entity_type"] = previous_context.get("candidate_entity_type")
    if not updated_context.get("candidate_source") and previous_context.get("candidate_source"):
        updated_context["candidate_source"] = previous_context.get("candidate_source")
    if not updated_context.get("shown_order") and previous_context.get("shown_order"):
        updated_context["shown_order"] = deepcopy(previous_context.get("shown_order"))
    if not updated_context.get("channel_identity") and previous_context.get("channel_identity"):
        updated_context["channel_identity"] = deepcopy(previous_context.get("channel_identity"))
    if not updated_context.get("assistant_memory") and previous_context.get("assistant_memory"):
        updated_context["assistant_memory"] = deepcopy(previous_context.get("assistant_memory"))
    updated_context.pop("_new_session", None)

    last_action_trace = _build_last_action_trace(parsed_query)
    if last_action_trace:
        updated_context["last_action_trace"] = last_action_trace
    elif _should_clear_last_action_trace(parsed_query):
        updated_context.pop("last_action_trace", None)
    elif "last_action_trace" in updated_context or previous_context.get("last_action_trace"):
        updated_context["last_action_trace"] = deepcopy(previous_context.get("last_action_trace"))

    return updated_context


def _collect_recent_entities(updated_context: dict, parsed_query: dict) -> list[dict]:
    recent_entities: list[dict] = []
    for scope in ("task", "project", "client"):
        item = updated_context.get(scope) or {}
        if isinstance(item, dict) and item.get("name"):
            recent_entities.append({"scope": scope, "id": item.get("id"), "name": item.get("name")})

    resolved_references = parsed_query.get("_resolved_references") or {}
    for scope in ("task", "project", "client"):
        resolved = (resolved_references.get(scope) or {}).get("resolved") or {}
        if resolved.get("name"):
            recent_entities.append({"scope": scope, "id": resolved.get("id"), "name": resolved.get("name")})

    affected_entity = (parsed_query.get("_audit_trace") or {}).get("affected_entity") or {}
    if affected_entity.get("scope") in {"task", "project", "client"} and affected_entity.get("name"):
        recent_entities.append(
            {
                "scope": affected_entity.get("scope"),
                "id": affected_entity.get("id"),
                "name": affected_entity.get("name"),
            }
        )

    return recent_entities


def _build_last_action_trace(parsed_query: dict) -> dict | None:
    trace = parsed_query.get("_audit_trace") or {}
    if trace.get("action_status") != "executed":
        return None

    action_type = trace.get("action_type")
    affected_entity = trace.get("affected_entity") or {}
    creation_result = parsed_query.get("_creation_result") or {}
    update_result = parsed_query.get("_update_result") or {}

    if action_type in {"agenda_event", "agenda_reminder"} and affected_entity.get("id"):
        return _make_last_action_trace(
            action_type=action_type,
            scope="agenda",
            entity_id=affected_entity.get("id"),
            entity_name=affected_entity.get("name"),
            undo_type="delete_agenda_item",
        )

    if action_type == "create_task" and affected_entity.get("id"):
        return _make_last_action_trace(
            action_type=action_type,
            scope="task",
            entity_id=affected_entity.get("id"),
            entity_name=affected_entity.get("name"),
            undo_type="delete_task",
            proposal_text=creation_result.get("task_title"),
        )

    if action_type == "project_note" and update_result.get("project_id"):
        return _make_last_action_trace(
            action_type=action_type,
            scope="project",
            entity_id=update_result.get("project_id"),
            entity_name=update_result.get("project_name"),
            undo_type="restore_project_description",
            previous_value=update_result.get("old_value"),
            proposal_text=parsed_query.get("last_note"),
        )

    if action_type in {"last_note", "task_note"} and update_result.get("field") == "last_note" and update_result.get("task_id"):
        return _make_last_action_trace(
            action_type="task_note",
            scope="task",
            entity_id=update_result.get("task_id"),
            entity_name=update_result.get("task_title"),
            undo_type="restore_task_note",
            previous_value=update_result.get("old_value"),
            proposal_text=update_result.get("new_value"),
        )

    if action_type == "status" and update_result.get("task_id"):
        return _make_last_action_trace(
            action_type="status",
            scope="task",
            entity_id=update_result.get("task_id"),
            entity_name=update_result.get("task_title"),
            undo_type="restore_task_status",
            previous_value=update_result.get("old_value"),
            proposal_text=update_result.get("new_value"),
        )

    if action_type == "priority" and update_result.get("task_id"):
        return _make_last_action_trace(
            action_type="priority",
            scope="task",
            entity_id=update_result.get("task_id"),
            entity_name=update_result.get("task_title"),
            undo_type="restore_task_priority",
            previous_value=update_result.get("old_value"),
            proposal_text=update_result.get("new_value"),
        )

    return None


def _make_last_action_trace(
    *,
    action_type: str,
    scope: str,
    entity_id,
    entity_name: str | None,
    undo_type: str,
    previous_value=None,
    proposal_text: str | None = None,
) -> dict:
    trace = {
        "action_type": action_type,
        "scope": scope,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "entity": {
            "scope": scope,
            "id": entity_id,
            "name": entity_name,
        },
        "undo_type": undo_type,
        "undo_operation": {
            "type": undo_type,
            "scope": scope,
            "entity_id": entity_id,
        },
        "payload": {},
    }
    if previous_value is not None:
        trace["previous_value"] = previous_value
        trace["payload"]["previous_value"] = previous_value
    if proposal_text:
        trace["proposal_text"] = proposal_text
        trace["payload"]["proposal_text"] = proposal_text
    if not trace["payload"]:
        trace.pop("payload", None)
    return trace


def _should_clear_last_action_trace(parsed_query: dict) -> bool:
    trace = parsed_query.get("_audit_trace") or {}
    if trace.get("action_status") != "executed":
        return False
    return trace.get("action_type") in {
        "agenda_delete",
        "task_delete",
        "task_note_restore",
        "project_note_restore",
        "task_status_restore",
        "task_priority_restore",
    }

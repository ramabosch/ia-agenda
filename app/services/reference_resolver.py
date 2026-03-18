import ast
import re
from difflib import SequenceMatcher
from typing import Any

from app.services.client_service import get_all_clients
from app.services.conversation_service import get_last_conversation
from app.services.project_service import get_all_projects, get_projects_by_client_id
from app.services.task_service import (
    get_all_tasks,
    get_tasks_by_client_id,
    get_tasks_by_project_id,
)
from app.services.text_normalizer_service import normalize_entity_text


LOW_CONFIDENCE = 0.70
AMBIGUITY_DELTA = 0.08
UPDATE_LOW_CONFIDENCE = 0.90
UPDATE_AMBIGUITY_DELTA = 0.05

CLIENT_CONTEXT_HINTS = {
    "este cliente",
    "ese cliente",
    "cliente actual",
    "sus proyectos",
}
PROJECT_CONTEXT_HINTS = {
    "este proyecto",
    "ese proyecto",
    "proyecto actual",
    "ahi",
}
TASK_CONTEXT_HINTS = {
    "esta tarea",
    "esa tarea",
    "la tarea",
    "eso",
    "ponelo",
    "ponela",
    "marcalo",
    "marcala",
    "cerralo",
    "cerrala",
    "agregale",
    "subile",
}
GENERIC_HINTS = {"cliente", "proyecto", "tarea", "eso", "esto", "algo", "lo del cliente"}
FOLLOW_UP_MARKERS = (
    " y ",
    "ponelo",
    "ponela",
    "marcalo",
    "marcala",
    "cerralo",
    "cerrala",
    "agregale",
    "subile",
    "ahi",
    "eso",
    "sus proyectos",
    "la del",
    "la de",
)


def resolve_references(
    parsed_query: dict[str, Any],
    user_query: str | None = None,
    conversation_context: dict[str, Any] | None = None,
    *,
    allow_global_context: bool = False,
) -> dict[str, Any]:
    context = _normalize_context(conversation_context)
    context_source = "current" if context else "none"
    entity_hint = parsed_query.get("entity_hint")
    intent = parsed_query.get("intent")

    if not context and allow_global_context:
        context = _load_conversation_context()
        context_source = "global" if context else "none"

    follow_up_mode = _is_follow_up_query(user_query)
    is_update_request = _is_update_intent(parsed_query.get("intent"))
    missing_safe_context = follow_up_mode and _query_requires_context(user_query) and not context

    client_result = _resolve_client_reference(
        _raw_reference_for_scope(parsed_query, "client", entity_hint, context),
        user_query=user_query,
        context=context,
        follow_up_mode=follow_up_mode,
        is_update_request=is_update_request,
    )

    if client_result["resolved"] is None and follow_up_mode and context.get("client"):
        client_result = _build_context_result("client", context["client"])

    client_id = _resolved_id(client_result)
    project_result = _resolve_project_reference(
        _raw_reference_for_scope(parsed_query, "project", entity_hint, context),
        client_id=client_id,
        user_query=user_query,
        context=context,
        follow_up_mode=follow_up_mode,
        is_update_request=is_update_request,
    )

    if project_result["resolved"] is None and follow_up_mode and context.get("project"):
        project_result = _build_context_result("project", context["project"])

    project_id = _resolved_id(project_result)
    if client_id is None and project_result["resolved"] is not None and project_result["resolved"].get("entity"):
        project_entity = project_result["resolved"]["entity"]
        client_result = _build_derived_result("client", project_entity.client)
        client_id = project_entity.client.id

    task_result = _resolve_task_reference(
        _raw_reference_for_scope(parsed_query, "task", entity_hint, context),
        client_id=None if intent == "clarify_entity_reference" else client_id,
        project_id=None if intent == "clarify_entity_reference" else project_id,
        user_query=user_query,
        context=context,
        follow_up_mode=follow_up_mode,
        is_update_request=is_update_request,
    )

    if task_result["resolved"] is None and follow_up_mode and context.get("task") and _query_allows_task_context(user_query):
        task_result = _build_context_result("task", context["task"])

    if task_result["resolved"] is not None and task_result["resolved"].get("entity"):
        task_entity = task_result["resolved"]["entity"]

        if project_result["resolved"] is None:
            project_result = _build_derived_result("project", task_entity.project)
            project_id = task_entity.project.id

        if client_result["resolved"] is None and task_entity.project and task_entity.project.client:
            client_result = _build_derived_result("client", task_entity.project.client)
            client_id = task_entity.project.client.id

    scope = _infer_scope(client_result, project_result, task_result)
    confidence = max(
        client_result["confidence"],
        project_result["confidence"],
        task_result["confidence"],
        0.0,
    )
    ambiguous = any(result["ambiguous"] for result in (client_result, project_result, task_result))
    candidate_types = [
        scope
        for scope, result in (("client", client_result), ("project", project_result), ("task", task_result))
        if result["matches"] and result.get("source") != "derived"
    ]
    clarification_candidates = _build_clarification_candidates(client_result, project_result, task_result)
    clarification_needed, clarification_reason = _detect_clarification_need(
        intent=intent,
        entity_hint=entity_hint,
        context=context,
        missing_safe_context=missing_safe_context,
        client_result=client_result,
        project_result=project_result,
        task_result=task_result,
    )

    serialized_client = _serialize_result(client_result)
    serialized_project = _serialize_result(project_result)
    serialized_task = _serialize_result(task_result)

    return {
        "scope": scope,
        "source": _infer_source([serialized_client, serialized_project, serialized_task]),
        "confidence": round(confidence, 3),
        "ambiguous": ambiguous,
        "clarification_needed": clarification_needed,
        "clarification_reason": clarification_reason,
        "candidate_types": candidate_types,
        "clarification_candidates": clarification_candidates,
        "client": serialized_client,
        "project": serialized_project,
        "task": serialized_task,
        "matches": {
            "client": client_result["matches"],
            "project": project_result["matches"],
            "task": task_result["matches"],
        },
        "candidates": {
            "client": client_result["matches"],
            "project": project_result["matches"],
            "task": task_result["matches"],
        },
        "context": context,
        "context_source": context_source,
        "context_isolated": bool(context.get("_isolated")),
        "security_blocked": missing_safe_context,
        "security_reason": "missing_isolated_context" if missing_safe_context else None,
        "used_context": {
            "client": serialized_client["source"] == "contextual",
            "project": serialized_project["source"] == "contextual",
            "task": serialized_task["source"] == "contextual",
        },
        "used_context_to_disambiguate": bool(context) and not clarification_needed and any(
            item["source"] in {"contextual", "mixed"} for item in (serialized_client, serialized_project, serialized_task)
        ) or (
            bool(context)
            and intent == "clarify_entity_reference"
            and ((entity_hint or "").strip().lower() in GENERIC_HINTS or normalize_entity_text(entity_hint) in GENERIC_HINTS)
            and not clarification_needed
            and scope != "none"
        ),
    }


def _resolve_client_reference(
    raw_name: str | None,
    *,
    user_query: str | None,
    context: dict[str, Any],
    follow_up_mode: bool,
    is_update_request: bool,
) -> dict[str, Any]:
    name = _coerce_context_reference(raw_name, "client", user_query, context)
    if not name:
        return _empty_result("client", raw_name)

    result = _rank_candidates(
        "client",
        raw_name=name,
        candidates=get_all_clients(),
        label_getter=lambda item: item.name,
        is_update_request=is_update_request,
    )
    if result["resolved"] is not None:
        result["source"] = _resolve_source(raw_name, name, follow_up_mode, context.get("client"))
    return result


def _resolve_project_reference(
    raw_name: str | None,
    *,
    client_id: int | None,
    user_query: str | None,
    context: dict[str, Any],
    follow_up_mode: bool,
    is_update_request: bool,
) -> dict[str, Any]:
    name = _coerce_context_reference(raw_name, "project", user_query, context)
    if not name:
        return _empty_result("project", raw_name)

    candidates = get_projects_by_client_id(client_id) if client_id is not None else get_all_projects()
    result = _rank_candidates(
        "project",
        raw_name=name,
        candidates=candidates,
        label_getter=lambda item: item.name,
        is_update_request=is_update_request,
    )
    if result["resolved"] is not None:
        result["source"] = _resolve_source(raw_name, name, follow_up_mode, context.get("project"))
    return result


def _resolve_task_reference(
    raw_name: str | None,
    *,
    client_id: int | None,
    project_id: int | None,
    user_query: str | None,
    context: dict[str, Any],
    follow_up_mode: bool,
    is_update_request: bool,
) -> dict[str, Any]:
    name = _coerce_context_reference(raw_name, "task", user_query, context)
    if not name:
        return _empty_result("task", raw_name)

    if project_id is not None:
        candidates = get_tasks_by_project_id(project_id)
    elif client_id is not None:
        candidates = get_tasks_by_client_id(client_id)
    else:
        candidates = get_all_tasks()

    result = _rank_candidates(
        "task",
        raw_name=name,
        candidates=candidates,
        label_getter=lambda item: item.title,
        is_update_request=is_update_request,
    )
    if result["resolved"] is not None:
        result["source"] = _resolve_source(raw_name, name, follow_up_mode, context.get("task"))
    return result


def _rank_candidates(scope: str, raw_name: str, candidates: list[Any], label_getter, *, is_update_request: bool) -> dict[str, Any]:
    normalized_query = normalize_entity_text(raw_name)
    if not normalized_query:
        return _empty_result(scope, raw_name)

    threshold = _confidence_threshold(scope, is_update_request)
    ambiguity_delta = UPDATE_AMBIGUITY_DELTA if is_update_request and scope == "task" else AMBIGUITY_DELTA

    scored: list[dict[str, Any]] = []
    for candidate in candidates:
        label = label_getter(candidate)
        normalized_label = normalize_entity_text(label)
        score = _score_candidate(normalized_query, normalized_label)
        if score < threshold:
            continue

        scored.append(
            {
                "id": candidate.id,
                "name": label,
                "normalized": normalized_label,
                "confidence": round(score, 3),
                "scope": scope,
                "entity": candidate,
            }
        )

    scored.sort(key=lambda item: (-item["confidence"], len(item["normalized"]), item["name"]))
    if not scored:
        return _empty_result(scope, raw_name, normalized=normalized_query)

    best = scored[0]
    second = scored[1] if len(scored) > 1 else None
    ambiguous = bool(
        second
        and best["confidence"] < 0.98
        and second["confidence"] >= threshold
        and (best["confidence"] - second["confidence"]) <= ambiguity_delta
    )

    return {
        "scope": scope,
        "input": raw_name,
        "normalized": normalized_query,
        "confidence": best["confidence"],
        "ambiguous": ambiguous,
        "source": "explicit",
        "resolved": None if ambiguous else best,
        "matches": [_strip_entity(match) for match in scored[:5]],
    }


def _score_candidate(query: str, label: str) -> float:
    if not query or not label:
        return 0.0
    if query == label:
        return 1.0
    if label.startswith(query):
        return 0.93
    if _query_tokens_subset(query, label):
        return 0.91
    if query.startswith(label):
        return 0.89
    if query in label:
        return 0.85
    ratio = SequenceMatcher(None, query, label).ratio()
    return ratio if ratio >= LOW_CONFIDENCE else 0.0


def _query_tokens_subset(query: str, label: str) -> bool:
    query_tokens = {token for token in re.split(r"\s+", query) if len(token) >= 4}
    label_tokens = {token for token in re.split(r"\s+", label) if token}
    return bool(query_tokens) and query_tokens.issubset(label_tokens)


def _confidence_threshold(scope: str, is_update_request: bool) -> float:
    if is_update_request and scope == "task":
        return UPDATE_LOW_CONFIDENCE
    return LOW_CONFIDENCE


def _coerce_context_reference(
    raw_name: str | None,
    scope: str,
    user_query: str | None,
    context: dict[str, Any],
) -> str | None:
    if raw_name and not _looks_like_context_reference(raw_name, scope):
        return raw_name

    if raw_name and _looks_like_context_reference(raw_name, scope):
        contextual_name = context.get(scope, {}).get("name")
        if contextual_name:
            return contextual_name
        return None

    if user_query:
        raw_query = user_query.strip().lower()
        if scope == "client" and any(hint in raw_query for hint in CLIENT_CONTEXT_HINTS):
            return context.get("client", {}).get("name")
        if scope == "project" and any(hint in raw_query for hint in PROJECT_CONTEXT_HINTS):
            return context.get("project", {}).get("name")
        if scope == "task" and any(hint in raw_query for hint in TASK_CONTEXT_HINTS):
            return context.get("task", {}).get("name")

    return raw_name


def _raw_reference_for_scope(
    parsed_query: dict[str, Any],
    scope: str,
    entity_hint: str | None,
    context: dict[str, Any],
) -> str | None:
    explicit = parsed_query.get(f"{scope}_name")
    if explicit:
        return explicit
    if parsed_query.get("intent") == "clarify_entity_reference":
        raw_hint = (entity_hint or "").strip().lower()
        normalized_hint = normalize_entity_text(entity_hint)
        if (raw_hint in GENERIC_HINTS or normalized_hint in GENERIC_HINTS) and context.get("scope") == scope and context.get(scope, {}).get("name"):
            return context[scope]["name"]
        return entity_hint
    return None


def _looks_like_context_reference(raw_name: str, scope: str) -> bool:
    raw_value = raw_name.strip().lower()
    if scope == "client":
        return raw_value in CLIENT_CONTEXT_HINTS
    if scope == "project":
        return raw_value in PROJECT_CONTEXT_HINTS
    if scope == "task":
        return raw_value in TASK_CONTEXT_HINTS
    return False


def _query_allows_task_context(user_query: str | None) -> bool:
    if not user_query:
        return False
    raw_query = user_query.strip().lower()
    return any(
        marker in raw_query
        for marker in TASK_CONTEXT_HINTS | {"la del", "la de", "que sigue", "proximo paso", "hacer ahora"}
    )


def _is_follow_up_query(user_query: str | None) -> bool:
    if not user_query:
        return False
    raw_query = f" {user_query.strip().lower()} "
    return any(marker in raw_query for marker in FOLLOW_UP_MARKERS)


def _query_requires_context(user_query: str | None) -> bool:
    if not user_query:
        return False
    raw_query = f" {user_query.strip().lower()} "
    return any(marker in raw_query for marker in FOLLOW_UP_MARKERS)


def _normalize_context(conversation_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(conversation_context, dict):
        return {}
    if not conversation_context.get("_isolated"):
        return {}
    return conversation_context


def _load_conversation_context() -> dict[str, Any]:
    log = get_last_conversation()
    if not log or not log.parsed_intent:
        return {}

    try:
        parsed = ast.literal_eval(log.parsed_intent)
    except Exception:
        return {}

    if not isinstance(parsed, dict):
        return {}

    stored_context = parsed.get("_conversation_context")
    if isinstance(stored_context, dict) and stored_context:
        return stored_context

    resolved = parsed.get("_resolved_references")
    if not isinstance(resolved, dict):
        return {}

    context: dict[str, Any] = {
        "last_intent": parsed.get("intent"),
    }
    for scope in ("client", "project", "task"):
        item = resolved.get(scope)
        if isinstance(item, dict) and isinstance(item.get("resolved"), dict):
            context[scope] = {
                "id": item["resolved"].get("id"),
                "name": item["resolved"].get("name"),
            }
    return context


def _build_context_result(scope: str, context_item: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope": scope,
        "input": None,
        "normalized": normalize_entity_text(context_item["name"]),
        "confidence": 0.96,
        "ambiguous": False,
        "source": "contextual",
        "resolved": {
            "id": context_item["id"],
            "name": context_item["name"],
            "normalized": normalize_entity_text(context_item["name"]),
            "confidence": 0.96,
            "scope": scope,
            "entity": None,
        },
        "matches": [
            {
                "id": context_item["id"],
                "name": context_item["name"],
                "confidence": 0.96,
                "scope": scope,
            }
        ],
    }


def _build_derived_result(scope: str, entity: Any) -> dict[str, Any]:
    if entity is None:
        return _empty_result(scope, None)

    label = entity.title if hasattr(entity, "title") else entity.name
    return {
        "scope": scope,
        "input": None,
        "normalized": normalize_entity_text(label),
        "confidence": 0.99,
        "ambiguous": False,
        "source": "derived",
        "resolved": {
            "id": entity.id,
            "name": label,
            "normalized": normalize_entity_text(label),
            "confidence": 0.99,
            "scope": scope,
            "entity": entity,
        },
        "matches": [{"id": entity.id, "name": label, "confidence": 0.99, "scope": scope}],
    }


def _empty_result(scope: str, raw_name: str | None, normalized: str | None = None) -> dict[str, Any]:
    return {
        "scope": scope,
        "input": raw_name,
        "normalized": normalized or (normalize_entity_text(raw_name) if raw_name else None),
        "confidence": 0.0,
        "ambiguous": False,
        "source": "none",
        "resolved": None,
        "matches": [],
    }


def _infer_scope(client_result: dict[str, Any], project_result: dict[str, Any], task_result: dict[str, Any]) -> str:
    if task_result["resolved"] is not None:
        return "task"
    if project_result["resolved"] is not None:
        return "project"
    if client_result["resolved"] is not None:
        return "client"
    return "none"


def _resolved_id(result: dict[str, Any]) -> int | None:
    if result["resolved"] is None:
        return None
    return result["resolved"]["id"]


def _strip_entity(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "confidence": item["confidence"],
        "scope": item["scope"],
    }


def _serialize_result(result: dict[str, Any]) -> dict[str, Any]:
    resolved = result["resolved"]
    return {
        "input": result["input"],
        "normalized": result["normalized"],
        "confidence": result["confidence"],
        "ambiguous": result["ambiguous"],
        "scope": result["scope"],
        "source": result.get("source", "none"),
        "resolved": _strip_entity(resolved) if resolved else None,
        "matches": result["matches"],
    }


def _build_clarification_candidates(*results: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for result in results:
        if result.get("source") == "derived":
            continue
        for match in result["matches"][:3]:
            key = (match["scope"], match["id"])
            if key in seen:
                continue
            seen.add(key)
            candidates.append(match)
    candidates.sort(key=lambda item: (-item["confidence"], item["scope"], item["name"]))
    return candidates[:6]


def _detect_clarification_need(
    *,
    intent: str | None,
    entity_hint: str | None,
    context: dict[str, Any],
    missing_safe_context: bool,
    client_result: dict[str, Any],
    project_result: dict[str, Any],
    task_result: dict[str, Any],
) -> tuple[bool, str | None]:
    results = {"client": client_result, "project": project_result, "task": task_result}
    matched_scopes = [scope for scope, result in results.items() if result["matches"] and result.get("source") != "derived"]
    resolved_scopes = [scope for scope, result in results.items() if result["resolved"] is not None and result.get("source") != "derived"]

    if missing_safe_context:
        return True, "missing_context"

    if any(result["ambiguous"] for result in results.values()):
        return True, "ambiguous_matches"

    if intent == "clarify_entity_reference":
        raw_hint = (entity_hint or "").strip().lower()
        normalized_hint = normalize_entity_text(entity_hint)
        if not normalized_hint and raw_hint not in GENERIC_HINTS:
            return True, "generic_request"
        if (raw_hint in GENERIC_HINTS or normalized_hint in GENERIC_HINTS) and not resolved_scopes:
            return True, "generic_request"
        if len(matched_scopes) > 1 or len(resolved_scopes) > 1:
            return True, "cross_scope_ambiguity"
        if not matched_scopes:
            return True, "missing_entity"

    return False, None


def _resolve_source(raw_name: str | None, resolved_name: str, follow_up_mode: bool, context_item: dict[str, Any] | None) -> str:
    if raw_name and raw_name.strip().lower() == resolved_name.strip().lower():
        return "explicit"
    if context_item and follow_up_mode:
        return "mixed"
    return "explicit"


def _infer_source(results: list[dict[str, Any]]) -> str:
    sources = {item["source"] for item in results if item.get("resolved")}
    if not sources:
        return "none"
    if len(sources) == 1:
        return next(iter(sources))
    return "mixed"


def _is_update_intent(intent: str | None) -> bool:
    return intent in {
        "update_task_status",
        "update_task_priority",
        "add_task_note",
        "update_task_next_action",
        "update_task_last_note",
        "complete_task_by_name",
        "update_task_priority_by_name",
        "add_task_update_by_name",
    }

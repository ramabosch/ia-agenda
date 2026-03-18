import ast
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

CLIENT_CONTEXT_HINTS = {"este cliente", "ese cliente", "cliente actual"}
PROJECT_CONTEXT_HINTS = {"este proyecto", "ese proyecto", "proyecto actual"}
TASK_CONTEXT_HINTS = {"esta tarea", "esa tarea", "tarea actual"}


def resolve_references(parsed_query: dict[str, Any], user_query: str | None = None) -> dict[str, Any]:
    context = _load_conversation_context()

    client_result = _resolve_client_reference(
        parsed_query.get("client_name"),
        user_query=user_query,
        context=context,
    )

    client_id = _resolved_id(client_result)
    project_result = _resolve_project_reference(
        parsed_query.get("project_name"),
        client_id=client_id,
        user_query=user_query,
        context=context,
    )

    project_id = _resolved_id(project_result)
    if client_id is None and project_result["resolved"] is not None:
        project_entity = project_result["resolved"]["entity"]
        client_result = _build_derived_result("client", project_entity.client)
        client_id = project_entity.client.id

    task_result = _resolve_task_reference(
        parsed_query.get("task_name"),
        client_id=client_id,
        project_id=project_id,
        user_query=user_query,
        context=context,
    )

    if task_result["resolved"] is not None:
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

    return {
        "scope": scope,
        "confidence": round(confidence, 3),
        "ambiguous": ambiguous,
        "client": _serialize_result(client_result),
        "project": _serialize_result(project_result),
        "task": _serialize_result(task_result),
        "matches": {
            "client": client_result["matches"],
            "project": project_result["matches"],
            "task": task_result["matches"],
        },
        "context": context,
    }


def _resolve_client_reference(
    raw_name: str | None,
    *,
    user_query: str | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    name = _coerce_context_reference(raw_name, "client", user_query, context)
    if not name:
        return _empty_result("client", raw_name)

    candidates = get_all_clients()
    return _rank_candidates("client", raw_name=name, candidates=candidates, label_getter=lambda item: item.name)


def _resolve_project_reference(
    raw_name: str | None,
    *,
    client_id: int | None,
    user_query: str | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    name = _coerce_context_reference(raw_name, "project", user_query, context)
    if not name:
        return _empty_result("project", raw_name)

    candidates = get_projects_by_client_id(client_id) if client_id is not None else get_all_projects()
    return _rank_candidates("project", raw_name=name, candidates=candidates, label_getter=lambda item: item.name)


def _resolve_task_reference(
    raw_name: str | None,
    *,
    client_id: int | None,
    project_id: int | None,
    user_query: str | None,
    context: dict[str, Any],
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

    return _rank_candidates("task", raw_name=name, candidates=candidates, label_getter=lambda item: item.title)


def _rank_candidates(scope: str, raw_name: str, candidates: list[Any], label_getter) -> dict[str, Any]:
    normalized_query = normalize_entity_text(raw_name)
    if not normalized_query:
        return _empty_result(scope, raw_name)

    scored: list[dict[str, Any]] = []
    for candidate in candidates:
        label = label_getter(candidate)
        normalized_label = normalize_entity_text(label)
        score = _score_candidate(normalized_query, normalized_label)

        if score < LOW_CONFIDENCE:
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
        and second["confidence"] >= LOW_CONFIDENCE
        and (best["confidence"] - second["confidence"]) <= AMBIGUITY_DELTA
    )

    return {
        "scope": scope,
        "input": raw_name,
        "normalized": normalized_query,
        "confidence": best["confidence"],
        "ambiguous": ambiguous,
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

    if query.startswith(label):
        return 0.89

    if query in label:
        return 0.85

    ratio = SequenceMatcher(None, query, label).ratio()
    return ratio if ratio >= LOW_CONFIDENCE else 0.0


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

    if user_query:
        raw_query = user_query.strip().lower()
        if scope == "client" and any(hint in raw_query for hint in CLIENT_CONTEXT_HINTS):
            return context.get("client", {}).get("name")
        if scope == "project" and any(hint in raw_query for hint in PROJECT_CONTEXT_HINTS):
            return context.get("project", {}).get("name")
        if scope == "task" and any(hint in raw_query for hint in TASK_CONTEXT_HINTS):
            return context.get("task", {}).get("name")

    return raw_name


def _looks_like_context_reference(raw_name: str, scope: str) -> bool:
    normalized = raw_name.strip().lower()
    if scope == "client":
        return normalized in CLIENT_CONTEXT_HINTS
    if scope == "project":
        return normalized in PROJECT_CONTEXT_HINTS
    if scope == "task":
        return normalized in TASK_CONTEXT_HINTS
    return False


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

    resolved = parsed.get("_resolved_references")
    if not isinstance(resolved, dict):
        return {}

    context: dict[str, Any] = {}
    for scope in ("client", "project", "task"):
        item = resolved.get(scope)
        if isinstance(item, dict) and isinstance(item.get("resolved"), dict):
            context[scope] = {
                "id": item["resolved"].get("id"),
                "name": item["resolved"].get("name"),
            }
    return context


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
        "resolved": _strip_entity(resolved) if resolved else None,
        "matches": result["matches"],
    }

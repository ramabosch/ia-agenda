from app.config import USE_LLM_PARSER
from app.services.llm_parser_service import parse_actions_with_llm
from app.services.query_parser_service import parse_user_query as parse_user_query_rules
from app.services.structured_logger import log_parser_decision

EXECUTIVE_INTENTS = {
    "get_active_projects",
    "get_blocked_items_summary",
    "get_today_priority_summary",
    "get_overdue_or_stuck_summary",
    "get_client_attention_summary",
    "get_project_attention_summary",
    "get_general_executive_summary",
    "get_operational_friction_summary",
    "get_operational_recommendation",
    "get_followup_focus_summary",
    "get_recommendation_explanation",
    "get_filtered_context_summary",
    "get_rephrased_summary",
    "get_client_facing_summary",
    "get_next_actions_summary",
    "get_missing_next_actions_summary",
    "get_followup_needed_summary",
    "get_push_today_summary",
    "get_due_tasks_summary",
    "get_overdue_tasks_summary",
    "get_missing_due_date_summary",
    "create_agenda_item",
    "get_agenda_items_summary",
    "update_agenda_item",
    "delete_agenda_item",
}

CLARIFICATION_INTENTS = {
    "clarify_entity_reference",
}

AUDIT_INTENTS = {
    "get_audit_trace_summary",
}

SUMMARY_INTENTS = {
    "get_operational_summary",
    "compound_query",
    "expand_context",
}


def parse_query_with_llm(query: str) -> dict | None:
    return _pick_primary_action(parse_actions_with_llm(query))


def parse_user_query_hybrid(query: str) -> dict:
    rules_result = parse_user_query_rules(query)
    rules_intent = rules_result.get("intent", "unknown")

    if not USE_LLM_PARSER:
        rules_result["_parser_source"] = "rules"
        return rules_result

    llm_actions = parse_actions_with_llm(query)
    llm_result = _pick_primary_action(llm_actions)
    llm_intent = (llm_result or {}).get("intent", "unknown")

    if llm_result is None:
        # LLM no devolvió resultado utilizable
        log_parser_decision(
            decision="rules_fallback",
            reason="llm_no_result",
            query_preview=query,
        )
        rules_result["_parser_source"] = "rules"
        return rules_result

    if llm_intent in (None, "", "unknown"):
        log_parser_decision(
            decision="rules_fallback",
            reason="llm_unknown_intent",
            query_preview=query,
        )
        rules_result["_parser_source"] = "rules"
        rules_result["_parser_decision"] = "llm_rejected"
        return rules_result

    if _should_prefer_rules(query, rules_result, llm_result):
        rules_result["_parser_source"] = "rules"
        if llm_intent not in (None, "", "unknown"):
            rules_result["_parser_decision"] = "rules_over_llm"
        log_parser_decision(
            decision="rules_preferred",
            reason="rules_have_better_fields",
            query_preview=query,
        )
        return rules_result

    llm_result["_actions"] = llm_actions
    llm_result["_parser_decision"] = "llm_accepted"
    return llm_result


def _pick_primary_action(actions: list[dict] | None) -> dict | None:
    if not actions:
        return None
    for action in actions:
        if action.get("intent") not in (None, "", "unknown"):
            return dict(action)
    return dict(actions[0]) if actions else None


def _should_prefer_rules(query: str, rules_result: dict, llm_result: dict | None) -> bool:
    rules_intent = rules_result.get("intent", "unknown")
    llm_intent = (llm_result or {}).get("intent", "unknown")
    normalized_query = query.strip().lower()

    if rules_intent not in (None, "", "unknown"):
        if _rules_have_more_useful_fields(rules_result, llm_result):
            return True
        if rules_intent in EXECUTIVE_INTENTS:
            return True
        if rules_intent in CLARIFICATION_INTENTS:
            return True
        if rules_intent in AUDIT_INTENTS:
            return True
        if rules_intent in SUMMARY_INTENTS:
            return True
        if "inbox" in normalized_query and rules_result.get("project_name") == "Inbox":
            return True
        if _is_short_or_follow_up(query):
            return True
        if _is_update_intent(rules_intent):
            return True
        if llm_intent in (None, "", "unknown"):
            return True
        if llm_intent != rules_intent:
            return True

    if rules_intent in (None, "", "unknown") and _is_short_or_follow_up(query) and llm_intent in (None, "", "unknown"):
        return True

    if llm_result and _is_contextual_result(llm_result) and rules_intent in (None, "", "unknown"):
        return True

    if llm_intent in CLARIFICATION_INTENTS and rules_intent in (None, "", "unknown") and _is_short_or_follow_up(query):
        return True

    return False


def _is_short_or_follow_up(query: str) -> bool:
    normalized = query.strip().lower()
    words = [token for token in normalized.replace("?", "").split() if token]
    markers = (
        "cerrala",
        "cerralo",
        "ponelo",
        "ponela",
        "marcalo",
        "marcala",
        "agregale",
        "subile",
        "y en ese proyecto",
        "y sus proyectos",
        "y el proximo paso",
        "ahi",
    )
    return len(words) <= 4 or any(marker in normalized for marker in markers)


def _is_update_intent(intent: str) -> bool:
    return intent in {
        "create_task",
        "create_followup",
        "add_project_note",
        "update_task_status",
        "update_task_priority",
        "add_task_note",
        "update_task_next_action",
        "update_task_last_note",
        "complete_task_by_name",
        "update_task_priority_by_name",
        "add_task_update_by_name",
    }


def _is_contextual_result(result: dict) -> bool:
    contextual_values = {
        "eso",
        "esta tarea",
        "esa tarea",
        "este proyecto",
        "ese proyecto",
        "proyecto actual",
        "este cliente",
        "ese cliente",
        "cliente actual",
    }
    return any(result.get(field) in contextual_values for field in ("task_name", "project_name", "client_name"))


def _rules_have_more_useful_fields(rules_result: dict, llm_result: dict | None) -> bool:
    if not llm_result:
        return False

    useful_fields = (
        "client_name",
        "project_name",
        "task_name",
        "entity_hint",
        "agenda_title",
        "agenda_date_hint",
        "agenda_time_hint",
        "agenda_query_scope",
        "ordinal_index",
    )
    rules_score = sum(1 for field in useful_fields if rules_result.get(field) not in (None, "", [], {}))
    llm_score = sum(1 for field in useful_fields if llm_result.get(field) not in (None, "", [], {}))

    if rules_score > llm_score:
        return True

    if rules_result.get("intent") == "create_agenda_item":
        return (
            bool(rules_result.get("agenda_title"))
            and bool(rules_result.get("agenda_date_hint"))
            and (
                not llm_result.get("agenda_title")
                or not llm_result.get("agenda_date_hint")
            )
        )

    if rules_result.get("project_name") == "Inbox" and llm_result.get("project_name") != "Inbox":
        return True

    return False

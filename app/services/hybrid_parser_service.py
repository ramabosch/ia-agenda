from app.config import USE_LLM_PARSER
from app.services.llm_parser_service import parse_query_with_llm
from app.services.query_parser_service import parse_user_query as parse_user_query_rules

EXECUTIVE_INTENTS = {
    "get_blocked_items_summary",
    "get_today_priority_summary",
    "get_overdue_or_stuck_summary",
    "get_client_attention_summary",
    "get_project_attention_summary",
    "get_general_executive_summary",
    "get_next_actions_summary",
    "get_missing_next_actions_summary",
    "get_followup_needed_summary",
    "get_push_today_summary",
}

CLARIFICATION_INTENTS = {
    "clarify_entity_reference",
}

SUMMARY_INTENTS = {
    "get_operational_summary",
}


def parse_user_query_hybrid(query: str) -> dict:
    rules_result = parse_user_query_rules(query)
    rules_intent = rules_result.get("intent", "unknown")

    if not USE_LLM_PARSER:
        rules_result["_parser_source"] = "rules"
        return rules_result

    llm_result = parse_query_with_llm(query)
    llm_intent = (llm_result or {}).get("intent", "unknown")

    if _should_prefer_rules(query, rules_result, llm_result):
        rules_result["_parser_source"] = "rules"
        if llm_intent not in (None, "", "unknown") and llm_intent != rules_intent:
            rules_result["_parser_decision"] = "rules_over_llm"
        return rules_result

    if llm_result and llm_intent not in (None, "", "unknown"):
        llm_result["_parser_decision"] = "llm_accepted"
        return llm_result

    rules_result["_parser_source"] = "rules"
    if llm_result is not None:
        rules_result["_parser_decision"] = "llm_rejected"
    return rules_result


def _should_prefer_rules(query: str, rules_result: dict, llm_result: dict | None) -> bool:
    rules_intent = rules_result.get("intent", "unknown")
    llm_intent = (llm_result or {}).get("intent", "unknown")

    if rules_intent not in (None, "", "unknown"):
        if rules_intent in EXECUTIVE_INTENTS:
            return True
        if rules_intent in CLARIFICATION_INTENTS:
            return True
        if rules_intent in SUMMARY_INTENTS:
            return True
        if _is_short_or_follow_up(query):
            return True
        if _is_update_intent(rules_intent):
            return True
        if llm_intent in (None, "", "unknown"):
            return True
        if llm_intent != rules_intent:
            return True

    if rules_intent in (None, "", "unknown") and _is_short_or_follow_up(query):
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

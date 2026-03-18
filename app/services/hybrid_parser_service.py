from app.config import USE_LLM_PARSER
from app.services.llm_parser_service import parse_query_with_llm
from app.services.query_parser_service import parse_user_query as parse_user_query_rules


def parse_user_query_hybrid(query: str) -> dict:
    if USE_LLM_PARSER:
        llm_result = parse_query_with_llm(query)

        if llm_result and llm_result.get("intent") not in (None, "", "unknown"):
            return llm_result

    fallback = parse_user_query_rules(query)
    fallback["_parser_source"] = "rules"
    return fallback
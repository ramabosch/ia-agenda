import streamlit as st

from app.services.conversation_service import save_conversation
from app.services.hybrid_parser_service import parse_user_query_hybrid
from app.services.query_response_service import build_response_from_query


def render_conversation_page():
    st.title("Asistente conversacional (v1)")
    st.session_state.setdefault("conversation_context", {})

    st.write("Escribi una consulta sobre tu agenda operativa.")

    if st.button("Nueva conversacion"):
        st.session_state["conversation_context"] = {}
        st.info("Se limpio el contexto reciente de esta sesion.")

    with st.expander("Ejemplos de consultas que podes hacer"):
        st.write("- que tengo pendiente con Cam")
        st.write("- y en ese proyecto?")
        st.write("- resumime onboarding")
        st.write("- ponelo en alta")
        st.write("- que esta bloqueado")
        st.write("- que deberia hacer hoy")
        st.write("- que cliente necesita atencion primero")
        st.write("- que proyecto esta mas trabado")
        st.write("- resumime lo mas importante del dia")
        st.write("- que sigue para este cliente")
        st.write("- que tareas no tienen proxima accion")
        st.write("- que quedo abierto sin seguimiento")
        st.write("- que deberia empujar hoy si o si")
        st.write("- y que sigue?")
        st.write("- dashboard")
        st.write("- resumime lo del dashboard")
        st.write("- quiero ver Cam")
        st.write("- comentame en que andamos con Cam")
        st.write("- como viene dashboard")
        st.write("- que es lo mas importante aca")
        st.write("- que viene estancado")
        st.write("- que proyecto esta acumulando friccion")
        st.write("- que me preocuparia de Cam")
        st.write("- que me recomendas hacer con Cam")
        st.write("- que atacaria primero")
        st.write("- que destraba mas ahora")
        st.write("- que conviene cerrar hoy")
        st.write("- que priorizarias en este proyecto")
        st.write("- que haria ahora")
        st.write("- por que esa")
        st.write("- y despues de eso?")
        st.write("- mostrame solo lo critico")
        st.write("- y solo lo urgente")
        st.write("- quiero ver solo tareas bloqueadas")
        st.write("- resumimelo en 3 lineas")
        st.write("- damelo mas ejecutivo")
        st.write("- explicamelo simple")
        st.write("- decimelo mas corto")
        st.write("- que le diria al cliente hoy")
        st.write("- que sigue con el CRM?")
        st.write("- marcalo como en progreso")
        st.write("- resumime el cliente Dallas")
        st.write("- y sus proyectos?")
        st.write("- cerra la del formulario")
        st.write("- agregale una nota: falta respuesta del cliente")

    user_query = st.text_input(
        "Tu consulta",
        placeholder="Ej: que tengo pendiente con Cam",
    )

    if st.button("Consultar"):
        if not user_query.strip():
            st.warning("Escribi una consulta primero.")
            return

        current_context = st.session_state.get("conversation_context", {})
        parsed_query = parse_user_query_hybrid(user_query)
        response = build_response_from_query(parsed_query, user_query=user_query, conversation_context=current_context)
        st.session_state["conversation_context"] = parsed_query.get("_conversation_context", {})

        save_conversation(
            user_input=user_query,
            parsed_intent=str(parsed_query),
            response_output=response,
        )

        st.subheader("Respuesta del asistente")
        st.write(response)

        with st.expander("Debug sesiones 20/21/22/22.1/23/25/26"):
            st.write("Parser usado:", parsed_query.get("_parser_source", "desconocido"))
            st.write("Decision parser:", parsed_query.get("_parser_decision"))
            st.write("Intent ejecutivo:", parsed_query.get("intent") if str(parsed_query.get("intent", "")).startswith("get_") else None)
            st.write("Executive scope:", parsed_query.get("_executive_scope", "none"))
            st.write("Follow-up scope:", parsed_query.get("_followup_scope", "none"))
            st.write("Resolver scope:", parsed_query.get("_resolver_scope", "none"))
            st.write("Resolver source:", parsed_query.get("_resolver_source", "none"))
            st.write("Resolver confidence:", parsed_query.get("_resolver_confidence", 0.0))
            st.write("Resolver ambiguous:", parsed_query.get("_resolver_ambiguous", False))
            st.write("Clarification needed:", parsed_query.get("_clarification_needed", False))
            st.write("Clarification reason:", parsed_query.get("_clarification_reason"))
            st.write("Candidate types:", parsed_query.get("_candidate_types", []))
            st.write("Used context to disambiguate:", parsed_query.get("_used_context_to_disambiguate", False))
            st.write("Context source:", parsed_query.get("_context_source", "none"))
            st.write("Context isolated:", parsed_query.get("_context_isolated", False))
            st.write("Security blocked:", parsed_query.get("_security_blocked", False))
            st.write("Security reason:", parsed_query.get("_security_reason"))
            st.write("Clarification candidates")
            st.json(parsed_query.get("_clarification_candidates", []))
            st.write("Update type:", parsed_query.get("_update_type"))
            st.write("Update real:", parsed_query.get("_update_real"))
            st.write("Heuristica ejecutiva")
            st.json(parsed_query.get("_executive_heuristic", []))
            st.write("Entidades priorizadas")
            st.json(parsed_query.get("_executive_entities", {}))
            st.write("Summary scope:", parsed_query.get("_summary_scope", "none"))
            st.write("Heuristica de resumen operativo")
            st.json(parsed_query.get("_summary_heuristic", []))
            st.write("Pendientes destacados")
            st.json(parsed_query.get("_summary_highlights", []))
            st.write("Bloqueos detectados")
            st.json(parsed_query.get("_summary_blockers", []))
            st.write("Proximos pasos detectados")
            st.json(parsed_query.get("_summary_next_steps", []))
            st.write("Recomendacion generada")
            st.write(parsed_query.get("_summary_recommendation"))
            st.write("Friction scope:", parsed_query.get("_friction_scope", "none"))
            st.write("Heuristica de friccion")
            st.json(parsed_query.get("_friction_heuristic", []))
            st.write("Senales detectadas")
            st.json(parsed_query.get("_friction_signals", []))
            st.write("Entidades destacadas por friccion")
            st.json(parsed_query.get("_friction_entities", []))
            st.write("Preocupacion / recomendacion")
            st.write(parsed_query.get("_friction_recommendation"))
            st.write("Recommendation scope:", parsed_query.get("_recommendation_scope", "none"))
            st.write("Heuristica de recomendacion")
            st.json(parsed_query.get("_recommendation_heuristic", []))
            st.write("Entidades candidatas")
            st.json(parsed_query.get("_recommendation_candidates", []))
            st.write("Razones de recomendacion")
            st.json(parsed_query.get("_recommendation_reasons", []))
            st.write("Resultado de recomendacion")
            st.write(parsed_query.get("_recommendation_result"))
            st.write("Tipo de follow-up detectado")
            st.write(parsed_query.get("_continuity_type"))
            st.write("Reutilizo contexto seguro")
            st.write(parsed_query.get("_continuity_used_context", False))
            st.write("Reutilizo recomendacion previa")
            st.write(parsed_query.get("_continuity_used_recommendation", False))
            st.write("Filtro aplicado")
            st.write(parsed_query.get("_continuity_filter_mode"))
            st.write("Modo de reformulacion")
            st.write(parsed_query.get("_continuity_rephrase_style"))
            st.write("Snapshot de respuesta previa")
            st.json(parsed_query.get("_response_snapshot", {}))
            st.write("Heuristica de proximos pasos")
            st.json(parsed_query.get("_followup_heuristic", []))
            st.write("Entidades con next_action")
            st.json(parsed_query.get("_followup_entities_with_next_action", []))
            st.write("Entidades sin next_action")
            st.json(parsed_query.get("_followup_entities_without_next_action", []))
            st.write("Hubo inferencia simple:", parsed_query.get("_followup_inference_used", False))
            st.write("Contexto reciente usado")
            st.json(parsed_query.get("_recent_context_used", {}))
            st.write("Valores detectados")
            st.json(
                {
                    "new_status": parsed_query.get("new_status"),
                    "new_priority": parsed_query.get("new_priority"),
                    "priority_direction": parsed_query.get("priority_direction"),
                    "last_note": parsed_query.get("last_note"),
                    "next_action": parsed_query.get("next_action"),
                }
            )
            st.write("Parsed intent")
            st.json(parsed_query)
            st.write("Resolved references")
            st.json(parsed_query.get("_resolved_references", {}))
            st.write("Conversation context persistido")
            st.json(parsed_query.get("_conversation_context", {}))
            st.write("Update result")
            st.json(parsed_query.get("_update_result", {}))

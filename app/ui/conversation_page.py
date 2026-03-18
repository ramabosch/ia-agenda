import streamlit as st

from app.services.conversation_service import save_conversation
from app.services.hybrid_parser_service import parse_user_query_hybrid
from app.services.query_response_service import build_response_from_query


def render_conversation_page():
    st.title("Asistente conversacional (v1)")

    st.write("Escribí una consulta sobre tu agenda operativa.")

    with st.expander("Ejemplos de consultas que podés hacer"):
        st.write("- decime los clientes activos")
        st.write("- que tengo pendiente con CAM")
        st.write("- resumime el proyecto CRM")
        st.write("- como va onboarding")
        st.write("- que sigue con este cliente")
        st.write("- marcá onboarding como en progreso")
        st.write("- cerrá la tarea formulario")
        st.write("- agregá una nota a onboarding: falta validar con el cliente")
        st.write("- dejá como próxima acción llamar mañana")

    user_query = st.text_input(
        "Tu consulta",
        placeholder="Ej: decime los clientes activos",
    )

    if st.button("Consultar"):
        if not user_query.strip():
            st.warning("Escribí una consulta primero.")
            return

        parsed_query = parse_user_query_hybrid(user_query)
        response = build_response_from_query(parsed_query, user_query=user_query)

        save_conversation(
            user_input=user_query,
            parsed_intent=str(parsed_query),
            response_output=response,
        )

        st.subheader("Respuesta del asistente")
        st.write(response)

        with st.expander("Debug sesión 20/21"):
            st.write("Parser usado:", parsed_query.get("_parser_source", "desconocido"))
            st.write("Resolver scope:", parsed_query.get("_resolver_scope", "none"))
            st.write("Resolver confidence:", parsed_query.get("_resolver_confidence", 0.0))
            st.write("Resolver ambiguous:", parsed_query.get("_resolver_ambiguous", False))
            st.write("Update type:", parsed_query.get("_update_type"))
            st.write("Update real:", parsed_query.get("_update_real"))
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
            st.write("Update result")
            st.json(parsed_query.get("_update_result", {}))

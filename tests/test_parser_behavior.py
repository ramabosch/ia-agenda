import unittest
from unittest.mock import patch

from app.services.hybrid_parser_service import parse_user_query_hybrid
from app.services.query_parser_service import parse_user_query


class ParserBehaviorTests(unittest.TestCase):
    def test_parse_open_tasks_by_client(self):
        parsed = parse_user_query("que tengo pendiente con Cam")
        self.assertEqual(parsed["intent"], "get_open_tasks_by_client_name")
        self.assertEqual(parsed["client_name"], "cam")

    def test_parse_task_status_update(self):
        parsed = parse_user_query("marca onboarding como en progreso")
        self.assertEqual(parsed["intent"], "update_task_status")
        self.assertEqual(parsed["task_name"], "onboarding")
        self.assertEqual(parsed["new_status"], "en_progreso")

    def test_parse_task_note_update(self):
        parsed = parse_user_query("agrega una nota a onboarding: falta validar")
        self.assertEqual(parsed["intent"], "add_task_note")
        self.assertEqual(parsed["task_name"], "onboarding")
        self.assertEqual(parsed["last_note"], "falta validar")

    def test_parse_executive_queries(self):
        blocked = parse_user_query("que esta bloqueado")
        today = parse_user_query("que deberia hacer hoy")
        self.assertEqual(blocked["intent"], "get_blocked_items_summary")
        self.assertEqual(today["intent"], "get_today_priority_summary")

    def test_parse_followup_queries(self):
        client_followup = parse_user_query("que sigue para este cliente")
        missing_next = parse_user_query("que tareas no tienen proxima accion")
        push_today = parse_user_query("que deberia empujar hoy si o si")
        self.assertEqual(client_followup["intent"], "get_next_actions_summary")
        self.assertEqual(client_followup["client_name"], "este cliente")
        self.assertEqual(missing_next["intent"], "get_missing_next_actions_summary")
        self.assertEqual(push_today["intent"], "get_push_today_summary")

    def test_parse_operational_summary_queries(self):
        client = parse_user_query("comentame en que andamos con Cam")
        project = parse_user_query("como viene dashboard")
        contextual = parse_user_query("que es lo mas importante aca")
        self.assertEqual(client["intent"], "get_operational_summary")
        self.assertEqual(client["entity_hint"], "cam")
        self.assertEqual(project["intent"], "get_operational_summary")
        self.assertEqual(project["entity_hint"], "dashboard")
        self.assertEqual(contextual["intent"], "get_operational_summary")

    def test_parse_operational_friction_queries(self):
        stalled = parse_user_query("que viene estancado")
        risky_client = parse_user_query("que me preocuparia de Cam")
        contextual = parse_user_query("y que esta frenado?")
        self.assertEqual(stalled["intent"], "get_operational_friction_summary")
        self.assertEqual(risky_client["intent"], "get_operational_friction_summary")
        self.assertEqual(risky_client["entity_hint"], "cam")
        self.assertEqual(contextual["intent"], "get_operational_friction_summary")

    def test_parse_operational_recommendation_queries(self):
        client = parse_user_query("que me recomendas hacer con Cam")
        first = parse_user_query("que atacaria primero")
        close = parse_user_query("que conviene cerrar hoy")
        contextual = parse_user_query("que priorizarias en este proyecto")
        self.assertEqual(client["intent"], "get_operational_recommendation")
        self.assertEqual(client["entity_hint"], "cam")
        self.assertEqual(first["intent"], "get_operational_recommendation")
        self.assertEqual(first["recommendation_focus"], "general")
        self.assertEqual(close["recommendation_focus"], "close")
        self.assertEqual(contextual["project_name"], "este proyecto")

    def test_parse_conversational_drilldown_queries(self):
        why = parse_user_query("por que esa")
        next_one = parse_user_query("y despues de eso?")
        critical = parse_user_query("mostrame solo lo critico")
        short = parse_user_query("resumimelo en 3 lineas")
        client_facing = parse_user_query("que le diria al cliente hoy")
        self.assertEqual(why["intent"], "get_recommendation_explanation")
        self.assertEqual(next_one["intent"], "get_followup_focus_summary")
        self.assertEqual(next_one["followup_focus"], "next_after_recommendation")
        self.assertEqual(critical["intent"], "get_filtered_context_summary")
        self.assertEqual(critical["filter_mode"], "critical")
        self.assertEqual(short["intent"], "get_rephrased_summary")
        self.assertEqual(short["rephrase_style"], "three_lines")
        self.assertEqual(client_facing["intent"], "get_client_facing_summary")

    def test_parse_adaptive_output_queries(self):
        short = parse_user_query("damelo corto")
        executive = parse_user_query("damelo ejecutivo")
        tactical = parse_user_query("damelo tactico")
        detailed = parse_user_query("quiero mas detalle")
        risks = parse_user_query("quiero solo riesgos")
        next_steps = parse_user_query("quiero solo proximos pasos")
        bullets = parse_user_query("dame solo bullets")
        meeting = parse_user_query("decimelo como para reunion")
        personal = parse_user_query("decimelo como para mi")
        important = parse_user_query("mostrame solo lo importante")
        client = parse_user_query("decimelo como para mandarselo al cliente")

        self.assertEqual(short["intent"], "get_rephrased_summary")
        self.assertEqual(short["rephrase_style"], "short")
        self.assertEqual(executive["rephrase_style"], "executive")
        self.assertEqual(tactical["rephrase_style"], "tactical")
        self.assertEqual(detailed["rephrase_style"], "detailed")
        self.assertEqual(risks["intent"], "get_filtered_context_summary")
        self.assertEqual(risks["filter_mode"], "risks")
        self.assertEqual(next_steps["filter_mode"], "next_steps")
        self.assertEqual(bullets["rephrase_style"], "bullets")
        self.assertEqual(meeting["rephrase_style"], "meeting_ready")
        self.assertEqual(personal["rephrase_style"], "personal")
        self.assertEqual(important["filter_mode"], "important")
        self.assertEqual(client["intent"], "get_client_facing_summary")

    def test_parse_creation_queries(self):
        create_task = parse_user_query("crea una tarea para revisar indicadores")
        create_for_client = parse_user_query("agrega una tarea a Cam para definir metricas")
        create_in_project = parse_user_query("agrega una tarea en este proyecto")
        project_note = parse_user_query("suma una nota al proyecto: falta validacion")
        project_note_without_content = parse_user_query("suma una nota al proyecto")
        next_action = parse_user_query("dejame una proxima accion para manana")
        convert = parse_user_query("converti esto en tarea")
        create_tomorrow = parse_user_query("crea una tarea para revisar indicadores para manana")
        create_urgent_today = parse_user_query("agrega una tarea urgente para revisar backlog para hoy")
        followup_friday = parse_user_query("deja follow-up para el viernes")

        self.assertEqual(create_task["intent"], "create_task")
        self.assertEqual(create_task["task_name"], "revisar indicadores")
        self.assertEqual(create_for_client["intent"], "create_task")
        self.assertEqual(create_for_client["client_name"], "cam")
        self.assertEqual(create_for_client["task_name"], "definir metricas")
        self.assertEqual(create_in_project["intent"], "create_task")
        self.assertEqual(create_in_project["project_name"], "este proyecto")
        self.assertEqual(project_note["intent"], "add_project_note")
        self.assertEqual(project_note["last_note"], "falta validacion")
        self.assertEqual(project_note_without_content["intent"], "add_project_note")
        self.assertIsNone(project_note_without_content["last_note"])
        self.assertEqual(next_action["intent"], "update_task_next_action")
        self.assertEqual(next_action["next_action"], "manana")
        self.assertEqual(convert["intent"], "create_task")
        self.assertEqual(convert["task_name"], "esto")
        self.assertEqual(create_tomorrow["due_hint"], "manana")
        self.assertEqual(create_tomorrow["time_scope"], "tomorrow")
        self.assertEqual(create_urgent_today["task_name"], "revisar backlog")
        self.assertEqual(create_urgent_today["new_priority"], "alta")
        self.assertEqual(create_urgent_today["due_hint"], "hoy")
        self.assertEqual(followup_friday["intent"], "create_followup")
        self.assertEqual(followup_friday["due_hint"], "viernes")

    def test_parse_temporal_queries(self):
        due_today = parse_user_query("que vence hoy")
        overdue = parse_user_query("que tengo atrasado")
        tomorrow = parse_user_query("que tengo para manana")
        week_followups = parse_user_query("que follow-ups vencen esta semana")
        missing_due = parse_user_query("que no tiene fecha y deberia tenerla")

        self.assertEqual(due_today["intent"], "get_due_tasks_summary")
        self.assertEqual(due_today["time_scope"], "today")
        self.assertEqual(overdue["intent"], "get_overdue_tasks_summary")
        self.assertEqual(overdue["time_scope"], "overdue")
        self.assertEqual(tomorrow["intent"], "get_due_tasks_summary")
        self.assertEqual(tomorrow["time_scope"], "tomorrow")
        self.assertEqual(week_followups["temporal_focus"], "followups")
        self.assertEqual(missing_due["intent"], "get_missing_due_date_summary")

    def test_parse_compound_queries(self):
        summary_and_recommend = parse_user_query("resumime Cam y decime que haria primero")
        temporal_and_friction = parse_user_query("que vence y que me preocuparia")
        urgent_and_overdue = parse_user_query("que tengo urgente y atrasado")
        summary_and_followup = parse_user_query("comentame dashboard y despues decime que sigue")
        client_facing = parse_user_query("que me preocuparia de Cam y que le diria al cliente")

        self.assertEqual(summary_and_recommend["intent"], "compound_query")
        self.assertEqual(summary_and_recommend["subqueries"][0]["intent"], "get_operational_summary")
        self.assertEqual(summary_and_recommend["subqueries"][1]["intent"], "get_operational_recommendation")
        self.assertEqual(temporal_and_friction["subqueries"][0]["intent"], "get_due_tasks_summary")
        self.assertEqual(temporal_and_friction["subqueries"][1]["intent"], "get_followup_focus_summary")
        self.assertEqual(urgent_and_overdue["subqueries"][0]["intent"], "get_today_priority_summary")
        self.assertEqual(urgent_and_overdue["subqueries"][1]["intent"], "get_overdue_tasks_summary")
        self.assertEqual(summary_and_followup["subqueries"][1]["intent"], "get_next_actions_summary")
        self.assertEqual(client_facing["subqueries"][1]["intent"], "get_client_facing_summary")

    def test_parse_contextual_followups(self):
        projects = parse_user_query("y sus proyectos?")
        close_task = parse_user_query("cerrala")
        self.assertEqual(projects["intent"], "get_projects_by_client_name")
        self.assertEqual(projects["client_name"], "este cliente")
        self.assertEqual(close_task["intent"], "update_task_status")
        self.assertEqual(close_task["task_name"], "eso")

    def test_parse_open_ambiguous_inputs_as_clarification(self):
        dashboard = parse_user_query("dashboard")
        view_cam = parse_user_query("quiero ver Cam")
        summary_dashboard = parse_user_query("resumime lo del dashboard")
        self.assertEqual(dashboard["intent"], "clarify_entity_reference")
        self.assertEqual(dashboard["entity_hint"], "dashboard")
        self.assertEqual(view_cam["intent"], "clarify_entity_reference")
        self.assertEqual(view_cam["entity_hint"], "cam")
        self.assertEqual(summary_dashboard["intent"], "clarify_entity_reference")
        self.assertEqual(summary_dashboard["entity_hint"], "dashboard")

    def test_hybrid_prefers_rules_for_short_updates(self):
        llm_result = {
            "intent": "get_task_summary",
            "task_name": "otra cosa",
            "_parser_source": "llm",
        }
        with patch("app.services.hybrid_parser_service.parse_query_with_llm", return_value=llm_result):
            parsed = parse_user_query_hybrid("cerrala")
        self.assertEqual(parsed["intent"], "update_task_status")
        self.assertEqual(parsed["_parser_source"], "rules")
        self.assertEqual(parsed["_parser_decision"], "rules_over_llm")


if __name__ == "__main__":
    unittest.main()

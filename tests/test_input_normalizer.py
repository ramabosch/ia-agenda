"""Tests para la normalización de input del usuario (Task 2 - Sesión 59)."""

import unittest
from unittest.mock import patch, MagicMock


class InputNormalizerTests(unittest.TestCase):
    def _normalize(self, text: str) -> str:
        from app.services.input_normalizer import normalize_input
        return normalize_input(text)

    # ------------------------------------------------------------------
    # Criterios de aceptación del spec
    # ------------------------------------------------------------------

    def test_spec_que_se_viene(self):
        """normalize_input('qué se viene?') → 'que se viene'"""
        self.assertEqual(self._normalize("qué se viene?"), "que se viene")

    def test_spec_tmb_agenda(self):
        """normalize_input('tmb agendá eso') → 'tambien agenda eso'"""
        self.assertEqual(self._normalize("tmb agendá eso"), "tambien agenda eso")

    # ------------------------------------------------------------------
    # Tildes / diacríticos
    # ------------------------------------------------------------------

    def test_a_con_tilde(self):
        self.assertEqual(self._normalize("acción"), "accion")

    def test_e_con_tilde(self):
        self.assertEqual(self._normalize("réunión"), "reunion")

    def test_i_con_tilde(self):
        self.assertEqual(self._normalize("índice"), "indice")

    def test_o_con_tilde(self):
        self.assertEqual(self._normalize("próximo"), "proximo")

    def test_u_con_tilde(self):
        self.assertEqual(self._normalize("últimas"), "ultimas")

    def test_u_umlaut(self):
        self.assertEqual(self._normalize("güero"), "guero")

    def test_enie(self):
        self.assertEqual(self._normalize("mañana"), "manana")

    def test_multiple_tildes(self):
        self.assertEqual(
            self._normalize("revisión de métricas con señal"),
            "revision de metricas con senal",
        )

    # ------------------------------------------------------------------
    # Abreviaciones
    # ------------------------------------------------------------------

    def test_abrev_q(self):
        self.assertEqual(self._normalize("q queres"), "que queres")

    def test_abrev_xq(self):
        self.assertEqual(self._normalize("no sé xq falla"), "no se porque falla")

    def test_abrev_tmb(self):
        self.assertEqual(self._normalize("tmb hay que ver eso"), "tambien hay que ver eso")

    def test_abrev_pls(self):
        self.assertEqual(self._normalize("hacelo pls"), "hacelo por favor")

    def test_abrev_porfa(self):
        self.assertEqual(self._normalize("ayudame porfa"), "ayudame por favor")

    def test_abrev_no_partial_match(self):
        """'camq' no debe expandir la 'q' embebida."""
        result = self._normalize("camq")
        self.assertNotIn("que", result)

    def test_abrev_tmb_no_partial_match(self):
        """'atmbla' no debe expandir 'tmb'."""
        result = self._normalize("atmbla")
        self.assertNotIn("tambien", result)

    # ------------------------------------------------------------------
    # Puntuación
    # ------------------------------------------------------------------

    def test_removes_question_marks(self):
        self.assertEqual(self._normalize("¿qué pasa?"), "que pasa")

    def test_removes_exclamation(self):
        self.assertEqual(self._normalize("¡hola!"), "hola")

    def test_removes_comma(self):
        self.assertEqual(self._normalize("uno, dos, tres"), "uno dos tres")

    def test_preserves_slash(self):
        """La barra / debe conservarse (separador útil en comandos)."""
        result = self._normalize("tareas/proyectos")
        self.assertIn("/", result)

    def test_removes_dots(self):
        self.assertEqual(self._normalize("revisar. actualizar."), "revisar actualizar")

    # ------------------------------------------------------------------
    # Lowercase
    # ------------------------------------------------------------------

    def test_lowercase_conversion(self):
        self.assertEqual(self._normalize("HOLA MUNDO"), "hola mundo")

    def test_mixed_case(self):
        self.assertEqual(self._normalize("Crea Una Tarea"), "crea una tarea")

    # ------------------------------------------------------------------
    # Espacios
    # ------------------------------------------------------------------

    def test_collapses_multiple_spaces(self):
        self.assertEqual(self._normalize("hola    mundo"), "hola mundo")

    def test_strips_leading_trailing(self):
        self.assertEqual(self._normalize("  hola  "), "hola")

    # ------------------------------------------------------------------
    # Función pura: no mutación de estado
    # ------------------------------------------------------------------

    def test_pure_function_same_input_same_output(self):
        from app.services.input_normalizer import normalize_input
        text = "¿Qué tareas tengo mañana?"
        self.assertEqual(normalize_input(text), normalize_input(text))

    def test_empty_string(self):
        self.assertEqual(self._normalize(""), "")

    def test_whitespace_only(self):
        self.assertEqual(self._normalize("   "), "")

    # ------------------------------------------------------------------
    # El texto guardado en DB NO está normalizado
    # ------------------------------------------------------------------

    def test_db_receives_original_text_not_normalized(self):
        """save_conversation debe recibir el user_query original, no el normalizado."""
        from app.services.conversation_runtime_service import process_conversation_turn

        original = "¿Qué tareas tengo mañana?"
        captured_calls = []

        def fake_parse(q):
            return {"intent": "get_active_projects", "_parser_source": "rules"}

        def fake_build(parsed, *, user_query, conversation_context):
            return "respuesta"

        def fake_save(*, user_input, parsed_intent, response_output):
            captured_calls.append(user_input)

        with patch("app.services.conversation_runtime_service.parse_user_query_hybrid", fake_parse), \
             patch("app.services.conversation_runtime_service.build_response_from_query", fake_build), \
             patch("app.services.conversation_runtime_service.save_conversation", fake_save):
            process_conversation_turn(original, persist_log=True)

        self.assertEqual(len(captured_calls), 1)
        self.assertEqual(captured_calls[0], original, "La DB debe recibir el texto original, no normalizado")


if __name__ == "__main__":
    unittest.main()

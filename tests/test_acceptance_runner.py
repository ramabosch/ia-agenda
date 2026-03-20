import tempfile
import unittest
from pathlib import Path

from tests.acceptance_runner import Scenario, ScenarioTurn, render_markdown_report, run_acceptance_suite


class AcceptanceRunnerTests(unittest.TestCase):
    def test_runner_supports_multi_turn_context_and_reports_pass(self):
        scenarios = [
            Scenario(
                scenario_id="CNT-T1",
                title="Continuidad basica",
                category="continuity",
                severity="medium",
                tags=["continuity"],
                turns=[
                    ScenarioTurn("comentame en que andamos con Cam", {"should_not_error": True, "should_have_response": True}),
                    ScenarioTurn("que me preocuparia", {"should_not_error": True, "should_have_response": True, "should_have_context_reuse": True}),
                ],
            )
        ]

        report = run_acceptance_suite(scenarios=scenarios)

        self.assertEqual(report["summary"]["pass"], 1)
        self.assertEqual(report["results"][0]["status"], "PASS")
        self.assertEqual(len(report["results"][0]["turns"]), 2)

    def test_runner_marks_partial_when_a_check_fails(self):
        scenarios = [
            Scenario(
                scenario_id="SAFE-T1",
                title="Check fallido",
                category="safety",
                severity="critical",
                tags=["safety"],
                turns=[
                    ScenarioTurn("cerrala", {"should_be_clear_confirmation": True}),
                ],
            )
        ]

        report = run_acceptance_suite(scenarios=scenarios)

        self.assertEqual(report["summary"]["partial"], 1)
        self.assertEqual(report["results"][0]["status"], "PARTIAL")

    def test_runner_exports_json_and_markdown(self):
        scenarios = [
            Scenario(
                scenario_id="FRI-T1",
                title="Export simple",
                category="friction",
                severity="high",
                tags=["friction"],
                turns=[ScenarioTurn("que me viene estancando", {"should_not_error": True, "should_have_response": True})],
            )
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            report = run_acceptance_suite(scenarios=scenarios, output_dir=tempdir)
            json_path = Path(report["artifacts"]["json"])
            markdown_path = Path(report["artifacts"]["markdown"])

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertIn("Acceptance Suite Report", render_markdown_report(report))
            self.assertIn("by_category", report["summary"])

    def test_runner_can_filter_by_severity(self):
        scenarios = [
            Scenario(
                scenario_id="REC-T1",
                title="Recomendacion",
                category="recommendation",
                severity="critical",
                tags=["recommendation"],
                turns=[ScenarioTurn("que destraba mas ahora", {"should_not_error": True, "should_have_response": True})],
            ),
            Scenario(
                scenario_id="TMP-T1",
                title="Temporal",
                category="temporal",
                severity="low",
                tags=["temporal"],
                turns=[ScenarioTurn("que vence hoy", {"should_not_error": True, "should_have_response": True})],
            ),
        ]

        report = run_acceptance_suite(scenarios=scenarios, severity_filters=["critical"])

        self.assertEqual(report["scenario_count"], 1)
        self.assertEqual(report["results"][0]["id"], "REC-T1")


if __name__ == "__main__":
    unittest.main()

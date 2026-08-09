from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/preflight_material_project.py"
FIXTURES = ROOT / "tests/fixtures/preflight"
spec = importlib.util.spec_from_file_location("preflight_material_project", SCRIPT)
assert spec and spec.loader
preflight = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = preflight
spec.loader.exec_module(preflight)


def base_request() -> dict:
    return {
        "original_problem": "ออกแบบใบงานเรื่องเซตหนึ่งไฟล์",
        "input_path": "workspace/nested/source.md",
        "work_kinds": ["material-design"],
        "approval_gate_count": 1,
    }


def inspect(request: dict) -> dict:
    return preflight.inspect_preflight(request, base=FIXTURES)


class MaterialPreflightTests(unittest.TestCase):
    def test_parent_skill_routes_by_mode_without_always_running_preflight(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Mode A — quick review", skill)
        self.assertIn("Mode B — project-aware", skill)
        self.assertIn("Mode C — approved production", skill)
        self.assertIn("Do not run preflight", skill)
        self.assertIn("references/project-preflight.md", skill)
        self.assertNotIn("Before work, read", skill)

    def test_parent_skill_preserves_project_state_and_dimension_authority(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("TEACHING-CONVENTIONS.md", normalized)
        self.assertIn("DOCX-PREFERENCES.md", normalized)
        self.assertIn("actually touch DOCX", normalized)
        self.assertIn("topic's approved", normalized)
        self.assertIn("resolve by dimension", normalized)
        self.assertIn("historical files are evidence", normalized)

    def test_parent_skill_preserves_approval_and_direct_docx_route(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("teacher both approves", normalized)
        self.assertIn("Thai DOCX repair or formatting", normalized)
        self.assertIn("route that case directly to `thai-math-docx`", normalized)
        self.assertIn("Do not begin production merely because it is possible", normalized)

    def test_preflight_reference_is_mode_b_conditional(self) -> None:
        reference = (ROOT / "references/project-preflight.md").read_text(encoding="utf-8")
        self.assertIn("Run preflight only from Mode B", reference)
        self.assertIn("Do not run it for\nan isolated Mode A review", reference)
        self.assertIn("MATERIAL-CONTROL-<slug>.md", reference)

    def test_metadata_no_longer_prompts_preflight_for_every_material(self) -> None:
        metadata = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn('short_description: "Review and route Thai math materials"', metadata)
        self.assertIn("review this Thai math example or resume", metadata)
        self.assertNotIn("preflight and map", metadata)

    def test_short_disposable_sheet_uses_embedded_project_map(self) -> None:
        report = inspect(base_request())
        self.assertEqual("embedded-project-map", report["control_mode"])
        self.assertEqual([], [item for item in report["long_project_signals"] if item["active"]])
        rendered = preflight.render_short_project_map(report)
        self.assertIn("## Project Map", rendered)
        self.assertIn("Original Problem", rendered)
        self.assertIn("Routing rationale", rendered)

    def test_three_committed_real_style_requests_render_expected_map_modes(self) -> None:
        expected = {
            "short-sheet.json": "embedded-project-map",
            "multi-session-batch.json": "material-control",
            "current-master.json": "material-control",
        }
        for name, mode in expected.items():
            request_path = FIXTURES / "requests" / name
            request = json.loads(request_path.read_text(encoding="utf-8"))
            with self.subTest(request=name):
                report = preflight.inspect_preflight(request, base=request_path.parent)
                self.assertEqual(mode, report["control_mode"])
                rendered = (
                    preflight.render_short_project_map(report)
                    if mode == "embedded-project-map"
                    else preflight.render_material_control(report)
                )
                self.assertIn("Original Problem", rendered)
                self.assertIn("Routing rationale", rendered)

    def test_every_locked_long_project_signal_routes_to_material_control(self) -> None:
        scenarios = json.loads((FIXTURES / "scenarios.json").read_text(encoding="utf-8"))
        for scenario in scenarios["long_signal_cases"]:
            request = copy.deepcopy(base_request())
            request.update(scenario["overrides"])
            with self.subTest(signal=scenario["signal"]):
                report = inspect(request)
                active = {item["signal"] for item in report["long_project_signals"] if item["active"]}
                self.assertIn(scenario["signal"], active)
                self.assertEqual("material-control", report["control_mode"])

    def test_nested_input_discovers_nearest_credible_root(self) -> None:
        report = inspect(base_request())
        self.assertEqual((FIXTURES / "workspace").resolve(), Path(report["project_root"]))
        self.assertEqual("nearest-credible-boundary", report["root_discovery"]["basis"])
        self.assertIn("MATERIAL-DESIGN-sample.md", report["root_discovery"]["markers"])

    def test_declared_root_wins_and_must_contain_input(self) -> None:
        request = base_request() | {"declared_root": "workspace"}
        self.assertEqual("explicit-declared-root", inspect(request)["root_discovery"]["basis"])
        with self.assertRaisesRegex(preflight.PreflightError, "outside declared_root"):
            inspect(base_request() | {"declared_root": "external"})

    def test_external_inputs_are_bounded_and_must_be_explicit(self) -> None:
        report = inspect(base_request() | {"external_inputs": ["external/reference.pdf"]})
        external = str((FIXTURES / "external/reference.pdf").resolve())
        self.assertEqual([external], report["path_scope"]["explicit_external_inputs"])
        self.assertEqual("external-reference", report["artifact_lifecycle"][0]["lifecycle"])
        with self.assertRaisesRegex(preflight.PreflightError, "must be named in external_inputs"):
            inspect(base_request() | {"design_paths": ["external/reference.pdf"]})

    def test_planned_route_paths_may_not_exist_but_remain_inside_root(self) -> None:
        report = inspect(
            base_request()
            | {
                "asset_paths": ["workspace/planned-assets"],
                "deliverable_paths": ["workspace/planned/future.docx"],
                "qa_paths": ["workspace/planned/qa"],
            }
        )
        self.assertIn(str((FIXTURES / "workspace/planned-assets").resolve()), report["route_candidates"]["assets"])
        self.assertIn(str((FIXTURES / "workspace/planned/future.docx").resolve()), report["route_candidates"]["deliverables"])
        self.assertIn(str((FIXTURES / "workspace/planned/qa").resolve()), report["route_candidates"]["qa"])
        with self.assertRaisesRegex(preflight.PreflightError, "outside root"):
            inspect(base_request() | {"deliverable_paths": ["external/future.docx"]})

    def test_filename_and_mtime_never_designate_current_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "MATERIAL-DESIGN-marker.md").write_text("marker", encoding="utf-8")
            latest = root / "FINAL_CURRENT_LATEST.docx"
            latest.write_text("fixture", encoding="utf-8")
            report = preflight.inspect_preflight(
                {
                    "original_problem": "ตรวจไฟล์ที่ชื่อเหมือนฉบับล่าสุด",
                    "input_path": str(latest),
                    "work_kinds": ["docx-production"],
                }
            )
        artifact_authority = next(
            item for item in report["authority_matrix"] if item["dimension"] == "current-artifact-layout"
        )
        self.assertEqual("not-designated", artifact_authority["status"])
        self.assertIn("never establish authority", report["authority_warning"])

    def test_explicit_current_master_is_authoritative_and_long(self) -> None:
        report = inspect(base_request() | {"current_editable_master": "workspace/master.docx"})
        master = next(item for item in report["artifact_lifecycle"] if item["lifecycle"] == "current-editable-master")
        self.assertTrue(master["authority_for_current_artifact"])
        self.assertEqual("explicit-user-designation", master["basis"])
        self.assertEqual("material-control", report["control_mode"])

    def test_historical_artifact_is_evidence_not_compatibility_authority(self) -> None:
        report = inspect(base_request() | {"historical_paths": ["workspace/outputs/sheet-a.docx"]})
        historical = report["artifact_lifecycle"][0]
        self.assertEqual("disposable-build-output", historical["lifecycle"])
        self.assertFalse(historical["authority_for_current_artifact"])
        authority = next(item for item in report["authority_matrix"] if item["dimension"] == "historical-behavior")
        self.assertEqual("evidence-only", authority["status"])

    def test_routing_is_explicit_announced_and_owner_correct(self) -> None:
        report = inspect(
            base_request()
            | {
                "work_kinds": [
                    "material-design",
                    "docx-production",
                    "answer-correctness",
                    "continuity-handoff",
                ]
            }
        )
        self.assertEqual(
            ["blind-answer-key-audit", "handoff", "thai-math-docx"],
            report["required_child_skills"],
        )
        announcements = "\n".join(report["routing_announcements"])
        self.assertIn("Keep material-design in math-handout-sandbox", announcements)
        self.assertIn("Route docx-production to thai-math-docx", announcements)

    def test_unsupported_route_blocks_instead_of_guessing(self) -> None:
        with self.assertRaisesRegex(preflight.PreflightError, "unsupported work_kinds"):
            inspect(base_request() | {"work_kinds": ["telepathic-publishing"]})

    def test_material_control_has_exact_bounded_section_order(self) -> None:
        report = inspect(base_request() | {"multi_session": True})
        rendered = preflight.render_material_control(report)
        headings = [line[3:] for line in rendered.splitlines() if line.startswith("## ")]
        self.assertEqual(list(preflight.CONTROL_SECTIONS), headings)
        self.assertIn("only hot material control", report["hot_control_rule"])

    def test_build_changelog_does_not_become_competing_hot_control(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            design = root / "MATERIAL-DESIGN-fixture.md"
            design.write_text("marker", encoding="utf-8")
            (root / "BUILD-CHANGELOG-old.md").write_text("legacy", encoding="utf-8")
            report = preflight.inspect_preflight(
                {
                    "original_problem": "งานสั้นที่มี log เก่า",
                    "input_path": str(design),
                    "work_kinds": ["material-design"],
                }
            )
        self.assertEqual("embedded-project-map", report["control_mode"])
        self.assertEqual([], report["route_candidates"]["control"])

    def test_conflicting_explicit_lifecycle_creates_cf_record(self) -> None:
        report = inspect(
            base_request()
            | {
                "current_editable_master": "workspace/master.docx",
                "historical_paths": ["workspace/master.docx"],
            }
        )
        self.assertEqual("CF-001", report["open_conflicts"][0]["conflict_id"])
        self.assertEqual("open", report["open_conflicts"][0]["status"])

    def test_cli_is_read_only_and_can_render_control(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            source = workspace / "MATERIAL-DESIGN-source.md"
            source.write_text("unchanged", encoding="utf-8")
            request = root / "request.json"
            request.write_text(
                json.dumps(
                    {
                        "original_problem": "งานหลาย session",
                        "input_path": "workspace/MATERIAL-DESIGN-source.md",
                        "multi_session": True,
                        "work_kinds": ["material-design"],
                    }
                ),
                encoding="utf-8",
            )
            before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(request), "--format", "control"],
                capture_output=True,
                text=True,
                check=False,
            )
            after = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("## ENTRYPOINT", completed.stdout)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

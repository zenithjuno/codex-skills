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
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


initializer = load_module("init_exam_project")
validator = load_module("validate_exam_state")
item_meta = load_module("item_meta")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_project(root: Path) -> Path:
    initializer.initialize_exam_project(
        root,
        slug="logic-midterm",
        title="ข้อสอบตรรกศาสตร์กลางภาค",
        chapter="ตรรกศาสตร์",
        objective_count=2,
        written_count=1,
        points_per_objective=1,
        points_per_written=2,
        passing_points=2,
        book_policy="open",
        time_minutes=50,
    )
    return root / "exam-state"


def config_first() -> dict:
    return read(FIXTURES / "config-first.json")


def item(
    item_id: str,
    section: str,
    position: int,
    difficulty: str,
    topic: str,
    *,
    paired: bool = False,
    configured: bool = False,
) -> dict:
    return {
        "item_id": item_id,
        "section": section,
        "position": position,
        "topic_group": topic,
        "source_action": "new",
        "intended_difficulty": difficulty,
        "target_skill": f"ทักษะของ {item_id}",
        "target_misconception": f"ความเข้าใจคลาดเคลื่อนของ {item_id}",
        "paired_or_proof": paired,
        "config_first": configured,
        "config": config_first() if configured else {},
        "current_variant": None,
        "status": "planned",
    }


def populate_item_map(project_root: Path) -> None:
    state = project_root / "exam-state"
    project = read(state / "exam-project.json")
    project["current_stage"] = "item-map"
    project["blueprint"] = {
        "approved": True,
        "topic_targets": {"ประพจน์": 2, "การอ้างเหตุผล": 1},
        "difficulty_targets": {"easy": 1, "medium": 1, "hard": 1},
        "rationale": "เริ่มจากความหมายพื้นฐานก่อนจบด้วยการอ้างเหตุผลแบบเขียน",
    }
    for key in ("format", "taxonomy", "blueprint", "item_map"):
        project["approvals"][key] = "approved"
    write(state / "exam-project.json", project)

    taxonomy = read(state / "difficulty-taxonomy.json")
    taxonomy["approved"] = True
    descriptions = {
        "easy": "ใช้ความหมายหรือกฎพื้นฐานหนึ่งขั้น",
        "medium": "เชื่อมสองแนวคิดที่คุ้นเคย",
        "hard": "ต้องเลือกเส้นทางให้เหตุผลที่ไม่ตรงไปตรงมา",
    }
    for level in taxonomy["levels"]:
        level["description"] = descriptions[level["id"]]
        level["techniques"] = [f"เทคนิค-{level['id']}"]
    taxonomy["scope_limits"] = ["ไม่ใช้ nested quantifiers"]
    taxonomy["book_policy_implications"] = ["ข้อค้นกฎตรง ๆ ไม่นับเป็นข้อยาก"]
    write(state / "difficulty-taxonomy.json", taxonomy)

    item_map = read(state / "item-map.json")
    item_map["items"] = [
        item("Q01", "objective", 1, "easy", "ประพจน์"),
        item("Q02", "objective", 2, "medium", "ประพจน์"),
        item("W01", "written", 1, "hard", "การอ้างเหตุผล", configured=True),
    ]
    write(state / "item-map.json", item_map)


def approve_drafting(project_root: Path) -> None:
    state = project_root / "exam-state"
    populate_item_map(project_root)
    project = read(state / "exam-project.json")
    project["current_stage"] = "drafting"
    project["approvals"]["questions"] = "approved"
    write(state / "exam-project.json", project)
    item_map = read(state / "item-map.json")
    variants = read(state / "item-variants.json")
    for mapped in item_map["items"]:
        variant_id = f"{mapped['item_id']}A"
        mapped["current_variant"] = variant_id
        mapped["status"] = "approved"
        variants["variants"].append(
            {
                "variant_id": variant_id,
                "item_id": mapped["item_id"],
                "status": "approved",
                "design_family": f"family-{mapped['item_id']}",
                "expression_summary": f"approved expression for {mapped['item_id']}",
                "decision_notes": "approved by teacher",
                "config_snapshot": copy.deepcopy(mapped["config"]),
            }
        )
    write(state / "item-map.json", item_map)
    write(state / "item-variants.json", variants)


class ExamProjectTests(unittest.TestCase):
    def test_initializer_creates_exact_owned_state_without_readme_or_owner_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            result = initializer.initialize_exam_project(
                root,
                slug="sets-final",
                title="ข้อสอบเรื่องเซต",
                chapter="เซต",
                objective_count=10,
                written_count=2,
            )
            self.assertEqual("EXM-sets-final", result["exam_id"])
            self.assertEqual(
                {
                    "EXAM-DRAFT.md",
                    "WORKING-SOLUTIONS.md",
                    "difficulty-taxonomy.json",
                    "exam-project.json",
                    "item-map.json",
                    "item-variants.json",
                },
                {path.name for path in (root / "exam-state").iterdir()},
            )
            self.assertFalse((root / "README.md").exists())
            self.assertFalse(any(path.name.startswith("build_docx") for path in root.rglob("*.py")))
            self.assertTrue(validator.validate_exam_state(root, gate="scaffold")["valid"])

    def test_initializer_refuses_overwrite_and_invalid_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            create_project(root)
            before = (root / "exam-state/exam-project.json").read_bytes()
            with self.assertRaisesRegex(initializer.InitError, "refusing to overwrite"):
                create_project(root)
            self.assertEqual(before, (root / "exam-state/exam-project.json").read_bytes())
            with self.assertRaisesRegex(initializer.InitError, "passing_points"):
                initializer.initialize_exam_project(
                    root / "bad",
                    slug="bad-score",
                    title="Bad",
                    chapter="Bad",
                    objective_count=1,
                    written_count=0,
                    passing_points=99,
                )

    def test_item_map_gate_accepts_consistent_taxonomy_blueprint_and_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            create_project(root)
            populate_item_map(root)
            result = validator.validate_exam_state(root)
        self.assertTrue(result["valid"], result["issues"])
        self.assertEqual(3, result["item_count"])

    def test_hard_written_and_paired_items_must_be_config_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            create_project(root)
            populate_item_map(root)
            path = root / "exam-state/item-map.json"
            data = read(path)
            data["items"][2]["config_first"] = False
            data["items"][2]["config"] = {}
            write(path, data)
            result = validator.validate_exam_state(root)
            self.assertFalse(result["valid"])
            self.assertTrue(any("W01 must be config-first" in issue for issue in result["issues"]))

            data["items"][2] = item("W01", "written", 1, "hard", "การอ้างเหตุผล", configured=True)
            data["items"][1]["paired_or_proof"] = True
            write(path, data)
            paired_result = validator.validate_exam_state(root)
        self.assertTrue(any("Q02 must be config-first" in issue for issue in paired_result["issues"]))

    def test_distribution_score_and_exact_item_ids_fail_actionably(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            create_project(root)
            populate_item_map(root)
            project_path = root / "exam-state/exam-project.json"
            project = read(project_path)
            project["format"]["total_points"] = 999
            project["blueprint"]["difficulty_targets"] = {"easy": 3, "medium": 0, "hard": 0}
            write(project_path, project)
            item_path = root / "exam-state/item-map.json"
            mapped = read(item_path)
            mapped["items"][0]["item_id"] = "Q09"
            write(item_path, mapped)
            result = validator.validate_exam_state(root)
        combined = "\n".join(result["issues"])
        self.assertIn("total_points", combined)
        self.assertIn("item ids must match", combined)
        self.assertIn("difficulty counts", combined)

    def test_missing_required_metadata_and_wrong_owner_route_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            create_project(root)
            path = root / "exam-state/exam-project.json"
            project = read(path)
            project["title"] = ""
            project["routes"]["docx_production"] = "local-build-docx-copy"
            write(path, project)
            result = validator.validate_exam_state(root, gate="scaffold")
        combined = "\n".join(result["issues"])
        self.assertIn("project.title is required", combined)
        self.assertIn("locked owner routing", combined)

    def test_malformed_nested_metadata_returns_issues_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            create_project(root)
            project_path = root / "exam-state/exam-project.json"
            project = read(project_path)
            project["format"] = "not-an-object"
            project["current_stage"] = "item-map"
            write(project_path, project)
            taxonomy_path = root / "exam-state/difficulty-taxonomy.json"
            taxonomy = read(taxonomy_path)
            taxonomy["levels"][0]["id"] = ["bad"]
            write(taxonomy_path, taxonomy)
            result = validator.validate_exam_state(root)
        self.assertFalse(result["valid"])
        self.assertTrue(any("project.format" in issue for issue in result["issues"]))
        self.assertTrue(any("unique easy, medium and hard" in issue for issue in result["issues"]))

    def test_approval_order_rejects_later_gate_leap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            create_project(root)
            path = root / "exam-state/exam-project.json"
            project = read(path)
            project["approvals"]["blind_audit"] = "approved"
            write(path, project)
            result = validator.validate_exam_state(root, gate="scaffold")
        self.assertTrue(any("blind_audit cannot be approved" in issue for issue in result["issues"]))

    def test_drafting_gate_requires_approved_current_variants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            create_project(root)
            approve_drafting(root)
            self.assertTrue(validator.validate_exam_state(root)["valid"])
            variants_path = root / "exam-state/item-variants.json"
            variants = read(variants_path)
            variants["variants"][0]["status"] = "rejected"
            write(variants_path, variants)
            result = validator.validate_exam_state(root)
        self.assertTrue(any("current variant Q01A must be approved" in issue for issue in result["issues"]))

    def test_item_meta_queries_current_and_specific_variant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            create_project(root)
            approve_drafting(root)
            records = item_meta.query_items(root, item_id="W01")
            by_variant = item_meta.query_items(root, variant_id="W01A")
        self.assertEqual("W01", records[0]["item_id"])
        self.assertEqual("W01A", records[0]["current_variant_record"]["variant_id"])
        self.assertEqual("W01", by_variant[0]["item_id"])

    def test_cli_exit_codes_cover_pass_fail_and_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "exam"
            create_project(root)
            passed = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_exam_state.py"), str(root), "--gate", "scaffold"],
                capture_output=True,
                text=True,
                check=False,
            )
            failed = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_exam_state.py"), str(root), "--gate", "item-map"],
                capture_output=True,
                text=True,
                check=False,
            )
            blocked = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_exam_state.py"), str(root / "missing")],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(0, passed.returncode)
        self.assertEqual(1, failed.returncode)
        self.assertEqual(2, blocked.returncode)

    def test_skill_is_provider_neutral_and_does_not_copy_other_owners(self) -> None:
        production_files = [
            ROOT / "SKILL.md",
            ROOT / "agents/openai.yaml",
            *sorted((ROOT / "references").glob("*.md")),
            *sorted(SCRIPTS.glob("*.py")),
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in production_files).casefold()
        for forbidden in ("sonnet", "claude", "background agent", "run_in_background", "general-purpose"):
            self.assertNotIn(forbidden, text)
        script_text = "\n".join(path.read_text(encoding="utf-8") for path in SCRIPTS.glob("*.py"))
        for forbidden in (
            "import docx",
            "from docx",
            "thai_math_docx_builder",
            "m:oMath",
            "w:rFonts",
            "from PIL",
            "import PIL",
        ):
            self.assertNotIn(forbidden, script_text)


if __name__ == "__main__":
    unittest.main()

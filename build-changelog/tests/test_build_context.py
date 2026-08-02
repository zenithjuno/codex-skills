import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "build_context.py"
SPEC = importlib.util.spec_from_file_location("build_context", SCRIPT_PATH)
assert SPEC and SPEC.loader
BUILD_CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD_CONTEXT)


def active_index(source: str) -> dict[str, str]:
    return {
        "ACTIVE CONTRACT INDEX": "\n".join(
            [
                "## ACTIVE CONTRACT INDEX",
                "| Scope | Active contract | Current source | Enforcement |",
                "|---|---|---|---|",
                f"| cross-cutting | `DEC-001` | `BLUEPRINT.md §{source}` | review-only |",
            ]
        )
    }


class ActiveSourceSectionTests(unittest.TestCase):
    def validate(self, heading: str, source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            blueprint = Path(directory) / "BLUEPRINT.md"
            blueprint.write_text(
                f"# Blueprint\n\n## {heading}\n\nDEC-001 is active.\n",
                encoding="utf-8",
            )
            return BUILD_CONTEXT.validate_active_contracts(
                active_index(source), blueprint
            )

    def test_short_number_fails_with_full_heading_hint(self) -> None:
        errors = self.validate("1. Cross-cutting", "1")
        self.assertEqual(len(errors), 1)
        self.assertIn("Did you mean §1. Cross-cutting?", errors[0])
        self.assertIn("full H2 heading text after `## `", errors[0])

    def test_number_only_heading_accepts_number_source(self) -> None:
        self.assertEqual(self.validate("1", "1"), [])

    def test_full_heading_accepts_full_source(self) -> None:
        self.assertEqual(
            self.validate("1. Cross-cutting", "1. Cross-cutting"), []
        )

    def test_reference_uses_full_heading_and_explains_contract(self) -> None:
        reference = (SKILL_ROOT / "references" / "build-control-format.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("§1. Core model / approach", reference)
        self.assertIn("full H2 heading", reference)
        self.assertNotIn("BLUEPRINT-<slug>.md §1`", reference)


class ScopeGateTests(unittest.TestCase):
    def control(self, directory: str) -> Path:
        control = Path(directory) / "BUILD-CONTROL-widget.md"
        control.write_text(
            "\n".join(
                [
                    "# Build Control",
                    "",
                    "## ENTRYPOINT",
                    "- Project root: `.`",
                    "",
                    "## PROJECT MAP",
                    "- Managed: `src/**`",
                    "- Read-only: `fixtures/**`",
                    "- Protected: `.env*`",
                ]
            ),
            encoding="utf-8",
        )
        return control

    def test_managed_and_read_only_paths_do_not_trip_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = BUILD_CONTEXT.command_check_scope(
                    self.control(directory), ["src/app.py", "fixtures/source.json"]
                )
            self.assertEqual(exit_code, 0)
            self.assertIn("MANAGED\tsrc/app.py", output.getvalue())
            self.assertIn("READ-ONLY\tfixtures/source.json", output.getvalue())

    def test_unmapped_or_protected_path_returns_stop_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = BUILD_CONTEXT.command_check_scope(
                    self.control(directory), ["notes/random.md", ".env.local"]
                )
            self.assertEqual(exit_code, 3)
            self.assertIn("UNMAPPED\tnotes/random.md", output.getvalue())
            self.assertIn("PROTECTED\t.env.local", output.getvalue())


class StageHeadingTests(unittest.TestCase):
    def test_canonical_h2_stage_heading_is_accepted(self) -> None:
        block = BUILD_CONTEXT.stage_block("## S15 — Keypad\nbody\n", "S15")
        self.assertTrue(block.startswith("## S15 — Keypad"))

    def test_noncanonical_stage_heading_has_actionable_error(self) -> None:
        for plan in ("### S15 — Keypad\n", "## Stage 15 — Keypad\n"):
            with self.subTest(plan=plan), self.assertRaisesRegex(
                BUILD_CONTEXT.BuildContextError,
                r"## S15 — <title>.*H3.*Stage 15",
            ):
                BUILD_CONTEXT.stage_block(plan, "S15")


class MigrationInventoryTests(unittest.TestCase):
    def blueprint(self, directory: str) -> Path:
        blueprint = Path(directory) / "BLUEPRINT-widget.md"
        blueprint.write_text(
            "# Blueprint\n\n## Task contract\n\nMigrate safely.\n",
            encoding="utf-8",
        )
        return blueprint

    def pending_index(self) -> dict[str, str]:
        return {
            "ACTIVE CONTRACT INDEX": "\n".join(
                [
                    "## ACTIVE CONTRACT INDEX",
                    "| Scope | Active contract | Current source | Enforcement |",
                    "|---|---|---|---|",
                    "| cross-cutting | `PENDING-INVENTORY` | `PENDING-INVENTORY` | `review-only` |",
                ]
            )
        }

    def test_pending_inventory_warns_only_in_migration_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            warnings: list[str] = []
            errors = BUILD_CONTEXT.validate_active_contracts(
                self.pending_index(),
                self.blueprint(directory),
                allow_pending_inventory=True,
                warnings=warnings,
            )
            self.assertEqual(errors, [])
            self.assertIn("pending decision inventory", warnings[0])

    def test_pending_inventory_errors_outside_migration_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            errors = BUILD_CONTEXT.validate_active_contracts(
                self.pending_index(), self.blueprint(directory)
            )
            self.assertIn("allowed only while STATE is MIGRATING", errors[0])

    def test_context_refuses_to_start_during_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blueprint = self.blueprint(directory)
            plan = root / "CONSTRUCTION_PLAN-widget.md"
            agents = root / "AGENTS.md"
            control = root / "BUILD-CONTROL-widget.md"
            plan.write_text("## S01 — Build\nbody\n", encoding="utf-8")
            agents.write_text("# Instructions\n", encoding="utf-8")
            control.write_text(
                "\n".join(
                    [
                        "# Build Control",
                        "",
                        "## ENTRYPOINT",
                        "- Project root: `.`",
                        f"- Blueprint: `{blueprint.name}`",
                        f"- Construction plan: `{plan.name}`",
                        f"- Task contract: `{blueprint.name} §Task contract`",
                        f"- AGENTS instructions: `{agents.name}`",
                        "",
                        "## PROJECT MAP",
                        "- Managed: `src/**`",
                        "",
                        "## STATE",
                        "- Current stage: `MIGRATING — DEC inventory incomplete`",
                        "",
                        "## VERSION CONTROL",
                        "- Mode: `none`",
                        "",
                        self.pending_index()["ACTIVE CONTRACT INDEX"],
                        "",
                        "## OPEN CHANGES",
                        "- (none)",
                        "",
                        "## HISTORY INDEX",
                        "| Segment | Stages | Status | Log |",
                        "|---|---|---|---|",
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                BUILD_CONTEXT.BuildContextError, "migration.*blocked"
            ):
                BUILD_CONTEXT.command_context(control, None)


class ProtocolDocumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.reference = (
            SKILL_ROOT / "references" / "build-control-format.md"
        ).read_text(encoding="utf-8")

    def test_agents_template_contains_executable_bootstrap_fields(self) -> None:
        for label in ("Helper command:", "Validate:", "Context:", "Lookup:", "Scope gate:"):
            self.assertIn(label, self.reference)
        self.assertIn("Never leave command placeholders", self.reference)
        self.assertIn("ACTIVE CONTRACT INDEX before editing code", self.reference)

    def test_stage_heading_invariant_is_documented(self) -> None:
        self.assertIn("`## SNN — <short title>`", self.skill)
        self.assertIn("H3", self.skill)
        self.assertIn("`## SNN — <short title>`", self.reference)

    def test_existing_control_home_and_schema_are_documented(self) -> None:
        self.assertIn("Control schema: `2`", self.reference)
        self.assertIn("already passes `validate`", self.skill)
        self.assertRegex(self.skill, r"must\s+not be relocated")

    def test_migration_inventory_is_build_blocking(self) -> None:
        self.assertIn("PENDING-INVENTORY", self.reference)
        self.assertIn("MIGRATING", self.reference)
        self.assertIn("must refuse build context", self.reference)


if __name__ == "__main__":
    unittest.main()

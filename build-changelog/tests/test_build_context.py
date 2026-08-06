from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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


def blueprint_index(rows: list[str]) -> str:
    return "\n".join(
        [
            "## Active Contract Index",
            "",
            "| Scope | Active contract | Current source | Enforcement |",
            "|---|---|---|---|",
            *rows,
        ]
    )


class IndexMirrorTests(unittest.TestCase):
    """The Blueprint index is canonical; the control copy is a checked mirror."""

    def mirror_errors(self, blueprint_body: str, control_rows: list[str]) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            blueprint = Path(directory) / "BLUEPRINT.md"
            blueprint.write_text(f"# Blueprint\n\n{blueprint_body}\n", encoding="utf-8")
            sections = {
                "ACTIVE CONTRACT INDEX": "\n".join(
                    [
                        "## ACTIVE CONTRACT INDEX",
                        "| Scope | Active contract | Current source | Enforcement |",
                        "|---|---|---|---|",
                        *control_rows,
                    ]
                )
            }
            return BUILD_CONTEXT.validate_index_mirror(sections, blueprint)

    def test_agreeing_copies_pass_despite_wording_differences(self) -> None:
        errors = self.mirror_errors(
            blueprint_index(["| `src/auth/**` | `DEC-014` | §2. Auth | review-only |"]),
            ["| `src/auth/**` | `DEC-014` | `BLUEPRINT.md §2. Auth` | review-only — no hardcoding |"],
        )
        self.assertEqual(errors, [])

    def test_contract_id_drift_between_copies_fails(self) -> None:
        errors = self.mirror_errors(
            blueprint_index(["| `src/auth/**` | `DEC-014` | §2. Auth | review-only |"]),
            ["| `src/auth/**` | `DEC-014`, `CHG-003` | `BLUEPRINT.md §2. Auth` | review-only |"],
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("mirror disagrees with the Blueprint", errors[0])

    def test_row_missing_from_mirror_fails(self) -> None:
        errors = self.mirror_errors(
            blueprint_index(
                [
                    "| `src/auth/**` | `DEC-014` | §2. Auth | review-only |",
                    "| `db/**` | `DEC-009` | §3. Data | migrations |",
                ]
            ),
            ["| `src/auth/**` | `DEC-014` | `BLUEPRINT.md §2. Auth` | review-only |"],
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("missing from the control mirror", errors[0])

    def test_blueprint_without_index_skips_the_comparison(self) -> None:
        errors = self.mirror_errors(
            "## Task contract\n\nShip it.",
            ["| `src/auth/**` | `DEC-014` | `BLUEPRINT.md §2. Auth` | review-only |"],
        )
        self.assertEqual(errors, [])


class TruthSurfaceRegistryTests(unittest.TestCase):
    def project_map(self, rows: list[str]) -> str:
        return "\n".join(
            [
                "## PROJECT MAP",
                "",
                "### Boundaries",
                "- Managed: `src/**`",
                "",
                "### Current truth surfaces",
                "| Role | Canonical source | Refresh trigger | Coverage |",
                "|---|---|---|---|",
                *rows,
                "",
                "### Verification",
                "- Focused test command: `pytest`",
            ]
        )

    def test_registry_rows_are_parsed_from_the_subsection(self) -> None:
        rows = BUILD_CONTEXT.truth_surface_rows(
            self.project_map(
                ["| code-routing | `CODEMAP.md` | topology change | `exact-files: src/*.py` |"]
            )
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["role"], "code-routing")
        self.assertEqual(rows[0]["source"], "`CODEMAP.md`")
        self.assertEqual(BUILD_CONTEXT.exact_files_globs(rows[0]["coverage"]), ["src/*.py"])

    def test_absent_registry_is_not_an_error(self) -> None:
        self.assertEqual(
            BUILD_CONTEXT.truth_surface_rows("## PROJECT MAP\n- Managed: `src/**`\n"), []
        )

    def test_semantic_coverage_declares_no_exact_inventory(self) -> None:
        self.assertEqual(BUILD_CONTEXT.exact_files_globs("semantic"), [])


class StageLifecycleTests(unittest.TestCase):
    def plan(self, rows: list[str], extra: str = "") -> str:
        return "\n".join(
            [
                "# CONSTRUCTION PLAN",
                extra,
                "## แผนที่การเดินทาง (Stage Map)",
                "",
                "| Stage | Lifecycle | Outcome / relationship |",
                "|---|---|---|",
                *rows,
                "",
                "## S16 — Practice mode",
                "body",
            ]
        )

    def test_lifecycle_table_is_found_by_header_not_heading_language(self) -> None:
        lifecycle = BUILD_CONTEXT.stage_lifecycle_rows(
            self.plan(
                [
                    "| `S01` | `PASS` | foundation |",
                    "| `S16` | `ACTIVE` | in progress |",
                    "| `S17` | `RETIRED` | merged into S16 by CHG-086 |",
                ]
            )
        )
        self.assertEqual(lifecycle["S01"], "PASS")
        self.assertEqual(lifecycle["S16"], "ACTIVE")
        self.assertEqual(lifecycle["S17"], "RETIRED")

    def test_lifecycle_token_ignores_trailing_free_text(self) -> None:
        self.assertEqual(
            BUILD_CONTEXT.lifecycle_token("RETIRED — merged into S16 by CHG-086"),
            "RETIRED",
        )

    def test_parallel_stages_must_be_declared_explicitly(self) -> None:
        self.assertFalse(BUILD_CONTEXT.parallel_stages_allowed(self.plan([])))
        self.assertTrue(
            BUILD_CONTEXT.parallel_stages_allowed(
                self.plan([], extra="Parallel stages: allowed for the art track.")
            )
        )


class DoctorTests(unittest.TestCase):
    def build(
        self,
        directory: str,
        *,
        stage: str = "S16",
        lifecycle: list[str] | None = None,
        surfaces: list[str] | None = None,
        open_changes: str = "- (none)",
        extra_files: dict[str, str] | None = None,
        plan_extra: str = "",
    ) -> Path:
        root = Path(directory)
        (root / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
        (root / "BLUEPRINT-widget.md").write_text(
            "# Blueprint\n\n## Task contract\n\nShip it.\n\n"
            + blueprint_index(["| cross-cutting | `DEC-001` | §1. Core | review-only |"])
            + "\n\n## 1. Core\n\nDEC-001 is active.\n",
            encoding="utf-8",
        )
        lifecycle_rows = lifecycle if lifecycle is not None else ["| `S16` | `ACTIVE` | building |"]
        (root / "CONSTRUCTION_PLAN-widget.md").write_text(
            "\n".join(
                [
                    "# CONSTRUCTION PLAN",
                    plan_extra,
                    "## Stage map",
                    "",
                    "| Stage | Lifecycle | Outcome |",
                    "|---|---|---|",
                    *lifecycle_rows,
                    "",
                    f"## {stage} — Current work",
                    "body",
                ]
            ),
            encoding="utf-8",
        )
        for name, body in (extra_files or {}).items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        registry = (
            ["", "### Current truth surfaces", "| Role | Canonical source | Refresh trigger | Coverage |", "|---|---|---|---|", *surfaces]
            if surfaces is not None
            else []
        )
        control = root / "BUILD-CONTROL-widget.md"
        control.write_text(
            "\n".join(
                [
                    "# Build Control",
                    "",
                    "## ENTRYPOINT",
                    "- Slug: `widget`",
                    "- Project root: `.`",
                    "- Blueprint: `BLUEPRINT-widget.md`",
                    "- Construction plan: `CONSTRUCTION_PLAN-widget.md`",
                    "- Task contract: `BLUEPRINT-widget.md §Task contract`",
                    "- AGENTS instructions: `AGENTS.md`",
                    "",
                    "## PROJECT MAP",
                    "- Managed: `src/**`",
                    *registry,
                    "",
                    "## STATE",
                    f"- Current stage: `{stage}`",
                    "",
                    "## VERSION CONTROL",
                    "- Mode: `none`",
                    "",
                    "## ACTIVE CONTRACT INDEX",
                    "| Scope | Active contract | Current source | Enforcement |",
                    "|---|---|---|---|",
                    "| cross-cutting | `DEC-001` | `BLUEPRINT-widget.md §1. Core` | review-only |",
                    "",
                    "## OPEN CHANGES",
                    open_changes,
                    "",
                    "## HISTORY INDEX",
                    "| Segment | Stages | Status | Log |",
                    "|---|---|---|---|",
                ]
            ),
            encoding="utf-8",
        )
        return control

    def doctor(self, control: Path) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = BUILD_CONTEXT.command_doctor(control)
        return code, out.getvalue(), err.getvalue()

    def test_healthy_control_reports_no_blocking_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(
                directory,
                surfaces=["| code-routing | `CODEMAP.md` | topology change | semantic |"],
                extra_files={"CODEMAP.md": "# Map\n"},
            )
            code, out, _ = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertIn("NO BLOCKING DRIFT", out)

    def test_missing_registered_surface_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(
                directory,
                surfaces=["| code-routing | `CODEMAP.md` | topology change | semantic |"],
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("registered current-truth surface is missing", err)

    def test_duplicate_authority_role_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(
                directory,
                surfaces=[
                    "| code-routing | `CODEMAP.md` | topology change | semantic |",
                    "| code-routing | `docs/MAP.md` | topology change | semantic |",
                ],
                extra_files={"CODEMAP.md": "# Map\n", "docs/MAP.md": "# Map\n"},
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("claim role", err)

    def test_current_stage_marked_pass_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(directory, lifecycle=["| `S16` | `PASS` | done |"])
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("a current stage must be ACTIVE or VERIFY", err)

    def test_current_stage_marked_verify_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(directory, lifecycle=["| `S16` | `VERIFY` | awaiting owner |"])
            self.assertEqual(self.doctor(control)[0], 0)

    def test_current_stage_absent_from_lifecycle_table_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(directory, lifecycle=["| `S01` | `PASS` | done |"])
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("absent from the plan's Stage map", err)

    def test_two_live_stages_block_unless_parallel_is_declared(self) -> None:
        rows = ["| `S16` | `ACTIVE` | building |", "| `S20` | `ACTIVE` | also building |"]
        with tempfile.TemporaryDirectory() as directory:
            code, _, err = self.doctor(self.build(directory, lifecycle=rows))
            self.assertEqual(code, 2)
            self.assertIn("Parallel stages: allowed", err)
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(
                directory, lifecycle=rows, plan_extra="Parallel stages: allowed — art track is independent."
            )
            self.assertEqual(self.doctor(control)[0], 0)

    def test_unknown_lifecycle_value_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(directory, lifecycle=["| `S16` | `INPROGRESS` | ? |"])
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("unknown lifecycle", err)

    def test_missing_registry_and_lifecycle_only_warn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = self.build(directory)
            plan = root / "CONSTRUCTION_PLAN-widget.md"
            plan.write_text("# CONSTRUCTION PLAN\n\n## S16 — Current work\nbody\n", encoding="utf-8")
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertIn("no `### Current truth surfaces` registry", err)
            self.assertIn("no `| Stage | Lifecycle |` map", err)

    def test_completed_residue_in_open_changes_warns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(directory, open_changes="- ~~CHG-004 keypad~~ shipped in v88")
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertIn("completed-looking residue", err)

    def test_exact_inventory_catches_an_unmapped_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "old.py").write_text("x = 1\n", encoding="utf-8")
            (root / "src" / "brand-new.py").write_text("y = 2\n", encoding="utf-8")
            control = self.build(
                directory,
                surfaces=["| code-routing | `CODEMAP.md` | topology change | `exact-files: src/*.py` |"],
                extra_files={"CODEMAP.md": "# Map\n\n- `src/old.py` — legacy\n"},
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertIn("src/brand-new.py", err)
            self.assertNotIn("src/old.py` matches", err)

    def test_known_drift_marker_in_a_current_surface_warns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(
                directory,
                open_changes="- CHG-005 reset button approved in chat, not written back to the spec",
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertIn("known-drift marker", err)


class GrepCurrentTests(unittest.TestCase):
    def build(self, directory: str) -> Path:
        control = DoctorTests().build(
            directory,
            surfaces=["| code-routing | `CODEMAP.md` | topology change | semantic |"],
            extra_files={"CODEMAP.md": "# Map\n\n- 14 source files\n"},
        )
        history = Path(directory) / "BUILD-LOG-widget-P01.md"
        history.write_text("# Log\n\n### PRG-001\n- Built: 14 source files\n", encoding="utf-8")
        return control

    def grep(self, control: Path, terms: list[str], allow: list[str] | None = None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = BUILD_CONTEXT.command_grep_current(control, terms, allow or [])
        return code, out.getvalue()

    def test_hits_in_registered_surfaces_return_the_documented_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, out = self.grep(self.build(directory), ["14 source files"])
            self.assertEqual(code, BUILD_CONTEXT.STALE_HIT_EXIT)
            self.assertIn("HIT\tCODEMAP.md:3", out)

    def test_cold_history_is_never_searched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _code, out = self.grep(self.build(directory), ["14 source files"])
            self.assertNotIn("BUILD-LOG", out)

    def test_no_hits_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, out = self.grep(self.build(directory), ["a claim nobody wrote"])
            self.assertEqual(code, 0)
            self.assertIn("NO STALE HITS", out)

    def test_allow_marks_a_surviving_hit_as_intentionally_current(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, out = self.grep(
                self.build(directory), ["14 source files"], allow=["CODEMAP.md:3"]
            )
            self.assertEqual(code, 0)
            self.assertIn("ALLOWED\tCODEMAP.md:3", out)


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

    def test_chg_template_requires_the_four_part_truth_delta(self) -> None:
        for field in ("Added:", "Replaced:", "Removed:", "Superseded:"):
            self.assertIn(f"  - {field}", self.reference)
        self.assertIn("Stale-claim sweep:", self.reference)
        self.assertIn("All four truth-delta lines are required", self.reference)

    def test_prg_template_requires_current_truth_reconciliation(self) -> None:
        self.assertIn("Current truth reconciliation:", self.reference)
        self.assertIn("Reviewed unchanged:", self.reference)

    def test_current_documents_must_retire_false_claims(self) -> None:
        self.assertIn("A current document is not an archive", self.skill)
        self.assertRegex(self.skill, r"removed, rewritten, or explicitly marked")
        self.assertIn("Adding new current truth without retiring", self.skill)

    def test_current_truth_surfaces_registry_is_documented(self) -> None:
        self.assertIn("### Current truth surfaces", self.skill)
        self.assertIn("### Current truth surfaces", self.reference)
        self.assertIn("exact-files:", self.reference)
        self.assertRegex(self.reference, r"never scaffold a `CODEMAP\.md`")

    def test_index_mirror_ownership_is_documented(self) -> None:
        self.assertIn("mirror", self.skill)
        self.assertRegex(self.reference, r"canonical; the control\s+section is a mirror")

    def test_maintenance_uses_prg_not_a_new_id_family(self) -> None:
        self.assertRegex(self.skill, r"PRG work, not a CHG")
        self.assertIn("rather than inventing another", self.skill)
        self.assertIn("Current-truth maintenance checklist", self.reference)

    def test_doctor_and_grep_current_are_bootstrap_commands(self) -> None:
        self.assertIn("Doctor:", self.reference)
        self.assertIn("Stale-claim sweep:", self.reference)
        self.assertIn("`grep-current`", self.skill)
        self.assertIn("`doctor`", self.skill)


class PlanAndBlueprintDocumentationTests(unittest.TestCase):
    """The stage lifecycle and canonical index live in the grill-to-build source."""

    def setUp(self) -> None:
        grill = SKILL_ROOT.parent / "grill-to-build" / "references"
        if not grill.is_dir():
            # build-changelog can be installed on its own; only assert on the
            # companion skill's source when it is actually a sibling.
            raise unittest.SkipTest("grill-to-build is not installed alongside this skill")

        def flowed(name: str) -> str:
            # Prose wraps at 80 columns; assert on content, not line breaks.
            return " ".join((grill / name).read_text(encoding="utf-8").split())

        self.plan_format = flowed("construction-plan-format.md")
        self.blueprint_format = flowed("blueprint-format.md")
        self.control_reference = flowed("coding-build-control.md")

    def test_stage_map_lifecycle_vocabulary_is_documented(self) -> None:
        self.assertIn("| Stage | Lifecycle |", self.plan_format)
        for status in BUILD_CONTEXT.LIFECYCLE_VOCABULARY:
            self.assertIn(f"`{status}`", self.plan_format)
        self.assertIn("Parallel stages: allowed", self.plan_format)
        self.assertRegex(self.plan_format, r"never deleted or renumbered")

    def test_stage_contract_names_truth_surfaces_and_retirements(self) -> None:
        self.assertIn("Current truth surfaces:", self.plan_format)
        self.assertIn("Retire/replace on pass:", self.plan_format)
        # Optional by design: a reflexive `(none)` on every stage teaches blindness.
        self.assertIn("Do not force `(none)` onto every ordinary stage", self.plan_format)

    def test_blueprint_owns_the_canonical_index_and_decision_lifecycle(self) -> None:
        self.assertIn("This table is the canonical index", self.blueprint_format)
        for status in ("CONSOLIDATED INTO DEC-###", "DEFERRED", "LOCAL / NON-BUILD-AFFECTING"):
            self.assertIn(status, self.blueprint_format)
        self.assertIn("Consolidation", self.blueprint_format)

    def test_artifact_role_contract_is_documented(self) -> None:
        self.assertIn("Artifact role contract", self.control_reference)
        self.assertIn("A log entry is evidence, not current truth", self.control_reference)
        self.assertIn("a current document is not an archive", self.control_reference)


if __name__ == "__main__":
    unittest.main()

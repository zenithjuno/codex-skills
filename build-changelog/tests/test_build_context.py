from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "build_context.py"
SPEC = importlib.util.spec_from_file_location("build_context", SCRIPT_PATH)
assert SPEC and SPEC.loader
BUILD_CONTEXT = importlib.util.module_from_spec(SPEC)
# Register in sys.modules before exec: on Python 3.9, dataclasses' ClassVar/
# InitVar detection looks the module up via sys.modules[cls.__module__] even
# with `from __future__ import annotations`, and raises AttributeError on an
# unregistered module. See https://bugs.python.org/issue42410.
sys.modules[SPEC.name] = BUILD_CONTEXT
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
            control = Path(directory) / "BUILD-CONTROL.md"
            return BUILD_CONTEXT.validate_active_contracts(
                control, active_index(source), blueprint
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


def active_index_with_source(cell: str) -> dict[str, str]:
    return {
        "ACTIVE CONTRACT INDEX": "\n".join(
            [
                "## ACTIVE CONTRACT INDEX",
                "| Scope | Active contract | Current source | Enforcement |",
                "|---|---|---|---|",
                f"| cross-cutting | `DEC-001` | {cell} | review-only |",
            ]
        )
    }


class ActiveContractSourceFileTests(unittest.TestCase):
    """P0.4: `Current source` pointers must resolve to a real file, and a named
    §section must be checked against *that* file, not always the Blueprint."""

    def build(self, directory: str) -> tuple[Path, Path]:
        root = Path(directory)
        blueprint = root / "BLUEPRINT.md"
        blueprint.write_text(
            "# Blueprint\n\n## 1. Core\n\nDEC-001 is active.\n", encoding="utf-8"
        )
        control = root / "BUILD-CONTROL.md"
        return control, blueprint

    def test_missing_active_contract_source_file_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control, blueprint = self.build(directory)
            errors = BUILD_CONTEXT.validate_active_contracts(
                control, active_index_with_source("`MISSING-SPEC.md`"), blueprint
            )
            self.assertEqual(len(errors), 1)
            self.assertIn("does not exist", errors[0])
            self.assertIn("MISSING-SPEC.md", errors[0])

    def test_external_spec_section_is_checked_in_external_spec(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control, blueprint = self.build(directory)
            spec = Path(directory) / "SPEC.md"
            spec.write_text("# Spec\n\n## 2. Auth\n\nDetail.\n", encoding="utf-8")
            errors = BUILD_CONTEXT.validate_active_contracts(
                control, active_index_with_source("`SPEC.md §2. Auth`"), blueprint
            )
            self.assertEqual(errors, [])

    def test_missing_external_spec_section_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control, blueprint = self.build(directory)
            spec = Path(directory) / "SPEC.md"
            spec.write_text("# Spec\n\n## 2. Auth\n\nDetail.\n", encoding="utf-8")
            errors = BUILD_CONTEXT.validate_active_contracts(
                control, active_index_with_source("`SPEC.md §3. Missing`"), blueprint
            )
            self.assertEqual(len(errors), 1)
            self.assertIn("absent from SPEC.md", errors[0])
            # Must not be checked against the Blueprint's sections by mistake.
            self.assertNotIn("absent from Blueprint", errors[0])

    def test_blueprint_section_shorthand_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control, blueprint = self.build(directory)
            errors = BUILD_CONTEXT.validate_active_contracts(
                control, active_index_with_source("§1. Core"), blueprint
            )
            self.assertEqual(errors, [])
            bad_errors = BUILD_CONTEXT.validate_active_contracts(
                control, active_index_with_source("§9. Missing"), blueprint
            )
            self.assertEqual(len(bad_errors), 1)
            self.assertIn("absent from Blueprint", bad_errors[0])

    def test_multiple_explicit_sources_in_one_cell_are_each_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control, blueprint = self.build(directory)
            spec = Path(directory) / "SPEC.md"
            spec.write_text("# Spec\n\n## 2. Auth\n\nDetail.\n", encoding="utf-8")
            errors = BUILD_CONTEXT.validate_active_contracts(
                control,
                active_index_with_source("`BLUEPRINT.md §1. Core`, `SPEC.md §9. Missing`"),
                blueprint,
            )
            self.assertEqual(len(errors), 1)
            self.assertIn("absent from SPEC.md", errors[0])


class GlobSemanticsTests(unittest.TestCase):
    """P0.8: one shared glob matcher, used by both check-scope and exact-file
    inventory, with documented `*`/`**`/`?` semantics."""

    def test_single_star_matches_top_level_only(self) -> None:
        self.assertTrue(BUILD_CONTEXT.repo_glob_match("src/a.html", "src/*.html"))
        self.assertFalse(BUILD_CONTEXT.repo_glob_match("src/nested/a.html", "src/*.html"))

    def test_double_star_segment_matches_nested_and_top_level(self) -> None:
        pattern = "src/**/*.html"
        self.assertTrue(BUILD_CONTEXT.repo_glob_match("src/a.html", pattern))
        self.assertTrue(BUILD_CONTEXT.repo_glob_match("src/nested/a.html", pattern))
        self.assertTrue(BUILD_CONTEXT.repo_glob_match("src/a/b/c.html", pattern))
        self.assertFalse(BUILD_CONTEXT.repo_glob_match("other/a.html", pattern))

    def test_leading_double_star_matches_any_depth_including_top_level(self) -> None:
        pattern = "**/*.md"
        self.assertTrue(BUILD_CONTEXT.repo_glob_match("README.md", pattern))
        self.assertTrue(BUILD_CONTEXT.repo_glob_match("docs/a/b.md", pattern))
        self.assertFalse(BUILD_CONTEXT.repo_glob_match("README.txt", pattern))

    def test_double_star_with_literal_prefix_after_matches_nested_and_top_level(self) -> None:
        pattern = "src/**/js-*.html"
        self.assertTrue(BUILD_CONTEXT.repo_glob_match("src/js-app.html", pattern))
        self.assertTrue(BUILD_CONTEXT.repo_glob_match("src/nested/js-x.html", pattern))
        self.assertFalse(BUILD_CONTEXT.repo_glob_match("src/app.html", pattern))

    def test_trailing_double_star_matches_the_directory_and_everything_under_it(self) -> None:
        pattern = "build-history/**"
        self.assertTrue(BUILD_CONTEXT.repo_glob_match("build-history/P01.md", pattern))
        self.assertTrue(BUILD_CONTEXT.repo_glob_match("build-history/nested/deep.md", pattern))
        self.assertFalse(BUILD_CONTEXT.repo_glob_match("other/P01.md", pattern))

    def test_check_scope_and_exact_inventory_share_one_matcher(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src" / "nested").mkdir(parents=True)
            (root / "src" / "a.html").write_text("<x/>", encoding="utf-8")
            (root / "src" / "nested" / "b.html").write_text("<x/>", encoding="utf-8")
            found = {
                match.relative_to(root).as_posix()
                for match in BUILD_CONTEXT.expand_repo_glob(root, "src/*.html")
            }
            self.assertEqual(found, {"src/a.html"})
            self.assertTrue(BUILD_CONTEXT.matches_any("src/a.html", ["src/*.html"]))
            self.assertFalse(BUILD_CONTEXT.matches_any("src/nested/b.html", ["src/*.html"]))


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
            control = Path(directory) / "BUILD-CONTROL.md"
            errors = BUILD_CONTEXT.validate_active_contracts(
                control,
                self.pending_index(),
                self.blueprint(directory),
                allow_pending_inventory=True,
                warnings=warnings,
            )
            self.assertEqual(errors, [])
            self.assertIn("pending decision inventory", warnings[0])

    def test_pending_inventory_errors_outside_migration_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory) / "BUILD-CONTROL.md"
            errors = BUILD_CONTEXT.validate_active_contracts(
                control, self.pending_index(), self.blueprint(directory)
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

    def test_nonempty_canonical_with_empty_mirror_blocks(self) -> None:
        errors = self.mirror_errors(
            blueprint_index(["| `src/auth/**` | `DEC-014` | §2. Auth | review-only |"]),
            [],
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("mirror has no data rows", errors[0])

    def test_duplicate_scope_in_canonical_blocks(self) -> None:
        errors = self.mirror_errors(
            blueprint_index(
                [
                    "| `src/auth/**` | `DEC-014` | §2. Auth | review-only |",
                    "| `src/auth/**` | `DEC-099` | §2. Auth | review-only |",
                ]
            ),
            ["| `src/auth/**` | `DEC-014` | `BLUEPRINT.md §2. Auth` | review-only |"],
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("canonical Blueprint Active Contract Index has duplicate scope", errors[0])

    def test_duplicate_scope_in_mirror_blocks(self) -> None:
        errors = self.mirror_errors(
            blueprint_index(["| `src/auth/**` | `DEC-014` | §2. Auth | review-only |"]),
            [
                "| `src/auth/**` | `DEC-014` | `BLUEPRINT.md §2. Auth` | review-only |",
                "| `src/auth/**` | `DEC-099` | `BLUEPRINT.md §2. Auth` | review-only |",
            ],
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("ACTIVE CONTRACT INDEX mirror has duplicate scope", errors[0])

    def test_duplicate_stale_row_cannot_be_hidden_by_later_correct_row(self) -> None:
        errors = self.mirror_errors(
            blueprint_index(["| `src/auth/**` | `DEC-014`, `CHG-003` | §2. Auth | review-only |"]),
            [
                "| `src/auth/**` | `DEC-014` | `BLUEPRINT.md §2. Auth` | review-only |",
                "| `src/auth/**` | `DEC-014`, `CHG-003` | `BLUEPRINT.md §2. Auth` | review-only |",
            ],
        )
        self.assertTrue(errors)
        self.assertIn("ACTIVE CONTRACT INDEX mirror has duplicate scope", errors[0])

    def test_star_and_doublestar_scopes_are_distinct_keys(self) -> None:
        # P0.1b: collapsing every `*` used to make these the same key.
        self.assertNotEqual(
            BUILD_CONTEXT.normalize_scope_cell("`src/*`"),
            BUILD_CONTEXT.normalize_scope_cell("`src/**`"),
        )
        errors = self.mirror_errors(
            blueprint_index(
                [
                    "| `src/*` | `DEC-014` | §2. Auth | review-only |",
                    "| `src/**` | `DEC-099` | §2. Auth | review-only |",
                ]
            ),
            [
                "| `src/*` | `DEC-014` | `BLUEPRINT.md §2. Auth` | review-only |",
                "| `src/**` | `DEC-099` | `BLUEPRINT.md §2. Auth` | review-only |",
            ],
        )
        # Two genuinely different scopes must not be reported as a duplicate.
        self.assertEqual(errors, [])

    def test_mirror_glob_depth_difference_is_detected(self) -> None:
        # Canonical narrows to one level (`src/*`); the mirror still claims the
        # old wider `src/**` — a real routing difference, not just wording.
        errors = self.mirror_errors(
            blueprint_index(["| `src/*` | `DEC-014` | §2. Auth | review-only |"]),
            ["| `src/**` | `DEC-014` | `BLUEPRINT.md §2. Auth` | review-only |"],
        )
        self.assertTrue(errors)
        joined = " ".join(errors)
        self.assertIn("src/*", joined)
        self.assertIn("src/**", joined)

    def test_bold_and_backtick_markup_still_normalized_away(self) -> None:
        self.assertEqual(
            BUILD_CONTEXT.normalize_scope_cell("**cross-cutting**"),
            BUILD_CONTEXT.normalize_scope_cell("`cross-cutting`"),
        )
        errors = self.mirror_errors(
            blueprint_index(["| **cross-cutting** | `DEC-014` | §2. Auth | review-only |"]),
            ["| `cross-cutting` | `DEC-014` | `BLUEPRINT.md §2. Auth` | review-only |"],
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

    def test_duplicate_stage_id_is_detected_independently_of_last_row_view(self) -> None:
        text = self.plan(
            [
                "| `S16` | `PASS` | old claim |",
                "| `S16` | `ACTIVE` | new claim |",
            ]
        )
        self.assertEqual(BUILD_CONTEXT.stage_lifecycle_rows(text)["S16"], "ACTIVE")
        self.assertEqual(BUILD_CONTEXT.stage_lifecycle_duplicates(text), ["S16"])

    def test_no_duplicates_when_every_stage_id_is_unique(self) -> None:
        text = self.plan(["| `S01` | `PASS` | foundation |", "| `S16` | `ACTIVE` | building |"])
        self.assertEqual(BUILD_CONTEXT.stage_lifecycle_duplicates(text), [])

    def test_columns_are_found_by_header_name_at_any_position(self) -> None:
        # A human-facing plan wants a name column; the parser adapts to the
        # layout rather than forcing the layout to suit the parser.
        plan = "\n".join([
            "# P",
            "| Stage | ชื่อ | Lifecycle | คุณจะได้เห็น |",
            "|---|---|---|---|",
            "| `S16` | โหมดซ้อม | `VERIFY` | เล่นซ้อมแล้วเห็นแต้มเพิ่ม |",
            "| `S20` | หน้าครู | `DEFERRED` | ครูเห็นว่าเด็กคนไหนติด |",
        ])
        self.assertEqual(
            BUILD_CONTEXT.stage_lifecycle_rows(plan), {"S16": "VERIFY", "S20": "DEFERRED"}
        )

    def test_lifecycle_before_stage_still_parses(self) -> None:
        plan = "\n".join([
            "# P",
            "| Lifecycle | Stage | Note |",
            "|---|---|---|",
            "| `ACTIVE` | `S16` | building |",
        ])
        self.assertEqual(BUILD_CONTEXT.stage_lifecycle_rows(plan), {"S16": "ACTIVE"})

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

    def test_duplicate_stage_lifecycle_rows_block(self) -> None:
        rows = ["| `S16` | `PASS` | old claim |", "| `S16` | `ACTIVE` | new claim |"]
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(directory, lifecycle=rows)
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("appears more than once", err)

    def test_live_stage_without_state_stage_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(
                directory, stage="TBD", lifecycle=["| `S16` | `ACTIVE` | building |"]
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("no parseable current stage", err)

    def test_not_started_with_live_stage_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(
                directory,
                stage="NOT STARTED",
                lifecycle=["| `S16` | `ACTIVE` | building |"],
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("STATE declares `NOT STARTED`", err)

    def test_complete_with_live_stage_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(
                directory,
                stage="COMPLETE",
                lifecycle=["| `S16` | `VERIFY` | awaiting owner |"],
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("STATE declares `COMPLETE`", err)

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

    def test_markdown_link_target_satisfies_exact_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "Main.gs").write_text("x = 1\n", encoding="utf-8")
            control = self.build(
                directory,
                surfaces=["| code-routing | `CODEMAP.md` | topology change | `exact-files: src/*.gs` |"],
                extra_files={"CODEMAP.md": "# Map\n\n| file | notes |\n|---|---|\n| [Main.gs](src/Main.gs) | entry |\n"},
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertNotIn("absent from", err)

    def test_removed_listed_file_warns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "new.py").write_text("y = 2\n", encoding="utf-8")
            control = self.build(
                directory,
                surfaces=["| code-routing | `CODEMAP.md` | topology change | `exact-files: src/*.py` |"],
                extra_files={
                    "CODEMAP.md": "# Map\n\n- `src/new.py` — current\n- `src/removed.py` — stale\n"
                },
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertIn("src/removed.py", err)
            self.assertIn("no longer exists", err)

    def test_exact_inventory_ignores_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src" / "sub").mkdir(parents=True)
            (root / "src" / "sub" / "keep.py").write_text("z = 3\n", encoding="utf-8")
            control = self.build(
                directory,
                surfaces=[
                    "| code-routing | `CODEMAP.md` | topology change | `exact-files: src/**` |"
                ],
                extra_files={"CODEMAP.md": "# Map\n\n- `src/sub/keep.py` — current\n"},
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            # A directory path must never be reported as an unmapped "file".
            self.assertNotIn("src/sub`", err)

    def test_exact_inventory_ignores_backticked_glob_expression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "new.py").write_text("y = 2\n", encoding="utf-8")
            control = self.build(
                directory,
                surfaces=["| code-routing | `CODEMAP.md` | topology change | `exact-files: src/*.py` |"],
                extra_files={
                    "CODEMAP.md": "# Map\n\nCovers `src/*.py` (see `src/new.py`).\n"
                },
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertNotIn("absent from", err)

    def test_factor_quest_codemap_format_regression(self) -> None:
        """Regression fixture modeled on the real Factor Quest `CODEMAP.md`:
        a mixed table of Markdown links (`[Main.gs](src/Main.gs)`) and a
        shortcut table with the same link style. Every real file is listed
        this way somewhere in the document; the false 26-warning noise this
        skill originally produced against that project must not recur."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            server_files = ["Main.gs", "Auth.gs", "Sheet.gs"]
            client_files = ["index.html", "js-app.html", "js-game.html"]
            for name in server_files + client_files:
                (root / "src" / name).write_text("// code\n", encoding="utf-8")
            codemap_lines = [
                "# CODEMAP",
                "",
                "## Quick reference",
                "| want | open |",
                "|---|---|",
                *[f"| edit {name} | [{name}](src/{name}) |" for name in server_files],
                "",
                "## Server files",
                "| file | notes |",
                "|---|---|",
                *[f"| [{name}](src/{name}) | server |" for name in server_files],
                "",
                "## Client include order",
                "| order | file | notes |",
                "|---|---|---|",
                *[f"| {i} | [{name}](src/{name}) | client |" for i, name in enumerate(client_files, 1)],
            ]
            control = self.build(
                directory,
                surfaces=[
                    "| code-routing | `CODEMAP.md` | topology change | "
                    "`exact-files: src/*.gs, src/*.html` |"
                ],
                extra_files={"CODEMAP.md": "\n".join(codemap_lines)},
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertNotIn("absent from", err)
            self.assertNotIn("no longer exists", err)

    def test_known_drift_marker_in_a_current_surface_warns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(
                directory,
                open_changes="- CHG-005 reset button approved in chat, not written back to the spec",
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertIn("known-drift marker", err)


class SectionScopedSurfaceTests(unittest.TestCase):
    """P0.3: registered `File.md §Section` pointers must be validated and
    respected as a scan boundary, not silently widened to the whole file."""

    SPEC_BODY = "\n".join(
        [
            "# Spec",
            "",
            "## Current behavior",
            "",
            "new claim lives here.",
            "",
            "## Historical appendix",
            "",
            "old claim used to be true here.",
        ]
    )

    def doctor(self, control):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = BUILD_CONTEXT.command_doctor(control)
        return code, out.getvalue(), err.getvalue()

    def grep(self, control, terms, allow=None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = BUILD_CONTEXT.command_grep_current(control, terms, allow or [])
        return code, out.getvalue(), err.getvalue()

    def test_registered_missing_section_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = DoctorTests().build(
                directory,
                surfaces=["| interaction-spec | `SPEC.md §Does Not Exist` | change | semantic |"],
                extra_files={"SPEC.md": self.SPEC_BODY},
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("not usable", err)
            self.assertIn("Does Not Exist", err)

    def test_registered_directory_returns_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = DoctorTests().build(
                directory,
                surfaces=["| interaction-spec | `some_dir` | change | semantic |"],
                extra_files={"some_dir/placeholder.txt": "x"},
            )
            code, _, err = self.doctor(control)
            self.assertEqual(code, 2)
            self.assertIn("not usable", err)
            self.assertIn("directory", err)

    def test_registered_section_passes_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = DoctorTests().build(
                directory,
                surfaces=["| interaction-spec | `SPEC.md §Current behavior` | change | semantic |"],
                extra_files={"SPEC.md": self.SPEC_BODY},
            )
            code, _, _err = self.doctor(control)
            self.assertEqual(code, 0)

    def test_grep_current_respects_registered_section_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = DoctorTests().build(
                directory,
                surfaces=["| interaction-spec | `SPEC.md §Current behavior` | change | semantic |"],
                extra_files={"SPEC.md": self.SPEC_BODY},
            )
            code, out, _ = self.grep(control, ["old claim"])
            self.assertEqual(code, 0)
            self.assertIn("NO STALE HITS", out)

            code, out, _ = self.grep(control, ["new claim"])
            self.assertEqual(code, BUILD_CONTEXT.STALE_HIT_EXIT)
            self.assertIn("HIT\tSPEC.md:", out)

    def test_same_file_two_nonoverlapping_sections_are_distinct_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = DoctorTests().build(
                directory,
                surfaces=[
                    "| interaction-spec | `SPEC.md §Current behavior` | change | semantic |",
                    "| teaching-spec | `SPEC.md §Historical appendix` | change | semantic |",
                ],
                extra_files={"SPEC.md": self.SPEC_BODY},
            )
            text = BUILD_CONTEXT.read_text(control)
            sections = BUILD_CONTEXT.h2_sections(text)
            refs = BUILD_CONTEXT.current_surfaces(control, sections)
            spec_refs = [ref for ref in refs if ref.path.name == "SPEC.md"]
            self.assertEqual(len(spec_refs), 2)
            self.assertEqual({ref.section for ref in spec_refs}, {"Current behavior", "Historical appendix"})
            # Neither role collides, so doctor must not block on duplicate-role grounds.
            code, _, err = self.doctor(control)
            self.assertEqual(code, 0)
            self.assertNotIn("claim role", err)

            # Both sections are individually scannable and mutually exclusive.
            code, out, _ = self.grep(control, ["new claim"])
            self.assertEqual(code, BUILD_CONTEXT.STALE_HIT_EXIT)
            self.assertIn("HIT", out)
            code, out, _ = self.grep(control, ["old claim"])
            self.assertEqual(code, BUILD_CONTEXT.STALE_HIT_EXIT)
            self.assertIn("HIT", out)


class LastTransitionTests(unittest.TestCase):
    """P0.6: the newest `### PRG-###`/`CHG-###` heading must be found even when
    its entry body is larger than one fixed-size tail read, and the id grammar
    must recognize the repository's real suffix/maintenance-id forms."""

    def write(self, directory: str, declared: str, log_body: str) -> tuple[Path, dict[str, str], Path]:
        root = Path(directory)
        log = root / "BUILD-LOG-P02.md"
        log.write_text(log_body, encoding="utf-8")
        control = root / "BUILD-CONTROL.md"
        control.write_text("# Build Control\n", encoding="utf-8")
        sections = {
            "STATE": "\n".join(
                [
                    "## STATE",
                    f"- Last transition: `{declared}`",
                    f"- Active history log: `{log.name}`",
                ]
            )
        }
        return control, sections, log

    def test_latest_entry_larger_than_8kb_is_found(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            padding = "x" * 9000
            log_body = (
                "### [2026-01-01] CHG-001 · old\n- body\n\n"
                f"### [2026-01-02] PRG-S16A · new\n- {padding}\n"
            )
            _control, _sections, log = self.write(directory, "CHG-001", log_body)
            latest, unrecognized = BUILD_CONTEXT.find_latest_audit_heading(log)
            self.assertEqual(latest, "PRG-S16A")
            self.assertFalse(unrecognized)

    def test_latest_prg_stage_maintenance_id_is_found(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control, sections, _log = self.write(
                directory, "CHG-094", "### [2026-08-05] PRG-S16A · maintenance\n- body\n"
            )
            warnings = BUILD_CONTEXT.last_transition_warnings(control, sections)
            self.assertEqual(len(warnings), 1)
            self.assertIn("PRG-S16A", warnings[0])

    def test_legacy_suffixed_prg_and_chg_ids_are_found(self) -> None:
        for heading, expected in (
            ("### [2026-01-01] CHG-012b · legacy suffix\n", "CHG-012B"),
            ("### [2026-01-01] PRG-015a · legacy suffix\n", "PRG-015A"),
            ("### [2026-01-01] PRG-015a.1 · legacy revision\n", "PRG-015A.1"),
        ):
            with self.subTest(heading=heading), tempfile.TemporaryDirectory() as directory:
                _control, _sections, log = self.write(directory, "X", heading + "- body\n")
                latest, unrecognized = BUILD_CONTEXT.find_latest_audit_heading(log)
                self.assertEqual(latest, expected)
                self.assertFalse(unrecognized)

    def test_matching_declared_id_produces_no_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control, sections, _log = self.write(
                directory, "PRG-S16A", "### [2026-08-05] PRG-S16A · maintenance\n- body\n"
            )
            self.assertEqual(BUILD_CONTEXT.last_transition_warnings(control, sections), [])

    def test_no_heading_before_cap_returns_warning_or_explicit_unknown_not_silent_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_body = "### Random status note\n- nothing parseable here\n" * 5
            control, sections, _log = self.write(directory, "CHG-001", log_body)
            warnings = BUILD_CONTEXT.last_transition_warnings(control, sections)
            self.assertEqual(len(warnings), 1)
            self.assertIn("could not find a recognized", warnings[0])

    def test_empty_log_with_no_headings_at_all_is_silent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control, sections, _log = self.write(directory, "CHG-001", "# Log\n\n(nothing yet)\n")
            self.assertEqual(BUILD_CONTEXT.last_transition_warnings(control, sections), [])


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

    def grep(
        self,
        control: Path,
        terms: list[str],
        allow: list[str] | None = None,
        *,
        use_regex: bool = False,
    ):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = BUILD_CONTEXT.command_grep_current(
                control, terms, allow or [], use_regex=use_regex
            )
        return code, out.getvalue(), err.getvalue()

    def test_hits_in_registered_surfaces_return_the_documented_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, out, _err = self.grep(self.build(directory), ["14 source files"])
            self.assertEqual(code, BUILD_CONTEXT.STALE_HIT_EXIT)
            self.assertIn("HIT\tCODEMAP.md:3", out)

    def test_cold_history_is_never_searched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _code, out, _err = self.grep(self.build(directory), ["14 source files"])
            self.assertNotIn("BUILD-LOG", out)

    def test_no_hits_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, out, _err = self.grep(self.build(directory), ["a claim nobody wrote"])
            self.assertEqual(code, 0)
            self.assertIn("NO STALE HITS", out)

    def test_allow_marks_a_surviving_hit_as_intentionally_current(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, out, _err = self.grep(
                self.build(directory), ["14 source files"], allow=["CODEMAP.md:3"]
            )
            self.assertEqual(code, 0)
            self.assertIn("ALLOWED\tCODEMAP.md:3", out)

    def test_reworded_stale_claim_is_a_clean_literal_grep_not_semantic_proof(self) -> None:
        """P0.7: `grep-current` is a literal check. Documenting the old claim as
        `13 files` and searching for a reworded `13 child files` legitimately
        finds nothing — that is expected, not a bug, and the docs must say so."""
        with tempfile.TemporaryDirectory() as directory:
            code, out, _err = self.grep(self.build(directory), ["13 child files"])
            self.assertEqual(code, 0)
            self.assertIn("NO STALE HITS", out)
            skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("not semantic proof", skill)
            self.assertIn("checks that the exact declared stale terms", skill)

    def test_regex_mode_is_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, out, _err = self.grep(
                self.build(directory), [r"\d+ SOURCE files"], use_regex=True
            )
            self.assertEqual(code, BUILD_CONTEXT.STALE_HIT_EXIT)
            self.assertIn("HIT\tCODEMAP.md:3", out)

    def test_invalid_regex_term_exits_with_the_documented_error_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            control = self.build(directory)
            with self.assertRaises(BUILD_CONTEXT.BuildContextError):
                BUILD_CONTEXT.command_grep_current(control, ["("], [], use_regex=True)

    def test_regex_mode_still_never_searches_cold_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _code, out, _err = self.grep(
                self.build(directory), [r"\d+ source files"], use_regex=True
            )
            self.assertNotIn("BUILD-LOG", out)


class WorktreeStateTests(unittest.TestCase):
    """A declared Working-tree state is a claim about the repo — check it."""

    def build(self, directory: str, declared: str, *, dirty: bool, untracked: bool = False):
        import subprocess

        root = Path(directory)
        (root / "tracked.txt").write_text("one\n", encoding="utf-8")
        for args in (["init", "-q"], ["add", "-A"], ["-c", "user.email=t@t", "-c", "user.name=t",
                                                     "commit", "-qm", "base"]):
            subprocess.run(["git", *args], cwd=root, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if dirty:
            (root / "tracked.txt").write_text("two\n", encoding="utf-8")
        if untracked:
            (root / "stray.log").write_text("noise\n", encoding="utf-8")
        control = root / "BUILD-CONTROL-widget.md"
        control.write_text("\n".join([
            "## ENTRYPOINT", "- Project root: `.`", "",
            "## VERSION CONTROL",
            "- Mode: `git`",
            "- Repository root: `.`",
            f"- Working-tree state: `{declared}`",
        ]), encoding="utf-8")
        sections = BUILD_CONTEXT.h2_sections(control.read_text(encoding="utf-8"))
        return BUILD_CONTEXT.worktree_state_warnings(control, sections)

    def test_dirty_claim_after_the_commit_landed_warns(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            w = self.build(d, "DIRTY \u2014 S16B waiting for the owner", dirty=False)
            self.assertEqual(len(w), 1)
            self.assertIn("part of the", w[0])

    def test_clean_claim_with_modified_tracked_files_warns(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            w = self.build(d, "CLEAN", dirty=True)
            self.assertEqual(len(w), 1)
            self.assertIn("1 tracked file(s) are modified", w[0])

    def test_matching_claims_are_silent(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.build(d, "CLEAN", dirty=False), [])
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.build(d, "DIRTY \u2014 mid-stage", dirty=True), [])

    def test_untracked_files_do_not_falsify_a_clean_claim(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.build(d, "CLEAN", dirty=False, untracked=True), [])

    def test_absent_field_is_backward_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            control = root / "BUILD-CONTROL-widget.md"
            control.write_text("## ENTRYPOINT\n- Project root: `.`\n\n"
                               "## VERSION CONTROL\n- Mode: `git`\n- Repository root: `.`\n",
                               encoding="utf-8")
            sections = BUILD_CONTEXT.h2_sections(control.read_text(encoding="utf-8"))
            self.assertEqual(BUILD_CONTEXT.worktree_state_warnings(control, sections), [])


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

    def test_checkpoint_advance_belongs_to_the_authorized_commit(self) -> None:
        self.assertIn("Working-tree state", self.skill)
        self.assertIn("Working-tree state: `CLEAN`", self.reference)
        self.assertRegex(self.skill, r"part of the authorized commit, not a chore")
        # The owner is often non-technical; the request must describe the effect.
        self.assertRegex(self.skill, r"save point they can return to")

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
        # Structure is not detail: the owner needs a skimmable name per stage.
        self.assertRegex(self.plan_format, r"Give every stage a short name column")
        self.assertRegex(self.plan_format, r"Cutting premature \*\*detail\*\* and cutting \*\*structure\*\*")
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

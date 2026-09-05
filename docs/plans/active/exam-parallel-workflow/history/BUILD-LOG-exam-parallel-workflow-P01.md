# BUILD-LOG — exam-parallel-workflow — P01

Immutable chronological evidence. Never current authority (see BLUEPRINT/BUILD-CONTROL for current truth).

---

## PRG-001 — S01 green baseline

- Date: 2026-09-04
- Branch: `feat/exam-parallel-workflow` · Baseline: `cb30353`
- Worktree: `~/Documents/chatgpt-math-doc-generator/work/exam-parallel-workflow`
- Env: Python 3.9.6 (no pytest → run test file directly)
- Command: `cd thai-math-exam-production && python3 tests/test_exam_state.py -v`
- Result: **12/12 OK** (ExamProjectTests) — initializer, validator, item_meta all green.
- Note: `python3 -m unittest discover` fails (tests dir not a package, no `__init__.py`); canonical command = run the test file directly. Recorded for all later validator/init stages.
- Scope check: no product files touched; only control docs + AGENTS.md untracked.
- Checkpoint: not committed (commit only on explicit user ask).

---

## PRG-002 — S02 schema 1.1.0 + validator read (backward-compat)

- Date: 2026-09-04 · Stage: S02 · Contracts: DEC-006
- Changed (managed paths):
  - `scripts/validate_exam_state.py` — `SCHEMA_VERSION`→"1.1.0"; add `SUPPORTED_SCHEMA_VERSIONS={1.0.0,1.1.0}`, `PRODUCTION_MODES`; `_validate_roots` now takes the authoritative version from the project doc, requires every sibling doc to match it, and reads `production_mode` (absent⇒original, enum-checked). No parallel/anchor/workload enforcement yet (S04).
  - `references/exam-project-contract.md` — document 1.1.0 fields (production_mode, parallel block) + "Schema versions and compatibility" section; 1.0.0 kept as accepted legacy, no migration.
  - `tests/test_exam_state.py` — new `SchemaCompatibilityTests` (5): legacy 1.0.0 valid, 1.1.0 original valid, 1.1.0 parallel valid at read gate, mixed versions rejected, unknown production_mode rejected.
- Tests: `python3 tests/test_exam_state.py -v` → **17/17 OK** (12 legacy + 5 new).
- Real-data regression: real 1.0.0 closed project (22 items / 46 variants) → validator PASS.
- Current-truth reconcile: exam-project-contract.md now states 1.1.0 current / 1.0.0 accepted. No claim retired beyond the "1.0.0" current-version wording.
- Checkpoint: not committed (awaiting user ask).

---

## CHG-note (pre-approval bounce-back, S04) — workload enforcement moved off the validator

- At S04 boundary a what-level question surfaced (flagged in plan "Not yet specified"): batch workload lives in markdown (GATE-6-BATCH-*.md), not JSON, so the validator cannot prove it. User chose option **A** (2026-09-05): workload enforced at BATCH-PROPOSAL template + review, not the JSON validator; no batch grouping added to JSON.
- Contract transaction (current surfaces updated BEFORE code): BLUEPRINT DEC-005 refined + new DEC-011; Active Contract Index (BLUEPRINT + control mirror) validator row DEC-005→DEC-011, BATCH template row +DEC-011; §4, §6, Edge cases, Acceptance #3 reworded; plan S04 retitled + "Not yet specified" workload line graduated.

---

## PRG-003 — S03 initializer: production_mode + EXAM-DESIGN.md

- Date: 2026-09-04 · Stage: S03 · Contracts: DEC-006, DEC-002
- Changed (managed paths):
  - `scripts/init_exam_project.py` — `SCHEMA_VERSION`→"1.1.0"; add `PRODUCTION_MODES`, `DIFFICULTY_RELATIONS`, `EXAM-DESIGN.md` in `STATE_FILES`, `ASSETS_DIR`/`EXAM_DESIGN_TEMPLATE`, `SPINE_SECTIONS`/`PARALLEL_SPINE_SECTIONS`, `_exam_design_skeleton()`. `initialize_exam_project` gains `production_mode`/`source_exam_id`/`source_exam_path`/`difficulty_relation`; validates parallel args; writes `production_mode` + conditional `parallel` block (reference_frozen=True); creates `EXAM-DESIGN.md` (prefers `assets/EXAM-DESIGN.template.md` if present — created S06 — else the mode-aware skeleton). CLI flags added + wired.
  - `tests/test_exam_state.py` — owned-state set now includes `EXAM-DESIGN.md`; new `InitializerModeTests` (3): original 1.1.0 + design note, parallel reference block + source-critique spine, parallel refuses missing source. Fixed S02 tests for the 1.1.0 default (legacy test now downgrades explicitly; mixed-version test flips project to 1.0.0 vs 1.1.0 siblings).
- Tests: `python3 tests/test_exam_state.py -v` → **20/20 OK**. Real 1.0.0 closed project → PASS.
- Demo: parallel init → exam-project.json `production_mode=parallel` + parallel block; EXAM-DESIGN.md carries Reference analysis / ### Equivalence diagnosis / Parallel contract Spine.
- Current-truth reconcile: initializer now the source of the `EXAM-DESIGN.md` state file (DEC-002). The rich asset template + init-reads-template wiring is S06 — until then init emits the skeleton.
- Note (forward): S06 must create `assets/EXAM-DESIGN.template.md` and confirm init's template-substitution (`<ชื่อข้อสอบ>`→title) covers mode/contract fill; extend substitution if the template needs more than the title placeholder.
- Checkpoint: not committed (awaiting user ask).

---

## PRG-004 — S04 validator: parallel block + per-item anchor (workload → template, DEC-011)

- Date: 2026-09-05 · Stage: S04 · Contracts: DEC-006, DEC-004, DEC-011
- Changed (managed paths):
  - `scripts/validate_exam_state.py` — add `DIFFICULTY_RELATIONS`; new `_validate_parallel()` (parallel block present + source fields nonempty + relation valid + reference_frozen True; original mode rejects a stray parallel block); wired after `_validate_roots`; `_validate_items` now requires nonempty `anchor` per item in parallel mode (only where items are validated). No batch/workload check (DEC-011).
  - `tests/test_exam_state.py` — new `ParallelValidationTests` (5) + `init_parallel` helper.
- Tests: **25/25 OK**. Real 1.0.0 closed project → PASS. S02 parallel-read test still green (block was well-formed by design).
- Current-truth reconcile: none newly stale (contract already updated in the S04 bounce-back transaction above).
- Checkpoint: not committed (awaiting user ask).

---

## PRG-005 — S05 lint check_exam_design.py

- Date: 2026-09-05 · Stage: S05 · Contracts: DEC-002, DEC-003
- Changed (managed paths):
  - `scripts/check_exam_design.py` (new) — mirror of check_note_sections.py. SPINE (9) + parallel PARALLEL_SPINE (Reference analysis, Parallel contract); Reference analysis requires `### Equivalence diagnosis` (Thai วินิจฉัย accepted); mode read from `## Contract` `Mode:` line or `--mode`; unknown `##` → REVIEW; original note carrying a parallel section → REVIEW (not FAIL). Exit 0/1/2. stdlib only, 3.9-safe.
  - `tests/test_exam_state.py` — new `ExamDesignLintTests` (5): init parallel/original notes PASS; missing parallel Spine → FAIL; missing equivalence diagnosis → FAIL; stray parallel section in original → REVIEW/exit 0.
- Tests: **30/30 OK**. provider-neutral scan (globs scripts/*.py) still green with the new script.
- Current-truth reconcile: none stale; check_exam_design.py registered under Skill triggering? no — it is a script; lint coverage noted in Active Contract Index (already lists it, test-enforced).
- Note (forward): SPINE list here is the enforcement twin of init's SPINE_SECTIONS and the S06 template — S06 must keep all three in step (template PASSes this lint).
- Checkpoint: not committed (awaiting user ask).

---

## PRG-006 — S06 EXAM-DESIGN.template.md (rich, material-design twin)

- Date: 2026-09-05 · Stage: S06 · Contracts: DEC-002, DEC-003, DEC-004
- Changed (managed paths):
  - `assets/EXAM-DESIGN.template.md` (new) — tiered rich template mirroring MATERIAL-DESIGN.template.md: Spine (9) + parallel source-critique spine (Reference analysis→### Equivalence diagnosis→Parallel contract, wrapped in `<!-- parallel:start/end -->`), `---` divider, Conditional (Batch workload policy, Decisions), Opt-in (Open questions), "current not cumulative" close. English headings + Thai guidance; content-boundary reminders (observe-only / systemic-not-per-item / recommend); "point at JSON, don't copy tables" (DEC-002).
  - `scripts/init_exam_project.py` — new `_render_exam_design()`: parallel keeps the block (drops markers, substitutes `<SOURCE_EXAM_ID>`); original strips the block + the reference Contract line; substitutes `<ชื่อข้อสอบ>`/`<MODE>`. init now renders from the asset (skeleton = fallback only).
- Tests: **30/30 OK** (existing init/lint tests now exercise the template path). Rendered original note = 12 sections, no parallel; rendered parallel note = Mode parallel + reference id filled; both `PASS: Spine complete.`
- Current-truth reconcile: init's EXAM-DESIGN.md now sourced from the asset template (the S03 forward-note is discharged). Template SPINE ↔ check_exam_design SPINE ↔ init SPINE_SECTIONS in step.
- Gate: richness is a teacher judgement — awaiting user's read of the note.
- User judgment (2026-09-05): PASS. Confirmed two changes-from-real: (1) drop per-project "Ordered workflow Gate 1–11" → moves to SKILL.md/workflow ref (S08); (2) Whole-paper = acceptance criteria in EXAM-DESIGN.md, executed review stays a separate GATE-8 doc.
- Checkpoint: not committed (awaiting user ask).

---

## PRG-007 — S07 BATCH-PROPOSAL.template.md + batch lint

- Date: 2026-09-05 · Stage: S07 · Contracts: DEC-004, DEC-005, DEC-011
- Changed (managed paths):
  - `assets/BATCH-PROPOSAL.template.md` (new) — grounded in real GATE-6-BATCH-01. Header lines Status/Items/**Workload** (DEC-011 point, with note "template+review not validator, batch not in JSON"); per-item block {เป้าหมาย, parallel: anchor/preserve/transform, โจทย์/ตัวเลือก/เฉลย, working solution (แก้ใหม่จากศูนย์), ตัวลวงรายตัว, เหตุผลความยากเทียบ anchor, config lock}; Batch review notes (contrast + parallel leakage); Decision requested; Approved decision. `<!-- parallel:start/end -->` marks the parallel-only per-item lines.
  - `scripts/check_exam_design.py` — add `--batch` mode: `scan_batch()` checks Status/Items/Workload header lines + Batch review notes + a decision section + ≥1 item block; mode-accurate PASS/FAIL summary.
  - `tests/test_exam_state.py` — new `BatchProposalLintTests` (3): template passes; missing Workload → FAIL; missing Batch review notes → FAIL.
- Tests: **33/33 OK**. Batch template `PASS: batch skeleton complete.`; design lint still `PASS: Spine complete.`
- Current-truth reconcile: none stale (batch template is new; workload enforcement now has its mechanical home per DEC-011).
- Checkpoint: not committed (awaiting user ask).

---

## PRG-008 — S08 SKILL.md + workflow reference (parallel overlay)

- Date: 2026-09-05 · Stage: S08 · Contracts: DEC-001, DEC-007, DEC-008, DEC-005
- Changed (managed paths):
  - `SKILL.md` — SKILL-VERSION → 2026.09.05; description +parallel set +EXAM-DESIGN.md; Start-or-resume adds parallel init invocation, EXAM-DESIGN.md creation + `check_exam_design.py` (incl. `--batch`); new "## Production modes" (original/parallel + parallel rules); gate 6 reworded to workload units; closing note routes the full gate procedure to the workflow reference (not duplicated per project — DEC-007) and requires JSON↔EXAM-DESIGN.md two-surface sync (point-not-copy, DEC-002).
  - `references/exam-production-workflow.md` — Foundation names EXAM-DESIGN.md + GATE-N archival; drafting line → workload units + BATCH template + `--batch` lint; new "## Parallel Mode Overlay" (Gate 1/3/4/5/6/7/8/9 additions + relation levels + validator-only-checks-structure caveat).
- Tests: **33/33 OK**. provider-neutral scan green with edited SKILL/references.
- Scope: `git status` = only `thai-math-exam-production/**` + `docs/**` + `AGENTS.md`; **0 thai-math-docx changes** (DEC-010 held).
- Current-truth reconcile: SKILL.md gate 6 now matches DEC-005 (workload units, was "three items"); workflow reference is the single home of the gate procedure. No stale claim left.
- Checkpoint: not committed (awaiting user ask).

---

## PRG-009 — S09 forward test (real parallel EXAM-DESIGN.md)

- Date: 2026-09-05 · Stage: S09 · Contracts: DEC-002, DEC-003, DEC-004, DEC-009
- Artifact location: **`~/Documents/chatgpt-math-doc-generator/real-numbers/exam-projects/real-number-quiz-parallel-B/`** — a real exam project in the doc-generator repo, NOT in the skill repo/worktree. The skill checkpoint does not include it.
- Did: `init_exam_project.py` (worktree) → parallel project B from the approved real-number quiz (source frozen), validate scaffold PASS. Filled `exam-state/EXAM-DESIGN.md` with real analysis grounded in reference anchors (Q01/Q02/Q03 + W01) and blueprint 4/7/7/4 · 6/12/4: Reference analysis table (observe) → Equivalence diagnosis 5-dim (diagnose) → Parallel contract preserve/transform/avoid per anchor (recommend). Not the 22 items / no batches / no DOCX (DEC-009).
- Tests/lint: `check_exam_design.py EXAM-DESIGN.md` → PASS: Spine complete. Note size 5180 chars (concise, current-not-cumulative).
- Proof: the template + lint produce a teacher-judgeable equivalence note from real data using only markdown (DEC-008).
- Gate: awaiting teacher's judgment — "can I decide equivalence from this markdown without opening both DOCX?" If insufficient → adjust template/lint (bounce to S06/S05) before completion.
- User judgment (2026-09-05): PASS — equivalence judgeable from markdown alone.
- Checkpoint: not committed (awaiting user ask).

---

## PRG-010 — S10 completion verification

- Date: 2026-09-05 · Stage: S10 (final) · Contracts: all
- Verification sweep (all green): tests **33/33 OK**; lints PASS ×3 (EXAM-DESIGN template, BATCH template `--batch`, forward-test note); real 1.0.0 project (22/46) validator PASS; `py_compile scripts/*.py` OK on 3.9; skill structure complete; managed-path diff closed to `thai-math-exam-production/**` + `docs/**` + `AGENTS.md`; **0 thai-math-docx changes** (DEC-010).
- Acceptance criteria 1–6 (BLUEPRINT §Acceptance): all met. DOCX intentionally not produced (DEC-008); forward test used representative anchors (DEC-009).
- Disclosed risk: A5 (AGENTS.md add/add vs thai-docx branch at eventual merge — resolvable by concatenating slug-marked blocks; UNVERIFIED until merge).
- STATE → build stages COMPLETE. Release (commit on `feat/exam-parallel-workflow` + `skill-release` mirror/push/install) is user-gated and NOT done. AGENTS owned block + active plan bundle kept until release; archive to `completed/` at release time.
- Forward-test artifact `real-number-quiz-parallel-B/` stays in the doc-generator repo for the teacher to keep or discard — not part of the skill release.
- Checkpoint: not committed (awaiting user ask).

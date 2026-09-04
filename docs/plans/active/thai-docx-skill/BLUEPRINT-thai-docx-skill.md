# BLUEPRINT — thai-docx skill

Version: 1.4 (patched after scrutiny rounds 1–4 + engine merge `3f978a4`, 2026-09-04; see `PLAN-SCRUTINY-thai-docx-skill.md`) · Owner: zenithjuno · Status: **Approved design, NOT yet built** — scrutiny verdict: content build-ready
This file is the current task contract and routing source for the `thai-docx` skill build.
Control: `BUILD-CONTROL-thai-docx-skill.md` (created with the CONSTRUCTION_PLAN).
Companion plan: `CONSTRUCTION_PLAN-thai-docx-skill.md` (same slug).

## Original problem (anchor)
Producing a plain Thai Word `.docx` (no equations) currently forces borrowing the whole
`thai-math-docx` skill, whose OMML/equation ceremony is irrelevant, muddies triggering, and
loads a heavier surface than prose work needs. We want a `thai-docx` skill that reuses the
mature `thai-math-docx` pipeline minus everything math/OMML, without creating drifting duplicate code.

## Task contract

| Field | Locked value |
|---|---|
| Goal | A new `thai-docx` skill that produces/repairs/audits/renders plain Thai `.docx` (no math), riding the mature `thai-math-docx` engine's math-free core, with no code duplication. |
| User value | The teacher (a non-standalone "docx bundle" author) gets correct Thai Word docs for prose/tables/handouts/letters/reports without math ceremony, and an agent triggered on it never reads or executes math code. |
| Scope | New folder `~/.codex/skills/thai-docx/`; a bounded, test-guarded general/math **seam refactor** inside `~/.codex/skills/thai-math-docx/scripts/`; a one-line carve-out edit to `thai-math-docx` SKILL.md; follow-on cleanup (fonts, workspace tools, memory). |
| Source of truth | Engine = `~/.codex/skills/thai-math-docx/scripts/` (builder core, layout, `audit_docx_font_defaults.py`, `audit_docx_insertion_safety.py`, `render_docx.py`, `contact_sheet.py`, `thai_math_docx_qa.py`). Font repair = `~/.codex/skills/thai-font-normalize/scripts/fix-thai-font`. Font standard = TH Sarabun New. |
| Constraints | (a) thai-math-docx routing + behavior must remain provably unchanged; (b) thai-docx's general path must load/execute NO math module; (c) no duplicated engine code (Path 1 reuse by absolute path); (d) font standard = TH Sarabun New only, no PSK font installed; (e) reference siblings by absolute `~/.codex/skills` path, no hardcoded codex-runtime python; (f) bump `SKILL-VERSION` on every skill edit. |
| Acceptance criteria | 1) thai-docx generates+repairs+renders a Thai prose/table doc **including prose with numeric relations (e.g. `คะแนน ≥ 80`)**, Thai correct (New), QA gate PASS with `math.required=false`. 2) thai-math-docx baseline tests/QA pass identically before/after the seam **except the one gate-coverage test deliberately updated by CHG-001** (math-in-plain-text present for math docs, legitimately absent for declared math-free). 3) A test proves no math authoring/scanner module loads on the general path (`audit_docx_math_in_text`, `thai_math_expr`, `thai_math_source_adapter` absent from `sys.modules`; `audit_docx_omml` excluded per Ω2) — asserted **in an isolated subprocess / clean interpreter** (not the `unittest discover` process, where sibling tests pre-import those modules — R2-F6). 4) Preflight fails loudly when a dep (engine/font-normalize/LibreOffice/TH Sarabun New) is missing. 5) Triggers are disjoint from thai-math-docx. |
| Verification | Automated tests (regression baseline diff, no-leak sys.modules assertion, seam lazy-import proof, thai-docx end-to-end render+QA on a fixture), plus a rendered contact sheet reviewed by the teacher. |
| Out of scope | Full SVG-diagram apparatus (visuals.md); PDF/image→DOCX reconstruction; `pdf` skill integration; the broader thai-math-docx size/grammar refactor (stays parked). |

## 0. Purpose & elevator pitch
`thai-docx` is a prose-first sibling of `thai-math-docx` for Thai Word documents that contain **no
mathematical notation** — handouts, letters, reports, forms, school/admin documents, and repair of
imported Thai `.docx`. It is an **orchestrator**: it borrows the mature engine and the font-normalizer
rather than reimplementing them. It is deliberately **not standalone** — it depends on sibling skills in
the docx bundle, and it must declare and preflight those dependencies.

## 1. Core model / approach — Path 1 (reuse + bounded seam)

Iron rules of this build:
1. **Reuse, don't duplicate.** thai-docx contains thin wrappers + docs + a prose entrypoint; the heavy
   lifting stays in `thai-math-docx/scripts/`, reached by absolute path (CLI shell-out) or `sys.path`
   bootstrap (Python import), following the repo's existing cross-skill pattern (`generator-template.py`).
2. **Draw the general/math seam inside thai-math-docx, minimally.** The general engine becomes cleanly
   importable with **zero math dependency**, so thai-docx rides a math-free core.
3. **Never touch the crown jewel unguarded.** Every seam change is covered by a regression baseline of
   thai-math-docx's own tests/QA (red-green): behavior identical before/after for math docs — the sole
   intended change is CHG-001 (a declared math-free doc no longer runs the plain-text-math scan).
4. **Font standard = TH Sarabun New.** Legacy fonts (PSK/Angsana/…) are normalized *in the document* to
   New (via `fix-thai-font`) before render; no legacy font is installed on the machine.

### The seam (what changes in thai-math-docx)
Facts (verified): general/math is already ~90% separated. Clean/math-free already:
`audit_docx_font_defaults`, `audit_docx_insertion_safety`, `render_docx`, `contact_sheet`,
`thai_math_docx_layout`. `thai_math_docx_qa.py` is already math-optional via a `math.required` contract
flag but **hard-imports** the math audit modules at top. `thai_math_docx_builder.py` mixes general funcs
(L60–180, 476–622) with a **contiguous** OMML block (L181–475) and imports `normalize_math_string`
(used once, L370, math path only). `append_parts` is the one general→math bridge (dispatches when a part
is `type:"math"`).

Minimal seam moves (finalized after scrutiny 2026-09-02; **the leak is a call, not only an import**):
- `thai_math_docx_qa.py` (line numbers as of merged engine `3f978a4`): **gate the call site at `qa.py:503`
  `math_in_text.scan(...)`** on math context (`math.required` true or `m:oMath` present) — NOT run unconditionally
  (it currently runs inside the `if not package_failures:` block for every doc, check id emitted L508). **Also
  relocate the top-level `import audit_docx_math_in_text` (qa.py:19) into that gated math branch** (R3-F8: gating
  only the *call* leaves L19 loading the module at import). This makes the general path load no `audit_docx_math_in_text`,
  AND fixes the prose false-positive (see §3 / F2). It changes one gate-coverage test's expectation → **CHG-001**.
  **`audit_docx_omml` is left AS-IS (Ω2):** the hardened engine's `_audit_omml` (L214) now runs unconditionally with
  `allow_no_math=True` (L481 call) — a passive structural validator that PASSes trivially on a math-free doc and never
  false-fails, so it is NOT gated and NOT in the no-leak set. The seam gates only the check that is *wrong* on prose.
- `thai_math_docx_builder.py`: make only the single `from thai_math_source_adapter import normalize_math_string`
  (L26, used once at L370 on the `type:"math"` path) **lazy**. Verified sufficient: importing the general
  builder then loads zero math modules; the OMML block (L181–474) physically stays put and runs only on the
  math path via `append_parts`. **Do NOT relocate the OMML block** (SQ1: zero no-leak benefit, that is the
  parked refactor). Preserve the public general API behavior.
- The general core exposes a math-free surface thai-docx imports. thai-docx must also never `import thai_math_expr`.

### thai-docx workflow (hand-off order)
```
generate / repair Thai docx (prose, tables, header/footer, basic image)
  → thai-math-docx ENGINE: builder CORE + font-default & insertion-safety audits
  → thai-font-normalize (fix-thai-font): legacy/PSK → TH Sarabun New
  → thai-math-docx ENGINE: render_docx (+ contact_sheet) + qa gate (math.required=false)
```

## Active Contract Index

| Scope | Active contract | Current source | Enforcement |
|---|---|---|---|
| `thai-docx/scripts/**` (wrappers, preflight, prose entrypoint) | DEC-002, DEC-007 | §1 Core model, §Dependency & routing | tests (end-to-end, no-leak) |
| `thai-docx/SKILL.md` + `references/**` | DEC-004, DEC-005, DEC-007 | §Task contract, §Trigger, §Dependency & routing | review + trigger check |
| `thai-math-docx/scripts/thai_math_docx_qa.py` (gate scan call L503 + relocate its import L19; omml left as-is per Ω2) | DEC-002, DEC-003, DEC-009, CHG-001 | §1 The seam | regression baseline + gated-call/no-leak test + updated gate-coverage test |
| `thai-math-docx/scripts/thai_math_docx_builder.py` (lazy math import only — no OMML relocation) | DEC-002, DEC-003 | §1 The seam | regression baseline + subprocess no-leak test |
| `thai-math-docx/SKILL.md` (carve-out + version bump) | DEC-005 | §Trigger | trigger disambiguation review |
| render/QA font behavior | DEC-006 | §Font strategy | preflight fail-loud + render Thai-face gate |
| cross-skill references | DEC-007 | §Dependency & routing | dependency preflight |
| follow-on cleanup (fonts, workspace tools, memory) | DEC-006, DEC-008 | §Cleanup | plan stages, post-approval only |

## Glossary
| Term | Means here | Not |
|---|---|---|
| Engine | the general (math-free) scripts inside `thai-math-docx/scripts/` that thai-docx reuses | not the whole thai-math-docx skill; not the math/OMML modules |
| Seam | the minimal boundary drawn inside thai-math-docx so the general core has zero math dependency | not a full refactor of thai-math-docx |
| The core | the math-free general builder/audit/render/QA surface thai-docx imports | not `thai_math_expr` / `audit_docx_omml` / the OMML builder block |
| Normalize (font) | remap a doc's Thai runs to TH Sarabun New via `fix-thai-font` | not installing a system font; not `thai-font-normalize` as an acceptance gate |
| No-leak | thai-docx's general path loads/executes no math module (`sys.modules` clean) | not "math files deleted"; the files still exist, just unused on this path |

## 2. Trigger & disambiguation (DEC-005)
Lever = **presence of mathematical notation/equations**.
- `thai-docx` description: Thai Word `.docx` that is prose / tables / forms / letters / reports / handouts /
  admin & school documents / imported-doc repair, **without math notation**; "if the document needs editable
  equations/OMML/math, use `thai-math-docx` instead". Mentions TH Sarabun New (shared font engine).
- `thai-math-docx` description (F4): not only append a carve-out line — also **qualify the overlapping nouns**
  so "handouts / imported DOCX repair / reconstruction" read as *with math*, plus the pointer "if the Thai `.docx`
  has **no** math, use `thai-docx`". Bump its `SKILL-VERSION`. Still description-only, one bump, no code/routing
  change. Without qualifying the nouns, a plain handout still pattern-matches both skills (F4).

## 3. Font strategy (DEC-006)
- Standard = **TH Sarabun New** everywhere (matches `fix-thai-font` TARGET_FONT + thai-math-docx).
- **No TH SarabunPSK font is installed or shipped.** PSK is outdated; the user is migrating to New; PSK and
  New contend for display on the real machine (one copy only). `make_sarabun_psk.py` is dropped.
- Legacy-font docs (PSK/Angsana/…) are handled by normalizing the **document** to New via `fix-thai-font`
  (verified: it lists "th sarabunpsk"/"th sarabun psk" → New across ascii/hAnsi/cs/eastAsia) before render.
- Prerequisite = **LibreOffice + TH Sarabun New**. Preflight fails loudly with remediation if either is missing.
- Render Thai-face gate: with New-normalization the embedded face is THSarabunNew (gate passes — verified A7). A
  non-normalized legacy doc would substitute Tahoma and the engine gate returns 2. **`render_docx.py` stays
  READ-ONLY / untouched** (F3). Any "normalize → New first" remediation lives in thai-docx's OWN preflight/wrapper
  (S05/S07), never in the engine — thai-docx's repair path always normalizes before render, so the gate passes.

## 4. Dependency & routing (DEC-007)
- **HARD deps**: (1) `thai-math-docx` engine — builder CORE (sys.path import), `thai_math_docx_layout`,
  `audit_docx_font_defaults`, `audit_docx_insertion_safety`, `render_docx`, `contact_sheet`,
  `thai_math_docx_qa` (with `math.required=false`). NEVER the math modules.
  (2) `thai-font-normalize` — `fix-thai-font` (shell-out) for legacy→New.
- **SOFT/REFERENCE**: `soffice-runtime-fix` (troubleshoot render env; not a runtime dep).
- **OUT**: `pdf` skill (reconstruction excluded).
- Mechanism: all sibling refs by absolute `~/.codex/skills/<sibling>/…` path; Python imports via `sys.path`
  bootstrap; **no hardcoded codex-runtime python** (resolve interpreter portably).
- Missing-dep **preflight** (enforce-not-instruct): verify required sibling scripts + render env exist; fail
  loudly with remediation. SKILL.md carries an explicit **"Orchestration / borrowed skills"** section naming
  each sibling, what is borrowed, and the hand-off order.

## 5. Cleanup (DEC-008) — post-approval plan stages only
1. Remove the PSK clone faces installed 2026-09-02: `~/Library/Fonts/THSarabunPSK*.ttf` and the copies placed
   in LibreOffice's font dir; decide whether the THSarabunNew copies added to LO's dir stay or are removed
   (native LO already reads `~/Library/Fonts`).
2. Delete workspace `~/Documents/Claude Code workspace/tools/render_thai_docx.py` and `make_sarabun_psk.py`
   (superseded by the engine).
3. Update memory `[[thai-docx-render-pipeline]]` to the New-normalize strategy; retire the PSK-clone note.

## Edge cases & validation
- Imported doc still declares a legacy font at render time → preflight detects, instructs normalize-first (or the
  workflow normalizes a temp copy); never silently substitute Tahoma.
- A part carries `type:"math"` in thai-docx → out of scope; the general path should reject/flag it, not silently
  route into OMML (keeps the no-leak guarantee meaningful).
- Sibling skill missing/moved → preflight fails with the exact expected path.
- `math.required` defaults to false for thai-docx; QA must still enforce all non-math invariants (fonts, insertion
  safety, structural gates).

## Platform / environment notes
macOS (Darwin), Apple Silicon. LibreOffice 25.8.7 at `/Applications/LibreOffice.app`. PyMuPDF + fontTools present.
`~/.claude/skills/thai-math-docx` is a symlink to the codex copy, so "release to both locations" for this family
collapses to one repo + push (via the `skill-release` workflow). Repo: `zenithjuno/codex-skills` (private).

## Decision Log

| ID | Scope | Decision and rationale | Status |
|---|---|---|---|
| DEC-000 | cross-cutting | PROBLEM: build `thai-docx` reusing the mature pipeline minus math, without drifting duplicate code. Confirmed by user. | ACTIVE |
| DEC-001 | setup | Slug `thai-docx-skill`; project root `~/.codex/skills`; control home `docs/plans/active/thai-docx-skill/`; VCS = feature branch off the repo, commit only on explicit ask. | ACTIVE |
| DEC-002 | sharing model | **Path 1**: reuse model C + a bounded, test-guarded general/math seam refactor inside thai-math-docx; thai-docx invokes ONLY the math-free core by absolute path; no code duplication. Chosen over trim-fork (A: duplication+drift) and shared-core-build (B: too risky to the mature skill). Reuse without disturbing the crown jewel, no drift, repo-native. | ACTIVE |
| DEC-003 | verification (T1) | Mandatory gates: (a) REGRESSION — thai-math-docx tests/QA pass identically before/after the seam **except CHG-001**: `test_verify_qa.py`'s gate-coverage test is deliberately updated to assert the math-in-plain-text check is present for math docs and legitimately ABSENT for declared math-free docs; (b) NO-LEAK — thai-docx general path loads/executes no math **authoring/scanner** module — `audit_docx_math_in_text`, `thai_math_expr`, `thai_math_source_adapter` absent from `sys.modules` (**Ω2: `audit_docx_omml` is NOT in this set** — the hardened engine runs it as a passive `allow_no_math` validator on every doc; it never false-fails on prose), **proven in an isolated subprocess** (R2-F6: an in-process check false-fails under `unittest discover`) — achieved by GATING the scan call at `qa.py:503` **and relocating the `import audit_docx_math_in_text` (qa.py:19) into the gated math branch** (R3-F8), not only a lazy import; (c) SEAM PROOF — the gated call + lazy imports verified; general core usable with math modules absent. Amended after scrutiny F1/F2 (user approved R2 2026-09-03). | ACTIVE |
| CHG-001 | `thai-math-docx/tests/test_verify_qa.py::test_gate_reports_every_document_check`, `qa.py:503` | Gate `math_in_text.scan` on math context (math.required or oMath_count>0) instead of unconditional; update the gate-coverage test (currently asserts `math-in-plain-text` present for a `math.required=False` doc) so that id is asserted present for math docs and legitimately absent for declared math-free. Rationale: the unconditional scan false-positives on ordinary Thai prose (`คะแนน = 80`, `อายุ ≥ 15 ปี`) — F2 — so a no-math skill needs it gated, which also delivers no-leak (F1). Behavior for math docs unchanged. | ACTIVE (planned; opens at S02) |
| DEC-004 | scope | v1 IN: create/edit Thai prose + tables + headings + header/footer + font-normalize + font-default & insertion-safety audits + render/QA (math.required=false) + imported-DOCX repair + basic single-image insert. OUT: full SVG-diagram apparatus, PDF/image→DOCX reconstruction. Matches intent; avoids scope creep. | ACTIVE |
| DEC-005 | trigger | Disambiguate by math presence. thai-docx = Thai no-math docs, cross-refs thai-math-docx for math. Edit thai-math-docx description: **qualify overlapping nouns (handouts/imported-repair/reconstruction) as "with math"** + add no-math pointer to thai-docx + bump SKILL-VERSION. Amended after scrutiny F4 (user approved 2026-09-03): a bare pointer line left the nouns advertised on both skills. | ACTIVE |
| DEC-006 | font strategy | Standard = TH Sarabun New; do NOT install/keep TH SarabunPSK (outdated, contends with New, one copy only); handle legacy fonts by normalizing the doc → New via fix-thai-font (verified it lists PSK); prereq = LibreOffice + TH Sarabun New; preflight fail-loud. Overrode the earlier PSK-install idea. `make_sarabun_psk.py` dropped. | ACTIVE |
| DEC-007 | dependency/routing | thai-docx is non-standalone. HARD deps: engine (math-free core) + thai-font-normalize; REF: soffice-runtime-fix; OUT: pdf. Reference by absolute path; import via sys.path bootstrap; no hardcoded codex-runtime python; dependency preflight; SKILL.md Orchestration section. Confirmed by user (map correct, cut pdf). | ACTIVE |
| DEC-008 | cleanup | Post-approval stages: remove PSK clone faces (one-copy), delete workspace tools/ scripts, update memory to New-normalize. Runs after plan approval, never during grill. | ACTIVE |
| DEC-009 | no-leak scope (Ω2) | After merging thai-math-docx hardening (`3f978a4`), `_audit_omml` runs unconditionally with `allow_no_math=True` — a passive validator that PASSes trivially on math-free docs and never false-fails. So `audit_docx_omml` is EXCLUDED from the no-leak set; the seam gates ONLY the check that is *wrong* on prose (`math_in_text.scan`). No-leak = {`audit_docx_math_in_text`, `thai_math_expr`, `thai_math_source_adapter`}. Dissolves R4-F9 (no omml lazy-import). User approved Ω2 2026-09-04. Supersedes the earlier "no math/equation module at all" wording in DEC-003(b). | ACTIVE |

## Assumptions

| ID | Assumption | Status / how verified |
|---|---|---|
| A1 | `~/.claude/skills/thai-math-docx` symlinks to the codex copy → one repo + push. | VERIFIED 2026-09-02 (symlink shown). |
| A2 | Repo shares code cross-skill by absolute path (font-normalize precedent) + sys.path bootstrap (generator-template). | VERIFIED 2026-09-02. |
| A3 | qa.py is math-optional via `math.required` but runs the plain-text-math scan unconditionally + hard-imports the scanner → needs the scan CALL gated (qa.py:503) + its import (qa.py:19) relocated. (omml is NOT touched — Ω2.) | VERIFIED on merged engine `3f978a4` (qa.py L19, L120–122, L214/L481 unconditional `_audit_omml`, L503 scan). Seam handles it (see §1 The seam). |
| A4 | LibreOffice + TH Sarabun New render Thai correctly (via engine render_docx). | VERIFIED 2026-09-02 (TARGET, 41pp). |
| A5 | Builder mixes general + a contiguous math block; only tangle points are that block + `normalize_math_string` + qa imports. | VERIFIED 2026-09-02; RE-ANCHORED to merged engine `3f978a4`: builder `normalize_math_string` import still `qa`-free at L26, used L368; math block ~L181–470s; general funcs L60–180 & L470s–640s. qa.py: import L19/L21, `_audit_omml` L214 (call L481, unconditional), `math_in_text.scan` L503, check id L508. |
| A6 | fix-thai-font remaps PSK → New (ascii/hAnsi/cs/eastAsia). | VERIFIED 2026-09-02 (fix-thai-font v3.3 L149–168). |
| A7 | With New-normalization the render Thai-face gate passes; `render_docx.py` needs no change. | VERIFIED by scrutiny (render_docx.py:140 matches "Sarabun"; New embed passes). render_docx.py kept READ-ONLY (F3). Confirmed at S07/S08. |
| A8 | The existing thai-math-docx tests are a sufficient regression net. | VERIFIED by scrutiny with two gaps: (1) no prose-with-numeric-relations math-free PASS fixture — added at S06/S10 (F2); (2) no sys.modules no-leak assertion — added at S02/S03. The net is precisely what surfaces F1 as a red test. |
| A9 | This partially un-parks [[thai-math-docx-refactor-interest]]; only the general/math seam slice is taken, broader refactor stays parked. | Scope boundary, enforced by DEC-004/DEC-002. Reinforced by SQ1 (OMML split dropped: zero no-leak benefit). |
| A10 | Runner for the regression net. | VERIFIED: `unittest.main`, no pytest config → `python -m unittest discover -s tests` (R3: `tests/` has no `__init__.py`). Count updated to **16 test files** after merging hardening `3f978a4` (added `test_omml_structural_regressions.py`; `test_verify_qa.py`/`test_math_insertion_safety.py` expanded). S01 baseline retaken vs the 16-file suite. |

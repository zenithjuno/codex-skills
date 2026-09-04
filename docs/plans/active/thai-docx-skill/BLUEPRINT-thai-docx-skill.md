# BLUEPRINT — thai-docx skill

Version: 1.3 (patched after scrutiny rounds 1–3, 2026-09-03; see `PLAN-SCRUTINY-thai-docx-skill.md`) · Owner: zenithjuno · Status: **Approved design, NOT yet built** — scrutiny verdict: build-ready
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
| Acceptance criteria | 1) thai-docx generates+repairs+renders a Thai prose/table doc **including prose with numeric relations (e.g. `คะแนน ≥ 80`)**, Thai correct (New), QA gate PASS with `math.required=false`. 2) thai-math-docx baseline tests/QA pass identically before/after the seam **except the one gate-coverage test deliberately updated by CHG-001** (math-in-plain-text present for math docs, legitimately absent for declared math-free). 3) A test proves no math/equation module loads on the general path (`audit_docx_omml`, `audit_docx_math_in_text`, `thai_math_expr`, `thai_math_source_adapter` absent from `sys.modules`) — asserted **in an isolated subprocess / clean interpreter** (not the `unittest discover` process, where sibling tests pre-import those modules — R2-F6). 4) Preflight fails loudly when a dep (engine/font-normalize/LibreOffice/TH Sarabun New) is missing. 5) Triggers are disjoint from thai-math-docx. |
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
- `thai_math_docx_qa.py`: **gate the call site at `qa.py:517` `math_in_text.scan(...)`** on math context
  (`math.required` true or `m:oMath` present) — NOT run unconditionally. **Also relocate the top-level
  `import audit_docx_math_in_text` (qa.py:19) into that gated math branch** (R3-F8: gating only the *call* leaves
  L19 loading the module at import, so the no-leak assertion still fails), and make `audit_docx_omml` import lazy.
  This is what makes math-free QA load no math module, AND fixes the prose false-positive (see §3 / F2).
  It changes one existing gate-coverage test's expectation → **CHG-001** (see Decision Log DEC-003).
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
| `thai-math-docx/scripts/thai_math_docx_qa.py` (gate scan call + lazy math import) | DEC-002, DEC-003, CHG-001 | §1 The seam | regression baseline + gated-call/no-leak test + updated gate-coverage test |
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
| DEC-003 | verification (T1) | Mandatory gates: (a) REGRESSION — thai-math-docx tests/QA pass identically before/after the seam **except CHG-001**: `test_verify_qa.py`'s gate-coverage test is deliberately updated to assert the math-in-plain-text check is present for math docs and legitimately ABSENT for declared math-free docs; (b) NO-LEAK — thai-docx general path loads/executes no math/equation module (`audit_docx_omml`, `audit_docx_math_in_text`, `thai_math_expr`, `thai_math_source_adapter` absent from `sys.modules`), **proven in an isolated subprocess** (R2-F6: an in-process check false-fails under `unittest discover`) — achieved by GATING the call at `qa.py:517` **and relocating both the `audit_docx_math_in_text` (qa.py:19) and `audit_docx_omml` imports into the gated math branch** (R3-F8: gating the call alone leaves the L19 import loading the module), not only lazy imports; (c) SEAM PROOF — the gated call + lazy imports verified; general core usable with math modules absent. Amended after scrutiny F1/F2 (user approved R2 2026-09-03). | ACTIVE |
| CHG-001 | `thai-math-docx/tests/test_verify_qa.py`, `qa.py:517` | Gate `math_in_text.scan` on math context (math.required or m:oMath) instead of unconditional; update the gate-coverage test expectation accordingly. Rationale: the unconditional scan false-positives on ordinary Thai prose (`คะแนน = 80`, `อายุ ≥ 15 ปี`) — F2 — so a no-math skill needs it gated, which also delivers no-leak (F1). Behavior for math docs unchanged. | ACTIVE (planned; opens at S02) |
| DEC-004 | scope | v1 IN: create/edit Thai prose + tables + headings + header/footer + font-normalize + font-default & insertion-safety audits + render/QA (math.required=false) + imported-DOCX repair + basic single-image insert. OUT: full SVG-diagram apparatus, PDF/image→DOCX reconstruction. Matches intent; avoids scope creep. | ACTIVE |
| DEC-005 | trigger | Disambiguate by math presence. thai-docx = Thai no-math docs, cross-refs thai-math-docx for math. Edit thai-math-docx description: **qualify overlapping nouns (handouts/imported-repair/reconstruction) as "with math"** + add no-math pointer to thai-docx + bump SKILL-VERSION. Amended after scrutiny F4 (user approved 2026-09-03): a bare pointer line left the nouns advertised on both skills. | ACTIVE |
| DEC-006 | font strategy | Standard = TH Sarabun New; do NOT install/keep TH SarabunPSK (outdated, contends with New, one copy only); handle legacy fonts by normalizing the doc → New via fix-thai-font (verified it lists PSK); prereq = LibreOffice + TH Sarabun New; preflight fail-loud. Overrode the earlier PSK-install idea. `make_sarabun_psk.py` dropped. | ACTIVE |
| DEC-007 | dependency/routing | thai-docx is non-standalone. HARD deps: engine (math-free core) + thai-font-normalize; REF: soffice-runtime-fix; OUT: pdf. Reference by absolute path; import via sys.path bootstrap; no hardcoded codex-runtime python; dependency preflight; SKILL.md Orchestration section. Confirmed by user (map correct, cut pdf). | ACTIVE |
| DEC-008 | cleanup | Post-approval stages: remove PSK clone faces (one-copy), delete workspace tools/ scripts, update memory to New-normalize. Runs after plan approval, never during grill. | ACTIVE |

## Assumptions

| ID | Assumption | Status / how verified |
|---|---|---|
| A1 | `~/.claude/skills/thai-math-docx` symlinks to the codex copy → one repo + push. | VERIFIED 2026-09-02 (symlink shown). |
| A2 | Repo shares code cross-skill by absolute path (font-normalize precedent) + sys.path bootstrap (generator-template). | VERIFIED 2026-09-02. |
| A3 | qa.py is math-optional via `math.required` but runs the plain-text-math scan unconditionally + hard-imports math modules → needs the scan CALL gated (qa.py:517) + the omml import lazy. | VERIFIED (qa.py L19–21, 121–129, 236, 517). Seam handles it (see §1 The seam L58–60). |
| A4 | LibreOffice + TH Sarabun New render Thai correctly (via engine render_docx). | VERIFIED 2026-09-02 (TARGET, 41pp). |
| A5 | Builder mixes general + a contiguous math block (L181–475); only tangle points are that block + `normalize_math_string` + qa imports. | VERIFIED 2026-09-02 (function inventory). |
| A6 | fix-thai-font remaps PSK → New (ascii/hAnsi/cs/eastAsia). | VERIFIED 2026-09-02 (fix-thai-font v3.3 L149–168). |
| A7 | With New-normalization the render Thai-face gate passes; `render_docx.py` needs no change. | VERIFIED by scrutiny (render_docx.py:140 matches "Sarabun"; New embed passes). render_docx.py kept READ-ONLY (F3). Confirmed at S07/S08. |
| A8 | The existing thai-math-docx tests are a sufficient regression net. | VERIFIED by scrutiny with two gaps: (1) no prose-with-numeric-relations math-free PASS fixture — added at S06/S10 (F2); (2) no sys.modules no-leak assertion — added at S02/S03. The net is precisely what surfaces F1 as a red test. |
| A9 | This partially un-parks [[thai-math-docx-refactor-interest]]; only the general/math seam slice is taken, broader refactor stays parked. | Scope boundary, enforced by DEC-004/DEC-002. Reinforced by SQ1 (OMML split dropped: zero no-leak benefit). |
| A10 | Runner for the regression net. | VERIFIED by scrutiny: all 15 test files use `unittest.main`; no pytest config → `python -m unittest discover` from skill root (S01). |

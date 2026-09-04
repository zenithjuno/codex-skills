# CONSTRUCTION PLAN — thai-docx skill

Companion to `BLUEPRINT-thai-docx-skill.md`. Method: create → test → pass.
Control: `BUILD-CONTROL-thai-docx-skill.md`. Task contract: `BLUEPRINT-thai-docx-skill.md §Task contract`.
Target: skill folder in `~/.codex/skills` + a bounded seam in `thai-math-docx`. Platform: macOS arm64, LibreOffice 25.8.7.

## How to read this (for a non-dev)
Each stage is **build a small piece → test it → you look → you say pass/fail**. Your job at 👁️ YOU SEE is to
judge "ถูก/ผิด เพราะ…" against what you know is true (e.g. "ไทยขึ้นถูก ตารางไม่เพี้ยน"). Replies are **commands**,
not chit-chat: `Pass S02` closes S02 and I immediately start the next; `Fail S02 — เหตุผล` keeps it open to fix.
I always give you the exact line to copy.

## Build startup (after approval, before S01 edits)
1. `git` on `~/.codex/skills`; confirm clean `main`, record baseline hash in BUILD-CONTROL §VERSION CONTROL.
2. Create branch `build/thai-docx-skill`.
3. Create `history/BUILD-LOG-thai-docx-skill-P01.md`; set STATE current stage = S01.
4. If the worktree has unrelated dirty changes, stop and ask (never absorb).

## Golden rules of this build
1. **thai-math-docx is sacred** — its existing `tests/` must stay green at every seam stage (regression net).
2. **No math authoring/scanner on the general path** — prove it mechanically (no `audit_docx_math_in_text` / `thai_math_expr` / `thai_math_source_adapter` in `sys.modules`; `audit_docx_omml` validator is allowed — Ω2), not by eyeballing.
3. **No duplicated engine code** — thai-docx imports/invokes the engine by absolute path; it copies nothing.
4. **Engine (seam) before interface (skill)** — prove the seam is safe before building thai-docx on it.
5. **Smallest touch to the crown jewel** — prefer lazy-import over relocating code; relocate only if trivially safe.
6. **Font = TH Sarabun New only** — never install a legacy font; normalize the document instead.

## Destination
A working `thai-docx` skill for Thai no-math Word docs that rides thai-math-docx's math-free engine, with
thai-math-docx proven unchanged and the general path proven math-free.

## Stable decisions
See `BLUEPRINT-thai-docx-skill.md §Decision Log` (DEC-000…DEC-008). Do not restate or re-litigate here.

## Active frontier

Full six-part detail exists for `ACTIVE`/foundation stages; later `PLANNED` stages carry coarse intent
(one line each) and graduate to full detail when they become active.

| Stage | Name | Lifecycle | Outcome |
|---|---|---|---|
| `S01` | regression baseline | `PASS` | |
| `S02` | qa.py gate math scan (CHG-001) | `PASS` | |
| `S03` | builder lazy math-grammar import | `PASS` | |
| `S04` | thai-docx skeleton + SKILL.md | `ACTIVE` | ครูเห็น description/ทริกของสกิลใหม่ ชัดว่าใช้ตอนไหน ไม่ชนกับ math |
| `S05` | dependency + render-env preflight | `PLANNED` | ครูเห็นว่าถ้าขาด LibreOffice/ฟอนต์/สกิลพี่น้อง มันฟ้องบอกวิธีแก้ ไม่เงียบ |
| `S06` | prose+table generate (core, math-free) | `PLANNED` | ครูเห็นเอกสารไทย prose+ตารางที่สร้างจาก engine ไทยถูก |
| `S07` | repair imported (legacy→New) | `PLANNED` | ครูเห็นไฟล์ import (ฟอนต์ PSK) ถูก normalize เป็น New แล้ว render ถูก |
| `S08` | render + QA gate integration | `PLANNED` | ครูเห็น contact sheet ของเอกสารที่ render + QA ผ่าน (math.required=false) |
| `S09` | trigger carve-out + docs | `PLANNED` | ครูเห็น description thai-math-docx เพิ่มบรรทัดชี้มา thai-docx + version bump |
| `S10` | end-to-end + acceptance sweep | `PLANNED` | ครูเห็นงานจริงทั้งเส้น + สรุปว่าเข้าเกณฑ์ acceptance ครบ |
| `S11` | cleanup (fonts/tools/memory) | `PLANNED` | ครูเห็นว่า PSK clone หายจากเครื่อง (เหลือ New copy เดียว), tools ซ้ำถูกลบ, memory อัปเดต |

### S01 — regression baseline
📁 SCOPE — read `thai-math-docx/tests/**`, `thai-math-docx/scripts/**`; create none; modify none. Protected: everything else.
🔗 CONTRACT — DEC-003(a). Current source: BLUEPRINT §1 (iron rule 3). Current truth surfaces: BUILD-CONTROL STATE.
🔨 BUILD — determine the exact test runner and record the **green baseline** of thai-math-docx's existing suite on
  `main` — the safety net every seam stage must keep green. No product change. NOTE (R3 heads-up): `tests/` has no
  `__init__.py`, so a bare `python -m unittest discover` from the skill root collects nothing — use
  `python -m unittest discover -s tests` (or run from inside `tests/`); do **not** misread an empty discovery as
  "0 tests, green." Record the exact working command.
🧪 TEST — run the full thai-math-docx suite; capture pass count + command. Expected: a non-zero pass count, all pass (record any pre-existing skips/failures verbatim as the baseline). A "0 collected" result is a runner error, not a pass.
👁️ YOU SEE — a one-line result: "รันชุดเทสต์ thai-math-docx: ผ่าน N/N (คำสั่ง: …)" — the net is in place.
✅ PASS GATE — baseline captured and green (or its exact pre-existing state recorded). Reply `Pass S01` / `Fail S01 — เหตุผล`. A pass logs S01 and starts S02.

### S02 — qa.py gate the math scan on math context (opens CHG-001)
📁 SCOPE — modify `thai-math-docx/scripts/thai_math_docx_qa.py`; modify `thai-math-docx/tests/test_verify_qa.py` (the gate-coverage expectation — CHG-001); create `thai-math-docx/tests/test_qa_mathfree_no_leak.py`. Protected: math modules (edit none).
🔗 CONTRACT — DEC-002, DEC-003(a,b,c), **CHG-001**. Current source: BLUEPRINT §1 The seam, §3. Current truth surfaces: BLUEPRINT (DEC-003/CHG-001), BUILD-CONTROL STATE + OPEN CHANGES.
🔨 BUILD — **gate the call site**: `qa.py:503` `math_in_text.scan(...)` runs only when math context is present
  (`math.required` true or `metrics["omml"]["oMath_count"]` > 0 — both available at that point), not unconditionally.
  **Also relocate the top-level `import audit_docx_math_in_text` from `qa.py:19` into that gated math branch**
  (co-located with the conditional scan) — R3-F8: gating only the call leaves L19 importing the module. The leak is
  a *call* **and** an *import*. **`audit_docx_omml` is LEFT AS-IS (Ω2/DEC-009)** — `_audit_omml` (L214) runs
  unconditionally with `allow_no_math=True` and PASSes trivially on prose, so it is neither gated nor removed;
  R4-F9 is dissolved. Behavior for math docs is unchanged. (Line numbers as of merged engine `3f978a4`.)
  Then open CHG-001: update `test_verify_qa.py`'s gate-coverage test so the `math-in-plain-text` check id is
  asserted present for a math doc and legitimately absent for a declared `math.required=false` doc.
🧪 TEST — (focused 1) new no-leak test: run QA on a math-free `math.required=false` fixture **that contains a numeric
  relation in prose (e.g. `นักเรียนที่ได้คะแนน ≥ 80`)** and assert (a) verdict is not FAIL on that account and
  (b) `audit_docx_math_in_text` absent from `sys.modules` **checked in an isolated subprocess**
  (`subprocess.run([sys.executable, "-c", ...])` that runs `qa.audit_docx` on the fixture) — NOT an in-process
  assertion, which false-fails under `unittest discover` because sibling tests pre-import it (R2-F6).
  **Do NOT assert `audit_docx_omml` absent** — per Ω2 it legitimately loads/runs as the `allow_no_math` validator.
  (focused 2) the updated gate-coverage test
  passes both ways. (regression) full suite green vs S01 baseline except that one intentionally-updated test.
👁️ YOU SEE — a small before/after: a prose doc with `คะแนน ≥ 80` → **before**: QA FAIL "fused into one run"; **after**:
  QA PASS, no math scanner module (`audit_docx_math_in_text`) loaded. Plus "ชุดเทสต์เดิมผ่าน N/N (แก้ 1 ตัวตามตั้งใจ = CHG-001)".
✅ PASS GATE — gated call proven (prose-with-operator PASSes + no `audit_docx_math_in_text` loaded) AND regression identical to S01 except CHG-001's test. `Pass S02` / `Fail S02 — เหตุผล`.

### S03 — builder: make the single math-grammar import lazy (⚠️ highest-risk, slow down)
📁 SCOPE — modify `thai-math-docx/scripts/thai_math_docx_builder.py` (one import); create `thai-math-docx/tests/test_builder_mathfree_no_leak.py`. **No new module, no OMML relocation** (SQ1 dropped: zero no-leak benefit, = the parked refactor). Protected: math audit modules + the OMML block (stays in place).
🔗 CONTRACT — DEC-002, DEC-003(b). Current source: BLUEPRINT §1 The seam. Current truth surfaces: BUILD-CONTROL STATE.
🔨 BUILD — make only `from thai_math_source_adapter import normalize_math_string` (L26) **lazy** — import inside the
  `type:"math"` call path (used at L368). The OMML block stays put and runs only via `append_parts` on math parts.
  General builder API (`set_thai_body_run`, `add_paragraph`, `add_table`, `add_heading`, `save_docx`, font helpers)
  unchanged. (Line numbers as of merged engine `3f978a4`.)
🧪 TEST — (focused) new no-leak test **in an isolated subprocess** (`subprocess.run([sys.executable, "-c", ...])`):
  import ONLY the general builder API + build a prose+table doc, then assert `thai_math_source_adapter` and
  `thai_math_expr` are absent from that clean interpreter's `sys.modules` — an in-process check false-fails under
  `unittest discover` (R2-F6). (**Not `audit_docx_omml` — Ω2.**) (regression) full suite green vs baseline.
👁️ YOU SEE — "สร้างเอกสาร prose+ตารางผ่าน builder = ไม่โหลด grammar/โมดูล math (ผ่าน) ; ชุดเทสต์เดิมผ่าน N/N".
✅ PASS GATE — no-leak test passes AND regression identical to baseline. `Pass S03` / `Fail S03 — เหตุผล`.

### S04–S11 (coarse intent; graduate to full detail when active)
- **S04** thai-docx skeleton + SKILL.md (prose-first description with math cross-ref + Orchestration/borrowed-skills section + SKILL-VERSION). Test: frontmatter valid + trigger review. You judge the two descriptions read as disjoint.
- **S05** dependency + render-env preflight script (engine scripts, fix-thai-font, LibreOffice, TH Sarabun New; interpreter resolved portably via `sys.executable`/`/usr/bin/env python3`, **never** the codex-runtime path — F5; fail-loud). This script also owns the "normalize→New first" remediation text (F3), NOT the engine. Test: all-present passes; each simulated-missing fails with remediation text.
- **S06** prose+table generate through the engine core via sys.path bootstrap, math.required=false. Fixture **includes a numeric relation in prose** (`≥`) to prove F2 is fixed. Test: docx built + audits pass + QA PASS + no-leak on this path. You see the rendered Thai.
- **S07** repair-imported path: normalize legacy(PSK)→New via fix-thai-font + audits on an imported fixture, THEN render. `render_docx.py` stays untouched (F3); the gate passes because normalize runs first. Test: embedded face = New; render correct. You compare before/after.
- **S08** render + contact_sheet + QA gate integration (math.required=false), end-to-end. You see a contact sheet.
- **S09** thai-math-docx description edit — **qualify overlapping nouns as "with math" + add no-math pointer** (F4), bump version; finalize thai-docx orchestration docs. Test: both suites green; you judge the two descriptions read as disjoint.
- **S10** end-to-end on a real user prose doc **containing numeric relations** + full no-leak + regression sweep = Task Contract acceptance sweep (final gate).
- **S11** cleanup (post-approval, off-repo): remove PSK clone faces (one-copy), delete workspace tools, update memory. You confirm before I remove fonts; you confirm PSK gone.

## Not yet specified
- (none — the path is visible for a build this size; discoveries during S03 that change the seam approach bounce back to the grill per the bounce-back rule.)

## Out of scope
- Full SVG-diagram apparatus (visuals.md). · PDF/image→DOCX reconstruction. · `pdf` skill integration. · The broader thai-math-docx size/grammar refactor (stays parked).

## What I need from you during the build
- S01–S03 (the seam) is where I go slow — you mainly confirm "เทสต์เดิมยังเขียว" and "ไม่รั่วไป math".
- S06–S08 you judge Thai rendering against reality (your own eyes on the rendered pages).
- S11 changes your machine's fonts — I'll confirm before removing the PSK clones.

## Risk notes
- Builder seam (S03): the OMML block is contiguous but `append_parts` bridges general→math; a wrong lazy-import
  could break math-doc generation. The regression suite + no-leak test bracket this.
- render_docx.py stays READ-ONLY (F3); the Thai-face gate passes because thai-docx normalizes→New before render. "Normalize first" remediation lives in thai-docx's own preflight (S05), never the engine.
- QA plain-text-math scan false-positives on prose operators (`=`/`≥`) — the whole point of gating it at S02 (F2). Fixtures at S06/S10 MUST contain such operators or they pass while dodging the real behavior.
- No-leak proof MUST run in an isolated subprocess (R2-F6): `sys.modules` is process-global and `unittest discover` pre-imports sibling math-test modules, so an in-process assertion false-fails even when the seam is correct. Do NOT weaken the assertion to "fix" a false-fail — spawn a clean interpreter instead.
- Portability: do not hardcode the codex-runtime python path anywhere in thai-docx (DEC-007).

## Deliverables
`thai-docx/` skill; the seam edits in `thai-math-docx`; `BLUEPRINT-`, `CONSTRUCTION_PLAN-`, `BUILD-CONTROL-thai-docx-skill.md`; cold `history/BUILD-LOG-*`; released via `skill-release` (on explicit ask).

## Completion protocol
Verify every Task Contract acceptance criterion; run thai-math-docx regression + thai-docx tests + a real-doc
render; inspect managed-path diff; update BLUEPRINT/BUILD-CONTROL; disclose any skipped check; set STATE COMPLETE;
remove the AGENTS.md block; move the bundle to `docs/plans/completed/thai-docx-skill/`. Release via `skill-release`.

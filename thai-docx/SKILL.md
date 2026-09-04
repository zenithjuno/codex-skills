---
name: thai-docx
description: >
  Use when creating, editing, repairing, or auditing a Thai Microsoft Word .docx
  that is PROSE and contains NO mathematical notation — reports, letters, memos,
  official/administrative documents, school forms, meeting minutes, handouts, and
  plain tables. Optimizes for the user's Word workflow: Thai body text in TH Sarabun
  New with Complex-Script font routing that survives Clear Formatting and PDF export,
  insertion-safe Thai runs, and robust docDefaults/Normal defaults. Also repairs an
  imported or legacy Thai .docx (e.g. TH SarabunPSK / Angsana → TH Sarabun New) and
  renders a page preview for review. NOTE: if the document needs editable equations,
  OMML, or any mathematical notation, use `thai-math-docx` instead — this skill is
  for Thai documents WITHOUT math.
---

<!-- SKILL-VERSION: 2026.09.04 | name: thai-docx | canonical: ~/.codex/skills/thai-docx | bump this date on every edit -->

# Thai DOCX (no math)

Use this skill to produce, edit, repair, or audit a Thai Word `.docx` whose content is
**prose and tables with no mathematical notation** — the everyday Thai documents a teacher
or administrator writes: reports, official letters, memos, forms, minutes, plain handouts.

**Trigger boundary (read first).** The single lever that separates this skill from its
sibling is *the presence of mathematical notation*:

- **No math → this skill.** Thai prose, tables, headings, headers/footers; repairing an
  imported Thai document; previewing a Thai document.
- **Any editable equation / OMML / math notation → `thai-math-docx`.** Exams, answer keys,
  worksheets with equations, anything where math must stay editable in Word. Do not use
  `thai-docx` for those; hand off to `thai-math-docx`.

A relational glyph inside ordinary prose (`คะแนน ≥ 80`, `ราคา < 100 บาท`) is **not** math
notation for this purpose — it is normal administrative writing and stays plain text.

## This skill is an orchestrator, not a standalone

`thai-docx` deliberately owns almost no engine code. It **reuses the mature, battle-tested
`thai-math-docx` engine's general (math-free) surface** and the `thai-font-normalize`
repairer, both by absolute path. It is therefore **not standalone** — the sibling skills
below must be installed. Run the preflight (next section) before real work; it fails loudly
with the exact missing path rather than producing a broken document.

### Orchestration / borrowed skills

| Borrowed from | What this skill uses it for | How |
|---|---|---|
| `~/.codex/skills/thai-math-docx/scripts/` | Thai run/table/heading insertion (builder **core**), font-default & insertion-safety audits, page render + contact sheet, the unified QA gate | Python import via a `sys.path` bootstrap; CLIs by absolute path |
| `~/.codex/skills/thai-font-normalize/scripts/fix-thai-font` | normalize a document's Thai fonts (incl. legacy TH SarabunPSK / Angsana) → **TH Sarabun New** | shell out by absolute path |
| `~/.codex/skills/soffice-runtime-fix` | reference only — consult if the render environment (LibreOffice) is broken | not a runtime dependency |

**Never** import or invoke `thai-math-docx`'s math modules (`audit_docx_omml`,
`audit_docx_math_in_text`, `thai_math_expr`, `thai_math_source_adapter`, the OMML builder
functions). This skill's whole point is a Thai-document path that touches no math authoring
code. The engine's QA is run with `math.required = false`, under which the plain-text-math
scan is correctly skipped, so ordinary prose relations never false-fail.

## Font standard

**TH Sarabun New** is the one Thai font standard (matching `thai-font-normalize` and
`thai-math-docx`). This skill never installs a legacy font. When a document declares an
older Thai font (TH SarabunPSK, Angsana, …), it is **normalized in the document** to TH
Sarabun New via `fix-thai-font` — the font is fixed in the file, not added to the machine.

## Workflow (hand-off order)

```
generate / edit / repair the Thai docx  (prose, tables, headings, header/footer, basic image)
  → thai-math-docx ENGINE: builder CORE + font-default & insertion-safety audits
  → thai-font-normalize (fix-thai-font): any legacy/PSK Thai font → TH Sarabun New
  → thai-math-docx ENGINE: render_docx (+ contact_sheet) + unified QA gate (math.required = false)
```

For a **repair of an imported document**, start at the normalize step on the imported file,
then audit and render. For a **new document**, build with the engine core, then normalize,
then render/QA.

## Visual truth

**Microsoft Word on the user's machine is the visual authority.** The LibreOffice/PyMuPDF
render (page image or contact sheet) is only an internal **sanity check** to catch gross
breakage — it substitutes fonts and approximates layout, so it is NOT what the user signs
off on. When a document needs the user's visual judgment, **deliver the actual `.docx`** for
them to open in Word; never present a render as the final truth.

## Dependency + render-env preflight

Run `scripts/preflight.py` before real work (added in build stage S05). It verifies the
sibling engine + `fix-thai-font` exist, and that the render environment is present
(LibreOffice + TH Sarabun New), failing with a precise remediation message if anything is
missing. It resolves the Python interpreter portably (`sys.executable`) — never a hardcoded
runtime path.

## Reference — load on demand

| Read | When |
|---|---|
| `references/engine-reuse.md` | you need the exact `sys.path` bootstrap and the engine functions/CLIs this skill is allowed to call |
| `references/repair.md` | repairing an imported / legacy-font Thai document |

Open an engine script's source only when its behavior is unclear; do not copy engine code
into this skill.

---
name: thai-font-normalize
description: >
  Normalize Thai fonts in generated Word .docx files to TH Sarabun New so that Thai
  text renders correctly in Word, in PDF export, and after Clear Formatting or applying
  paragraph styles. Use this skill WHENEVER generating, editing, or producing a .docx
  that contains Thai text — even if the user does not explicitly mention fonts. This
  prevents the common failure where Thai falls back to Angsana New. The skill both
  (a) writes correct OOXML during generation and (b) runs a bundled verification script
  on the finished file as a mandatory final pass. Default Thai font: TH Sarabun New,
  Complex Script size 16pt.
---
<!-- SKILL-VERSION: 2026.08.09 | name: thai-font-normalize | canonical: ~/.codex/skills/thai-font-normalize | bump this date on every edit -->

# Thai Font Normalization

Single clear objective: **every .docx containing Thai text must render Thai in TH Sarabun New**
consistently — in Word display, in PDF export, after "Clear Formatting", and after applying
paragraph styles.

This is harder than setting a font, because Word routes Thai through a separate "Complex Script"
font system that most generators get wrong. The result is Thai silently falling back to
**Angsana New** (Microsoft's 20-year-old default Thai theme font) the moment a style is applied
or the file is exported to PDF.

This skill enforces correctness in **two layers**:

1. **Write correct OOXML during generation** — follow the rules in `references/thai-ooxml-rules.md`.
2. **Repair and verify with a deterministic script** — run `scripts/fix-thai-font` on the finished
   file as a mandatory final pass. The script catches anything the generation step missed and exits
   nonzero if required Thai Complex Script invariants are still broken.

Do BOTH. The script is the safety net; writing correctly the first time keeps the document clean
and minimizes the script's work.

---

## Defaults

- **Thai font:** TH Sarabun New
- **Complex Script size:** 16pt (`w:szCs` = `32`, since OOXML sizes are in half-points)
- **Latin font:** leave whatever the document/user specifies (commonly Cambria or Times New Roman).
  Never change Western Latin fonts.

---

## Workflow

### Step 1 — Generate the document following the rules

Before writing any document XML, read `references/thai-ooxml-rules.md`. The seven rules there are
mandatory. The most important, in priority order:

1. Every run containing Thai characters MUST include the empty `<w:cs/>` toggle in its `<w:rPr>`.
   This is the single most common cause of the Angsana New fallback.
2. When generating XML, never put a Thai-only font (Angsana New, Cordia New, *UPC fonts) in the
   Latin slots (`w:ascii` / `w:hAnsi`).
3. Set `w:cs="TH Sarabun New"` and `w:bidi="th-TH"` in the document defaults (`docDefaults`).
4. Set both `<a:font script="Thai" .../>` entries in the theme to TH Sarabun New.
5. Split runs at Thai/Latin boundaries when they need different fonts.
6. Never emit non-font values (CSS variables, placeholders) into font-name attributes.
7. Language tags must match the script of each run.

### Step 2 — Run the verification script (mandatory)

After the .docx is written to disk, run the bundled script on it. This runs entirely on the target
`.docx`; it does not need network access or external packages.

```bash
bash scripts/fix-thai-font -i /path/to/generated.docx
```

- `-i` overwrites the file in place. A `.bak` copy is written only when the file
  sits outside a git working tree; inside a repository the history is the
  backup, so no clutter is created. Override with `--backup` / `--no-backup`.
- Omit `-i` to instead produce `generated_fixed.docx` next to the original.
- Use `--check` to audit without writing a repaired file.

The script:
- Replaces known Thai fallback fonts (Angsana New, Cordia New, Browallia New, and the UPC family,
  plus TH SarabunPSK) in Complex Script slots (`w:cs`) with TH Sarabun New.
- Preserves Latin slots (`w:ascii` / `w:hAnsi`) exactly as found. The script does not guess a
  replacement Latin font.
- Fixes Thai entries in Word theme XML, regardless of attribute order.
- Ensures `styles.xml` document defaults have `w:cs="TH Sarabun New"`, `w:bidi="th-TH"`, and
  `w:szCs`.
- Inserts a true `<w:cs/>` toggle into every run that contains Thai characters and lacks it.
- Adds run-level `w:rFonts w:cs="TH Sarabun New"` and `w:lang w:bidi="th-TH"` to Thai text runs.
- Audits the result and fails loudly if any required invariant is still missing.
- Leaves all Western Latin font routing untouched.

To target a different Thai font (rare):

```bash
bash scripts/fix-thai-font -f "Sarabun" -i /path/to/generated.docx
```

To audit a file without changing it:

```bash
bash scripts/fix-thai-font --check /path/to/generated.docx
```

### Step 3 — Confirm and deliver

Present the finished file to the user. If the document was built with a document-creation tool
(e.g. the docx skill), the verification pass runs on its final output, after all other edits.

---

## Scope

This skill does ONE thing: normalize Thai fonts and Complex Script routing. It does not set
margins, heading styles, page layout, or other formatting preferences — those belong to whatever
template or instructions the user provides. Keeping the scope tight is deliberate: the objective
is "Thai renders in TH Sarabun New, always."

---

## Reference

- `references/thai-ooxml-rules.md` — the full seven-rule specification with XML examples and a
  pre-emit self-check. Read it before generating Thai document XML.
- `scripts/fix-thai-font` — the bundled verification/repair script (bash + embedded Python;
  needs only `unzip`, `zip`, `python3`, all standard).

# Repairing an imported / legacy-font Thai .docx

Imported Thai documents (from a school, a colleague, an old template) commonly declare
an outdated Thai font — **TH SarabunPSK**, Angsana, Cordia, UPC families — which the user
is migrating away from. Repair brings the document to the **TH Sarabun New** standard.

## Steps

1. **Repair the fonts** with `scripts/repair.py` (two passes). It mutates the
   supplied path and creates a backup; work on an output copy unless in-place
   repair is authorized:

   ```bash
   python3 ~/.codex/skills/thai-docx/scripts/repair.py "<file>.docx"
   ```

   - Pass 1 shells out to `thai-font-normalize/scripts/fix-thai-font` — routes Thai
     Complex Script (`w:cs`) + the theme mapping to TH Sarabun New (this fixes the Thai
     TEXT).
   - Pass 2 is a **residual legacy-Thai-font sweep**: fix-thai-font deliberately leaves
     Latin slots alone (thai-math-docx wants Latin=Cambria), so a legacy Thai font in an
     `ascii`/`hAnsi` slot — e.g. on a numbers-only run in a budget document — would survive
     and then substitute once the legacy font is uninstalled. This pass rewrites any
     **legacy Thai font** (PSK, Angsana, Cordia, UPC, …) in **any** slot across **every**
     document part to TH Sarabun New. Genuine Latin fonts (Calibri, Cambria, Arial, Times
     New Roman) are **preserved** — repair fixes Thai fonts, it does not restyle Latin.

   Legacy Thai font declarations become TH Sarabun New; genuine Latin fonts
   remain as authored. No legacy font installation is needed.
   `repair()` writes a `.orig.bak` beside the file.

2. **Audit** the result with the engine's math-free QA. Use the bootstrap in
   [engine-reuse.md](engine-reuse.md); declare teacher-master, layout and media
   when applicable:

   ```python
   import engine  # thai-docx/scripts/engine.py
   result = engine.audit_prose("<file>.docx", source_mode="imported")
   reports = engine.qa.write_reports(result, report_dir="qa-reports")
   print(result["verdict"], result["needs_word_review"], reports)
   if result["verdict"] != "PASS":
       raise SystemExit(1)
   ```

3. **Render a sanity preview** (LibreOffice + PyMuPDF) to catch gross breakage —
   but remember: **Microsoft Word is the visual authority** (SKILL.md § Visual truth).
   Deliver the repaired `.docx` for the user to judge in Word.

## Repair boundary

The shared normalizer handles Thai routing and theme/defaults. This skill's
second pass converts residual legacy Thai fonts in all slots. Genuine Latin
fonts remain unchanged; converting those too is a separate restyling request.
An existing explicit request for a uniform prose profile already authorizes that
restyling; do not ask for the same preference again.

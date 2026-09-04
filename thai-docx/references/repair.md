# Repairing an imported / legacy-font Thai .docx

Imported Thai documents (from a school, a colleague, an old template) commonly declare
an outdated Thai font — **TH SarabunPSK**, Angsana, Cordia, UPC families — which the user
is migrating away from. Repair brings the document to the **TH Sarabun New** standard.

## Steps

1. **Repair the fonts** with `scripts/repair.py` (two passes):

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

   The result renders entirely in TH Sarabun New with **no legacy font installed**.
   `repair()` writes a `.orig.bak` beside the file.

2. **Audit** the result with the engine's math-free QA:

   ```python
   import engine  # thai-docx/scripts/engine.py
   engine.audit_prose("<file>.docx")   # math.required=false
   ```

3. **Render a sanity preview** (LibreOffice + PyMuPDF) to catch gross breakage —
   but remember: **Microsoft Word is the visual authority** (SKILL.md § Visual truth).
   Deliver the repaired `.docx` for the user to judge in Word.

## What fix-thai-font does and does not touch

- **Does:** the `w:cs` (Thai Complex Script) slot on every run + the theme Thai mapping →
  TH Sarabun New. This is what makes Thai render correctly.
- **Does not:** the Latin `w:ascii` / `w:hAnsi` slots. It leaves them as authored, on
  purpose — thai-math-docx wants Latin to stay Cambria. So a legacy font left in a Latin
  slot survives repair. That is a **cosmetic** issue (it only affects Latin glyphs, never
  Thai). If a fully-uniform TH Sarabun New result is wanted (matching the prose profile),
  that Latin-slot conversion is a separate, opt-in step — confirm with the user first.

---
name: soffice-runtime-fix
description: Diagnose and repair the bundled macOS LibreOffice runtime when DOCX-to-PDF conversion, dylib loading, writable profiles, or Thai font rendering fails after a Codex runtime update. Classify DOCX-to-PDF separately from PDF-to-PNG failures; do not patch LibreOffice for a missing rasterizer alone.
---
<!-- SKILL-VERSION: 2026.08.26 | name: soffice-runtime-fix -->

# soffice-runtime-fix

Recover the render path the active consumer actually uses. Diagnose before
mutating the runtime, and verify document content rather than treating
`soffice --version` or the existence of a PNG as proof of success.

## Trigger and boundary

Use this skill when bundled LibreOffice fails with a dylib, profile, cache, or
Fontconfig error; when DOCX-to-PDF fails after a runtime update; or when a PDF
is produced but Thai text disappears.

First locate the failing stage:

- `DOCX -> PDF`: launcher/topology, dylib, profile/cache, or font integrity.
- `PDF -> PNG`: PyMuPDF, Poppler, output-path, or image-generation failure.
- DOCX package/content: invalid input rather than a runtime fault.

Missing PyMuPDF alone is a rasterizer failure. Prefer bundled `pdftoppm` when
available and do not patch LibreOffice unless DOCX-to-PDF or font integrity is
also broken.

## Workflow

1. Call `load_workspace_dependencies` and record the dependency root and bundle
   version. Identify the renderer used by the current task.
2. Diagnose without mutation:

   ```bash
   python scripts/repair_soffice_runtime.py \
     --diagnose \
     --dependency-root <dependencies> \
     --bundle-version <version> \
     --renderer <render_docx.py> \
     --json
   ```

   Candidate order is the renderer-resolved launcher, then
   `bin/override/soffice`, then legacy `bin/soffice`. Do not create the legacy
   path merely to make the repair script run.
3. Repair only failure classes `A` through `D`:

   - `A`: launcher missing or consumer topology mismatch
   - `B`: dyld or hard-coded Homebrew reference
   - `C`: LibreOffice profile or writable-cache failure
   - `D`: PDF created but Thai text/font is missing
   - `E`: PDF created but no rasterizer; use fallback, no LibreOffice patch
   - `F`: output-path or unrelated renderer failure; investigate that layer
   - `G`: invalid DOCX package/content; repair the document or generator

   ```bash
   python scripts/repair_soffice_runtime.py \
     --repair \
     --dependency-root <dependencies> \
     --bundle-version <version> \
     --renderer <render_docx.py> \
     --verify-docx <thai-and-omml-smoke.docx> \
     --knowledge-doc <project>/outputs/soffice-docx-render-fix-knowledge.md \
     --json
   ```

   Runtime-cache mutation may require escalation. `--dry-run` reports the
   intended launcher, patches, and backup without changing files.
4. If the project has no suitable fixture, create the bundled one:

   ```bash
   python scripts/create_smoke_fixture.py <temporary-output>/thai-omml-smoke.docx
   ```

   Run the same renderer command the document task will use. The smoke DOCX
   must contain Thai text, Latin text/numbers, and editable OMML. Require a
   non-empty PDF, at least one PNG, and evidence of an embedded Thai font when
   the DOCX contains Thai.
5. Open at least one rendered smoke page during a release/regression check.
   Then rerun diagnosis: it must be healthy or a no-op and must not create a
   second backup.

## Repair invariants

- Back up the active launcher before changing it; include its original checksum
  in the backup name so reruns remain idempotent and reversible.
- Generate wrapper paths relative to the launcher's real directory. A wrapper
  in `bin/override` needs different relative paths from one in `bin`.
- Use a temporary LibreOffice profile, writable cache, and a minimal generated
  Fontconfig file that names macOS font directories. Do not reuse the full
  Poppler Fontconfig configuration merely because its libraries are bundled.
- Patch only known Homebrew references whose bundled replacement exists. Leave
  an unmapped reference visible and fail safely.
- `soffice --version` proves launchability only. It never proves Thai or OMML
  render integrity.

## Status and evidence

The script emits `HEALTHY`, `LAUNCH_HEALTHY_UNVERIFIED`, `REPAIRED_DYLIB`,
`REPAIRED_WRAPPER`, `THAI_RENDER_FAILURE`, `RASTERIZER_MISSING`, or
`UNSUPPORTED_TOPOLOGY` in JSON or human-readable form. The unverified launch
status means `--version` passed but no content-bearing DOCX was checked. Preserve
exact failure signatures and retained warnings.

Knowledge entries are keyed by date, bundle version, active launcher, skill
version, and failure stage so multiple repairs on one day are not discarded.

Treat LibreOffice output as a layout sanity check, not final Microsoft Word
truth. Resume the original document task only after its real renderer passes.

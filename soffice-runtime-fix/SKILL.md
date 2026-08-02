---
name: soffice-runtime-fix
description: Automatically use when bundled LibreOffice/soffice or render_docx.py fails after Codex runtime updates on macOS, including dyld "Library not loaded", /opt/homebrew dylib errors for little-cms2/fontconfig/freetype, "User installation could not be completed", Fontconfig errors, or DOCX-to-PNG render failures; repair the runtime, restore the wrapper, verify rendering, and update the evolving local knowledge document.
---
<!-- SKILL-VERSION: 2026.06.29 | name: soffice-runtime-fix | canonical: ~/.codex/skills/soffice-runtime-fix | bump this date on every edit -->

# soffice-runtime-fix

Use this skill proactively when the user says `soffice` broke again, bundled
LibreOffice cannot launch, DOCX render QA fails, or the known `/opt/homebrew`
dylib problem returns after a Codex update.

Also use this skill automatically when **you** run or observe a failed command
with any of these signatures, even if the user did not name the skill:

- `soffice --version` exits nonzero
- `render_docx.py` fails while converting DOCX to PDF/PNG
- `dyld: Library not loaded`
- `/opt/homebrew/opt/little-cms2`
- `/opt/homebrew/opt/fontconfig`
- `/opt/homebrew/opt/freetype`
- `LibreOfficeDev - Fatal Error`
- `User installation could not be completed`
- `Fontconfig error`

When one of these signatures appears during document work, pause the document
task, repair `soffice` with this skill, verify the render path, then resume the
original task. Tell the user briefly that the render runtime self-healed.

## Workflow

1. Call `load_workspace_dependencies` first. Record the bundle version and
   dependency root.
2. Run `soffice --version` from the returned native binaries path and inspect
   the current `bin/soffice` wrapper.
3. Use `scripts/repair_soffice_runtime.py` to:
   - scan bundled LibreOffice for hard-coded `/opt/homebrew` dylib references
   - patch known references to bundled Poppler dylibs with `install_name_tool`
   - restore the robust wrapper with a temp LibreOffice profile and writable
     fontconfig cache
   - verify `soffice --version`
   - re-scan for remaining `/opt/homebrew` references
   - append a dated note to the local knowledge document
4. Run a real render smoke test using the current Documents plugin
   `render_docx.py` if a smoke DOCX is available:
   `work/docx-render-smoke/smoke.docx`.
5. If smoke render passes, update the knowledge document with PNG/PDF
   verification details. If it fails, fix rendering before claiming success.

## Script Invocation

Use the current paths from `load_workspace_dependencies`:

```bash
python scripts/repair_soffice_runtime.py \
  --dependency-root /Users/chutpong/.cache/codex-runtimes/codex-primary-runtime/dependencies \
  --bundle-version 26.x.y \
  --knowledge-doc outputs/soffice-docx-render-fix-knowledge.md
```

The script modifies files under the Codex runtime cache, so run it with
escalation when sandboxing blocks writes.

## Trust Policy

Treat `soffice` output as a layout sanity check, not final visual truth, when
fonts differ from Microsoft Word or the user's final renderer. Keep this
distinction in final replies.

## Knowledge Document

Default knowledge document:

```text
outputs/soffice-docx-render-fix-knowledge.md
```

When the repair pattern changes, update the document rather than leaving it as a
static historical note.

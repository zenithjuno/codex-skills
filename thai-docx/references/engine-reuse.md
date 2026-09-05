# Prose engine usage

Load only the section needed for the current operation. `engine.py` locates the
sibling engine; do not load the math skill's full instructions to borrow it.

## Create or edit

This example creates a new prose document, saves it, audits it, and writes the
QA reports. Set an absolute output path within the requested workspace.

```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path.home() / ".codex/skills/thai-docx/scripts"))
import engine

output = Path("/absolute/workspace/report.docx")
with engine.font_profile("prose"):
    doc = engine.new_prose_document()
    engine.builder.add_heading(doc, "รายงานสรุปผลการเรียน")
    engine.builder.add_paragraph(doc, [
        {"type": "text", "text": "เกณฑ์ผ่าน: คะแนน ≥ 80"}
    ])
    engine.builder.save_docx(doc, output)

result = engine.audit_prose(output)
reports = engine.qa.write_reports(result, report_dir=output.parent / "qa-reports")
print(result["verdict"], "word_review=", result["needs_word_review"], reports)
if result["verdict"] != "PASS":
    raise SystemExit(1)
```

Core calls: `add_heading(doc, text)`, `add_paragraph(doc, parts)`,
`add_table(doc, rows, widths=...)`, `save_docx(doc, path)`.
Table rows contain cells; each cell is a list of text-part dictionaries.
For explicit centimetres use
`thai_math_docx_layout.set_table_fixed_widths_cm(table, widths_cm)`.
For other layout calls, read only the builder/layout section of the sibling
`thai-math-docx/references/api-cheatsheet.md`.

For an existing document, open it with `docx.Document(input_path)`, preserve its
structure, and change only the requested content. The prose profile applies to
newly built content; do not reconfigure imported defaults as an incidental edit.

## QA

Use the same bootstrap as above, then call `engine.audit_prose(path, ...)` and
write reports. Default arguments describe a newly generated A4 document without
media. For imported documents pass `source_mode="imported"`; for a designated
teacher master use `source_mode="teacher-master"`. Declare custom layout and
media when present. Read the sibling `references/qa-runner.md` contract section
only when those require a non-default contract.

The returned verdict must be checked: calling `audit_prose` alone neither prints
a result nor fails the process. `PASS` covers automated checks;
`needs_word_review` remains an independent review flag. Audit-only work uses
`audit_prose` without save or repair calls.

## Preview

After structural QA for generated/repaired output:

```bash
python3 ~/.codex/skills/thai-math-docx/scripts/render_docx.py /absolute/workspace/report.docx --contact-sheet
```

For a preview-only request, render the supplied file directly. Inspect the fresh
contact sheet; open individual pages only where necessary. A preview does not
certify content or exact Word layout, and does not authorize changing the file.

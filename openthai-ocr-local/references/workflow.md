# Review and evidence workflow

Use `PY=~/.local/share/openthai-ocr/venv/bin/python` and the absolute skill folder to invoke `scripts/document.py`. Examples below abbreviate that entrypoint as `document.py`; always use the dedicated interpreter.

## Output contract

The output folder is a document cache. `manifest.json` pins source hash, model revision, reader hash, DPI and reading method. `page-NNNN.json` retains text, line boxes/confidence and `dropped` entries/reasons; `.txt` is the raw text. Text-layer lines have no OCR confidence or per-line pixel box. `index.json` holds the complete local chunk index; it can be large.

`audit.json` reports requested/processed pages, missing or invalid results, per-page quality flags, and current visual review records. It never assigns a document-wide accuracy score. Rules currently cover missing/invalid results, short/empty text, likely blank ink, discarded/low-confidence lines, invalid characters, repetition, rotation/skew, malformed digit grouping and disagreement with a retained higher-DPI retry. Dates, arithmetic totals and table relationships are not generically verified by these rules; inspect task-critical facts visually or with a task-specific check. No independent OCR engine is installed.

`requests/<fingerprint>/` contains the request snapshot, per-request audit, `packet.txt`, a short audit report, and review images/transcripts (retained and discarded lines, labelled explicitly). Identical requests reuse the path; review state/code/settings changes yield new fingerprints. These are regenerated outputs, not an append-only history. The packet labels `Page N`, `[Lx]` retained lines, `[Dx]` recovered discarded lines and adjacent-page context explicitly. Search selection includes overlapping context and neighboring page edges; a header farther away still needs deliberate inspection. Overview shows page-leading lines, not AI-generated summaries; omitted overview pages are counted.

`reviews.json` retains visual evidence and explicit corrections tied to the exact page-result hash. The latest verdict for a given page/scope controls status; task-region checks are reused only for the same query/terms, while full-page checks can serve other questions; stale records are excluded when the raw result changes. `task_relevant_region` reviews do not imply a full page is verified. `risk_pages_without_full_page_review` remains explicit. Corrected text is used in future evidence packets, with discarded-line recoveries placed by source row/position where available; raw files remain unchanged. This does not reconstruct table cells.

## Record a real visual comparison

Read the request's task list to obtain its ID. After actually inspecting the source image:

```sh
document.py review '/absolute/cache/requests/REQUEST' --task 'TASK_ID' --verdict matched --scope task_relevant_region --evidence 'Compared the target-group and school-term lines with the source image; class, pupil count and year agree. Other lines not checked.'
```

Verdicts: `matched`, `corrected`, `uncertain`. An unresolved issue must remain uncertain. `--scope full_page` is reserved for a full comparison, not a quick page glance. This is an evidence log, not an automatic verifier; an assistant must not fabricate its evidence.

For a correction, write a UTF-8 JSON file with raw stable line IDs and exact before text:

```json
[
  {"line": "L12", "before": "Uทคัดย่อ", "after": "บทคัดย่อ"},
  {"line": "D1", "before": "ซู้อมูด", "after": "ข้อมูล"}
]
```

Then use `--verdict corrected --corrections '/absolute/edits.json' --evidence '...'`. Only include edits actually established from the image. Before text must match the raw line, preventing accidental edits to the wrong content. Each retained line is L1-based; discarded lines are D1-based in their respective arrays. After recording, `inspect` refreshes the effective text/audit; it does not silently overwrite raw output.

## Crop and one local retry

```sh
document.py crop '/absolute/cache' --page 2 --box 100 300 1300 800 --out '/absolute/task/check-region.png'
document.py retry '/absolute/cache' --page 2
```

Crop coordinates are source pixels at the cache's rendering DPI (`image_size` for OCR pages), not PDF points. Crop validation rejects out-of-bounds regions. Keep page/line provenance and enough adjacent context; whole-table comparisons may require the prior page's header too.

Retry adds 100 DPI up to 600, forces OCR once per selected page into `cache/retry/`, and writes a comparison. Repeating the same retry uses its cache. It preserves the original and never promotes an alternative automatically. For a native text-layer page, this can provide an OCR comparison, but still cannot certify correctness. Check image evidence where the readings differ. At the maximum DPI, prefer image review instead of claiming a higher-resolution retry.

## Budget and stopping rules

- Evidence defaults to 4,000 Unicode characters, not tokens, and four review images. Metadata/status is additional and reported separately from evidence size. Use `--images 0` for subsequent text-only batches so review images do not multiply unnecessarily.
- Scope can be a selected page range or whole document; an audit of selected pages is never described as whole-document completion.
- `remaining_chunks`, `before_offset`, `next_offset`, `blocked_by_budget`, incomplete pages and overview omissions expose gaps. A packet is delivered context, not a semantic guarantee of relevance or factual correctness.
- For no matches, broaden literal terms or use source-order reading. When scope/budget cannot support the task, report what remains unverified/unread and the necessary next step.
- Keep the actual comparison budget bounded across helper calls, not four new images on every refresh. A one-request assistant workflow may use several local commands; it should not ask the user to perform those routine steps.
- Count full text, actual emitted evidence/status, image checks and repair rounds when comparing context use. Do not present character reduction as a measured token saving. For whole-document summaries, batching does not eliminate the need to read all relevant content.

## Verification

```sh
~/.local/share/openthai-ocr/venv/bin/python -m unittest discover -s /absolute/skill/tests -v
```

The tests cover audit signals versus correctness, context across pages, alternate search phrases, tiny budgets, complete batching, corrections/provenance, missing/corrupt page results, PDF text-layer versus image routing, PNG, retries, crop bounds, and stale-source/cache rejection. Integration subprocesses run with outbound socket connections disabled. Thai integration fixtures use this Mac's `~/Library/Fonts/THSarabunNew.ttf`; if unavailable those integration tests explicitly skip and must not be reported as passed. Evaluate OCR quality separately on visually checked representative Thai documents, including real tables/degraded pages; functional test success alone is not an accuracy measurement.

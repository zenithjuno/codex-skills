# Model source and update tracking

## Installed model

- **Model:** `iapp/OpenThai2.1-OCR-Text-20261118` (OpenThai 2.1 OCR Text).
- **Publisher:** iApp Technology / OpenThai.
- **Model-card version:** v2.1.4, 18 November 2026.
- **Installed upstream Git revision:** `fac2b5ceefc19d66e65de7d32d75ab99c7e927c8`.
- **Recorded installation date:** 18 November 2026.
- **Task:** Thai and English printed-text OCR on CPU. Returns reading-order text plus line boxes and confidence; no reconstructed table grid.
- **Detector:** PaddlePaddle PP-OCRv6-tiny, `det.onnx`, 1,780,590 bytes.
- **Recognizer:** iApp Thai CTC line recognizer fine-tuned from PP-OCRv6-tiny, `rec.onnx`, 2,392,837 bytes.
- **Second recognizer:** `rec2.onnx`, 2,392,837 bytes, for selective re-reading of loopless Thai fonts. All three ONNX files total about 6.6 MB.
- **Licence:** Apache-2.0, upstream `NOTICE` retained in the installed model folder.
- **Backend used here:** ONNX Runtime, explicitly `CPUExecutionProvider`; no GPU or hosted OCR API.

These facts describe the installed release, not whichever release is newest when this reference is read. Read `models/REVISION` in the installation for the actual local pin.

## Canonical upstream links

- [Model card and usage](https://huggingface.co/iapp/OpenThai2.1-OCR-Text-20261118)
- [Current source and model files](https://huggingface.co/iapp/OpenThai2.1-OCR-Text-20261118/tree/main)
- [Upstream commit history — check here for updates](https://huggingface.co/iapp/OpenThai2.1-OCR-Text-20261118/commits/main)
- [Exact installed source revision](https://huggingface.co/iapp/OpenThai2.1-OCR-Text-20261118/tree/fac2b5ceefc19d66e65de7d32d75ab99c7e927c8)
- [Publisher's Thai installation guide](https://iapp.co.th/blog/openthai2p0-ocr-how-to-run)
- [Publisher's English installation guide](https://iapp.co.th/en/blog/openthai2p0-ocr-how-to-run)

The related [OpenThai2.1-OCR-Markdown-20261118](https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118) is a **different model**, derived from NVIDIA Nemotron 3.5 Parse, with a different licence and runtime. It is not installed here. Do not silently switch to it as an update of Text.

## Local resources

Runtime root: `~/.local/share/openthai-ocr/`.

- `venv/bin/python`: dedicated Python environment; `requirements-lock.txt` records installed package versions.
- `models/REVISION`: installed upstream commit pin.
- `models/det.onnx`, `rec.onnx`, `rec2.onnx`, `rec_dict.txt`, `det.yml`, `config.json`: inference resources.
- `models/runtime/__init__.py`, `line_engine.py`, `thai_norm.py`: upstream Python runtime code, downloaded from the same revision as the weights.
- `models/README.md`, `NOTICE`, `SHA256SUMS`: upstream documentation and checksum reference.

The skill release intentionally excludes model weights, the Python environment, and user documents. Another machine needs a separate runtime installation. Use the publisher's installation guide and the exact source revision above for reproducibility; on Apple silicon use ONNX Runtime CPU as this helper does.

## Checking and applying an update

1. Read the current local `models/REVISION`; compare it with upstream Hugging Face tags, commit history and iApp release notes. The skill’s GitHub repository tracks our wrapper and instructions. The weights and upstream runtime are released on Hugging Face. Resolve the desired release tag to an immutable commit before downloading. A changed commit may be documentation only, not new weights.
2. When an update is requested, review runtime/API changes, dependencies and licence. Download a complete candidate into a separate model directory from **one exact commit**, retaining the old installation. Do not mix runtime code and weights from different revisions.
3. Verify relevant downloaded model/runtime files against upstream checksums where provided. All 12 downloaded files listed in the pinned release checksum manifest matched. If no trustworthy matching manifest is available, record actual SHA-256 hashes and the immutable source URLs instead of claiming upstream checksum verification.
4. Before replacing the active model, test representative readable Thai page images and a multi-page scan. Visually confirm Thai glyphs exist in the input first. Compare text, important numbers, runtime, and memory with the previous version; include known OCR mistakes. High line confidence alone does not prove correct transcription.
5. If the update passes, install the complete model directory and update `models/REVISION` to the exact commit. Update this reference when its installed-model facts change, refresh the dependency lock if dependencies changed, validate the skill and release the scoped changes.
6. Use a fresh output cache for the new revision. The helper includes the revision in its cache identity and rejects a cache created with a different model revision. Preserve old outputs for comparison.

Do not automatically replace the working model merely because upstream changed. A request to check for updates is read-only; an explicit update/install request authorizes the corresponding local change.

On the M5 Mac with 24 GB unified memory, use Text for batch search and prose. Consider Markdown GGUF with the publisher’s llama.cpp fork and Metal for selected table/formula pages after testing against originals. The skill disables Text v2.1.4 automatic decimal-comma rewriting to preserve evidence for auditing.

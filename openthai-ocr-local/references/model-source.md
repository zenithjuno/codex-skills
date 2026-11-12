# Model source and update tracking

## Installed model

- **Model:** `iapp/OpenThai2.0-OCR-Text` (OpenThai 2.0 OCR Text).
- **Publisher:** iApp Technology / OpenThai.
- **Model-card version:** v1.0.0, November 2026.
- **Installed upstream Git revision:** `39fa41bdd49f067ba41b1d9de79c06ab506d67d4`.
- **Recorded installation date:** 12 November 2026.
- **Task:** Thai and English printed-text OCR on CPU. Returns reading-order text plus line boxes and confidence; no reconstructed table grid.
- **Detector:** PaddlePaddle PP-OCRv6-tiny, `det.onnx`, 1,780,590 bytes.
- **Recognizer:** iApp Thai CTC line recognizer fine-tuned from PP-OCRv6-tiny, `rec.onnx`, 2,392,837 bytes.
- **Licence:** Apache-2.0, upstream `NOTICE` retained in the installed model folder.
- **Backend used here:** ONNX Runtime, explicitly `CPUExecutionProvider`; no GPU or hosted OCR API.

These facts describe the installed release, not whichever release is newest when this reference is read. Read `models/REVISION` in the installation for the actual local pin.

## Canonical upstream links

- [Model card and usage](https://huggingface.co/iapp/OpenThai2.0-OCR-Text)
- [Current source and model files](https://huggingface.co/iapp/OpenThai2.0-OCR-Text/tree/main)
- [Upstream commit history — check here for updates](https://huggingface.co/iapp/OpenThai2.0-OCR-Text/commits/main)
- [Exact installed source revision](https://huggingface.co/iapp/OpenThai2.0-OCR-Text/tree/39fa41bdd49f067ba41b1d9de79c06ab506d67d4)
- [Publisher's Thai installation guide](https://iapp.co.th/blog/openthai2p0-ocr-how-to-run)
- [Publisher's English installation guide](https://iapp.co.th/en/blog/openthai2p0-ocr-how-to-run)

The related [OpenThai2.0-OCR-Markdown](https://huggingface.co/iapp/OpenThai2.0-OCR-Markdown) is a **different model**, derived from NVIDIA Nemotron 3.5 Parse, with a different licence and runtime. It is not installed here. Do not silently switch to it as an update of Text.

## Local resources

Runtime root: `~/.local/share/openthai-ocr/`.

- `venv/bin/python`: dedicated Python environment; `requirements-lock.txt` records installed package versions.
- `models/REVISION`: installed upstream commit pin.
- `models/det.onnx`, `rec.onnx`, `rec_dict.txt`, `det.yml`, `config.json`: inference resources.
- `models/runtime/__init__.py`, `line_engine.py`, `thai_norm.py`: upstream Python runtime code, downloaded from the same revision as the weights.
- `models/README.md`, `NOTICE`, `SHA256SUMS`: upstream documentation and checksum reference.

The skill release intentionally excludes model weights, the Python environment, and user documents. Another machine needs a separate runtime installation. Use the publisher's installation guide and the exact source revision above for reproducibility; on Apple silicon use ONNX Runtime CPU as this helper does.

## Checking and applying an update

1. Read the current local `models/REVISION`; compare it with upstream commit history and model-card release notes. A changed commit may be documentation only, not new weights.
2. When an update is requested, review runtime/API changes, dependencies and licence. Download a complete candidate into a separate model directory from **one exact commit**, retaining the old installation. Do not mix runtime code and weights from different revisions.
3. Verify relevant downloaded model/runtime files against upstream checksums where provided. At the installed revision, nine downloaded non-README resources matched `SHA256SUMS`; its README checksum is stale, so do not mistake that documentation mismatch for proof that weights are corrupt. If no trustworthy matching manifest is available, record actual SHA-256 hashes and the immutable source URLs instead of claiming upstream checksum verification.
4. Before replacing the active model, test representative readable Thai page images and a multi-page scan. Visually confirm Thai glyphs exist in the input first. Compare text, important numbers, runtime, and memory with the previous version; include known OCR mistakes. High line confidence alone does not prove correct transcription.
5. If the update passes, install the complete model directory and update `models/REVISION` to the exact commit. Update this reference when its installed-model facts change, refresh the dependency lock if dependencies changed, validate the skill and release the scoped changes.
6. Use a fresh output cache for the new revision. The helper includes the revision in its cache identity and rejects a cache created with a different model revision. Preserve old outputs for comparison.

Do not automatically replace the working model merely because upstream changed. A request to check for updates is read-only; an explicit update/install request authorizes the corresponding local change.

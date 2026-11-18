# Local OpenThai Markdown 2.1

Use this reader for pages whose table structure or mathematical notation matters. For searching a long document, ordinary prose, and the standard page-by-page audit, use the Text workflow. If a table spans pages, include the header page and relevant continuation pages.

```sh
~/.local/share/openthai-ocr/markdown/venv/bin/python /Users/chutpong/.codex/skills/openthai-ocr-local/scripts/read_markdown.py '/absolute/input.pdf' --pages '4,8-9' --out '/absolute/task/new-markdown-output'
```

PDFs require explicit page selection. For a single image omit the page flag. Use a new writable output folder. A failed or interrupted run may leave completed pages and a log. Reuse completed results after checking source and pinned versions. The helper prints only page numbers, timings and paths. Each `page-NNNN.md` contains rendered Markdown with HTML tables and LaTeX. The JSON alongside it preserves the source path, page, exact model/runtime revisions, structured blocks and raw response. Read bounded portions of the Markdown with adjacent headers and page references. Audit table dimensions, merged cells and important values against the source. For equations, inspect signs, indices, grouping, fraction bounds and exponents. Report ambiguous portions. Markdown results do not replace the Text audit or automatically correct OCR evidence.

The helper starts the iApp llama.cpp engine on an authenticated loopback-only connection for the duration of the run. All model inference is local. It uses the Apple GPU via Metal, with CPU work where required. The model requires the matched vision encoder. The two GGUF files total about 1.12 GB, separate from runtime disk and memory use.

## Installed sources

- [GGUF, exact revision](https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118-GGUF/tree/ce0d5466e035867fff870b465c612262f409f42d). Q8_0 decoder plus F16 vision encoder. Both files verified against Hugging Face LFS SHA-256 values.
- [OpenThai Markdown v2.1.0 parser, exact revision](https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118/tree/bc79c3521d56ad299da41ece6f57641e8fd7282e). Licence OpenMDW 1.1. Attribution and notices are installed with these files.
- [iApp llama.cpp fork, exact revision](https://github.com/iapp-technology/llama.cpp/tree/1796ec1d0835f2b94330c01c6ddc6f3438748021), built with Metal and kernels embedded, with the web UI and external downloads disabled. Upstream generic llama.cpp does not supply this architecture in the cited release.

Installation is under `~/.local/share/openthai-ocr/markdown/`. See `pins.json`, `requirements-lock.txt` and `upstream.md` there. Check the upstream model card and the fork before upgrading these paired components. Verify the pinned files, then compare a known Thai table and formula against images before switching. If the runtime is missing, report or repair this local installation.

# Workspace & Code Token Hygiene

`project_context.py` protects **document routing** (`AGENTS.md`, `STATE.md`, `docs/`).
`workspace_hygiene.py` and `token_profiler.py` protect **code search, media/browser usage, and session length**.

## 1. Stop search traps with `.rgignore`

Unignored minified fixtures or historical dumps burn tens of thousands of tokens on a single `grep`/`rg` call:

```sh
W=<skill-directory>/scripts/workspace_hygiene.py
python3 $W audit --root <root>
python3 $W init-ignore --root <root>          # dry-run preview (respects live project-context routes)
python3 $W init-ignore --root <root> --write  # apply safely
```

Always keep `legacy/`, `private/`, `_snapshots/`, `archive/`, `reference/`, cold `outputs/`, and minified vendor/fixture JS out of default search.

## 2. Jump to functions with `CODEMAP.md`

For large code files (>600 lines, e.g. `Code.gs` or `core.js`), read `CODEMAP.md` first and open only the `Lstart-Lend` range you need:

```sh
python3 $W codemap --root <root> --write CODEMAP.md   # creates or updates marker block only
python3 $W codemap --root <root> --check CODEMAP.md   # exit 1 if symbol line ranges drifted
```

It indexes file scope, wrapping IIFE bodies, `A.fn = ...`, `X.prototype.fn`, and class methods (up to 200 symbols/file). Custom sections outside `<!-- workspace-hygiene:codemap:start/end -->` are preserved; hand-crafted maps without markers are never overwritten unless `--force` is passed.

## 3. Peek large data schemas without dumping rows (`peek`)

Never `read_file` or dump raw JSON/CSV/JSONL tables just to check keys or row counts:

```sh
python3 $W peek path/to/data.json
```

Prints only counts, column headers, and key/type shapes — zero raw values or PII.

## 4. Measure real session leaks (`token_profiler.py`)

```sh
P=<skill-directory>/scripts/token_profiler.py
python3 $P --limit 5 [--project <name>] [--json]
```

Profiles `~/.claude/projects/**/*.jsonl` (counts + bytes only, zero chat text) and flags:
- **DOM-First, Screenshot-Last:** prefer `javascript_tool` (<1 KB/call) over browser screenshots (`computer` / `browser_batch` ~40–70 KB/call); screenshot only the final visual pass.
- **Subagent Media Quarantine:** delegate multi-page PDF or rendered PNG inspection to a subagent so binary payloads never stay in the main thread across hundreds of turns.
- **Thread Length Multiplier:** once a session exceeds ~150–200 API calls, run `handoff` to reset `cache_read` overhead.

## 5. Routine-to-Script rule (the 11% Token Pattern)

Whenever a workflow repeats **≥ 2 times** or inspects **> 20 rows/records** (e.g. `ppksar` audit/write, gradebook checks, batch document generation):

1. Put variable targets/rules in JSON (`targets.json` or `config.json`), not prose.
2. Run deterministic capture/check scripts that read raw files directly and emit **only counts, verdicts, and mismatch IDs**.
3. Let the check script generate `check.json` / `closeout.md` (`before` vs `after` diff).
4. Record tool quirks once in `Known Tool Pitfalls` so future sessions never burn tokens retrying broken paths.

# Workspace & Code Token Hygiene

`project_context.py` protects **document routing** (`AGENTS.md`, `STATE.md`, `docs/`).
`workspace_hygiene.py` protects **code search & reading** — the other half of token cost.

## 1. Stop search traps with `.rgignore`

One unignored minified fixture (e.g. 750 KB on 1 line) or 7 snapshot copies of an HTML app can burn tens of thousands of tokens on a single `grep`/`rg` call.

```sh
W=<skill-directory>/scripts/workspace_hygiene.py
python3 $W audit --root <root>
python3 $W init-ignore --root <root>          # dry-run preview
python3 $W init-ignore --root <root> --write  # apply safely
```

Always keep `legacy/`, `private/`, `outputs/`, `_snapshots/`, `archive/`, `reference/`, and minified vendor/fixture JS out of default search.

## 2. Jump to functions with an auto `CODEMAP.md`

For monolith files (>600 lines, e.g. `Code.gs` or `core.js`), reading the whole file every turn burns context. Generate a compact symbol index once (and refresh after major refactors):

```sh
python3 $W codemap --root <root> --write CODEMAP.md
```

Agents read `CODEMAP.md` first, then open only the exact `Lstart-Lend` range of the function they need.

It indexes module-level code: file scope and the body of a wrapping IIFE (`(function(){ … })()`), which most browser scripts use. Listed: `function f()`, `const f = () =>`, member assignments (`A.save = function`, `A.pages.plan = {`, `X.prototype.m = function`) and class methods (`Engine.search`). Helpers nested inside a function are not listed. Up to 200 symbols per file.

## 3. Routine-to-Script rule (the 11% Token Pattern)

Whenever a workflow repeats **≥ 2 times** or inspects **> 20 rows/records** (e.g. `ppksar` audit/write cycles, gradebook checks, batch document generation):

1. Put variable targets/rules in a machine-readable JSON (`targets.json` or `config.json`), not prose.
2. Run deterministic capture/check scripts that read raw files/exports directly and print **only counts, verdicts, and mismatch IDs** — never dump raw rows into LLM stdout.
3. Let the check script generate `check.json` / `closeout.md` (including `before` vs `after` diff so untouched fields stay untouched).
4. Record concrete tool quirks once in a `Known Tool Pitfalls` section so future sessions never burn tokens retrying broken paths.

---
name: gas-html-guard
description: Fast anti-slop and syntax back-pressure gate for Google Apps Script (.gs) and standalone HTML/JS projects. Runs deterministic checks (JS syntax via `node --check` including inline `<script>` in `.html` and GAS `<?!= ?>` templates, `.gs` and HTML-partial global scope collisions, GAS loop I/O, unsafe `getContent()` in `include()`, missing `withFailureHandler`, empty `catch`, raw `innerHTML`, and monolith/god-function size guards) with compact token-efficient output. Use before `clasp push`, deploy, commit, or after editing `.gs`/`.html`/`.js` code — triggers include "ตรวจโค้ด GAS/HTML", "anti-slop", "gas-html-guard", "เช็กก่อน push", "เช็ก syntax .gs/.html".
---
<!-- SKILL-VERSION: 2026.11.25 | name: gas-html-guard | canonical: ~/.codex/skills/gas-html-guard | bump this date on every edit -->

# GAS & HTML Anti-Slop Guard

Deterministic, zero-npm back pressure for Google Apps Script (`.gs`) and HTML/JS projects.
Run this **before** `clasp push`, deploy, or commit — never rely on memory or prose reminders alone.

## Run the gate

```bash
python3 ~/.codex/skills/gas-html-guard/scripts/gas_html_guard.py <src-dir-or-file>
```

Optional flags:
- `--max-lines 600` — warn when a code file exceeds this line count (default: 600)
- `--max-func-lines 120` — warn when a single function exceeds this line count (default: 120)
- `--no-syntax` — skip `node --check` (only if `node` is unavailable)

Exit codes:
- `0` = **PASS** — clean
- `1` = **WARN** — soft anti-slop warnings (review or justify; does not hard-block unless project policy says so)
- `2` = **FAIL** — hard blockers; **fix before `clasp push` or commit**

## What it catches

| Severity | Rule | What it prevents |
|---|---|---|
| `FAIL` | `SYNTAX` | Broken JS in `.gs`, `.js`, or inline `<script>` inside `.html` (handles GAS `<?!= ... ?>` scriptlets with exact line numbers) |
| `FAIL` | `GLOBAL_COLLISION` | Duplicate top-level `function` names across `.gs` files in the same project (GAS merges all `.gs` into one global scope) |
| `FAIL` | `GAS_INCLUDE_GETCONTENT` | `createHtmlOutputFromFile(...).getContent()` instead of `.getRawContent()` (causes `Malformed HTML` on `<`/`>` in JS) |
| `FAIL` | `DEBUGGER` | Leftover `debugger;` statements |
| `WARN` | `HTML_GLOBAL_COLLISION` | Duplicate top-level `function` names across HTML partials (`js-*.html`) |
| `WARN` | `GAS_LOOP_IO` | `getValue`/`setValue`/`getRange`/`appendRow` inside loops (causes quota/timeout failures; batch with `getValues`/`setValues`) |
| `WARN` | `GAS_NO_FAILURE_HANDLER` | `google.script.run` call missing `.withFailureHandler(...)` (fails silently in UI) |
| `WARN` | `EMPTY_CATCH` | Empty `catch {}` blocks hiding failures |
| `WARN` | `RAW_INNERHTML` | Dynamic `.innerHTML` without a visible escape helper (XSS / quote-breakage risk) |
| `WARN` | `MONOLITH_FILE` / `GOD_FUNCTION` | Oversized files (>600L) or functions (>120L) that inflate token usage and edit risk |

## Output discipline

- Quote the exact verdict and `FAIL` lines; never paraphrase a `FAIL` away.
- Respects `.rgignore` / `.ignore` / `.gasguardignore` and automatically skips `legacy/`, `private/`, `outputs/`, `_snapshots/`, `archive/`, `reference/`, `node_modules/`.
- For pre-publish browser/offline checks on learning games, run `ship-check` after this gate passes.

## Enforcement & Routine-to-Script templates

To wire this gate into `AGENTS.md`, `deploy.sh`, or git pre-commit — or to apply the **Routine-to-Script (11% Token Pattern)** for repetitive workflows — read [references/enforcement-templates.md](references/enforcement-templates.md).

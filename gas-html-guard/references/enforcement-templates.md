# Enforcement & Routine-to-Script Templates

Copy-paste blocks to turn prose reminders into mechanical back pressure across current and future projects.

---

## 1. `AGENTS.md` Hard Gate Block (3 lines)

Drop this into any GAS / HTML project's `AGENTS.md` under `## Verification` or `## Safety`:

```markdown
## Code & Token Gates (mandatory before push/commit)
- Anti-slop & syntax gate: `python3 ~/.codex/skills/gas-html-guard/scripts/gas_html_guard.py src/` (exit 2 = FAIL, must fix before `clasp push` or commit)
- Workspace hygiene / codemap: `python3 ~/.codex/skills/project-bootstrap/scripts/workspace_hygiene.py audit --root .`
```

---

## 2. `deploy.sh` Pre-Push Gate (for `clasp` projects)

Insert these 5 lines **before** `clasp push` in `deploy.sh` so broken syntax or `.gs` global collisions can never reach Apps Script:

```bash
GUARD="$HOME/.codex/skills/gas-html-guard/scripts/gas_html_guard.py"
if [ -f "$GUARD" ]; then
  python3 "$GUARD" src/ || {
    rc=$?
    [ "$rc" -eq 2 ] && { echo "BLOCKED: gas-html-guard FAIL — fix blockers before clasp push"; exit 2; }
  }
fi
```

*(Exits only on `rc=2` FAIL; `rc=1` WARN prints findings and still lets you deploy if intentional. Change `[ "$rc" -eq 2 ]` to `[ "$rc" -ne 0 ]` for strict mode.)*

---

## 3. Optional Git Pre-Commit Hook

Save as `.git/hooks/pre-commit` (`chmod +x .git/hooks/pre-commit`):

```bash
#!/bin/sh
GUARD="$HOME/.codex/skills/gas-html-guard/scripts/gas_html_guard.py"
[ -f "$GUARD" ] || exit 0
python3 "$GUARD" .
rc=$?
[ "$rc" -eq 2 ] && echo "Commit blocked by gas-html-guard (FAIL)." && exit 1
exit 0
```

---

## 4. The "Routine-to-Script" Pattern (Proven 11% Token Workflow)

Extracted from the `ppksar` (`write-task` / `audit-cycle`) and `grade-cut` optimizations where moving repetitive work from LLM eyes to deterministic scripts cut token usage from hitting session limits down to ~11%.

**Trigger rule:** Whenever a task will repeat **≥ 2 times** OR requires checking/transforming **> 20 rows/records**, STOP having the LLM eyeball raw tables or write manual closeouts. Build this 4-piece micro-kit instead:

1. **Machine-readable input (`targets.json` or `config.json`)**
   - Put variable parameters (IDs, thresholds, rules, waivers) in JSON, not prose.
   - Generate human-readable `ASSIGNMENT.md` from JSON if needed; never parse prose back into code.
2. **Deterministic capture + judge scripts (`scan`/`snap` → `check.py`)**
   - Scripts read raw data (JSON, CSV, PDF, Sheet export, DOM snapshot) directly.
   - **Output cap rule:** Scripts print **only counts, verdicts, and mismatch IDs** (`file:line` or `id: field expected != actual`). Never dump full raw rows into LLM stdout.
   - Enforce *"things not ordered = must not change"* by diffing `before.json` vs `after.json` mechanically.
3. **Script-generated closeout (`closeout.md` / `check.json`)**
   - Do not ask the LLM to hand-type checklists or self-certify pass/fail. Let `check.py` emit the verdict and summary table.
4. **Append-only `Known Tool Pitfalls` section**
   - Record concrete tool quirks once (e.g., Chrome 1,000-char eval truncation → chunk at 900 chars; Safari iframe upload fails → use Chrome; GAS `getContent()` breaks JS → use `getRawContent()`) so future sessions never burn tokens rediscovering them.

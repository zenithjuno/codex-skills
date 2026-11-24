# Handoff Templates and Writing Rules

Use these exact templates when creating a Codex continuity snapshot and updating a stable pointer.

## 1. Routing Record (determine before writing)

```text
scope_kind: project | work-object | personal | unknown
scope_id: <identifier | unknown>
lifecycle: current | transition | historical
canonical_directory: <path | fallback>
current_pointer: <path | none>
current_pointer_scope: <scope | unknown>
archive_directory: <path | none>
proposed_snapshot: <path>
pointer_action: update | preserve | none
archive_action: archive-same-scope | none
reason: <one sentence>
```

## 2. Dated Snapshot Template (`handoff-YYYY-MM-DD-<short-slug>.md`)

Write in English by default for token efficiency; preserve Thai work products, code, math, prompts, and finalized wording verbatim. Drop sections only when genuinely empty.

```markdown
# Codex Handoff: <YYYY-MM-DD> — <short task title>

- Handoff date: `<YYYY-MM-DD>`
- Handoff slug: `<short-slug>`
- Scope kind: `<project | work-object | personal | unknown>`
- Scope ID: `<stable identifier | unknown>`
- Expected resumer: `<role/person/session | unknown>`
- Lifecycle: `<current | transition | historical>`
- Canonical handoff location: `<repository-relative path>`
- Snapshot file: `<repository-relative path>`
- Current-pointer action: `<updated <path> | preserved <path> | none>`

> **For the Codex session picking this up:** You are continuing work already in
> progress. You cannot see the previous conversation. Treat this handoff as the
> conversation state plus the workspace map. Start with "Start Here," inspect
> the listed files, then continue from "Next Steps." If something required is
> missing, ask the user rather than inventing it.

## Start Here
- Workspace root: `<absolute path>`
- Handoff file: `<absolute path to this dated snapshot>`
- Current goal: <one sentence>
- Immediate next action: <the next thing Codex should do>
- Do not redo: <settled decisions, completed work, or checks that should not be repeated unless there is a reason>

## Files To Inspect First
- `<absolute/or/workspace-relative/path>` — <why it matters and what to look for>

## Current Workspace State
- Created: <files or "none known">
- Modified: <files or "none known">
- Outputs delivered: <files or "none known">
- Temporary/work files: <files worth keeping, ignoring, or cleaning up>

## Decisions Already Made
- <decision> — <why, so the next session does not reopen it>

## Checks Already Run
- <check/command/process> — <passed, failed, blocked, or key result>

## Conversation-Only State
- <important context, preferences, constraints, or facts that live only in chat>

## Verbatim Carry-Forward Content
<Only include exact content here if it does not already live in a workspace file, or if exact wording must survive. Preserve Thai, code, math, prompts, and finalized text exactly.>

## Next Steps
- [ ] <specific next action>
- [ ] <specific next action>

## User Preferences For This Task
- <language, tone, formatting, verification, tool, or workflow preferences>

## Files To Re-upload
- `<filename>` — <only for uploads, downloads, Desktop files, external files, or anything outside the workspace that a fresh session may not access>

## Suggested Skills
- `<skill-name>` — <why it will help>
```

## 3. Short Stable-Pointer Template (`handoff-latest.md` or policy pointer)

```markdown
# Current Codex Handoff

- Scope: `<scope kind>/<scope ID>`
- Lifecycle: `<current | transition | historical>`
- Current snapshot: `<repository-relative path>`
- Updated: `<YYYY-MM-DD HH:MM timezone>`

Open the current snapshot above before continuing.
```

## 4. Writing Quality Rules

- Put the highest-value continuation information at the top; the next session should understand the task in 15 seconds.
- Include both date and a specific kebab-case slug (`nu-science-set-bank`, not `handoff`, `new-chat`, `project`, or `continue`). On collision, add `-HHMM` or `-02`.
- Make "Immediate next action" concrete enough to start without broad questioning; use "Do not redo" to prevent relitigating settled decisions.
- Keep workspace files as pointers, never pasted content; state exact check results (including failures/blockers).

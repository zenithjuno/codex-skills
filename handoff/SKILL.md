---
name: handoff
description: >
  Create a scope-safe, repo-aware continuity handoff for resuming in a fresh session.
  Triggers: "handoff", "hand this off", "continue in a new chat", "start a fresh chat",
  "this chat is getting long", "running low on context", "ส่งต่อ", "สรุปไว้ไปคุยต่อแชทใหม่",
  "เปิดแชทใหม่", "แชทนี้ยาวแล้ว".
---
<!-- SKILL-VERSION: 2026.11.25 | name: handoff | canonical: ~/.codex/skills/handoff | bump this date on every edit -->
<!-- SKILL-FINGERPRINT: updated_at=2026-11-25 | change=split templates to references/handoff-templates.md and slim frontmatter -->

# Handoff

Create a Codex continuity file: a compact mission briefing plus workspace index
that lets a fresh session continue efficiently in the same project. A handoff is
the next session's starting map, not a generic recap.

## Core Rules

Capture conversation-only state, exact workspace paths to inspect, settled
decisions (with why), checks already run (with real outcomes), user preferences,
and the immediate next action. **Keep workspace files as pointers, not pasted
content**; include verbatim text only when it exists solely in chat or exact
wording must survive.

## Scope & Lifecycle

Treat every handoff as a scoped routing object, not merely the newest file by date:
- **Scope kind:** `project`, `work-object`, or `personal`.
- **Scope ID:** stable identifier (`project` for project-wide).
- **Expected resumer:** informative role/person/session (does not define succession).
- **Lifecycle:** `current`, `transition`, or `historical`.

Only a note with matching `scope kind + scope ID` may replace that scope's
current pointer or archive its prior current snapshot. Never archive another
active scope's handoff, and never promote a transition/status note to current
by filename or recency. If scope is unknown, set `pointer_action: none`.

## Fast Preflight & Precedence

Run this small, read-only discovery in order before writing:
1. Read any explicit user destination, scope, lifecycle, or promotion request.
2. Read workspace-root `AGENTS.md` and only instruction files it directly names.
3. Read any existing handoff readme/index and current pointer(s).
4. If `project-context.json` exists, run `project-bootstrap` `check --root <root> --format md` once; exit 3 (partial) is **not** a pass — fix or report findings. Skip when no config exists.

Resolve destination and storage policy in order: (1) explicit user instruction,
(2) current repo instructions/governance, (3) explicit handoff readme/index and
canonical pointer, (4) configured deliverables folder, (5) `outputs/` fallback.
Use targeted Git history only to resolve path conflicts or suspected
migrations; never recreate a retired handoff location or invent new archive/index
folders without user approval.

Before writing the snapshot or pointer file, read
[references/handoff-templates.md](references/handoff-templates.md) and follow its
Routing Record and Markdown templates.

## Storage, Retention & Validation

- Save dated snapshot as `<canonical-dir>/handoff-YYYY-MM-DD-<short-slug>.md`;
  never overwrite an existing dated snapshot without explicit user permission.
- With no repo convention, write `outputs/handoff-YYYY-MM-DD-<short-slug>.md`
  and a short pointer at `outputs/handoff-latest.md`.
- Update an existing pointer only when `pointer_action: update` for the same
  scope (comparing existing scope, lifecycle, work object, and next action first).
- Before finishing, verify: self-reported paths match actual paths; only the
  intended same-scope pointer changed; no retired location or dated snapshot was
  overwritten; `git status` shows only expected files; any `project-context.json`
  route named still exits `0`; and if written from a Git worktree, state that
  worktree path and whether its `project-context.json` route is merged into main.

In your final reply, link the saved snapshot and state its scope, canonical
location, lifecycle, and current-pointer action. Do not paste the full handoff
into chat unless asked.

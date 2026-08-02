---
name: handoff
description: >
  Create a Codex-first continuity handoff for continuing work in a fresh Codex
  session. Use whenever the user wants to continue in a new chat/session,
  preserve context, compact a long thread, avoid losing work, or leave a
  "start here" briefing. Triggers include "handoff," "hand this off,"
  "continue in a new chat," "start a fresh chat," "this chat is getting long,"
  "I'm running low on context," "summarize this so I can pick it up later,"
  and Thai equivalents such as "ส่งต่อ," "สรุปไว้ไปคุยต่อแชทใหม่,"
  "เปิดแชทใหม่," "แชทนี้ยาวแล้ว." Create repository-aware, scope-safe
  handoffs that preserve local storage conventions and current continuation
  routes while capturing conversation-only state, exact workspace paths,
  completed checks, settled decisions, and the immediate next action.
---
<!-- SKILL-VERSION: 2026.07.10 | name: handoff | canonical: ~/.codex/skills/handoff | bump this date on every edit -->
<!-- SKILL-FINGERPRINT: updated_at=2026-07-10T21:40:53+07:00 | updated_by=Codex (GPT-5), at Chutpong's direction | change=repository-aware storage lifecycle and scope-safe routing | basis=HANDOFF-SKILL-UPGRADE-VERDICT-2026-07-10 -->

# Handoff

Create a Codex continuity file: a short mission briefing plus workspace index
that lets a fresh Codex session continue efficiently in the same project.

The handoff is not a generic summary. It is the next session's starting map.

## Core Assumption

A fresh Codex session cannot see the old conversation, but it can often inspect
the same workspace files if the user opens the same project. Use that advantage.

Capture:

- conversation-only state that would otherwise disappear
- exact workspace files the next session should inspect
- decisions already made and why
- checks already run and their results
- the immediate next action
- user preferences that shaped the work

Do not copy whole workspace files into the handoff. Point to them with exact
paths and explain what matters. Only paste content verbatim when it exists only
in chat or when exact wording must survive.

## Scope and Lifecycle

Treat a handoff as a routing object with a stable scope, not as merely the most
recent file by date.

- **Scope kind:** `project`, `work-object`, or `personal`.
- **Scope ID:** a stable identifier for that scope; use `project` for a
  project-wide handoff.
- **Expected resumer:** the role, person, or next session expected to resume;
  it is informative and does not define succession.
- **Lifecycle:** `current`, `transition`, or `historical`.

Only a note with the same `scope kind + scope ID` may replace that scope's
current pointer or cause its current snapshot to be archived. A transition or
status note is not current by default. If scope is unknown, write no current
pointer.

“Lane” is optional vocabulary for a work-object scope. These rules work for a
single person resuming several work objects as well as for a multi-agent team.

## Repository Policy and Fast Preflight

Before writing, run this small, read-only discovery in order:

1. Read an explicit user destination, scope, lifecycle, or promotion request.
2. From the workspace root, read `AGENTS.md` and only instruction files it
   directly names when present.
3. Read a handoff readme/index and existing current pointer(s) when present.

Resolve destination and routing policy in this precedence order:

1. explicit user instruction;
2. current repository instructions/governance;
3. an explicit handoff readme/index and canonical current pointer;
4. configured deliverables folder;
5. the generic `outputs/` fallback.

Use targeted Git history only when paths conflict, a migration/retirement is
suspected, or several candidate pointers exist. Git history is supporting
evidence, not policy. Treat a location as retired only when current explicit
policy or an explicit migration record says so; do not recreate it without user
approval.

Avoid broad repository inventories. If policy names a handoff home, use it. If
no convention exists, use the fallback in **Output and Storage**.

## Routing Record

Before writing, determine and retain this concise record internally:

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

Read an existing pointer before replacing it. Compare its declared scope,
lifecycle, work object, and next action. A project-wide pointer is not replaced
by a work-object handoff unless the user explicitly promotes the new note to
the project-wide continuation entrypoint.

If multiple active scopes exist but the repository has no declared index or
scope-local pointer topology, preserve any different/unknown pointer, write a
dated snapshot in the approved handoff home, set `pointer_action: none`, and
propose a one-time migration. Do not invent new folders, an index, or pointer
topology during an ordinary handoff.

## Output and Storage

Use the repository-approved handoff home, archive policy, and pointer scope
when they exist. Use `outputs/` only when no repository convention exists and
the user has not specified another deliverables location.

For the fallback, create `outputs/` under the current workspace if needed.
Determine a stable handoff date and slug before writing:

- Date: use the current local date in `YYYY-MM-DD` format.
- Slug: create a short, meaningful, lowercase kebab-case English slug from the
  project/task, such as `nu-science-set-bank`, `thai-docx-audit`, or
  `score-system-phone-fill`.
- Do not use generic slugs such as `handoff`, `new-chat`, `project`, `work`, or
  `continue`.
- If the task title is Thai, translate/romanize only enough to make a clear
  filesystem-safe English slug.

Save the durable snapshot as:

```text
<canonical-directory>/handoff-YYYY-MM-DD-<short-slug>.md
```

Never overwrite an existing dated snapshot unless the user explicitly asks. On
collision, add an unambiguous suffix such as `-HHMM` or `-02`.

When `pointer_action: update`, write the policy-approved stable pointer. Unless
local policy requires a full duplicate, make it a short routing note that names
the scope, lifecycle, exact repository-relative snapshot path, and update time.
A fresh session must be able to open the full snapshot with one follow-up open.

For a workspace with no handoff convention, preserve compatibility by writing:

```text
outputs/handoff-YYYY-MM-DD-<short-slug>.md
outputs/handoff-latest.md
```

The fallback `handoff-latest.md` may be a short routing pointer rather than a
copy of the dated snapshot. If repeated handoffs make `outputs/` crowded,
propose—but do not perform—a one-time migration to a dedicated handoff home.

## Retention and Indexes

Follow an existing repository archive/readme/index policy. Where such a policy
exists:

- Keep one active snapshot per scope.
- Archive a dated snapshot only when it is explicitly superseded or closed by a
  handoff in the same scope.
- Never archive another active scope's handoff.
- Preserve transition notes as transition records or archive them under local
  policy; do not promote them merely because they are newer.
- Update one existing index/registry row for the scope with its lifecycle,
  latest snapshot, expected resumer, and updated date.

Do not silently create an index, an `active/<scope>` directory, lane-local
pointers, or a new archival topology. Those are a one-time repository migration
that requires the user's approval. A useful migration may use an index as a
project dispatcher plus one active route and archive stream per scope.

## Handoff Template

Write the durable snapshot in English by default for token efficiency and
cross-session clarity. Preserve work products verbatim in their original
language: Thai, code, math, finalized wording, prompts, problem statements, or
document text.

Use this structure. Drop sections only when genuinely empty.

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

Use this short stable-pointer format when local policy permits it:

```markdown
# Current Codex Handoff

- Scope: `<scope kind>/<scope ID>`
- Lifecycle: `<current | transition | historical>`
- Current snapshot: `<repository-relative path>`
- Updated: `<YYYY-MM-DD HH:MM timezone>`

Open the current snapshot above before continuing.
```

## Fast Context Gathering

Gather only the state that helps the next session move:

- Identify the workspace root/current working directory.
- List relevant created, modified, or delivered files.
- If the workspace is a git repo, inspect current status so changed files are
  not missed.
- Review recent handoff files only when they matter to scope, succession,
  retention, or the next action.
- Use conversation context for decisions, unresolved questions, and work that
  exists only in chat.

## Validate and Report

After writing, verify:

- the snapshot's self-reported paths match actual paths;
- only the intended same-scope pointer changed, if any;
- no pointer was created in a retired location;
- no dated snapshot was overwritten;
- any archive action affected only the same scope;
- an index row changed only when an existing index policy required it; and
- Git status includes only expected handoff files when Git is available.

In the final response, link the saved snapshot and state its scope, canonical
location, lifecycle, and current-pointer action. Do not paste the full handoff
into chat unless the user explicitly asks.

## Writing Rules

- Put the highest-value continuation information at the top. The next session
  should understand the task in 15 seconds.
- Make the filename distinguishable before writing: include both date and a
  meaningful slug.
- Make "Immediate next action" concrete enough that Codex can start without
  asking a broad question.
- Use "Do not redo" to protect the user's time and avoid relitigating settled
  decisions.
- Keep workspace files as pointers, not pasted content.
- Include checks already run, including failures and blockers.
- Keep conversation-only state compact but complete.
- Include user preferences that affect output quality.
- Preserve any Thai or other source-language work product verbatim.

## What Not To Do

- Do not write a vague recap that hides the next action.
- Do not save snapshots as undated `handoff-<slug>.md`.
- Do not overwrite a dated snapshot without explicit user permission.
- Do not replace a pointer just because a note is newer or has a different
  owner/resumer.
- Do not turn a transition/status note into a current project handoff by
  filename or recency.
- Do not recreate a retired handoff location.
- Do not silently reorganize a repository's handoff topology.
- Do not paste entire workspace files into the handoff.
- Do not omit file paths when files matter.
- Do not imply completed checks passed if they were not run.
- Do not make the user re-explain preferences that were already clear in the
  conversation.

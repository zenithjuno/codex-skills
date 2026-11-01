---
name: retro
description: "User-invoked retrospective on a finished work session (/retro). Reads the session record, finds where the agent struggled, and proposes the smallest change to the agent's environment — check, pointer, helper, or deletion — so the next run goes better. Proposes only; edits nothing until the user picks a candidate."
disable-model-invocation: true
---
<!-- SKILL-VERSION: 2026.11.02 | name: retro | canonical: ~/.codex/skills/retro | bump this date on every edit | adapted from mattpocock/skills retro (MIT) -->

# Retro

Improve the **environment** the agent works in, not the work product. The
session's own fixes are done; this asks what in the skills, project files,
or tools let the struggle happen.

## Steps

1. **Pick the session.** Default to the current one. If the user names an
   earlier session, or this one is too long to recall its middle reliably,
   read its log instead: Claude Code `~/.claude/projects/<cwd-slug>/<id>.jsonl`,
   Codex `~/.codex/sessions/YYYY/MM/DD/*.jsonl`. Search the log with `grep`/`jq`
   for errors, retries, and repeated reads; do not load it whole.

2. **List the struggle moments.** Each one cites a concrete moment: a tool call,
   an error, a user correction, a repeated search. A smooth session may have
   none; say so and stop.

3. **Classify each moment** with the cause table in `feedback-to-leverage`
   (section 2), plus these session-only categories:

   | Moment in the session | Candidate fix |
   |---|---|
   | Same expensive call repeated (Word/LibreOffice export, render, full-file read) | helper script, cached output, or narrower command in the owning skill |
   | A skill or project file instruction that changed nothing the agent did | delete it (no-op) |
   | The agent lacked information it needed (log, rendered PDF, teacher preference) | widen access: write the log/render to a known path, add a pointer |
   | A check exists but was not run or is broken | wire or repair it — not a new check |

   Prefer, in order: deletion > existing check wired in > new deterministic
   check > pointer in a file the agent already reads > new prose. Never add a
   line to a global `CLAUDE.md`/`AGENTS.md` or memory when a check or a
   skill-local pointer would do.

4. **Drop** any candidate you cannot trace to a step-2 moment. No generic advice
   to fill a category.

5. **Present** candidates most severe first, then stop and wait:

   ```text
   1. <severity> — <moment, with where it happened>
      Fix: <change> in <file/skill>
   ```

## After the user picks

Apply only the chosen candidates. A change to a skill under `~/.codex/skills` is
a release: follow `skill-release`.

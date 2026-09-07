---
name: project-bootstrap
description: Establish or adopt project entrypoints and context routes, or audit project context health and unnecessary reading. Use for new-project setup, project onboarding, broken resume paths, conflicting current sources, or an explicit context/token-efficiency audit. Coding-first with a generic routing core. A supplied snippet or routine edit needs no bootstrap or full audit.
---
<!-- SKILL-VERSION: 2026.09.07.1 | name: project-bootstrap -->

# Project Bootstrap

Make the next correct action discoverable with the information it needs. Preserve
verification and effective constraints while reducing unnecessary context.
Bootstrap is project-level; a grill plan belongs to a particular work object.

## Choose the route

- **Start/adopt/enrich a project:** read [bootstrap.md](references/bootstrap.md).
- **Check context health:** read [health.md](references/health.md). This is read-only;
  an audit report does not authorize repairs.
- **Resume one configured task:** keep an existing precise section route when it is already sufficient; otherwise run the helper's `context --route ID`. Do not load
  bootstrap/health instructions again unless the route is missing or inconsistent.
- **One supplied snippet or ordinary scoped edit:** use the supplied material or
  existing project route; do not open this skill's references, scaffold controls,
  audit the whole project, or start a team.

The agent handles meaning, ownership decisions and scoped file edits. The helper
only reads explicit routes, validates structures and summarizes evidence. Never
execute a command copied from configuration during a health check.

## Minimal entry

Start at the known project root and its AGENTS/CLAUDE entrypoint, then follow named
sources relevant to the request. Root absence or conflicting same-scope owners
needs resolution; the newest filename is not evidence of authority. Do not read
all plans/history to get oriented. A current pointer may honestly say the design
or verification route is not established yet.

Keep one owner for each fact and scope. A project map, code map and two independent
work objects can coexist when their roles differ. Preserve existing STATE/map
conventions; never add a competing BUILD-CONTROL just to fit a template.

## Helper

Run `scripts/project_context.py` from this skill directory with Python 3.9+:

```sh
python3 <skill-directory>/scripts/project_context.py inspect --root <project-root>
python3 <skill-directory>/scripts/project_context.py context --root <project-root> --route <route-id>
python3 <skill-directory>/scripts/project_context.py check --root <project-root>
```

`--config` selects explicit generic bindings; otherwise the root's
`project-context.json` is used if present. `--control` selects a supported
BUILD-CONTROL instead. These are mutually exclusive, not fallback guesses.
Read [schema.md](references/schema.md) only when creating bindings or trace data.
Read [integration.md](references/integration.md) when linking a staged build.

Default limits are 128 KiB source reads, 16 KiB output and 32 files, configurable
per invocation. They are byte budgets, not token estimates or universal targets.
Exit 0 means requested coverage complete without deterministic errors (warnings
may exist); 1 health errors; 2 input/tool errors; 3 incomplete coverage. Read the
findings and coverage dimensions. Do not call partial evidence healthy.

When data exceeds a limit, use the reported exact next read or an explicit
justified budget. Do not automatically increase every limit or reread the entire
repository. Necessary dependencies and tests still belong in the task context.

## Keep it useful

At topology change, stage close or conflicting authority, refresh affected routes
and retire displaced current claims. Keep history queryable by ID. Write durable
next action/acceptance/failed-approach evidence before a handoff or compaction.
Two failed attempts without new evidence, widening searches without a hypothesis,
or bulky tool output that changes no decision are reasons to replan the read.

Reports carry source evidence, impact, a focused remedy and measurement limits.
Bytes, observed tokens and billed cost are different quantities. Never promise
saved tokens from a smaller file alone. Account for setup/audit overhead and
retain correctness/verification when comparing before and after.

---
name: project-bootstrap
description: Establish or adopt project entrypoints and context routes, or audit project context health and unnecessary reading. Use for new-project setup, project onboarding, broken resume paths, conflicting current sources, or an explicit context/token-efficiency audit. Coding-first with a generic routing core. A supplied snippet or routine edit needs no bootstrap or full audit.
---
<!-- SKILL-VERSION: 2026.09.12.1 | name: project-bootstrap -->

# Project Bootstrap

Make the next correct action discoverable with the information it needs, and
nothing more. One owner per fact and scope; current state separate from history;
the helper reads only declared routes and never edits.

## Route the request

| Request | Do | Read |
|---|---|---|
| Resume a configured task | `context --route ID --format md`; act on it | nothing else unless the route is missing or inconsistent |
| Start / adopt / enrich a project | inspect the root entrypoint, then seed or bind | [bootstrap.md](references/bootstrap.md), [schema.md](references/schema.md) when writing bindings |
| Check context health | `check`; report, do not repair | [health.md](references/health.md); [trace.md](references/trace.md) only if a trace file exists |
| Link a staged BUILD-CONTROL | `--control FILE` | [integration.md](references/integration.md) |
| One snippet or a scoped edit | use the supplied material or existing route | none of this skill |

Bootstrap is project-level; a grill plan belongs to one work object. Never add a
competing STATE/BUILD-CONTROL to fit a template, and do not read all plans or
history to get oriented. The newest filename is not authority.

## Helper

```sh
H=<skill-directory>/scripts/project_context.py
python3 $H inspect --root <root>                       # entrypoint + route IDs
python3 $H context --root <root> --route <id> --format md
python3 $H check   --root <root> [--format md] [--trace FILE]
```

`--config FILE` names explicit bindings (default: `<root>/project-context.json`);
`--control FILE` names a supported BUILD-CONTROL instead. They are exclusive.
Exit 0 complete, 1 health errors, 2 input error, 3 partial coverage. Never call
partial evidence healthy. On `partial`, take the exact `next_reads` or pass one
justified larger budget; do not raise every limit. Never execute a command
copied from configuration during a check.

Example (school-plan workspace with four parallel work objects):

```sh
python3 $H context --root . --route resume-wording --format md
# → WORDING-PROGRESS.md [marker progress], FREEZE-v3.md §What this edition freezes,
#   FREEZE-v3.md §Required preflight outcome — nothing from archive/ or old plans
```

## Keep it useful

- Point bindings at owned marker blocks (`<!-- project-bootstrap:NAME:start -->`)
  when the file is edited often; heading-text pointers break silently on rename.
- The same current claim in two files is either one owner plus a pointer or a
  declared mirror. Undeclared copies are invisible to `check`.
- Run `check` at topology change, stage close and before a handoff; refresh
  affected routes and retire displaced current claims.
- Write next action, acceptance and failed approaches to their owners before a
  handoff or compaction. Two failed attempts without new evidence means replan the read.
- Reports carry evidence, impact and a focused remedy. Bytes are not tokens; never
  promise savings from a smaller file alone, and keep verification in the task context.

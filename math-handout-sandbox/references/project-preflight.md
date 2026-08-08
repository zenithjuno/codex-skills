# Material Project Preflight and Project Map

Run preflight only from Mode B when project root, scope, authority, or routes are
unclear, or when the work has a declared long-project signal. Do not run it for
an isolated Mode A review. Its collector is read-only: it reports filesystem
facts and explicit user declarations, while the agent adjudicates roles and
authority.

## Collector request

Create a temporary JSON request containing at least:

```json
{
  "original_problem": "ข้อความปัญหางานตามที่ผู้ใช้กำลังขอ",
  "input_path": "path/to/current/input",
  "work_kinds": ["material-design"]
}
```

Optional explicit facts include:

- `declared_root`
- `external_inputs`
- `policy_paths`, `design_paths`
- `asset_paths`, `deliverable_paths`, `archive_paths`, `qa_paths` (planned paths may not exist yet)
- `historical_paths`
- `structured_source_paths`, `generator_paths`
- `current_editable_master`
- `multi_session`, `build_assets_pipeline`, `continuation_state`
- `approval_gate_count`
- `current_stage`, `next_action`

Supported `work_kinds` and owners:

| Work kind | Owner / route |
|---|---|
| `material-design` | keep in `math-handout-sandbox` |
| `set-diagram` | keep material/semantic ownership in parent |
| `docx-production` | `thai-math-docx` (core applies the canonical font-normalization route) |
| `exam-production` | `thai-math-exam-production` |
| `answer-correctness` | `blind-answer-key-audit` |
| `continuity-handoff` | `handoff` |
| `generator-maintenance` | coding-only `build-changelog` |

Unknown work kinds block for adjudication; never guess a production owner.

Run:

```bash
python scripts/preflight_material_project.py <request.json> --format json
```

Use `--format short-map` for a compact block to embed in the design note, or
`--format control` for the eight-section long-project control skeleton. The
script prints to stdout and does not alter the project.

## Root and scope

The collector walks upward from the named input to the nearest credible marker,
or uses an explicit declared root. Once declared, discovery remains inside that
root. A path outside it is allowed only when named in `external_inputs`.

Filename, words such as “final/current/latest”, and modification time never
establish authority. They remain factual clues only.

## Short versus long

Use a compact Project Map inside `MATERIAL-DESIGN-<slug>.md` when no long signal
exists. Create `MATERIAL-CONTROL-<slug>.md` when any of these is true:

- multiple deliverables;
- multiple sessions;
- explicitly designated current editable master;
- multiple child skills;
- build/assets pipeline;
- more than one approval gate;
- existing handoff or continuation state.

## Required Project Map fields

Record:

1. Original Problem;
2. declared root and path scope, including named external inputs;
3. policy/convention candidates;
4. dimension-specific authority;
5. design, build, assets, deliverables, archive and QA routes;
6. current stage;
7. next action;
8. required child skills and the announced routing rationale;
9. unresolved conflicts.

Classify relevant artifacts as `disposable-build-output`,
`current-editable-master`, or `external-reference`. Historical documents and
generators are evidence, not compatibility requirements. Only explicit user
designation creates a current editable master.

## Authority order by dimension

| Dimension | Authority |
|---|---|
| Current intent | explicit current user instruction |
| Pedagogy/content | approved design, draft, or Blueprint |
| Current artifact/layout | DOCX/PDF only when explicitly designated current |
| Historical behavior | evidence only |
| New reproducibility | current structured source plus central generator |
| Routing/status | current MATERIAL-CONTROL and current handoff |
| Fallback | installed skill/preference ledger only when project context is silent |

Announce selected child skills and the reason, then continue automatically.
Request approval only at a material/build gate, before mutation of an explicitly
designated current master, when authority must expand, or when real scope changes.

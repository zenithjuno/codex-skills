# Integration with staged work

Grill calls bootstrap during root/role discovery, enriches after its contracts
exist and checks routing at completion. Bootstrap never calls grill recursively,
changes its approvals, or escalates a small task to a large workflow.

New Mode L builds retain the normal map-inside-BUILD-CONTROL convention. Adopted
projects may keep existing map/state owners; staged pointers refer to them rather
than creating another authority. Generic binding validation is not full staged
validation. If control format isn't supported, say so and route manually.

The BUILD-CONTROL adapter uses the companion build-changelog helper's opt-in
bounded validation, and existing pure lifecycle parsing for the declared current
stage. It does not run live Git commands in bounded mode: Git may follow external metadata, global configuration or worktree pointers outside document-read accounting. Version-control coverage is unavailable; run the normal build-changelog validate at the build gate. This structural audit does not waive that gate.

It does not claim full doctor coverage: that routine also scans history
and live filesystem state outside this bounded subset. Old helpers without
bounded validation are explicitly unsupported. See helper output for coverage.

`--control FILE` uses explicit route `resume` for current stage. `inspect` offers
this route. Before a stage exists, read the named contract directly; do not invent
an active stage to satisfy a helper. No automatic searching for multiple controls.

If the helper is absent, manually read the known control entrypoint, current
stage and referenced contract sections only. This is a fallback for orientation,
not evidence that staged checks passed. Do not install dependencies during audit.

Canonical instructions can be shared by Codex/Claude through a thin local bridge.
Explicit entrypoint behavior is tested; automatic harness loading depends on the
installation and must not be claimed universally.

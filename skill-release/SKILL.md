---
name: skill-release
description: Publish any update, addition, repair, rename, or removal of a user-managed Codex/Claude skill from the local `~/.codex/skills` source checkout to its GitHub mirror. Use whenever an agent changes a skill folder or asks to commit, push, install, sync, release, or make a skill available to other sessions. Enforce scoped preflight, verification, commit/push, and clean local-mirror proof through the shared release helper.
---

# Skill Release

Treat every change to a user-managed skill as a release. The local checkout is
the source of truth; GitHub mirrors it. Do not use broad `git add`, a temporary
clone, or manual `git pull`/`push` instead of the helper.

## Required workflow

1. Name the exact top-level skills being released. Keep unrelated edits out of
   the working tree.
2. Before editing, run:

   ```bash
   cd ~/.codex/skills
   python3 tools/skill_release.py preflight --skill <skill-name>
   ```

   Proceed only on `READY`. It fast-forwards a clean local source automatically.
   On `BLOCKED`, stop and report the reason; never overwrite or reset files.
3. Make the scoped change and run the owning skill's relevant tests/validator.
4. Release only after fresh verification:

   ```bash
   python3 tools/skill_release.py release \
     --skill <skill-name> \
     --message "type: concise change"
   ```

   For a separately tested candidate tree, let the helper adopt complete folders:

   ```bash
   python3 tools/skill_release.py release \
     --source-root /path/to/candidate-skills \
     --skill <skill-name> \
     --message "type: concise change"
   ```

5. Call the release complete only when the helper reports `DEPLOYED`. This proves
   a clean local `HEAD` equals `origin/main`. `PUBLISH_PENDING` and `BLOCKED`
   are not completion; preserve evidence and request resolution.

## Scope exceptions

For repository-level release tooling or documentation, enumerate every intended
path explicitly with `--path`; never widen the commit to absorb unrelated work.
Use `python3 tools/skill_release.py sync` only to fast-forward a clean source
without publishing a change.

## Work already committed locally

`release` stages, commits and pushes in one step, and refuses to start unless the
checkout still mirrors origin. So a skill edit that was already committed — for
instance because a project's own commit protocol asked for a checkpoint first —
cannot go out that way. Publish those commits instead of resetting them or
pushing by hand:

```bash
python3 tools/skill_release.py publish
```

It requires a clean tree that is strictly ahead of `origin/main`, pushes, and
then proves the same clean-mirror guarantee. `DEPLOYED` is still the only
completion. Prefer the normal `release` flow: leave skill edits uncommitted and
let the helper own the commit.

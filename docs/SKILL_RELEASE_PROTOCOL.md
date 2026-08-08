# Skill release protocol

`~/.codex/skills` is the live source for both Codex and Claude.  GitHub mirrors
that checkout.  A release is complete only when local `HEAD`, `origin/main`, and
the working tree agree.

Use `tools/skill_release.py`; do not use `git add -A`, a temporary clone, or a
manual `git pull` as a substitute for this protocol.

## Normal release

Before editing a live skill, establish that the source checkout is current and
clean.  `preflight` fast-forwards a clean local source automatically when GitHub
has moved:

```bash
python3 tools/skill_release.py preflight --skill thai-math-docx
```

After testing the changed skill, publish its local changes with an exact scope:

```bash
python3 tools/skill_release.py release \
  --skill thai-math-docx \
  --message "feat: improve Thai math DOCX QA"
```

The command fetches first, rejects changes outside the declared scope, commits,
pushes, fetches again, and fast-forwards local source if GitHub advanced during
the push.  Success is only `{"status": "DEPLOYED", ...}`.  To synchronize a
clean source without releasing a change, use `python3 tools/skill_release.py sync`.

## Adopt a tested staged skill

When a separate build has a complete candidate folder, keep live source clean
until the release command adopts the named folders atomically:

```bash
python3 tools/skill_release.py release \
  --source-root /path/to/staging/skills \
  --skill math-handout-sandbox \
  --skill thai-math-docx \
  --message "feat: update Thai math document skills"
```

The helper copies only the named complete skill folders, proves their hashes,
rolls them back if a pre-commit operation fails, then commits and mirrors them.
If GitHub rejects the push after the local commit, it reports `PUBLISH_PENDING`:
do not overwrite, reset, or pull manually.  Resolve that release deliberately.

## Required interpretation

- `READY`: local source is clean and equals GitHub; editing may begin.
- `SYNCED`: a clean local source was fast-forwarded and now equals GitHub.
- `DEPLOYED`: the local source is clean and exactly mirrors GitHub.
- `PUBLISH_PENDING`: a local release commit exists but GitHub was not confirmed.
- `BLOCKED`: nothing was released; read the exact reason first.

For an agent adding repository-level release tooling rather than a skill folder,
use explicit `--path` values.  Never release unrelated paths merely because they
happen to be modified.

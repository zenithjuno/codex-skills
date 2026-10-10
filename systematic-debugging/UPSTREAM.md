---
repo: https://github.com/obra/superpowers
path: skills/systematic-debugging
commit: bb92a77741419a4ab5f06e711a283343f1ada0c3
---

# Upstream: systematic-debugging

This skill is borrowed. Update it with `python3 tools/upstream_sync.py check systematic-debugging` and `merge systematic-debugging`, never by re-copying.

Adapted 2026-08-02 (MIT). Trimmed and re-pointed at this user's tooling (Apps Script `src/Tests.gs`, game-content-audit, ship-check, playwright).
- Removed: CREATION-LOG.md, test-*.md pressure evals, condition-based-waiting-example.ts, find-polluter.sh.
- Added (local only): agents/openai.yaml, SKILL-VERSION stamp.
- Pin chosen 2026-10-10 as the upstream commit whose files are closest to our copy (identical content from 2026-07-05 to 2026-07-24).
- 2026-10-10: upstream bb92a77 changed only the env-var shell example (SKILL.md) and `./find-polluter.sh` → `bash ./find-polluter.sh` (root-cause-tracing.md). Both spots were already replaced here by Apps Script examples, so we kept ours and moved the pin without changing files.

---
repo: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
path: .claude/skills/ui-ux-pro-max
commit: 01706130e32f2af1d12923cce8d64a85fd76a3cd
---

# Upstream: ui-ux-pro-max

This skill is borrowed. Update it with `python3 tools/upstream_sync.py check ui-ux-pro-max` and `merge ui-ux-pro-max`, never by re-copying.

Taken from `nextlevelbuilder/ui-ux-pro-max-skill` (MIT; `LICENSE.txt` copied from repo root) at the pinned commit (checked 2026-11-26).
- Local changes:
  - Added `SKILL-VERSION` stamp.
  - Tuned `description` (≤ 420 chars) with Thai + English triggers and explicit scope boundaries: design-system/domain/stack reference DB paired with `frontend-design`, excluding post-build UI/a11y audits (`web-design-guidelines`).
  - Updated `When to Apply` to mirror the same non-overlapping boundaries.
  - Replaced `${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py` with `~/.codex/skills/ui-ux-pro-max/scripts/search.py` (using `python3`) so it runs cleanly across Codex, Claude Code, and Gemini/Antigravity.

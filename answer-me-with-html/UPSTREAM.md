---
repo: https://github.com/QingYunA/answer-me-with-html
path: skills/answer-me-with-html
commit: c0a2e3e7dc5d2b51ac71dfd33eddfa4a26c68669
take_theirs: scripts/am.mjs
---

# Upstream: answer-me-with-html

This skill is borrowed. Update it with `python3 tools/upstream_sync.py check answer-me-with-html` and `merge answer-me-with-html`, never by re-copying.

Installed 2026-10-10 (MIT) as a vendored skill, not the Claude Code plugin, so Codex and Claude share one customised copy.
- scripts/am.mjs is a generated bundle: never edit it here; take_theirs replaces it on every merge.
- Local changes, keep them small so merges stay clean:
  - SKILL.md: SKILL-VERSION stamp; one line in section 0 routing `update` to this tool; one line in section 2 pointing Thai drafts to references/thai-budget.md; selective visual scope and Markdown-default delivery (2026-10-12).
  - references/thai-budget.md and agents/openai.yaml (local only): Thai/budget/math guidance; Codex display metadata.
- Ideas that need CLI changes (Thai page labels, Thai filenames, a math component) are NOT patched here; they belong upstream.

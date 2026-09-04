
---

## PRG-S11 — cleanup (post-approval, off-repo)
- Date: 2026-09-04 (user confirmed 'ลบเลย')
- Removed PSK clone fonts: ~/Library/Fonts/THSarabunPSK*.ttf (4) + LibreOffice-dir THSarabunPSK*.ttf (4) + redundant LibreOffice-dir THSarabunNew*.ttf (4). User's real ~/Library/Fonts/THSarabunNew (Jun 2011) untouched — one Sarabun copy remains.
- Removed superseded workspace tools: ~/Documents/Claude Code workspace/tools/{render_thai_docx,make_sarabun_psk}.py.
- Verified after removal: fresh-profile LibreOffice render embeds THSarabunNew(+Bold), NO Tahoma substitution → native LO reads the real ~/Library/Fonts; the bundle copies were redundant. No regression.
- Updated memory [[thai-docx-render-pipeline]] to the normalize→New strategy (retired the PSK-clone note); [[docx-visual-truth-is-word]] recorded earlier.
- Awaiting gate: `Pass S11` → completion protocol.

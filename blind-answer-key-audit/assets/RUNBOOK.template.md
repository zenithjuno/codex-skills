# RUNBOOK — starting a blind answer-key audit (paste-to-AI guide)

> Read this, then point your AI agent (Claude / Codex / etc.) at the data. The AI is the *solver*;
> `audit.py` just enforces blindness + records + watches drift.

## 0. Layout
Keep the checker workspace separate from the producer's data:
```
<DATA_ROOT>/                       ← producer's questions_*.json + solutions_*.json (searched recursively)
  └─ <checker-workspace>/
       ├─ audit.py · STATE.md · RUNBOOK.md
       └─ audit/   (manifest.jsonl · solutions/ · schema_snapshot.json · audit_results.xlsx)
```
Point the tool at the data: `export AUDIT_ROOT="<DATA_ROOT>"` (or place the workspace inside DATA_ROOT for auto-detect).

## 1. First session (setup) — paste to the AI:
```
อ่าน STATE.md ก่อน แล้วรัน `python3 audit.py sets` และ `python3 audit.py scan`
รายงานว่ามีชุดอะไรบ้าง / scan เจออะไรน่าระวัง (kind แปลก, เฉลยถูกแก้, ไฟล์ใหม่) — อย่าเพิ่งเริ่มตรวจ
```

## 2. Audit loop — paste to the AI (repeat per batch):
```
รัน `python3 audit.py scan` ก่อน (เช็ค drift). แล้วเลือกชุดด้วย `use`, เริ่มจาก `next`
ทำ 3 ข้อ โดยแต่ละข้อ:
1) python3 audit.py question <n>  → แก้เอง เขียนคำตอบ+วิธี+confidence ลง audit/solutions/ ก่อน
2) python3 audit.py answer <n>    → เทียบ จัด bucket (pass / flag-*)
3) python3 audit.py record '<json>'  ทันที
ห้ามดู answer ก่อนเขียน solution ของตัวเอง. จบ batch รัน `python3 audit.py export`
สรุปให้ฟังว่าข้อไหน pass ข้อไหน flag เพราะอะไร
```

## 3. Resume (new session / next day) — paste:
```
อ่าน STATE.md แล้วรัน `python3 audit.py scan` (เผื่อ producer แก้อะไร) แล้วทำต่อจาก `next` อีก 3 ข้อ
```

## 4. Finish → human review
- `python3 audit.py progress` → flag list · `export` → audit_results.xlsx
- Human adjudicates flags (start with `flag-mismatch`) + spot-reads ~10–15% of passes.
- Feed decisions back, re-`export`.

## 4.5 Apply audit status back to bank JSON
After the producer/human accepts the audit batch, run:
```
python3 scripts/apply_audit_to_bank.py \
  --bank <questions_bank.json> \
  --manifest audit/manifest.jsonl \
  --out <questions_bank.with-audit.json> \
  --auditor <checker-agent-name>
```
Use `--in-place` only when intentionally updating the canonical bank; it creates `.bak` by default.

## 5. Gotchas
- `record` payload with `{` `(` unicode → write via Python (see references/adapting-to-your-data.md).
- `scan` says "ยังไม่มี handler" → add a renderer handler before auditing that file (don't audit through `⟦?⟧`).
- `scan` says "เฉลยถูกแก้ N ข้อ" → producer changed those keys; re-audit them (did they fix the root cause?).

# เขียนโปรไฟล์เล่ม (PROFILE.json)

กฎทั่วไปทำทุกเล่มเสมอ (R1 · P1 · P2 · B1 ย่อหน้าว่างหลังตัวแบ่งส่วน · T1). ที่เหลือผูกกับข้อความในเล่ม
จึงอยู่ในโปรไฟล์ — **ไม่มีคีย์ = ไม่ทำกฎนั้น**. ตัวอย่างจริงครบทุกคีย์: `profiles/pp-2570.json`.

เริ่มเล่มใหม่: คัดลอก `pp-2570.json` → ลบคีย์ที่ไม่เกี่ยว → แก้คำค้นให้ตรงเล่มใหม่ → รัน `layout_pass.py --report`
แล้วดูจำนวนต่อกฎ (กฎที่ได้ 0 แปลว่าคำค้นไม่ตรง หรือเล่มนั้นไม่มีปัญหานั้น — ต้องรู้ว่าเป็นแบบไหน).
regex ทั้งหมดใช้กับข้อความย่อหน้าที่ strip แล้ว · `re.match` = ตรงต้นข้อความ.

| คีย์ | กฎ | รูปแบบ |
|---|---|---|
| `replace_text` | X แก้ข้อความที่ครูสั่ง (ระดับ w:t) | `[{"contains": "ผิด", "to": "ถูก"}, {"exact": "...", "to": "..."}]` |
| `merge_tables` | M1 รวมตารางที่หั่นตามหน้า PDF | `[{"anchor_prefix": ข้อความย่อหน้าก่อนตาราง, "spill_exclude_regex": แถวแรกท่อนถัดไปที่ *ไม่ใช่* แถวเศษ, "head_rows": 1-2}]` |
| `headings` | P2 หัวเรื่อง 20 pt | ค่าเริ่มต้น `["คำนำ","บทสรุปผู้บริหาร","สารบัญ"]` |
| `part_heading_regex` | P2 หัวส่วน (+ชื่อส่วนถัดไป 18 pt) | ค่าเริ่มต้น `"ส่วนที่ \\d"` |
| `preface_closing` | P3 ลงท้ายคำนำครึ่งขวา | `{"heading","lines":[…],"date_regex","left_cm"}` |
| `prose_skip_prefixes` | P1 ย่อหน้าที่ห้ามย่อ | รายการคำขึ้นต้น |
| `facility_list` | P4 รายการ จำนวน/หน่วย | `{"units":["ห้อง","เครื่อง"],"tabs_cm":[7.0,9.4,9.8]}` |
| `unbreak_prefixes` | B1 ย่อหน้าที่ต้องตัด "ขึ้นหน้าใหม่" | คำขึ้นต้น — หาจาก contact sheet หน้าที่ว่างครึ่งหน้า |
| `signature_block` | บล็อกลงชื่อไม่แยกหน้า | `{"start_prefixes","seen_text","end_text"}` |
| `copy_logo` | B2 สำเนาย่อหน้าภาพ (โลโก้+ขึ้นหน้า) จากหน้าต้นแบบไปหน้าเป้าหมาย | `{"source_heading_regex","target_heading_regex"}` |
| `strategy_tables` | K1 คอลัมน์ 2 แยกข้อ หนาเฉพาะหัวข้อ · คอลัมน์ 1 ป้ายหนา | `{"table_prefix","contains","item_regex","split_word":[regex,แทน],"label_regex"}` |
| `page_break_before` | B3 ขึ้นหน้าใหม่ | คำขึ้นต้น |
| `keep_blocks` | B3 ตั้งแต่ start ถึง end อยู่หน้าเดียวกัน | `[{"start_regex","end_regex","page_break":true}]` |
| `fixed_width_tables` | T2 ความกว้างคอลัมน์ตายตัว | `{"caption_regex","widths_cm":[…ต้องเท่าจำนวน gridCol…],"header_until_prefix","header_pt","small_cells"}` |
| `quality_column` | 2 คอลัมน์ท้ายกึ่งกลาง | `{"row2_text": ข้อความแถว 2 ตัดช่องว่าง}` |
| `center_columns` | T3 คอลัมน์ตามดัชนีกึ่งกลาง | `[{"caption_prefix","skip_rows","min_cells","cols":[0,1,…]}]` |
| `autofit_captions` | T4 พอดีเนื้อหา+กึ่งกลางหน้า | คำขึ้นต้นของย่อหน้าก่อนตาราง (ตารางต้องอยู่ใน 3 element ถัดไป) |
| `toc` | สารบัญ | ดูด้านล่าง |
| `check` | check_book | `{"forbidden_regex","min_table_pt":12,"unnumbered_front_pages":N}` |

## toc

```json
"toc": {
  "start_prefix": "- คำนำ",
  "label": "first",
  "rules": [
    {"title_regex": "^โครงการที่(\\d)$", "where": "full", "pattern": "โครงการ/งาน\\1\\.", "min_page_index": 60},
    {"title_regex": "^(ส่วนที่\\d)", "where": "top", "top_lines": 2, "pattern": "^\\1$"}
  ]
}
```

- ชื่อหัวข้อและข้อความในหน้าถูกตัดช่องว่างและรวมสระอำก่อนเทียบ — เขียน regex แบบไม่มีช่องว่าง
- ค่าเริ่มต้น (ไม่เข้า rule ไหน): บรรทัด 2–4 ของหน้าขึ้นต้นด้วยชื่อหัวข้อ
- rule แรกที่ `title_regex` ตรงเป็นตัวตัดสิน · `pattern` อ้างกลุ่มจาก title_regex ได้ (`\1`) · `where: top` ดู `top_lines` บรรทัดแรกหลังเลขหน้า · `full` ดูทั้งหน้า · `min_page_index` ข้ามหน้าต้นเล่ม (เช่น ชื่อโครงการที่โผล่ในตารางสรุป)
- ใช้ rule เมื่อ: หัวข้อซ้ำกับข้อความในสารบัญ/ตาราง (ตรงผิดหน้า) หรือชื่อในสารบัญไม่ตรงหัวในหน้า
- `label: "last"` ถ้าเลขหน้าอยู่ท้ายกระดาษ

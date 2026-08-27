# Content Components — the reusable blocks inside `Approved content`

The design-note sections above `Approved content` are about the material — the
teacher reads them to judge intent. **This is the other layer:** the blocks that
are the material, the things printed on the sheet. A handout is assembled from a
few of these, in order.

This catalog is **closed**: the block types below are the known vocabulary, each
with one canonical shape, so the same idea does not get three different headings
across notes (in real notes `บทนิยาม` was written `####` and `#####`; `ข้อสังเกต`
was a heading in some and `**bold**` in others; `คำสั่ง` sometimes had `>` and
sometimes not). Normalizing them is the whole point.

**Not every note uses every block.** Pull only the ones the sheet needs. A pure
exercise sheet is often just `คำสั่ง` + `ตัวอย่าง/โจทย์`; a concept sheet may open
with `คำเกริ่น`, state a `บทนิยาม` and a `ทฤษฎีบท`, then examples. Leave the rest
out — do not write an empty heading.

Conventions used below:
- **Default voice: student-friendly กึ่งทางการ** — เขียนให้ผู้เรียนอ่านเข้าใจ
  แต่ยังคงศัพท์คณิตที่ถูกต้อง ไม่กันเอง ไม่แข็งแบบตำรา ครูปรับสำนวนหน้างานได้เสมอ
  นี่เป็นแค่ค่าตั้งต้น
- Each block is a `###` heading under `## Approved content`; `ตัวอย่าง/โจทย์`
  items nest one level deeper as `#### ตัวอย่างที่ N`.
- Block headings are Thai — they are content the reader sees, not note structure.
- Math is Unicode inside inline code (`x²`, `−13⁄5`, `{x ∈ ℕ ∣ x < 5}`), never
  LaTeX — same rule as the rest of the note.

---

## Catalog

### คำเกริ่น — opens the topic
One short paragraph of context before the content proper. Use when the sheet
starts a new idea; skip on a plain practice sheet.
```markdown
### คำเกริ่น
การแก้อสมการพหุนามดีกรี `3` ขึ้นไป ยังใช้แนวคิดเดียวกับดีกรี `2` คือ…
```

### คำอธิบาย — prose that carries a step of reasoning
Explanation placed before or after an example, theorem, or definition. Replaces
the old ad-hoc headings (`คำอธิบายก่อนตัวอย่างแรก`, `คำอธิบายหลังทฤษฎีบท`) with one
name; say where it sits in the first line if it matters.
```markdown
### คำอธิบาย
ก่อนเข้าตัวอย่างแรก: จำนวนที่ทำให้พหุนามเป็นศูนย์เรียกว่า “ค่าวิกฤต” เพราะ…
```

### บทนิยาม — a definition
```markdown
### บทนิยาม
**<พจน์>:** <ข้อความนิยาม>
ตัวอย่างสั้น: <ถ้าช่วยให้เห็นภาพ>
```

### ทฤษฎีบท — a theorem or a property you rely on
Both a theorem and a property (`สมบัติ`) use this block — they do the same job in
the sheet (a statement the learner leans on). Say which in the first line.
```markdown
### ทฤษฎีบท
**ทฤษฎีบท:** <ข้อความ>          <!-- หรือ **สมบัติ:** สำหรับสมบัติ -->
เงื่อนไขที่มักลืม: <จุดที่ผู้เรียนพลาดบ่อย>
```

### หมายเหตุ — a short aside or caution
The observation family (`ข้อสังเกต`, `หมายเหตุ`) — a remark next to the content,
not a statement the sheet is built on. Keep it to a line or two.
```markdown
### หมายเหตุ
`c` ต้องเป็นจำนวนลบเท่านั้น เครื่องหมายจึงกลับ — ถ้า `c > 0` อสมการไม่เปลี่ยนทิศ
```

### อัลกอริทึม — an ordered procedure
Numbered steps the learner follows in order.
```markdown
### อัลกอริทึม
1. ย้ายทุกพจน์ไปข้างเดียวให้เหลือ `0` อีกข้าง
2. แยกตัวประกอบ
3. หาค่าวิกฤตแล้วทดสอบเครื่องหมายแต่ละช่วง
```

### คำสั่ง — the instruction to the learner
Plain text, **no blockquote** (`4:2` in real notes favour plain).
```markdown
### คำสั่ง
จงแก้อสมการต่อไปนี้ และเขียนเซตคำตอบในรูปช่วง
```

### ตัวอย่าง / โจทย์ — the worked examples or problems
Each item is its own `####`. For an `examples` sheet with `Scaffolding: mixed`,
label each item `Support: worked | faded | independent`.
```markdown
#### ตัวอย่างที่ 1
แก้ `2x < 8`
<!-- Support: worked -->
```

### เฉลยและแนวคิด — full answer and the idea behind it
Complete solutions live here in every mode (including `worksheet` and faded
examples); what reaches the DOCX depends on `Deliverable`/`Scaffolding`.
```markdown
### เฉลยและแนวคิด
ตัวอย่างที่ 1 มีค่าต่ำสุดเท่ากับ `3` จึงเป็นบวกทุกจำนวนจริง เซตคำตอบเป็น `ℝ`…
```

---

## `[custom]` — the escape hatch

The catalog is closed, but a genuinely new block that recurs is worth adding. For
a one-off, use a `### <ชื่อ>` heading and leave a comment saying why it did not
fit an existing block — that comment is the signal to promote it into the catalog
later if it shows up again.
```markdown
### ตารางสรุปเครื่องหมาย
<!-- custom: ยังไม่มีบล็อกสำหรับตารางเครื่องหมายรายช่วง; ถ้าใช้ซ้ำ ค่อยเพิ่มเข้า catalog -->
```

Do not reach for `[custom]` to avoid a block that already fits. It is for a shape
the catalog genuinely lacks, not a second spelling of one it has.

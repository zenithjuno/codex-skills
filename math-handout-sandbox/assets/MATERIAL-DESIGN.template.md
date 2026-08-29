# Material Design — <ชื่อหัวข้อภาษาไทย>

> Headings stay English so they stay searchable. Everything you write under them
> is Thai, because the teacher reads this to judge and argue with it. Only the
> `Contract` values are English — those are read by tooling.
>
> Which sections a note needs is set by `references/design-note-sections.md`:
> the Spine below is always present; the rest is kept or deleted by its trigger.

## Contract

- Slug: `<slug>`
- Deliverable: `worksheet` | `answer-key` | `examples` | `design-only`
- Scaffolding: `worked` | `faded` | `independent` | `mixed`
- Status: `drafting` | `approved` | `built`
- Generator: `build_<slug>.py`
- Output: `<ชื่อไฟล์>.docx`
- History: `DESIGN-LOG-<slug>.md`

Delete the lines that do not apply rather than writing `—`. Require
`Scaffolding` only when `Deliverable: examples`. `Deliverable` states the
document's role; `Scaffolding` states the support learners see. `worksheet`
prints prompts only, `answer-key` prints complete solutions, `examples` follows
its scaffolding contract, and `design-only` produces no DOCX.

## Source observations

วิเคราะห์ของเดิม — หนังสือเรียน แบบฝึกหัดเก่า หรือข้อสอบที่ครูส่งมา — **ก่อน**
ตัดสินใจ progression **มีต้นฉบับเมื่อไหร่ หัวข้อนี้บังคับ** วิเคราะห์จริงห้ามผ่านเฉย
เพราะหน้าที่ของมันคือกันไม่ให้เออออไปกับของเดิมโดยไม่คิด **หัวข้อนี้สังเกตล้วน** —
ข้อเสนอว่าจะย้าย/ตัด/แทรกอะไร ไปเขียนที่ `Recommended revision`

| ข้อเดิม | ข้อดี | ข้อเสีย/ความเสี่ยง |
|---|---|---|

`ข้อเสีย/ความเสี่ยง` เขียนสิ่งที่มันฝึก**จริง** ไม่ใช่สิ่งที่อ้างว่าฝึก — โจทย์หลายข้อ
ฝึกอย่างหนึ่งแต่หน้าตาเหมือนอีกอย่าง

**ห้ามเสกปัญหาเพื่อดูขยัน** — ข้อที่ดีอยู่แล้วบอกว่าดี ชี้จุดอ่อนเฉพาะที่เจอจริง
แต่ถ้าอ่านทั้งชุดแล้วไม่เจออะไรเลย บอกด้วยว่าทำไมมันดี อย่าผ่านแบบ "ดีหมด" ลอย ๆ
รายข้อเต็มทำเมื่อ**ยกเครื่องหนัก** — ยาวได้ คุ้ม ปรับเบาเขียนเฉพาะข้อที่มีประเด็น

### Diagnosis

จุดอ่อน **เชิงระบบ** ของทั้งชุด (ไม่ใช่รายข้อ) — รูปแบบความพลาดที่ต้องแก้ เช่น
"ข้อ 3–8 กระโดด edge case เร็วไป เด็กเลยจำเป็นจับผิดวงเล็บ" เขียนเป็นย่อหน้าเดียว
หรือแยก `สิ่งที่ดี / สิ่งที่ยังไม่ดี` ก็ได้ ถ้าต้นฉบับดีจริงเขียนว่าดีตรงไหนเหลือปรับอะไร
`Recommended revision` ต้องตอบ Diagnosis นี้

ไม่มีต้นฉบับให้วิเคราะห์ = ลบทั้ง `Source observations` (รวม `Diagnosis`) ทิ้ง

## Learning objective

ทำครบชุดแล้วผู้เรียนควรทำอะไรได้ และแนวคิดแกนกลางของชุดนี้คืออะไร —
เขียนแกนกลางเป็นประโยคเดียวที่ครูพูดออกเสียงในคาบได้จริง

## Progression map

ลำดับของชุด และหน้าที่ของแต่ละข้อในลำดับนั้น เขียนก่อนร่างโจทย์จริง

| # | Item | Answer (teacher) | Job of this item |
|---|---|---|---|

`Job of this item` คือหัวใจ: ข้อนี้ปูอะไร ขัดกับข้อก่อนหน้าตรงไหน
หรือบังคับให้ผู้เรียนตัดสินใจอะไร

ตามด้วยย่อหน้าสั้น ๆ ว่า **ทำไมเรียงแบบนี้ · ความซับซ้อนเพิ่มขึ้นตรงไหน ·
ข้อไหนเป็นคู่ที่ตั้งใจให้เปรียบเทียบกัน**

### ตรวจก่อนเสนอ — ตรวจกับชุดจริง ไม่ใช่กับแผน

แผนที่ดีกับโจทย์ที่ดีเป็นคนละเรื่อง ชุดที่ผ่านแผนแล้วยังพังได้ด้วยสี่อาการนี้

- ทุกข้อบังคับให้ตัดสินใจอะไรบางอย่างที่พลาดได้จริงไหม — ไม่ใช่ทำตามสูตรได้เลย
- มีข้อไหนเป็นข้อก่อนหน้าที่เปลี่ยนแค่ตัวเลขไหม
- ชนิดของงานเปลี่ยนกี่ครั้งตลอดชุด ไม่ใช่แค่ตัวเลขโตขึ้น
- ข้อที่ยากที่สุดยังอยู่ในเป้าหมายของบทไหม หรือความยากไปโผล่ที่ทักษะอื่น

## Anticipated errors

คลังความเข้าใจผิดของเรื่องนี้ — ไม่ใช่ทุกข้อต้องถูกจี้ในชุดนี้ บางอันรอไปลง
ชุดถัดไปได้ ประโยชน์ของคลังคือเห็นภาพรวมแล้วเลือกจังหวะแทรกได้ดี

| ความเข้าใจผิด | จี้ไว้ที่ | สถานะ |
|---|---|---|

`จี้ไว้ที่` เขียนได้ว่า `ตัวอย่างที่ 2` · `ข้อ 4` · หรือ `ยังไม่ได้วาง` —
ค่าสุดท้ายมีความหมาย มันคือรายการรอสำหรับชุดหน้า

`สถานะ` เปลี่ยนคลังนี้เป็น **coverage audit**: `ครอบคลุมดี` · `ช่องว่างสำคัญ` ·
`เป็นประเด็นใหม่ ควรเน้น` — บอกทันทีว่าอะไรยังขาดและควรอุดที่ `Recommended revision`

## Link to the teaching examples

แบบฝึกหัดเป็นลูกของชุดตัวอย่างในเชิงประเด็นและ misconception ตารางนี้บอกว่า
รับอะไรมาบ้าง และฝึกซ้ำที่ข้อไหน

| ประเด็นที่สอนไว้ | สอนไว้ที่ | ฝึกที่ข้อ |
|---|---|---|

- ประเด็นที่ไม่มีเลขข้อ = สอนแล้วไม่ได้ฝึก
- ข้อที่ไม่ปรากฏในคอลัมน์ขวา = ผู้เรียนย้อนกลับไปหาที่มาไม่ได้ ต้องเพิ่มตัวอย่าง
  หรือตัดข้อนั้นทิ้ง

`สอนไว้ที่` เขียนเป็นอะไรก็ได้ที่ชี้ที่มาได้จริง — `ตัวอย่างที่ 3` ·
หัวข้อในหนังสือ · หรือชื่อโน้ตอื่น

**ไม่มีชุดตัวอย่าง ก็ลบหัวข้อนี้ทิ้ง** แบบฝึกหัดที่ตั้งใจ craft ขึ้นมาลอย ๆ
ไม่ต้อง link ไปไหน ให้สังเคราะห์ประเด็นเองใน `Progression map` และ
`Anticipated errors` แทน

เมื่อแก้ชุดตัวอย่างหรือชุดฝึก กลับมาแก้ตารางนี้ในเทิร์นเดียวกัน ไม่มีเครื่องมือ
ไหนตรวจให้ได้ว่าประเด็นยังตรงกันอยู่

## Recommended revision

**ข้อเสนอ**ที่ตอบ `Diagnosis` — ประมวลจาก Source observations, Progression และ
Anticipated errors มาเป็นลำดับที่ปรับ พร้อมข้อที่แทรก/ตัด/สลับและเหตุผล **เกือบ Spine
เมื่อ adapt** ต้นฉบับที่มีจุดอ่อน (ต้นฉบับดีจริงก็เขียนสั้น ๆ ว่า "เก็บทั้งหมด" + การสลับ
เล็กน้อยถ้ามี) หัวข้อนี้รับข้อ**ใหม่**ที่ไม่มีในต้นฉบับได้ — ต่างจาก `Source observations`
ที่ผูกกับข้อเดิม การสังเกตดิบไม่เขียนที่นี่ เขียนที่ `Source observations`

| ลำดับเสนอ | โจทย์ | หน้าที่ | คำตอบ |
|---|---|---|---|

ตามด้วยเหตุผลว่าลำดับนี้ครอบคลุมสิ่งที่ต้นฉบับขาด และ**ทางเลือก**ถ้ามี (เช่น เก็บทุกข้อ
แล้วชุดยาวขึ้น) ให้ครูเห็นทั้งสองทาง

### Decision needed

สรุปทางเลือกให้ครูเลือกแบบเป็นกลาง (เช่น "คง 5 ข้อตามที่เสนอ" vs "เก็บเดิม + ขยายเป็น
7 ข้อ") ก่อนเปลี่ยน `Status` เป็น approved — ไม่ต้องชี้นำว่าควรเลือกอะไร นั่นคือหน้าที่
ของข้อเสนอด้านบนแล้ว

## Approved content

ข้อความที่นักเรียนจะอ่านเขียนที่นี่ตรงตามที่จะพิมพ์จริง คณิตศาสตร์เป็น Unicode
ใน inline code (`x²`, `−13⁄5`, `{x ∈ ℕ ∣ x < 5}`) ไม่ใช้ LaTeX

ประกอบจากบล็อกใน `references/content-components.md` เรียงเท่าที่ชีทนี้ใช้ —
ปกติไม่ครบทุกบล็อก คำสั่ง/โจทย์/เฉลยด้านล่างเป็นโครงที่พบบ่อย ส่วนคำเกริ่น บทนิยาม
ทฤษฎีบท ฯลฯ หยิบจาก catalog มาใส่เมื่อเนื้อหาต้องการ ลบหัวข้อที่ไม่ใช้ทิ้ง

### คำสั่ง

### โจทย์ / ตัวอย่าง

For `examples + mixed`, label every item with one of:

- `Support: worked` — print the complete method.
- `Support: faded` — print selected steps and leave named target steps blank.
- `Support: independent` — print the prompt only.

For a single-level examples document, the contract-level `Scaffolding` applies to
every item, so do not repeat it item by item.

### เฉลยและแนวคิด

เฉลยเต็มอยู่ที่นี่ทุกโหมด รวมทั้ง `worksheet` และตัวอย่างแบบ faded
สิ่งที่ไปถึง DOCX ขึ้นกับ `Deliverable` และ `Scaffolding`

## Rejected alternative

สิ่งที่พิจารณาแล้วไม่เอา พร้อมเหตุผล — ไม่ต้องเขียนทุกไอเดียที่ถูกทิ้ง เขียน
เฉพาะอันที่คนอ่านทีหลังน่าจะเสนอซ้ำ เพื่อให้เขาเจอเหตุผลก่อนเสนอ

---

> ตั้งแต่บรรทัดนี้ลงไปเป็นส่วนสำหรับคนผลิตและสำหรับเก็บประวัติ ไม่ใช่ส่วนที่ครู
> ต้องอ่านเพื่ออนุมัติ เขียนให้พอใช้งาน ไม่ต้องขัดเกลา

## Layout notes

เฉพาะสิ่งที่ต่างจาก `DOCX-PREFERENCES.md` ของหัวข้อนั้น ถ้าไม่ต่างเลย ลบทิ้ง —
อย่าเขียนซ้ำโปรไฟล์ที่ใช้ร่วมกัน

## Artifact plan

Opt-in — โน้ตส่วนใหญ่ไม่มีหัวข้อนี้ เพราะเรื่อง artifact มักตัดสินหน้างานระหว่างทาง
ไม่ได้วางล่วงหน้า ใส่เฉพาะเมื่อการแบ่งหน้ามีผลต่อการสอน หรือมี acceptance check
ที่ต้องระบุ นอกนั้นลบทั้งหัวข้อทิ้ง

- **Page plan** — เขียนเมื่อการแบ่งหน้ามีผลต่อการสอนเท่านั้น
- **Acceptance checks** — ข้อความที่ตรวจได้บนไฟล์ที่ build เสร็จ เช่น ข้อไหน
  ต้องคงเดิม อะไรต้องไม่โผล่ อะไรต้องมาก่อนอะไร เกต QA ตรวจกลไกได้ แต่ไม่รู้
  เรื่องพวกนี้เลย

## Open questions

อะไรที่ยังรอครูตอบ ว่างเมื่อไหร่ลบทิ้ง

## Decisions

| Date | Decision | Why |
|---|---|---|

เฉพาะการตัดสินใจที่ครูรับแล้วและย้อนกลับแล้วเสียแรง — การคุยหนึ่งรอบไม่ใช่
การตัดสินใจ

---

**Keep this note current, not cumulative.** Replace superseded wording, examples
and decisions in place. When the reasoning behind a replaced choice is worth
keeping, move it to `DESIGN-LOG-<slug>.md` and leave one pointer line here.
Never keep both versions.

Length is not the enemy — a transcript is. Analysis that explains why the
sequence works earns its space; a record of every turn of the conversation does
not, and one note in this project reached 48,000 characters that way.

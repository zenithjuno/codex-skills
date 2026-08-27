# Material Design — <ชื่อหัวข้อภาษาไทย>

> Headings stay English so they stay searchable. Everything you write under them
> is Thai, because the teacher reads this to judge and argue with it. Only the
> `Contract` values are English — those are read by tooling.

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

สิ่งที่ของเดิมทำจริง — หนังสือเรียน แบบฝึกหัดเก่า หรือข้อสอบที่ครูส่งมา
เขียนเป็นหลักฐาน ไม่ใช่ความเห็น และเฉพาะส่วนที่มีผลต่อการตัดสินใจในไฟล์นี้

| ข้อเดิม | ผลลัพธ์ | สิ่งที่ได้ฝึกจริง | ปัญหาด้าน Material Design |
|---|---|---|---|

`สิ่งที่ได้ฝึกจริง` คือคอลัมน์ที่ทำงานหนักที่สุด — โจทย์หลายข้อฝึกอย่างหนึ่ง
แต่หน้าตาเหมือนฝึกอีกอย่าง เขียนสิ่งที่มันฝึกจริง ไม่ใช่สิ่งที่มันอ้างว่าฝึก

จบด้วยหนึ่งถึงสองบรรทัดว่าชุดใหม่นี้แก้อะไร ถ้าไม่มีของเดิมให้ตรวจ ลบหัวข้อนี้ทิ้ง

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

| ความเข้าใจผิด | จี้ไว้ที่ |
|---|---|

`จี้ไว้ที่` เขียนได้ว่า `ตัวอย่างที่ 2` · `ข้อ 4` · หรือ `ยังไม่ได้วาง` —
ค่าสุดท้ายมีความหมาย มันคือรายการรอสำหรับชุดหน้า

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

- **Page plan** — เขียนเมื่อการแบ่งหน้ามีผลต่อการสอนเท่านั้น
- **Acceptance checks** — ข้อความที่ตรวจได้บนไฟล์ที่ build เสร็จ เช่น ข้อไหน
  ต้องคงเดิม อะไรต้องไม่โผล่ อะไรต้องมาก่อนอะไร เกต QA ตรวจกลไกได้ แต่ไม่รู้
  เรื่องพวกนี้เลย

ลบทั้งหัวข้อเมื่อ `Deliverable: design-only`

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

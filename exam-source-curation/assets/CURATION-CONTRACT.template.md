# Curation Contract — <course or lane name>

## Contract

- Contract ID: `<slug>-curation`
- Status: `draft` | `approved`
- Current phase: `0 intake` | `1 transcribe-check` | `2 item-analysis` | `3 taxonomy` | `4 selection` | `5 sequence` | `6 foundation-targets`
- Primary objective: <ผู้เรียนกลุ่มไหน จะได้อะไรจากชุดข้อที่คัด ภายในเวลาเท่าไร>
- Learners and time budget: <ระดับผู้เรียน, จำนวนชั่วโมง, ส่วนฐาน/ส่วนขยาย>
- Machine facts: `curation-config.json`, `records/`, `curation-state.json`
- Current status lives in: <SHEET-INDEX หรือไฟล์สถานะของโปรเจกต์>

Contract นี้เป็นเจ้าของขอบเขต source นโยบายหลักฐาน และเกตของงานคัดข้อ
ข้อเท็จจริงรายข้ออยู่ใน JSON; เหตุผลและข้อเสนออยู่ในไฟล์ markdown ของแต่ละเฟส

## Sources and evidence policy

- Canonical sets, roles and provenance: ดู `curation-config.json`; สรุปใน `SOURCE-INVENTORY-<slug>.md`
- Frequency denominator: <ชุดที่นับ> — น้ำหนักหลักฐาน: <official เต็ม / มีชุด tutor-compiled จึงเป็นหลักฐานอ่อน>
- Supplementary use: <ใช้หาวิธีเทียบ โจทย์สะพาน หรือคู่เปรียบต่าง; ไม่เพิ่มความถี่>
- Answer keys: <ชุดไหนมีเฉลยต้นฉบับ ชุดไหนต้อง blind audit>

## Authority

1. คำสั่งปัจจุบันของครูและการตัดสิน candidate ของครู
2. หน้าต้นฉบับที่มองเห็นจริงเป็นหลักฐานของโจทย์ ตัวเลือก และรูป; ข้อความที่ดึงอัตโนมัติเป็นตัวช่วยค้น
3. เฉลยต้นฉบับเป็นสิ่งที่ต้องตรวจ ไม่ใช่ข้อยุติ
4. ห้ามแก้ source เงียบ ๆ; ติดธงพร้อมหลักฐานและข้อเสนอ

## Phase scope

<เขียนเฉพาะเฟสที่ตกลงแล้ว พร้อมสิ่งที่อยู่นอกขอบเขต เช่น ยังไม่ผลิต DOCX>

## Current boundary

- <ทำถึงไหนแล้ว ตัวเลขจาก check_curation.py>
- <เกตถัดไปและสิ่งที่รอครูตัดสิน>

## Decisions

| Date | Decision | Why |
|---|---|---|

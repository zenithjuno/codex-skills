# codex-skills

ชุด **Agent Skills** ที่ผมใช้จริงในงานสอนคณิตศาสตร์และการทำสื่อการเรียนรู้ — ใช้ได้ทั้ง **Codex** และ **Claude Code**
เขียนโดยครูคณิตศาสตร์ที่ไม่ใช่ developer จึงเน้น *ตรวจสอบได้ · พึ่งพา dependency น้อย · อธิบายเป็นภาษาคน*

> A set of agent skills for Thai mathematics teaching materials and educational-game development.
> Authored by a maths teacher (non-developer); the design bias is toward verifiable output, minimal
> dependencies, and plain-language explanation. Skill bodies are in English (model-facing);
> some domain terms are Thai because the output is Thai teaching material.

---

## กระบวนการทำงาน (workflow)

| skill | ทำอะไร |
|---|---|
| [`task-scoping`](task-scoping) | ตัดสินก่อนลงมือว่างานนี้เป็น S / M / L แล้วเลือกกระบวนการที่เบาที่สุดที่ยังปลอดภัย |
| [`grill-to-build`](grill-to-build) | ออกแบบก่อนสร้าง — ซักผู้ใช้ด้วยคำถามที่มีข้อเสนอแนะกำกับ ล็อกทุกการตัดสินใจลง ledger แล้วออก BLUEPRINT + CONSTRUCTION_PLAN · ไม่เริ่ม build จนกว่าจะอนุมัติ |
| [`plan-scrutinize`](plan-scrutinize) | อ่านแผนแบบคนนอก **ก่อน** ลงมือ เพื่อจับความผิดพลาดราคาแพงตอนที่ยังแก้ด้วยประโยคเดียวได้ |
| [`build-changelog`](build-changelog) | คุม build ยาว ๆ โดยไม่ต้องแบกประวัติไว้ใน context — hot state หนึ่งไฟล์ + audit log แบบ append-only ค้นด้วย id |
| [`handoff`](handoff) | สรุปสถานะเพื่อไปคุยต่อใน session ใหม่โดยไม่เสียบริบท |
| [`whats-next`](whats-next) | บอกว่าตอนนี้อยู่ตรงไหนของวงจร แล้วควรทำอะไรต่อ **หนึ่งอย่าง** |

## คุณภาพและการตรวจสอบ (quality)

| skill | ทำอะไร |
|---|---|
| [`systematic-debugging`](systematic-debugging) | ห้ามแก้ก่อนหาสาเหตุ — 4 เฟส และถ้าแก้ไม่หาย 3 ครั้งให้หยุดตั้งคำถามกับสถาปัตยกรรม |
| [`verification-before-completion`](verification-before-completion) | ห้ามบอกว่า "เสร็จ/ผ่าน/แก้แล้ว" ถ้ายังไม่ได้รันคำสั่งพิสูจน์ในเทิร์นนั้น |
| [`karpathy-guidelines`](karpathy-guidelines) | กันนิสัยเสียของ LLM — อย่าซับซ้อนเกิน แก้เท่าที่จำเป็น บอกสมมติฐาน ตั้งเกณฑ์สำเร็จที่วัดได้ |
| [`feedback-to-leverage`](feedback-to-leverage) | เวลาโดนแก้งานซ้ำ ๆ ให้เปลี่ยนเป็นการ์ดถาวรที่เล็กที่สุด (เทสต์ / กฎ / เอกสาร) แทนการจำเอาเอง |
| [`blind-answer-key-audit`](blind-answer-key-audit) | ตรวจเฉลยด้วยการ **แก้โจทย์ใหม่แบบไม่ดูเฉลย** แล้วค่อยเทียบ |

## สื่อการสอนภาษาไทย (Thai teaching material)

| skill | ทำอะไร |
|---|---|
| [`thai-math-docx`](thai-math-docx) | สร้าง/แก้/ตรวจไฟล์ Word คณิตศาสตร์ภาษาไทย รวมสมการ OMML และการตรวจความปลอดภัยตอนแทรกเนื้อหา |
| [`thai-font-normalize`](thai-font-normalize) | บังคับฟอนต์ไทยใน .docx ให้เป็น TH Sarabun New กันตกไป Angsana New ตอน export PDF หรือ clear formatting |
| [`math-handout-sandbox`](math-handout-sandbox) | ออกแบบสื่อคณิตศาสตร์แบบครูนำ คุยก่อนแล้วค่อยผลิต |
| [`soffice-runtime-fix`](soffice-runtime-fix) | ซ่อม LibreOffice/soffice ที่พังหลัง Codex อัปเดต runtime บน macOS |

## เกมการเรียนรู้ (HTML/JS learning games)

| skill | ทำอะไร |
|---|---|
| [`learning-game-design`](learning-game-design) | ออกแบบเกมการเรียนรู้แบบเบา — จากเป้าหมายการเรียนรู้ → loop → แผนเนื้อหา |
| [`game-content-audit`](game-content-audit) | ตรวจ **ความถูกต้องของเนื้อหา** ที่เกมสร้าง + ความสมบูรณ์/ความเป็นส่วนตัวของข้อมูลผู้เล่น (สคริปต์ Python stdlib ล้วน) |
| [`learner-playtest`](learner-playtest) | เก็บและวิเคราะห์ feedback จาก **ผู้เรียนจริง** (AI ไม่จำลองผู้เล่นแทน) |
| [`ship-check`](ship-check) | ด่านสุดท้ายก่อนปล่อยให้ผู้เรียนใช้ — สแกนหา ship-blocker + dry-run + เช็กลิสต์ความพร้อม |
| [`playwright`](playwright) | ขับเบราว์เซอร์จริงจาก terminal เพื่อทดสอบหน้าเว็บ |

---

## ติดตั้ง

**Codex** — วางไว้ที่ `~/.codex/skills/<name>/`

```bash
git clone https://github.com/zenithjuno/codex-skills.git ~/.codex/skills
```

**Claude Code** — symlink เข้ามาให้เห็นทั้งสองเครื่องมือจากต้นทางเดียว ไม่มี drift

```bash
mkdir -p ~/.claude/skills
for s in ~/.codex/skills/*/; do ln -sfn "$s" ~/.claude/skills/"$(basename "$s")"; done
```

> **ทั้งสองเครื่องมือ cache รายชื่อสกิล — ต้องรีสตาร์ตถึงจะเห็นของใหม่**

แต่ละสกิลมี `SKILL.md` (frontmatter `name` + `description` สำหรับ Claude) และส่วนใหญ่มี
`agents/openai.yaml` (สำหรับ Codex) — แต่ละเครื่องมืออ่านส่วนของตัวเองและไม่สนใจอีกส่วน
จึงใช้ต้นฉบับเดียวร่วมกันได้

---

## ลิขสิทธิ์และที่มา

โค้ดและเอกสารที่เขียนเองอยู่ภายใต้ [MIT](LICENSE) — ยกเว้นส่วนที่ระบุไว้ด้านล่าง

| skill | ที่มา | สัญญาอนุญาต |
|---|---|---|
| `playwright` | ดัดแปลงจาก [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) | Apache-2.0 — ดู [`playwright/LICENSE.txt`](playwright/LICENSE.txt) และ [`NOTICE.txt`](playwright/NOTICE.txt) |
| `systematic-debugging` | ดัดแปลงจาก [obra/superpowers](https://github.com/obra/superpowers) | MIT (เล็มและปรับให้เข้ากับงาน Apps Script/HTML) |
| `verification-before-completion` | ดัดแปลงจาก [obra/superpowers](https://github.com/obra/superpowers) | MIT |
| `karpathy-guidelines` | เรียบเรียงจากข้อสังเกตของ [Andrej Karpathy](https://x.com/karpathy/status/2015883857489522876) | MIT |

**ไม่รวมอยู่ใน repo นี้โดยตั้งใจ** (ดู [`.gitignore`](.gitignore)) — เป็นของบุคคลที่สาม ไม่ใช่ผลงานเรา
และไม่มีสิทธิ์เผยแพร่ต่อ:

- `pdf/` — © Anthropic PBC, all rights reserved
- `.system/` — สกิลระบบที่มากับ Codex (`skill-creator`, `skill-installer`, `openai-docs`, `imagegen`, `plugin-creator`, `review-agent`)

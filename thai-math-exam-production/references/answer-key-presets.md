# Answer-Key Export Presets (`thai-math-exam-production`)

Load this reference **only** when exporting an approved exam's answer key to DOCX/PDF.
Choose one named preset based on who will read the exported file:

| Preset | Audience | Rubric | Structure & tone |
|---|---|---|---|
| `rath-center-student` | Students studying and rewriting missed items (screen-first PDF/DOCX) | **Omit** | Clean Rath Center style: underlined `ตอบ`, conversational "พี่สอนน้อง" prose + aligned equations, no bullet dots, color annotated figures, full algebra/inequality steps |
| `teacher-full` | Teacher grading / archival reference | **Include** | Complete key from `ANSWER-KEY.md` with scoring rubrics and full distractor notes |

---

## Preset 1 — `rath-center-student` (Recommended for student-facing answer keys)

### 1. Item layout (zero visual clutter)
- **No bullet dots (`•`)** on solution steps and **no repetitive boilerplate headers** (`แนวคิดหลัก:`, `วิธีทำ:`, `ข้อควรระวัง:`) or heavy colored banners on every item.
- Exact per-item flow:
  1. Bold item number + **exact approved stem, figure, and choices** imported directly from the approved exam generator/state (zero rephrasing).
  2. Single answer line: **<u>ตอบ</u> `<คำตอบ>`** (navy `#1E3A8A`, `keep_with_next=True`).
  3. **Flowing Thai tutor prose ("พี่สอนน้อง")** alternating with indented equation lines (`left_indent = 0.75 cm`) and short inline step callouts (`← คูณ −1 ตลอด (ต้องกลับ > เป็น <)`).
  4. Subtle light-gray divider (`#CBD5E1`) between items.
- **Written items:** Keep **all valid solution methods** (students pick whichever method clicks best) and **omit teacher `Scoring rubric`**.

### 2. Pedagogical depth (for learners with weak foundations)
- Never shortcut foundational algebra steps — especially **quadratic inequalities** and **absolute-value inequalities**. Always show the full chain:
  1. Move terms so one side is `0` (or multiply by `−1` with an explicit inequality-flip reminder).
  2. Factor explicitly (name the identity used, e.g., difference of squares `a² − b² = (a − b)(a + b)`, or `|A| ≤ k ⇔ −k ≤ A ≤ k`).
  3. Solve each factor `= 0` for critical points.
  4. Draw a compact **number line (`+ − +`)** with solid/open dots and shade the chosen interval before stating the final answer.
- Include brief distractor cautions only where a real misconception traps students (do not mechanically list all 3 wrong choices on every item).

### 3. Screen-first layout & figures
- **2-column dashed-divider splits (`┆`, `style="dashed", size=4, color="94A3B8"`):** Use for parallel equations/cases or side-by-side dual methods. **Fallback to full-width stacked layout** whenever equations are wide enough to risk mid-formula wrapping.
- **Side-by-side text + figure:** For graph items (domain/range projection, inverse reflection `y = x`), place explanation text on the left (~10.5 cm) and the annotated solution figure on the right (~6.2–6.8 cm).
- **Color accents allowed (screen-first):** Keep the original curve clean/faint and highlight projections, reflection lines, critical points, and overlap intervals with crisp accent colors (blue/red/green/orange).
  - *PyMuPDF (`fitz`) SVG note:* Avoid `<tspan>` inside `<text text-anchor="middle">` (use `text-anchor="start"` when subscripts are present).

### 4. Mandatory technical guardrails
- **Zero leaked math in plain-text runs (`_t(...)`):** Every standalone Latin variable (`X`, `Y`, `B`, `x`, `y`, `r⁻¹`), negative number (`−1`, `−4`), or calculated numeric value (`ได้ 2`) must be emitted as editable OMML (`_m(...)`), never plain Thai text. Run a regex scan over `_t(...)` before export because automated `math-in-plain-text` checks only catch relational operators (`=`, `<`, `>`, `≤`, `≥`).
- **Keep every item intact on one page:** Apply `keep_with_next = True` from stem → choices → `ตอบ` → all solution blocks except the last block of the item, and add `<w:cantSplit/>` to every table row. (If a multi-method written item exceeds one full page, break cleanly at a major sub-heading/method boundary.)
- **Verify in Microsoft Word:** Export via `word_export_pdf.py` and visually inspect a contact sheet of all pages for equation wrapping, figure clarity, and page breaks.

---

## Preset 2 — `teacher-full`

- Maps `exam-state/ANSWER-KEY.md` directly into a clean 1-column DOCX preserving every section: exact approved stem/choices (fidelity-checked against `item-variants.json`), answer, teaching solution (with all methods and distractor notes), and full `Scoring rubric` for written items.
- Keep synthetic division as an editable Word table (`add_synthetic_division`) rather than prose.

# Thai Math DOCX Text Knowledge

This document records the user's concrete preferences for generating Thai math documents in `.docx`, especially mixed Thai prose plus Latin/math-like tokens. It is intended to be used as source material for a future Codex skill.

The goal is not "pretty enough in a generic renderer." The goal is: when opened in Microsoft Word on the user's machine, the generated file should behave almost exactly like a document the user typed manually.

## 1. Target Output

Generate editable Word documents for Thai mathematics content:

- Thai prose should look like normal Thai exam/handout text.
- Latin/math-ish content inside Thai prose should look mathematically intentional, not like random English text.
- Real mathematical notation should be editable Word Equation / OMML, not images.
- Clear Formatting in Word must not destroy the typography.
- Copy/paste into the user's own Word files should remain compatible with the user's normal Thai document style.

The preferred visual target is Microsoft Word with `TH Sarabun New` available. LibreOffice/Codex render is useful only as a structural sanity check; Word on the user's machine is the visual truth.

## 2. Core Typography Preference

### 2.1 Normal Thai Body Text

Thai text:

- Font: `TH Sarabun New`
- Size: 16pt
- Word script route: Complex Script
- OOXML size: `w:szCs="32"`
- Language: Thai / bidi route should be present: `w:bidi="th-TH"`

This applies to:

- ordinary Thai prose
- Thai exam instructions
- Thai choice text
- Thai units such as `คน`
- Thai labels such as `ข้อใดกล่าวถูกต้อง`
- Thai alphabet choice markers `ก.`, `ข.`, `ค.`, `ง.`

### 2.2 Latin Administrative Text

Plain Latin or ordinary numbers that are not mathematically meaningful may remain normal text:

- Font: `Cambria`
- Size: 12pt
- OOXML Latin size: `w:sz="24"`

Examples where plain text is acceptable:

- dates and times in administrative header text: `09.00 - 10.00`
- page numbering text if the whole footer is intentionally Thai-style
- file metadata
- ordinary English labels in a developer spike

However, in this project the footer has a separate decision: use `TH Sarabun New 12pt` throughout the footer for both Thai and page-number fields.

### 2.3 Math Equations

Mathematical notation should be real Word Equation / OMML.

Expected visual behavior:

- Variables are italic where mathematical convention calls for it.
- Delimiters, fractions, radicals, bars, matrices, sums, subscripts, and superscripts are Word equation structures.
- The user can click, edit, copy, and paste equations in Word.
- Equations must not be raster images.

Default math font may be Word's equation default, normally Cambria Math.

### 2.4 Question Number Labels

Question labels such as `1.`, `2.`, `3.` visually function like Thai document labels, not mathematical numbers and not English text.

Preference:

- Font: `TH Sarabun New`
- Size: 16pt
- Set all font slots to `TH Sarabun New`: `ascii`, `hAnsi`, and `cs`

Reason: if `1.` is left in Cambria 12pt, it looks visually detached from the Thai question line. If it is only partially styled, Word may show it as a smaller Latin run.

Recommended helper:

```python
def set_thai_label_run(run, bold=None, size=16):
    if bold is not None:
        run.bold = bold
    set_run_font(
        run,
        ascii_font="TH Sarabun New",
        cs_font="TH Sarabun New",
        size=size,
    )
    r_pr = run._r.get_or_add_rPr()
    if r_pr.find(qn("w:cs")) is None:
        r_pr.append(OxmlElement("w:cs"))
    lang = r_pr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        r_pr.append(lang)
    lang.set(qn("w:bidi"), "th-TH")
```

## 3. The Most Important Word OOXML Detail

Word does not use one font-size setting for every script.

Latin text size:

- Element: `w:sz`
- Example: `w:sz w:val="24"` means 12pt

Thai / Complex Script size:

- Element: `w:szCs`
- Example: `w:szCs w:val="32"` means 16pt

This is why setting only `normal.font.size = Pt(12)` in `python-docx` is not enough. It writes Latin size, but Thai may still inherit Complex Script size 11pt from defaults.

### 3.1 Required Clear Formatting Safety Net

Every generated `.docx` with Thai text must explicitly set both `docDefaults` and `Normal` style:

- Latin font: `Cambria`
- Latin size: 12pt (`w:sz="24"`)
- Complex Script font: `TH Sarabun New`
- Complex Script size: 16pt (`w:szCs="32"`)
- Complex Script language: `w:bidi="th-TH"`

This is required because the user often clears formatting or pastes generated content into existing Word documents. If `Normal` or `docDefaults` still say Complex Script 11pt, Clear Formatting will turn Thai text into `TH Sarabun New 11pt`, which is wrong.

### 3.2 Required Default XML Shape

The effective style defaults should contain the equivalent of:

```xml
<w:docDefaults>
  <w:rPrDefault>
    <w:rPr>
      <w:rFonts w:ascii="Cambria" w:hAnsi="Cambria" w:cs="TH Sarabun New"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="32"/>
      <w:lang w:val="en-US" w:bidi="th-TH"/>
    </w:rPr>
  </w:rPrDefault>
</w:docDefaults>
```

The `Normal` style should carry the same run properties:

```xml
<w:style w:type="paragraph" w:styleId="Normal">
  <w:name w:val="Normal"/>
  <w:rPr>
    <w:rFonts w:ascii="Cambria" w:hAnsi="Cambria" w:cs="TH Sarabun New"/>
    <w:sz w:val="24"/>
    <w:szCs w:val="32"/>
    <w:lang w:val="en-US" w:bidi="th-TH"/>
  </w:rPr>
</w:style>
```

Remove theme attributes from these defaults when possible:

- `w:asciiTheme`
- `w:hAnsiTheme`
- `w:eastAsiaTheme`
- `w:cstheme`

Theme attributes can make Word resolve fonts differently than intended.

### 3.3 Python Helper Pattern

Use a helper like this before writing content:

```python
def ensure_child(parent, tag):
    child = parent.find(qn(tag))
    if child is None:
        child = OxmlElement(tag)
        parent.append(child)
    return child


def set_default_run_properties(r_pr):
    r_fonts = ensure_child(r_pr, "w:rFonts")
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        r_fonts.attrib.pop(qn(attr), None)
    r_fonts.set(qn("w:ascii"), "Cambria")
    r_fonts.set(qn("w:hAnsi"), "Cambria")
    r_fonts.set(qn("w:cs"), "TH Sarabun New")

    sz = ensure_child(r_pr, "w:sz")
    sz.set(qn("w:val"), "24")
    sz_cs = ensure_child(r_pr, "w:szCs")
    sz_cs.set(qn("w:val"), "32")

    lang = ensure_child(r_pr, "w:lang")
    lang.set(qn("w:val"), "en-US")
    lang.set(qn("w:bidi"), "th-TH")


def enforce_document_font_defaults(doc):
    styles = doc.styles.element
    doc_defaults = styles.find(qn("w:docDefaults"))
    if doc_defaults is None:
        doc_defaults = OxmlElement("w:docDefaults")
        styles.insert(0, doc_defaults)
    r_pr_default = ensure_child(doc_defaults, "w:rPrDefault")
    set_default_run_properties(ensure_child(r_pr_default, "w:rPr"))

    normal = doc.styles["Normal"]
    set_default_run_properties(normal._element.get_or_add_rPr())
```

Then configure paragraph spacing:

```python
normal = doc.styles["Normal"]
enforce_document_font_defaults(doc)
normal.font.name = "Cambria"
normal.font.size = Pt(12)
normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
normal.paragraph_format.line_spacing = 1.0
```

Important: `normal.font.size = Pt(12)` does not replace the need for `w:szCs=32`.

## 4. Run-Level Rules

### 4.1 Thai Runs

Every run containing Thai should:

- use `w:rFonts w:cs="TH Sarabun New"`
- include the empty `<w:cs/>` toggle
- include `w:lang w:bidi="th-TH"`
- usually have Complex Script size 16pt

The empty `<w:cs/>` toggle matters. Without it, Word may still route the run incorrectly or fall back when styles change.

Recommended helper:

```python
def set_run_font(run, ascii_font="Cambria", cs_font="TH Sarabun New", size=12):
    run.font.name = ascii_font
    run.font.size = Pt(size)
    r_pr = run._r.get_or_add_rPr()
    r_fonts = r_pr.rFonts
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    r_fonts.set(qn("w:ascii"), ascii_font)
    r_fonts.set(qn("w:hAnsi"), ascii_font)
    r_fonts.set(qn("w:cs"), cs_font)


def set_thai_run(run, bold=None, size=16):
    if bold is not None:
        run.bold = bold
    set_run_font(run, size=12)
    r_pr = run._r.get_or_add_rPr()
    sz = ensure_child(r_pr, "w:sz")
    sz.set(qn("w:val"), "24")
    sz_cs = ensure_child(r_pr, "w:szCs")
    sz_cs.set(qn("w:val"), str(size * 2))
    if r_pr.find(qn("w:cs")) is None:
        r_pr.append(OxmlElement("w:cs"))
    lang = r_pr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        r_pr.append(lang)
    lang.set(qn("w:val"), "en-US")
    lang.set(qn("w:bidi"), "th-TH")
```

Important insertion-point detail: for Thai body runs, do not set Latin size to 16pt. The run should carry Latin `w:sz=24` and Complex Script `w:szCs=32`. If a Thai body run has `w:sz=32`, then manually typing Latin text at the end of that Thai run in Word can inherit 16pt direct formatting instead of Normal's Cambria 12pt. Reserve all-slot 16pt formatting for question labels or other intentionally Thai-styled labels.

### 4.2 Latin Runs

Latin text that is truly prose or administrative should be:

- `Cambria`
- 12pt
- no `<w:cs/>` required unless it contains Thai

But in question statements, many Latin tokens are actually mathematical tokens. Prefer OMML for those.

For plain numeric/comma/Latin sequences that are not intended to be Thai prose and should visually
stay in Cambria, use an explicit Latin text run rather than a Thai `text` part. In the transcript
schema this can be represented as:

```json
{"type": "latin_text", "text": "123, 221, 112, "}
```

The builder should emit `w:rFonts w:ascii="Cambria" w:hAnsi="Cambria"`, `w:sz="24"`, and
`w:lang w:val="en-US"`, without a `<w:cs/>` toggle. This prevents numeric lists inside Thai
sentences from rendering as `TH Sarabun New` simply because they were encoded as Thai text runs.
Keep variables inside the list, such as `a` or `6b`, as math tokens when they are mathematical
variables.

### 4.3 Mixed Thai + Latin/Math-ish Lines

The preferred approach for exam questions is:

- Thai prose as Thai runs.
- Math-ish Latin variables, expressions, set notation, logic symbols, and question-relevant numbers as inline OMML.
- Do not rely on plain Cambria text for variables if those variables are part of math notation.

This gives deterministic equation editing and avoids inconsistent mixed-font runs.

Example target line:

```text
ให้ A และ B เป็นเซต โดยที่จำนวนสมาชิกของ P(A ∪ B) และ P(A ∩ B) เท่ากับ 256 และ 16 ตามลำดับ
```

Preferred structured representation:

```json
[
  {"type": "text", "text": "ให้ "},
  {"type": "math", "kind": "plain", "value": "A"},
  {"type": "text", "text": " และ "},
  {"type": "math", "kind": "plain", "value": "B"},
  {"type": "text", "text": " เป็นเซต โดยที่จำนวนสมาชิกของ "},
  {"type": "math", "kind": "set_expr", "func": "P", "inside": ["A", "∪", "B"]},
  {"type": "text", "text": " และ "},
  {"type": "math", "kind": "set_expr", "func": "P", "inside": ["A", "∩", "B"]},
  {"type": "text", "text": " เท่ากับ "},
  {"type": "math", "kind": "plain", "value": "256"},
  {"type": "text", "text": " และ "},
  {"type": "math", "kind": "plain", "value": "16"},
  {"type": "text", "text": " ตามลำดับ"}
]
```

This may seem more aggressive than ordinary textbook typesetting, but it is preferred because it is deterministic and editable.

## 5. What Counts as Math-ish

Use OMML for:

- Variables: `A`, `B`, `x`, `p`, `q`, `r`, `s`, `z`
- Multiple variable lists in mathematical context: `p, q, r`
- Set/probability notation: `P(A ∪ B)`, `P(B - A)`
- Logic notation: `(p ∧ q) ↔ (r ∨ s)`, `p → (q → r)`
- Numbers that are values inside the question's mathematical structure: `256`, `16`, `80`, `33`, `28`, etc. when they are part of the problem data
- Choice values when choices are pure numeric answers: `ก. 1`, `ข. 2`, etc.
- Fractions, radicals, powers, subscripts, bars, matrices, sums
- Special symbols: `ℝ`, `∪`, `∩`, `∧`, `∨`, `↔`, `→`, `∑`, `√`

Plain text is acceptable for:

- Thai words and units
- Administrative dates/times
- Page footer prose
- Form labels
- Non-math English prose

Borderline policy:

- In exam question bodies, lean toward OMML for Latin/math-ish tokens.
- In headers/footers/admin copy, lean toward styled text unless the symbol is truly mathematical, such as `ℝ`.

## 6. OMML Preferences

### 6.1 Use Real Structures

Do not fake complex math with Unicode-only text if Word has an equation structure.

Use:

- `<m:f>` for fractions
- `<m:rad>` for radicals
- `<m:sSup>` for superscripts
- `<m:sSub>` for subscripts
- `<m:sSubSup>` for subscript plus superscript
- `<m:nary>` for sums
- `<m:limLow>` for limits with conditions below `lim`
- `<m:bar>` with top position for conjugates
- `<m:m>` for matrices
- `<m:d>` for delimiters

### 6.2 Conjugate Bar

Complex conjugate should use a bar above the symbol, not below.

Correct:

```xml
<m:bar>
  <m:barPr><m:pos m:val="top"/></m:barPr>
  <m:e>...</m:e>
</m:bar>
```

### 6.3 Delimiters

For expressions such as `P(A ∪ B)`, prefer OMML delimiters:

```xml
<m:d>
  <m:dPr>
    <m:begChr m:val="("/>
    <m:endChr m:val=")"/>
  </m:dPr>
  <m:e>...</m:e>
</m:d>
```

This keeps the parentheses semantically part of the equation.

Use the same paired `<m:d>` structure for finite-set braces. Do not emit `{`
and `}` as separate `<m:r>` runs: Word then edits them independently rather
than treating the set as one delimited object.

Distinguish source scope from visible mathematics. In linear notation such as
`∛(−64)`, the outer parentheses may exist only to tell the parser that `−64` is
the full radicand. Consume that wrapper because `<m:rad>` already supplies the
scope. Preserve a delimiter only when it groups a genuine subexpression inside
the radicand, such as a grouped base to which a power applies.

Likewise, parse `−1⁄4` as unary minus followed by `<m:f>1/4</m:f>`. Do not move
the sign into `<m:num>` merely because it precedes the numerator in linear
source. An explicitly grouped numerator remains a separate source decision.

For matrices, use editable OMML `<m:m>` wrapped in delimiter `<m:d>` rather than plain text brackets. Transcript nodes can carry rows/cells explicitly, for example a 2×2 matrix as `{"kind":"matrix","rows":[[["1"],["1"]],[["1"],["−1"]]]}`. Each cell should still be built from math items so variables remain italic and numerals/operators remain upright.

### 6.4 Variables and Upright Text

Italicize variables:

```xml
<m:r>
  <m:rPr><m:sty m:val="i"/></m:rPr>
  <m:t>x</m:t>
</m:r>
```

Variables stay italic **even when adjacent to a coefficient or another variable**.
The builder decomposes compact string items such as `"3x"`, `"−2x"`, `"ac"`, and
`"2π"` through the shared math grammar, so `3x` renders as an upright `3` run
followed by an italic `x` run — you do not need to pre-split them into
`["3", "x"]`. Known function names (`sin`, `cos`, `log`, `ln`, …) are never split.
Deliberate multi-letter **upright** identifiers, units, or labels (e.g. `cm`,
`kg`, a segment name `AB`) must be passed as an explicit `{"kind": "upright",
"text": "…"}` node — a bare multi-letter alphabetic string is treated as a
product of variables and italicized.

Use upright/plain equation text for:

- numerals
- operators
- punctuation
- known function names such as `sin`, `cos`, `tan`, `sec`, `csc`, `cosec`, `cot`, `log`, `ln`
- Thai should not be inside OMML unless it is deliberately part of the equation layout

Known math functions must not be treated as variables. If emitted as ordinary italic math runs,
Word will show `sin x`, `cos y`, `log x`, etc. incorrectly. The user's Word behavior when typing
manually is the target: function names are upright/roman, while arguments such as `x`, `y`, and
`theta` stay italic when they are variables.

For function calls with an explicit argument, prefer real OMML function structures:

```xml
<m:func>
  <m:fName>
    <m:r><m:rPr><m:nor/></m:rPr><m:t>sin</m:t></m:r>
  </m:fName>
  <m:e>
    <!-- italic variable, angle, delimiter, etc. -->
  </m:e>
</m:func>
```

For function names with no explicit function argument inside the same OMML function node, do not
use an empty `<m:func>`. In LibreOffice sanity render this can show an unwanted empty placeholder
box, and in Word it may behave like a function waiting for an argument. Example: `log_2 x` should
be emitted as roman/upright `log` with a subscript base and then a separate italic `x`, not as
`<m:func>` with an empty `<m:e/>`.

Recommended pattern for `log_2 x`:

```xml
<m:sSub>
  <m:e>
    <m:r><m:rPr><m:nor/></m:rPr><m:t>log</m:t></m:r>
  </m:e>
  <m:sub>
    <m:r><m:rPr><m:nor/></m:rPr><m:t>2</m:t></m:r>
  </m:sub>
</m:sSub>
<m:r><m:rPr><m:sty m:val="i"/></m:rPr><m:t>x</m:t></m:r>
```

### 6.5 No Equation Images

Equation images are forbidden for normal math text. If OMML cannot represent the notation, stop and report the limitation instead of silently inserting an image.

Generic document images are not evidence of rasterized equations. The OMML audit
checks native math; the media contract checks whether images are allowed and
valid. Do not fail the OMML audit merely because a drawing or picture exists.

### 6.6 Vector Arrows and Accents

For vector notation such as `\vec u`, `\overrightarrow{AB}`, or dot products of vectors, use OMML
accent structures rather than plain Unicode arrows when possible. Current user preference:

- general vectors such as `u`, `v`, `w`, `AB`, `BC`, and `CA` use a right harpoon accent;
- unit basis vectors `i`, `j`, and `k` use a hat accent with OMML `m:chr` set to combining
  circumflex `U+0302`, not ASCII caret `^`.

```xml
<m:acc>
  <m:accPr><m:chr m:val="&#x20D1;"/></m:accPr>
  <m:e>...</m:e>
</m:acc>
```

This keeps the vector marker attached to the base expression. Render sanity should still inspect
the result because accent placement can vary across renderers. In Stage 6, this pattern rendered
acceptably for `u`, `v`, `w`, `AB`, `BC`, and `CA`.

For unit basis vector hats, Microsoft Word visual truth on 2026-07-07 showed that ASCII caret
`^` as the OMML hat character can render too low and overlap the base letter. Use `U+0302`
instead. This preserves the original italic `i/j/k` base characters and avoids the extra source
risk of dotless `ı/ȷ` or upright base substitutions.

### 6.7 Summations and Limits

For summations with upper/lower limits such as `\sum_{n=1}^{\infty} a_n^{-1}`, use a real
`<m:nary>` object instead of a plain Unicode `∑` plus loose superscripts/subscripts.

Recommended structure:

```xml
<m:nary>
  <m:naryPr>
    <m:chr m:val="∑"/>
    <m:limLoc m:val="undOvr"/>
  </m:naryPr>
  <m:sub>...</m:sub>
  <m:sup>...</m:sup>
  <m:e>...</m:e>
</m:nary>
```

For limits such as `lim_{x→−3}`, use `<m:limLow>` so the condition is attached to `lim` as a
limit object:

```xml
<m:limLow>
  <m:e>lim</m:e>
  <m:lim>x→−3</m:lim>
</m:limLow>
```

### 6.8 Thai Text Inside OMML

Default rule: Thai text should live in normal Word text runs outside OMML. This is the safest route
for ordinary prose connectors such as `และ`, `หรือ`, `โดยที่`, `ซึ่ง`, `เป็น`, `ให้`, and units like
`คน`, `วิธี`, `หน่วย` when those words can sit naturally between inline equations.

Allowed exception: Thai may be inside OMML when moving it outside would break the mathematical
layout or editability. Examples:

- Piecewise/cases definitions: `f(x) = { ... เมื่อ x > 0; ... เมื่อ x ≤ 0 }`
- Equation arrays or systems where the Thai word aligns inside the brace/array column
- Underbrace/overbrace labels or annotations whose label must remain attached to the math object
- Multi-line definitions where a Thai condition phrase is visually part of each equation row
- Rare set-builder or condition notation where the source explicitly places Thai condition text
  inside the displayed mathematical structure

Not allowed: Thai that is only a prose connector between adjacent math tokens. For example,
`z_1 และ z_2` should be encoded as math `z_1`, text ` และ `, then math `z_2`, not as one OMML run.

Transcript policy: Thai in math must be explicit, never an accidental string inside `math.items`.
Use a dedicated node such as:

```json
{"kind": "thai_text", "text": " เมื่อ "}
```

Builder policy: explicit Thai math text must be upright and must carry Word run properties inside
the math run. Use `m:rPr` first, then `w:rPr`, because Word accepts both in a math run and expects
the math run properties before WordprocessingML run properties.

Recommended XML shape:

```xml
<m:r>
  <m:rPr><m:nor/></m:rPr>
  <w:rPr>
    <w:rFonts w:ascii="TH Sarabun New" w:hAnsi="TH Sarabun New" w:cs="TH Sarabun New"/>
    <w:sz w:val="32"/>
    <w:szCs w:val="32"/>
    <w:cs/>
    <w:lang w:val="th-TH" w:bidi="th-TH"/>
  </w:rPr>
  <m:t> เมื่อ </m:t>
</m:r>
```

Reason: an OMML run with only `<m:rPr><m:nor/></m:rPr>` does not carry the normal Thai text
formatting. It can render smaller or through the equation/text fallback route. `w:sz` and `w:szCs`
are half-point sizes, so `32` means 16 pt; `w:szCs` is the Complex Script size used by Thai.

Audit policy: OMML audit should not simply reject all Thai inside `m:oMath`. Instead, it should
fail only Thai math runs that lack the explicit Thai `w:rPr` above. It is acceptable for
`thai_math_run_count` to be nonzero only when those runs are intentional and pass formatting checks.

## 7. Paragraph Rhythm and Layout

Default paragraph rhythm:

- Line spacing: single (`1.0`), not `1.15`
- Space before: usually 0pt
- Space after: small and explicit, role-dependent

Do not rely on Word defaults.

Typical roles:

- Body question paragraph: Thai 16pt, single spacing, small space after
- Choices: indented slightly, Thai 16pt, single spacing
- Header title: larger TH Sarabun New, bold
- Footer: TH Sarabun New 12pt throughout

Because this is an exam-bank reconstruction, the target is clean reusable typography, not pixel-perfect replication of the PDF.

For compact exam data tables, the structured transcript may include explicit column widths rather than relying on Word auto-fit. This is especially useful for two-row statistical tables where a long Thai header column and several short numeric columns should stay on one or two natural lines. The builder should write fixed table layout plus per-cell `w:tcW` values, while allowing row heights to expand naturally.

## 8. Footer Preference

Footer final decision:

- Use `TH Sarabun New 12pt` throughout.
- Page field numbers should use the same footer styling.
- Do not spend time calibrating Codex/LibreOffice point sizes to match Microsoft Word exactly.

Reason: Codex's render stack may not match Word's real TH Sarabun New metrics. The user's Word render is authoritative, and the user is comfortable doing final manual handpicking.

Recommended field-run helper:

```python
def set_footer_field_run(run):
    set_run_font(run, ascii_font="TH Sarabun New", cs_font="TH Sarabun New", size=12)
    r_pr = run._r.get_or_add_rPr()
    if r_pr.find(qn("w:cs")) is None:
        r_pr.append(OxmlElement("w:cs"))
    lang = r_pr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        r_pr.append(lang)
    lang.set(qn("w:bidi"), "th-TH")
```

## 9. Structured Transcript Before DOCX

For fragile Thai/math exam content, do not generate `.docx` directly from prose in the prompt. Create an intermediate JSON transcript.

Benefits:

- User can review transcription outside Word.
- Math parts are explicitly typed.
- Source crops and uncertainties are linked.
- The DOCX generator becomes deterministic.
- Future sessions can resume from the JSON.

Recommended pattern:

```json
{
  "source": {
    "pdf": "/path/to/source.pdf",
    "rendered_pages_dir": "outputs/.../source/pdf-pages",
    "crops": ["outputs/.../stage2/crops/q01_q03_context.png"]
  },
  "document": {
    "title": "ข้อสอบ_..._ข้อ01-03.docx",
    "stage": "Stage 2",
    "questions": "01-03"
  },
  "uncertainties": [
    {
      "question": 3,
      "note": "Confirm variable q is plain q, no mark."
    }
  ],
  "questions": [
    {
      "number": 1,
      "prompt": [
        {"type": "text", "text": "ให้ "},
        {"type": "math", "kind": "plain", "value": "A"}
      ],
      "choices": [
        {"label": "ก", "parts": [{"type": "math", "kind": "plain", "value": "1"}]}
      ]
    }
  ]
}
```

Text parts should be Thai runs. Math parts should be converted to inline OMML.

When Thai text appears between math tokens, split it as separate transcript parts instead of
embedding it inside one math item. For example, `z_1 และ z_2` should be encoded as math `z_1`,
text ` และ `, then math `z_2`. If `และ` is placed inside `math.items`, Word treats it as part of
the same equation and the Thai text visually sinks into the OMML run. Builders should reject Thai
characters inside math items so this failure is caught before a DOCX is delivered.

## 10. Preferred Build Pipeline

For each DOCX:

1. Read source from rendered PDF pages/crops, not PDF text layer.
2. Create or update structured transcript JSON.
3. Generate DOCX using deterministic builder code.
4. Explicitly set `docDefaults` and `Normal` style safety net.
5. Apply direct run-level Thai/Latin/label/footer formatting.
6. Insert all math as OMML.
7. Run `thai-font-normalize` on the final DOCX.
8. Run a font-default audit.
9. Run an OMML audit.
10. Render DOCX to PNG/PDF for structural sanity check.
11. User opens in Microsoft Word for visual truth and final approval.

## 11. Required Audits

### 11.1 Font Default Audit

The audit must check both `docDefaults` and `Normal`.

Expected values:

- `ascii = Cambria`
- `hAnsi = Cambria`
- `cs = TH Sarabun New`
- `sz = 24`
- `szCs = 32`
- `bidi = th-TH`

Failure example:

```text
Normal: expected szCs='32', got '22'
```

This exact failure means Clear Formatting will likely produce Thai 11pt.

### 11.2 Thai Font Normalize

Run the user's `thai-font-normalize` skill or equivalent script after generation.

The normalizer should:

- repair `w:cs` font fallback
- ensure Thai text runs have `<w:cs/>`
- set Thai theme entries if needed
- preserve Latin font routing
- verify the result

Important: the normalizer is a safety net, not a replacement for writing correct OOXML during generation.

### 11.3 OMML Audit

The audit should count:

- `m:oMath`
- fractions
- radicals
- superscripts/subscripts
- n-ary operators
- bars
- matrices
- delimiters
- drawing/pict elements

Required:

- `m:oMath` count > 0 for math documents
- `image_count = 0` for equation content

### 11.4 Render QA

Use render output only to catch structural problems:

- missing glyphs
- layout collapse
- text overlap
- footer/header broken
- page count surprises

Do not over-calibrate font sizes based only on LibreOffice render if the user's Microsoft Word render looks right.

## 12. Common Failure Modes

### 12.1 Thai Looks Correct Until Clear Formatting

Cause:

- Direct runs were styled correctly, but `Normal` or `docDefaults` still had Complex Script 11pt.

Fix:

- Add `w:szCs="32"` to both `docDefaults` and `Normal`.
- Audit after `thai-font-normalize`.

### 12.2 Question Number Looks Too Small

Cause:

- `1.` stayed in Cambria 12pt or only Latin size was applied.

Fix:

- Treat question number as Thai label.
- Set ascii/hAnsi/cs all to `TH Sarabun New`.
- Use 16pt.

### 12.3 Footer Page Number Uses Cambria 12pt

Cause:

- Word field result/instruction runs were not styled.

Fix:

- Style every run that makes up the field: begin, instrText, separate, result, end.
- Use `TH Sarabun New 12pt` for footer field runs.

### 12.4 Thai Font Looks Wrong in Codex Render

Cause:

- LibreOffice/render environment may not resolve/render `TH Sarabun New` exactly like Microsoft Word.

Fix:

- Check XML invariants.
- Ask user to inspect in Microsoft Word.
- Do not chase exact visual calibration unless user explicitly requests it.

### 12.5 Latin Tokens in Thai Prose Feel Inconsistent

Cause:

- Some variables are plain Cambria text, others are OMML.

Fix:

- For question body content, prefer inline OMML for math-ish tokens.
- Use structured JSON to make the split explicit.

### 12.6 Manually Typed Latin After Thai Text Is Too Large

Cause:

- The visible Thai run is correct, but its direct run properties also set Latin size `w:sz="32"` because the generator used a single `run.font.size = 16pt` call.
- Word's style pane may still show Normal as Cambria 12pt, but the insertion point inherits direct formatting from the preceding run before it falls back to Normal.

Fix:

- For ordinary Thai body text, set `w:sz="24"` and `w:szCs="32"` on the same run.
- Keep `w:rFonts ascii/hAnsi="Cambria"` and `w:cs="TH Sarabun New"`.
- Keep `<w:cs/>` and `w:bidi="th-TH"` so Thai still routes as Complex Script 16pt.
- Use a separate label helper for question/choice labels that intentionally uses `TH Sarabun New 16pt` in all font slots.
- Add or run an insertion-safety audit that flags Thai body runs with `w:sz != 24` unless the run is an explicit label/title role.

## 13. Copy/Paste Compatibility Rules

The user may paste generated content into their own Word files.

To make this behave well:

- Keep `Normal` and `docDefaults` compatible with user preference.
- Avoid excessive one-off direct styling when a style/default should carry the behavior.
- Still apply run-level formatting for fragile mixed Thai/math content.
- Make labels and footers intentionally styled, not accidentally inherited.
- Keep equations as real OMML so pasted math remains editable.

The document should survive:

- Clear Formatting
- applying Normal style
- copy/paste into another Word document
- PDF export from Word

## 14. Skill Design Recommendation

If this knowledge becomes a Codex skill, keep `SKILL.md` lean and put this detailed material into `references/thai-math-docx-text.md`.

Suggested skill shape:

```text
thai-math-docx/
├── SKILL.md
├── references/
│   └── thai-math-docx-text.md
└── scripts/
    ├── audit_docx_font_defaults.py
    └── audit_docx_omml.py
```

`SKILL.md` should contain only the always-needed workflow:

1. Use rendered PDF/crops as source truth for Thai/math transcription.
2. Build structured JSON before DOCX.
3. Use TH Sarabun New 16pt for Thai, Cambria 12pt for Latin/admin text.
4. Prefer inline OMML for math-ish Latin/numeric tokens in question bodies.
5. Set `docDefaults` and `Normal` safety net.
6. Run `thai-font-normalize`.
7. Run font-default and OMML audits.
8. Render for sanity; user Word is visual truth.

Then link to the reference file for the detailed OOXML, examples, and failure modes.

## 15. Minimum Acceptance Checklist

A generated Thai math `.docx` is acceptable only if:

- Thai prose is `TH Sarabun New 16pt`.
- Latin/admin prose is `Cambria 12pt`, except explicitly Thai-styled labels/footers.
- Question numbers are `TH Sarabun New 16pt` in all font slots.
- Footer is `TH Sarabun New 12pt` throughout.
- `docDefaults` and `Normal` pass the font-default audit.
- All real math is OMML.
- Required mathematics is native OMML; generic document images follow the media
  contract.
- Paragraph spacing is single (`1.0`).
- `thai-font-normalize` passes.
- Render sanity check does not show broken layout.
- User's Microsoft Word inspection is treated as final visual authority.

## 16. Project-Derived Skill Upgrade Notes

These notes come from generating the 2568 NU Science Week math exam questions 1-30 according to the user's actual Word preferences. They are technical implementation guidance for upgrading a future `thai-math-docx` skill, not one-off project status.

### 16.1 Generator Architecture That Worked

Use a deterministic structured transcript as the source of truth for fragile exam reconstruction. A good schema separates:

- `text`: Thai prose runs routed through Complex Script.
- `latin_text`: ordinary Latin/numeric/comma runs that should stay Cambria text, not Thai text.
- `math`: editable OMML expressions.
- `table`: real Word tables, optionally with fixed column widths.
- `line_break`: explicit source-like breaks, used sparingly.

This separation made bugs easy to localize: transcription errors stayed in JSON, typography logic stayed in the builder, and audit failures stayed in XML checks.

### 16.2 Emit Decisions: Math, Thai Text, and Latin Text

Default for exam question bodies: lean toward OMML for math-ish tokens. This includes variables, expressions, equations, pure numeric answer choices, fractions, radicals, powers, subscripts, matrices, set notation, and statistics/probability values when they function as problem data.

Use `latin_text` when the user expects the visible run to be ordinary Cambria text, especially numeric/comma lists such as:

```json
{"type": "latin_text", "text": "123, 221, 112, "}
```

Keep variables inside those lists as math if they are conceptual variables:

```json
[
  {"type": "latin_text", "text": "123, 221, 112, "},
  {"type": "math", "kind": "plain", "value": "a"},
  {"type": "latin_text", "text": ", 124, 6"},
  {"type": "math", "kind": "plain", "value": "b"}
]
```

Do not let Thai prose accidentally enter generic math item arrays. The builder should fail fast when Thai codepoints appear inside ordinary math items. This caught the same class of bug as `z_1 และ z_2` being swallowed into one equation.

Thai inside OMML is allowed only when deliberately part of an equation layout, such as a future piecewise/cases row containing `เมื่อ`. In that case use an explicit node such as:

```json
{"kind": "thai_text", "text": " เมื่อ "}
```

and emit it as an OMML normal run with Word run properties:

- `w:rFonts ascii/hAnsi/cs = TH Sarabun New`
- `w:sz = 32`
- `w:szCs = 32`
- `<w:cs/>`
- `w:lang w:val="th-TH" w:bidi="th-TH"`

This is important because Thai inside an equation otherwise tends to render too small or route through the wrong font.

### 16.3 OMML Primitive Coverage From This Exam

The question set exercised these primitives successfully:

- `plain`: variables, numbers, short equations.
- `expr`: ordered mixed math items.
- `sup`, `sub`: powers and indices.
- `frac`: answer choices and algebraic expressions.
- `rad`: square roots and nth roots.
- `nary`: summation with upper/lower limits.
- `lim_low`: limits with lower annotations.
- `bar`: complex conjugates with top bar.
- `func`: upright function names.
- `delim` / `paren`: semantic delimiters.
- `cases`: future-ready piecewise/case layouts.
- `matrix`: editable `<m:m>` matrices wrapped in bracket delimiters.
- `thai_text`: deliberate Thai text inside equation structures.

Useful implementation details:

- Square-root OMML should include an explicit empty `<m:deg/>` with `degHide=on`; omitting the degree caused blank/placeholder rendering in LibreOffice sanity output.
- Known functions such as `sin`, `cos`, `tan`, `sec`, `cosec`/`csc`, `cot`, and `log` should be upright. Prefer `<m:func>` when the function has a real argument; for forms like `log_2 x`, avoid an empty `<m:func>` argument because it can render as an empty placeholder.
- Matrices should be editable `<m:m>` inside `<m:d>` delimiters, not plain text brackets. Cells should still use normal math item conversion so variables italicize and numbers/operators remain upright.
- Keep an explicit variable whitelist or classifier broad enough for common variables used in exams: `A`, `B`, `C`, `R`, `X`, `I`, `x`, `y`, `z`, `a`, `b`, `c`, `d`, `f`, `g`, `n`, `p`, `q`, `r`, `s`, `u`, `v`, `w`, `θ`.

### 16.4 Font Defaults and Imported DOCX Repair

The most important acceptance gate is not direct-run appearance; it is whether `docDefaults` and `Normal` survive Clear Formatting:

- `w:ascii = Cambria`
- `w:hAnsi = Cambria`
- `w:cs = TH Sarabun New`
- `w:sz = 24`
- `w:szCs = 32`
- `w:bidi = th-TH`

Imported or externally generated DOCX files can pass OMML/image audits but still fail this gate. In the solution-import phase, one answer file had valid OMML but failed font-default audit, proving that imported files need the same safety-net repair before assembly.

Skill upgrade recommendation: expose a first-class "repair Thai math DOCX defaults" operation that:

1. Runs `thai-font-normalize -i`.
2. Runs font-default audit.
3. Runs OMML audit if math exists.
4. Renders only after structural XML gates pass.

### 16.5 Audits That Paid For Themselves

Keep these as mandatory gates for generated or repaired exam DOCX:

- `thai-font-normalize --check`: catches missing Thai CS routing and theme/default problems.
- Font-default audit: specifically checks `docDefaults` and `Normal`, catching Clear Formatting failures.
- OMML audit: counts `m:oMath`, structure types, image elements for information,
  and Thai math runs. Image policy belongs to media QA.
- Thai-in-math audit: fail generic/unformatted Thai text inside `m:oMath`, but allow explicitly formatted `thai_text`.
- Latin insertion-safety audit: flag ordinary Thai body runs where direct `w:sz` is `32`; they should normally be `w:sz=24` and `w:szCs=32` so manually typed Latin after Thai inherits Cambria 12pt behavior.
- Render QA: catches layout collapse, page-count surprises, table wrapping, and LibreOffice-specific placeholder issues.

The OMML audit should report at least:

- `oMath`
- `fraction`
- `radical`
- `superscript`
- `subscript`
- `nary`
- `bar`
- `matrix`
- `delimiter`
- `image_count`
- `thai_math_run_count`

### 16.6 Layout Lessons

Do not overfit to the source PDF. The target is reusable Word typography that the user can inspect and edit.

However, the following layout controls were useful:

- Keep paragraph line spacing at single `1.0`.
- Keep question labels Thai-style: `TH Sarabun New 16pt` in all font slots.
- Use explicit `line_break` only when source-like line shape helps readability; remove unnecessary manual breaks if they create bad page breaks.
- Render to a fresh output folder per final pass, or stale `page-2.png` files from older renders can mislead page-count checks.
- Compact two-row statistical tables should support transcript-level `widths` in inches and the builder should write fixed table layout plus cell `w:tcW`; this avoids tall wrapping from auto-fit/equal-width tables.
- If a matrix expression is too long for a line, allow Word to wrap after nearby prose or before the matrix instead of shrinking Thai body text.

### 16.7 Recommended Skill Shape After This Project

Split the future skill into three layers:

1. `SKILL.md`: short operational workflow and acceptance gates.
2. `references/thai-math-docx-text.md`: typography, emit policy, OMML patterns, edge cases.
3. `scripts/`: reusable builder/audit/repair helpers.

Suggested scripts:

- `audit_docx_font_defaults.py`
- `audit_docx_omml.py`
- `fix_or_verify_thai_math_docx` wrapper that runs normalize + audits.
- Optional transcript validator that fails before build when:
  - Thai leaks into generic math items.
  - `latin_text` contains Thai.
  - table `widths` length does not match column count.
  - unsupported OMML kind appears.

### 16.8 Practical Heuristics For The Agent

When generating for this user:

- Treat Microsoft Word as the visual truth; render output is only structural QA.
- Be conservative about changing font sizes. Prefer better line breaks/table widths over shrinking Thai text.
- Remember that visible correctness is not enough: body Thai runs should be insertion-safe for future manual Latin typing, with Latin slot 12pt and CS slot 16pt.
- Keep equations editable even if a quick Unicode rendering would look passable.
- Fail loudly rather than silently using equation images.
- Preserve Western Latin routing; do not let Thai font normalization overwrite Cambria Latin slots.
- Update durable progress/knowledge notes whenever a new OMML primitive or failure mode is discovered.

## 17. Current Standard After The 2559-2566 Real-World Pass

This section is the compact standard distilled after producing all available 2559-2566 Science Week topic batches:

- set
- logic
- real numbers
- relations and functions
- exponential/logarithmic functions
- analytic geometry and conics
- trigonometry
- matrices
- vectors
- complex numbers
- counting and probability
- sequences and series
- calculus
- statistics

Use this section as the first checklist when starting a new Thai math DOCX task. The older sections remain useful for details and examples.

### 17.1 Product Standard

The deliverable is not just a visually similar DOCX. It is a reusable Microsoft Word math document:

- Thai text behaves like normal user-typed Thai Word text.
- Equations are editable OMML, not images.
- The file survives Clear Formatting, copy/paste into the user's documents, and Word PDF export.
- The source of truth is structured data plus deterministic generator code, not manual edits in Word.
- LibreOffice render is a structural smoke test only; Microsoft Word on the user's machine is the visual authority.

### 17.2 Canonical Batch Output

For exam-bank work, the final topic DOCX should contain both:

1. A questions-only section.
2. A repeated-questions-with-solutions section, where each solution repeats the original question before the explanation.

Build in batches of 3 questions by default. Each batch should add:

- question transcript JSON
- solution transcript JSON or deterministic solution data/functions
- source crops or page references
- final accumulated DOCX
- QA artifacts: font check, font-default audit, OMML audit, render output

If the final batch has fewer than 3 questions, build the remaining count exactly.

### 17.3 Transcript Standard

Every fragile PDF/image-to-DOCX reconstruction should use structured JSON before DOCX generation.

Required question fields:

- `number`
- `source_crops` or equivalent source page references
- `source_assets`
- `prompt`
- `choices`

Required `source_assets` shape:

```json
{
  "has_figure": false,
  "figure_redraw_needed": false,
  "figure_notes": ""
}
```

Set `has_figure=true` only when the original problem contains an actual figure, graph, or diagram that is part of the question. Do not draw figures during normal solution writing unless explicitly requested; flag them so they can be redrawn later.

Transcript part routing:

- `text`: Thai prose and Thai units.
- `latin_text`: ordinary Latin/numeric/comma text that should remain Cambria text.
- `math`: real math-ish content to emit as OMML.
- `table`: real Word table data, with optional fixed widths.
- `line_break`: source-like line breaks only when they help readability.

Keep Thai prose out of generic `math.items`. Thai inside OMML is allowed only through an explicit `thai_text` node with Thai Word run properties.

Do not make the transcript or database shape the builder API. Source files may be JSON, OCR, spreadsheet rows, database records, Markdown-ish snippets, or direct Python data. Normalize those sources first, then feed the builder the small part schema above.

### 17.4 Typography Standard

Use these values unless the user explicitly changes the house style:

- Body Thai: `TH Sarabun New`, 16 pt via Complex Script (`w:szCs=32`).
- Ordinary Thai body runs: Latin slot stays 12 pt (`w:sz=24`) and CS slot is 16 pt (`w:szCs=32`).
- Latin/admin text: `Cambria`, 12 pt (`w:sz=24`).
- Question labels and Thai choice labels: `TH Sarabun New` 16 pt in all font slots.
- Footer text and page fields: `TH Sarabun New` 12 pt throughout.
- Paragraph line spacing: single (`1.0`) unless a specific document says otherwise.

The insertion-safety rule is now mandatory: visible Thai 16 pt must not accidentally make manually typed Latin after the Thai run inherit 16 pt. This means ordinary Thai body runs should not use `w:sz=32`; keep `w:sz=24` and `w:szCs=32`.

### 17.5 Style Safety Net

Every generated or repaired Thai math DOCX must pass this exact `docDefaults` and `Normal` gate:

- `w:ascii = Cambria`
- `w:hAnsi = Cambria`
- `w:cs = TH Sarabun New`
- `w:sz = 24`
- `w:szCs = 32`
- `w:bidi = th-TH`

This is not optional. Direct formatting can look correct while Clear Formatting still fails if these defaults are wrong.

Imported DOCX files must be treated as repair targets even when their OMML is valid. Run the same normalize and audit sequence before assembling them with generated files.

### 17.6 OMML Standard

Prefer editable OMML for math-ish tokens in question bodies, choices, and solutions:

- variables
- function notation
- equation-relevant numbers
- set/logic/probability notation
- fractions, radicals, powers, subscripts, superscripts
- matrices, sums, limits, bars, delimiters
- vector accents

Operators must be tight OMML tokens. Do not emit literal preserved spaces around operators such as `=`, `∪`, `∩`, `+`, `−`, `<`, `≤`, `∈`, `∧`, `∨`, `↔`, `→`, or `:`.

Known functions such as `sin`, `cos`, `tan`, `sec`, `cosec`/`csc`, `cot`, `log`, and `ln` must be upright/roman. Avoid empty `<m:func>` arguments, especially for forms like `log_2 x`.

Square-root OMML should include the empty degree node plus `degHide=on`; omitting it caused placeholder/blank radical rendering during QA.

Matrices should be real editable `<m:m>` structures wrapped in OMML delimiters, not plain text brackets. The default builder behavior should produce bracketed matrices; use an explicit no-bracket option only when another structure supplies the delimiter, such as cases.

Summations and limits should use `<m:nary>` and `<m:limLow>` when limits are semantically attached.

Complex conjugates should use top bars. Vector notation should use OMML accents with the user's current vector preference: right harpoon above for general vectors and hat above for unit basis vectors `i`, `j`, and `k`.

```xml
<m:acc>
  <m:accPr><m:chr m:val="&#x20D1;"/></m:accPr>
  <m:e>...</m:e>
</m:acc>
```

Do not use the normal right arrow glyph `→` as the accent character. In Word it can render through the base letters like a strikethrough.

### 17.7 Layout Standard

Do not chase pixel-perfect PDF reconstruction. The standard is clean reusable Word typography.

Useful layout controls from the real-world pass:

- Use A4 with `2.54 cm` (`1 in`) margins on all sides by default. Treat this as
  the geometry used to calculate every fixed table width unless the teacher
  explicitly supplies another template.

- Use the current named student-table profile: `16 cm` for one column, or
  `8.5 cm × 2` only when the teacher explicitly requests an equal two-column
  layout. Keep `2.54 cm` margins and do not silently shrink that `17 cm` table.
  Unequal or mixed-role tables require an explicit task contract.

- Prefer transcript/table width controls over shrinking font size.
- Use fixed table layout and explicit column widths for compact statistical tables.
- Remove unnecessary manual line breaks if they create awkward page breaks.
- Use `line_break` deliberately when it improves readability or matches a source structure.
- Render to a fresh output folder every meaningful pass so stale page PNGs do not mislead QA.
- Let long matrix/vector expressions wrap naturally near prose boundaries instead of compressing Thai text.

### 17.8 QA Standard

Every generated or substantially repaired DOCX must run:

1. `thai-font-normalize -i`
2. `thai-font-normalize --check`
3. `audit_docx_font_defaults.py`
4. `audit_docx_insertion_safety.py`
5. `audit_docx_omml.py` for math documents
6. render to PDF/PNG for structural sanity when layout matters

Acceptance:

- normalize check OK
- font-default audit PASS
- OMML audit PASS
- `image_count=0`
- `oMath > 0` for math documents
- no generic/unformatted Thai inside OMML
- no spaced operator tokens in OMML
- no unsafe ordinary Thai body runs with `w:sz=32`
- render shows no tofu, collapsed tables, missing equations, stale pages, or broken headers/footers

Microsoft Word inspection remains the final visual gate.

### 17.9 Generator Standard

For new math-related generators, start from the latest shared pattern instead of retyping a minimal builder.

Keep three layers separate:

1. Source adapter / normalizer: turns JSON, OCR, database rows, Markdown-ish text, or direct Python data into builder-ready `parts`. Use `thai_math_source_adapter.py` for compact math-ish strings, legacy aliases, and matrix/table normalization.
2. Builder / insertion layer: uses `thai_math_docx_builder.py` for Thai body runs, Thai labels, Latin text runs, footer runs, tables, and OMML.
3. Post-build repair and QA: runs Thai font normalization, font-default audit, insertion-safety audit, OMML audit, and render sanity.

The shared builder should provide centralized OMML primitives for `plain`, `expr`, `sup`, `sub`, `sub_sup`, `frac`, `rad`, `nary`, `lim_low`, `bar`, `func`, `log`, `delim`, `matrix`, `cases`, `thai_text`, and `acc`. It should fail fast for unsupported math kinds and accidental Thai in generic math items.

Project-specific exam-bank metadata, answer-key IDs, page ranges, and batch policies belong in the source layer, not in the builder.

When a new failure mode appears, patch the correct layer first: source-shaped bugs belong in the adapter, insertion/OMML bugs belong in the builder, and Word behavior bugs belong in the normalizer/audits. Then rebuild affected files from source data.

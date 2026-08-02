# Thai OOXML Rules

The mandatory rules for writing `.docx` XML that renders Thai correctly. Target font in all
examples: **TH Sarabun New**, Complex Script size 16pt (`w:szCs="32"`).

## Core concept

Word stores two parallel font systems per run:

| Slot | XML attribute | Used for |
|---|---|---|
| Latin / Western | `w:ascii`, `w:hAnsi` | English, digits, Western punctuation |
| Complex Script (CS) | `w:cs` | Thai, Arabic, Hebrew |

Word picks the slot per character based on the character's Unicode script AND the run's
`<w:cs/>` toggle and language tags. Thai renders through `w:cs` **only if the run is explicitly
flagged as Complex Script.** Otherwise Word routes Thai through `w:ascii` and it falls back to the
Latin/theme font — historically Angsana New.

---

## RULE 1 — Every Thai run MUST have `<w:cs/>`

The single most important rule. `<w:cs/>` is an empty toggle inside `<w:rPr>` meaning "treat this
run as Complex Script."

**Correct:**
```xml
<w:r>
  <w:rPr>
    <w:rFonts w:ascii="TH Sarabun New" w:hAnsi="TH Sarabun New" w:cs="TH Sarabun New"/>
    <w:szCs w:val="32"/>
    <w:cs/>
  </w:rPr>
  <w:t>คำชี้แจง</w:t>
</w:r>
```

**Broken (missing `<w:cs/>`):** looks fine on first open, but Word treats it as English-script
text (status bar shows "English (United States)"). Applying a style or Clear Formatting then routes
Thai through the Latin slot → Angsana New.

For bold/italic Thai, also include `<w:bCs/>` / `<w:iCs/>` alongside `<w:b/>` / `<w:i/>`.

---

## RULE 2 — During generation, never put a Thai-only font in the Latin slots

Thai-only fonts: Angsana New, Cordia New, Browallia New, and all UPC fonts (AngsanaUPC, CordiaUPC,
DilleniaUPC, EucrosiaUPC, FreesiaUPC, IrisUPC, JasmineUPC, KodchiangUPC, LilyUPC). They have no
place in `w:ascii` / `w:hAnsi`.

**Never:**
```xml
<w:rFonts w:ascii="Angsana New" w:hAnsi="Angsana New" w:cs="Angsana New"/>
```

The repair script does not guess a replacement Latin font for existing documents. It fixes the Thai
Complex Script path (`w:cs`, Thai theme entries, Thai run toggles, `w:bidi`) and preserves
`w:ascii` / `w:hAnsi` unless the generator already set them explicitly.

---

## RULE 3 — Fix `docDefaults` in styles.xml

`<w:rPrDefault>` is what runs inherit when they specify no font. Its `w:cs` slot must be the Thai
font and the bidi language must be Thai.

**Correct:**
```xml
<w:docDefaults>
  <w:rPrDefault>
    <w:rPr>
      <w:rFonts w:ascii="Cambria" w:hAnsi="Cambria" w:cs="TH Sarabun New"/>
      <w:szCs w:val="32"/>
      <w:lang w:val="en-US" w:bidi="th-TH"/>
    </w:rPr>
  </w:rPrDefault>
</w:docDefaults>
```

- `w:cs="TH Sarabun New"` — never leave as Angsana New.
- `w:bidi="th-TH"` — makes inherited Thai route correctly.
- `w:szCs="32"` — 16pt default for Complex Script.

---

## RULE 4 — Fix the theme (theme1.xml)

Word's default theme maps Thai to Angsana New (in `<a:majorFont>`) and Cordia New (in
`<a:minorFont>`). This map is consulted by theme-linked styles (e.g. built-in headings via
`w:cstheme="majorBidi"`). Fix BOTH entries:

**Before:**
```xml
<a:font script="Thai" typeface="Angsana New"/>
<a:font script="Thai" typeface="Cordia New"/>
```

**After:**
```xml
<a:font script="Thai" typeface="TH Sarabun New"/>
<a:font script="Thai" typeface="TH Sarabun New"/>
```

Skipping this leaves headings falling back to Angsana New even when everything else is correct.

---

## RULE 5 — Do not mix Thai and Latin in one run

A run with both Thai letters and Latin digits/words can't be tagged as both scripts; Word forces
one. Split at script boundaries.

**Avoid:**
```xml
<w:r><w:rPr><w:cs/></w:rPr><w:t>จากตัวเลือก 1, 2, 3, 4 หรือ 5</w:t></w:r>
```

**Prefer:**
```xml
<w:r><w:rPr><w:rFonts w:cs="TH Sarabun New"/><w:cs/></w:rPr><w:t xml:space="preserve">จากตัวเลือก </w:t></w:r>
<w:r><w:rPr><w:rFonts w:ascii="Cambria" w:hAnsi="Cambria"/></w:rPr><w:t xml:space="preserve">1, 2, 3, 4 </w:t></w:r>
<w:r><w:rPr><w:rFonts w:cs="TH Sarabun New"/><w:cs/></w:rPr><w:t>หรือ 5</w:t></w:r>
```

(If having digits render in the Thai font alongside Thai is acceptable — typographically normal for
Thai documents — keeping them in the Thai run is fine. Just be consistent.)

---

## RULE 6 — Never emit non-font values into font attributes

A clear sign of a broken generator: CSS variables or template tokens leaking into font names.

**Never:**
```xml
<w:rFonts w:ascii="var(--s-heading)" w:hAnsi="var(--s-heading)"/>
```

`w:ascii` / `w:hAnsi` / `w:cs` must always be a real installed font name as a literal string.
Resolve any CSS variables to actual font names before writing OOXML. Unresolved tokens cause Word
to fall back to defaults (Angsana New for Thai).

---

## RULE 7 — Language tags must match the script

- Thai run: `<w:lang w:bidi="th-TH"/>` (paired with `<w:cs/>`)
- Latin run: `<w:lang w:val="en-US"/>` (no `<w:cs/>`)

Mismatches (Thai tagged purely `w:val="en-US"` with no bidi/CS) cause the "status bar says English
on Thai text" bug and the Angsana New fallback.

---

## Pre-emit self-check

1. Does every run containing Thai have `<w:cs/>` in its `<w:rPr>`?
2. Is `w:cs` in `docDefaults` the Thai font (not Angsana New)?
3. Are both `<a:font script="Thai" .../>` theme entries the Thai font?
4. Is `w:bidi="th-TH"` set in `docDefaults`?
5. Any Thai-only fonts in `w:ascii` / `w:hAnsi`? → remove.
6. Are Thai and Latin split into separate runs where they need different fonts?
7. Are all font attributes real font names (no `var(...)`, no placeholders)?

All seven passing = consistent Thai rendering in Word display, PDF export, after Clear Formatting,
and after applying paragraph styles. Then run `scripts/fix-thai-font --check file.docx`; the audit
must pass before delivery. If it fails, run `scripts/fix-thai-font -i file.docx` and audit again.

## Regression shape to remember

The classic broken document is internally contradictory:

- Direct formatting or a paragraph style may set `w:ascii` / `w:hAnsi` to TH Sarabun New, so Word's
  font picker and initial display can look correct.
- `w:cs`, `docDefaults`, or the Thai theme mapping still points to Angsana New or Cordia New.
- The Thai run is missing the `<w:cs/>` toggle or `w:bidi="th-TH"`.

That file can look like TH Sarabun New while editing, then fall back after Clear Formatting or route
through Angsana New during PDF export. The repair script is meant to remove all three contradictions,
not just replace visible font names.

## One-line summary

Put the Thai font in the `w:cs` slot, add an empty `<w:cs/>` toggle to every Thai-containing run,
set `w:cs` + `w:bidi="th-TH"` (+ `w:szCs="32"` for 16pt) in docDefaults, fix both Thai entries in
the theme, never place Thai-only fonts in the Latin slots, never emit CSS variables as font names,
and split runs at Thai/Latin boundaries.

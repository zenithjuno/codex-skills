# Thai drafts, budget figures and math (local addition)

Local to this machine; not part of upstream. Read it before a Thai draft, a page with budget numbers, or a page with formulas. Everything here was checked against the bundled CLI on 2026-10-10.

## Thai drafts

- Write `lang: th` in the frontmatter. Detection also finds Thai, but the tag makes it explicit.
- The page buttons stay in English (upstream has no Thai label set). That is expected, not a bug to fix here.
- The STE check segments Thai into words, so the sentence-length warning works: 25 words for a description, 20 for a step. Thai officialese runs long ("ได้รับการพิจารณา…และได้มีการ…"). Split it into short sentences, or a list, instead of ignoring the warning.
- Thai has no passive-voice or plain-word rules in the checker. Apply them yourself: prefer "คณะกรรมการอนุมัติ" over "ได้รับการอนุมัติจากคณะกรรมการ", and cut filler ("ในส่วนของ", "ได้มีการ", "ดำเนินการ" + verb).
- Saved file names may drop Thai vowel marks (ตัว → ต-ว). The page content is fine; give the user the path exactly as the `✓` line prints it.

## Budget figures

- **Never invent or estimate numbers.** Use only figures the user gave or that are in their files. Compute every total, remainder and percentage with a tool (a short Python call), not mentally, and say in the panel where the numbers came from (`meta="ที่มา: …"`).
- **`limits` rejects thousands separators.** Write `82000 / 100000 | บาท`, not `82,000 / 100,000`. The bar shows the raw number, so when exact figures matter add a table that shows them formatted (`82,000`).
- A row in `limits` turns red when the value passes the limit; add a 4th field as the note (`| เกินงบ`).
- Fiscal year: ปีงบประมาณ พ.ศ. runs 1 Oct – 30 Sep (ปีงบ 2570 = 1 ต.ค. 2569 – 30 ก.ย. 2570). Write years in พ.ศ. unless the user's source uses ค.ศ.
- There is no chart component. Do not hand-write SVG bar or pie charts unless the user asks; use `limits` for spent-vs-allocated and a table with a `%` column for shares.

| Budget question | Component |
|---|---|
| The verdict (over / under / needs a transfer) | `callout ok\|warn\|err` as the first panel |
| Spent or committed vs allocated, per category | `limits` |
| Line items with figures and status | Markdown table, status column `ok` / `warn` / `no` |
| แผนงาน → โครงการ → กิจกรรม breakdown | `tree` (`label \| amount`) |
| Quarterly disbursement plan, fiscal-year phases | `timeline` |
| Approval or procurement steps | `flow` |
| Project title block (ชื่อโครงการ, ผู้รับผิดชอบ, ปีงบ) | `kv` |
| A reallocation the user must decide | `ask`, suggested option marked `*` |

## Math

- Short expressions inside prose or tables: Unicode is enough (x², √, ×, ÷, ≤, ≥, ±, −).
- A display formula: put MathML in an ```` ```html ```` block. Browsers draw MathML natively, so the page stays offline and dependency-free. Keep it to the formulas that matter; MathML is verbose.

```html
<math display="block"><mi>x</mi><mo>=</mo><mfrac><mrow><mo>−</mo><mi>b</mi><mo>±</mo><msqrt><msup><mi>b</mi><mn>2</mn></msup><mo>−</mo><mn>4</mn><mi>a</mi><mi>c</mi></msqrt></mrow><mrow><mn>2</mn><mi>a</mi></mrow></mfrac></math>
```

- Do not load KaTeX or MathJax from a CDN: pages must open offline.

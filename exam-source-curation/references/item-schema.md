# Item Analysis and Taxonomy — Phases 1–3

## Phase 1 — transcribe and check

Per set, keep one audit note `source-audit/<SET>-review.md` with a heading
`## <item id>` per item containing: source location, transcription (stem,
choices, figure description), independent answer, short reasoning, confidence,
then — only after that is saved — the comparison with the source key.

`audit_status` values:

| Value | Meaning |
|---|---|
| `pass` | Answer and method agree (or blind check agrees when there is no key) |
| `flag-question` | Question is wrong, missing information, or has no / several valid choices |
| `flag-answer` | Source key gives a wrong answer |
| `flag-method` | Source answer is right but its method is wrong or misleading |
| `flag-ambiguous` | Readable in more than one valid way |
| `flag-reading` | The page itself cannot be read reliably |
| `unresolved` | Not yet checked |

A flag is never counted as a pass.

## Phase 2 — item record

One JSON object per line in `records/<SET>.jsonl`. Every field is required; no
`null`, and no generic text such as "ใช้สูตร" or "คิดวิเคราะห์" in place of an
item-specific reason.

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Item id from the inventory, matching the config pattern (for example `A67-Q09`) |
| `source_location` | list of strings | Pages or paragraphs holding the item and its figure, for example `["p11"]`, `["P0063"]` |
| `audit_ref` | string | Path from the project root to the audit note containing `## <id>` |
| `audit_status` | string | One value from the table above |
| `primary_topic` | string | One broad search label; may be a chapter name |
| `pattern_label` | string | The learner's main decision and the method that follows; narrower than `primary_topic`, reusable across sets, never named after one item's numbers or story |
| `core_decision` | string | The first non-obvious thing the learner must notice or choose |
| `method_signature` | string | 1–3 core steps of the method (calculation, reasoning, reading strategy); not a full solution |
| `supporting_topics` | list of strings | Other topics actually used, not merely present in the story |
| `prerequisites` | list of strings | Sub-skills needed first, in dependency order |
| `recognition_cue` | string | Word, condition, layout or figure that signals this method |
| `distinctive_feature` | string | How it differs from same-pattern items, or why it is representative |
| `likely_error` | string | A real misconception or slip for this item |
| `load` | object | `concept`, `procedure`, `reading` each 1–3, plus `reason` naming the highest dimension |
| `sequence_role` | string | `single-topic`, or `integrative` when it needs several topics taught in order |
| `candidate_signal` | object | `status` = `possible` / `uncertain` / `unsuitable`, with an item-specific `reason` |

Optional fields:

| Field | Meaning |
|---|---|
| `stimulus` | Shared stimulus group id (see source-intake) |
| `duplicate_of` | Earlier item id this item repeats; counted once |

A project may require extra fields through `extra_fields` in the config.

### Load scale

`procedure` covers calculation, multi-step execution or manipulation;
`reading` covers language, conditions, tables and figures.

- 1 — reachable after a short summary; short execution
- 2 — has a decision point or a manipulation that needs practice
- 3 — coordinates several patterns, heavy reading, or long execution

Never judge difficulty from how a formula or passage looks.

### Candidate signal

`candidate_signal` is a per-item screen, not the final selection:

- `possible` — all load dimensions ≤ 2, `audit_status` is `pass`, and the reason
  says what thinking the learner gains after a short foundation;
- `uncertain` — a dimension is 3, the source is flagged, or the teaching
  position is unclear; say what must be fixed or taught first;
- `unsuitable` — wrong for the course goal even after foundations; say why.

A load-3 item can still be a good late `integrative` choice. `possible` never
just means "the key is correct".

## Phase 3 — taxonomy

### Grouping test

Put two items in one **family** when the learner must **notice the same thing
first** and use the **same core method**, so that one short summary and one
bridge drill set can carry them in, even if numbers or contexts change.

Keep them apart when the learner must choose a different tool, needs a new
prerequisite, or the likely error calls for different teaching. Decide from
`core_decision`, `method_signature`, `prerequisites` and `likely_error`. Never
merge because `primary_topic` matches.

### Families and evidence

Agent labels are proposals. After all sets are analysed, the root merges labels
that mean the same pattern, then records families in `curation-state.json`:

```json
{"families": [
  {"id": "F01", "label": "ใช้หลักบวกลบแก้การนับซ้อนของสามเซต",
   "items": ["A68-Q29", "A69-Q02"], "supporting": ["C65-Q19"]}
]}
```

- `items` are canonical items from denominator sets; a family needs items from
  at least two distinct denominator sets after collapsing duplicates.
- `supporting` holds supplementary or non-denominator items that show the same
  method; they never change the count.
- An item belongs to at most one family. Everything else is evidence `single`,
  which means "no second set with the same decision and method", not "unimportant".

Run `families`, then paste the output of `table` into the taxonomy note. Also
list **similar but separate** pairs with the reason they were not merged; this
is what lets the teacher check the grouping.

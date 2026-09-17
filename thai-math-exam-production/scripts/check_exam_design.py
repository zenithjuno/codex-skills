#!/usr/bin/env python3
"""Fail an EXAM-DESIGN.md that is missing a Spine section (or, in parallel mode,
the source-critique spine), so the teacher-facing design note can always be
judged and approved.

Mirror of math-handout-sandbox/scripts/check_note_sections.py: the spec
(BLUEPRINT §2) tells an agent which sections the note must have; this check fails
the note when the agent forgot, so the structure survives a fresh session that
never read the spec. Only mechanical facts are checked — whether the *content* is
rich enough is the teacher's judgement, never a script's.

Mode: parallel notes must additionally carry `## Reference analysis` (with a
`### Equivalence diagnosis`) and `## Parallel contract` — the observe → diagnose →
recommend spine. The mode is read from the `## Contract` block (`Mode: parallel`)
unless given with --mode.

Usage:  python3 check_exam_design.py <EXAM-DESIGN.md> [more.md ...] [--mode original|parallel]
        python3 check_exam_design.py <GATE-6-BATCH-NN.md> --batch
        python3 check_exam_design.py <ANSWER-KEY.md> --answer-key
Exit 0 when the Spine is complete (REVIEW notes may still print), 1 when a Spine
section or the equivalence diagnosis is missing, 2 on a usage error.

`--batch` also enforces the workload arithmetic (Easy 1 · Medium 2 · Hard 3, 3–4
units unless an override reason is given) and, for anchored (parallel) items, the
embedded Reference A / Proposed B blocks. `--answer-key` checks that every item
block of a teacher-facing ANSWER-KEY.md is self-contained.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# A note without any of these cannot be argued or approved (BLUEPRINT §2).
SPINE = [
    "Contract",
    "Assessment purpose",
    "Source boundary",
    "Format and scoring",
    "Difficulty taxonomy",
    "Blueprint",
    "Item map",
    "Whole-paper acceptance",
    "Approval state",
]
# Added to the Spine in parallel mode: the source-critique spine.
PARALLEL_SPINE = ["Reference analysis", "Parallel contract"]

# Every heading that is a legitimate top-level section (Spine + parallel spine +
# Conditional + Opt-in). A `##` outside this set is a soft REVIEW.
KNOWN = set(SPINE) | set(PARALLEL_SPINE) | {
    "Batch workload policy", "Decisions", "Open questions",
}

HEADING = re.compile(r"^##[ \t]+(.+?)\s*$")
# Reference analysis, when present, must end with an equivalence diagnosis — the
# analytical heart that keeps the parallel set from mirroring the reference. Accept
# a Thai label carrying วินิจฉัย.
DIAGNOSIS = re.compile(r"^###[ \t]+(?:Equivalence diagnosis|.*วินิจฉัย)", re.M)
MODE_LINE = re.compile(r"Mode:\s*`?(original|parallel)`?", re.I)


# Batch-proposal structure (BLUEPRINT §7). The Workload line is the mechanical
# enforcement point for DEC-011 (batch workload is a template/review concern, not
# the JSON validator). Item blocks are freeform, so only the batch skeleton is
# checked, never per-item content.
BATCH_LINES = {
    "Status": re.compile(r"^`?Status", re.M),
    "Items": re.compile(r"^`?Items", re.M),
    "Workload": re.compile(r"^`?Workload", re.M),
}
BATCH_SECTIONS = ["Batch review notes"]
BATCH_DECISION = {"Decision requested", "Approved decision"}

# Workload arithmetic (teacher rule): Easy 1 · Medium 2 · Hard 3, 3–4 units per
# batch. A batch outside the band must say why on or right after the Workload line
# (override / exception / ข้อยกเว้น). A wrong weight such as `Hard 4` is always a FAIL.
WORKLOAD_WEIGHTS = {"easy": 1, "medium": 2, "hard": 3}
WORKLOAD_BAND = (3, 4)
WORKLOAD_LINE = re.compile(r"^`?Workload[^:\n]*:`?\s*`?([^`\n]*)`?\s*$", re.M)
WORKLOAD_TERM = re.compile(r"(Easy|Medium|Hard)\s*(\d+)", re.I)
WORKLOAD_TOTAL = re.compile(r"=\s*(\d+)")
WORKLOAD_OVERRIDE = re.compile(r"override|exception|ข้อยกเว้น", re.I)

# Parallel batches embed both papers per item so the teacher judges equivalence
# from one file: a `### ชุดอ้างอิง A` (or `### Reference A`) block and a
# `### ชุดคู่ขนาน B` (or `### Proposed B`) block, each carrying a key and a solution.
ANCHOR_LINE = re.compile(r"\*\*Item anchor:\*\*|^Item anchor:", re.M)
REFERENCE_A = re.compile(r"^###\s+(?:ชุดอ้างอิง A|Reference A)\b", re.M)
PROPOSED_B = re.compile(r"^###\s+(?:ชุดคู่ขนาน B|Proposed B)\b", re.M)
KEY_MARK = re.compile(r"\*\*เฉลย[^*]*:\*\*|\*\*Answer[^*]*:\*\*")
SOLUTION_MARK = re.compile(r"วิธีทำ|working solution|เหตุผล", re.I)

# Answer-key structure (assets/ANSWER-KEY.template.md): one `## Q01`/`## W01`
# block per item with question, answer, solution, and a rubric for written items.
KEY_ITEM = re.compile(r"^##\s+(Q\d{2}|W\d{2})\s*$", re.M)
KEY_QUESTION = re.compile(r"^###\s+โจทย์และตัวเลือก", re.M)
KEY_SOLUTION = re.compile(r"^###\s+เฉลยและวิธีทำ", re.M)
KEY_ANSWER = re.compile(r"\*\*คำตอบ:\*\*")
KEY_RUBRIC = re.compile(r"^####\s+(?:Scoring rubric|เกณฑ์ให้คะแนน)", re.M)
KEY_CHOICE = re.compile(r"(?:^|\s)([ก-ง])\.\s", re.M)  # one per line or inline ก. … ข. …
KEY_EQUATION_REF = re.compile(r"สมการนี้")


def check_workload(text: str) -> list[tuple[str, str]]:
    """FAIL a Workload line whose weights or arithmetic break the teacher rule."""
    match = WORKLOAD_LINE.search(text)
    if not match:
        return []  # the missing-line FAIL is reported by scan_batch
    line = match.group(1)
    terms = WORKLOAD_TERM.findall(line)
    issues: list[tuple[str, str]] = []
    if not terms:
        return [("FAIL", f"Workload line has no `Easy n`/`Medium n`/`Hard n` terms: {line.strip()}")]
    total = 0
    for level, weight in terms:
        expected = WORKLOAD_WEIGHTS[level.lower()]
        if int(weight) != expected:
            issues.append(("FAIL", f"Workload weight {level} {weight} — rule is {level} {expected}"))
        total += int(weight)
    declared = WORKLOAD_TOTAL.search(line)
    if declared and int(declared.group(1)) != total:
        issues.append(("FAIL", f"Workload total says {declared.group(1)} but terms sum to {total}"))
    low, high = WORKLOAD_BAND
    if not low <= total <= high:
        # The excuse must be the batch's own words: the Workload line or the plain
        # paragraph right after it. Template guidance (`>` blockquotes) and the
        # next heading do not count.
        following: list[str] = []
        for raw in text[match.end():].splitlines():
            stripped = raw.strip()
            if not stripped:
                if following:
                    break
                continue
            if stripped.startswith(("#", ">", "<!--", "---")):
                break
            following.append(stripped)
            if len(following) >= 3:
                break
        if not (WORKLOAD_OVERRIDE.search(line) or WORKLOAD_OVERRIDE.search(" ".join(following))):
            issues.append(("FAIL", f"Workload {total} is outside {low}–{high} units with no override/exception reason "
                                   "on or right after the Workload line"))
    return issues


def item_blocks(text: str) -> list[tuple[str, str]]:
    """[(heading, body)] for every `## ` section, in order."""
    blocks: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            blocks.append((match.group(1), []))
        elif blocks:
            blocks[-1][1].append(line)
    return [(head, "\n".join(body)) for head, body in blocks]


def check_parallel_blocks(text: str) -> list[tuple[str, str]]:
    """In a parallel batch every anchored item must show Reference A and Proposed B
    side by side, each with its key and solution — the teacher decides from one file."""
    issues: list[tuple[str, str]] = []
    for head, body in item_blocks(text):
        if head in set(BATCH_SECTIONS) | BATCH_DECISION or not ANCHOR_LINE.search(body):
            continue
        has_a, has_b = REFERENCE_A.search(body), PROPOSED_B.search(body)
        if not has_a:
            issues.append(("FAIL", f"{head}: anchored item lacks a `### ชุดอ้างอิง A` / `### Reference A` block"))
        if not has_b:
            issues.append(("FAIL", f"{head}: anchored item lacks a `### ชุดคู่ขนาน B` / `### Proposed B` block"))
        if has_a and has_b:
            if len(KEY_MARK.findall(body)) < 2:
                issues.append(("FAIL", f"{head}: both A and B blocks need an **เฉลย…:** line"))
            if len(SOLUTION_MARK.findall(body)) < 2:
                issues.append(("FAIL", f"{head}: both A and B blocks need a วิธีทำ / working solution"))
    return issues


def scan_answer_key(path: Path) -> list[tuple[str, str]]:
    """Check an ANSWER-KEY.md is self-contained per item: question (+ choices for
    objective items), answer, solution, and a rubric for written items."""
    text = path.read_text(encoding="utf-8")
    issues: list[tuple[str, str]] = []
    heads = KEY_ITEM.findall(text)
    if not heads:
        return [("FAIL", "no item blocks found (expected `## Q01` … `## W01`)")]
    blocks = [(h, b) for h, b in item_blocks(text) if KEY_ITEM.match(f"## {h}")]
    for head, body in blocks:
        if not KEY_QUESTION.search(body):
            issues.append(("FAIL", f"{head}: missing `### โจทย์และตัวเลือก`"))
        if not KEY_SOLUTION.search(body):
            issues.append(("FAIL", f"{head}: missing `### เฉลยและวิธีทำ`"))
        if not KEY_ANSWER.search(body):
            issues.append(("FAIL", f"{head}: missing `**คำตอบ:**`"))
        question = body.split("### เฉลยและวิธีทำ", 1)[0]
        if head.startswith("Q") and len(set(KEY_CHOICE.findall(question))) < 4:
            issues.append(("FAIL", f"{head}: objective item needs four choices ก.–ง. in โจทย์และตัวเลือก"))
        if head.startswith("W") and not KEY_RUBRIC.search(body):
            issues.append(("FAIL", f"{head}: written item needs `#### Scoring rubric` (or เกณฑ์ให้คะแนน)"))
        if KEY_EQUATION_REF.search(question) and "=" not in question:
            issues.append(("FAIL", f"{head}: stem says “สมการนี้” but states no equation with `=`"))
    q_count = sum(1 for h in heads if h.startswith("Q"))
    w_count = sum(1 for h in heads if h.startswith("W"))
    issues.append(("INFO", f"{q_count} objective + {w_count} written item block(s)"))
    return issues


def section_headings(text: str) -> list[str]:
    """Top-level (`## `) headings, in order; deeper `###`/`####` are ignored."""
    return [m.group(1) for line in text.splitlines()
            for m in (HEADING.match(line),) if m]


def detect_mode(text: str) -> str:
    match = MODE_LINE.search(text)
    return match.group(1).lower() if match else "original"


def scan(path: Path, mode: str | None) -> list[tuple[str, str]]:
    """Return [(severity, message)]. severity in {'FAIL', 'REVIEW'}."""
    text = path.read_text(encoding="utf-8")
    resolved_mode = mode or detect_mode(text)
    heads = section_headings(text)
    present = set(heads)
    issues: list[tuple[str, str]] = []

    required = list(SPINE)
    if resolved_mode == "parallel":
        required += PARALLEL_SPINE
    for name in required:
        if name not in present:
            issues.append(("FAIL", f"missing Spine section: ## {name}"))

    if "Reference analysis" in present and not DIAGNOSIS.search(text):
        issues.append(("FAIL", "## Reference analysis must contain a `### Equivalence diagnosis` "
                               "(where the difficulty could drift, not a per-item note)"))

    if resolved_mode == "original":
        for name in PARALLEL_SPINE:
            if name in present:
                issues.append(("REVIEW", f"## {name} in an original-mode note — parallel section left over?"))

    for name in heads:
        if name not in KNOWN:
            issues.append(("REVIEW", f"unrecognized section — an Opt-in or a stray heading?: ## {name}"))
    return issues


def scan_batch(path: Path) -> list[tuple[str, str]]:
    """Check a BATCH-PROPOSAL.md skeleton (BLUEPRINT §7). Only the batch frame is
    mechanical: the Status/Items/Workload header lines, at least one item block, a
    Batch review section, and a decision section. Per-item quality is a teacher
    judgement."""
    text = path.read_text(encoding="utf-8")
    heads = section_headings(text)
    present = set(heads)
    issues: list[tuple[str, str]] = []
    for name, pattern in BATCH_LINES.items():
        if not pattern.search(text):
            issues.append(("FAIL", f"missing batch header line: {name}:"))
    for name in BATCH_SECTIONS:
        if name not in present:
            issues.append(("FAIL", f"missing section: ## {name}"))
    if not (present & BATCH_DECISION):
        issues.append(("FAIL", "missing a decision section: ## Decision requested or ## Approved decision"))
    item_heads = [h for h in heads if h not in set(BATCH_SECTIONS) | BATCH_DECISION]
    if not item_heads:
        issues.append(("FAIL", "no item block found (expected at least one `## <ITEM_ID> — ...`)"))
    issues.extend(check_workload(text))
    issues.extend(check_parallel_blocks(text))
    return issues


def main(argv: list[str]) -> int:
    mode: str | None = None
    kind = "design"
    files: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--mode":
            index += 1
            if index >= len(argv) or argv[index] not in {"original", "parallel"}:
                print("usage: --mode original|parallel", file=sys.stderr)
                return 2
            mode = argv[index]
        elif arg == "--batch":
            kind = "batch"
        elif arg == "--answer-key":
            kind = "answer-key"
        else:
            files.append(arg)
        index += 1
    if not files:
        print("usage: check_exam_design.py <file.md> [more.md ...] [--mode original|parallel] "
              "[--batch | --answer-key]", file=sys.stderr)
        return 2

    scanners = {"design": lambda p: scan(p, mode), "batch": scan_batch, "answer-key": scan_answer_key}
    labels = {"design": ("Spine", "EXAM-DESIGN.template.md"),
              "batch": ("batch skeleton", "BATCH-PROPOSAL.template.md"),
              "answer-key": ("answer-key structure", "ANSWER-KEY.template.md")}
    failures = 0
    for name in files:
        path = Path(name)
        if not path.is_file():
            print(f"BLOCKED: not a file: {path}", file=sys.stderr)
            return 2
        for severity, message in scanners[kind](path):
            print(f"{path} [{severity}] {message}")
            if severity == "FAIL":
                failures += 1
    what, template = labels[kind]
    if failures:
        print(f"\nFAIL: {failures} {what} violation(s). See assets/{template} for the expected structure.")
        return 1
    print(f"PASS: {what} complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

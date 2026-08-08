#!/usr/bin/env python3
"""Reusable material patterns above the Thai math builder and layout layers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm

import thai_math_docx_builder as builder
import thai_math_docx_layout as layout


class UnsupportedCapabilityError(RuntimeError):
    """Visible failure carrying a candidate record for the work-batch review."""

    def __init__(self, capability: str, reason: str, candidate: Mapping[str, Any]):
        super().__init__(
            f"Unsupported capability {capability!r}: {reason}. "
            "Record the attached candidate and run the relevant QA review; do not approximate."
        )
        self.capability = capability
        self.candidate = dict(candidate)


@dataclass(frozen=True)
class ReviewedExpertExtension:
    name: str
    review_reference: str
    candidate_id: str
    handler: Callable[[Any, Mapping[str, Any]], Any]

    def apply(self, target: Any, request: Mapping[str, Any]) -> dict[str, Any]:
        if not self.review_reference.strip() or not self.candidate_id.strip():
            raise ValueError("expert extensions require a review_reference and candidate_id")
        return {
            "result": self.handler(target, request),
            "expert_extension": self.name,
            "review_reference": self.review_reference,
            "candidate_id": self.candidate_id,
            "needs_qa_review": True,
        }


@dataclass(frozen=True)
class MediaBlock:
    source_path: str | Path
    media_kind: str
    width_cm: float
    editable_source_path: str | Path | None = None
    contains_equations: bool = False


def _validate_parts(parts: Sequence[Mapping[str, Any]], field: str) -> None:
    for part in parts:
        if part.get("type") == "table":
            raise ValueError(f"{field} cannot contain a nested table part")


def add_question_grid(
    document: Any,
    questions: Sequence[Mapping[str, Any]],
    *,
    columns: int = 1,
    cell_margins_twips: Mapping[str, int] | None = None,
) -> Any:
    """Add a fixed, borderless row-major question grid using current profiles."""
    if columns not in (1, 2):
        raise UnsupportedCapabilityError(
            "question-grid-columns",
            f"current shared pattern supports 1 or explicit equal 2 columns, got {columns}",
            {"capability": "question-grid-columns", "requested_columns": columns},
        )
    if not questions:
        raise ValueError("questions must not be empty")
    for question in questions:
        if "number" not in question or "prompt_parts" not in question:
            raise ValueError("every question requires number and prompt_parts")
        _validate_parts(question["prompt_parts"], "prompt_parts")

    row_count = (len(questions) + columns - 1) // columns
    table = document.add_table(rows=row_count, cols=columns)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    profile = "one-column" if columns == 1 else "explicit-equal-two-column"
    layout.apply_student_table_width_profile(table, profile)
    margins = dict(cell_margins_twips or {"top": 70, "start": 100, "bottom": 70, "end": 100})

    for index in range(row_count * columns):
        cell = table.cell(index // columns, index % columns)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
        layout.clear_cell_borders(cell)
        layout.set_cell_margins(cell, **margins)
        paragraph = cell.paragraphs[0]
        builder.configure_paragraph(paragraph, space_after=0)
        if index >= len(questions):
            continue
        question = questions[index]
        label = paragraph.add_run(f"ข้อ {question['number']}. ")
        builder.set_thai_label_run(label, bold=True)
        builder.append_parts(paragraph, list(question["prompt_parts"]))
        if question.get("response_lines"):
            layout.add_dotted_response_lines(
                cell,
                count=int(question["response_lines"]),
                dots=int(question.get("response_dots", 60)),
            )
    return table


def add_worked_example(
    document: Any,
    *,
    title: str,
    prompt_parts: Sequence[Mapping[str, Any]],
    steps: Sequence[Sequence[Mapping[str, Any]]],
    heading_fill: str = "EAF4F8",
) -> Any:
    """Add one current 16 cm worked-example box with semantic prompt and steps."""
    _validate_parts(prompt_parts, "prompt_parts")
    if not steps:
        raise ValueError("worked example requires at least one step")
    for step in steps:
        _validate_parts(step, "steps")
    table = document.add_table(rows=2, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    layout.apply_student_table_width_profile(table, "one-column")
    layout.set_cell_shading(table.cell(0, 0), heading_fill)
    layout.set_cell_margins(table.cell(0, 0), top=70, start=120, bottom=70, end=120)
    layout.set_cell_margins(table.cell(1, 0), top=90, start=120, bottom=90, end=120)

    heading = table.cell(0, 0).paragraphs[0]
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    builder.configure_paragraph(heading, space_after=0)
    builder.set_thai_label_run(heading.add_run(title), bold=True)

    body = table.cell(1, 0)
    prompt = body.paragraphs[0]
    builder.configure_paragraph(prompt, space_after=4)
    builder.append_parts(prompt, list(prompt_parts))
    for number, step in enumerate(steps, start=1):
        paragraph = body.add_paragraph()
        builder.configure_paragraph(paragraph, space_after=2)
        builder.set_thai_label_run(paragraph.add_run(f"ขั้นที่ {number}  "), bold=True)
        builder.append_parts(paragraph, list(step))
    return table


def add_response_area(
    container: Any,
    *,
    label: str | None = None,
    line_count: int = 3,
    dots: int = 80,
) -> list[Any]:
    if label:
        paragraph = container.add_paragraph()
        builder.configure_paragraph(paragraph, space_after=0)
        builder.set_thai_label_run(paragraph.add_run(label), bold=True)
    return layout.add_dotted_response_lines(container, count=line_count, dots=dots)


def add_media_block(
    container: Any,
    block: MediaBlock,
    *,
    expert_extension: ReviewedExpertExtension | None = None,
) -> dict[str, Any]:
    """Insert an approved media block or fail with a reviewable candidate."""
    source = Path(block.source_path)
    if block.width_cm <= 0:
        raise ValueError("media width_cm must be greater than zero")
    if block.contains_equations:
        raise UnsupportedCapabilityError(
            "equation-inside-media",
            "equations must remain editable OMML rather than image content",
            {"capability": "equation-inside-media", "source_path": str(source)},
        )
    if not source.is_file():
        raise FileNotFoundError(f"media source does not exist: {source}")
    if block.media_kind == "png-answer-visual":
        if source.suffix.lower() != ".png" or not block.editable_source_path:
            raise ValueError("PNG answer visuals require a .png plus editable_source_path")
        editable_source = Path(block.editable_source_path)
        if not editable_source.is_file():
            raise FileNotFoundError(f"editable media source does not exist: {editable_source}")
        paragraph = container.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run()
        run.add_picture(str(source), width=Cm(block.width_cm))
        return {
            "media_kind": block.media_kind,
            "source_path": str(source),
            "editable_source_path": str(editable_source),
            "needs_qa_review": True,
        }
    if block.media_kind == "svg-editable":
        if source.suffix.lower() != ".svg":
            raise ValueError("svg-editable media requires an .svg source")
        if expert_extension is None:
            raise UnsupportedCapabilityError(
                "svg-word-insertion",
                "the current python-docx path has no reviewed native SVG package inserter",
                {
                    "capability": "svg-word-insertion",
                    "source_path": str(source),
                    "required_policy": "keep editable SVG source; never rasterize silently",
                },
            )
        return expert_extension.apply(container, {"block": block})
    raise UnsupportedCapabilityError(
        "media-kind",
        f"unknown media kind {block.media_kind!r}",
        {"capability": "media-kind", "requested_kind": block.media_kind},
    )

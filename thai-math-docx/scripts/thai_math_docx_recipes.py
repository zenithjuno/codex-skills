#!/usr/bin/env python3
"""Thin family recipes assembled only from shared builder and pattern APIs."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import thai_math_docx_builder as builder
import thai_math_docx_patterns as patterns


def build_handout(
    *,
    title: str,
    introduction_parts: Sequence[Mapping[str, Any]],
    worked_examples: Sequence[Mapping[str, Any]],
    practice_questions: Sequence[Mapping[str, Any]],
    practice_columns: int = 1,
) -> Any:
    document = builder.new_document()
    builder.add_heading(document, title)
    builder.add_paragraph(document, list(introduction_parts), space_after=6)
    for example in worked_examples:
        patterns.add_worked_example(document, **example)
    if practice_questions:
        builder.add_heading(document, "แบบฝึกหัด")
        patterns.add_question_grid(document, practice_questions, columns=practice_columns)
    return document


def build_exam_paper(
    *,
    title: str,
    instruction_parts: Sequence[Mapping[str, Any]],
    objective_questions: Sequence[Mapping[str, Any]],
    written_questions: Sequence[Mapping[str, Any]],
    objective_columns: int = 1,
) -> Any:
    document = builder.new_document()
    builder.add_heading(document, title)
    builder.add_paragraph(document, list(instruction_parts), space_after=6)
    if objective_questions:
        builder.add_heading(document, "ตอนที่ 1  ปรนัย")
        patterns.add_question_grid(document, objective_questions, columns=objective_columns)
    if written_questions:
        builder.add_heading(document, "ตอนที่ 2  อัตนัย")
        for question in written_questions:
            builder.add_question_block(
                document,
                int(question["number"]),
                list(question["prompt_parts"]),
                space_after=0,
            )
            patterns.add_response_area(
                document,
                line_count=int(question.get("response_lines", 3)),
                dots=int(question.get("response_dots", 80)),
            )
    return document


def build_answer_key(
    *,
    title: str,
    answers: Sequence[Mapping[str, Any]],
) -> Any:
    document = builder.new_document()
    builder.add_heading(document, title)
    for answer in answers:
        paragraph = document.add_paragraph()
        builder.configure_paragraph(paragraph, space_after=2)
        builder.set_thai_label_run(
            paragraph.add_run(f"ข้อ {answer['number']}. "),
            bold=True,
        )
        builder.append_parts(paragraph, list(answer["answer_parts"]))
        for step in answer.get("explanation_steps", []):
            explanation = document.add_paragraph()
            builder.configure_paragraph(explanation, space_after=2)
            builder.append_parts(explanation, list(step))
    return document

#!/usr/bin/env python3
"""Reusable material patterns above the Thai math builder and layout layers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.part import Part
from docx.shared import Cm, Pt

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


def _svg_aspect_ratio(source: Path) -> float:
    root = ET.fromstring(source.read_bytes())
    view_box = root.get("viewBox")
    if view_box:
        values = [float(value) for value in re.split(r"[\s,]+", view_box.strip())]
        if len(values) == 4 and values[2] > 0 and values[3] > 0:
            return values[2] / values[3]

    def numeric_dimension(name: str) -> float | None:
        value = root.get(name)
        if not value:
            return None
        match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(?:px|pt|pc|mm|cm|in)?\s*", value)
        return float(match.group(1)) if match else None

    width = numeric_dimension("width")
    height = numeric_dimension("height")
    if width and height and width > 0 and height > 0:
        return width / height
    raise ValueError(f"SVG requires a positive viewBox or numeric width and height: {source}")


def add_svg_picture(
    container: Any,
    source_path: str | Path,
    *,
    width_cm: float,
    alt_text: str | None = None,
) -> Any:
    """Embed an SVG package part as a centered inline Word picture."""
    source = Path(source_path)
    if source.suffix.lower() != ".svg" or not source.is_file():
        raise ValueError(f"SVG source must be an existing .svg file: {source}")
    if width_cm <= 0:
        raise ValueError("SVG width_cm must be greater than zero")

    paragraph = container.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    package = paragraph.part.package
    svg_part = Part(
        package.next_partname("/word/media/image%d.svg"),
        "image/svg+xml",
        source.read_bytes(),
        package,
    )
    relationship_id = paragraph.part.relate_to(svg_part, RT.IMAGE)

    doc_pr_ids = [
        int(node.get("id", "0"))
        for node in paragraph.part.element.iter(qn("wp:docPr"))
        if node.get("id", "0").isdigit()
    ]
    drawing_id = max(doc_pr_ids, default=0) + 1
    width_emu = int(Cm(width_cm))
    height_emu = round(width_emu / _svg_aspect_ratio(source))
    safe_name = escape(source.name, {'"': "&quot;"})
    safe_description = escape(alt_text or source.stem, {'"': "&quot;"})

    drawing = parse_xml(
        f"""
        <w:drawing xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
          xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
          xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
          xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
          <wp:inline distT="0" distB="0" distL="0" distR="0">
            <wp:extent cx="{width_emu}" cy="{height_emu}"/>
            <wp:effectExtent l="0" t="0" r="0" b="0"/>
            <wp:docPr id="{drawing_id}" name="{safe_name}" descr="{safe_description}"/>
            <wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>
            <a:graphic>
              <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:pic>
                  <pic:nvPicPr>
                    <pic:cNvPr id="0" name="{safe_name}"/>
                    <pic:cNvPicPr/>
                  </pic:nvPicPr>
                  <pic:blipFill>
                    <a:blip r:embed="{relationship_id}"/>
                    <a:stretch><a:fillRect/></a:stretch>
                  </pic:blipFill>
                  <pic:spPr>
                    <a:xfrm>
                      <a:off x="0" y="0"/>
                      <a:ext cx="{width_emu}" cy="{height_emu}"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                    <a:noFill/>
                    <a:ln><a:noFill/></a:ln>
                  </pic:spPr>
                </pic:pic>
              </a:graphicData>
            </a:graphic>
          </wp:inline>
        </w:drawing>
        """
    )
    paragraph.add_run()._r.append(drawing)
    return paragraph


def _validate_parts(parts: Sequence[Mapping[str, Any]], field: str) -> None:
    for part in parts:
        if part.get("type") == "table":
            raise ValueError(f"{field} cannot contain a nested table part")


def add_synthetic_division(
    container: Any,
    *,
    root: Any,
    coefficients: Sequence[Any],
    products: Sequence[Any],
    results: Sequence[Any],
    total_width_cm: float = 16.0,
    root_width_cm: float = 1.65,
    border_size: int = 12,
) -> Any:
    """Add editable synthetic division in the approved traditional layout.

    The products omit the empty slot beneath the brought-down leading
    coefficient. All supplied values are emitted as editable Word equations.
    """
    coefficient_count = len(coefficients)
    if coefficient_count < 2:
        raise ValueError("coefficients must contain at least two values")
    if len(products) != coefficient_count - 1:
        raise ValueError(f"products must contain {coefficient_count - 1} values")
    if len(results) != coefficient_count:
        raise ValueError(f"results must contain {coefficient_count} values")
    if total_width_cm <= 0 or root_width_cm <= 0 or root_width_cm >= total_width_cm:
        raise ValueError("widths must satisfy 0 < root_width_cm < total_width_cm")
    if border_size <= 0:
        raise ValueError("border_size must be greater than zero")

    table = container.add_table(rows=3, cols=coefficient_count + 1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    value_width = (total_width_cm - root_width_cm) / coefficient_count
    layout.set_table_fixed_widths_cm(table, [root_width_cm] + [value_width] * coefficient_count)

    for row_index, row in enumerate(table.rows):
        row_properties = row._tr.get_or_add_trPr()
        if row_properties.find(qn("w:cantSplit")) is None:
            row_properties.append(parse_xml('<w:cantSplit xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'))
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            layout.clear_cell_borders(cell)
            layout.set_cell_margins(cell, top=30, start=45, bottom=30, end=45)
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            builder.configure_paragraph(paragraph, space_after=0)
            paragraph.paragraph_format.keep_with_next = row_index < 2

    def append_editable_value(row: int, column: int, value: Any) -> None:
        builder.append_parts(table.cell(row, column).paragraphs[0], [{"type": "math", "expr": value}])

    append_editable_value(0, 0, root)
    for column, value in enumerate(coefficients, start=1):
        append_editable_value(0, column, value)
    for column, value in enumerate(products, start=2):
        append_editable_value(1, column, value)
    for column, value in enumerate(results, start=1):
        append_editable_value(2, column, value)

    for row in (0, 1):
        layout.set_cell_borders(table.cell(row, 0), right={"size": border_size})
    for column in range(1, coefficient_count + 1):
        layout.set_cell_borders(table.cell(2, column), top={"size": border_size})
    return table


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
        if expert_extension is not None:
            return expert_extension.apply(container, {"block": block})
        add_svg_picture(
            container,
            source,
            width_cm=block.width_cm,
            alt_text=source.stem,
        )
        return {
            "media_kind": block.media_kind,
            "source_path": str(source),
            "needs_qa_review": True,
        }
    raise UnsupportedCapabilityError(
        "media-kind",
        f"unknown media kind {block.media_kind!r}",
        {"capability": "media-kind", "requested_kind": block.media_kind},
    )


HEADING_PRESETS: dict[str, dict[str, Any]] = {
    "section_heading": {
        "fill": "D9EAD3",
        "text_color": "1B4D2E",
        "size_pt": 19,
        "borders": {
            "top": {"val": "single", "sz": 6, "space": 4, "color": "6AA84F"},
            "left": {"val": "single", "sz": 48, "space": 8, "color": "6AA84F"},
            "bottom": {"val": "single", "sz": 6, "space": 4, "color": "6AA84F"},
            "right": {"val": "single", "sz": 6, "space": 8, "color": "6AA84F"},
        },
        "left_ind": 80,
    },
    "sub_heading": {
        "fill": "F4F9F4",
        "text_color": "235733",
        "size_pt": 18,
        "borders": {
            "top": {"val": "dashed", "sz": 6, "space": 4, "color": "4E8B5A"},
            "left": {"val": "single", "sz": 48, "space": 8, "color": "4E8B5A"},
            "bottom": {"val": "dashed", "sz": 6, "space": 4, "color": "4E8B5A"},
            "right": {"val": "dashed", "sz": 6, "space": 8, "color": "4E8B5A"},
        },
        "left_ind": 80,
    },
    "exercise_banner": {
        "fill": "F7E6EF",
        "text_color": "7A284E",
        "size_pt": 18,
        "borders": {
            "top": {"val": "single", "sz": 4, "space": 4, "color": "E6BDD0"},
            "left": {"val": "single", "sz": 24, "space": 8, "color": "B85582"},
            "bottom": {"val": "single", "sz": 4, "space": 4, "color": "E6BDD0"},
            "right": {"val": "single", "sz": 4, "space": 8, "color": "E6BDD0"},
        },
        "left_ind": 100,
    },
}

CALLOUT_PRESETS: dict[str, dict[str, Any]] = {
    "definition": {
        "rows": 2,
        "header_fill": "3B7A57",
        "header_text_color": "FFFFFF",
        "body_fill": "F2F7F2",
        "border_color": "B7D5B9",
    },
    "theorem": {
        "rows": 2,
        "header_fill": "B85582",
        "header_text_color": "FFFFFF",
        "body_fill": "FDF2F7",
        "border_color": "E6BDD0",
    },
    "property": {
        "rows": 2,
        "header_fill": "3E6B99",
        "header_text_color": "FFFFFF",
        "body_fill": "F1F6FB",
        "border_color": "BDD1E6",
    },
    "caution": {
        "rows": 1,
        "accent_color": "D97706",
        "title_color": "9A5200",
        "body_fill": "FFF8EB",
        "border_color": "F3D08A",
    },
    "funfact": {
        "rows": 1,
        "accent_color": "2A7B76",
        "title_color": "1D5B57",
        "body_fill": "F0F9F8",
        "border_color": "B2DAD7",
    },
    "note": {
        "rows": 1,
        "accent_color": "5C6F82",
        "title_color": "374757",
        "body_fill": "F5F7FA",
        "border_color": "CDD6E0",
    },
    "strategy": {
        "rows": 1,
        "accent_color": "6E52B5",
        "title_color": "4D348C",
        "body_fill": "F6F3FC",
        "border_color": "D5C8F0",
    },
}


def _apply_run_color(paragraph: Any, hex_color: str) -> None:
    ns_w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    for r in paragraph._p.findall(f"{{{ns_w}}}r"):
        rPr = r.find(f"{{{ns_w}}}rPr")
        if rPr is None:
            rPr = parse_xml(f'<w:rPr xmlns:w="{ns_w}"/>')
            r.insert(0, rPr)
        old = rPr.find(f"{{{ns_w}}}color")
        if old is not None:
            rPr.remove(old)
        rPr.append(parse_xml(f'<w:color xmlns:w="{ns_w}" w:val="{hex_color}"/>'))


def _set_paragraph_shading_and_borders(
    paragraph: Any,
    *,
    fill: str | None,
    borders: Mapping[str, Mapping[str, Any]],
    left_ind: int = 80,
) -> None:
    ns_w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    pPr = paragraph._p.get_or_add_pPr()
    for tag in ("pBdr", "shd", "ind"):
        old = pPr.find(f"{{{ns_w}}}{tag}")
        if old is not None:
            pPr.remove(old)
    if borders:
        parts = []
        for side in ("top", "left", "bottom", "right"):
            spec = borders.get(side)
            if spec:
                parts.append(
                    f'<w:{side} w:val="{spec.get("val", "single")}" '
                    f'w:sz="{spec.get("sz", 6)}" '
                    f'w:space="{spec.get("space", 4)}" '
                    f'w:color="{spec.get("color", "6AA84F")}"/>'
                )
        pPr.append(parse_xml(f'<w:pBdr xmlns:w="{ns_w}">{"".join(parts)}</w:pBdr>'))
    if fill:
        pPr.append(
            parse_xml(f'<w:shd xmlns:w="{ns_w}" w:val="clear" w:color="auto" w:fill="{fill}"/>')
        )
    if left_ind:
        pPr.append(parse_xml(f'<w:ind xmlns:w="{ns_w}" w:left="{left_ind}"/>'))


ICON_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "icons"


def _prepend_inline_icon(
    paragraph: Any,
    icon_name: str,
    *,
    size_cm: float = 0.48,
    vshift_pt: float = -2.0,
) -> bool:
    """Prepend a bundled inline PNG icon (rendered from SVG source) before paragraph runs."""
    icon_path = ICON_ASSETS_DIR / f"{icon_name}.png"
    if not icon_path.is_file():
        return False
    ns_w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    run_icon = paragraph.add_run()
    run_icon.add_picture(str(icon_path), width=Cm(size_cm))
    rPr = run_icon._r.get_or_add_rPr()
    pos = parse_xml(f'<w:position xmlns:w="{ns_w}" w:val="{int(round(vshift_pt * 2))}"/>')
    rPr.append(pos)
    run_sp = paragraph.add_run("  ")
    p_el = paragraph._p
    pPr = p_el.find(f"{{{ns_w}}}pPr")
    insert_at = 1 if pPr is not None else 0
    p_el.remove(run_icon._r)
    p_el.remove(run_sp._r)
    p_el.insert(insert_at, run_icon._r)
    p_el.insert(insert_at + 1, run_sp._r)
    return True


def add_styled_heading(
    container: Any,
    text_or_parts: str | Sequence[Mapping[str, Any]],
    *,
    kind: str = "section_heading",
    page_break_before: bool = False,
    keep_next: bool = True,
    space_before: int = 6,
    space_after: int = 6,
    icon: bool | None = None,
) -> Any:
    """Add a border+shading heading paragraph (no floating shape) using a named preset."""
    if kind not in HEADING_PRESETS:
        raise ValueError(f"unknown heading kind {kind!r}; expected one of {sorted(HEADING_PRESETS)}")
    preset = HEADING_PRESETS[kind]
    paragraph = container.add_paragraph()
    builder.configure_paragraph(paragraph, space_after=space_after)
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.keep_with_next = keep_next
    paragraph.paragraph_format.page_break_before = page_break_before

    if isinstance(text_or_parts, str):
        builder.set_thai_label_run(paragraph.add_run(text_or_parts), bold=True, size=preset["size_pt"])
    else:
        builder.append_parts(paragraph, list(text_or_parts))
    _apply_run_color(paragraph, preset["text_color"])
    use_icon = (kind == "exercise_banner") if icon is None else icon
    if use_icon:
        _prepend_inline_icon(paragraph, kind, size_cm=0.52)
    _set_paragraph_shading_and_borders(
        paragraph,
        fill=preset["fill"],
        borders=preset["borders"],
        left_ind=preset["left_ind"],
    )
    return paragraph


def add_callout_box(
    container: Any,
    kind: str,
    title: str | Sequence[Mapping[str, Any]],
    body_paragraphs: Sequence[Sequence[Mapping[str, Any]]],
    *,
    total_width_cm: float = 17.0,
    icon: bool = True,
) -> Any:
    """Add a 1-column callout table (2-row header-band or 1-row left-accent) with cantSplit."""
    if kind not in CALLOUT_PRESETS:
        raise ValueError(f"unknown callout kind {kind!r}; expected one of {sorted(CALLOUT_PRESETS)}")
    preset = CALLOUT_PRESETS[kind]
    ns_w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    row_count = preset["rows"]
    table = container.add_table(rows=row_count, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    layout.set_table_fixed_widths_cm(table, [total_width_cm])

    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        if trPr.find(f"{{{ns_w}}}cantSplit") is None:
            trPr.append(parse_xml(f'<w:cantSplit xmlns:w="{ns_w}"/>'))

    if row_count == 2:
        border_col = preset["border_color"]
        hdr_cell = table.cell(0, 0)
        body_cell = table.cell(1, 0)
        layout.set_cell_shading(hdr_cell, preset["header_fill"])
        layout.set_cell_margins(hdr_cell, top=55, start=150, bottom=55, end=150)
        layout.set_cell_borders(
            hdr_cell,
            top={"style": "single", "size": 6, "color": border_col},
            left={"style": "single", "size": 6, "color": border_col},
            right={"style": "single", "size": 6, "color": border_col},
            bottom={"style": "single", "size": 4, "color": border_col},
        )
        p_hdr = hdr_cell.paragraphs[0]
        builder.configure_paragraph(p_hdr, space_after=0)
        p_hdr.paragraph_format.keep_with_next = True
        if isinstance(title, str):
            builder.set_thai_label_run(p_hdr.add_run(title), bold=True, size=17)
        else:
            builder.append_parts(p_hdr, list(title))
        _apply_run_color(p_hdr, preset["header_text_color"])
        if icon:
            _prepend_inline_icon(p_hdr, kind, size_cm=0.48)

        layout.set_cell_shading(body_cell, preset["body_fill"])
        layout.set_cell_margins(body_cell, top=90, start=160, bottom=90, end=150)
        layout.set_cell_borders(
            body_cell,
            top={"style": "single", "size": 4, "color": border_col},
            left={"style": "single", "size": 6, "color": border_col},
            right={"style": "single", "size": 6, "color": border_col},
            bottom={"style": "single", "size": 6, "color": border_col},
        )
        for idx, parts in enumerate(body_paragraphs):
            p = body_cell.paragraphs[0] if idx == 0 else body_cell.add_paragraph()
            builder.configure_paragraph(p, space_after=2 if idx < len(body_paragraphs) - 1 else 0)
            builder.append_parts(p, list(parts))
    else:
        cell = table.cell(0, 0)
        border_col = preset["border_color"]
        layout.set_cell_shading(cell, preset["body_fill"])
        layout.set_cell_margins(cell, top=90, start=160, bottom=90, end=150)
        layout.set_cell_borders(
            cell,
            top={"style": "single", "size": 4, "color": border_col},
            left={"style": "single", "size": 24, "color": preset["accent_color"]},
            right={"style": "single", "size": 4, "color": border_col},
            bottom={"style": "single", "size": 4, "color": border_col},
        )
        p_title = cell.paragraphs[0]
        builder.configure_paragraph(p_title, space_after=2)
        if isinstance(title, str):
            builder.set_thai_label_run(p_title.add_run(title), bold=True, size=17)
        else:
            builder.append_parts(p_title, list(title))
        _apply_run_color(p_title, preset["title_color"])
        if icon:
            _prepend_inline_icon(p_title, kind, size_cm=0.48)

        for idx, parts in enumerate(body_paragraphs):
            p = cell.add_paragraph()
            builder.configure_paragraph(p, space_after=2 if idx < len(body_paragraphs) - 1 else 0)
            builder.append_parts(p, list(parts))

    return table

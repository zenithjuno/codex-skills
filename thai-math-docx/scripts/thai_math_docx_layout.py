#!/usr/bin/env python3
"""Shared, unit-explicit layout primitives for Thai mathematics DOCX files."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


TWIPS_PER_INCH = 1440
CM_PER_INCH = 2.54
DEFAULT_PROFILE_PATH = Path(__file__).resolve().parents[1] / "references/layout-profiles.json"
CELL_BORDER_EDGES = ("top", "left", "bottom", "right", "insideH", "insideV")


@dataclass(frozen=True)
class BorderSpec:
    """Semantic Word border description; ``None`` means an explicit nil border."""

    color: str = "auto"
    size: int = 8
    style: str = "single"
    space: int = 0


def _ensure_child(parent: Any, tag: str) -> Any:
    child = parent.find(qn(tag))
    if child is None:
        child = OxmlElement(tag)
        parent.append(child)
    return child


def _cm_to_twips(value_cm: float) -> int:
    if value_cm <= 0:
        raise ValueError("widths must be greater than zero")
    return int(round(value_cm / CM_PER_INCH * TWIPS_PER_INCH))


def load_layout_profiles(path: str | Path = DEFAULT_PROFILE_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_current_layout_profile(
    use_case: str,
    path: str | Path = DEFAULT_PROFILE_PATH,
) -> dict[str, Any]:
    profiles = [
        profile
        for profile in load_layout_profiles(path)["profiles"]
        if profile["use_case"] == use_case and profile["status"] == "current"
    ]
    if len(profiles) != 1:
        raise ValueError(f"expected exactly one current profile for {use_case!r}, found {len(profiles)}")
    return profiles[0]


def set_cell_margins(
    cell: Any,
    *,
    top: int,
    start: int,
    bottom: int,
    end: int,
) -> None:
    """Set cell margins in twips using logical start/end sides."""
    values = {"top": top, "start": start, "bottom": bottom, "end": end}
    if any(value < 0 for value in values.values()):
        raise ValueError("cell margins cannot be negative")
    tc_mar = _ensure_child(cell._tc.get_or_add_tcPr(), "w:tcMar")
    for side, value in values.items():
        node = _ensure_child(tc_mar, f"w:{side}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_borders(cell: Any, **edges: BorderSpec | Mapping[str, Any] | None) -> None:
    """Set selected cell borders; pass ``None`` to explicitly clear an edge."""
    unknown = set(edges) - set(CELL_BORDER_EDGES)
    if unknown:
        raise ValueError(f"unsupported cell border edges: {sorted(unknown)}")
    borders = _ensure_child(cell._tc.get_or_add_tcPr(), "w:tcBorders")
    for edge, raw_spec in edges.items():
        node = _ensure_child(borders, f"w:{edge}")
        if raw_spec is None:
            node.attrib.clear()
            node.set(qn("w:val"), "nil")
            continue
        spec = raw_spec if isinstance(raw_spec, BorderSpec) else BorderSpec(**raw_spec)
        node.attrib.clear()
        node.set(qn("w:val"), spec.style)
        node.set(qn("w:sz"), str(spec.size))
        node.set(qn("w:color"), spec.color)
        node.set(qn("w:space"), str(spec.space))


def clear_cell_borders(cell: Any, edges: tuple[str, ...] = CELL_BORDER_EDGES) -> None:
    set_cell_borders(cell, **{edge: None for edge in edges})


def set_cell_shading(cell: Any, fill: str, *, pattern: str = "clear", color: str = "auto") -> None:
    if not fill:
        raise ValueError("fill must be a Word color value")
    shading = _ensure_child(cell._tc.get_or_add_tcPr(), "w:shd")
    shading.set(qn("w:fill"), fill)
    shading.set(qn("w:val"), pattern)
    shading.set(qn("w:color"), color)


def set_repeat_table_header(row: Any, repeat: bool = True) -> None:
    header = _ensure_child(row._tr.get_or_add_trPr(), "w:tblHeader")
    header.set(qn("w:val"), "true" if repeat else "false")


def equal_widths_cm(total_width_cm: float, column_count: int) -> list[float]:
    if total_width_cm <= 0:
        raise ValueError("total_width_cm must be greater than zero")
    if column_count < 1:
        raise ValueError("column_count must be at least 1")
    return [total_width_cm / column_count] * column_count


def set_table_fixed_widths_cm(table: Any, widths_cm: list[float]) -> None:
    """Emit fixed table grid, total width and merged-cell-aware cell widths."""
    if not widths_cm:
        raise ValueError("widths_cm must contain at least one width")
    widths_twips = [_cm_to_twips(width) for width in widths_cm]
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    _ensure_child(tbl_pr, "w:tblLayout").set(qn("w:type"), "fixed")
    tbl_w = _ensure_child(tbl_pr, "w:tblW")
    tbl_w.set(qn("w:type"), "dxa")
    tbl_w.set(qn("w:w"), str(sum(widths_twips)))

    for old_grid in tbl.findall(qn("w:tblGrid")):
        tbl.remove(old_grid)
    grid = OxmlElement("w:tblGrid")
    for width_twips in widths_twips:
        column = OxmlElement("w:gridCol")
        column.set(qn("w:w"), str(width_twips))
        grid.append(column)
    tbl.insert(1, grid)

    for row in table.rows:
        grid_index = 0
        for tc in row._tr.tc_lst:
            span = int(tc.grid_span or 1)
            if grid_index + span > len(widths_twips):
                raise ValueError("table row spans more grid columns than widths_cm defines")
            tc_w = _ensure_child(tc.get_or_add_tcPr(), "w:tcW")
            tc_w.set(qn("w:w"), str(sum(widths_twips[grid_index : grid_index + span])))
            tc_w.set(qn("w:type"), "dxa")
            grid_index += span
        if grid_index != len(widths_twips):
            raise ValueError("table row has fewer grid columns than widths_cm defines")


def apply_student_table_width_profile(table: Any, layout: str) -> list[float]:
    profile = get_current_layout_profile("student-question-layout")
    try:
        widths_cm = profile["table_widths_cm"][layout]
    except KeyError as exc:
        raise ValueError(f"unsupported student table layout: {layout!r}") from exc
    set_table_fixed_widths_cm(table, widths_cm)
    return list(widths_cm)


def set_section_columns(section: Any, count: int, *, gap_twips: int, separator: bool = False) -> None:
    if count < 1:
        raise ValueError("column count must be at least 1")
    if gap_twips < 0:
        raise ValueError("column gap cannot be negative")
    cols = _ensure_child(section._sectPr, "w:cols")
    cols.set(qn("w:space"), str(gap_twips))
    if count == 1:
        cols.attrib.pop(qn("w:num"), None)
    else:
        cols.set(qn("w:num"), str(count))
    if separator:
        cols.set(qn("w:sep"), "true")
    else:
        cols.attrib.pop(qn("w:sep"), None)


def apply_section_profile(section: Any, profile: Mapping[str, Any]) -> None:
    page = profile["page"]
    section.page_width = Cm(page["width_cm"])
    section.page_height = Cm(page["height_cm"])
    margins = page["margins_cm"]
    section.top_margin = Cm(margins["top"])
    section.bottom_margin = Cm(margins["bottom"])
    section.left_margin = Cm(margins["left"])
    section.right_margin = Cm(margins["right"])
    columns = profile["columns"]
    set_section_columns(
        section,
        columns["count"],
        gap_twips=columns["gap_twips"],
        separator=columns.get("separator", False),
    )


def add_section_transition(
    document: Any,
    profile: Mapping[str, Any],
    *,
    start: WD_SECTION_START = WD_SECTION_START.CONTINUOUS,
) -> Any:
    section = document.add_section(start)
    apply_section_profile(section, profile)
    return section


def add_dotted_response_lines(
    container: Any,
    *,
    count: int = 1,
    dots: int = 80,
    space_after_pt: float = 0,
    line_spacing: float = 1.15,
) -> list[Any]:
    """Add literal-period response lines in the approved Thai 16 pt style."""
    if count < 1 or dots < 1:
        raise ValueError("count and dots must be at least 1")
    paragraphs = []
    for _ in range(count):
        paragraph = container.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(space_after_pt)
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        paragraph.paragraph_format.line_spacing = line_spacing
        run = paragraph.add_run("." * dots)
        run.font.name = "TH Sarabun New"
        run.font.size = Pt(16)
        r_pr = run._r.get_or_add_rPr()
        r_fonts = _ensure_child(r_pr, "w:rFonts")
        for slot in ("w:ascii", "w:hAnsi", "w:cs"):
            r_fonts.set(qn(slot), "TH Sarabun New")
        _ensure_child(r_pr, "w:sz").set(qn("w:val"), "32")
        _ensure_child(r_pr, "w:szCs").set(qn("w:val"), "32")
        if r_pr.find(qn("w:cs")) is None:
            r_pr.append(OxmlElement("w:cs"))
        language = _ensure_child(r_pr, "w:lang")
        language.set(qn("w:val"), "th-TH")
        language.set(qn("w:bidi"), "th-TH")
        paragraphs.append(paragraph)
    return paragraphs

#!/usr/bin/env python3
"""Unified generic DOCX QA core for Thai mathematics working drafts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import posixpath
import shutil
from typing import Any, Mapping
import zipfile
from xml.etree import ElementTree as ET

from docx import Document

import audit_docx_font_defaults as font_defaults
import audit_docx_insertion_safety as insertion_safety
import audit_docx_omml as omml_audit
import thai_math_docx_builder as builder


SCHEMA_VERSION = "1.0.0"
LAYOUT_MODES = {"standard-a4", "fixed-table", "native-columns", "custom-template"}
MEDIA_MODES = {"none", "svg-editable", "png-golden", "mixed"}
SOURCE_MODES = {"generated", "imported", "teacher-master"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
THAI_FONT = "TH Sarabun New"
REQUIRED_PACKAGE_PARTS = {"[Content_Types].xml", "word/document.xml", "word/styles.xml"}


class ContractError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        # No contract means the ordinary case: a document this toolchain just
        # generated, carrying maths and no media. The rare cases — an imported
        # or teacher-master file, embedded media, a deliberately maths-free
        # sheet — declare themselves with a contract. The previous default
        # assumed the worst case instead, which raised a Word-review flag on
        # every generated file (noise that stopped being read) while leaving
        # `math.required` false, so a handout whose equations all went missing
        # still passed.
        raw: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "layout": "standard-a4",
            "media": "none",
            "source_mode": "generated",
            "math": {"required": True},
        }
    else:
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(f"cannot read QA contract: {exc}") from exc
    return normalize_contract(raw)


def normalize_contract(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a contract supplied by a CLI file or Python caller."""
    if not isinstance(raw, dict):
        raise ContractError("QA contract root must be an object")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {SCHEMA_VERSION!r}")

    def axis(name: str, allowed: set[str]) -> dict[str, Any]:
        value = raw.get(name)
        if isinstance(value, str):
            normalized = {"mode": value}
        elif isinstance(value, Mapping):
            normalized = dict(value)
        else:
            raise ContractError(f"{name} must be a string or object")
        mode = normalized.get("mode")
        if mode not in allowed:
            raise ContractError(f"{name}.mode must be one of {sorted(allowed)}, got {mode!r}")
        return normalized

    source_mode = raw.get("source_mode")
    if source_mode not in SOURCE_MODES:
        raise ContractError(
            f"source_mode must be one of {sorted(SOURCE_MODES)}, got {source_mode!r}"
        )
    media_axis = axis("media", MEDIA_MODES)
    media_defaults = {
        "none": {"role": "none", "editability": "none", "embedding_policy": "embedded", "expected_count": {"min": 0, "max": 0}},
        "svg-editable": {"role": "diagram", "editability": "package-editable", "embedding_policy": "embedded", "expected_count": {"min": 1}},
        "png-golden": {"role": "answer-visual", "editability": "editable-source-required", "embedding_policy": "embedded", "expected_count": {"min": 1}},
        "mixed": {"role": "unknown", "editability": "review-only", "embedding_policy": "embedded", "expected_count": {"min": 0}},
    }[media_axis["mode"]]
    for key, value in media_defaults.items():
        media_axis.setdefault(key, value)
    expected_count = media_axis.get("expected_count")
    if not isinstance(expected_count, Mapping):
        raise ContractError("media.expected_count must be an object")
    for bound in ("min", "max"):
        if bound in expected_count and (
            not isinstance(expected_count[bound], int)
            or isinstance(expected_count[bound], bool)
            or expected_count[bound] < 0
        ):
            raise ContractError(f"media.expected_count.{bound} must be a non-negative integer")
    editable_sources = media_axis.get("editable_source_paths", [])
    if not isinstance(editable_sources, list) or any(not isinstance(item, str) for item in editable_sources):
        raise ContractError("media.editable_source_paths must be an array of paths")
    math_contract = raw.get("math") or {"required": False}
    if not isinstance(math_contract, Mapping) or not isinstance(math_contract.get("required", False), bool):
        raise ContractError("math.required must be boolean")
    return {
        "schema_version": SCHEMA_VERSION,
        "layout": axis("layout", LAYOUT_MODES),
        "media": media_axis,
        "source_mode": source_mode,
        "math": dict(math_contract),
    }


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    status: str,
    summary: str,
    **metrics: Any,
) -> None:
    checks.append({"id": check_id, "status": status, "summary": summary, "metrics": metrics})


def _word_roots(roots: Mapping[str, ET.Element]) -> list[tuple[str, ET.Element]]:
    return [
        (name, root)
        for name, root in roots.items()
        if name == "word/document.xml" or name.startswith("word/header") or name.startswith("word/footer")
    ]


def _text(element: ET.Element) -> str:
    return "".join(element.itertext())


def _has_thai(text: str) -> bool:
    return any("\u0e00" <= character <= "\u0e7f" for character in text)


def _parse_package(path: Path) -> tuple[dict[str, ET.Element], list[str], list[str], set[str]]:
    roots: dict[str, ET.Element] = {}
    failures: list[str] = []
    media: list[str] = []
    package_parts: set[str] = set()
    if not zipfile.is_zipfile(path):
        return roots, ["not a valid ZIP/DOCX package"], media, package_parts
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                failures.append(f"ZIP CRC failure in {bad_member}")
            package_parts = set(archive.namelist())
            for missing in sorted(REQUIRED_PACKAGE_PARTS - package_parts):
                failures.append(f"required package part missing: {missing}")
            media = sorted(name for name in package_parts if name.startswith("word/media/") and not name.endswith("/"))
            for name in sorted(package_parts):
                if not (name.endswith(".xml") or name.endswith(".rels")):
                    continue
                try:
                    roots[name] = ET.fromstring(archive.read(name))
                except (ET.ParseError, KeyError) as exc:
                    failures.append(f"invalid XML in {name}: {exc}")
    except (OSError, zipfile.BadZipFile) as exc:
        failures.append(f"cannot read DOCX package: {exc}")
    return roots, failures, media, package_parts


def _audit_fonts(
    roots: Mapping[str, ET.Element],
    path: Path,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    styles = roots.get("word/styles.xml")
    if styles is None:
        return ["word/styles.xml is unavailable"], {}
    doc_defaults = styles.find("w:docDefaults/w:rPrDefault/w:rPr", font_defaults.NS)
    normal = styles.find(
        "w:style[@w:type='paragraph'][@w:styleId='Normal']/w:rPr",
        font_defaults.NS,
    )
    failures.extend(
        font_defaults.audit_block(
            "docDefaults", font_defaults.extract_run_props(doc_defaults)
        )
    )
    failures.extend(
        font_defaults.audit_block("Normal", font_defaults.extract_run_props(normal))
    )
    failures.extend(insertion_safety.audit_docx(path))
    theme_fonts: list[str] = []
    for name, root in roots.items():
        if not (name.startswith("word/theme/") and name.endswith(".xml")):
            continue
        for node in root.findall(f".//{A}font"):
            if node.get("script") == "Thai":
                theme_fonts.append(node.get("typeface", ""))
    if not theme_fonts:
        failures.append("Thai theme font mapping is missing")
    elif any(font != THAI_FONT for font in theme_fonts):
        failures.append(f"Thai theme font mapping must be {THAI_FONT!r}, got {theme_fonts!r}")
    return failures, {"thai_theme_fonts": theme_fonts}


def _audit_omml(
    roots: Mapping[str, ET.Element],
    contract: Mapping[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    math_count = 0
    unformatted: list[str] = []
    for name, root in _word_roots(roots):
        math_count += len(root.findall(f".//{M}oMath"))
        for run in root.findall(f".//{M}oMath//{M}r"):
            text = _text(run)
            if _has_thai(text) and not omml_audit.has_explicit_thai_math_format(run):
                unformatted.append(f"{name}: {_text(run).strip()[:60]!r}")
    if contract["math"].get("required") and math_count == 0:
        failures.append("contract requires editable OMML but no m:oMath was found")
    failures.extend(
        f"Thai inside generic/unformatted math run: {item}" for item in unformatted
    )
    return failures, {"oMath_count": math_count, "unformatted_thai_math": unformatted}


def _audit_geometry_and_tables(
    roots: Mapping[str, ET.Element],
    layout_contract: Mapping[str, Any],
) -> tuple[list[str], list[str], dict[str, Any]]:
    failures: list[str] = []
    reviews: list[str] = []
    document = roots.get("word/document.xml")
    if document is None:
        return ["word/document.xml is unavailable"], reviews, {}
    sections = document.findall(f".//{W}sectPr")
    section_metrics = []
    for section in sections:
        size = section.find(f"{W}pgSz")
        margins = section.find(f"{W}pgMar")
        columns = section.find(f"{W}cols")
        section_metrics.append(
            {
                "width_twips": size.get(f"{W}w") if size is not None else None,
                "height_twips": size.get(f"{W}h") if size is not None else None,
                "margins_twips": {
                    side: margins.get(f"{W}{side}") if margins is not None else None
                    for side in ("top", "right", "bottom", "left")
                },
                "columns": int(columns.get(f"{W}num", "1")) if columns is not None else 1,
                "column_gap_twips": columns.get(f"{W}space") if columns is not None else None,
            }
        )

    mode = layout_contract["mode"]
    if mode == "standard-a4":
        if not section_metrics:
            failures.append("standard-a4 requires at least one section")
        for index, section in enumerate(section_metrics, start=1):
            width = section["width_twips"]
            height = section["height_twips"]
            if width is None or abs(int(width) - 11906) > 30:
                failures.append(f"section {index} is not A4 width: {width!r} twips")
            if height is None or abs(int(height) - 16838) > 30:
                failures.append(f"section {index} is not A4 height: {height!r} twips")
            for side, value in section["margins_twips"].items():
                if value is None or abs(int(value) - 1440) > 2:
                    failures.append(f"section {index} {side} margin must be 1440 twips, got {value!r}")
    elif mode == "native-columns":
        if not any(section["columns"] >= 2 for section in section_metrics):
            failures.append("native-columns contract requires a section with at least two Word columns")
    elif mode == "custom-template":
        reviews.append("custom-template geometry requires representative Microsoft Word review")

    tables = document.findall(f".//{W}tbl")
    table_metrics: list[dict[str, Any]] = []
    for table_index, table in enumerate(tables, start=1):
        grid = table.find(f"{W}tblGrid")
        grid_columns = grid.findall(f"{W}gridCol") if grid is not None else []
        layout = table.find(f"{W}tblPr/{W}tblLayout")
        fixed = layout is not None and layout.get(f"{W}type") == "fixed"
        row_shapes: list[int] = []
        for row in table.findall(f"{W}tr"):
            occupied = 0
            for cell in row.findall(f"{W}tc"):
                span = cell.find(f"{W}tcPr/{W}gridSpan")
                occupied += int(span.get(f"{W}val", "1")) if span is not None else 1
                width = cell.find(f"{W}tcPr/{W}tcW")
                if mode == "fixed-table" and width is None:
                    failures.append(f"table {table_index} has a cell without explicit w:tcW")
            row_shapes.append(occupied)
            if grid_columns and occupied != len(grid_columns):
                failures.append(
                    f"table {table_index} row occupies {occupied} grid columns; expected {len(grid_columns)}"
                )
        if mode == "fixed-table" and (not fixed or not grid_columns):
            failures.append(f"table {table_index} lacks fixed layout or explicit table grid")
        table_metrics.append(
            {
                "table_index": table_index,
                "fixed": fixed,
                "grid_columns": len(grid_columns),
                "row_grid_shapes": row_shapes,
            }
        )
    if mode == "fixed-table" and not tables:
        failures.append("fixed-table contract requires at least one Word table")
    return failures, reviews, {"sections": section_metrics, "tables": table_metrics}


def _source_part_for_relationships_part(relationships_part: str) -> str | None:
    path = PurePosixPath(relationships_part)
    if path.parent.name != "_rels" or not path.name.endswith(".rels"):
        return None
    return str(path.parent.parent / path.name.removesuffix(".rels"))


def _resolve_relationship_target(source_part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(str(PurePosixPath(source_part).parent), target))


def _audit_media(
    media_paths: list[str],
    media_contract: Mapping[str, Any],
    roots: Mapping[str, ET.Element],
    package_parts: set[str],
) -> tuple[list[str], list[str], dict[str, Any]]:
    failures: list[str] = []
    reviews: list[str] = []
    extensions = [Path(path).suffix.lower().lstrip(".") for path in media_paths]
    counts = {extension: extensions.count(extension) for extension in sorted(set(extensions))}
    mode = media_contract["mode"]
    defaults = {
        "none": {"role": "none", "editability": "none", "embedding_policy": "embedded"},
        "svg-editable": {"role": "diagram", "editability": "package-editable", "embedding_policy": "embedded"},
        "png-golden": {"role": "answer-visual", "editability": "editable-source-required", "embedding_policy": "embedded"},
        "mixed": {"role": "unknown", "editability": "review-only", "embedding_policy": "embedded"},
    }[mode]
    role = str(media_contract.get("role", defaults["role"]))
    editability = str(media_contract.get("editability", defaults["editability"]))
    embedding_policy = str(media_contract.get("embedding_policy", defaults["embedding_policy"]))
    external_image_links = []
    internal_image_relationships = []
    broken_image_relationships = []
    for name, root in roots.items():
        if not name.endswith(".rels"):
            continue
        source_part = _source_part_for_relationships_part(name)
        for relationship in root.findall(f".//{REL}Relationship"):
            if not relationship.get("Type", "").endswith("/image"):
                continue
            target = relationship.get("Target", "")
            if relationship.get("TargetMode") == "External":
                external_image_links.append(target)
                continue
            if source_part is None:
                failures.append(f"cannot resolve internal image relationship from {name}: {relationship.get('Id', '')}")
                continue
            resolved = _resolve_relationship_target(source_part, target)
            item = {
                "source_part": source_part,
                "relationship_id": relationship.get("Id", ""),
                "target": target,
                "resolved_target": resolved,
            }
            internal_image_relationships.append(item)
            if resolved not in package_parts:
                broken_image_relationships.append(item)
                failures.append(
                    f"broken internal image relationship: {source_part}:{item['relationship_id']} -> {resolved} is missing from package",
                )
    if mode == "none" and media_paths:
        failures.append(f"media contract is none but package contains {len(media_paths)} media parts")
    elif mode == "svg-editable":
        if not media_paths or any(extension != "svg" for extension in extensions):
            failures.append(f"svg-editable requires only SVG package media, got {counts}")
        reviews.append("SVG placement/editability requires representative Microsoft Word review")
    elif mode == "png-golden":
        if not media_paths or any(extension != "png" for extension in extensions):
            failures.append(f"png-golden requires only PNG package media, got {counts}")
        editable_sources = media_contract.get("editable_source_paths", [])
        if not editable_sources or any(not Path(path).is_file() for path in editable_sources):
            failures.append("png-golden requires existing editable_source_paths")
        reviews.append("PNG answer-visual placement requires representative Microsoft Word review")
    elif mode == "mixed" and media_paths:
        unknown = sorted(set(extensions) - {"png", "svg", "jpg", "jpeg"})
        if unknown:
            reviews.append(f"unknown media types require review: {unknown}")
        else:
            reviews.append("mixed media placement requires representative Microsoft Word review")

    if embedding_policy == "embedded" and external_image_links:
        failures.append(f"media contract requires embedded media but found external image links: {external_image_links}")
    elif embedding_policy == "linked-allowed" and external_image_links:
        reviews.append("externally linked media requires availability review")
    elif embedding_policy not in {"embedded", "linked-allowed"}:
        failures.append(f"unknown media embedding_policy: {embedding_policy!r}")
    if editability not in {"none", "package-editable", "editable-source-required", "review-only"}:
        failures.append(f"unknown media editability contract: {editability!r}")

    expected = media_contract.get("expected_count", {})
    minimum = int(expected.get("min", 0))
    maximum = expected.get("max")
    if len(media_paths) < minimum:
        failures.append(f"media count {len(media_paths)} is below contract minimum {minimum}")
    if maximum is not None and len(media_paths) > int(maximum):
        failures.append(f"media count {len(media_paths)} exceeds contract maximum {maximum}")
    return failures, reviews, {
        "count": len(media_paths),
        "extensions": counts,
        "paths": media_paths,
        "role": role,
        "editability": editability,
        "embedding_policy": embedding_policy,
        "external_image_links": external_image_links,
        "internal_image_relationship_count": len(internal_image_relationships),
        "broken_internal_image_relationships": broken_image_relationships,
    }


def blocked_result(
    artifact_path: str | Path,
    mode: str,
    reason: str,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "document_type": "thai-math-docx-qa-report",
        "artifact_path": str(artifact_path),
        "mode": mode,
        "contract": dict(contract or {}),
        "verdict": "BLOCKED",
        "needs_word_review": False,
        "summary": f"BLOCKED: automated handoff-readiness checks could not run: {reason}",
        "failures": [],
        "review_items": [],
        "blocked_reasons": [reason],
        "checks": [],
        "metrics": {},
        "mutation": {},
    }


def audit_docx(
    artifact_path: str | Path,
    contract: Mapping[str, Any],
    *,
    mode: str = "check",
    source_path: str | Path | None = None,
    source_sha256_before: str | None = None,
) -> dict[str, Any]:
    path = Path(artifact_path)
    if not path.is_file():
        return blocked_result(path, mode, f"file not found: {path}", contract)
    artifact_sha_before = sha256_file(path)
    roots, package_failures, media_paths, package_parts = _parse_package(path)
    failures = list(package_failures)
    reviews: list[str] = []
    checks: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    _check(
        checks,
        "package-xml-integrity",
        "FAIL" if package_failures else "PASS",
        "DOCX ZIP/XML package is invalid" if package_failures else "DOCX ZIP/XML package is readable",
        xml_parts=len(roots),
    )

    if not package_failures:
        font_failures, font_metrics = _audit_fonts(roots, path)
        failures.extend(font_failures)
        metrics["fonts"] = font_metrics
        _check(checks, "thai-fonts-defaults-theme-insertion", "FAIL" if font_failures else "PASS", "Thai font/default/theme/insertion checks", issue_count=len(font_failures))

        omml_failures, omml_metrics = _audit_omml(roots, contract)
        failures.extend(omml_failures)
        metrics["omml"] = omml_metrics
        _check(checks, "omml-editability", "FAIL" if omml_failures else "PASS", "Editable OMML and Thai-in-math checks", issue_count=len(omml_failures))

        layout_failures, layout_reviews, layout_metrics = _audit_geometry_and_tables(roots, contract["layout"])
        failures.extend(layout_failures)
        reviews.extend(layout_reviews)
        metrics["layout"] = layout_metrics
        _check(checks, "geometry-table-shape", "FAIL" if layout_failures else ("REVIEW" if layout_reviews else "PASS"), "Page geometry, native columns and table grid/content shape", issue_count=len(layout_failures), review_count=len(layout_reviews))

        media_failures, media_reviews, media_metrics = _audit_media(media_paths, contract["media"], roots, package_parts)
        failures.extend(media_failures)
        reviews.extend(media_reviews)
        metrics["media"] = media_metrics
        _check(checks, "media-contract", "FAIL" if media_failures else ("REVIEW" if media_reviews else "PASS"), "Media inventory and contract", issue_count=len(media_failures), review_count=len(media_reviews))

    if contract["source_mode"] in {"imported", "teacher-master"}:
        reviews.append(f"{contract['source_mode']} source requires representative Microsoft Word handoff review")
    artifact_sha_after = sha256_file(path)
    source = Path(source_path) if source_path is not None else path
    source_after = sha256_file(source) if source.is_file() else None
    source_before = source_sha256_before or (artifact_sha_before if source == path else None)
    source_unchanged = source_before is None or source_before == source_after
    artifact_unchanged = artifact_sha_before == artifact_sha_after
    if not source_unchanged:
        failures.append("source artifact changed during QA")
    if not artifact_unchanged:
        failures.append("audited artifact changed during QA")
    _check(
        checks,
        "mutation-provenance",
        "FAIL" if not (source_unchanged and artifact_unchanged) else "PASS",
        "Source and audited-artifact mutation provenance",
        source_unchanged=source_unchanged,
        artifact_unchanged=artifact_unchanged,
    )

    verdict = "FAIL" if failures else "PASS"
    needs_word_review = bool(reviews)
    qualifier = "; representative Word review required" if needs_word_review else ""
    summary = (
        f"{verdict}: automated handoff-readiness checks "
        f"{'found contract/artifact issues' if failures else 'passed'}{qualifier}"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "document_type": "thai-math-docx-qa-report",
        "artifact_path": str(path),
        "mode": mode,
        "contract": dict(contract),
        "verdict": verdict,
        "needs_word_review": needs_word_review,
        "summary": summary,
        "failures": failures,
        "review_items": reviews,
        "blocked_reasons": [],
        "checks": checks,
        "metrics": metrics,
        "mutation": {
            "source_path": str(source),
            "source_sha256_before": source_before,
            "source_sha256_after": source_after,
            "source_unchanged": source_unchanged,
            "artifact_unchanged_during_audit": artifact_unchanged,
            "artifact_sha256_before": artifact_sha_before,
            "artifact_sha256_after": artifact_sha_after,
        },
    }


def fix_copy(source: str | Path, output: str | Path) -> tuple[Path, str]:
    source_path = Path(source)
    output_path = Path(output)
    if source_path.resolve() == output_path.resolve():
        raise ContractError("--output must not overwrite the source DOCX")
    if not source_path.is_file():
        raise FileNotFoundError(f"file not found: {source_path}")
    source_hash = sha256_file(source_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, output_path)
    document = Document(output_path)
    builder.enforce_document_font_defaults(document)
    document.save(output_path)
    builder.normalize_docx_theme_thai_fonts(output_path)
    return output_path, source_hash


def write_reports(
    result: dict[str, Any],
    *,
    report_dir: str | Path | None,
) -> dict[str, str]:
    explicit_dir = report_dir is not None
    target = Path(report_dir) if explicit_dir else Path.cwd() / "qa-reports"
    target.mkdir(parents=True, exist_ok=True)
    stem = Path(result["artifact_path"]).stem or "artifact"
    json_path = target / f"{stem}.qa.json"
    paths = {"json": str(json_path)}
    if explicit_dir:
        paths["markdown"] = str(target / f"{stem}.qa.md")
    result["report_paths"] = paths
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if explicit_dir:
        markdown = [
            f"# Thai Math DOCX QA — {Path(result['artifact_path']).name}",
            "",
            f"- Verdict: `{result['verdict']}`",
            f"- Needs Word review: `{str(result['needs_word_review']).lower()}`",
            f"- Meaning: {result['summary']}",
            "",
            "## Checks",
            "",
        ]
        markdown.extend(
            f"- `{check['status']}` · `{check['id']}` — {check['summary']}"
            for check in result["checks"]
        )
        if result["failures"]:
            markdown.extend(["", "## Failures", ""] + [f"- {item}" for item in result["failures"]])
        if result["review_items"]:
            markdown.extend(["", "## Word review items", ""] + [f"- {item}" for item in result["review_items"]])
        Path(paths["markdown"]).write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return paths

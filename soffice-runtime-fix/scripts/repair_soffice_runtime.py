#!/usr/bin/env python3
"""Diagnose and repair the active Codex bundled LibreOffice launcher on macOS."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from xml.sax.saxutils import escape
import zipfile


SKILL_VERSION = "2026.08.26"
HOMEBREW_TO_POPPLER = {
    "/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib": "liblcms2.2.dylib",
    "/opt/homebrew/opt/fontconfig/lib/libfontconfig.1.dylib": "libfontconfig.1.dylib",
    "/opt/homebrew/opt/freetype/lib/libfreetype.6.dylib": "libfreetype.6.dylib",
}
THAI_RANGE = re.compile(r"[\u0e00-\u0e7f]")
THAI_FONT_HINTS = (
    "sarabun", "thai", "angsana", "cordia", "leelawadee", "tahoma", "thonburi"
)


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False, env=env)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def otool_refs(path: Path) -> list[str]:
    proc = run(["otool", "-L", str(path)])
    if proc.returncode != 0:
        return []
    return [
        line.strip().split(" ", 1)[0]
        for line in proc.stdout.splitlines()[1:]
        if line.strip().startswith("/opt/homebrew/")
    ]


def executable_files(root: Path) -> list[Path]:
    files: list[Path] = []
    if not root.exists():
        return files
    for path in root.rglob("*"):
        try:
            mode = path.stat().st_mode
        except OSError:
            continue
        if path.is_file() and mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            files.append(path)
    return files


def scan_homebrew_refs(lo_contents: Path) -> dict[str, list[str]]:
    return {
        str(path): refs
        for path in executable_files(lo_contents)
        if (refs := otool_refs(path))
    }


def renderer_prefers_override(renderer: Path | None) -> bool:
    if not renderer or not renderer.is_file():
        return False
    try:
        source = renderer.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    markers = ("bin/override/soffice", '"bin", "override"', "'bin', 'override'")
    return any(marker in source for marker in markers)


def discover_launcher(
    dep_root: Path, explicit: Path | None = None, renderer: Path | None = None
) -> tuple[Path | None, str, list[Path]]:
    override = dep_root / "bin/override/soffice"
    legacy = dep_root / "bin/soffice"
    ordered: list[tuple[Path, str]] = []
    if explicit:
        ordered.append((explicit, "explicit"))
    if renderer_prefers_override(renderer):
        ordered.append((override, "renderer"))
    ordered.extend(((override, "override"), (legacy, "legacy")))
    seen: set[Path] = set()
    candidates: list[Path] = []
    sources: dict[Path, str] = {}
    for path, source in ordered:
        resolved = Path(os.path.abspath(path.expanduser()))
        if resolved in seen:
            continue
        seen.add(resolved)
        candidates.append(resolved)
        sources[resolved] = source
    for resolved in candidates:
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved, sources[resolved], candidates
    return None, "missing", candidates


def native_target(dep_root: Path) -> Path:
    return (
        dep_root
        / "native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/MacOS/soffice"
    )


def wrapper_text(launcher: Path, target: Path, *, user_home: Path | None = None) -> str:
    relative_target = os.path.relpath(target, launcher.parent)
    user_fonts = escape(str((user_home or Path.home()) / "Library/Fonts"))
    return f'''#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
TARGET="${{SCRIPT_DIR}}/{relative_target}"
WORK_ROOT="$(mktemp -d "${{TMPDIR:-/private/tmp}}/codex-soffice.XXXXXX")"
cleanup() {{ rm -rf "${{WORK_ROOT}}"; }}
trap cleanup EXIT
mkdir -p "${{WORK_ROOT}}/font-cache" "${{WORK_ROOT}}/profile"
cat > "${{WORK_ROOT}}/fonts.conf" <<EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>{user_fonts}</dir>
  <dir>/Library/Fonts</dir>
  <dir>/System/Library/Fonts</dir>
  <cachedir>${{WORK_ROOT}}/font-cache</cachedir>
</fontconfig>
EOF
export FONTCONFIG_FILE="${{WORK_ROOT}}/fonts.conf"
export XDG_CACHE_HOME="${{WORK_ROOT}}"
ARGS=()
for ARG in "$@"; do
  case "${{ARG}}" in
    -env:UserInstallation=*) ;;
    *) ARGS+=("${{ARG}}") ;;
  esac
done
"${{TARGET}}" -env:UserInstallation="file://${{WORK_ROOT}}/profile" "${{ARGS[@]}}"
'''


def plan_wrapper_change(launcher: Path, target: Path, today: str) -> dict[str, object]:
    desired = wrapper_text(launcher, target).encode()
    is_symlink = launcher.is_symlink()
    link_target = os.readlink(launcher) if is_symlink else None
    old = f"symlink:{link_target}".encode() if is_symlink else launcher.read_bytes()
    checksum = sha256_bytes(old)
    backup = launcher.with_name(f"{launcher.name}.orig-runtime-fix-{today}-{checksum[:12]}")
    return {
        "changed": old != desired,
        "backup": str(backup),
        "before_checksum": checksum,
        "after_checksum": sha256_bytes(desired),
        "was_symlink": is_symlink,
        "link_target": link_target,
        "desired": desired,
    }


def apply_wrapper_change(launcher: Path, plan: dict[str, object]) -> None:
    if not plan["changed"]:
        return
    backup = Path(str(plan["backup"]))
    if not os.path.lexists(backup):
        if plan["was_symlink"]:
            backup.symlink_to(str(plan["link_target"]))
        else:
            backup.write_bytes(launcher.read_bytes())
            backup.chmod(stat.S_IMODE(launcher.stat().st_mode))
    if launcher.is_symlink():
        launcher.unlink()
    launcher.write_bytes(bytes(plan["desired"]))
    launcher.chmod(0o755)


def patch_homebrew_refs(
    refs: dict[str, list[str]], poppler_lib: Path, *, dry_run: bool
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    patched: list[dict[str, str]] = []
    unmapped: list[dict[str, str]] = []
    planned: list[tuple[Path, str, Path]] = []
    for path_string, found_refs in refs.items():
        path = Path(path_string)
        for old_ref in found_refs:
            name = HOMEBREW_TO_POPPLER.get(old_ref)
            replacement = poppler_lib / name if name else None
            if not replacement or not replacement.exists():
                unmapped.append({"path": str(path), "reference": old_ref})
                continue
            patched.append({"path": str(path), "old": old_ref, "new": str(replacement)})
            planned.append((path, old_ref, replacement))
    if unmapped:
        return patched, unmapped
    if not dry_run:
        for path, old_ref, replacement in planned:
            proc = run(["install_name_tool", "-change", old_ref, str(replacement), str(path)])
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or f"install_name_tool failed for {path}")
    return patched, unmapped


def launch_check(launcher: Path) -> dict[str, object]:
    proc = run([str(launcher), "--version"])
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def docx_has_thai(docx: Path) -> bool:
    try:
        with zipfile.ZipFile(docx) as bundle:
            xml = bundle.read("word/document.xml").decode("utf-8", "replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return False
    return bool(THAI_RANGE.search(xml))


def pdf_fonts(pdf: Path, dep_root: Path) -> list[str]:
    pdffonts = find_poppler_tool(dep_root, "pdffonts")
    if pdffonts:
        proc = run([str(pdffonts), str(pdf)])
        if proc.returncode == 0:
            lines = proc.stdout.splitlines()[2:]
            return sorted({line.split()[0] for line in lines if line.split()})
    data = pdf.read_bytes()
    return sorted({m.decode() for m in re.findall(rb"/BaseFont\s*/([A-Za-z0-9+,_-]+)", data)})


def find_poppler_tool(dep_root: Path, name: str) -> Path | None:
    for candidate in (
        dep_root / f"bin/override/{name}",
        dep_root / f"bin/{name}",
        dep_root / f"native/poppler/poppler/bin/{name}",
        dep_root / f"native/poppler/bin/{name}",
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def rasterizer(dep_root: Path) -> tuple[str | None, Path | None]:
    if importlib.util.find_spec("fitz") is not None:
        return "pymupdf", None
    if candidate := find_poppler_tool(dep_root, "pdftoppm"):
        return "pdftoppm", candidate
    return None, None


def verify_docx(launcher: Path, docx: Path, dep_root: Path) -> dict[str, object]:
    if not docx.is_file() or not zipfile.is_zipfile(docx):
        return {"ok": False, "failure_class": "G", "error": "invalid DOCX package"}
    with tempfile.TemporaryDirectory(prefix="soffice-runtime-verify-") as temp_string:
        temp = Path(temp_string)
        pdf_dir = temp / "pdf"
        png_dir = temp / "png"
        profile = temp / "profile"
        pdf_dir.mkdir()
        png_dir.mkdir()
        proc = run([
            str(launcher), "--headless", f"-env:UserInstallation={profile.as_uri()}",
            "--convert-to", "pdf", "--outdir", str(pdf_dir), str(docx),
        ])
        pdf = pdf_dir / f"{docx.stem}.pdf"
        if proc.returncode != 0 or not pdf.is_file() or pdf.stat().st_size == 0:
            output = f"{proc.stdout}\n{proc.stderr}".strip()
            failure = "C" if any(
                token in output.lower() for token in ("user installation", "fontconfig", "cache")
            ) else "A"
            return {"ok": False, "failure_class": failure, "error": output or "PDF not created"}

        fonts = pdf_fonts(pdf, dep_root)
        has_thai = docx_has_thai(docx)
        thai_font = any(hint in font.lower() for font in fonts for hint in THAI_FONT_HINTS)
        if has_thai and not thai_font:
            return {
                "ok": False, "failure_class": "D", "pdf": True,
                "fonts": fonts, "error": "DOCX contains Thai but no Thai font was embedded",
            }

        backend, pdftoppm = rasterizer(dep_root)
        if backend == "pymupdf":
            import fitz  # type: ignore
            with fitz.open(pdf) as document:
                for number, page in enumerate(document, 1):
                    page.get_pixmap(dpi=120).save(png_dir / f"page-{number}.png")
        elif backend == "pdftoppm" and pdftoppm:
            raster = run([str(pdftoppm), "-png", "-r", "120", str(pdf), str(png_dir / "page")])
            if raster.returncode != 0:
                return {"ok": False, "failure_class": "F", "error": raster.stderr.strip()}
        else:
            return {
                "ok": False, "failure_class": "E", "pdf": True,
                "fonts": fonts, "error": "no PyMuPDF or bundled pdftoppm rasterizer",
            }
        pages = sorted(png_dir.glob("*.png"))
        return {
            "ok": bool(pages), "failure_class": None if pages else "F", "pdf": True,
            "png_pages": len(pages), "rasterizer": backend, "fonts": fonts,
            "thai_font_embedded": thai_font if has_thai else None,
        }


def classify(
    launcher: Path | None,
    refs: dict[str, list[str]],
    check: dict[str, object] | None,
    verification: dict[str, object] | None,
) -> str | None:
    if launcher is None:
        return "A"
    if refs:
        return "B"
    if check and not check["ok"]:
        text = f"{check.get('stdout', '')}\n{check.get('stderr', '')}".lower()
        if any(token in text for token in ("user installation", "fontconfig", "writable cache")):
            return "C"
        return "A"
    if verification and not verification.get("ok"):
        return str(verification.get("failure_class") or "F")
    return None


def classify_failure_log(text: str) -> str | None:
    lowered = text.lower()
    if "pymupdf is required to rasterise" in lowered or "no module named 'fitz'" in lowered:
        return "E"
    if "thai text is missing" in lowered or "no thai font was embedded" in lowered:
        return "D"
    if "dyld: library not loaded" in lowered or "/opt/homebrew/opt/" in lowered:
        return "B"
    if any(token in lowered for token in ("user installation could not be completed", "no writable cache", "fontconfig error")):
        return "C"
    if "badzipfile" in lowered or "invalid docx" in lowered:
        return "G"
    return None


def status_for(failure: str | None, actions: list[str]) -> str:
    if failure == "D":
        return "THAI_RENDER_FAILURE"
    if failure == "E":
        return "RASTERIZER_MISSING"
    if failure in {"A", "F", "G"}:
        return "UNSUPPORTED_TOPOLOGY" if failure == "A" else "UNRESOLVED"
    if "patched_dylib" in actions:
        return "REPAIRED_DYLIB"
    if "replaced_wrapper" in actions:
        return "REPAIRED_WRAPPER"
    return "HEALTHY" if failure is None else "NEEDS_REPAIR"


def append_knowledge(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    key_material = "|".join([
        str(report.get("date")), str(report.get("bundle_version")),
        str(report.get("active_launcher")), SKILL_VERSION, str(report.get("failure_class")),
    ])
    key = sha256_bytes(key_material.encode())[:16]
    marker = f"<!-- soffice-runtime-fix:{key} -->"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# soffice Runtime Fix Knowledge\n"
    if marker in existing:
        return
    note = (
        f"\n{marker}\n## {report['date']} — {report['bundle_version']} — {report['failure_class'] or 'healthy'}\n\n"
        f"```json\n{json.dumps(report, ensure_ascii=False, indent=2, default=str)}\n```\n"
    )
    path.write_text(existing.rstrip() + "\n" + note, encoding="utf-8")


def report_for_json(report: dict[str, object]) -> dict[str, object]:
    cleaned = dict(report)
    cleaned.pop("_wrapper_desired", None)
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--diagnose", action="store_true")
    mode.add_argument("--repair", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dependency-root", required=True)
    parser.add_argument("--bundle-version", default="unknown")
    parser.add_argument("--renderer", type=Path)
    parser.add_argument("--launcher", type=Path)
    parser.add_argument("--verify-docx", type=Path)
    parser.add_argument("--failure-log", type=Path,
                        help="captured renderer stderr/stdout used to classify the failing stage")
    parser.add_argument("--knowledge-doc", type=Path)
    parser.add_argument("--date", default=dt.date.today().isoformat())
    args = parser.parse_args()

    dep_root = Path(args.dependency_root).expanduser().resolve()
    renderer = args.renderer.expanduser().resolve() if args.renderer else None
    explicit = Path(os.path.abspath(args.launcher.expanduser())) if args.launcher else None
    lo_contents = dep_root / "native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents"
    poppler_lib = dep_root / "native/poppler/poppler/lib"
    target = native_target(dep_root)
    launcher, source, candidates = discover_launcher(dep_root, explicit, renderer)

    refs = scan_homebrew_refs(lo_contents)
    check = launch_check(launcher) if launcher else None
    verification = verify_docx(launcher, args.verify_docx.resolve(), dep_root) if launcher and args.verify_docx else None
    failure_log_text = ""
    if args.failure_log:
        failure_log_text = args.failure_log.expanduser().read_text(encoding="utf-8", errors="replace")
    reported_failure = classify_failure_log(failure_log_text)
    initial_failure = reported_failure or classify(launcher, refs, check, verification)
    actions: list[str] = []
    wrapper_plan: dict[str, object] | None = None
    patched: list[dict[str, str]] = []
    unmapped: list[dict[str, str]] = []

    should_repair = args.repair or not args.diagnose
    if should_repair and launcher and initial_failure in {"A", "B", "C", "D"} and target.exists():
        if refs:
            patched, unmapped = patch_homebrew_refs(refs, poppler_lib, dry_run=args.dry_run)
            if patched and not unmapped:
                actions.append("would_patch_dylib" if args.dry_run else "patched_dylib")
            if unmapped:
                actions.append("blocked_unmapped_dylib")
        wrapper_plan = plan_wrapper_change(launcher, target, args.date)
        if wrapper_plan["changed"]:
            if not args.dry_run and not unmapped:
                apply_wrapper_change(launcher, wrapper_plan)
                actions.append("replaced_wrapper")
            else:
                actions.append("would_replace_wrapper")

    remaining_refs = refs if args.dry_run else scan_homebrew_refs(lo_contents)
    final_check = check
    final_verification = verification
    if should_repair and launcher and not args.dry_run and actions:
        final_check = launch_check(launcher)
        final_verification = verify_docx(launcher, args.verify_docx.resolve(), dep_root) if args.verify_docx else None
    if reported_failure in {"E", "F", "G"}:
        final_failure = reported_failure
    elif reported_failure == "D" and final_verification is None:
        final_failure = "D"
    else:
        final_failure = classify(launcher, remaining_refs, final_check, final_verification)

    report: dict[str, object] = {
        "skill_version": SKILL_VERSION,
        "date": args.date,
        "mode": "diagnose" if args.diagnose else "repair",
        "dry_run": args.dry_run,
        "dependency_root": str(dep_root),
        "bundle_version": args.bundle_version,
        "renderer": str(renderer) if renderer else None,
        "launcher_candidates": [str(path) for path in candidates],
        "active_launcher": str(launcher) if launcher else None,
        "launcher_source": source,
        "native_target": str(target),
        "failure_class_before": initial_failure,
        "failure_class": final_failure,
        "reported_failure_class": reported_failure,
        "homebrew_refs_before": refs,
        "homebrew_refs_after": remaining_refs,
        "launch_check": final_check,
        "verification": final_verification,
        "rasterizers": {
            "pymupdf": importlib.util.find_spec("fitz") is not None,
            "pdftoppm": (
                str(find_poppler_tool(dep_root, "pdftoppm"))
                if find_poppler_tool(dep_root, "pdftoppm") else None
            ),
        },
        "wrapper": ({key: value for key, value in wrapper_plan.items() if key != "desired"} if wrapper_plan else None),
        "patched": patched,
        "unmapped": unmapped,
        "actions": actions,
    }
    report["status"] = (
        "LAUNCH_HEALTHY_UNVERIFIED"
        if final_failure is None and final_verification is None
        else status_for(final_failure, actions)
    )

    if args.knowledge_doc and should_repair and not args.dry_run:
        append_knowledge(args.knowledge_doc.expanduser().resolve(), report)

    clean = report_for_json(report)
    if args.json:
        print(json.dumps(clean, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"status: {clean['status']}")
        print(f"failure class: {clean['failure_class'] or 'none'}")
        print(f"active launcher: {clean['active_launcher'] or 'not found'}")
        if actions:
            print("actions: " + ", ".join(actions))
    return 0 if final_failure is None else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render a Thai maths .docx to page images for visual review.

The pipeline is LibreOffice (DOCX -> PDF) then PyMuPDF (PDF -> PNG).

Why the fontconfig dance
------------------------
The headless LibreOffice build resolves fonts through fontconfig. When its
cache or config is in the state this project keeps hitting, it never sees
``~/Library/Fonts``, so TH Sarabun New is unavailable. Thai runs are then
dropped from the PDF entirely -- the maths and layout still render, which makes
the output look like a document defect rather than a font failure. This script
always hands LibreOffice a config that names the macOS font directories, and
then *verifies* that a Thai face was embedded before reporting success.

macOS Quick Look is not a substitute: it renders Thai but silently drops OMML
equations, so it cannot verify a maths handout either.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SOFFICE_CANDIDATES = (
    Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice",
    Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    Path("/usr/local/bin/soffice"),
    Path("/opt/homebrew/bin/soffice"),
)
FONT_DIRS = (Path.home() / "Library/Fonts", Path("/Library/Fonts"), Path("/System/Library/Fonts"))
THAI_RANGE = re.compile(r"[฀-๿]")


def find_soffice(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            sys.exit(f"soffice not found at {path}")
        return path
    for candidate in SOFFICE_CANDIDATES:
        if candidate.exists():
            return candidate
    from shutil import which
    found = which("soffice")
    if found:
        return Path(found)
    sys.exit("no soffice binary found; pass --soffice PATH")


def write_font_config(directory: Path) -> Path:
    """Point fontconfig at the real macOS font directories."""
    dirs = "\n".join(f"  <dir>{d}</dir>" for d in FONT_DIRS if d.exists())
    config = directory / "fonts.conf"
    config.write_text(
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
        f"<fontconfig>\n{dirs}\n  <cachedir>{directory / 'fc-cache'}</cachedir>\n</fontconfig>\n",
        encoding="utf-8",
    )
    (directory / "fc-cache").mkdir(exist_ok=True)
    return config


def docx_has_thai(docx: Path) -> bool:
    import zipfile
    with zipfile.ZipFile(docx) as bundle:
        return bool(THAI_RANGE.search(bundle.read("word/document.xml").decode("utf-8", "replace")))


def embedded_fonts(pdf: Path) -> list[str]:
    data = pdf.read_bytes()
    return sorted({m.decode() for m in re.findall(rb"/BaseFont\s*/([A-Za-z0-9+\-,_]+)", data)})


def convert_to_pdf(soffice: Path, docx: Path, outdir: Path, workdir: Path) -> Path:
    env = dict(os.environ)
    env["FONTCONFIG_FILE"] = str(write_font_config(workdir))
    result = subprocess.run(
        [str(soffice), "--headless",
         f"-env:UserInstallation=file://{workdir / 'profile'}",
         "--convert-to", "pdf", "--outdir", str(outdir), str(docx)],
        capture_output=True, text=True, env=env,
    )
    pdf = outdir / (docx.stem + ".pdf")
    if not pdf.exists():
        sys.exit(f"conversion failed\n{result.stdout}\n{result.stderr}")
    return pdf


def rasterise(pdf: Path, outdir: Path, dpi: int) -> list[Path]:
    try:
        import fitz
    except ImportError:
        sys.exit("PyMuPDF is required to rasterise: python3 -m pip install pymupdf")
    pages = []
    with fitz.open(pdf) as document:
        for number, page in enumerate(document, start=1):
            target = outdir / f"page-{number}.png"
            page.get_pixmap(dpi=dpi).save(target)
            pages.append(target)
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("docx", type=Path)
    parser.add_argument("-o", "--outdir", type=Path,
                        help="output directory (default: <docx parent>/rendered/<stem>)")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--soffice", help="explicit soffice path")
    parser.add_argument("--keep-pdf", action="store_true")
    parser.add_argument("--contact-sheet", action="store_true",
                        help="also compose the pages into one review sheet")
    args = parser.parse_args()

    if not args.docx.exists():
        sys.exit(f"no such file: {args.docx}")
    outdir = args.outdir or args.docx.parent / "rendered" / args.docx.stem
    outdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="render-docx-") as tmp:
        workdir = Path(tmp)
        pdf = convert_to_pdf(find_soffice(args.soffice), args.docx, workdir, workdir)
        fonts = embedded_fonts(pdf)
        pages = rasterise(pdf, outdir, args.dpi)
        if args.keep_pdf:
            (outdir / pdf.name).write_bytes(pdf.read_bytes())

    print(f"{len(pages)} page image(s) -> {outdir}")
    print(f"  embedded fonts: {', '.join(fonts) or 'none'}")

    if docx_has_thai(args.docx):
        thai_face = [f for f in fonts if "Sarabun" in f or "Thai" in f]
        if thai_face:
            print(f"  Thai font embedded: {', '.join(thai_face)}")
        else:
            print("  WARNING: the document contains Thai but no Thai font was embedded.")
            print("  The Thai text is missing from these images. Do not review Thai "
                  "wording from them, and do not 'fix' the DOCX on their evidence.")
            return 2

    if args.contact_sheet:
        sys.stdout.flush()  # keep the child's output after ours
        composer = Path(__file__).with_name("contact_sheet.py")
        subprocess.run([sys.executable, str(composer), str(outdir)], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

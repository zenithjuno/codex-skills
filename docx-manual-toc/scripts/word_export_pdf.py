#!/usr/bin/env python3
"""Compatibility CLI; shared Word export belongs to thai-math-docx."""
from pathlib import Path
import sys
SCRIPTS=Path(__file__).resolve().parents[2]/'thai-math-docx/scripts'
if not (SCRIPTS/'word_export_pdf.py').is_file():
    raise SystemExit('Shared Word exporter missing: install sibling thai-math-docx')
sys.path.insert(0,str(SCRIPTS))
if __name__=='__main__':
    from word_export_pdf import main
    raise SystemExit(main())

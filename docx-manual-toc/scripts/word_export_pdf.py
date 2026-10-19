#!/usr/bin/env python3
"""Export a DOCX to PDF with Microsoft Word itself (macOS), for true pagination.

    python3 word_export_pdf.py IN.docx OUT.pdf

LibreOffice paginates Thai teacher masters very differently from Word (one
122-page book rendered as 141 pages) and garbles tab-aligned contents pages, so
page numbers and tab alignment must come from Word.

Word is sandboxed: the file is copied into Word's own container, opened,
saved as PDF, closed WITHOUT saving, and the temporary folder is removed. The
input file is never opened in place, so a copy the teacher has open is safe.
"""
import os
import shutil
import subprocess
import sys
import tempfile

CONTAINER = os.path.expanduser('~/Library/Containers/com.microsoft.Word/Data')

SCRIPT = '''
with timeout of %(timeout)d seconds
tell application "Microsoft Word"
    set d to open file name "%(inp)s"
    delay 5
    save as d file name "%(out)s" file format format PDF
    close d saving no
end tell
end timeout
'''


def export(src, dst, timeout=280):
    if not os.path.isdir(CONTAINER):
        sys.exit('Microsoft Word container not found; is Word for Mac installed?')
    work = tempfile.mkdtemp(prefix='wordexport-', dir=CONTAINER)
    try:
        inp = os.path.join(work, 'in.docx')
        out = os.path.join(work, 'out.pdf')
        shutil.copyfile(src, inp)
        r = subprocess.run(['osascript', '-'], input=SCRIPT % {'inp': inp, 'out': out, 'timeout': timeout},
                           text=True, capture_output=True, timeout=timeout + 30)
        if r.returncode != 0 or not os.path.exists(out):
            sys.exit('Word export failed: %s' % (r.stderr.strip() or 'no PDF produced'))
        shutil.copyfile(out, dst)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print('Word PDF written:', dst)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    export(sys.argv[1], sys.argv[2])

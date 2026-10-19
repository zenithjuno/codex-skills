#!/usr/bin/env python3
"""Compare two Word-exported PDFs of the same book (before / after an edit).

    python3 compare_pages.py BEFORE.pdf AFTER.pdf [--margin 60] [--near 40]

Reports: page counts; the first page whose printed page number (read from the
header band) or large headings differ; and pages where body text now reaches
within --near points of the bottom margin band, i.e. pages that may overflow on
another machine. Make both PDFs with Word (docx-manual-toc/scripts/
word_export_pdf.py); LibreOffice pagination is not trustworthy for this.
"""
import argparse
import re

import fitz


def norm(s):
    # Word PDFs split sara am, also around a tone mark: ซ + ํ + ้ + า -> ซ้ำ
    return re.sub('\u0e4d([\u0e48-\u0e4b]?)\u0e32', '\\1\u0e33', re.sub(r'\s+', '', s))


def page_info(pg, margin):
    h = pg.rect.height
    num, heads, bottom = None, [], 0
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = norm(''.join(s['text'] for s in l['spans']))
            if not t:
                continue
            y0, y1 = l['bbox'][1], l['bbox'][3]
            if y0 < margin and re.fullmatch(r'\d+', t):
                num = t
            elif y1 < h - margin:
                bottom = max(bottom, y1)
                if max(s['size'] for s in l['spans']) >= 17.5:
                    heads.append(t[:30])
    return num, heads, bottom, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('before')
    ap.add_argument('after')
    ap.add_argument('--margin', type=float, default=60, help='header/footer band height in points')
    ap.add_argument('--near', type=float, default=40, help='warn when text ends this close to the footer band')
    a = ap.parse_args()
    A, B = fitz.open(a.before), fitz.open(a.after)
    print('pages: before %d, after %d%s' % (len(A), len(B), '' if len(A) == len(B) else '  <-- CHANGED'))
    ia = [page_info(p, a.margin) for p in A]
    ib = [page_info(p, a.margin) for p in B]
    for i in range(min(len(ia), len(ib))):
        if ia[i][0] != ib[i][0] or ia[i][1] != ib[i][1]:
            print('first divergence at pdf page %d: before printed %s %s | after printed %s %s'
                  % (i + 1, ia[i][0], ia[i][1][:2], ib[i][0], ib[i][1][:2]))
            break
    else:
        print('printed page numbers and headings match page for page')
    tight = [(i + 1, ib[i][0], round(ib[i][3] - a.margin - ib[i][2]))
             for i in range(len(ib)) if ib[i][3] - a.margin - ib[i][2] < a.near and ib[i][2] > 0]
    grew = [i + 1 for i in range(min(len(ia), len(ib))) if ib[i][2] - ia[i][2] > 2]
    print('pages whose text now ends lower than before: %d' % len(grew))
    for pdf_page, printed, room in tight:
        print('  near bottom: pdf page %d (printed %s), %dpt left' % (pdf_page, printed, room))


if __name__ == '__main__':
    main()

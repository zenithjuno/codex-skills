#!/usr/bin/env python3
"""Renumber hand-typed question labels in an existing DOCX.

Main items look like "1." (also "x.", "ข้อ 87.") at the start of a paragraph.
Sub-items look like "1)" at the start of a paragraph or right after a tab.
Labels are plain typed text, not Word list numbering.

Subcommands
  find   DOCX TEXT                  list paragraph indices whose text contains TEXT
  scan   DOCX --from A --to B --report R.md --config C.json
                                    survey a range, write a readable report and a
                                    draft config with suggested exclusions
  apply  DOCX --config C.json --output OUT.docx [--log L.txt]
                                    rewrite labels into a NEW file and verify it

Paragraph index = position in document order of every w:p in the body,
tables included (the same order for scan, config and apply).

Lessons baked in:
  * only w:t text is editable; an equation (m:oMath) is a barrier, so "(−1, 2)"
    inside math never looks like a "2)" label;
  * floating images (w:drawing) emit nothing, so a label after an anchored
    graph is still "at paragraph start";
  * sub labels need start-of-paragraph or a preceding tab, and at most two
    digits, so "(ปี 2569)" is never a label;
  * text-box paragraphs are skipped (Word stores them twice);
  * the new label is its own run with every font slot set, so Latin digits
    stop falling back to the Normal style's Latin font (often Cambria 12 pt).
"""
import argparse
import copy
import json
import re
import sys
import zipfile

from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
XS = '{http://www.w3.org/XML/1998/namespace}space'


def w(tag):
    return '{%s}%s' % (W, tag)


MAIN_RE = re.compile(r'^([ \t]*)((?:ข้อ\s*)?(?:\d+|[xX])\s*\.(?!\d)[ ]*)')
SUB_RE = re.compile(r'(?:^|(?<=\t))([ ]*)((\d{1,2})\)[ ]*)')
BOX_WORDS = ('ที่ควรรู้', 'สมบัติ', 'ขั้นตอน', 'สรุป', 'บทนิยาม', 'เทคนิค', 'สูตร', 'หลักการ')


# ---------- reading ----------

def load(path):
    z = zipfile.ZipFile(path)
    root = etree.fromstring(z.read('word/document.xml'))
    paras = list(root.find(w('body')).iter(w('p')))
    return z, root, paras


def in_textbox(p):
    return any(a.tag == w('txbxContent') for a in p.iterancestors())


def table_cell(p):
    for a in p.iterancestors():
        if a.tag == w('tc'):
            return a
    return None


def stream(p):
    """(char, w:t element or None, offset). Tabs -> '\t', equations -> '\x00'."""
    out = []
    for el in p.iter():
        if el.tag == w('t') and el.getparent().tag == w('r'):
            for k, ch in enumerate(el.text or ''):
                out.append((ch, el, k))
        elif el.tag == w('tab') and el.getparent().tag == w('r'):
            out.append(('\t', None, None))
        elif el.tag == '{%s}oMath' % M:
            out.append(('\x00', None, None))
    return out


def text_of(st):
    return ''.join(c for c, _, _ in st)


def readable(p):
    s = ''
    for el in p.iter():
        if el.tag == w('t'):
            s += el.text or ''
        elif el.tag == '{%s}t' % M:
            s += '‹' + (el.text or '') + '›'
        elif el.tag == w('tab'):
            s += '⇥'
    return s


def run_props(t):
    """Describe the run that holds text element t: (font, half-point size, bold)."""
    r = t.getparent()
    rpr = r.find(w('rPr'))
    font = size = ''
    bold = False
    if rpr is not None:
        f = rpr.find(w('rFonts'))
        if f is not None:
            font = f.get(w('cs')) or f.get(w('ascii')) or ''
        s = rpr.find(w('szCs')) if rpr.find(w('szCs')) is not None else rpr.find(w('sz'))
        if s is not None:
            size = s.get(w('val'))
        b = rpr.find(w('b'))
        bold = b is not None and b.get(w('val')) not in ('0', 'false')
    return font, size, bold


def table_first_text(cell):
    tbl = None
    for a in cell.iterancestors():
        if a.tag == w('tbl'):
            tbl = a
            break
    if tbl is None:
        return ''
    first = tbl.find('.//' + w('p'))
    head = readable(first)[:60] if first is not None else ''
    prev = tbl.getprevious()
    while prev is not None and prev.tag == w('p') and not readable(prev).strip():
        prev = prev.getprevious()
    if prev is not None and prev.tag == w('p'):
        head = readable(prev)[:40] + ' / ' + head
    return head


def expand(items):
    out = set()
    for it in items:
        if isinstance(it, list):
            out.update(range(it[0], it[1] + 1))
        else:
            out.add(int(it))
    return out


# ---------- scan ----------

def classify(paras, lo, hi):
    mains, subs = [], []
    seen_main = False
    restart_last = 0
    for i in range(lo, hi + 1):
        p = paras[i]
        if in_textbox(p):
            continue
        st = stream(p)
        s = text_of(st)
        cell = table_cell(p)
        m = MAIN_RE.match(s)
        if m and cell is None:
            a = m.start(2)
            font, size, bold = run_props(st[a][1]) if st[a][1] is not None else ('', '', False)
            rest = s[m.end(2):]
            flags = []
            if bold:
                flags.append('bold label')
            if size and int(size) >= 36:
                flags.append('large label (%spt)' % (int(size) // 2))
            if 'คือ' in rest[:30]:
                flags.append('definition-like (คือ)')
            if len(m.group(1).replace('\t', '    ')) >= 2:
                flags.append('indented')
            old = m.group(2).strip()
            num = re.sub(r'\D', '', old)
            if num == '1' and mains:
                flags.append('numbering restarts at 1')
                restart_last = 1
            elif num and restart_last and int(num) == restart_last + 1:
                flags.append('continues a restarted list')
                restart_last += 1
            strong = [f for f in flags if f != 'bold label']
            mains.append({'index': i, 'old': old, 'text': readable(p)[:70],
                          'flags': flags, 'exclude': bool(strong)})
            seen_main = True
            continue
        if not seen_main:
            continue
        found = [sm.group(3) for sm in SUB_RE.finditer(s)]
        if found:
            box = table_first_text(cell) if cell is not None else ''
            flags = []
            if cell is not None and any(k in box for k in BOX_WORDS):
                flags.append('inside a knowledge box: "%s"' % box[:40])
            subs.append({'index': i, 'labels': found, 'in_table': cell is not None,
                         'text': readable(p)[:70], 'flags': flags, 'exclude': bool(flags)})
    return mains, subs


def cmd_scan(a):
    _, _, paras = load(a.docx)
    mains, subs = classify(paras, a.from_, a.to)
    n = a.start - 1
    lines = ['# Renumber survey', '',
             'Range: paragraphs %d–%d of %s' % (a.from_, a.to, a.docx), '',
             '## Main items (suggested exclusions marked ✗)', '',
             '| para | old | new | flags | text |', '|---|---|---|---|---|']
    for it in mains:
        if it['exclude']:
            new = '✗'
        else:
            n += 1
            new = str(n)
        lines.append('| %d | %s | %s | %s | %s |' % (it['index'], it['old'], new,
                                                    '; '.join(it['flags']), it['text'].replace('|', '/')))
    kept_items = [it for it in mains if not it['exclude']]
    kept = len(kept_items)
    changed = sum(1 for j, it in enumerate(kept_items)
                  if it['old'] != '%d.' % (a.start + j))
    lines += ['', 'Main items kept: %d; labels that change: %d' % (kept, changed), '',
              '## Sub-item paragraphs with flags', '',
              '| para | labels | flags | text |', '|---|---|---|---|']
    for it in subs:
        if it['flags'] or it['in_table']:
            lines.append('| %d | %s | %s | %s |' % (it['index'], ' '.join(it['labels']),
                                                 '; '.join(it['flags']) or 'in table', it['text'].replace('|', '/')))
    lines += ['', 'Sub-label paragraphs total: %d' % len(subs)]
    open(a.report, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    cfg = {
        'range': [a.from_, a.to],
        'start': a.start,
        'exclude_main': [it['index'] for it in mains if it['exclude']],
        'exclude_sub': [it['index'] for it in subs if it['exclude']],
        'strip_prefix': True,
        'main_suffix': '.', 'sub_suffix': ')', 'space_after': ' ',
        'font': 'TH Sarabun New', 'size_pt': 16, 'bold': False,
    }
    json.dump(cfg, open(a.config, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('scan: %d main candidates (%d suggested exclusions), %d sub-label paragraphs; report %s, draft config %s'
          % (len(mains), len(cfg['exclude_main']), len(subs), a.report, a.config))


# ---------- apply ----------

def label_rpr(cfg):
    r = etree.Element(w('rPr'))
    f = etree.SubElement(r, w('rFonts'))
    for slot in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
        f.set(w(slot), cfg['font'])
    val = '1' if cfg['bold'] else '0'
    etree.SubElement(r, w('b')).set(w('val'), val)
    etree.SubElement(r, w('bCs')).set(w('val'), val)
    hp = str(int(round(cfg['size_pt'] * 2)))
    etree.SubElement(r, w('sz')).set(w('val'), hp)
    etree.SubElement(r, w('szCs')).set(w('val'), hp)
    etree.SubElement(r, w('lang')).set(w('bidi'), 'th-TH')
    return r


def replace_span(st, a, b, newtext, cfg):
    """Delete characters st[a:b] (all inside w:t) and put a label run in their place."""
    _, t0, k0 = st[a]
    per = {}
    for _, t, k in st[a:b]:
        per.setdefault(t, []).append(k)
    run0 = t0.getparent()
    content = [c for c in run0 if c.tag != w('rPr')]
    idx = content.index(t0)
    pre = (t0.text or '')[:k0]
    if idx > 0 or pre:                       # split the run so the label lands in order
        clone = copy.deepcopy(run0)
        for c in [c for c in clone if c.tag != w('rPr')]:
            clone.remove(c)
        for c in content[:idx]:
            clone.append(c)
        if pre:
            nt = etree.SubElement(clone, w('t'))
            nt.text = pre
            nt.set(XS, 'preserve')
        run0.addprevious(clone)
        t0.text = (t0.text or '')[k0:]
        per[t0] = [k - k0 for k in per[t0]]
    for t, ks in per.items():
        drop = set(ks)
        t.text = ''.join(c for j, c in enumerate(t.text or '') if j not in drop)
        t.set(XS, 'preserve')
    lr = etree.Element(w('r'))
    lr.append(label_rpr(cfg))
    lt = etree.SubElement(lr, w('t'))
    lt.text = newtext
    lt.set(XS, 'preserve')
    run0.addprevious(lr)
    for t in per:                            # drop runs left holding only empty text
        r = t.getparent()
        if r is not None and r.getparent() is not None and not (t.text or ''):
            if all(c.tag == w('rPr') or (c.tag == w('t') and not (c.text or '')) for c in r):
                r.getparent().remove(r)


def cmd_apply(a):
    if a.output == a.docx:
        sys.exit('refusing to overwrite the input; give a different --output')
    cfg = json.load(open(a.config, encoding='utf-8'))
    z, root, paras = load(a.docx)
    lo, hi = cfg['range']
    ex_main = expand(cfg.get('exclude_main', []))
    ex_sub = expand(cfg.get('exclude_sub', []))
    sp = cfg.get('space_after', ' ')
    log = []
    n = cfg.get('start', 1) - 1
    cur = None
    k = 0
    for i in range(lo, hi + 1):
        p = paras[i]
        if in_textbox(p):
            continue
        st = stream(p)
        s = text_of(st)
        m = MAIN_RE.match(s)
        if m and table_cell(p) is None and i not in ex_main:
            a0, b0 = m.start(2), m.end(2)
            if any(t is None for _, t, _ in st[a0:b0]):
                sys.exit('main label at paragraph %d crosses a non-text element' % i)
            n += 1
            cur, k = n, 0
            replace_span(st, a0, b0, '%d%s%s' % (n, cfg['main_suffix'], sp), cfg)
            log.append('MAIN p%d: %r -> %d%s' % (i, m.group(2).strip(), n, cfg['main_suffix']))
            continue
        if cur is None or i in ex_sub:
            continue
        hits = list(SUB_RE.finditer(s))
        numbered = []
        for sm in hits:
            k += 1
            numbered.append((sm, k))
        for sm, kk in reversed(numbered):    # edit back to front so offsets hold
            st = stream(p)
            s = text_of(st)
            a0, b0 = sm.start(2), sm.end(2)
            if any(t is None for _, t, _ in st[a0:b0]):
                sys.exit('sub label at paragraph %d crosses a non-text element' % i)
            nxt = s[b0] if b0 < len(s) else ''
            new = '%d%s' % (kk, cfg['sub_suffix']) + ('' if nxt in ('\t', '') else sp)
            replace_span(st, a0, b0, new, cfg)
        for sm, kk in numbered:
            log.append('  sub p%d item %d: %s) -> %d)' % (i, cur, sm.group(3), kk))
    data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    with zipfile.ZipFile(a.output, 'w', zipfile.ZIP_DEFLATED) as o:
        for it in z.infolist():
            o.writestr(it, data if it.filename == 'word/document.xml' else z.read(it.filename))
    if a.log:
        open(a.log, 'w', encoding='utf-8').write('\n'.join(log) + '\n')
    changed_sub = [l for l in log if l.startswith('  sub') and l.split(': ')[1].split(')')[0] != l.split('-> ')[1].rstrip(')')]
    print('apply: %d main items numbered %d..%d, %d sub labels (%d changed number); wrote %s'
          % (n - cfg.get('start', 1) + 1, cfg.get('start', 1), n, sum(1 for l in log if l.startswith('  sub')),
             len(changed_sub), a.output))
    verify(a.output, cfg)


def verify(path, cfg):
    _, _, paras = load(path)
    lo, hi = cfg['range']
    ex_main = expand(cfg.get('exclude_main', []))
    seq = []
    bad_fmt = 0
    for i in range(lo, min(hi, len(paras) - 1) + 1):
        p = paras[i]
        if in_textbox(p) or table_cell(p) is not None or i in ex_main:
            continue
        st = stream(p)
        m = MAIN_RE.match(text_of(st))
        if m:
            seq.append(m.group(2).strip())
            font, size, bold = run_props(st[m.start(2)][1])
            if font != cfg['font'] or size != str(int(round(cfg['size_pt'] * 2))) or bold != cfg['bold']:
                bad_fmt += 1
    want = ['%d%s' % (j, cfg['main_suffix']) for j in range(cfg.get('start', 1), cfg.get('start', 1) + len(seq))]
    ok = seq == want
    print('verify: main sequence %s; labels with wrong font/size/bold: %d' % ('OK' if ok else 'MISMATCH', bad_fmt))
    if not ok:
        for j, (got, exp) in enumerate(zip(seq, want)):
            if got != exp:
                print('  first mismatch at item %d: got %s, expected %s' % (j + 1, got, exp))
                break
        sys.exit(1)


def cmd_find(a):
    _, _, paras = load(a.docx)
    for i, p in enumerate(paras):
        s = readable(p)
        if a.text in s:
            print(i, 'T' if table_cell(p) is not None else ' ', s[:100])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('find')
    f.add_argument('docx')
    f.add_argument('text')
    s = sub.add_parser('scan')
    s.add_argument('docx')
    s.add_argument('--from', dest='from_', type=int, required=True)
    s.add_argument('--to', type=int, required=True)
    s.add_argument('--start', type=int, default=1)
    s.add_argument('--report', required=True)
    s.add_argument('--config', required=True)
    p = sub.add_parser('apply')
    p.add_argument('docx')
    p.add_argument('--config', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--log')
    a = ap.parse_args()
    {'find': cmd_find, 'scan': cmd_scan, 'apply': cmd_apply}[a.cmd](a)


if __name__ == '__main__':
    main()

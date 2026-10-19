#!/usr/bin/env python3
"""Maintain a hand-typed (tab-aligned) contents page in an existing DOCX.

A manual contents page here is one or more paragraphs whose lines are split by
w:br and look like:   " ⇥- Title⇥⇥⇥⇥⇥⇥42"   (no TOC field, no Heading styles).

Subcommands
  inspect  DOCX [--paras 8,10,12]      list contents lines: paragraph, title, tabs,
                                        number, and the column the number lands on
  headings PDF [--min-size 17.5]       list large headings per page with the page's
                                        printed number (read from the header)
  set      DOCX --plan PLAN.json --output OUT.docx
                                        update numbers of existing lines and insert
                                        missing lines, matching the existing style
  verify   PDF --plan PLAN.json         check each entry's page against a Word PDF
  restyle-header DOCX --para N --like M --output OUT.docx
                                        give paragraph N's chapter header the run
                                        style of paragraph M's header, realign number
  sections DOCX                         list section breaks near the front
  drop-empty-section DOCX --para N --output OUT.docx
                                        remove an empty section-break paragraph

PLAN.json
  {"paragraphs": {"8": [ {"title": "บทที่ 1", "prefix": true, "page": 1},
                         {"title": "คู่อันดับ", "page": 1, "heading": "คู่อันดับ"},
                         {"title": "ผลคูณคาร์ทีเซียน", "page": 2}, ... ],
                  "10": [...]}}
  Entries are listed in the order they should appear. "title" matches an
  existing line by its text with spaces removed (exact, or prefix when
  "prefix": true); an unmatched entry becomes a new line after the previous
  entry. "heading" (default: title) is the text searched for in the PDF.
"""
import argparse
import copy
import json
import os
import re
import sys
import zipfile

from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XS = '{http://www.w3.org/XML/1998/namespace}space'


def w(tag):
    return '{%s}%s' % (W, tag)


def norm(s):
    # Word PDFs split sara am, also around a tone mark: ซ + ํ + ้ + า -> ซ้ำ
    return re.sub('\u0e4d([\u0e48-\u0e4b]?)\u0e32', '\\1\u0e33', re.sub(r'\s+', '', s))


# ---------- font metrics ----------

FONT_DIRS = ['~/Library/Fonts', '/Library/Fonts', '/System/Library/Fonts/Supplemental',
             '/Applications/Microsoft Word.app/Contents/Resources/DFonts']
FONT_FILES = {('th sarabun new', False): 'THSarabunNew.ttf', ('th sarabun new', True): 'THSarabunNew Bold.ttf',
              ('th sarabunpsk', False): 'thsarabun.ttf', ('th sarabunpsk', True): 'thsarabun-bold.ttf'}
_font_cache = {}


def font_for(name, bold=False):
    """Font for width estimates; bold runs need the bold face (it is wider)."""
    from PIL import ImageFont
    key = ((name or '').lower(), bool(bold))
    if key in _font_cache:
        return _font_cache[key]
    wanted = [FONT_FILES.get(key, ''), 'THSarabunNew Bold.ttf' if bold else 'THSarabunNew.ttf']
    for fn in wanted:
        for d in FONT_DIRS:
            p = os.path.join(os.path.expanduser(d), fn)
            if fn and os.path.exists(p):
                _font_cache[key] = ImageFont.truetype(p, 1000)
                return _font_cache[key]
    sys.exit('no Thai font file found for width estimates (looked for %s)' % wanted)


def width_twips(text, font, half_points):
    return font.getlength(text) / 1000 * (half_points / 2) * 20


# ---------- document model ----------

def load(path):
    z = zipfile.ZipFile(path)
    root = etree.fromstring(z.read('word/document.xml'))
    settings = etree.fromstring(z.read('word/settings.xml'))
    dts = settings.find(w('defaultTabStop'))
    default_tab = int(dts.get(w('val'))) if dts is not None else 720
    return z, root, list(root.find(w('body')).iter(w('p'))), default_tab


def run_text(r):
    return ''.join(t.text or '' for t in r.findall(w('t')))


def run_style(r):
    rpr = r.find(w('rPr'))
    name, hp = '', 32
    if rpr is not None:
        f = rpr.find(w('rFonts'))
        if f is not None:
            name = f.get(w('cs')) or f.get(w('ascii')) or ''
        for tag in ('szCs', 'sz'):
            s = rpr.find(w(tag))
            if s is not None:
                hp = int(s.get(w('val')))
                break
    return name, hp


def is_bold(r):
    rpr = r.find(w('rPr'))
    b = rpr.find(w('b')) if rpr is not None else None
    return b is not None and b.get(w('val')) not in ('0', 'false')


def tokens(p):
    """Every w:t / w:tab / w:br inside the paragraph's direct runs, in order.
    One run may hold several (e.g. a tab and the page number)."""
    out = []
    for r in p.findall(w('r')):
        for c in r:
            if c.tag in (w('t'), w('tab')):
                out.append(c)
            elif c.tag == w('br') and c.get(w('type')) in (None, 'textWrapping'):
                out.append(c)
    return out


def kind(tok):
    return tok.tag.split('}')[1]


def lines_of(p):
    """Lines split at w:br tokens: [{'br': br token or None, 'toks': [...]}]."""
    out = [{'br': None, 'toks': []}]
    for t in tokens(p):
        if kind(t) == 'br':
            out.append({'br': t, 'toks': []})
        else:
            out[-1]['toks'].append(t)
    return out


def clean_title(s):
    return re.sub(r'^[\s\-]+', '', s).strip()


def parse_line(line):
    toks = line['toks']
    num_i = None
    for j in range(len(toks) - 1, -1, -1):
        if kind(toks[j]) == 't' and (toks[j].text or '').strip():
            if re.fullmatch(r'\d+', toks[j].text.strip()):
                num_i = j
            break
    if num_i is None:
        return None
    k = num_i - 1
    while k >= 0 and (kind(toks[k]) == 'tab' or not (toks[k].text or '').strip()):
        k -= 1
    tabs = [t for t in toks[k + 1:num_i] if kind(t) == 'tab']
    body = toks[:k + 1]
    lead = 0
    while lead < len(body) and (kind(body[lead]) == 'tab' or (body[lead].text or '').strip() in ('', '-')):
        lead += 1
    title_toks = body[lead:]
    return {'toks': toks, 'before_num': toks[:num_i], 'lead': body[:lead], 'title_toks': title_toks,
            'tabs': tabs, 'num': toks[num_i],
            'title': clean_title(''.join(t.text or '' for t in title_toks if kind(t) == 't'))}


def tab_stops(p):
    stops = []
    ppr = p.find(w('pPr'))
    if ppr is not None and ppr.find(w('tabs')) is not None:
        for t in ppr.find(w('tabs')):
            if t.get(w('val')) not in ('clear', 'bar'):
                stops.append(int(t.get(w('pos'))))
    return sorted(stops)


def next_stop(x, stops, default_tab):
    for s in stops:
        if s > x + 1:
            return s
    return (int(x) // default_tab + 1) * default_tab


def simulate(toks, stops, default_tab):
    """x (twips) after laying out the tokens; tabs jump to the next stop."""
    x = 0.0
    for t in toks:
        if kind(t) == 'tab':
            x = next_stop(x, stops, default_tab)
        elif kind(t) == 't':
            name, hp = run_style(t.getparent())
            x += width_twips(t.text or '', font_for(name, is_bold(t.getparent())), hp)
    return x


def make_run(style_tok, child):
    """A fresh run carrying the rPr of style_tok's run and one child element."""
    r = etree.Element(w('r'))
    rpr = style_tok.getparent().find(w('rPr'))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    r.append(child)
    return r


def t_el(text):
    e = etree.Element(w('t'))
    e.text = text
    e.set(XS, 'preserve')
    return e


def split_after(tok):
    """Return the run to insert after, splitting it if tok is not its last child."""
    r = tok.getparent()
    after = list(r)[list(r).index(tok) + 1:]
    if after:
        tail = etree.Element(w('r'))
        rpr = r.find(w('rPr'))
        if rpr is not None:
            tail.append(copy.deepcopy(rpr))
        for c in after:
            tail.append(c)
        r.addnext(tail)
    return r


# ---------- commands ----------

def toc_paras(paras, given):
    if given:
        return [int(x) for x in given.split(',')]
    found = []
    for i, p in enumerate(paras[:120]):
        ls = [parse_line(l) for l in lines_of(p)]
        if sum(1 for l in ls if l and l['tabs']) >= 2:
            found.append(i)
    return found


def cmd_inspect(a):
    _, _, paras, dt = load(a.docx)
    for i in toc_paras(paras, a.paras):
        p = paras[i]
        stops = tab_stops(p)
        for n, line in enumerate(lines_of(p)):
            pl = parse_line(line)
            if not pl:
                continue
            col = simulate(pl['before_num'], stops, dt)
            print('para %d line %d | %-45s | tabs %d | number %s | column %d'
                  % (i, n, pl['title'][:45], len(pl['tabs']), pl['num'].text.strip(), col))


def is_bold_heading(line, tt):
    """A short line set entirely in bold (sub-headings are often body size)."""
    spans = [s for s in line['spans'] if s['text'].strip()]
    return (bool(spans) and len(tt) <= 45 and not re.match(r'^(ข้อ|\d)', tt)
            and all(s['flags'] & 16 or 'bold' in s['font'].lower() for s in spans))


def cmd_headings(a):
    import fitz
    d = fitz.open(a.pdf)
    for i, pg in enumerate(d):
        num, heads = None, []
        for b in pg.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                t = ''.join(s['text'] for s in l['spans'])
                tt = norm(t)
                sz = max(s['size'] for s in l['spans'])
                if l['bbox'][1] < a.header_band and re.fullmatch(r'\d+', tt):
                    num = tt
                elif tt and (sz >= a.min_size or is_bold_heading(l, tt)):
                    heads.append('%s(%d%s)' % (t.strip()[:50], round(sz), '' if sz >= a.min_size else ' bold'))
        if heads:
            print('pdf %d | printed %s | %s' % (i + 1, num, ' · '.join(heads)))
    print('total pages', len(d))


def find_line(p, entry):
    want = norm(clean_title(entry['title']))
    for line in lines_of(p):
        pl = parse_line(line)
        if not pl:
            continue
        got = norm(pl['title'])
        if got == want or (entry.get('prefix') and got.startswith(want)):
            return line, pl
    return None, None


def entries_of(plan, key):
    return plan['paragraphs'][key]


def find_bare_header(p, entry):
    """Tokens of a line that matches a chapter entry by prefix but has no number yet."""
    want = norm(clean_title(entry['title']))
    for line in lines_of(p):
        toks = [t for t in line['toks']]
        texts = [t for t in toks if kind(t) == 't' and (t.text or '').strip()]
        if not texts or parse_line(line):
            continue
        if norm(clean_title(''.join(t.text or '' for t in texts))).startswith(want):
            while toks and (kind(toks[-1]) == 'tab' or not (toks[-1].text or '').strip()):
                toks.pop()
            return toks
    return None


def cmd_set(a):
    if a.output == a.docx:
        sys.exit('refusing to overwrite the input; give a different --output')
    plan = json.load(open(a.plan, encoding='utf-8'))
    z, root, paras, dt = load(a.docx)
    keys = list(plan['paragraphs'])

    def regular_template(p):
        for line in lines_of(p):
            pl = parse_line(line)
            if pl and pl['lead'] and pl['tabs'] and line['br'] is not None:
                return line, pl
        return None

    def header_template(p):
        for line in lines_of(p):
            pl = parse_line(line)
            if pl and not pl['lead'] and pl['tabs']:
                return pl
        return None

    headers_by_key = {k: header_template(paras[int(k)]) for k in keys}
    for ki, key in enumerate(keys):
        p = paras[int(key)]
        stops = tab_stops(p)
        # copy the line style of this paragraph; else the nearest earlier one
        template = regular_template(p)
        j = ki
        while template is None and j > 0:
            j -= 1
            template = regular_template(paras[int(keys[j])])
        if template is None:
            sys.exit('no regular contents line to copy the style from')
        t_line, t_pl = template
        lead_toks = t_pl['lead']
        title_tok = t_pl['title_toks'][0]
        tab_tok = t_pl['tabs'][0]
        cols = [round(simulate(pl['before_num'], stops, dt)) for pl in
                (parse_line(l) for l in lines_of(p)) if pl and pl['lead']]
        if not cols:
            cols = [round(simulate(t_pl['before_num'], tab_stops(t_pl['num'].getparent().getparent()), dt))]
        target = max(set(cols), key=cols.count)       # the column most numbers land on
        anchor = None
        for e in entries_of(plan, key):
            line, pl = find_line(p, e)
            if pl:
                old = pl['num'].text.strip()
                pl['num'].text = str(e['page'])
                print('kept  %-42s %s -> %s' % (pl['title'][:42], old, e['page']))
                anchor = pl['num']
                continue
            bare = find_bare_header(p, e) if e.get('prefix') else None
            if bare is not None:                      # chapter header typed without a number
                headers = [h for h in headers_by_key.values() if h]
                if not headers:
                    sys.exit('no numbered chapter header to copy the number style from')
                earlier = [headers_by_key[k] for k in keys[:ki] if headers_by_key[k]]
                h = earlier[-1] if earlier else headers[0]   # nearest earlier chapter's style
                hcols = [round(simulate(x['before_num'], tab_stops(x['num'].getparent().getparent()), dt))
                         for x in headers]
                htarget = max(set(hcols), key=hcols.count)
                x = simulate(bare, stops, dt)
                n = 0
                while x < htarget - 1:
                    x = next_stop(x, stops, dt)
                    n += 1
                last = [t for t in bare if kind(t) == 't'][-1]
                at = split_after(last)
                num_el = t_el(str(e['page']))
                for r in [make_run(h['tabs'][0], etree.Element(w('tab'))) for _ in range(n)] + \
                         [make_run(h['num'], num_el)]:
                    at.addnext(r)
                    at = r
                anchor = num_el
                print('numbered header %-32s %s  (tabs %d, lands %d, target %d)'
                      % (e['title'][:32], e['page'], n, x, htarget))
                continue
            if anchor is None:
                sys.exit('new entry "%s" has no matched entry before it in paragraph %s' % (e['title'], key))
            name, hp = run_style(title_tok.getparent())
            font = font_for(name, is_bold(title_tok.getparent()))
            lead_w = simulate(lead_toks, stops, dt)

            def plan_tabs(text):
                x = lead_w + width_twips(text, font, hp)
                gap = next_stop(x, stops, dt) - x
                n = 0
                while x < target - 1:
                    x = next_stop(x, stops, dt)
                    n += 1
                return n, gap, x

            title = e['title']
            n, gap, land = plan_tabs(title)
            while gap < 80 or gap > dt - 60:           # keep clear of a tab stop
                title += ' '
                n, gap, land = plan_tabs(title)
            new = [make_run(t_line['br'], etree.Element(w('br')))]
            for t in lead_toks:
                new.append(make_run(t, etree.Element(w('tab')) if kind(t) == 'tab' else t_el(t.text)))
            new.append(make_run(title_tok, t_el(title)))
            new += [make_run(tab_tok, etree.Element(w('tab'))) for _ in range(n)]
            num_el = t_el(str(e['page']))
            new.append(make_run(t_pl['num'], num_el))
            at = split_after(anchor)
            for r in new:
                at.addnext(r)
                at = r
            anchor = num_el
            print('added %-42s %s  (tabs %d, lands %d, target %d%s)'
                  % (title.strip()[:42], e['page'], n, land, target, '' if abs(land - target) < 2 else ' MISALIGNED'))
        for line in lines_of(p):
            pl = parse_line(line)
            if pl and not any(norm(pl['title']) == norm(e['title']) or
                              (e.get('prefix') and norm(pl['title']).startswith(norm(e['title'])))
                              for e in entries_of(plan, key)):
                print('WARNING: paragraph %s line "%s" is not in the plan; left unchanged' % (key, pl['title']))
    data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    with zipfile.ZipFile(a.output, 'w', zipfile.ZIP_DEFLATED) as o:
        for it in z.infolist():
            o.writestr(it, data if it.filename == 'word/document.xml' else z.read(it.filename))
    print('wrote', a.output)


def cmd_verify(a):
    import fitz
    plan = json.load(open(a.plan, encoding='utf-8'))
    d = fitz.open(a.pdf)
    pages = []
    for pg in d:
        num, heads = None, []
        for b in pg.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                tt = norm(''.join(s['text'] for s in l['spans']))
                sz = max(s['size'] for s in l['spans'])
                if l['bbox'][1] < a.header_band and re.fullmatch(r'\d+', tt):
                    num = int(tt)
                elif sz >= a.min_size or is_bold_heading(l, tt):
                    heads.append(tt)
        pages.append((num, heads))
    body = next((i for i, (n, _) in enumerate(pages) if n == 1), None)
    if body is None:
        sys.exit('no page printed as 1 found; check --header-band')
    blank_front = sum(1 for i in range(body) if not d[i].get_text().strip())
    print('pages %d; first body page (printed 1) is pdf page %d; blank pages before it: %d'
          % (len(d), body + 1, blank_front))
    bad = 0
    for key, entries in plan['paragraphs'].items():
        for e in entries:
            h = norm(e.get('heading', e['title']))
            hits = [n for n, hs in pages[body:] if any(x.startswith(h) for x in hs)]
            ok = e['page'] in hits
            bad += not ok
            if not ok or a.all:
                print('%-6s %-40s contents %-4s found on %s' % ('OK' if ok else 'CHECK', e['title'][:40], e['page'], hits[:4]))
    xs = {}
    for i in range(body):
        for b in d[i].get_text('dict')['blocks']:
            for l in b.get('lines', []):
                sp = [s for s in l['spans'] if s['text'].strip()]
                if sp and l['bbox'][1] > a.header_band and re.fullmatch(r'\d+', sp[-1]['text'].strip()):
                    xs.setdefault(round(sp[-1]['bbox'][0]), []).append(sp[-1]['text'].strip())
    if len(xs) > 1:
        bad += 1
        print('CHECK  contents numbers sit in %d columns: %s'
              % (len(xs), '; '.join('x=%d: %s' % (x, ' '.join(v[:6])) for x, v in sorted(xs.items()))))
    elif xs:
        print('contents numbers share one column (x=%d)' % list(xs)[0])
    print('verify: %d entries, %d to check' % (sum(len(v) for v in plan['paragraphs'].values()), bad))
    sys.exit(1 if bad else 0)


def cmd_sections(a):
    _, _, paras, _ = load(a.docx)
    for i, p in enumerate(paras[:a.limit]):
        sp = p.find(w('pPr') + '/' + w('sectPr'))
        if sp is None:
            continue
        t = sp.find(w('type'))
        empty = not ''.join(x.text or '' for x in p.iter(w('t'))).strip() and p.find('.//' + w('drawing')) is None
        print('para %d | section break type %s | %s' % (i, t.get(w('val')) if t is not None else 'nextPage (default)',
                                                       'empty paragraph' if empty else 'has content'))


def cmd_drop_section(a):
    if a.output == a.docx:
        sys.exit('refusing to overwrite the input; give a different --output')
    z, root, paras, _ = load(a.docx)
    p = paras[a.para]
    if p.find(w('pPr') + '/' + w('sectPr')) is None:
        sys.exit('paragraph %d carries no section break' % a.para)
    if ''.join(x.text or '' for x in p.iter(w('t'))).strip() or p.find('.//' + w('drawing')) is not None \
            or p.find('.//' + w('br')) is not None:
        sys.exit('paragraph %d is not empty; refusing' % a.para)
    p.getparent().remove(p)
    data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    with zipfile.ZipFile(a.output, 'w', zipfile.ZIP_DEFLATED) as o:
        for it in z.infolist():
            o.writestr(it, data if it.filename == 'word/document.xml' else z.read(it.filename))
    print('removed empty section paragraph %d; wrote %s' % (a.para, a.output))


def header_line(p):
    for line in lines_of(p):
        pl = parse_line(line)
        if pl and not pl['lead']:
            return pl
    return None


def cmd_restyle_header(a):
    if a.output == a.docx:
        sys.exit('refusing to overwrite the input; give a different --output')
    z, root, paras, dt = load(a.docx)
    ref, tgt = header_line(paras[a.like]), header_line(paras[a.para])
    if not ref or not tgt:
        sys.exit('both paragraphs need a numbered chapter header line (run set first)')
    style = ref['title_toks'][0].getparent().find(w('rPr'))
    for tok in tgt['title_toks']:
        r = tok.getparent()
        old = r.find(w('rPr'))
        if old is not None:
            r.remove(old)
        if style is not None:
            r.insert(0, copy.deepcopy(style))
    stops = tab_stops(paras[a.para])
    target = round(simulate(ref['before_num'], tab_stops(paras[a.like]), dt))
    for tab in tgt['tabs']:
        r = tab.getparent()
        r.remove(tab)
        if not [c for c in r if c.tag != w('rPr')]:
            r.getparent().remove(r)
    x = simulate(tgt['title_toks'], stops, dt)
    n = 0
    while x < target - 1:
        x = next_stop(x, stops, dt)
        n += 1
    at = tgt['title_toks'][-1].getparent()
    for _ in range(n):
        r = make_run(ref['tabs'][0], etree.Element(w('tab')))
        at.addnext(r)
        at = r
    data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    with zipfile.ZipFile(a.output, 'w', zipfile.ZIP_DEFLATED) as o:
        for it in z.infolist():
            o.writestr(it, data if it.filename == 'word/document.xml' else z.read(it.filename))
    print('header of paragraph %d now styled like paragraph %d; tabs %d, lands %d (target %d); wrote %s'
          % (a.para, a.like, n, x, target, a.output))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    i = sub.add_parser('inspect')
    i.add_argument('docx')
    i.add_argument('--paras')
    h = sub.add_parser('headings')
    h.add_argument('pdf')
    h.add_argument('--min-size', type=float, default=17.5)
    h.add_argument('--header-band', type=float, default=60)
    s = sub.add_parser('set')
    s.add_argument('docx')
    s.add_argument('--plan', required=True)
    s.add_argument('--output', required=True)
    v = sub.add_parser('verify')
    v.add_argument('pdf')
    v.add_argument('--plan', required=True)
    v.add_argument('--min-size', type=float, default=17.5)
    v.add_argument('--header-band', type=float, default=60)
    v.add_argument('--all', action='store_true')
    se = sub.add_parser('sections')
    se.add_argument('docx')
    se.add_argument('--limit', type=int, default=200)
    ds = sub.add_parser('drop-empty-section')
    ds.add_argument('docx')
    ds.add_argument('--para', type=int, required=True)
    ds.add_argument('--output', required=True)
    rh = sub.add_parser('restyle-header')
    rh.add_argument('docx')
    rh.add_argument('--para', type=int, required=True)
    rh.add_argument('--like', type=int, required=True)
    rh.add_argument('--output', required=True)
    a = ap.parse_args()
    {'restyle-header': cmd_restyle_header, 'inspect': cmd_inspect, 'headings': cmd_headings, 'set': cmd_set, 'verify': cmd_verify,
     'sections': cmd_sections, 'drop-empty-section': cmd_drop_section}[a.cmd](a)


if __name__ == '__main__':
    main()

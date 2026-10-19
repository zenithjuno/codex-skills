"""Explicit personal document profiles; default behavior remains unchanged."""
import json,os
from pathlib import Path
from lxml import etree
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
PROFILES=Path(__file__).resolve().parents[1]/'assets/profiles'
FLAGS=('keepNext','keepLines','pageBreakBefore','numPr','outlineLvl')


def load_profile():
    value=os.environ.get('THAI_MATH_DOCX_PROFILE')
    if not value:return {}
    path=PROFILES/(value+'.json') if value=='solve-tutoring' else Path(value)
    p=json.loads(path.read_text(encoding='utf-8'))
    if p.get('schema_version')!=1 or type(p.get('plain_paragraphs',False)) is not bool:raise ValueError('Invalid document profile')
    aligns=p.get('cases_col_aligns')
    if aligns is not None and (not isinstance(aligns,list) or not aligns or any(a not in ['left','center','right'] for a in aligns)):raise ValueError('Invalid cases_col_aligns')
    return p


def apply_profile(doc):
    p=load_profile()
    if not p.get('plain_paragraphs'):return
    for part in doc.part.package.parts:
        root=getattr(part,'element',None)
        generic=root is None
        if generic:
            if not str(part.partname).endswith('.xml') or W.encode() not in part.blob:continue
            root=etree.fromstring(part.blob)
        for pr in root.iter('{'+W+'}pPr'):
            for name in FLAGS:
                for node in list(pr.findall('{'+W+'}'+name)):pr.remove(node)
        if generic:part._blob=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)


def audit_profile(roots):
    p=load_profile();failures=[]
    if p.get('plain_paragraphs'):
        for name,root in roots.items():
            for pr in root.iter('{'+W+'}pPr'):
                for tag in FLAGS:
                    for node in pr.findall('{'+W+'}'+tag):
                        if node.get('{'+W+'}val','1') not in {'0','false','off'}:failures.append(f'{name}: plain profile forbids active {tag}')
    if p.get('cases_col_aligns'):
        for name,root in roots.items():
            for delim in root.iter('{'+M+'}d'):
                beg=delim.find('./{'+M+'}dPr/{'+M+'}begChr');end=delim.find('./{'+M+'}dPr/{'+M+'}endChr')
                if beg is None or beg.get('{'+M+'}val')!='{' or end is None or end.get('{'+M+'}val')!='':continue
                for matrix in delim.findall('./{'+M+'}e/{'+M+'}m'):
                    aligns=[]
                    for col in matrix.findall('./{'+M+'}mPr/{'+M+'}mcs/{'+M+'}mc'):
                        pr=col.find('{'+M+'}mcPr');jc=pr.find('{'+M+'}mcJc') if pr is not None else None
                        count=pr.find('{'+M+'}count') if pr is not None else None
                        aligns.extend([jc.get('{'+M+'}val') if jc is not None else None]*int(count.get('{'+M+'}val','1') if count is not None else '1'))
                    if aligns!=p['cases_col_aligns']:failures.append(f'{name}: cases columns {aligns} differ from profile {p["cases_col_aligns"]}')
                    allowed=p.get('cases_connectors',[])
                    if allowed:
                        for row in matrix.findall('{'+M+'}mr'):
                            cells=row.findall('{'+M+'}e')
                            if len(cells)!=len(p['cases_col_aligns']):failures.append(f'{name}: cases row column count differs from profile');continue
                            middle=''.join(n.text or '' for n in cells[1].iter('{'+M+'}t')).strip()
                            if middle not in allowed:failures.append(f'{name}: cases connector {middle!r} differs from profile')
    return failures

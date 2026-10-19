"""Check an exported Word PDF against explicit page anchors, not heading size."""
from __future__ import annotations
import argparse,hashlib,json,re,unicodedata,os,shutil,subprocess,sys
from pathlib import Path


def normalize(text):
    text=unicodedata.normalize('NFKC',text)
    text=re.sub(r'\s+','',text)
    return re.sub('\u0e4d([\u0e48-\u0e4b]?)\u0e32',lambda m:m[1]+'\u0e33',text)


def load_plan(path):
    plan=json.loads(Path(path).read_text(encoding='utf-8'))
    if plan.get('schema_version')!=1 or not isinstance(plan.get('anchors',[]),list):raise ValueError('Invalid page plan schema')
    if 'page_count' in plan and (type(plan['page_count']) is not int or plan['page_count']<1):raise ValueError('page_count must be a positive integer')
    for a in plan.get('anchors',[]):
        if not isinstance(a.get('text'),str) or not normalize(a['text']) or type(a.get('page')) is not int or a['page']<1:raise ValueError('Each anchor needs non-empty text and positive page')
        if a.get('match','exact') not in {'exact','prefix'}:raise ValueError('Anchor match must be exact or prefix')
    return plan


def check_pdf(path,plan=None):
    import fitz
    plan=plan or {};doc=fitz.open(path);lines=[];warnings=[]
    for i,page in enumerate(doc):
        bbox=[]
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                text=''.join(s['text'] for s in line['spans'])
                if text.strip():
                    lines.append((i+1,normalize(text),line['bbox']))
                    bbox.append(line['bbox'])
        images=page.get_image_info();bbox.extend(x['bbox'] for x in images)
        if bbox:
            bottom=max(b[3] for b in bbox)
            if bottom>page.rect.height-90:warnings.append({'page':i+1,'kind':'near-bottom','bottom_pt':round(bottom,2)})
        else:warnings.append({'page':i+1,'kind':'no-text-or-raster-image','note':'May contain vector art or intentional working space; inspect visually'})
    failures=[];anchors=[]
    if plan.get('page_count') is not None and len(doc)!=plan['page_count']:failures.append(f"Expected {plan['page_count']} pages, found {len(doc)}")
    for a in plan.get('anchors',[]):
        needle=normalize(a['text'])
        hits=[(p,b) for p,t,b in lines if (t.startswith(needle) if a.get('match','exact')=='prefix' else t==needle)]
        # Require unique identity across the file. A repeated question number or
        # a TOC entry must not accidentally satisfy a body-page assertion.
        ok=len(hits)==1 and hits[0][0]==a['page']
        anchors.append({'text':a['text'],'expected_page':a['page'],'found_pages':[p for p,b in hits],'passed':ok})
        if not ok:failures.append(f"Anchor {a['text']!r}: expected one match on page {a['page']}, found {[p for p,b in hits]}")
    return {'status':'FAIL' if failures else 'PASS' if plan else 'EXPORTED','page_count':len(doc),'anchors':anchors,'failures':failures,'warnings':warnings,'visual_review_required':True,'pdf_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def check_pdf_with_runtime(path, plan=None):
    """Use the selected PDF Python only when this build runtime lacks PyMuPDF."""
    try:
        return check_pdf(path, plan)
    except ModuleNotFoundError as exc:
        if exc.name not in {'fitz','pymupdf'}:raise
    candidates=[os.environ.get('THAI_MATH_PDF_PYTHON'),shutil.which('python3'),'/usr/bin/python3']
    for executable in dict.fromkeys(x for x in candidates if x):
        try:
            probe=subprocess.run([executable,'-c','import fitz'],capture_output=True,timeout=5)
            if probe.returncode:continue
            command=[executable,str(Path(__file__).resolve()),str(path),'--native-runtime']
            if plan is not None:command+=['--plan-json',json.dumps(plan,ensure_ascii=False)]
            checked=subprocess.run(command,capture_output=True,text=True,timeout=30)
            if checked.returncode not in (0,1):raise ValueError(checked.stderr.strip() or 'PDF runtime failed')
            return json.loads(checked.stdout)
        except (FileNotFoundError,subprocess.TimeoutExpired):continue
    raise ImportError('PyMuPDF unavailable; set THAI_MATH_PDF_PYTHON to a Python with fitz')


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('pdf');ap.add_argument('--plan');ap.add_argument('--report');ap.add_argument('--plan-json',help=argparse.SUPPRESS);ap.add_argument('--native-runtime',action='store_true',help=argparse.SUPPRESS);a=ap.parse_args(argv)
    plan=load_plan(a.plan) if a.plan else json.loads(a.plan_json) if a.plan_json else None
    r=(check_pdf if a.native_runtime else check_pdf_with_runtime)(a.pdf,plan)
    if a.report:Path(a.report).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False));return int(r['status']=='FAIL')

if __name__=='__main__':raise SystemExit(main())

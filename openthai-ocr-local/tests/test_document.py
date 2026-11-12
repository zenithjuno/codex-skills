"""Behaviour tests; run with the dedicated OpenThai interpreter (no network needed)."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import document as d
from read_local import valid_page, useful_text


def result(number, texts, confidence=.99, dropped=None):
    return dict(page=number, text='\n'.join(texts),
                lines=[dict(text=t, confidence=confidence, box=[[0,0],[100,0],[100,30],[0,30]]) for t in texts],
                dropped=dropped or [], method='ocr', ink_fraction=.1)


class Rules(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        d.atomic_json(self.root/'manifest.json', dict(identity={'model':'test'}, total_pages=3))

    def tearDown(self):
        self.temp.cleanup()

    def put(self, r):
        d.atomic_json(self.root/f"page-{r['page']:04d}.json", r)

    def test_missing_invalid_and_discarded_are_not_success(self):
        self.put(result(1, ['ข้อความทดสอบที่อ่านได้ครบ'], dropped=[dict(text='ตกหล่น', confidence=.4, reason='low_confidence')]))
        (self.root/'page-0002.json').write_text('{broken')
        report, _ = d.audit(self.root, [1,2,3])
        self.assertEqual(report['processed'], 1)
        self.assertEqual(report['incomplete_pages'], [2,3])
        self.assertIn('discarded_lines', report['pages'][0]['flags'])
        self.assertEqual(report['accuracy'], 'not_established')

    def test_confident_error_not_certified_and_sampled(self):
        self.put(result(1, ['โรงเรียนจัดทำแผนปฏิบัติการประจำปี อ่านคลาดเคลื่อนได้']))
        report, results = d.audit(self.root, [1])
        self.assertEqual(report['flagged_pages'], [])
        self.assertEqual(report['accuracy'], 'not_established')
        tasks = d.review_tasks(report, results, {'selected':[]}, 1)
        self.assertEqual(tasks[0]['reason'], 'sample')
        self.assertEqual(report['review_records'], [])

    def test_blank_and_empty_with_ink_distinct(self):
        blank = result(1, []); blank['ink_fraction'] = 0
        self.put(blank); self.put(result(2, []))
        report, _ = d.audit(self.root, [1,2])
        self.assertIn('likely_blank_needs_visual_check', report['pages'][0]['flags'])
        self.assertIn('empty_with_ink_or_unknown', report['pages'][1]['flags'])

    def test_region_review_reused_only_for_same_question(self):
        raw=result(1,['ข้อความภาษาไทยเพื่อใช้ทดสอบการตรวจภาพ']);self.put(raw)
        report,results=d.audit(self.root,[1])
        report['review_records']=[dict(page=1,result_hash=d.digest(raw),scope='task_relevant_region',
                                      verdict='matched',question_key='question-a')]
        self.assertEqual(d.review_tasks(report,results,{'selected':[]},1,'question-a'),[])
        self.assertEqual(len(d.review_tasks(report,results,{'selected':[]},1,'question-b')),1)

    def test_native_quality_gate(self):
        self.assertFalse(useful_text('just a header'))
        self.assertFalse(useful_text('ก'*80))
        self.assertFalse(useful_text('A useful long enough document about school teachers and students.\ufffd'))
        self.assertTrue(useful_text('โรงเรียนจัดทำแผนปฏิบัติการประจำปีและจัดกิจกรรมพัฒนาครูเพื่อส่งเสริมการเรียนรู้ของนักเรียน'))

    def test_aliases_context_and_overflow(self):
        results={'1':result(1,['หัวตาราง รายการ งบประมาณ','โครงการพัฒนาบุคลากร']),
                 '2':result(2,['จำนวนเงิน 125,000 บาท','ผู้รับผิดชอบฝ่ายวิชาการ'])}
        chunks = d.make_chunks(results, [])
        selected=d.select(chunks, 'พัฒนาครู', ['พัฒนาบุคลากร'], 0, 5000)
        text='\n'.join(c['text'] for c in selected['selected'])
        self.assertIn('125,000', text)
        self.assertIn('Page 2', text)
        self.assertIn('หัวตาราง', text)
        tiny=d.select(chunks, '', [], 0, 1)
        self.assertTrue(tiny['blocked_by_budget'])
        self.assertEqual(tiny['remaining'], 2)
        absent=d.select(chunks, 'ไม่มีคำนี้', ['ดาราศาสตร์'], 0, 5000)
        self.assertTrue(absent['no_matches'])
        self.assertEqual(absent['selected'], [])

    def test_batches_cover_all_chunks_without_skipping(self):
        chunks=d.make_chunks({'1':result(1,[f'บรรทัดหมายเลข {i} ข้อความภาษาไทย' for i in range(50)])},[])
        offset=0; all_selected=[]
        while offset<len(chunks):
            batch=d.select(chunks, '', [], offset, 1000)
            self.assertFalse(batch['blocked_by_budget'])
            all_selected+=batch['selected']; offset=batch['next_offset']
        self.assertEqual(all_selected, chunks)

    def test_correction_keeps_raw_and_stale_reviews_ignored(self):
        raw=result(1,['Uทคัดย่อ','เนื้อหาภาษาไทย']); self.put(raw)
        record=dict(page=1,result_hash=d.digest(raw),scope='task_relevant_region',verdict='corrected',
                    corrections=[dict(line='L1',before='Uทคัดย่อ',after='บทคัดย่อ')])
        d.atomic_json(self.root/'reviews.json',[record])
        reviews=d.current_reviews(self.root,{'1':raw})
        self.assertEqual(d.effective_lines(raw,reviews)[0][1],'บทคัดย่อ')
        self.assertEqual(raw['lines'][0]['text'],'Uทคัดย่อ')
        changed=result(1,['new reading'])
        self.assertEqual(d.current_reviews(self.root,{'1':changed}),[])
        newer=dict(record,verdict='uncertain')
        self.assertEqual(d.latest_status([record,newer],1,'task_relevant_region'),'uncertain')

    def test_no_visual_record_without_evidence_and_matching_text(self):
        raw=result(1,['อ่านผิด']); self.put(raw)
        task=dict(id='task1',page=1,result_hash=d.digest(raw))
        req=self.root/'req';req.mkdir()
        d.atomic_json(req/'request.json',dict(cache=str(self.root),tasks=[task]))
        from argparse import Namespace
        args=Namespace(request=req,task='task1',corrections=None,verdict='matched',scope='full_page',evidence='')
        with patch.object(d,'ensure_source',return_value=(None,None)):
            with self.assertRaises(ValueError):d.review(args)
            edit=self.root/'edits.json'; d.atomic_json(edit,[dict(line='L1',before='not the raw text',after='ถูก')])
            args.evidence='Compared source image';args.corrections=edit;args.verdict='corrected'
            with self.assertRaises(ValueError):d.review(args)
        self.assertFalse((self.root/'reviews.json').exists())


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.script=Path(d.__file__)
        # Block all outbound socket connections in the helper AND its subprocesses.
        (cls.root/'sitecustomize.py').write_text('import socket\ndef denied(*a,**kw): raise RuntimeError("NETWORK BLOCKED DURING TEST")\nsocket.socket.connect=denied\nsocket.create_connection=denied\n')
        cls.env=dict(os.environ,PYTHONPATH=str(cls.root),PYTHONDONTWRITEBYTECODE='1')
        from pypdf import PdfWriter
        from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
        writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 14 Tf 40 740 Td (School teacher development program budget 125,000 baht for students in the academic year 2569.) Tj ET')
        page[NameObject('/Contents')]=writer._add_object(stream)
        writer.write(cls.root/'native.pdf')
        from PIL import Image,ImageDraw,ImageFont
        fontpath=Path.home()/'Library/Fonts/THSarabunNew.ttf'
        if not fontpath.exists():
            raise unittest.SkipTest('Local Thai fixture font unavailable')
        image=Image.new('RGB',(1600,1000),'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype(str(fontpath),52)
        cls.expected=['โครงการพัฒนาครูและบุคลากร','งบประมาณ 125,000 บาท','นักเรียนชั้นมัธยมศึกษาปีที่ 4 จำนวน 40 คน']
        for i,text in enumerate(cls.expected):draw.text((100,100+i*170),text,font=font,fill='black')
        image.save(cls.root/'thai.png');image.save(cls.root/'scan.pdf',resolution=150)
        writer=PdfWriter();writer.append(cls.root/'native.pdf');writer.append(cls.root/'scan.pdf');writer.add_blank_page(width=600,height=800);writer.write(cls.root/'mixed.pdf')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def run_helper(self,*args,check=True):
        r=subprocess.run([sys.executable,str(self.script),*map(str,args)],env=self.env,capture_output=True,text=True)
        if check and r.returncode:self.fail(r.stderr)
        return r

    def test_mixed_auto_route_cache_corruption_and_query(self):
        cache=self.root/'mixed-cache'
        r=self.run_helper('prepare',self.root/'mixed.pdf','--out',cache,'--query','งบประมาณ','--term','งบประมาณ','--budget-chars','1500','--images','1')
        self.assertIn('125,000',r.stdout)
        one=d.load(cache/'page-0001.json');two=d.load(cache/'page-0002.json');three=d.load(cache/'page-0003.json')
        self.assertEqual(one['method'],'text_layer');self.assertEqual(two['method'],'ocr')
        self.assertIn('โครงการ',two['text']);self.assertIn('125,000',two['text'])
        self.assertEqual(three['text'],'')
        again=self.run_helper('prepare',self.root/'mixed.pdf','--out',cache,'--images','0')
        self.assertEqual(json.loads(again.stdout.splitlines()[0])['read_summary']['cached'],3)
        (cache/'page-0002.json').write_text('broken')
        repaired=self.run_helper('prepare',self.root/'mixed.pdf','--out',cache,'--images','0')
        self.assertEqual(json.loads(repaired.stdout.splitlines()[0])['read_summary']['processed'],1)
        mismatch=self.run_helper('prepare',self.root/'mixed.pdf','--out',cache,'--dpi','300',check=False)
        self.assertNotEqual(mismatch.returncode,0)
        (cache/'page-0003.json').unlink()
        partial=self.run_helper('inspect',cache,'--images','0')
        self.assertEqual(d.load(cache/'audit.json')['incomplete_pages'],[3])
        self.assertIn('incomplete',partial.stdout)

    def test_png_retry_crop_and_input_change_guard(self):
        cache=self.root/'png-cache'
        self.run_helper('prepare',self.root/'thai.png','--out',cache,'--images','1')
        taskfile=next((cache/'requests').glob('*/request.json'));request=d.load(taskfile)
        task=request['tasks'][0]
        reviewed=self.run_helper('review',taskfile.parent,'--task',task['id'],'--verdict','uncertain','--evidence','Test record: image still needs comparison')
        self.assertIn('recorded',reviewed.stdout)
        self.run_helper('retry',cache,'--page','1')
        retry=self.run_helper('retry',cache,'--page','1')
        self.assertEqual(json.loads(retry.stdout.splitlines()[0])['cached'],1)
        image=self.root/'crop.png'
        self.run_helper('crop',cache,'--page','1','--box','0','0','800','500','--out',image)
        self.assertTrue(image.exists())
        bad=self.run_helper('crop',cache,'--page','1','--box','0','0','9999','500','--out',image,check=False)
        self.assertNotEqual(bad.returncode,0)
        source=self.root/'thai.png';source.write_bytes(source.read_bytes()+b'changed')
        stale=self.run_helper('inspect',cache,'--images','1',check=False)
        self.assertNotEqual(stale.returncode,0)


if __name__=='__main__':unittest.main()

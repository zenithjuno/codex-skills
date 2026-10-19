from pathlib import Path
import json,os,sys,tempfile,unittest,subprocess
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import word_export_pdf as exporter
import word_page_check as pages

class WordChecks(unittest.TestCase):
 def test_applescript_path_is_escaped(self):
  self.assertEqual('"a\\"b\\\\c"',exporter.apple_string('a"b\\c'))
 def test_source_cannot_be_output(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'in.docx';p.write_bytes(b'original')
   self.assertEqual('ERROR',exporter.export_pdf(p,p)['status'])
   self.assertEqual(b'original',p.read_bytes())
 def test_unavailable_word_is_not_layout_pass(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'in.docx';p.write_bytes(b'original')
   with patch.object(exporter.sys,'platform','linux'):
    self.assertEqual('SKIPPED',exporter.export_pdf(p,Path(d)/'out.pdf')['status'])
 def test_permission_denial_is_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'in.docx';p.write_bytes(b'original')
   with patch.object(exporter.sys,'platform','darwin'),patch.object(exporter.Path,'exists',return_value=True),patch.object(exporter.Path,'is_dir',return_value=True),patch.object(exporter.tempfile,'mkdtemp',side_effect=PermissionError('denied')):
    r=exporter.export_pdf(p,Path(d)/'out.pdf')
   self.assertEqual('BLOCKED',r['status']);self.assertTrue(r['source_unchanged'])
 def test_timeout_closes_only_private_copy_without_source_save(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'in.docx';p.write_bytes(b'original');work=Path(d)/'owned';work.mkdir()
   with patch.object(exporter.sys,'platform','darwin'),patch.object(exporter.Path,'exists',return_value=True),patch.object(exporter.Path,'is_dir',return_value=True),patch.object(exporter.tempfile,'mkdtemp',return_value=str(work)),patch.object(exporter.subprocess,'run',side_effect=[subprocess.TimeoutExpired('osascript',45),SimpleNamespace(returncode=0)]) as run:
    r=exporter.export_pdf(p,Path(d)/'out.pdf')
   self.assertEqual('BLOCKED',r['status']);self.assertTrue(r['source_unchanged']);self.assertFalse(work.exists())
   export_script=run.call_args_list[0].kwargs['input'];cleanup_script=run.call_args_list[1].kwargs['input']
   self.assertNotIn('active document',export_script);self.assertNotIn('quit',export_script)
   self.assertIn(str(work/'input.docx'),cleanup_script);self.assertIn('saving no',cleanup_script)
 def test_explicit_anchors_work_at_body_size_and_fail_wrong_page(self):
  import fitz
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.pdf';doc=fitz.open()
   doc.new_page().insert_text((72,72),'Example 93.',fontsize=12)
   doc.new_page().insert_text((72,72),'Example 94.',fontsize=12);doc.save(p);doc.close()
   good={'page_count':2,'anchors':[{'text':'Example 94.','page':2}]}
   self.assertEqual('PASS',pages.check_pdf(p,good)['status'])
   good['anchors'][0]['page']=1
   self.assertEqual('FAIL',pages.check_pdf(p,good)['status'])
 def test_duplicate_identity_cannot_silently_pass(self):
  import fitz
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.pdf';doc=fitz.open()
   for _ in range(2):doc.new_page().insert_text((72,72),'Example 93.')
   doc.save(p);doc.close()
   self.assertEqual('FAIL',pages.check_pdf(p,{'anchors':[{'text':'Example 93.','page':1}]})['status'])
 def test_normalize_thai_sara_am(self):
  self.assertEqual(pages.normalize('ซ้ำ'),pages.normalize('ซ ํ ้ า'))
 def test_empty_working_page_is_warning_not_failure(self):
  import fitz
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.pdf';doc=fitz.open();doc.new_page();doc.save(p);doc.close()
   r=pages.check_pdf(p,{'page_count':1})
   self.assertEqual('PASS',r['status']);self.assertTrue(r['warnings']);self.assertTrue(r['visual_review_required'])

if __name__=='__main__':unittest.main()

from pathlib import Path
import os,sys,unittest,tempfile
from zipfile import ZipFile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from lxml import etree as E
from document_profile import apply_profile,audit_profile
from thai_math_docx_builder import new_document,math_omml,save_docx

class Profiles(unittest.TestCase):
 def test_default_does_not_strip_paragraph_controls(self):
  with patch.dict(os.environ,{},clear=True):
   d=new_document();p=d.add_paragraph('text');p.paragraph_format.keep_with_next=True
   apply_profile(d)
   self.assertTrue(p.paragraph_format.keep_with_next)
 def test_plain_profile_normalizes_only_when_requested_and_detects_mutation(self):
  with patch.dict(os.environ,{'THAI_MATH_DOCX_PROFILE':'solve-tutoring'}):
   d=new_document();p=d.add_paragraph('text');p.paragraph_format.keep_with_next=True
   self.assertTrue(audit_profile({'document':d._element}))
   apply_profile(d);self.assertFalse(audit_profile({'document':d._element}))
   p.paragraph_format.page_break_before=True
   self.assertTrue(audit_profile({'document':d._element}))
 def test_saved_profile_also_normalizes_generic_effects_styles(self):
  with patch.dict(os.environ,{'THAI_MATH_DOCX_PROFILE':'solve-tutoring'}),tempfile.TemporaryDirectory() as tmp:
   d=new_document();d.add_paragraph('text').paragraph_format.keep_with_next=True
   out=save_docx(d,Path(tmp)/'sheet.docx')
   with ZipFile(out) as z:
    roots={name:E.fromstring(z.read(name)) for name in z.namelist() if name.startswith('word/') and name.endswith('.xml')}
   self.assertFalse(audit_profile(roots))
 def test_cases_profile_does_not_accept_wrong_connector_or_columns(self):
  W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';M='http://schemas.openxmlformats.org/officeDocument/2006/math'
  with patch.dict(os.environ,{'THAI_MATH_DOCX_PROFILE':'solve-tutoring'}):
   good={'kind':'cases','rows':[[['1'],[{'kind':'thai_text','text':'เมื่อ'}],['x≥0']]]}
   root=E.fromstring(f'<r xmlns:m="{M}" xmlns:w="{W}">{math_omml(good)}</r>')
   self.assertFalse(audit_profile({'document':root}))
   bad={'kind':'cases','rows':[[['1'],[','],['x≥0']]],'col_aligns':['left','left','left']}
   root=E.fromstring(f'<r xmlns:m="{M}" xmlns:w="{W}">{math_omml(bad)}</r>')
   self.assertTrue(audit_profile({'document':root}))

if __name__=='__main__':unittest.main()

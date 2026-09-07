import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_project_context import CLI

ROOT=Path(__file__).resolve().parents[1]
HELPER=CLI.parents[2]/'build-changelog/scripts/build_context.py'


def make_control(root):
    index='| Scope | Active contract | Current source | Enforcement |\n|---|---|---|---|\n| cross-cutting | `DEC-001` | `BLUEPRINT.md §Rules` | review-only |\n'
    (root/'AGENTS.md').write_text('# Router\nRead BUILD-CONTROL.md\n')
    (root/'BLUEPRINT.md').write_text('# Blueprint\n## Task contract\nGoal: fix the paired checkers; approved scope checker only.\n## Rules\nDEC-001 — reject empty input in both client and server.\n## Active Contract Index\n'+index)
    (root/'PLAN.md').write_text('# Plan\n## Active frontier\n| Stage | Lifecycle | Outcome |\n|---|---|---|\n| S01 | ACTIVE | Fix checkers |\n## S01 — Fix checkers\nCONTRACT DEC-001. Read client.py and server.py; verify both with pair-check. No deployment.\n')
    (root/'BUILD-CONTROL.md').write_text('# Control\n## ENTRYPOINT\n- Slug: `fixture`\n- Control schema: `2`\n- Project root: `.`\n- Blueprint: `BLUEPRINT.md`\n- Construction plan: `PLAN.md`\n- Task contract: `BLUEPRINT.md §Task contract`\n- AGENTS instructions: `AGENTS.md`\n## PROJECT MAP\n### Current truth surfaces\n| Role | Canonical source | Refresh trigger | Coverage |\n|---|---|---|---|\n| product-contract | `BLUEPRINT.md` | change | semantic |\n## STATE\n- Current stage: `S01`\n## VERSION CONTROL\n- Mode: `snapshot`\n## ACTIVE CONTRACT INDEX\n'+index+'## OPEN CHANGES\n- none\n## HISTORY INDEX\n- none\n')


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);make_control(self.root)
    def tearDown(self):self.tmp.cleanup()
    def cli(self,*args):
        r=subprocess.run([sys.executable,str(CLI),*args,'--root',str(self.root),'--control','BUILD-CONTROL.md'],capture_output=True)
        self.assertEqual(r.stderr,b'');return r.returncode,json.loads(r.stdout)

    def test_T19_supported_control(self):
        code,r=self.cli('check');self.assertEqual(code,0,r)
        self.assertEqual(r['coverage_by_dimension']['full-doctor'],'unavailable')
        code,r=self.cli('context','--route','resume');self.assertEqual(code,0,r)
        text=''.join(x['text'] for x in r['sources'])
        for required in ['client.py and server.py','reject empty input','approved scope','pair-check']:
            self.assertIn(required,text)

    def test_T08_lifecycle_error(self):
        p=self.root/'PLAN.md';p.write_text(p.read_text().replace('| S01 | ACTIVE |','| S01 | PASS |'))
        code,r=self.cli('check');self.assertEqual(code,1)
        self.assertTrue(any(x['check']=='stage-lifecycle' for x in r['findings']))

    def test_T14_cumulative_delegated_budget(self):
        code,r=self.cli('check','--max-read-bytes','1100')
        self.assertEqual(code,3,r);self.assertLessEqual(r['metrics']['source_read_bytes'],1100)

    def test_T14_indirect_big_source(self):
        p=self.root/'BLUEPRINT.md';p.write_text(p.read_text()+'big'*100000)
        code,r=self.cli('check','--max-read-bytes','5000');self.assertEqual(code,3,r)
        self.assertLessEqual(r['metrics']['source_read_bytes'],5000)

    def test_T15_indirect_external_source(self):
        with tempfile.TemporaryDirectory() as other:
            bp=Path(other)/'BLUEPRINT.md';bp.write_bytes((self.root/'BLUEPRINT.md').read_bytes())
            (self.root/'BLUEPRINT.md').unlink();(self.root/'BLUEPRINT.md').symlink_to(bp)
            code,r=self.cli('check');self.assertEqual(code,1,r)
            self.assertEqual(self.cli('check','--allow-read',other)[0],0)

    def test_T19_missing_helper(self):
        self.assertEqual(self.cli('check','--build-helper',str(self.root/'absent.py'))[0],3)

    def test_T19_old_helper_unsupported(self):
        old=self.root/'old.py';old.write_text('import sys\nprint("unsupported flags")\nsys.exit(2)\n')
        code,r=self.cli('check','--build-helper',str(old));self.assertEqual(code,3)

    def test_T14_runaway_helper(self):
        fake=self.root/'flood.py';fake.write_text('while True: print("x"*4096, flush=True)\n')
        code,r=self.cli('check','--build-helper',str(fake),'--max-output-bytes','2000')
        self.assertEqual(code,3);self.assertEqual(r['coverage'],'partial')

    def test_T14_hung_helper(self):
        fake=self.root/'hang.py';fake.write_text('import time\ntime.sleep(5)\n')
        code,r=self.cli('check','--build-helper',str(fake),'--timeout','0.1')
        self.assertEqual(code,3);self.assertEqual(r['coverage'],'partial')

    def test_T14_timeout_then_trace_budget(self):
        fake=self.root/'hang.py';fake.write_text('import time\ntime.sleep(5)\n')
        trace=self.root/'trace.jsonl';trace.write_text(json.dumps(dict(schema_version=1,event_id='e',session_id='s',operation='read',source='a',selector='b',source_revision=None,observed_bytes=0,truncated=None,purpose='unknown',outcome='unknown'))+'\n')
        code,r=self.cli('check','--build-helper',str(fake),'--timeout','0.05','--max-read-bytes','2000','--trace',str(trace))
        self.assertEqual(code,3);self.assertLessEqual(r['metrics']['source_read_bytes'],2000)

    def test_T14_closed_stream_hang(self):
        fake=self.root/'silent.py';fake.write_text('import os,time\nos.close(1);os.close(2);time.sleep(5)\n')
        code,r=self.cli('check','--build-helper',str(fake),'--timeout','0.05','--max-output-bytes','300')
        self.assertEqual(code,3);self.assertEqual(r['coverage'],'partial')

    def test_T15_git_metadata_is_not_read_by_bounded_health(self):
        p=self.root/'BUILD-CONTROL.md';s=p.read_text().replace('- Mode: `snapshot`','- Mode: `git`\n- Repository root: `.`\n- Branch: `main`')
        p.write_text(s)
        with tempfile.TemporaryDirectory() as outside:
            ext=Path(outside)/'gitdata'
            subprocess.run(['git','init','--quiet','--separate-git-dir',str(ext),str(self.root)],check=True)
            (ext/'HEAD').write_text('ref: refs/heads/private-outside-branch\n')
            code,r=self.cli('check')
            self.assertEqual(r['coverage_by_dimension'].get('version-control'),'unavailable',r)
            self.assertNotIn('private-outside-branch',json.dumps(r))

    def test_T19_bad_schema(self):
        p=self.root/'BUILD-CONTROL.md';p.write_text(p.read_text().replace('schema: `2`','schema: `77`'))
        self.assertEqual(self.cli('check')[0],3)

    def test_T28_index_mutation(self):
        p=self.root/'BUILD-CONTROL.md';p.write_text(p.read_text().replace('`DEC-001`','`DEC-999`'))
        self.assertEqual(self.cli('check')[0],1)
        make_control(self.root);self.assertEqual(self.cli('check')[0],0)

    def test_T14_indirect_later_contract_budget(self):
        for name in ['BUILD-CONTROL.md','BLUEPRINT.md']:
            p=self.root/name;p.write_text(p.read_text().replace('`BLUEPRINT.md §Rules`','`SPEC.md §Rules`'))
        (self.root/'SPEC.md').write_text('## Rules\n'+'large'*30000)
        code,r=self.cli('check','--max-read-bytes','7000')
        self.assertEqual(code,3,r);self.assertLessEqual(r['metrics']['source_read_bytes'],7000)

    def test_T09_delegated_duplicate_heading(self):
        p=self.root/'BLUEPRINT.md';p.write_text(p.read_text()+'\n## Rules\nDuplicate.\n')
        self.assertEqual(self.cli('check')[0],1)

    def test_T07_duplicate_registered_role(self):
        p=self.root/'BUILD-CONTROL.md';s=p.read_text();row='| product-contract | `BLUEPRINT.md` | change | semantic |'
        p.write_text(s.replace(row,row+'\n'+row))
        self.assertEqual(self.cli('check')[0],1)

    def test_T27_bounded_protocol_counters(self):
        r=subprocess.run([sys.executable,str(HELPER),'validate',str(self.root/'BUILD-CONTROL.md'),'--read-root',str(self.root)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        m=json.loads(r.stderr.split('BOUNDED_READ_METRICS ')[1])
        self.assertEqual(m['bytes'],sum((self.root/p).stat().st_size for p in ['AGENTS.md','BLUEPRINT.md','PLAN.md','BUILD-CONTROL.md'])-(self.root/'AGENTS.md').stat().st_size)
        # Legacy validator checks existence only for AGENTS; do not claim it read it.

if __name__=='__main__':unittest.main()

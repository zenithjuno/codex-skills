import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = (ROOT if (ROOT/'scripts/project_context.py').is_file() else ROOT/'candidate-skills/project-bootstrap')/'scripts/project_context.py'


def config():
    return dict(schema_version=1, profile='coding', entrypoint='AGENTS.md',
        bindings=[dict(scope='app',role=role,path='CURRENT.md',section=section)
                  for role,section in [('goal','Goal'),('current-state','State'),('contract','Contract'),('verification','Verify')]],
        routes=[dict(id='resume',scope='app',purpose='Resume work',reads=[dict(path='CURRENT.md',section='Task')],
                     verification_binding=dict(scope='app',role='verification'))])


def setup(root):
    (root/'AGENTS.md').write_text('# Router\nUse project-context.json for declared routes.\n')
    (root/'CURRENT.md').write_text('# Current\n## Goal\nImprove paired checker.\n## State\nApproved: checker only. Next: compare both checkers.\n## Contract\nClient and server must agree; retain the empty-answer check.\n## Verify\nRun pair-check; do not deploy.\n## Task\nRead client.py and server.py before edits.\n')
    (root/'project-context.json').write_text(json.dumps(config()))


def event(i, **kw):
    e=dict(schema_version=1,event_id=str(i),session_id='s',operation='read',source='CURRENT.md',selector='State',
           source_revision='hash-a',observed_bytes=123,truncated=False,purpose='resume',outcome='no-new-evidence')
    e.update(kw)
    return e


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        setup(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args, root=None, limit=16384):
        r=subprocess.run([sys.executable,str(CLI),*args,'--root',str(root or self.root),'--max-output-bytes',str(limit)],capture_output=True)
        self.assertLessEqual(len(r.stdout),limit)
        self.assertFalse(r.stderr, r.stderr.decode())
        return r.returncode,json.loads(r.stdout) if r.stdout else {},r.stdout

    def edit(self, func):
        f=self.root/'project-context.json';d=json.loads(f.read_text());func(d);f.write_text(json.dumps(d))

    def trace(self,*events):
        p=self.root/'trace.jsonl';p.write_text('\n'.join(json.dumps(e) for e in events)+'\n');return p

    def checks(self,r):
        return {x['check'] for x in r['findings']}

    def test_T02_context_required_facts(self):
        code,r,_=self.cli('context','--route','resume')
        self.assertEqual(code,0)
        text=''.join(s['text'] for s in r['sources'])
        for fact in ['Improve paired','Approved:','both checkers','empty-answer','pair-check','client.py and server.py']:
            self.assertIn(fact,text)
        self.assertEqual(r['metrics']['source_files'],2)
        self.assertEqual(r['coverage_by_dimension']['session'],'unavailable')

    def test_T03_T13_readonly(self):
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()}
        self.assertEqual(self.cli('check')[0],0)
        self.cli('context','--route','resume')
        self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()})

    def test_T07_duplicate_owner(self):
        self.edit(lambda d:d['bindings'].append(dict(d['bindings'][0],path='OTHER.md')))
        code,r,_=self.cli('check');self.assertEqual(code,1);self.assertIn('duplicate-owner',self.checks(r))

    def test_T07_distinct_scopes_valid(self):
        self.edit(lambda d:d['bindings'].append(dict(d['bindings'][0],scope='other')))
        self.assertEqual(self.cli('check')[0],0)

    def test_T08_mirror_disagreement_and_equal(self):
        (self.root/'MIRROR.md').write_text('## State\nObsolete stage complete.\n')
        self.edit(lambda d:d.update(mirrors=[dict(scope='app',role='current-state',path='MIRROR.md',section='State')]))
        code,r,_=self.cli('check');self.assertEqual(code,1);self.assertIn('mirror-drift',self.checks(r))
        (self.root/'MIRROR.md').write_text('## State\nApproved: checker only. Next: compare both checkers.\n')
        self.assertEqual(self.cli('check')[0],0)

    def test_T09_section_ambiguity(self):
        with (self.root/'CURRENT.md').open('a') as f:f.write('\n## Task\nDuplicate.\n')
        code,r,_=self.cli('context','--route','resume');self.assertEqual(code,1)
        self.assertTrue(any('2 matches' in f['impact'] for f in r['findings']))

    def test_T09_missing_section(self):
        self.edit(lambda d:d['bindings'][0].update(section='Gone'))
        self.assertEqual(self.cli('check')[0],1)

    def test_T10_history_not_read(self):
        (self.root/'history').mkdir();(self.root/'history/HUGE.md').write_text('unused'*100000)
        self.assertEqual(self.cli('context','--route','resume')[0],0)

    def test_T11_missing_target(self):
        (self.root/'CURRENT.md').unlink();code,r,_=self.cli('check');self.assertEqual(code,1)
        self.assertIn('source',self.checks(r))

    def test_T12_input_budget(self):
        (self.root/'CURRENT.md').write_text('ไทย🙂'*100000)
        code,r,_=self.cli('check','--max-read-bytes','10000');self.assertEqual(code,3)
        self.assertLessEqual(r['metrics']['source_read_bytes'],10000)
        self.assertEqual(r['coverage'],'partial');self.assertTrue(r['next_reads'])

    def test_T12_output_budget(self):
        (self.root/'CURRENT.md').write_text((self.root/'CURRENT.md').read_text().replace('Improve paired checker.','ไทย🙂'*1500))
        code,r,_=self.cli('context','--route','resume',limit=1400)
        self.assertEqual(code,3);self.assertEqual(r['coverage'],'partial')

    def test_T12_tiny_limit(self):
        code,r,out=self.cli('check',limit=3);self.assertEqual(code,3);self.assertEqual(out,b'{}\n')

    def test_T13_report_only_explicit_new_path(self):
        report=self.root/'report.json';self.assertEqual(self.cli('check','--report',str(report))[0],0)
        before=report.read_bytes();self.assertEqual(self.cli('check','--report',str(report))[0],2)
        self.assertEqual(before,report.read_bytes())

    def test_T15_escape_and_allowlist(self):
        with tempfile.TemporaryDirectory() as other:
            path=Path(other)/'outside.md';path.write_text('## Goal\nExternal fact\n')
            (self.root/'LINK.md').symlink_to(path)
            self.edit(lambda d:d['bindings'][0].update(path='LINK.md'))
            self.assertEqual(self.cli('check')[0],1)
            self.assertEqual(self.cli('check','--allow-read',other)[0],0)

    def test_T15_redirect_cycle_and_backlink(self):
        (self.root/'AGENTS.md').write_text('# Router\nRead [bridge](CLAUDE.md).\n')
        (self.root/'CLAUDE.md').write_text('# Bridge\nRead [owner](AGENTS.md).\n')
        code,r,_=self.cli('check');self.assertEqual(code,1);self.assertIn('redirect-cycle',self.checks(r))
        (self.root/'AGENTS.md').write_text('# Router\nFull role instructions\nCurrent task route\nOther work route\nBacklink [bridge](CLAUDE.md).\n')
        self.assertEqual(self.cli('check')[0],0)

    def test_T16_same_revision_reread(self):
        p=self.trace(event(1),event(2));code,r,_=self.cli('check','--trace',str(p))
        self.assertEqual(code,0);f=[f for f in r['findings'] if f['check']=='reread'][0]
        self.assertEqual(f['confidence'],'inferred');self.assertEqual(len(f['evidence']),2)

    def test_T17_changed_revision_checkpoint_unknown(self):
        for events in [(event(1),event(2,source_revision='other')), (event(1),event(2,operation='checkpoint'),event(3)), (event(1,source_revision=None),event(2,source_revision=None))]:
            p=self.trace(*events);code,r,_=self.cli('check','--trace',str(p))
            self.assertEqual(code,0);self.assertNotIn('reread',self.checks(r))

    def test_T18_observed_failures_truncation_history(self):
        p=self.trace(event(1,status='failure'),event(2,status='failure',truncated=True),event(3,source='history/P01.md',purpose='current-state'))
        code,r,_=self.cli('check','--trace',str(p));self.assertEqual(code,0)
        self.assertTrue({'failed-loop','truncated-event','history-for-state'}<=self.checks(r))

    def test_T18_unknown_outcome_is_not_failure(self):
        p=self.trace(event(1),event(2));r=self.cli('check','--trace',str(p))[1]
        self.assertNotIn('failed-loop',self.checks(r))

    def test_T18_missing_trace_not_clean(self):
        code,r,_=self.cli('check','--trace','missing.jsonl');self.assertNotEqual(code,0)
        self.assertEqual(r['coverage'],'partial');self.assertEqual(r['coverage_by_dimension']['session'],'unavailable')

    def test_T21_empty_inspect_no_stack(self):
        with tempfile.TemporaryDirectory() as d:
            code,r,_=self.cli('inspect',root=Path(d));self.assertEqual(code,0)
            self.assertEqual(list(Path(d).iterdir()),[]);self.assertIn('uninitialized',self.checks(r))

    def test_T22_generic_profile(self):
        self.edit(lambda d:d.update(profile='generic'))
        self.assertEqual(self.cli('context','--route','resume')[0],0)
        self.assertFalse((self.root/'src').exists())

    def test_T24_nondefault_cwd(self):
        r=subprocess.run([sys.executable,str(CLI),'context','--root',str(self.root),'--route','resume'],cwd='/',capture_output=True)
        self.assertEqual(r.returncode,0)

    def test_T28_bad_binding_negative_control(self):
        good=self.root/'CURRENT.md';good.rename(self.root/'away')
        self.assertEqual(self.cli('check')[0],1)
        (self.root/'away').rename(good);self.assertEqual(self.cli('check')[0],0)

    def test_T29_usage_unknown_and_cache_subset(self):
        p=self.trace(event(1,usage=dict(provider='example',model='fixture',input_tokens=100,cached_input_tokens=80,output_tokens=4,accounting_semantics='input_includes_cached')))
        r=self.cli('check','--trace',str(p))[1]
        self.assertIsNone(r['metrics']['trace']['token_totals']);self.assertIsNone(r['metrics']['trace']['monetary_savings'])
        p=self.trace(event(2,usage=dict(input_tokens=None,accounting_semantics='unknown')))
        self.assertEqual(self.cli('check','--trace',str(p))[0],0)

    def test_T29_duplicate_and_malformed(self):
        for events in [(event(1),event(1)),(event(1,schema_version=2),),(event(1,observed_bytes=-1),)]:
            p=self.trace(*events);self.assertEqual(self.cli('check','--trace',str(p))[0],2)
        p=self.root/'trace.jsonl';p.write_text('not json\n');self.assertEqual(self.cli('check','--trace',str(p))[0],2)

    def test_invalid_timeout_is_bounded_input_error(self):
        self.assertEqual(self.cli('check','--timeout','nan')[0],2)

    def test_T06_config_route_does_not_read_code(self):
        (self.root/'SETTINGS.md').write_text('## Difficulty\nDifficulty belongs in Config sheet, not checker code.\n')
        self.edit(lambda d:d.update(routes=d['routes']+[dict(id='difficulty',scope='settings',purpose='Adjust difficulty',reads=[dict(path='SETTINGS.md',section='Difficulty')],verification_binding=None)]))
        code,r,_=self.cli('context','--route','difficulty');self.assertEqual(code,0)
        self.assertEqual(len(r['sources']),1);self.assertIn('Config sheet',r['sources'][0]['text'])

    def test_T18_unfocused_search(self):
        p=self.trace(event(1,operation='search',purpose='unknown',outcome='no-new-evidence'))
        self.assertIn('unfocused-search',self.checks(self.cli('check','--trace',str(p))[1]))

    def test_T24_thai_space_root(self):
        nested=self.root/'โปรเจกต์ มีช่องว่าง';nested.mkdir();setup(nested)
        self.assertEqual(self.cli('context','--route','resume',root=nested)[0],0)

    def test_invalid_arguments_respect_output_cap(self):
        code,r,_=self.cli('check','--unknown-flag',limit=300)
        self.assertEqual(code,2)

    def test_invalid_equals_limit_is_bounded(self):
        r=subprocess.run([sys.executable,str(CLI),'check','--root',str(self.root),'--unknown','--max-output-bytes=30'],capture_output=True)
        self.assertEqual(r.returncode,2);self.assertLessEqual(len(r.stdout)+len(r.stderr),30)

    def test_config_verification_shape(self):
        self.edit(lambda d:d['routes'][0].update(verification_binding='verification'))
        self.assertEqual(self.cli('check')[0],2)

    def test_source_file_limit(self):
        code,r,_=self.cli('check','--max-files','1');self.assertEqual(code,3)
        self.assertEqual(r['metrics']['source_files'],1)

    def test_T31_check_stats_whole_file_pointers(self):
        (self.root/'HISTORY.md').write_text('# History\n'+'old'*200000)
        self.edit(lambda d:d['bindings'].append(dict(scope='app',role='history',path='HISTORY.md',section=None)))
        code,r,_=self.cli('check');self.assertEqual(code,0,r)
        self.assertLess(r['metrics']['source_read_bytes'],10000)
        (self.root/'HISTORY.md').unlink()
        code,r,_=self.cli('check');self.assertEqual(code,1);self.assertIn('source',self.checks(r))

    def test_T31_context_still_reads_whole_file_pointer(self):
        (self.root/'NOTES.md').write_text('whole file body\n')
        self.edit(lambda d:d['routes'][0]['reads'].append(dict(path='NOTES.md',section=None)))
        code,r,_=self.cli('context','--route','resume');self.assertEqual(code,0)
        self.assertIn('whole file body',''.join(s['text'] for s in r['sources']))

    def test_T32_marker_pointer(self):
        (self.root/'CURRENT.md').write_text('# Current\n## Goal\nImprove paired checker.\n<!-- project-bootstrap:state:start -->\nApproved: checker only.\n<!-- project-bootstrap:state:end -->\n## Contract\nc\n## Verify\nv\n## Task\nt\n')
        self.edit(lambda d:d['bindings'][1].update(section=None,marker='state'))
        code,r,_=self.cli('context','--route','resume');self.assertEqual(code,0,r)
        src=[s for s in r['sources'] if s.get('marker')=='state'][0]
        self.assertEqual(src['text'],'Approved: checker only.\n');self.assertEqual(src['line_start'],5)
        self.edit(lambda d:d['bindings'][1].update(marker='absent'))
        self.assertEqual(self.cli('check')[0],1)
        self.edit(lambda d:d['bindings'][1].update(section='State',marker='state'))
        self.assertEqual(self.cli('check')[0],2)

    def test_T33_section_ignores_fenced_headings(self):
        (self.root/'CURRENT.md').write_text('# Current\n## Goal\nrun:\n```sh\n# comment\nnpm test\n```\nImprove paired checker.\n## State ##\nApproved: checker only. Next: compare both checkers.\n## Contract\nc\n## Verify\nv\n## Task\nt\n')
        code,r,_=self.cli('context','--route','resume');self.assertEqual(code,0,r)
        goal=[s for s in r['sources'] if s['section']=='Goal'][0]['text']
        self.assertIn('Improve paired checker',goal);self.assertNotIn('Approved',goal)

    def test_T34_markdown_format(self):
        r=subprocess.run([sys.executable,str(CLI),'context','--root',str(self.root),'--route','resume','--format','md'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout)
        self.assertIn('## ',r.stdout);self.assertIn('Improve paired checker.',r.stdout);self.assertNotIn('"sha256"',r.stdout)

    def test_T35_default_output_budget_per_command(self):
        r=subprocess.run([sys.executable,str(CLI),'context','--root',str(self.root),'--route','resume'],capture_output=True)
        self.assertLessEqual(len(r.stdout),65536)
        r=subprocess.run([sys.executable,str(CLI),'check','--root',str(self.root)],capture_output=True)
        self.assertLessEqual(len(r.stdout),16384)

    def test_T36_blocks_and_undeclared(self):
        (self.root/'AGENTS.md').write_text('# Router\n<!-- project-bootstrap:route:start -->\nUse project-context.json.\n<!-- project-bootstrap:route:end -->\n')
        code,r,_=self.cli('blocks');self.assertEqual(code,0,r)
        self.assertEqual([b['name'] for b in r['blocks']],['route']);self.assertEqual(r['blocks'][0]['line_start'],3)
        code,r,_=self.cli('check');self.assertEqual(code,0)
        self.assertIn('undeclared-block',self.checks(r))
        self.edit(lambda d:d['bindings'].append(dict(scope='app',role='routing',path='AGENTS.md',section=None,marker='route')))
        code,r,_=self.cli('check');self.assertEqual(code,0);self.assertNotIn('undeclared-block',self.checks(r))

    def test_T36_duplicate_and_malformed_blocks(self):
        (self.root/'AGENTS.md').write_text('# Router\n<!-- project-bootstrap:now:start -->\nA\n<!-- project-bootstrap:now:end -->\n')
        (self.root/'OTHER.md').write_text('<!-- project-bootstrap:now:start -->\nB\n<!-- project-bootstrap:now:end -->\n')
        code,r,_=self.cli('check','--path','OTHER.md');self.assertEqual(code,0)
        self.assertIn('duplicate-block',self.checks(r))
        (self.root/'OTHER.md').write_text('<!-- project-bootstrap:now:start -->\nB\n')
        code,r,_=self.cli('check','--path','OTHER.md');self.assertEqual(code,1);self.assertIn('malformed-block',self.checks(r))

    def test_T36_blocks_hashes_stable_for_idempotence(self):
        (self.root/'AGENTS.md').write_text('# Router\n<!-- project-bootstrap:route:start -->\nUse it.\n<!-- project-bootstrap:route:end -->\n')
        a=self.cli('blocks')[1]['blocks'];b=self.cli('blocks')[1]['blocks'];self.assertEqual(a,b)
        with (self.root/'AGENTS.md').open('a') as f:f.write('unowned line\n')
        self.assertEqual(self.cli('blocks')[1]['blocks'],a)


if __name__ == '__main__':
    unittest.main()

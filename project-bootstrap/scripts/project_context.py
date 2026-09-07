#!/usr/bin/env python3
"""Bounded, read-only project routing and context diagnostics (stdlib only)."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time


class InputError(Exception):
    pass


class Partial(Exception):
    pass


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def select_section(text, section):
    if section is None:
        return text, 1, len(text.splitlines())
    lines = text.splitlines(keepends=True)
    matches = [(i, len(m[1])) for i, line in enumerate(lines)
               if (m := re.match(r'^(#{2,3}) (.+?)\s*$', line)) and m[2] == section]
    if len(matches) != 1:
        raise InputError(f'section {section!r}: {len(matches)} matches (expected one)')
    start, level = matches[0]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        m = re.match(r'^(#{1,6}) ', lines[i])
        if m and len(m[1]) <= level:
            end = i
            break
    return ''.join(lines[start:end]), start + 1, end


class Reader:
    def __init__(self, root, allow, budget, max_files):
        self.root = root.resolve()
        self.allow = [self.root] + [p.resolve() for p in allow]
        self.budget, self.max_files = budget, max_files
        self.used = 0
        self.cache = {}

    def resolve(self, path):
        p = Path(path)
        p = (p if p.is_absolute() else self.root / p).resolve()
        if not any(p == a or a in p.parents for a in self.allow):
            raise InputError(f'outside declared read roots: {p}')
        return p

    def load(self, path):
        p = self.resolve(path)
        if p in self.cache:
            return p, self.cache[p]
        if len(self.cache) >= self.max_files:
            raise Partial('source file limit reached')
        try:
            if not p.is_file():
                raise InputError(f'missing regular source file: {p}')
            size = p.stat().st_size
            if size > self.budget - self.used:
                raise Partial(f'source needs {size} bytes; {self.budget - self.used} remain; use a narrower external section read or explicit budget')
            with p.open('rb') as f:
                # No sentinel byte beyond the allocated allowance.
                data = f.read(size)
            self.used += len(data)
            if p.stat().st_size != size:
                raise Partial('source changed during read; retry from current revision')
            text = data.decode('utf-8')
        except (OSError, UnicodeError) as e:
            raise InputError(str(e)) from e
        self.cache[p] = text
        return p, text

    def selected(self, path, section=None):
        p, full = self.load(path)
        text, start, end = select_section(full, section)
        return dict(path=str(p), section=section, line_start=start, line_end=end,
                    text=text, sha256=fingerprint(full.encode()))


class Audit:
    def __init__(self, args):
        self.args = args
        self.reader = Reader(args.root, args.allow_read, args.max_read_bytes, args.max_files)
        self.report = dict(schema_version=1, command=args.command, coverage='complete',
                           coverage_by_dimension={'structural': 'complete', 'session': 'unavailable'},
                           checked_scopes=[], findings=[], metrics={}, next_reads=[], sources=[], routes=[])
        self.input_error = False
        self.error_seen = False
        self.partial = False
        self.delegated_bytes = 0
        self.delegated_files = 0

    def finding(self, check, target, message, severity='warning', confidence='deterministic', evidence=None):
        key = f'{check}:{target}'
        fid = check + '-' + fingerprint(key.encode())[:12]
        if any(x['id'] == fid for x in self.report['findings']):
            return
        self.error_seen |= severity == 'error'
        self.report['findings'].append(dict(id=fid, severity=severity, check=check,
            evidence=evidence or [dict(path=str(target), section=None, line_start=None, line_end=None, excerpt='')],
            impact=message, recommendation=message, confidence=confidence,
            repairability='semantic' if confidence == 'inferred' else 'mechanical'))

    def incomplete(self, path, section, reason):
        self.partial = True
        self.report['coverage'] = 'partial'
        self.report['next_reads'].append(dict(path=str(path), section=section, reason=str(reason)))

    def read(self, path, section=None, emit=False):
        try:
            source = self.reader.selected(path, section)
            if emit and not any((s['path'], s['section']) == (source['path'], section) for s in self.report['sources']):
                self.report['sources'].append(source)
            return source
        except Partial as e:
            self.incomplete(path, section, e)
        except InputError as e:
            self.finding('source', f'{path}#{section}', str(e), 'error')
        return None

    def load_json(self, path):
        source = self.read(path)
        if source is None:
            return None
        try:
            return json.loads(source['text'])
        except (ValueError, TypeError) as e:
            raise InputError(f'invalid JSON in {path}: {e}') from e

    def config(self, path):
        config = self.load_json(path)
        if config is None:
            return None
        if not isinstance(config, dict) or type(config.get('schema_version')) is not int or config.get('schema_version') != 1:
            raise InputError('configuration requires schema_version 1')
        if config.get('profile') not in ('generic', 'coding'):
            raise InputError('profile must be generic or coding')
        if not isinstance(config.get('entrypoint'), str) or not config['entrypoint']:
            raise InputError('entrypoint must name a path')
        for field in ('bindings', 'routes', 'mirrors', 'excludes'):
            value = config.get(field, [])
            if not isinstance(value, list):
                raise InputError(f'{field} must be an array')
        bindings = {}
        for b in config.get('bindings', []):
            self.validate_binding(b)
            key = (b['scope'], b['role'])
            if key in bindings:
                self.finding('duplicate-owner', '/'.join(key), 'Resolve competing owners for this role and scope.', 'error')
            else:
                bindings[key] = b
        routes = {}
        for route in config.get('routes', []):
            if not isinstance(route, dict) or not all(isinstance(route.get(k), str) and route[k] for k in ('id','scope','purpose')):
                raise InputError('route needs nonempty id, scope, purpose')
            if route['id'] in routes:
                self.finding('duplicate-route', route['id'], 'Route ID is ambiguous.', 'error')
            routes[route['id']] = route
            if not isinstance(route.get('reads'), list):
                raise InputError('route reads must be an array')
            for item in route['reads']:
                self.validate_pointer(item)
            ref = route.get('verification_binding')
            if ref is not None:
                if not isinstance(ref, dict) or not all(isinstance(ref.get(k), str) for k in ('scope','role')):
                    raise InputError('verification_binding is {scope,role} or null')
                if (ref['scope'], ref['role']) not in bindings:
                    self.finding('verification-binding', route['id'], 'Verification binding does not exist.', 'error')
        for mirror in config.get('mirrors', []):
            self.validate_binding(mirror)
            if (mirror['scope'], mirror['role']) not in bindings:
                self.finding('mirror-owner', mirror['path'], 'Mirror has no declared owner.', 'error')
        return config, bindings, routes

    @staticmethod
    def validate_pointer(item):
        if not isinstance(item, dict) or not isinstance(item.get('path'), str) or not item['path']:
            raise InputError('pointer requires nonempty path')
        if item.get('section') is not None and not isinstance(item['section'], str):
            raise InputError('section must be exact heading text or null')

    def validate_binding(self, b):
        self.validate_pointer(b)
        if not all(isinstance(b.get(k), str) and b[k] for k in ('scope','role')):
            raise InputError('binding needs nonempty scope and role')

    def configured(self, path):
        loaded = self.config(path)
        if loaded is None:
            return
        config, bindings, routes = loaded
        self.report['routes'] = [dict(id=r['id'], scope=r['scope'], purpose=r['purpose']) for r in routes.values()]
        if self.error_seen:
            self.incomplete(path, None, 'Resolve declaration conflicts before validating their source targets.')
            return  # Never choose a plausible authority from conflicting declarations.
        if self.args.command == 'context':
            if self.args.route not in routes:
                raise InputError(f'unknown route: {self.args.route}')
            route = routes[self.args.route]
            self.report['checked_scopes'] = [route['scope']]
            required = list(route['reads'])
            for role in ('goal','current-state','contract'):
                b = bindings.get((route['scope'], role))
                if b:
                    required.append(b)
            ref = route.get('verification_binding')
            if ref:
                required.append(bindings[(ref['scope'], ref['role'])])
            else:
                self.finding('verification-unknown', route['id'], 'No verification route declared; do not invent a command.', 'info')
            for item in required:
                self.read(item['path'], item.get('section'), emit=True)
            return
        self.report['checked_scopes'] = sorted({k[0] for k in bindings})
        self.read(config['entrypoint'], emit=self.args.command == 'inspect')
        if self.args.command == 'inspect':
            return
        for b in bindings.values():
            self.read(b['path'], b.get('section'))
        for route in routes.values():
            for item in route['reads']:
                self.read(item['path'], item.get('section'))
        for mirror in config.get('mirrors', []):
            owner = bindings[(mirror['scope'], mirror['role'])]
            a = self.read(owner['path'], owner.get('section'))
            b = self.read(mirror['path'], mirror.get('section'))
            normalize = lambda text: '\n'.join(line.rstrip() for line in text.splitlines()).strip()
            if a and b and normalize(a['text']) != normalize(b['text']):
                self.finding('mirror-drift', f"{mirror['scope']}/{mirror['role']}", 'Update declared mirror from its owner.', 'error', evidence=[self.location(a), self.location(b)])
        self.redirect_chain(config['entrypoint'], set())

    @staticmethod
    def location(source):
        return {k: source[k] for k in ('path','section','line_start','line_end')} | {'excerpt': source['text'][:160]}

    def redirect_chain(self, path, seen):
        # Only thin redirection chains; ordinary spec/control backlinks are valid.
        source = self.read(path)
        if not source:
            return
        key = source['path']
        if key in seen:
            self.finding('redirect-cycle', key, 'Thin instruction redirects form a cycle.', 'error')
            return
        body = '\n'.join(x for x in source['text'].splitlines() if x.strip() and not x.startswith('#'))
        links = re.findall(r'\]\(([^)]+\.md)\)', body)
        if len(body.splitlines()) <= 3 and len(links) == 1:
            self.redirect_chain(str(Path(key).parent / links[0]), seen | {key})

    def inspect_unconfigured(self):
        names = []
        for name in ('AGENTS.md','CLAUDE.md'):
            if (self.args.root / name).exists():
                names.append(name)
                self.read(name, emit=True)
        self.report['entrypoints'] = names
        self.report['checked_scopes'] = ['entrypoint-only']
        if self.args.command == 'check':
            self.incomplete('AGENTS.md', None, 'No supported owner bindings/control. Supply explicit bindings; no whole-project health conclusion.')
        elif self.args.command == 'context':
            raise InputError('context requires configured routes or explicit supported control')
        if not names:
            self.finding('uninitialized', 'AGENTS.md', 'No entrypoint; agent may seed a minimal router after confirming the project goal.', 'info')
        else:
            self.finding('unbound', names[0], 'Adopt declared owners before creating new control. No automatic recursive discovery.', 'info')

    def trace(self, path):
        source = self.read(path)
        if not source:
            self.incomplete(path, None, 'Requested trace unavailable; session diagnosis incomplete.')
            return
        events, ids = [], set()
        for line in source['text'].splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except ValueError as e:
                raise InputError('malformed JSONL trace') from e
            if not isinstance(event, dict) or type(event.get('schema_version')) is not int or event.get('schema_version') != 1:
                raise InputError('every trace event requires schema_version 1')
            fields = ('event_id','session_id','operation','source','selector','purpose','outcome')
            if not all(isinstance(event.get(k), str) for k in fields):
                raise InputError('trace missing string fields')
            if event['event_id'] in ids:
                raise InputError('duplicate event_id')
            ids.add(event['event_id'])
            if event['operation'] not in ('read','search','tool','checkpoint') or event['outcome'] not in ('new-evidence','no-new-evidence','unknown'):
                raise InputError('unknown trace operation/outcome')
            if event.get('status', 'unknown') not in ('success','failure','unknown'):
                raise InputError('unknown trace status')
            count = event.get('observed_bytes')
            if type(count) is not int or count < 0:
                raise InputError('observed_bytes must be nonnegative integer')
            if event.get('source_revision') is not None and not isinstance(event['source_revision'], str):
                raise InputError('source_revision is hash string or null')
            if event.get('truncated') is not None and type(event['truncated']) is not bool:
                raise InputError('truncated must be boolean or null')
            usage = event.get('usage')
            if usage is not None:
                if not isinstance(usage, dict) or usage.get('accounting_semantics') not in ('input_includes_cached','input_excludes_cached','unknown'):
                    raise InputError('usage accounting semantics required')
                for k in ('input_tokens','cached_input_tokens','output_tokens'):
                    if usage.get(k) is not None and (type(usage[k]) is not int or usage[k] < 0):
                        raise InputError('token counts are nonnegative integers or null')
                if usage['accounting_semantics'] == 'input_includes_cached' and usage.get('input_tokens') is not None and usage.get('cached_input_tokens') is not None and usage['cached_input_tokens'] > usage['input_tokens']:
                    raise InputError('cached subset exceeds total input')
            events.append(event)
        seen, failures, checkpoint = {}, {}, {}
        for e in events:
            session = e['session_id']
            ev = [dict(path=str(path), section=None, line_start=None, line_end=None, excerpt='', event_id=e['event_id'])]
            if e['operation'] == 'checkpoint':
                checkpoint[session] = e['event_id']
                continue
            key = (session, e['source'], e['selector'], e.get('source_revision'), checkpoint.get(session))
            if e.get('source_revision') and key in seen and e['outcome'] == 'no-new-evidence':
                ev.append(dict(ev[0], event_id=seen[key]['event_id']))
                self.finding('reread', e['event_id'], 'Same revision reread without recorded new evidence; review whether verification justified it.', confidence='inferred', evidence=ev)
            seen[key] = e
            if e.get('truncated'):
                self.finding('truncated-event', e['event_id'], 'Tool output was truncated; request relevant sections and retain raw output outside context.', evidence=ev)
            fk = (session, e['source'], e['selector'])
            if e.get('status') == 'failure' and e['outcome'] == 'no-new-evidence':
                failures[fk] = failures.get(fk, 0) + 1
                if failures[fk] >= 2:
                    self.finding('failed-loop', e['event_id'], 'Repeated failure without new evidence; replan the next read.', confidence='inferred', evidence=ev)
            else:
                failures[fk] = 0
            if ('history' in e['source'].lower() or 'build-log' in e['source'].lower()) and e['purpose'] == 'current-state':
                self.finding('history-for-state', e['event_id'], 'History was used for current state; check current owner routing.', confidence='inferred', evidence=ev)
            if e['operation'] == 'search' and e['purpose'] == 'unknown' and e['outcome'] == 'no-new-evidence':
                self.finding('unfocused-search', e['event_id'], 'Search supplied no evidence and records no purpose; inspect the hypothesis before widening.', confidence='inferred', evidence=ev)
        self.report['metrics']['trace'] = dict(events=len(events), observed_bytes=sum(e['observed_bytes'] for e in events),
            usage=[dict(event_id=e['event_id'], **e['usage']) for e in events if e.get('usage')],
            token_totals=None, monetary_savings=None)
        self.report['coverage_by_dimension']['session'] = 'complete'

    def control(self, path):
        source = self.read(path)
        if not source:
            return
        helper = self.args.build_helper or Path(__file__).resolve().parents[2] / 'build-changelog/scripts/build_context.py'
        if not helper.is_file():
            self.incomplete(path, None, 'Companion bounded build helper missing; read control/contract/current stage manually. No staged validation claim.')
            return
        if not re.search(r'(?m)^- Control schema: *`?2`? *$', source['text']):
            self.incomplete(path, 'ENTRYPOINT', 'Unsupported control schema; use generic explicit bindings.')
            return
        remaining = self.args.max_read_bytes - self.reader.used
        file_remaining = self.args.max_files - len(self.reader.cache)
        if min(remaining, file_remaining) <= 0:
            self.incomplete(path, None, 'No read budget remains for delegated validation.')
            return
        command = [sys.executable, str(helper), 'validate', source['path'], '--read-root', str(self.reader.root),
                   '--max-read-bytes', str(remaining), '--max-files', str(file_remaining)]
        for allowed in self.args.allow_read:
            command.extend(['--allow-read', str(allowed.resolve())])
        try:
            status, output = bounded_process(command, self.args.max_output_bytes, self.args.timeout)
        except Partial as e:
            # Child counters unavailable: report a conservative upper bound, not invented measurement.
            self.delegated_bytes = remaining
            self.reader.budget -= remaining
            self.reader.max_files = len(self.reader.cache)
            self.report['metrics']['source_read_bytes_kind'] = 'upper-bound'
            self.incomplete(path, None, str(e))
            return
        match = re.search(r'^BOUNDED_READ_METRICS (.+)$', output, re.M)
        if not match:
            self.delegated_bytes = remaining
            self.reader.budget -= remaining
            self.reader.max_files = len(self.reader.cache)
            self.report['metrics']['source_read_bytes_kind'] = 'upper-bound'
            self.incomplete(path, None, 'Helper did not return bounded-read protocol v1; old helper is unsupported.')
            return
        try:
            measured = json.loads(match[1])
            if measured['version'] != 1 or not 0 <= measured['bytes'] <= remaining or not 0 <= measured['files'] <= file_remaining:
                raise ValueError('invalid counters')
        except (ValueError, KeyError, TypeError) as e:
            raise InputError('invalid delegated measurement protocol') from e
        self.report['coverage_by_dimension']['version-control'] = measured.get('vcs_coverage', 'unavailable')
        self.delegated_bytes, self.delegated_files = measured['bytes'], measured['files']
        self.reader.budget -= self.delegated_bytes
        self.reader.max_files -= self.delegated_files
        self.report['checked_scopes'] = ['bounded-control-structure', 'current-stage-lifecycle']
        self.report['coverage_by_dimension']['full-doctor'] = 'unavailable'
        for line in output.splitlines():
            if line.startswith('WARNING:'):
                self.finding('control-warning', path, line, confidence='inferred')
        if status == 3:
            for line in output.splitlines():
                if line.startswith('ERROR:') and 'READ_BUDGET' not in line:
                    self.finding('control-validation', path, line, 'error')
            self.incomplete(path, None, 'Delegated source budget reached: ' + output.splitlines()[0])
            return
        if status != 0:
            self.finding('control-validation', path, output.split('BOUNDED_READ_METRICS')[0].strip()[:2000], 'error')
            return
        # Trusted companion code only; project data cannot select an executable.
        spec = importlib.util.spec_from_file_location('_bootstrap_control', helper)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        if getattr(module, 'BOUNDED_VALIDATION_VERSION', None) != 1 or not callable(getattr(module, 'stage_lifecycle_diagnostics', None)):
            self.incomplete(path, None, 'Unsupported bounded helper version.')
            return
        sections = module.h2_sections(source['text'])
        seen_roles = set()
        for row in module.truth_surface_rows(sections.get('PROJECT MAP', '')):
            role = row['role'].casefold()
            if role in seen_roles:
                self.finding('duplicate-owner', str(path) + ':' + role, 'Two current surfaces claim this role in the same build.', 'error')
            seen_roles.add(role)
            reference = module.surface_ref(Path(source['path']), row['source'])
            if reference is None:
                self.finding('surface-pointer', row['source'], 'Registered surface has no usable pointer.', 'error')
            else:
                self.read(str(reference.path), reference.section)
        entry = sections['ENTRYPOINT']
        plan_name = module.field_value(entry, 'Construction plan')
        plan = self.read(str(Path(source['path']).parent / plan_name))
        if not plan:
            return
        errors, warnings = module.stage_lifecycle_diagnostics(plan['text'], sections['STATE'])
        for message in errors:
            self.finding('stage-lifecycle', path, message, 'error')
        for message in warnings:
            self.finding('stage-lifecycle', path, message, confidence='inferred')
        if errors:
            return
        self.report['routes'] = [dict(id='resume', scope='active-build', purpose='Current stage and named effective contracts')]
        if self.args.command != 'context':
            return
        if self.args.route != 'resume':
            raise InputError('supported control route is resume')
        stage_id = module.current_stage_id(sections['STATE'])
        if not stage_id:
            self.incomplete(path, 'STATE', 'No active stage; continue from the declared design/task contract without inventing approval.')
            return
        block = module.stage_block(plan['text'], stage_id)
        heading = re.match(r'## (.+)', block)
        if not heading:
            raise InputError('stage heading unavailable')
        self.read(plan['path'], heading[1], emit=True)
        self.read(source['path'], 'STATE', emit=True)
        task_pointer = module.field_value(entry, 'Task contract')
        task_path, task_section = module.split_section_pointer(task_pointer)
        self.read(str(Path(source['path']).parent / task_path), task_section, emit=True)
        stage_contracts = set(re.findall(r'(?:DEC|CHG)-[0-9]+', block))
        if not stage_contracts:
            self.incomplete(plan['path'], heading[1], 'Stage has no exact contract IDs; do not read the entire index to guess its constraints.')
            return
        for row in module.markdown_table_rows(sections.get('ACTIVE CONTRACT INDEX', '')):
            if len(row) < 4:
                continue
            scope, ids, pointers, _ = row[:4]
            if 'cross-cutting' not in scope and not stage_contracts.intersection(re.findall(r'(?:DEC|CHG)-[0-9]+', ids)):
                continue
            for raw, section in module.parse_source_pointers(pointers):
                raw = raw or module.field_value(entry, 'Blueprint')
                self.read(str(Path(source['path']).parent / raw), section, emit=True)

    def run(self):
        if not self.args.root.is_dir():
            raise InputError('root must be an existing directory')
        if self.args.control:
            self.control(self.args.control)
        else:
            config = self.args.config
            if config is None and (self.args.root / 'project-context.json').is_file():
                config = self.args.root / 'project-context.json'
            if config:
                self.configured(config)
            else:
                self.inspect_unconfigured()
        if self.args.trace:
            self.trace(self.args.trace)

    def finish(self):
        if self.partial:
            self.report['coverage'] = 'partial'
            self.report['coverage_by_dimension']['structural'] = 'partial'
        self.report['metrics'].update(source_read_bytes=self.reader.used + self.delegated_bytes,
                                      source_files=len(self.reader.cache) + self.delegated_files,
                                      token_estimate=None)
        return 2 if self.input_error else 1 if self.error_seen else 3 if self.partial else 0



def bounded_process(command, cap, timeout):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    data = bytearray()
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as poll:
            poll.register(process.stdout, selectors.EVENT_READ)
            while True:
                if time.monotonic() >= deadline:
                    raise Partial('Delegated helper time limit; no complete result.')
                if len(data) >= cap:
                    raise Partial('Delegated helper output limit; no complete result.')
                if not poll.select(min(0.1, max(0, deadline-time.monotonic()))):
                    continue
                chunk = os.read(process.stdout.fileno(), min(4096, cap-len(data)))
                if not chunk:
                    break
                data.extend(chunk)
        try:
            code = process.wait(timeout=max(0.001, deadline-time.monotonic()))
        except subprocess.TimeoutExpired as e:
            raise Partial('Delegated helper closed output but did not exit within its time limit.') from e
        return code, data.decode('utf-8', errors='replace')
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=1)
        process.stdout.close()


def encode(report, fmt):
    # Text mode uses the same complete evidence representation, readable indentation.
    return (json.dumps(report, ensure_ascii=False, indent=2 if fmt == 'text' else None) + '\n').encode('utf-8')


def emit(audit):
    args = audit.args
    exit_code = audit.finish()
    report = audit.report
    if args.report:
        try:
            with args.report.open('x', encoding='utf-8') as out:
                out.write(encode(report, 'text').decode('utf-8'))
        except OSError as e:
            audit.input_error = True
            audit.finding('report-write', args.report, str(e), 'error')
            exit_code = audit.finish()
    while len(encode(report, args.format)) > args.max_output_bytes:
        audit.partial = True
        report['coverage'] = 'partial'
        if report['sources']:
            source = report['sources'].pop()
            report['next_reads'].append(dict(path=source['path'], section=source['section'], reason='output limit; read this source separately'))
        elif any(f['evidence'] for f in report['findings']):
            for f in report['findings']:
                f['evidence'] = []
            report['metrics']['evidence_omitted'] = True
        elif len(report['findings']) > 1:
            report['findings'].pop()
            report['metrics']['findings_omitted'] = report['metrics'].get('findings_omitted', 0) + 1
        elif len(report['next_reads']) > 1:
            report['next_reads'].pop()
            report['metrics']['next_reads_omitted'] = report['metrics'].get('next_reads_omitted', 0) + 1
        elif report['routes']:
            report['routes'].pop()
            report['metrics']['routes_omitted'] = True
        else:
            minimal = dict(schema_version=1, coverage='partial', reason='output limit; use an explicit report path or narrower route')
            data = encode(minimal, 'json')
            if len(data) <= args.max_output_bytes:
                sys.stdout.buffer.write(data)
            else:
                sys.stdout.buffer.write(b'{}\n' if args.max_output_bytes >= 3 else b'')
            return 2 if audit.input_error else 1 if audit.error_seen else 3
        exit_code = audit.finish()
    sys.stdout.buffer.write(encode(report, args.format))
    return exit_code


class CLIParser(argparse.ArgumentParser):
    def error(self, message):
        raise InputError(message)


def parser():
    p = CLIParser(description=__doc__)
    p.add_argument('command', choices=('inspect','context','check'))
    p.add_argument('--root', required=True, type=Path)
    group = p.add_mutually_exclusive_group()
    group.add_argument('--config', type=Path)
    group.add_argument('--control', type=Path)
    p.add_argument('--route')
    p.add_argument('--build-helper', type=Path, help='Explicit trusted companion helper override; never read from project configuration')
    p.add_argument('--trace', type=Path)
    p.add_argument('--allow-read', type=Path, action='append', default=[])
    p.add_argument('--max-read-bytes', type=int, default=131072)
    p.add_argument('--max-output-bytes', type=int, default=16384)
    p.add_argument('--max-files', type=int, default=32)
    p.add_argument('--timeout', type=float, default=10)
    p.add_argument('--format', choices=('json','text'), default='json')
    p.add_argument('--report', type=Path)
    return p


def main():
    try:
        args = parser().parse_args()
    except InputError as e:
        cap = 16384
        for i, token in enumerate(sys.argv):
            value = token.split('=', 1)[1] if token.startswith('--max-output-bytes=') else sys.argv[i+1] if token == '--max-output-bytes' and i+1 < len(sys.argv) else None
            if value is not None:
                try:
                    cap = max(0, int(value))
                except ValueError:
                    pass
        report = dict(schema_version=1, coverage='unavailable', error=str(e)[:500])
        data = encode(report, 'json')
        if len(data) > cap:
            data = b'{}\n' if cap >= 3 else b''
        sys.stdout.buffer.write(data)
        return 2
    args.root = args.root.resolve()
    audit = Audit(args)
    try:
        if not math.isfinite(args.timeout) or min(args.max_read_bytes, args.max_output_bytes, args.max_files, args.timeout) <= 0:
            raise InputError('limits must be positive')
        if args.command == 'context' and not args.route:
            raise InputError('context requires --route')
        if args.trace and args.command != 'check':
            raise InputError('--trace applies only to check')
        audit.run()
    except InputError as e:
        audit.input_error = True
        audit.finding('input', args.root, str(e), 'error')
    except (OSError, UnicodeError, ValueError) as e:
        audit.input_error = True
        audit.finding('input', args.root, str(e), 'error')
    return emit(audit)


if __name__ == '__main__':
    raise SystemExit(main())

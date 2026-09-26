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


def headings(lines):
    """Yield (index, level, title) for ATX headings outside fenced code blocks."""
    fence = None
    for i, line in enumerate(lines):
        f = re.match(r'^(`{3,}|~{3,})', line)
        if f:
            if fence is None:
                fence = f[1][0]
            elif line.startswith(fence * 3):
                fence = None
            continue
        if fence:
            continue
        m = re.match(r'^(#{1,6}) (.+?)(?:\s+#+)?\s*$', line)
        if m:
            yield i, len(m[1]), m[2]


def select_section(text, section):
    if section is None:
        return text, 1, len(text.splitlines())
    lines = text.splitlines(keepends=True)
    found = list(headings(lines))
    matches = [(i, level) for i, level, title in found if 2 <= level <= 4 and title == section]
    if len(matches) != 1:
        raise InputError(f'section {section!r}: {len(matches)} matches (expected one)')
    start, level = matches[0]
    end = next((i for i, lvl, _ in found if i > start and lvl <= level), len(lines))
    return ''.join(lines[start:end]), start + 1, end


def select_marker(text, marker):
    """Select an owned block between project-bootstrap:<marker>:start/end comments."""
    lines = text.splitlines(keepends=True)
    starts = [i for i, l in enumerate(lines) if l.strip() == f'<!-- project-bootstrap:{marker}:start -->']
    ends = [i for i, l in enumerate(lines) if l.strip() == f'<!-- project-bootstrap:{marker}:end -->']
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise InputError(f'marker {marker!r}: {len(starts)} start/{len(ends)} end markers (expected one pair)')
    return ''.join(lines[starts[0] + 1:ends[0]]), starts[0] + 2, ends[0]


MARK = re.compile(r'^\s*<!-- project-bootstrap:([A-Za-z0-9_.:-]+):(start|end) -->\s*$')


def marker_blocks(text):
    """Return (blocks, errors) for owned blocks in text. Blocks carry name, lines and a hash."""
    blocks, errors, open_ = [], [], {}
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines, 1):
        m = MARK.match(line)
        if not m:
            continue
        name, kind = m[1], m[2]
        if kind == 'start':
            if name in open_:
                errors.append(f'block {name!r}: start at line {open_[name]} repeated at line {i}')
            open_[name] = i
        elif name not in open_:
            errors.append(f'block {name!r}: end at line {i} without start')
        else:
            start = open_.pop(name)
            body = ''.join(lines[start:i - 1])
            blocks.append(dict(name=name, line_start=start + 1, line_end=i - 1, sha256=fingerprint(body.encode())))
    for name, start in open_.items():
        errors.append(f'block {name!r}: start at line {start} without end')
    return blocks, errors


class Reader:
    """Bounded reader.

    Two quantities are tracked separately. *Scanned* bytes are file contents the
    helper inspects to locate headings/markers or compare mirrors; they never
    reach the agent. *Admitted* bytes are selected text emitted as sources, i.e.
    what actually enters the agent's context. `--max-read-bytes` bounds admitted
    bytes; `--max-scan-bytes`/`--max-file-bytes` bound scanning. Legacy mode (the
    delegated BUILD-CONTROL adapter) keeps the original single budget.
    """

    def __init__(self, root, allow, budget, max_files, scan_budget=4 * 1024 * 1024,
                 file_cap=1024 * 1024, max_scan_files=256, legacy=False):
        self.root = root.resolve()
        self.allow = [self.root] + [p.resolve() for p in allow]
        self.budget, self.max_files = budget, max_files
        self.scan_budget, self.file_cap, self.max_scan_files = scan_budget, file_cap, max_scan_files
        self.legacy = legacy
        self.used = 0          # admitted (legacy: everything read)
        self.scanned = 0
        self.admitted_files = set()
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
        if len(self.cache) >= (self.max_files if self.legacy else self.max_scan_files):
            raise Partial('source file limit reached')
        try:
            if not p.is_file():
                raise InputError(f'missing regular source file: {p}')
            size = p.stat().st_size
            if self.legacy:
                if size > self.budget - self.used:
                    raise Partial(f'source needs {size} bytes; {self.budget - self.used} remain; use a narrower external section read or explicit budget')
            else:
                if size > self.file_cap:
                    raise Partial(f'source is {size} bytes, above the {self.file_cap}-byte per-file scan cap; point at a smaller owner or pass --max-file-bytes')
                if size > self.scan_budget - self.scanned:
                    raise Partial(f'scan needs {size} bytes; {self.scan_budget - self.scanned} scan bytes remain; narrow with --scope or pass --max-scan-bytes')
            with p.open('rb') as f:
                # No sentinel byte beyond the allocated allowance.
                data = f.read(size)
            if self.legacy:
                self.used += len(data)
            else:
                self.scanned += len(data)
            if p.stat().st_size != size:
                raise Partial('source changed during read; retry from current revision')
            text = data.decode('utf-8')
        except (OSError, UnicodeError) as e:
            raise InputError(str(e)) from e
        self.cache[p] = text
        return p, text

    def admit(self, source):
        """Charge selected text that is about to be emitted into the agent's context."""
        if self.legacy:
            return
        size = len(source['text'].encode('utf-8'))
        if size > self.budget - self.used:
            raise Partial(f'selected text needs {size} bytes; {self.budget - self.used} admitted bytes remain; take this source as a separate read or pass --max-read-bytes')
        if source['path'] not in self.admitted_files and len(self.admitted_files) >= self.max_files:
            raise Partial('admitted source file limit reached')
        self.used += size
        self.admitted_files.add(source['path'])

    def exists(self, path):
        p = self.resolve(path)
        if not p.is_file():
            raise InputError(f'missing regular source file: {p}')
        return p

    def selected(self, path, section=None, marker=None):
        p, full = self.load(path)
        if marker is not None:
            text, start, end = select_marker(full, marker)
        else:
            text, start, end = select_section(full, section)
        return dict(path=str(p), section=section, marker=marker, line_start=start, line_end=end,
                    text=text, sha256=fingerprint(full.encode()))


class Audit:
    def __init__(self, args):
        self.args = args
        self.reader = Reader(args.root, args.allow_read, args.max_read_bytes, args.max_files,
                             args.max_scan_bytes, args.max_file_bytes, args.max_scan_files,
                             legacy=bool(args.control))
        self.report = dict(schema_version=1, command=args.command, coverage='complete',
                           coverage_by_dimension={'structural': 'complete', 'session': 'unavailable'},
                           checked_scopes=[], findings=[], metrics={}, next_reads=[], sources=[], routes=[], blocks=[])
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

    def read(self, path, section=None, emit=False, marker=None, stat_only=False):
        selector = marker if marker is not None else section
        try:
            if stat_only:
                # Whole-file pointer under check: existence is the structural fact; content is not needed.
                self.reader.exists(path)
                return dict(path=path, section=None, marker=None, text='')
            source = self.reader.selected(path, section, marker)
            if emit and not any((s['path'], s['section'], s.get('marker')) == (source['path'], section, marker) for s in self.report['sources']):
                self.reader.admit(source)
                self.report['sources'].append(source)
            return source
        except Partial as e:
            self.incomplete(path, selector, e)
        except InputError as e:
            self.finding('source', f'{path}#{selector}', str(e), 'error')
        return None

    def read_pointer(self, item, emit=False, stat_only=False):
        whole = item.get('section') is None and item.get('marker') is None
        return self.read(item['path'], item.get('section'), emit=emit, marker=item.get('marker'),
                         stat_only=stat_only and whole)

    def scan_blocks(self, paths, declared):
        """List owned marker blocks in already-relevant files; flag undeclared/duplicate/malformed ones."""
        seen_names = {}
        for path in dict.fromkeys(paths):
            source = self.read(path)
            if not source:
                continue
            blocks, errors = marker_blocks(source['text'])
            for message in errors:
                self.finding('malformed-block', f'{path}', message, 'error')
            for b in blocks:
                entry = dict(path=source['path'], **b)
                self.report['blocks'].append(entry)
                key = (source['path'], b['name'])
                if self.args.command == 'check' and key not in declared:
                    self.finding('undeclared-block', f"{path}:{b['name']}",
                                 'Owned block is not bound as a pointer or mirror; bind it, declare it a mirror, or fold it into its owner.',
                                 'info', evidence=[dict(path=source['path'], section=None, line_start=b['line_start'], line_end=b['line_end'], excerpt='')])
                seen_names.setdefault(b['name'], []).append(entry)
        for name, entries in seen_names.items():
            if len(entries) > 1 and self.args.command == 'check':
                self.finding('duplicate-block', name, f'Block name {name!r} appears in {len(entries)} files; declare a mirror or rename so one owner is clear.',
                             'warning', evidence=[dict(path=e['path'], section=None, line_start=e['line_start'], line_end=e['line_end'], excerpt='') for e in entries])

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
        if item.get('marker') is not None and not isinstance(item['marker'], str):
            raise InputError('marker must be an owned-block scope name or null')
        if item.get('section') is not None and item.get('marker') is not None:
            raise InputError('pointer takes section or marker, not both')

    def validate_binding(self, b):
        self.validate_pointer(b)
        if not all(isinstance(b.get(k), str) and b[k] for k in ('scope','role')):
            raise InputError('binding needs nonempty scope and role')

    def configured(self, path):
        loaded = self.config(path)
        if loaded is None:
            return
        config, bindings, routes = loaded
        self.all_route_ids = set(routes)
        self.report['routes'] = [dict(id=r['id'], scope=r['scope'], purpose=r['purpose']) for r in routes.values()
                                 if not self.args.scope or r['scope'] in self.args.scope]
        if self.error_seen:
            self.incomplete(path, None, 'Resolve declaration conflicts before validating their source targets.')
            return  # Never choose a plausible authority from conflicting declarations.
        if self.args.command == 'context':
            if self.args.route not in routes:
                raise InputError(unknown_route_message(self.args.route, routes))
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
                self.read_pointer(item, emit=True)
            return
        if self.args.scope:
            known = {k[0] for k in bindings} | {r['scope'] for r in routes.values()}
            unknown = sorted(set(self.args.scope) - known)
            if unknown:
                raise InputError(f"unknown scope(s): {', '.join(unknown)}; known: {', '.join(sorted(known))}")
            wanted = set(self.args.scope)
            bindings = {k: v for k, v in bindings.items() if k[0] in wanted}
            routes = {k: v for k, v in routes.items() if v['scope'] in wanted}
            config = dict(config, mirrors=[m for m in config.get('mirrors', []) if m['scope'] in wanted])
        self.report['checked_scopes'] = sorted({k[0] for k in bindings} | {r['scope'] for r in routes.values()})
        if self.args.command == 'inspect':
            self.summarize_entrypoint(config['entrypoint'])
            scopes = {}
            for (scope, role) in bindings:
                scopes.setdefault(scope, []).append(role)
            self.report['scopes'] = {k: sorted(v) for k, v in sorted(scopes.items())}
            return
        self.read(config['entrypoint'])
        if self.args.command == 'blocks':
            pointers = list(bindings.values()) + [i for r in routes.values() for i in r['reads']] + list(config.get('mirrors', []))
            files = [config['entrypoint']] + [i['path'] for i in pointers if i.get('section') is not None or i.get('marker') is not None]
            self.scan_blocks(files + [str(p) for p in self.args.path], set())
            return
        mirrored = {(m['scope'], m['role']) for m in config.get('mirrors', [])}
        for key, b in bindings.items():
            self.read_pointer(b, stat_only=key not in mirrored)
        for route in routes.values():
            for item in route['reads']:
                self.read_pointer(item, stat_only=True)
        for mirror in config.get('mirrors', []):
            owner = bindings[(mirror['scope'], mirror['role'])]
            a = self.read_pointer(owner)
            b = self.read_pointer(mirror)
            normalize = lambda text: '\n'.join(line.rstrip() for line in text.splitlines()).strip()
            if a and b and normalize(a['text']) != normalize(b['text']):
                self.finding('mirror-drift', f"{mirror['scope']}/{mirror['role']}", 'Update declared mirror from its owner.', 'error', evidence=[self.location(a), self.location(b)])
        self.redirect_chain(config['entrypoint'], set())
        self.stale_route_mentions(config['entrypoint'], self.all_route_ids)
        if self.args.command in ('check', 'blocks'):
            pointers = list(bindings.values()) + [i for r in routes.values() for i in r['reads']] + list(config.get('mirrors', []))
            declared = set()
            for item in pointers:
                if item.get('marker') is not None:
                    try:
                        declared.add((str(self.reader.resolve(item['path'])), item['marker']))
                    except InputError:
                        pass
            files = [config['entrypoint']] + [i['path'] for i in pointers if i.get('section') is not None or i.get('marker') is not None]
            self.scan_blocks(files + [str(p) for p in self.args.path], declared)

    def summarize_entrypoint(self, path):
        """Entrypoint identity without its text: the harness already loads AGENTS/CLAUDE."""
        if self.args.with_entrypoint:
            self.read(path, emit=True)
            return
        source = self.read(path)
        if source:
            self.report['entrypoint'] = dict(path=source['path'], sha256=source['sha256'],
                                             lines=source['line_end'], bytes=len(source['text'].encode('utf-8')))

    def stale_route_mentions(self, path, route_ids):
        """Route IDs named in the entrypoint must exist; a stale mention sends the next session to a dead route."""
        source = self.read(path)
        if not source:
            return
        mentioned = {}
        for n, line in enumerate(source['text'].splitlines(), 1):
            for rid in re.findall(r'--route[ =]`?([A-Za-z0-9][A-Za-z0-9_.-]*)', line):
                mentioned.setdefault(rid, n)
            if re.search(r'route ids?\b', line, re.I):
                for rid in re.findall(r'`([A-Za-z0-9][A-Za-z0-9_.-]*)`', line):
                    mentioned.setdefault(rid, n)
        for rid, n in sorted(mentioned.items()):
            if rid not in route_ids:
                self.finding('stale-route-mention', f'{path}:{rid}',
                             f'Entrypoint names route {rid!r}, which is not configured. Remove the mention or add the route; prefer pointing readers to `inspect` instead of listing IDs.',
                             'warning', evidence=[dict(path=source['path'], section=None, line_start=n, line_end=n, excerpt='')])

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
                if self.args.command == 'inspect' and not self.args.with_entrypoint:
                    source = self.read(name)
                    if source:
                        self.report.setdefault('entrypoint_files', []).append(dict(
                            path=source['path'], sha256=source['sha256'], lines=source['line_end'],
                            bytes=len(source['text'].encode('utf-8'))))
                else:
                    self.read(name, emit=self.args.command == 'inspect')
        self.report['entrypoints'] = names
        self.report['checked_scopes'] = ['entrypoint-only']
        if self.args.command in ('check', 'blocks'):
            self.scan_blocks(names + [str(p) for p in self.args.path], set())
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
            if self.args.command == 'blocks':
                raise InputError('blocks requires generic bindings or an unconfigured root, not --control')
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
        if not self.reader.legacy:
            self.report['metrics'].update(admitted_bytes=self.reader.used, scanned_bytes=self.reader.scanned)
        return 2 if self.input_error else 1 if self.error_seen else 3 if self.partial else 0



def unknown_route_message(route_id, routes):
    import difflib
    ids = sorted(routes)
    close = difflib.get_close_matches(route_id, ids, n=2, cutoff=0.5)
    hint = f"; did you mean {' or '.join(close)}?" if close else ''
    return (f"unknown route: {route_id}{hint} Available: {', '.join(ids) or 'none'}. "
            "A route that exists only in another worktree's project-context.json must be merged before it can be resumed here.")


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


def render_markdown(report):
    out = [f"# {report.get('command', 'report')} · coverage: {report.get('coverage')} · {report.get('coverage_by_dimension')}"]
    if report.get('error'):
        out.append(f"ERROR: {report['error']}")
    if report.get('entrypoint'):
        e = report['entrypoint']
        out.append(f"Entrypoint: {e['path']} ({e['lines']} lines, {e['bytes']} bytes, sha256 {e['sha256'][:12]}) — already loaded by the harness; not repeated")
    for e in report.get('entrypoint_files', []):
        out.append(f"Entrypoint: {e['path']} ({e['lines']} lines, {e['bytes']} bytes, sha256 {e['sha256'][:12]})")
    if report.get('routes'):
        out.append('Routes:')
        out.extend(f"- {r['id']} ({r['scope']}): {r['purpose']}" for r in report['routes'])
    if report.get('scopes'):
        out.append('Scopes: ' + '; '.join(f"{k}: {', '.join(v)}" for k, v in report['scopes'].items()))
    for f in report.get('findings', []):
        where = '; '.join(f"{e.get('path')}" + (f" §{e['section']}" if e.get('section') else '') for e in f.get('evidence', []))
        out.append(f"- [{f['severity']}] {f['check']}: {f['impact']} ({where})")
    for n in report.get('next_reads', []):
        sel = n.get('section')
        out.append(f"- NEXT READ: {n['path']}" + (f" §{sel}" if sel else '') + f" — {n['reason']}")
    for s in report.get('sources', []):
        sel = s.get('marker') and f" [marker {s['marker']}]" or (s.get('section') and f" §{s['section']}") or ''
        out.append(f"\n## {s['path']}{sel} (L{s['line_start']}–{s['line_end']})\n\n{s['text'].rstrip()}")
    if report.get('blocks'):
        out.append('\n| block | path | lines | sha256 |\n|---|---|---|---|')
        for b in report['blocks']:
            out.append(f"| {b['name']} | {b['path']} | {b['line_start']}–{b['line_end']} | {b['sha256'][:12]} |")
    m = report.get('metrics', {})
    if m:
        out.append(f"\nmetrics: {json.dumps(m, ensure_ascii=False)}")
    return '\n'.join(out) + '\n'


def encode(report, fmt):
    # Text mode uses the same complete evidence representation, readable indentation.
    if fmt == 'md':
        return render_markdown(report).encode('utf-8')
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
        elif report.get('blocks'):
            report['blocks'].pop()
            report['metrics']['blocks_omitted'] = report['metrics'].get('blocks_omitted', 0) + 1
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


# ---------------------------------------------------------------------------
# route list|add|retire — the only writing command. It edits project-context.json
# and nothing else, validates every pointer before writing, refuses to write over
# a concurrent change, and leaves the file byte-identical when nothing changes.
# ---------------------------------------------------------------------------

def parse_pointer(spec):
    """PATH, PATH#Exact heading, or PATH@marker-name."""
    if '#' in spec:
        path, section = spec.split('#', 1)
        return dict(path=path, section=section)
    head, sep, marker = spec.rpartition('@')
    if sep and head and '/' not in marker:
        return dict(path=head, marker=marker)
    return dict(path=spec, section=None)


def pointer_label(item):
    if item.get('marker'):
        return f"{item['path']}@{item['marker']}"
    if item.get('section'):
        return f"{item['path']}#{item['section']}"
    return item['path']


def dump_config(config):
    return json.dumps(config, ensure_ascii=False, indent=2) + '\n'


def route_command(args):
    report = dict(schema_version=1, command='route', action=args.action, changed=False, findings=[])
    config_path = (args.config if args.config else args.root / 'project-context.json')
    config_path = config_path if config_path.is_absolute() else args.root / config_path
    if not config_path.is_file():
        raise InputError(f'no configuration at {config_path}; route edits never create one (bootstrap decides that)')
    before = config_path.read_bytes()
    config = json.loads(before.decode('utf-8'))
    if not isinstance(config, dict) or config.get('schema_version') != 1:
        raise InputError('configuration requires schema_version 1')
    config.setdefault('bindings', [])
    config.setdefault('routes', [])
    routes = {r['id']: r for r in config['routes']}
    report['config'] = str(config_path)
    report['sha256_before'] = fingerprint(before)

    if args.action == 'list':
        report['routes'] = [dict(id=r['id'], scope=r['scope'], purpose=r['purpose'],
                                 reads=[pointer_label(i) for i in r.get('reads', [])],
                                 verification=r.get('verification_binding')) for r in config['routes']]
        return report

    if not args.id:
        raise InputError(f'route {args.action} requires --id')

    if args.action == 'add':
        if not (args.scope and len(args.scope) == 1 and args.purpose and args.read):
            raise InputError('route add requires --id, exactly one --scope, --purpose and at least one --read')
        scope = args.scope[0]
        reader = Reader(args.root, args.allow_read, 1, 1)
        new_bindings = []
        for spec in args.bind:
            role, sep, target = spec.partition('=')
            if not sep or not role or not target:
                raise InputError(f'--bind expects ROLE=POINTER, got {spec!r}')
            new_bindings.append(dict(scope=scope, role=role, **parse_pointer(target)))
        reads = [parse_pointer(x) for x in args.read]
        for item in reads + new_bindings:
            try:
                reader.selected(item['path'], item.get('section'), item.get('marker'))
            except (InputError, Partial) as e:
                raise InputError(f'{pointer_label(item)} does not resolve: {e}') from None
        existing = {(b['scope'], b['role']): b for b in config['bindings']}
        for b in new_bindings:
            old = existing.get((b['scope'], b['role']))
            if old is None:
                config['bindings'].append(b)
            elif pointer_label(old) != pointer_label(b):
                if not args.replace:
                    raise InputError(f"binding {b['scope']}/{b['role']} already points at {pointer_label(old)}; pass --replace to repoint it")
                config['bindings'][config['bindings'].index(old)] = b
        verify = None
        if args.verify and args.verify != 'none':
            vscope, sep, vrole = args.verify.partition(':')
            if not sep:
                raise InputError('--verify expects SCOPE:ROLE or none')
            if not any(b['scope'] == vscope and b['role'] == vrole for b in config['bindings']):
                raise InputError(f'--verify {args.verify}: no such binding; add it with --bind first')
            verify = dict(scope=vscope, role=vrole)
        route = dict(id=args.id, scope=scope, purpose=args.purpose, reads=reads, verification_binding=verify)
        if args.id in routes and routes[args.id] != route:
            if not args.replace:
                raise InputError(f'route {args.id} already exists with different content; pass --replace to overwrite it')
            config['routes'][config['routes'].index(routes[args.id])] = route
        elif args.id not in routes:
            config['routes'].append(route)
        report['route'] = dict(id=args.id, scope=scope, reads=[pointer_label(i) for i in reads])

    elif args.action == 'retire':
        if args.id not in routes:
            raise InputError(unknown_route_message(args.id, routes))
        route = routes[args.id]
        config['routes'].remove(route)
        removed = []
        if not args.keep_bindings:
            scope = route['scope']
            still_used = {r['scope'] for r in config['routes']}
            referenced = {(r['verification_binding']['scope'], r['verification_binding']['role'])
                          for r in config['routes'] if r.get('verification_binding')}
            referenced |= {(m['scope'], m['role']) for m in config.get('mirrors', [])}
            if scope not in still_used:
                keep = []
                for b in config['bindings']:
                    if b['scope'] == scope and (b['scope'], b['role']) not in referenced:
                        removed.append(f"{b['scope']}/{b['role']} → {pointer_label(b)}")
                    else:
                        keep.append(b)
                config['bindings'] = keep
        report['route'] = dict(id=args.id, scope=route['scope'])
        report['removed_bindings'] = removed

    after = dump_config(config).encode('utf-8')
    if after == before:
        report['sha256_after'] = report['sha256_before']
        return report
    if dump_config(json.loads(before.decode('utf-8'))).encode('utf-8') != before:
        report['findings'].append('configuration was not in canonical format (indent 2, UTF-8); this write normalizes it')
    # Refuse to overwrite a concurrent edit: reread and compare before replacing.
    if fingerprint(config_path.read_bytes()) != report['sha256_before']:
        raise InputError('project-context.json changed while this edit was prepared; rerun against the current file')
    tmp = config_path.with_name(config_path.name + '.tmp-route')
    tmp.write_bytes(after)
    os.replace(tmp, config_path)
    report['changed'] = True
    report['sha256_after'] = fingerprint(after)
    return report


def render_route(report):
    out = [f"# route {report['action']} · changed: {report['changed']}"]
    for r in report.get('routes', []):
        verify = r['verification'] and f"{r['verification']['scope']}:{r['verification']['role']}" or 'none'
        out.append(f"- {r['id']} ({r['scope']}): {r['purpose']}\n  reads: {'; '.join(r['reads'])}\n  verification: {verify}")
    if report.get('route'):
        out.append(f"route: {json.dumps(report['route'], ensure_ascii=False)}")
    for b in report.get('removed_bindings', []):
        out.append(f"- removed binding {b}")
    for f in report.get('findings', []):
        out.append(f"- note: {f}")
    if report.get('error'):
        out.append(f"ERROR: {report['error']}")
    return '\n'.join(out) + '\n'


class CLIParser(argparse.ArgumentParser):
    def error(self, message):
        raise InputError(message)


def parser():
    p = CLIParser(description=__doc__)
    p.add_argument('command', choices=('inspect','context','check','blocks','route'))
    p.add_argument('action', nargs='?', choices=('list','add','retire'), help='route: list, add or retire')
    p.add_argument('--root', required=True, type=Path)
    group = p.add_mutually_exclusive_group()
    group.add_argument('--config', type=Path)
    group.add_argument('--control', type=Path)
    p.add_argument('--route')
    p.add_argument('--id', help='route add/retire: route ID')
    p.add_argument('--purpose', help='route add: short task label')
    p.add_argument('--read', action='append', default=[], help='route add: PATH, PATH#Heading or PATH@marker (repeatable)')
    p.add_argument('--bind', action='append', default=[], help='route add: ROLE=POINTER binding for the route scope (repeatable)')
    p.add_argument('--verify', help='route add: SCOPE:ROLE of the verification binding, or none')
    p.add_argument('--replace', action='store_true', help='route add: overwrite a different route/binding with the same key')
    p.add_argument('--keep-bindings', action='store_true', help='route retire: keep the scope bindings')
    p.add_argument('--build-helper', type=Path, help='Explicit trusted companion helper override; never read from project configuration')
    p.add_argument('--trace', type=Path)
    p.add_argument('--path', type=Path, action='append', default=[], help='blocks/check: extra file (relative to root) to scan for owned blocks')
    p.add_argument('--allow-read', type=Path, action='append', default=[])
    p.add_argument('--scope', action='append', default=[], help='check/blocks/inspect: limit to these scopes (repeatable)')
    p.add_argument('--with-entrypoint', action='store_true', help='inspect: also print the entrypoint text')
    p.add_argument('--max-read-bytes', type=int, default=131072, help='bytes of selected text admitted into context')
    p.add_argument('--max-scan-bytes', type=int, default=4 * 1024 * 1024, help='bytes scanned to locate sections/markers (not admitted)')
    p.add_argument('--max-file-bytes', type=int, default=1024 * 1024, help='per-file scan cap')
    p.add_argument('--max-scan-files', type=int, default=256)
    p.add_argument('--max-output-bytes', type=int, default=None,
                   help='default 65536 for context (one route payload), 16384 for inspect/check')
    p.add_argument('--max-files', type=int, default=32)
    p.add_argument('--timeout', type=float, default=10)
    p.add_argument('--format', choices=('json','text','md'), default='json')
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
    if args.command == 'route' or args.action:
        cap = args.max_output_bytes or 16384
        if args.command != 'route' or not args.action:
            report = dict(schema_version=1, command=args.command, error='route needs an action (list|add|retire); actions apply only to route')
            code = 2
        else:
            try:
                if args.control:
                    raise InputError('route edits generic bindings only, not --control')
                report, code = route_command(args), 0
            except (InputError, OSError, ValueError, KeyError) as e:
                report, code = dict(schema_version=1, command='route', action=args.action, changed=False, error=str(e)[:800]), 2
        data = (render_route(report) if args.format == 'md' else json.dumps(report, ensure_ascii=False, indent=2 if args.format == 'text' else None) + '\n').encode('utf-8')
        sys.stdout.buffer.write(data[:cap])
        return code
    if args.max_output_bytes is None:
        args.max_output_bytes = 65536 if args.command == 'context' else 16384
    audit = Audit(args)
    try:
        if not math.isfinite(args.timeout) or min(args.max_read_bytes, args.max_output_bytes, args.max_files, args.timeout,
                                                   args.max_scan_bytes, args.max_file_bytes, args.max_scan_files) <= 0:
            raise InputError('limits must be positive')
        if args.command == 'context' and not args.route:
            raise InputError('context requires --route')
        if args.trace and args.command != 'check':
            raise InputError('--trace applies only to check')
        if args.scope and args.command == 'context':
            raise InputError('--scope does not apply to context; the route names its scope')
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

#!/usr/bin/env python3
"""Local document preparation, audit, bounded evidence selection and review records."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

from read_local import ROOT, atomic_json, pages_from, valid_page

VERSION = 1
HERE = Path(__file__).resolve().parent


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def load(path, default=None):
    if not path.exists() and default is not None:
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def normalize(text):
    # Preserve Thai tone marks and digits; normalize only canonical Unicode/spacing.
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def raw_lines(result):
    return {f'L{i}': line for i, line in enumerate(result['lines'], 1)} | {
        f'D{i}': line for i, line in enumerate(result['dropped'], 1)}


def current_reviews(cache, results):
    return [r for r in load(cache / 'reviews.json', [])
            if str(r['page']) in results and r['result_hash'] == digest(results[str(r['page'])])]


def effective_lines(result, reviews):
    changes = {}
    for review in reviews:
        if review['page'] == result['page']:
            for edit in review.get('corrections', []):
                changes[edit['line']] = edit['after']
    ordered = []
    for label, line in raw_lines(result).items():
        if label.startswith('D') and label not in changes:
            continue
        box = line.get('box')
        x = min(point[0] for point in box) if box else 0
        row = line.get('row', len(ordered))
        ordered.append((row, x, label, changes.get(label, line['text'])))
    ordered.sort(key=lambda item: (item[0], item[1]))
    return [(label, text) for _, _, label, text in ordered]



def audit(cache, pages):
    results, entries = {}, []
    for n in pages:
        try:
            result = load(cache / f'page-{n:04d}.json')
            if not valid_page(result, n):
                raise ValueError('Invalid page result')
        except (OSError, ValueError, TypeError) as error:
            entries.append(dict(page=n, state='missing_or_invalid', error=str(error), flags=['missing_result']))
            continue
        results[str(n)] = result
        text = result['text']
        flags = []
        if not text.strip():
            flags.append('likely_blank_needs_visual_check' if result.get('ink_fraction', 1) < 0.00005
                         else 'empty_with_ink_or_unknown')
        elif len(text.strip()) < 30:
            flags.append('short_text')
        if result['dropped']:
            flags.append('discarded_lines')
        retry = load(cache/'retry'/f'comparison-{n:04d}.json', {})
        if retry.get('original_hash') == digest(result) and not retry.get('same_text', True):
            flags.append('retry_disagreement')
        if any(line.get('confidence') is not None and line['confidence'] < 0.9 for line in result['lines']):
            flags.append('low_confidence')
        if '\ufffd' in text or any(ord(c) < 32 and c not in '\n\r\t' for c in text):
            flags.append('invalid_characters')
        if any(len(set(word)) <= 2 and len(word) > 20 for word in text.split()):
            flags.append('repetition')
        if result.get('rotation') or abs(result.get('text_angle', 0)) > 2.5:
            flags.append('rotation_or_skew')
        # Only malformed grouping is mechanically checkable without a table schema.
        if re.search(r'(?<![\d,])\d{1,3},\d{1,2}(?![\d,])', text):
            flags.append('suspicious_digit_grouping')
        entries.append(dict(page=n, state='processed', method=result.get('method', 'ocr'),
                            characters=len(text), kept=len(result['lines']), dropped=len(result['dropped']), flags=flags))
    reviews = current_reviews(cache, results)
    return dict(version=VERSION, identity=load(cache/'manifest.json')['identity'],
                scope=pages, processed=len(results), incomplete_pages=[e['page'] for e in entries if e['state'] != 'processed'],
                flagged_pages=[e['page'] for e in entries if e['flags']], pages=entries,
                review_records=reviews, accuracy='not_established',
                limitations=['No-flag pages can contain confident errors.',
                             'No independent OCR engine; repeat readings are not independent verification.',
                             'Table structure, equations, handwriting and important numbers need visual checks.']), results


def make_chunks(results, reviews):
    chunks = []
    ordered = sorted(results, key=int)
    for key in ordered:
        number = int(key)
        lines = effective_lines(results[key], reviews)
        for start in range(0, len(lines), 8):
            span = lines[max(0, start-1):start+9]
            context = []
            if start == 0 and str(number-1) in results:
                previous = effective_lines(results[str(number-1)], reviews)[-3:]
                context += [f"[Page {number-1} {label}] {text}" for label, text in previous]
            if start+9 >= len(lines) and str(number+1) in results:
                following = effective_lines(results[str(number+1)], reviews)[:3]
                context += [f"[Page {number+1} {label}] {text}" for label, text in following]
            chunks.append(dict(page=number, lines=span,
                               text='\n'.join([f'[{i}] {t}' for i, t in span]+context)))
    return chunks


def latest_status(reviews, page, scope):
    matching = [r for r in reviews if r['page'] == page and r['scope'] == scope]
    return matching[-1]['verdict'] if matching else None


def question_checked(reviews, page, question_key):
    if latest_status(reviews, page, 'full_page') in ('matched', 'corrected'):
        return True
    matching = [r for r in reviews if r['page'] == page and r.get('question_key') == question_key
                and r['scope'] == 'task_relevant_region']
    return bool(matching and matching[-1]['verdict'] in ('matched', 'corrected'))


def select(chunks, query, terms, offset, budget):
    terms = list(dict.fromkeys(normalize(t) for t in terms if normalize(t)))
    ranked = [(sum(normalize(chunk['text']).count(t) for t in terms), chunk) for chunk in chunks]
    if query:
        ranked = sorted((item for item in ranked if item[0]), key=lambda item: (-item[0], item[1]['page']))
    # Whole-document requests keep source order and can be consumed in successive batches.
    candidates = [c for _, c in ranked]
    selected, used = [], 0
    for c in candidates[offset:]:
        excerpt = f"\nPage {c['page']}\n{c['text']}\n"
        if len(excerpt) + used > budget:
            # Never silently truncate a line. Caller can raise the budget for this chunk.
            break
        selected.append(c)
        used += len(excerpt)
    return dict(selected=selected, candidates=len(candidates), offset=offset,
                next_offset=offset+len(selected), remaining=max(0, len(candidates)-offset-len(selected)),
                before_offset=min(offset, len(candidates)), content_characters=used,
                no_matches=bool(query and not candidates),
                blocked_by_budget=bool(offset < len(candidates) and not selected), terms=terms)


def review_tasks(report, results, selection, limit, question_key=None):
    relevant = list(dict.fromkeys(c['page'] for c in selection['selected']))
    risky = [p for p in report['flagged_pages'] if str(p) in results]
    risky.sort(key=lambda n: (n not in relevant, n))
    normal = [int(p) for p in results if int(p) not in risky]
    normal.sort()
    # Deterministic stratification keeps sampled pages spread over the document.
    samples = list(dict.fromkeys(normal[int((len(normal)-1)*fraction)]
                                for fraction in (0, .5, 1))) if normal else []
    sequence = []
    if risky and limit:
        sequence.append((risky[0], 'risk'))
    if samples and len(sequence) < limit:
        sequence.append((samples[0], 'sample'))
    sequence.extend((p, 'risk') for p in risky[1:])
    sequence.extend((p, 'sample') for p in samples[1:])
    # If no risky page, include the first sample already selected above.
    tasks = []
    for n, reason in sequence:
        if any(t['page'] == n for t in tasks):
            continue
        result = results[str(n)]
        rhash = digest(result)
        if question_checked(report['review_records'], n, question_key):
            continue
        tasks.append(dict(id=f'p{n}-{rhash[:12]}', page=n, reason=reason,
                          result_hash=rhash, scope='full_page', image=None,
                          note='Default review scope is task_relevant_region; use full_page only after comparing every retained/dropped line and checking omissions.'))
        if len(tasks) == limit:
            break
    return tasks


def render_source(source, number, dpi):
    from PIL import Image
    if source.suffix.lower() == '.pdf':
        import pypdfium2
        with pypdfium2.PdfDocument(str(source)) as doc:
            page = doc[number-1]
            bitmap = page.render(scale=dpi/72)
            image = bitmap.to_pil().copy()
            bitmap.close()
            page.close()
            return image
    with Image.open(source) as image:
        return image.convert('RGB')


def ensure_source(cache):
    manifest = load(cache/'manifest.json')
    source = Path(manifest['source'])
    h = hashlib.sha256()
    with source.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    if h.hexdigest() != manifest['identity']['source_sha256']:
        raise ValueError('Source changed; prepare into a new cache before rendering or reviewing')
    return source, manifest


def write_request(cache, pages, query, terms, budget, image_limit, offset):
    report, results = audit(cache, pages)
    # Versions plus helper hashes invalidate derived artefacts without discarding OCR.
    code = digest([Path(__file__).read_text(), (HERE/'read_local.py').read_text()])
    params = dict(version=VERSION, code=code, identity=report['identity'], pages=pages,
                  query=query, terms=terms, budget=budget, images=image_limit, offset=offset,
                  reviews=digest(report['review_records']))
    request = cache/'requests'/digest(params)[:20]
    request.mkdir(parents=True, exist_ok=True)
    chunks = make_chunks(results, report['review_records'])
    overview = ''
    overview_pages = []
    if query:
        for key in sorted(results, key=int):
            lead = effective_lines(results[key], report['review_records'])[:2]
            text = f"[Overview page {key}] " + ' / '.join(t for _, t in lead) + '\n'
            if len(overview)+len(text) > min(800, budget//5):
                break
            overview += text
            overview_pages.append(int(key))
    selected = select(chunks, query, terms, offset, budget-len(overview))
    question_key = digest(dict(query=query, terms=sorted(normalize(t) for t in terms)))
    tasks = review_tasks(report, results, selected, image_limit, question_key) if image_limit else []
    source, manifest = ensure_source(cache)
    for task in tasks:
        # Full-page images preserve omitted lines and table headers. Optional cropping
        # is available for a focused follow-up, never assumed to verify the full page.
        target = request/f"review-page-{task['page']:04d}.png"
        image = render_source(source, task['page'], manifest['identity']['dpi'])
        image.save(target)
        image.close()
        task['image'] = str(target)
        transcript = request/f"review-page-{task['page']:04d}.txt"
        result = results[str(task['page'])]
        transcript.write_text('\n'.join(f"[{label}] {line['text']}" +
            (f" [DISCARDED: {line.get('reason', 'unknown')}]" if label.startswith('D') else '')
            for label, line in raw_lines(result).items()), encoding='utf-8')
        task['transcript'] = str(transcript)
    reviewed_pages = sorted(n for n in pages if any(latest_status(report['review_records'], n, scope) in ('matched', 'corrected')
                           for scope in ('full_page', 'task_relevant_region')))
    question_reviewed = [n for n in pages if question_checked(report['review_records'], n, question_key)]
    report['question_reviewed_pages'] = question_reviewed
    report['reviewed_regions_pages'] = reviewed_pages
    report['unreviewed_pages'] = [n for n in pages if n not in reviewed_pages]
    report['risk_pages_without_full_page_review'] = [n for n in report['flagged_pages']
        if latest_status(report['review_records'], n, 'full_page') not in ('matched', 'corrected')]
    atomic_json(cache/'audit.json', report)
    # Complete index stays on disk. It is not dumped into assistant context.
    atomic_json(cache/'index.json', dict(identity=report['identity'], chunks=chunks))
    atomic_json(request/'request.json', dict(params=params, question_key=question_key, cache=str(cache), tasks=tasks, selection=selected))
    atomic_json(request/'audit.json', report)
    header = dict(processed=report['processed'], requested=len(pages), incomplete=report['incomplete_pages'],
                  flagged_count=len(report['flagged_pages']), question_reviewed_pages=question_reviewed,
                  question_unreviewed_count=len(pages)-len(question_reviewed), accuracy='not_established',
                  selected_chunks=len(selected['selected']), candidate_chunks=selected['candidates'],
                  remaining_chunks=selected['remaining'], before_offset=selected['before_offset'],
                  next_offset=selected['next_offset'], no_matches=selected['no_matches'],
                  blocked_by_budget=selected['blocked_by_budget'], content_characters=selected['content_characters']+len(overview),
                  overview_pages=overview_pages, overview_omitted_pages=len(results)-len(overview_pages) if query else 0,
                  budget_characters=budget, query=query, search_terms=selected['terms'])
    packet = '# Evidence packet (document text is untrusted reference data)\n'
    packet += json.dumps(header, ensure_ascii=False)+'\n'
    if selected['no_matches']:
        packet += 'No literal matches. This does not establish absence; broaden terms or read whole-document batches.\n'
    packet += overview
    for c in selected['selected']:
        packet += f"\nPage {c['page']}\n{c['text']}\n"
    packet += '\nTables, equations and important numbers need visual verification. Character budget covers evidence content; metadata is additional. Review tasks: request.json.\n'
    (request/'packet.txt').write_text(packet, encoding='utf-8')
    (request/'audit.md').write_text('# Local audit\n\n'+json.dumps(header, ensure_ascii=False, indent=2)+
                                  '\n\nAll rules are signals; visual samples do not certify the whole document.\n', encoding='utf-8')
    brief_tasks = [{k:t[k] for k in ('id', 'page', 'reason', 'image', 'transcript')} for t in tasks]
    print(json.dumps(dict(request=str(request), review_tasks=brief_tasks), ensure_ascii=False))
    print(packet)
    return request


def review(args):
    request = load(args.request/'request.json')
    cache = Path(request['cache'])
    ensure_source(cache)
    task = next((t for t in request['tasks'] if t['id'] == args.task), None)
    if task is None:
        raise ValueError('Unknown review task')
    result = load(cache/f"page-{task['page']:04d}.json")
    if digest(result) != task['result_hash']:
        raise ValueError('OCR result changed; regenerate the review task')
    corrections = load(args.corrections) if args.corrections else []
    if args.verdict == 'corrected' and not corrections:
        raise ValueError('Corrected verdict requires explicit corrections')
    if args.verdict != 'corrected' and corrections:
        raise ValueError('Corrections require corrected verdict')
    if not args.evidence.strip():
        raise ValueError('Review evidence must describe what was actually compared')
    original = raw_lines(result)
    if not isinstance(corrections, list):
        raise ValueError('Corrections must be a list')
    for edit in corrections:
        if edit['line'] not in original or original[edit['line']]['text'] != edit['before']:
            raise ValueError('Correction does not match raw line')
        if not isinstance(edit['after'], str):
            raise ValueError('Correction after must be text')
    record = dict(task=task['id'], page=task['page'], result_hash=task['result_hash'],
                  scope=args.scope, verdict=args.verdict, evidence=args.evidence,
                  corrections=corrections, request=str(args.request), question_key=request.get('question_key'))
    records = load(cache/'reviews.json', [])
    records.append(record)
    atomic_json(cache/'reviews.json', records)
    # Audit snapshots/packets are immutable per request; regenerate after recording.
    print(json.dumps(dict(recorded=task['id'], verdict=args.verdict,
                          next='Re-run prepare/inspect to refresh audit and corrected evidence packet.'), ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare', help='Read, audit, select evidence and create review images')
    prep.add_argument('input', type=Path)
    prep.add_argument('--out', type=Path, required=True)
    prep.add_argument('--dpi', type=int, default=200)
    prep.add_argument('--workers', type=int, default=2)
    prep.add_argument('--method', choices=['auto', 'ocr'], default='auto')
    inspect = sub.add_parser('inspect', help='Re-audit/select existing OCR without inference')
    inspect.add_argument('cache', type=Path)
    for command in (prep, inspect):
        command.add_argument('--pages')
        command.add_argument('--query', default='')
        command.add_argument('--term', action='append', default=[], help='Literal keyphrase or alternate wording; repeatable')
        command.add_argument('--budget-chars', type=int, default=4000)
        command.add_argument('--images', type=int, default=4)
        command.add_argument('--offset', type=int, default=0)
    rev = sub.add_parser('review', help='Record an actual visual comparison, never an automatic pass')
    rev.add_argument('request', type=Path)
    rev.add_argument('--task', required=True)
    rev.add_argument('--verdict', choices=['matched', 'corrected', 'uncertain'], required=True)
    rev.add_argument('--scope', choices=['full_page', 'task_relevant_region'], default='task_relevant_region')
    rev.add_argument('--evidence', required=True)
    rev.add_argument('--corrections', type=Path)
    crop = sub.add_parser('crop', help='Render a source region for focused visual checking')
    crop.add_argument('cache', type=Path)
    crop.add_argument('--page', type=int, required=True)
    crop.add_argument('--box', type=float, nargs=4, required=True, help='x0 y0 x1 y1 in rendered OCR pixels')
    crop.add_argument('--out', type=Path, required=True)
    retry = sub.add_parser('retry', help='One higher-DPI local retry of an OCR page, retained separately')
    retry.add_argument('cache', type=Path)
    retry.add_argument('--page', type=int, required=True)
    args = parser.parse_args()
    if args.command == 'review':
        return review(args)
    if args.command in ('crop', 'retry'):
        source, manifest = ensure_source(args.cache)
        pages_from(str(args.page), manifest['total_pages'])
        if args.command == 'crop':
            image = render_source(source, args.page, manifest['identity']['dpi'])
            x0,y0,x1,y1 = args.box
            if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
                raise ValueError('Crop is outside source image')
            args.out.parent.mkdir(parents=True, exist_ok=True)
            image.crop(args.box).save(args.out)
            image.close()
            print(json.dumps(dict(image=str(args.out.resolve()), scope='region_only')))
            return
        target = args.cache/'retry'
        dpi = min(600, manifest['identity']['dpi']+100)
        command = [sys.executable, str(HERE/'read_local.py'), str(source), '--out', str(target),
                   '--pages', str(args.page), '--dpi', str(dpi), '--method', 'ocr', '--workers', '1']
        completed = subprocess.run(command, capture_output=True, text=True)
        print(completed.stdout)
        if completed.returncode:
            raise ValueError(completed.stderr)
        original = load(args.cache/f'page-{args.page:04d}.json')
        alternative = load(target/f'page-{args.page:04d}.json')
        comparison = dict(page=args.page, original_hash=digest(original), same_text=original['text']==alternative['text'],
                          original=original['text'], alternative=alternative['text'], independent=False)
        atomic_json(target/f'comparison-{args.page:04d}.json', comparison)
        print(json.dumps(dict(comparison=str(target/f'comparison-{args.page:04d}.json'),
                              same_text=comparison['same_text'], independent=False)))
        return
    if args.budget_chars < 1 or args.images < 0 or args.offset < 0:
        parser.error('budget must be positive; images and offset nonnegative')
    if args.query and not args.term:
        parser.error('A query needs at least one --term; choose keyphrases/alternate wording, not just a question sentence')
    if args.command == 'prepare':
        command = [sys.executable, str(HERE/'read_local.py'), str(args.input), '--out', str(args.out),
                   '--dpi', str(args.dpi), '--workers', str(args.workers), '--method', args.method]
        if args.pages:
            command += ['--pages', args.pages]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode not in (0, 2):
            raise ValueError(completed.stderr)
        # argparse errors and per-page failures both use 2; only structured summaries permit partial audit.
        try:
            summary = json.loads(completed.stdout)
        except ValueError:
            raise ValueError(completed.stderr)
        print(json.dumps(dict(read_summary={k:summary[k] for k in ('processed', 'cached', 'failed')},
                              requested_pages=len(summary['selected_pages'])), ensure_ascii=False))
        cache = args.out.resolve()
    else:
        cache = args.cache.resolve()
    manifest = load(cache/'manifest.json')
    pages = pages_from(args.pages, manifest['total_pages'])
    write_request(cache, pages, args.query, args.term, args.budget_chars, args.images, args.offset)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        sys.exit(2)

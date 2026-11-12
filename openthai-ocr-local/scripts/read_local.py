#!/usr/bin/env python3
"""Offline OpenThai OCR; page cache avoids repeated inference and large stdout."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from concurrent.futures import ProcessPoolExecutor

ROOT = Path.home() / '.local/share/openthai-ocr'
SCHEMA = 1


def init_worker(source, dpi):
    global engine, pdf, image_source, render_scale
    sys.path.insert(0, str(ROOT / 'models'))
    from runtime.line_engine import LineOCR
    engine = LineOCR(ROOT / 'models', threads=1, runtime={'backend': 'onnxruntime'})
    image_source = source
    render_scale = dpi / 72
    pdf = None
    if Path(source).suffix.lower() == '.pdf':
        import pypdfium2
        pdf = pypdfium2.PdfDocument(source)


def read_page(number):
    from PIL import Image
    started = time.perf_counter()
    if pdf is not None:
        page = pdf[number - 1]
        bitmap = page.render(scale=render_scale)
        image = bitmap.to_pil().copy()
        bitmap.close()
        page.close()
    else:
        with Image.open(image_source) as original:
            image = original.convert('RGB')
    result = engine.read(image)
    image.close()
    result['page'] = number
    result['elapsed_seconds'] = round(time.perf_counter() - started, 3)
    return result


def pages_from(spec, total):
    if not spec:
        return list(range(1, total + 1))
    chosen = set()
    for part in spec.split(','):
        bounds = part.strip().split('-')
        if len(bounds) == 1:
            start = end = int(bounds[0])
        elif len(bounds) == 2:
            start, end = map(int, bounds)
        else:
            raise ValueError('Invalid page range')
        if not 1 <= start <= end <= total:
            raise ValueError(f'Pages must be within 1..{total}')
        chosen.update(range(start, end + 1))
    return sorted(chosen)


def atomic_json(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--pages', help='1-based selection, e.g. 1-5,9')
    parser.add_argument('--dpi', type=int, default=200)
    parser.add_argument('--workers', type=int, default=2, help='CPU processes; one inference thread each')
    args = parser.parse_args()
    source = args.input.expanduser().resolve(strict=True)
    if args.workers < 1 or not 72 <= args.dpi <= 600:
        parser.error('workers must be positive and dpi within 72..600')
    total = 1
    if source.suffix.lower() == '.pdf':
        import pypdfium2
        with pypdfium2.PdfDocument(str(source)) as doc:
            total = len(doc)
    else:
        from PIL import Image
        with Image.open(source) as image:
            if getattr(image, 'n_frames', 1) != 1:
                parser.error('Multi-frame images are unsupported; convert to PDF first')
    try:
        pages = pages_from(args.pages, total)
    except ValueError as error:
        parser.error(str(error))
    digest = hashlib.sha256()
    with source.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    identity = dict(schema=SCHEMA, source_sha256=digest.hexdigest(),
                    revision=(ROOT / 'models/REVISION').read_text().strip(), dpi=args.dpi)
    out = args.out.expanduser().resolve()
    manifest = out / 'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())['identity'] != identity:
            parser.error('Output cache belongs to different input/settings; choose a new --out')
    elif out.exists() and any(out.iterdir()):
        parser.error('Output directory is not an OCR cache; choose an empty --out')
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(manifest, dict(identity=identity, source=str(source), total_pages=total))
    pending = [n for n in pages if not (out / f'page-{n:04d}.json').exists()]
    started = time.perf_counter()
    if pending:
        with ProcessPoolExecutor(max_workers=min(args.workers, len(pending)),
                                 initializer=init_worker, initargs=(str(source), args.dpi)) as pool:
            for result in pool.map(read_page, pending):
                atomic_json(out / f"page-{result['page']:04d}.json", result)
                print(f"page {result['page']}/{total}: {result['elapsed_seconds']} s", file=sys.stderr, flush=True)
    empty, low = [], []
    for n in pages:
        result = json.loads((out / f'page-{n:04d}.json').read_text())
        (out / f'page-{n:04d}.txt').write_text(result['text'], encoding='utf-8')
        if not result['text'].strip():
            empty.append(n)
        if any(line.get('confidence', 1) < 0.9 for line in result.get('lines', [])):
            low.append(n)
    print(json.dumps(dict(output=str(out), selected_pages=pages, processed=len(pending),
                         cached=len(pages)-len(pending), empty_pages=empty,
                         low_confidence_pages=low, elapsed_seconds=round(time.perf_counter()-started, 3)), ensure_ascii=False))


if __name__ == '__main__':
    main()

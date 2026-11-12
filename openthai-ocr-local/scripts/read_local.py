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
SCHEMA = 2


def init_worker(source, dpi, method="ocr"):
    global engine, pdf, image_source, render_scale, read_method
    sys.path.insert(0, str(ROOT / 'models'))
    engine = None
    read_method = method
    image_source = source
    render_scale = dpi / 72
    pdf = None
    if Path(source).suffix.lower() == '.pdf':
        import pypdfium2
        pdf = pypdfium2.PdfDocument(source)


def useful_text(text):
    from collections import Counter
    chars = [c for c in text if not c.isspace()]
    return (len(chars) >= 60 and sum(c.isalpha() for c in chars) >= 20
            and not any(c == "\ufffd" or (ord(c) < 32 and c not in "\n\r\t") for c in text)
            and Counter(chars).most_common(1)[0][1] / len(chars) < 0.5)


def valid_page(result, number):
    return (isinstance(result, dict) and result.get('page') == number
            and isinstance(result.get('text'), str)
            and isinstance(result.get('lines'), list) and isinstance(result.get('dropped'), list)
            and all(isinstance(line, dict) and isinstance(line.get('text'), str)
                    for line in result['lines'] + result['dropped']))


def read_page(number):
    global engine
    from PIL import Image
    started = time.perf_counter()
    image = None
    try:
        if pdf is not None:
            page = pdf[number - 1]
            if read_method == 'auto':
                textpage = page.get_textpage()
                text = textpage.get_text_range()
                textpage.close()
                has_images = any(obj.type == 3 for obj in page.get_objects())
                if useful_text(text) and not has_images:
                    lines = [{'text': t, 'confidence': None, 'box': None, 'row': i}
                             for i, t in enumerate(text.splitlines()) if t.strip()]
                    page.close()
                    return dict(page=number, text='\n'.join(t['text'] for t in lines),
                                lines=lines, dropped=[], method='text_layer',
                                elapsed_seconds=round(time.perf_counter()-started, 3))
            bitmap = page.render(scale=render_scale)
            image = bitmap.to_pil().copy()
            bitmap.close()
            page.close()
        else:
            with Image.open(image_source) as original:
                image = original.convert('RGB')
        from runtime.line_engine import LineOCR
        if engine is None:
            engine = LineOCR(ROOT / 'models', threads=1, runtime={'backend': 'onnxruntime'})
        result = engine.read(image)
        import numpy as np
        ink = float((np.asarray(image.convert('L')) < 235).mean())
        result.update(page=number, method='ocr', image_size=list(image.size),
                      ink_fraction=round(ink, 6),
                      elapsed_seconds=round(time.perf_counter()-started, 3))
        return result
    except Exception as error:
        return dict(page=number, error=f'{type(error).__name__}: {error}')
    finally:
        if image is not None:
            image.close()


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
    parser.add_argument('--method', choices=['auto', 'ocr'], default='ocr')
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
                    revision=(ROOT / 'models/REVISION').read_text().strip(), dpi=args.dpi,
                    method=args.method, reader_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    out = args.out.expanduser().resolve()
    manifest = out / 'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())['identity'] != identity:
            parser.error('Output cache belongs to different input/settings; choose a new --out')
    elif out.exists() and any(out.iterdir()):
        parser.error('Output directory is not an OCR cache; choose an empty --out')
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(manifest, dict(identity=identity, source=str(source), total_pages=total))
    pending = []
    for n in pages:
        try:
            good = valid_page(json.loads((out / f'page-{n:04d}.json').read_text()), n)
        except (OSError, ValueError):
            good = False
        if not good:
            pending.append(n)
    failed = []
    started = time.perf_counter()
    if pending:
        with ProcessPoolExecutor(max_workers=min(args.workers, len(pending)),
                                 initializer=init_worker, initargs=(str(source), args.dpi, args.method)) as pool:
            for result in pool.map(read_page, pending):
                if 'error' in result:
                    failed.append(result)
                    print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
                    continue
                atomic_json(out / f"page-{result['page']:04d}.json", result)
                print(f"page {result['page']}/{total}: {result['elapsed_seconds']} s", file=sys.stderr, flush=True)
    empty, low = [], []
    for n in pages:
        if n in [item['page'] for item in failed]:
            continue
        result = json.loads((out / f'page-{n:04d}.json').read_text())
        (out / f'page-{n:04d}.txt').write_text(result['text'], encoding='utf-8')
        if not result['text'].strip():
            empty.append(n)
        if any(line.get('confidence') is not None and line['confidence'] < 0.9 for line in result.get('lines', [])):
            low.append(n)
    print(json.dumps(dict(output=str(out), selected_pages=pages, processed=len(pending)-len(failed), attempted=len(pending),
                         cached=len(pages)-len(pending), failed=failed, empty_pages=empty,
                         low_confidence_pages=low, elapsed_seconds=round(time.perf_counter()-started, 3)), ensure_ascii=False))
    return 2 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

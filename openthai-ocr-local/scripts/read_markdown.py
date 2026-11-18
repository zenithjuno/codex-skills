#!/usr/bin/env python3
"""Run the optional OpenThai Markdown model on selected pages using local Metal."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

from read_local import pages_from

ROOT = Path.home() / ".local/share/openthai-ocr/markdown"


def images(source, spec):
    from PIL import Image

    if source.suffix.lower() != ".pdf":
        pages_from(spec, 1)
        with Image.open(source) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("Use a single image or convert to PDF first")
            yield 1, image.convert("RGB")
        return
    if not spec:
        raise ValueError("For a PDF, select the specific pages with --pages")
    import pypdfium2

    with pypdfium2.PdfDocument(str(source)) as document:
        for number in pages_from(spec, len(document)):
            with contextlib.closing(document[number - 1]) as page:
                with contextlib.closing(page.render(scale=200 / 72)) as bitmap:
                    image = bitmap.to_pil().convert("RGB")
            yield number, image


@contextlib.contextmanager
def local_parser(output):
    import httpx
    from nemotron_parse.inference import DocumentParser, GenerationSettings

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    key = secrets.token_hex(32)
    client = httpx.Client(trust_env=False, timeout=180, headers={"Authorization": f"Bearer {key}"})
    base = f"http://127.0.0.1:{port}"
    with client, (output / "runtime.log").open("wb") as log:
        command = [
            str(ROOT / "bin/llama-server"),
            "-m", str(ROOT / "gguf/openthai2.1-ocr-markdown-q8_0.gguf"),
            "--mmproj", str(ROOT / "gguf/mmproj-openthai2.1-ocr-markdown-f16.gguf"),
            "--host", "127.0.0.1", "--port", str(port), "--alias", "openthai-markdown",
            "--jinja", "-c", "16384", "-np", "1", "-ngl", "99", "--repeat-penalty", "1.0",
        ]
        server = subprocess.Popen(command, stdout=log, stderr=log, env={**os.environ, "LLAMA_API_KEY": key})
        try:
            deadline = time.monotonic() + 90
            while True:
                if server.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError(f"Local engine failed to start. See {output / 'runtime.log'}")
                try:
                    if client.get(base + "/health", timeout=1).is_success:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.25)
            with DocumentParser(
                base_url=base + "/v1", model="openthai-markdown", api_key=key,
                client=client, fullpage=GenerationSettings(temperature=0.0, repetition_penalty=1.0),
            ) as parser:
                yield parser
        finally:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("--pages", help="PDF page selection, e.g. 2,5-7")
    cli.add_argument("--out", type=Path, required=True, help="New directory for per-page output")
    args = cli.parse_args()
    source = args.source.expanduser().resolve(strict=True)
    if not (ROOT / "pins.json").is_file():
        cli.error(f"Markdown runtime is not installed at {ROOT}")
    if source.suffix.lower() == ".pdf" and not args.pages:
        cli.error("For a PDF, select the specific pages with --pages")
    sys.path.insert(0, str(ROOT / "parser"))
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    pins = json.loads((ROOT / "pins.json").read_text())
    with local_parser(output) as parser:
        for number, image in images(source, args.pages):
            started = time.monotonic()
            with image:
                document = parser.parse(image)
            elapsed = round(time.monotonic() - started, 2)
            stem = output / f"page-{number:04d}"
            stem.with_suffix(".md").write_text(document["markdown"], encoding="utf-8")
            record = dict(source=str(source), page=number, seconds=elapsed, pins=pins, document=document)
            stem.with_suffix(".json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            print(json.dumps(dict(page=number, seconds=elapsed, markdown=str(stem.with_suffix(".md")))), flush=True)


if __name__ == "__main__":
    main()

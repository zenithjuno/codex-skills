"""Physical print styles shared by Solve diagram generators (no rendering dependencies)."""
from dataclasses import dataclass
from math import ceil
from pathlib import Path
import json

STYLE_PATH = Path(__file__).resolve().parents[1] / 'assets/math-figures/coordinate-graph-style.json'

@dataclass(frozen=True)
class PrintStyle:
    height_cm: float
    view_height: float
    values: dict

    @classmethod
    def load(cls, height_cm, view_height=760, path=STYLE_PATH):
        if height_cm <= 0 or view_height <= 0:
            raise ValueError('Print height and view height must be positive')
        values = json.loads(Path(path).read_text(encoding='utf-8'))
        return cls(float(height_cm), float(view_height), values)

    def units(self, pt):
        return float(pt) * self.view_height * 2.54 / (self.height_cm * 72)

    def token(self, name):
        return self.units(self.values[name])

    def points(self, units):
        return float(units) * self.height_cm * 72 / (self.view_height * 2.54)

    @property
    def raster_scale(self):
        return max(3, ceil(self.height_cm / 2.54 * self.values['min_dpi'] / self.view_height))

    def report(self):
        return {'height_cm': self.height_cm, 'view_height': self.view_height,
                'min_dpi': self.values['min_dpi'],
                'physical_pt': {k: v for k, v in self.values.items() if k.endswith('_pt')}}


def verify_docx_media(docx_path, image_paths, height_cm):
    """Reject size drift or stale images after a handout build."""
    from hashlib import sha256
    from zipfile import ZipFile
    from xml.etree import ElementTree as E
    namespaces = {'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
                  'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
                  'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}
    with ZipFile(docx_path) as package:
        root = E.fromstring(package.read('word/document.xml'))
        sizes = root.findall('.//wp:extent', namespaces)
        expected = round(float(height_cm) * 360000)
        if len(sizes) != len(image_paths) or any(int(s.attrib['cy']) != expected for s in sizes):
            raise ValueError('DOCX image heights do not match figure configuration')
        links = {r.attrib['Id']:r.attrib['Target'] for r in E.fromstring(package.read('word/_rels/document.xml.rels'))}
        images = root.findall('.//a:blip', namespaces)
        if len(images) != len(image_paths):
            raise ValueError('DOCX image count differs from generated figures')
        for image, source in zip(images, image_paths):
            rid = image.attrib['{'+namespaces['r']+'}embed']
            if sha256(package.read('word/'+links[rid])).digest() != sha256(Path(source).read_bytes()).digest():
                raise ValueError(f'DOCX contains an outdated figure: {source}')

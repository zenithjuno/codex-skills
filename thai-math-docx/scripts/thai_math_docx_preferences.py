"""Numeric DOCX preferences shared by generation and independent QA."""
from pathlib import Path
import json
import math
import os

SPACING_CONFIG_PATH = Path(__file__).resolve().parents[1]/'assets/paragraph-spacing.json'


def load_spacing_preferences(path=None):
    """Read fresh preferences; an explicit project override applies to build and QA.

    THAI_MATH_DOCX_SPACING_CONFIG may point to a project JSON using the same schema.
    There are no cached or separately hard-coded numeric fallback preferences.
    """
    source = Path(path or os.environ.get('THAI_MATH_DOCX_SPACING_CONFIG') or SPACING_CONFIG_PATH)
    values = json.loads(source.read_text(encoding='utf-8'))
    if values.get('schema_version') != 1:
        raise ValueError(f'{source}: unsupported spacing schema_version')
    for key in ('default_before_pt','default_after_pt','gap_pt','line_spacing'):
        value = values.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f'{source}: {key} must be a finite number')
        if value < 0 or key in ('gap_pt','line_spacing') and value == 0:
            raise ValueError(f'{source}: invalid {key}')
    allowed = {0, values['gap_pt']}
    if any(values[key] not in allowed for key in ('default_before_pt','default_after_pt')):
        raise ValueError(f'{source}: default gaps must be zero or gap_pt')
    if any(round(values[key]*20) != values[key]*20 for key in ('default_before_pt','default_after_pt','gap_pt')):
        raise ValueError(f'{source}: point gaps must be representable in Word twips')
    if round(values['line_spacing']*240) <= 0:
        raise ValueError(f'{source}: line_spacing is too small')
    return values

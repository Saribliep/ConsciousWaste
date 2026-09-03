"""
Builds the personalized TTS monologue from survey answers.
The actual Dutch text lives in text_templates/monologue.txt.jinja —
edit that file to change wording, this module just renders it.

The template also carries PAUZE-<seconds> markers (e.g. PAUZE-3) at
spots meant to become silent beats in the generated audio, mimicking
the pauses of someone thinking out loud. create_tss_segments() splits
on those markers so app.py can synthesise each text chunk separately
and stitch in real silence between them; create_tss_text() strips
them out entirely for the human-readable version (DB storage, mock
preview).
"""

import os
import re
from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'text_templates')
_PAUSE_RE = re.compile(r'PAUZE-(\d+)')

_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
)
_template = _env.get_template('monologue.txt.jinja')


def _render_raw(vals: dict) -> str:
    context = {**vals, 'naam': vals.get('q1', '').strip()}
    rendered = _template.render(**context)

    # Collapse the whitespace left behind by empty/skipped branches
    rendered = re.sub(r'[ \t]+', ' ', rendered)
    rendered = re.sub(r' \n', '\n', rendered)
    rendered = re.sub(r'\n{3,}', '\n\n', rendered)
    return rendered.strip()


def create_tss_text(vals: dict) -> str:
    """Human-readable version — PAUZE markers stripped. Used for the
    survey.db tts_text column and the MOCK_TTS preview."""
    raw = _render_raw(vals)
    text = _PAUSE_RE.sub(' ', raw)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' \n', '\n', text)
    return text.strip()


def create_tss_segments(vals: dict) -> list:
    """Ordered list of ('text', str) / ('pause', seconds) tuples for
    actually synthesising audio — each text segment becomes its own
    Voxtral call, each pause becomes real silence, stitched together
    in order."""
    raw = _render_raw(vals)
    parts = _PAUSE_RE.split(raw)

    segments = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            text = part.strip()
            if text:
                segments.append(('text', text))
        else:
            segments.append(('pause', int(part)))
    return segments

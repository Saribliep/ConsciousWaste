"""
Builds the personalized TTS monologue from survey answers.
The actual Dutch text lives in text_templates/monologue.txt.jinja —
edit that file to change wording, this module just renders it.
"""

import os
import re
from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'text_templates')

_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
)
_template = _env.get_template('monologue.txt.jinja')


def create_tss_text(vals: dict) -> str:
    context = {**vals, 'naam': vals.get('q1', '').strip()}
    rendered = _template.render(**context)

    # Collapse the whitespace left behind by empty/skipped branches
    rendered = re.sub(r'[ \t]+', ' ', rendered)
    rendered = re.sub(r' \n', '\n', rendered)
    rendered = re.sub(r'\n{3,}', '\n\n', rendered)
    return rendered.strip()

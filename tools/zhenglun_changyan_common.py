"""Provenance helpers for the two-book Wikisource compilation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / 'sources/zhenglun-changyan/progress.json'


def apparatus(raw):
    """Move balanced 〈editorial notes〉 out of the text, retaining exact positions."""
    main, notes, i = [], [], 0
    while i < len(raw):
        if raw[i] != '〈':
            main.append(raw[i])
            i += 1
            continue
        start, depth = i, 1
        i += 1
        while i < len(raw) and depth:
            depth += (raw[i] == '〈') - (raw[i] == '〉')
            i += 1
        assert depth == 0, raw[start:]
        notes.append({'main_offset': len(main), 'text': raw[start:i]})
    return ''.join(main), notes


def restore(main, notes):
    out, start = [], 0
    for note in notes:
        pos = note['main_offset']
        assert start <= pos <= len(main)
        out += [main[start:pos], note['text']]
        start = pos
    return ''.join(out) + main[start:]


def source_parts(raw):
    # The site's line-oriented source format cannot contain literal p-internal newlines.
    text, breaks = [], []
    for char in raw:
        if char in '\r\n':
            breaks.append({'main_offset': len(text), 'text': char})
        else:
            text.append(char)
    main, notes = apparatus(''.join(text))
    return main, notes, breaks


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def load():
    return json.loads(PROGRESS.read_text())


def save(progress):
    PROGRESS.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n')

#!/usr/bin/env python3
"""Site-wide audit of the generated pages (all books): links, anchors, headings, hover pairs and note counts."""
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build

SKIP = {'sources', 'tests', 'tools', 'assets', 'src', '.git'}


def html_pages():
    for f in sorted(ROOT.rglob('*.html')):
        if f.relative_to(ROOT).parts[0] in SKIP:
            continue
        yield f


def soup_of(path, cache={}):
    if path not in cache:
        cache[path] = BeautifulSoup(path.read_text(encoding='utf8'), 'html.parser')
    return cache[path]


def check_structure(problems):
    count = 0
    for f in html_pages():
        count += 1
        s = soup_of(f)
        rel = f.relative_to(ROOT)
        if not s.select_one('h1'):
            problems.append((str(rel), 'no h1'))
        ids = [x['id'] for x in s.select('[id]')]
        if len(ids) != len(set(ids)):
            problems.append((str(rel), 'duplicate ids'))
        for a in s.select('a[href]'):
            u = urlparse(a['href'])
            if u.scheme or u.netloc:
                continue
            target = (f.parent / unquote(u.path)).resolve() if u.path else f
            if not target.exists():
                problems.append((str(rel), 'missing link', a['href']))
            elif u.fragment and target.suffix == '.html':
                if not soup_of(target).find(id=unquote(u.fragment)):
                    problems.append((str(rel), 'missing anchor', a['href']))
        for b in s.select('button.note-btn'):
            box = s.find(id=b.get('aria-controls', ''))
            if box is None or not box.has_attr('hidden'):
                problems.append((str(rel), 'note box not collapsed'))
                continue
            m = re.search(r'注释（(\d+)）', b.get_text())
            if m and int(m[1]) != len(box.find_all('li', recursive=False)):
                problems.append((str(rel), 'note count mismatch'))
    return count


def check_poetry_books(problems):
    n = 0
    for slug, spec in build.POETRY.items():
        for page_slug, _title in spec['pages']:
            if page_slug is None:
                continue
            files = sorted((ROOT / 'src' / slug / page_slug).glob('*.txt')) if (ROOT / 'src' / slug / page_slug).exists() else []
            if not files:
                continue
            n += 1
            html = ROOT / slug / f'{page_slug}.html'
            if not html.exists():
                problems.append((slug, page_slug, 'page not built'))
                continue
            secs = build.parse_poems(files)
            pairs = [(o.replace('/', ''), t) for s in secs for c in s['chunks'] if 'tbl' not in c and c['t'] is not None
                     for o, t in build.split_pairs(c['o'], c['t'])]
            notes = sum(len(c['notes']) for s in secs for c in s['chunks'] if 'tbl' not in c)
            s = soup_of(html)
            got = [(x.get_text(), x['data-t']) for x in s.select('.s[data-t]')]
            if got != pairs:
                problems.append((slug, page_slug, 'hover pairs differ from source'))
            shown = 0
            for b in s.select('button.note-btn'):
                m = re.search(r'注释（(\d+)）', b.get_text())
                if m:
                    shown += int(m[1])
            if shown != notes:
                problems.append((slug, page_slug, 'notes', shown, notes))
    return n


def main():
    problems = []
    pages = check_structure(problems)
    book_pages = check_poetry_books(problems)
    for p in problems[:40]:
        print('PROBLEM', *p)
    if problems:
        sys.exit(f'{len(problems)} problem(s)')
    print(f'OK: {pages} pages, {book_pages} source pages cross-checked')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Audit 春秋左传: source coverage (ignoring punctuation), sentence alignment, notes, rendered pages."""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build
from prepare_zuozhuan import GONG, load  # noqa: E402  (tools/ is on sys.path when run as a script)

PUNCT = '\n，。；：？！、．.,:;“”‘’「」『』（）()《》〈〉…—·‧/ 　〔〕'
strip = lambda t: ''.join(c for c in re.sub('[-]', '缺字', t) if c not in PUNCT)


def main():
    progress = json.loads((ROOT / 'sources/zuozhuan/progress.json').read_text())
    pages = load()
    total = {'pairs': 0, 'notes': 0, 'sections': 0, 'chars': 0}
    for p in progress['pages']:
        sections = build.parse_poems(sorted((ROOT / 'src/zuozhuan' / p['slug']).glob('*.txt')))
        src = pages['序' if p['slug'] == 'xu' else next(g for g in GONG if p['source']['title'].endswith(g))]
        assert src['revision'] == p['source']['revision']
        assert hashlib.sha256('\n'.join(b['text'] for b in src['blocks']).encode()).hexdigest() == p['source']['text_sha256']
        # expected text: the page's years, from the cached source
        want, cur = [], None
        for b in src['blocks']:
            if b['type'] == 'h2':
                cur = b['text']
            elif b['type'] == 'p' and (p['slug'] == 'xu' or cur in p['years']) and b['text'] != '回目录下一篇':
                want.append(b['text'])
        got = [c['o'] for s in sections for c in s['chunks']]
        assert strip(''.join(got)) == strip(''.join(want)), (p['slug'], 'coverage')
        assert len(got) == len(want), (p['slug'], 'paragraph count')
        total['chars'] += len(strip(''.join(got)))
        # sections and per-year 题解
        titles = [s['title'] for s in sections]
        if p['slug'] != 'xu':
            years = []
            for t in titles:
                y = t.split('·')[0]
                if y not in years: years.append(y)
            assert years == p['years'], (p['slug'], 'years')
            for y in years:
                first = next(s for s in sections if s['title'].split('·')[0] == y)
                assert first['intro'], (p['slug'], y, 'missing 题解')
                for s in sections:
                    if s['title'].split('·')[0] == y and s is not first:
                        assert not s['intro'], (p['slug'], s['title'], 'extra 题解')
        pairs = []
        for s in sections:
            seen = set()
            for c in s['chunks']:
                assert c['t'] is not None and c['notes'], (p['slug'], s['title'], c['o'][:20])
                groups = build._frag_groups(build.split_sents(c['o']))
                assert len(c['t'].split('¦')) == len(groups), (p['slug'], s['title'], c['o'][:20])
                pairs.extend(build.split_pairs(c['o'], c['t']))
                for n in c['notes']:
                    term = n.split('：', 1)[0]
                    assert term not in seen or term == '校', (p['slug'], s['title'], term, 'repeat in section')
                    seen.add(term)
                total['notes'] += len(c['notes'])
        total['sections'] += len(sections)
        path = ROOT / 'zuozhuan' / (p['slug'] + '.html')
        soup = BeautifulSoup(path.read_text(), 'html.parser')
        assert [(n.get_text(), n['data-t']) for n in soup.select('.s[data-t]')] == [(o.replace('/', ''), t) for o, t in pairs], (p['slug'], 'rendered pairs')
        html_notes = 0
        for b in soup.select('button.note-btn'):
            m = re.search(r'注释（(\d+)）', b.get_text())
            if not m: continue
            t = soup.find(id=b['aria-controls'])
            assert t.has_attr('hidden') and int(m[1]) == len(t.find_all('li', recursive=False)), (p['slug'], 'note button')
            html_notes += int(m[1])
        assert html_notes == sum(len(c['notes']) for s in sections for c in s['chunks']), (p['slug'], 'rendered notes')
        for a in soup.select('a[href]'):
            href = a['href'].split('#')[0].split('?')[0]
            if href and not re.match(r'[a-z]+:', href):
                assert (path.parent / href).exists(), (path, href)
        total['pairs'] += len(pairs)
    assert (ROOT / 'zuozhuan/tijie.html').exists()
    print(f"OK: {len(progress['pages'])} pages, {total['sections']} sections, {total['chars']} chars, "
          f"{total['pairs']} sentence pairs, {total['notes']} notes")


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()

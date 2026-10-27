#!/usr/bin/env python3
"""Audit source coverage, chapter sequence, annotation anchors and generated pages."""
import hashlib
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build import parse_poems


def flatten(text):
    return re.sub(r'[\s/]', '', text)


def main():
    report = {}
    for slug, count in [('xixiangji',5),('xiyouji',100),('shuihuzhuan',120),('sanguoyanyi',120)]:
        dest = ROOT/'sources'/slug
        progress = json.loads((dest/'progress.json').read_text())
        chapters = [p for p in progress['pages'] if p['kind']=='chapter']
        assert [p['number'] for p in chapters] == list(range(1,count+1)),slug
        assert all(p['notes'] > 0 for p in chapters),slug
        cache = {d['title']:d for p in (dest/'wikisource/pages').glob('*.json') for d in [json.loads(p.read_text())]}
        chars = notes = 0
        for p in progress['pages']:
            files = sorted((ROOT/'src'/slug/p['slug']).glob('*.txt'))
            sections = parse_poems(files)
            assert sections, (slug,p['slug'])
            originals = ''.join(ch['o'] for s in sections for ch in s['chunks'])
            assert all(ch['t'] is None for s in sections for ch in s['chunks']), (slug,p['slug'],'unexpected translation')
            if p['kind'] not in ('editorial','opening_lyric'):
                d = cache[p['source']['title']]
                assert d['revision'] == p['source']['revision']
                raw = '\n'.join(b['text'] for b in d['blocks'])
                assert hashlib.sha256(raw.encode()).hexdigest() == p['source']['text_sha256']
                expected = ''.join(b['text'] for b in d['blocks'] if not b['type'].startswith('h'))
                assert flatten(originals) == flatten(expected),(slug,p['slug'],'source coverage')
                heading_texts = [b['text'] for b in d['blocks'] if b['type'].startswith('h')]
                assert [s['title'] for s in sections][1:] == heading_texts,(slug,p['slug'],'section headings')
                if p['kind'] == 'chapter':
                    assert len(flatten(originals)) > 500,(slug,p['slug'],'suspiciously short')
            actual_notes = 0
            seen = set()
            for section in sections:
                for ch in section['chunks']:
                    for note in ch['notes']:
                        actual_notes += 1
                        term = note.split('：',1)[0]
                        assert term in ch['o'] or (p['kind'] == 'opening_lyric' and term in section['title']),(slug,p['slug'],term,'unanchored note')
                        assert term not in seen,(slug,p['slug'],term,'repeated note')
                        seen.add(term)
            assert actual_notes == p['notes'],(slug,p['slug'],actual_notes,p['notes'])
            html_path = ROOT/slug/(p['slug']+'.html')
            soup = BeautifulSoup(html_path.read_text(),'html.parser')
            assert not soup.select('[data-t]'),(slug,p['slug'],'translation tooltip')
            html_notes = 0
            for button in soup.select('button.note-btn'):
                label = button.get_text()
                if '注释' not in label:continue
                target = soup.find(id=button['aria-controls'])
                total = len(target.find_all('li',recursive=False))
                assert int(re.search(r'（(\d+)）',label).group(1)) == total
                html_notes += total
            assert html_notes == actual_notes,(slug,p['slug'],'rendered count')
            for a in soup.select('a[href]'):
                href = a['href'].split('#')[0].split('?')[0]
                if href and not re.match(r'[a-z]+:',href):
                    assert (html_path.parent/href).exists(),(html_path,href)
            notes += actual_notes;chars += len(flatten(originals))
        report[slug]={'chapters':count,'pages':len(progress['pages']),'characters':chars,'notes':notes,'status':'passed'}
    (ROOT/'sources/four-classics-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == '__main__': main()

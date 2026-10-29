#!/usr/bin/env python3
"""Audit planned source coverage and completed Mengxi sentence translations."""
import json,sys,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import build
from zhenglun_changyan_common import source_parts,restore,digest
from check_liaozhai import Reader
ap=argparse.ArgumentParser();ap.add_argument('--report',type=Path);args=ap.parse_args()
j=json.loads((ROOT/'sources/mengxi/progress.json').read_text());coverage={};rows=[]
for p in j['pages']:
 if p.get('kind')=='editorial':continue
 snap=json.loads((ROOT/p['source']['snapshot']).read_text());expected=[];ns=0;done=0
 for u in p['units']:
  key=p['source']['snapshot'];coverage.setdefault(key,[]).append(u['source_block_index'])
  raw=snap['blocks'][u['source_block_index']]['text'];main,notes,breaks=source_parts(raw)
  assert digest(raw)==u['raw_sha256'] and digest(main)==u['main_sha256']
  assert notes==u['source_notes'] and breaks==u['format_breaks']
  assert restore(restore(main,notes),breaks)==raw
  path=ROOT/'src/mengxi'/p['slug']/(u['id']+'.txt')
  if u['status']!='complete':assert not path.exists();continue
  secs=build.parse_poems([path]);assert len(secs)==1 and secs[0]['intro'] and len(secs[0]['chunks'])==1
  c=secs[0]['chunks'][0];assert c['o']==main
  ts=c['t'].split('¦');assert len(ts)==len(build.split_sents(main))==u['sentence_pairs'];assert all(t.strip()for t in ts)
  assert len(build.split_pairs(main,c['t']))==len(ts)
  apparatus=[f'底本夹注{k:02}（主文第{n["main_offset"]}字后）：'+n['text']for k,n in enumerate(notes,1)]+[f'底本网页注{k:02}：'+n for k,n in enumerate(u.get('source_reference_notes',[]),1)]
  assert c['notes'][:len(apparatus)]==apparatus
  assert len(c['notes'])==u['source_note_count']+u['editor_note_count']
  for line in path.read_text().splitlines():
   if line.startswith('注：'):assert len(build.split_notes(line[2:]))==1
  done+=1;ns+=len(c['notes']);expected.extend(ts)
 if done:
  reader=Reader();reader.feed((ROOT/'mengxi'/(p['slug']+'.html')).read_text());assert reader.translations==expected
  assert len(reader.anchors)==done
  for target,count in reader.buttons:assert reader.lists[target]==count
 if p['annotation_status']=='complete':assert done==len(p['units'])
 rows.append(dict(page=p['slug'],completed_units=done,total_units=len(p['units']),sentence_pairs=len(expected),notes=ns))
for snapshot,indexes in coverage.items():
 snap=json.loads((ROOT/snapshot).read_text());skip={r['source_block_index']for r in j.get('source_only_headings',[])if r['snapshot']==snapshot}
 assert sorted(indexes)==[i for i,b in enumerate(snap['blocks'])if b['type']=='p' and i not in skip],snapshot
manifest=json.loads((ROOT/'sources/mengxi/wikisource/manifest.json').read_text())
for r in manifest['pages']:assert digest((ROOT/r['raw_snapshot']).read_bytes().decode())==r['raw_sha256']
home=(ROOT/'index.html').read_text();assert 'mengxi/index.html' in home and 'book-search' in home
report=dict(pages=rows,completed_units=sum(r['completed_units']for r in rows),total_units=sum(r['total_units']for r in rows),sentence_pairs=sum(r['sentence_pairs']for r in rows),notes=sum(r['notes']for r in rows),source_reconstruction_matches=True,raw_snapshots_verified=True,rendered_pairs_match=True,note_counts_match=True,next=j['next'],browser_visual_check=False,scope='Technical coverage; semantic completeness requires editorial reading.')
if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))

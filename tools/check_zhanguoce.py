#!/usr/bin/env python3
"""Audit the two completed volumes of the Shiliju edition, not the whole book."""
import json,sys,argparse,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import build
from zhenglun_changyan_common import source_parts,restore,digest
from check_liaozhai import Reader
ap=argparse.ArgumentParser();ap.add_argument('--report',type=Path);args=ap.parse_args()
j=json.loads((ROOT/'sources/zhanguoce/progress.json').read_text());rows=[]
assert [(p['slug'],len(p['units'])) for p in j['pages']]==[('dongzhou',28),('xizhou',17)]
for p in j['pages']:
 snap=json.loads((ROOT/p['source']['snapshot']).read_text());covered=list(p['preface_block_indices']);ts_all=[];nc=0
 raw_path=ROOT/snap['raw_snapshot'];assert digest(raw_path.read_text())==snap['raw_sha256']
 assert snap['revision']==p['source']['revision']
 assert [b['text'] for b in snap['blocks'] if b['type']=='h2']==[u['title'] for u in p['units']]
 for idx,u in enumerate(p['units']):
  assert u['status']=='complete'
  covered.extend(u['source_block_indices']);raw='\n'.join(snap['blocks'][i]['text'] for i in u['source_block_indices']);main,notes,breaks=source_parts(raw)
  assert digest(raw)==u['raw_sha256'] and digest(main)==u['main_sha256']
  assert notes==u['source_notes'] and breaks==u['format_breaks'];assert restore(restore(main,notes),breaks)==raw
  path=ROOT/'src/zhanguoce'/p['slug']/(u['id']+'.txt');secs=build.parse_poems([path]);assert len(secs)==1 and secs[0]['intro'] and len(secs[0]['chunks'])==1
  c=secs[0]['chunks'][0];assert c['o']==main;ts=c['t'].split('¦');assert len(ts)==len(build.split_sents(main))==u['sentence_pairs'];assert all(t.strip() for t in ts)
  assert len(build.split_pairs(main,c['t']))==len(ts)
  apparatus=[f'底本原注{k:03}（主文第{n["main_offset"]}字后）：'+n['text'] for k,n in enumerate(notes,1)]
  if idx==0:apparatus=['底本卷首注（非本篇主文）：'+snap['blocks'][0]['text']]+apparatus
  assert c['notes'][:len(apparatus)]==apparatus
  assert len(c['notes'])==u['source_note_count']+u['editor_note_count']+(idx==0)
  for line in path.read_text().splitlines():
   if line.startswith('注：'):assert len(build.split_notes(line[2:]))==1
  nc+=len(c['notes']);ts_all.extend(ts)
 assert sorted(covered)==[i for i,b in enumerate(snap['blocks']) if b['type']=='p']
 reader=Reader();reader.feed((ROOT/'zhanguoce'/(p['slug']+'.html')).read_text());assert reader.translations==ts_all;assert len(reader.anchors)==len(p['units'])
 for target,count in reader.buttons:assert reader.lists[target]==count
 rows.append(dict(page=p['slug'],chapters=len(p['units']),sentence_pairs=len(ts_all),notes=nc))
home=(ROOT/'index.html').read_text();assert 'zhanguoce/index.html' in home and 'book-search' in home
report=dict(pages=rows,completed_chapters=sum(r['chapters'] for r in rows),sentence_pairs=sum(r['sentence_pairs'] for r in rows),notes=sum(r['notes'] for r in rows),source_coverage=True,source_reconstruction=True,raw_snapshot_hashes=True,rendered_pairs=True,note_counts=True,whole_book_complete=False,browser_visual_check=False)
assert report['completed_chapters']==j['completed_units'];assert report['sentence_pairs']==j['sentence_pairs'];assert report['notes']==j['notes']
if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))

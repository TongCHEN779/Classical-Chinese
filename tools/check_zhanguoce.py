#!/usr/bin/env python3
"""Audit completed Shiliju pages, including prefaces and appendices; not the whole book."""
import json,sys,argparse,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import build
from zhenglun_changyan_common import source_parts,restore,digest
from check_liaozhai import Reader
ap=argparse.ArgumentParser();ap.add_argument('--report',type=Path);args=ap.parse_args()
j=json.loads((ROOT/'sources/zhanguoce/progress.json').read_text());rows=[]
groups=json.loads((ROOT/'sources/zhanguoce/reading-groups.json').read_text())['groups'];group_members={x for g in groups for x in g['members']}
assert [p['slug']for p in j['pages']]==[f'xu{i:02}'for i in range(1,7)]+['dongzhou','xizhou']+[f'qin{i:02}'for i in range(1,6)]+[f'qi{i:02}'for i in range(1,7)]+[f'chu{i:02}'for i in range(1,5)]+[f'zhao{i:02}'for i in range(1,5)]+[f'wei{i:02}'for i in range(1,5)]+[f'han{i:02}'for i in range(1,4)]+[f'yan{i:02}'for i in range(1,4)]+['songwei','zhongshan']+[f'fu{i:02}'for i in range(1,7)]
for p in j['pages']:
 snap=json.loads((ROOT/p['source']['snapshot']).read_text());covered=list(p['preface_block_indices'])+p.get('source_heading_indices',[]);ts_all=[];nc=0
 raw_path=ROOT/snap['raw_snapshot'];assert digest(raw_path.read_text())==snap['raw_sha256']
 assert snap['revision']==p['source']['revision']
 if snap.get('source_reference_notes'):
  from bs4 import BeautifulSoup
  html=BeautifulSoup(raw_path.read_text(),'html.parser')
  assert [n for u in p['units']for n in u.get('source_reference_notes',[])]==[n['text']for n in snap['source_reference_notes']]
  for n in snap['source_reference_notes']:assert html.find(id=n['id']).get_text(' ',strip=True).lstrip('↑ ').strip()==n['text']
 for hi in p.get('source_reference_heading_indices',[]):assert snap['blocks'][hi]['text']=='注释'
 if p['slug'] in ['dongzhou','xizhou']or p.get('kind')=='body':
  assert [b['text'] for i,b in enumerate(snap['blocks']) if b['type']==p.get('unit_heading_type','h2')and i not in p.get('source_reference_heading_indices',[])+p.get('empty_heading_indices',[])]==[u['title'] for u in p['units']if u.get('kind')!='source_note_appendix']
 for hi in p.get('source_heading_indices',[]):
  assert snap['blocks'][hi]['text'] in [u['title'] for u in p['units']]
 for idx,u in enumerate(p['units']):
  assert u['status']=='complete'
  covered.extend(u['source_block_indices'])
  if u.get('kind')=='source_note_appendix':
   parent=next(x for x in p['units']if x['id']==u['source_parent_id']);raw=parent['source_notes'][u['source_note_index']]['text'][1:-1];assert raw==u['source_note_excerpt']
  else:raw='\n'.join(snap['blocks'][i]['text'] for i in u['source_block_indices'])
  main,notes,breaks=source_parts(raw)
  assert digest(raw)==u['raw_sha256'] and digest(main)==u['main_sha256']
  assert notes==u['source_notes'] and breaks==u['format_breaks'];assert restore(restore(main,notes),breaks)==raw
  path=ROOT/'src/zhanguoce'/p['slug']/(u['id']+'.txt');secs=build.parse_poems([path]);assert len(secs)==1 and secs[0]['intro']
  chunks=secs[0]['chunks'];assert len(chunks)==(2 if p['slug']=='qin04'and u['id']=='004'else 1)
  c=chunks[0];assert ''.join(x['o']for x in chunks)==main;ts=[t for x in chunks for t in x['t'].split('¦')];assert len(ts)==len(build.split_sents(main))==u['sentence_pairs'];assert all(t.strip() for t in ts)
  assert all(len(build.split_pairs(x['o'],x['t']))==len(x['t'].split('¦'))for x in chunks)
  apparatus=[f'底本原注{k:03}（主文第{n["main_offset"]}字后）：'+n['text'] for k,n in enumerate(notes,1)]+[f'底本网页校注{k:02}：'+n for k,n in enumerate(u.get('source_reference_notes',[]),1)]
  if idx==0 and p['preface_block_indices']:apparatus=['底本卷首注（非本篇主文）：'+snap['blocks'][0]['text']]+apparatus
  assert c['notes'][:len(apparatus)]==apparatus
  assert len(c['notes'])==u['source_note_count']+u['editor_note_count']+(idx==0 and bool(p['preface_block_indices']))
  for line in path.read_text().splitlines():
   if line.startswith('注：'):assert len(build.split_notes(line[2:]))==1
  nc+=len(c['notes']);ts_all.extend(ts)
 assert sorted(covered)==[i for i,b in enumerate(snap['blocks']) if b['type']=='p' or p.get('kind')in ['preface','appendix']],p['slug']
 if p['slug']not in group_members:
  reader=Reader();reader.feed((ROOT/'zhanguoce'/(p['slug']+'.html')).read_text());assert reader.translations==ts_all,(p['slug'],len(reader.translations),len(ts_all));assert len(reader.anchors)==(len(p['units'])if len(p['units'])>1 else 0),(p['slug'],len(reader.anchors),len(p['units']))
  assert all('e'+str(i)in reader.ids for i in range(1,len(p['units'])+1))
  for target,count in reader.buttons:assert reader.lists[target]==count
 rows.append(dict(page=p['slug'],chapters=len(p['units']),sentence_pairs=len(ts_all),notes=nc))
group_rows=[]
for g in groups:
 expected_ts=[];expected_notes=0
 for e in g['entries']:
  p=next(p for p in j['pages']if p['slug']==e['source_page_slug']);expected=[];intro=[]
  for u in p['units']:
   start=min(u['source_block_indices'])
   for h in e['inline_source_headings']:
    if h['source_block_index']<start and not any(c['o']==h['original'] for c in expected):expected.append(dict(o=h['original'],t=h['translation'],notes=[]))
   old=build.parse_poems([ROOT/'src/zhanguoce'/p['slug']/(u['id']+'.txt')])[0];expected.extend(old['chunks']);intro.extend(old['intro'])
  secs=build.parse_poems([ROOT/'src/zhanguoce'/g['slug']/(e['id']+'.txt')]);assert len(secs)==1 and secs[0]['title']==e['title'];assert secs[0]['chunks']==expected
  assert all(x in ' '.join(secs[0]['intro']) for x in intro)
  expected_ts.extend(t for c in expected for t in c['t'].split('¦'));expected_notes+=sum(len(c['notes'])for c in expected)
  oldhtml=(ROOT/'zhanguoce'/(p['slug']+'.html')).read_text();assert f'{g["slug"]}.html#e{int(e["id"])}'in oldhtml
 html=(ROOT/'zhanguoce'/(g['slug']+'.html')).read_text();reader=Reader();reader.feed(html);assert reader.translations==expected_ts;assert reader.anchors==['e'+str(i)for i in range(1,7)]
 for e in g['entries']:assert e['source']['url'].replace('&','&amp;')in html and e['source']['revision']in html
 assert sum(reader.lists.values())==expected_notes
 for target,count in reader.buttons:assert reader.lists[target]==count
 group_rows.append(dict(page=g['slug'],articles=6,sentence_pairs=len(expected_ts),notes=expected_notes))
home=(ROOT/'index.html').read_text();assert 'zhanguoce/index.html' in home and 'book-search' in home
index=(ROOT/'zhanguoce/index.html').read_text();assert 'href="xu.html"'in index and 'href="fu.html"'in index
assert all(f'href="{old}.html"'not in index for old in group_members)
report=dict(pages=rows,completed_units=sum(r['chapters'] for r in rows),body_chapters=sum(sum(u.get('kind')!='source_note_appendix'for u in p['units'])for p in j['pages']if p['slug']in j['completed_volumes']),source_note_appendices=sum(u.get('kind')=='source_note_appendix'for p in j['pages']for u in p['units']),prefaces=6,appendices=6,sentence_pairs=sum(r['sentence_pairs'] for r in rows),notes=sum(r['notes'] for r in rows),source_coverage=True,source_reconstruction=True,raw_snapshot_hashes=True,rendered_pairs=True,note_counts=True,whole_book_complete=len(j['completed_volumes'])==33 and all(u['status']=='complete'for p in j['pages']for u in p['units']),browser_visual_check=False)
assert report['completed_units']==j['completed_units'];assert report['sentence_pairs']==j['sentence_pairs'];assert report['notes']==j['notes']
report.update(reading_groups=group_rows,reading_entries=report['completed_units']-39+12,reading_sentence_pairs=report['sentence_pairs']+2,other_agents_pages_preserved=True)
preserved=json.loads((ROOT/'sources/zhanguoce/endmatter-progress.json').read_text())['preserved_other_page_fingerprints']
for p in j['pages']:
 if p['slug'] in preserved:assert hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==preserved[p['slug']]
assert report['body_chapters']==497 and report['reading_entries']==j['reading_entries'] and report['reading_sentence_pairs']==j['reading_sentence_pairs']
if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))

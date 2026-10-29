# coding: utf-8
import sys,json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT)]
from zhenglun_changyan_common import load,save,source_parts,digest
import build

def add(slug,number,title,intro,translation,notes):
 j=load();page=next(p for p in j['pages'] if p['slug']==slug);u=next(u for u in page['units'] if u['id']==f'{number:03}')
 assert u['status']=='pending'
 snap=json.loads(Path(page['source']['snapshot']).read_text());raw=snap['blocks'][u['source_block_index']]['text'];main,source_notes,format_breaks=source_parts(raw)
 assert digest(main)==u['main_sha256']
 assert len(build.split_sents(main))==len(translation.split('¦')),(number,len(build.split_sents(main)),len(translation.split('¦')))
 apparatus_lines=[f'底本夹注{k:02}（主文第{n["main_offset"]}字后）：'+n['text'] for k,n in enumerate(source_notes,1)]
 for n in apparatus_lines+notes:assert len(build.split_notes(n))==1,n
 out=Path('src/zhenglun-changyan')/slug/f'{number:03}.txt';out.parent.mkdir(parents=True,exist_ok=True);assert not out.exists()
 out.write_text('\n'.join(['# '+title,'题解：'+intro,'原：'+main+' || '+translation]+['注：'+n for n in apparatus_lines+notes])+'\n')
 u.update(status='complete',title=title,sentence_pairs=len(build.split_sents(main)),source_note_count=len(source_notes),editor_note_count=len(notes))
 page['annotation_status']='complete' if all(u['status']=='complete'for u in page['units']) else 'in_progress'
 body=next(p for p in j['pages']if p['slug']=='zhenglun');j['books'][0]['completed_units']=sum(u['status']=='complete'for u in body['units']);j['annotation_status']='in_progress';j['site_entry'].update(status='created_in_progress',search_status='included')
 pending=next(((p,u) for p in j['pages'] for u in p['units'] if u['status']!='complete'),None)
 if pending:
  pp,uu=pending;j['next']={'book':'昌言' if pp['slug'].startswith('changyan') else '政论','page_slug':pp['slug'],'source_block_index':uu['source_block_index'],'unit_id':uu['id'],'action':'按已有分区和夹注原位映射续注译，不重写已完成单元。'}
 else:j['next']=None;j['status']='complete';j['annotation_status']='complete'
 for book in j['books']:
  related=[p for p in j['pages'] if p['slug'].startswith('changyan' if book['title']=='昌言' else 'zhenglun')]
  book['annotation_status']='complete' if all(all(u['status']=='complete'for u in p['units']) for p in related) else 'in_progress'
 save(j);print(slug,number,len(build.split_sents(main)),len(source_notes),len(notes))

if __name__ == '__main__':
 import argparse
 ap=argparse.ArgumentParser(description='Write only new, explicitly authored annotations; never overwrite completed units.')
 ap.add_argument('draft',type=Path)
 args=ap.parse_args()
 for item in json.loads(args.draft.read_text()):
  add(item['slug'],item['number'],item['title'],item['intro'],item['translation'],item['notes'])

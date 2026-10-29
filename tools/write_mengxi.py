# coding: utf-8
"""Write explicitly authored new Mengxi units without overwriting existing edits."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import build
from zhenglun_changyan_common import source_parts,digest
PROGRESS=ROOT/'sources/mengxi/progress.json'
def add(slug,number,title,intro,translation,notes):
 j=json.loads(PROGRESS.read_text());page=next(p for p in j['pages']if p['slug']==slug);u=next(u for u in page['units']if u['id']==f'{number:03}')
 assert u['status']=='pending'
 snap=json.loads((ROOT/page['source']['snapshot']).read_text());raw=snap['blocks'][u['source_block_index']]['text'];main,apparatus,breaks=source_parts(raw)
 assert digest(main)==u['main_sha256']
 assert len(build.split_sents(main))==len(translation.split('¦')),(slug,number,len(build.split_sents(main)),len(translation.split('¦')))
 ns=[f'底本夹注{k:02}（主文第{n["main_offset"]}字后）：'+n['text']for k,n in enumerate(apparatus,1)]+notes
 assert all(len(build.split_notes(n))==1 for n in ns)
 p=ROOT/'src/mengxi'/slug/f'{number:03}.txt';p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists()
 p.write_text('\n'.join(['# '+title,'题解：'+intro,'原：'+main+' || '+translation]+['注：'+n for n in ns])+'\n')
 u.update(status='complete',title=title,sentence_pairs=len(translation.split('¦')),source_note_count=len(apparatus),editor_note_count=len(notes))
 page['annotation_status']='complete'if all(u['status']=='complete'for u in page['units'])else 'in_progress'
 pending=next(((p,u)for p in j['pages']for u in p['units']if u['status']!='complete'),None)
 j['next']=j['next_new_entry']=dict(page_slug=pending[0]['slug'],unit_id=pending[1]['id'],source_block_index=pending[1]['source_block_index'],action='先核快照与完整主文，按句自撰完整白话及独立释词，不重写完成稿。')if pending else None
 if not pending:j['status']='complete'
 PROGRESS.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');print(slug,number,u['sentence_pairs'])

# coding: utf-8
"""Author new units of the specified Shiliju edition, preserving apparatus."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import build
from zhenglun_changyan_common import source_parts,digest
PROGRESS=ROOT/'sources/zhanguoce/progress.json'
def add(slug,number,intro,translation,notes):
 j=json.loads(PROGRESS.read_text());p=next(p for p in j['pages']if p['slug']==slug);u=p['units'][number-1];assert u['status']=='pending'
 s=json.loads((ROOT/p['source']['snapshot']).read_text());raw='\n'.join(s['blocks'][i]['text']for i in u['source_block_indices']);m,a,b=source_parts(raw)
 assert digest(m)==u['main_sha256'];assert len(build.split_sents(m))==len(translation.split('¦')),(slug,number,len(build.split_sents(m)),len(translation.split('¦')))
 ns=[f'底本原注{k:03}（主文第{n["main_offset"]}字后）：'+n['text']for k,n in enumerate(a,1)]+notes
 assert all(len(build.split_notes(n))==1 for n in ns)
 target=ROOT/'src/zhanguoce'/slug/f'{number:03}.txt';target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists();target.write_text('\n'.join(['# '+u['title'],'题解：'+intro,'原：'+m+' || '+translation]+['注：'+n for n in ns])+'\n')
 u.update(status='complete',sentence_pairs=len(translation.split('¦')),source_note_count=len(a),editor_note_count=len(notes));p['annotation_status']='complete'if all(x['status']=='complete'for x in p['units'])else 'in_progress'
 pending=next(((p,u)for p in j['pages']for u in p['units']if u['status']!='complete'),None);j['next']=j['next_new_entry']={'page_slug':pending[0]['slug'],'unit_id':pending[1]['id']}if pending else {'action':'已载计划全部写入；须更新累计统计、核验及下一未载卷位置，不能据此标全书完成'}
 PROGRESS.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');print(slug,number,u['sentence_pairs'])

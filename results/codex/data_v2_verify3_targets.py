"""Targeted published-row supplements: terminals, short/off-centre accepted scrolls, and original cases."""
from data_v2_verify3_rules import ROOT, BASE, CACHE, af, rules
from data_v2_verify3_provenance import amex_replay
import ast, collections as C, io, json, math, random, textwrap, zipfile
import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont

rows=[json.loads(l) for l in (CACHE/'pre_metadata.jsonl').read_text().splitlines()]
z=zipfile.ZipFile(BASE/'sources/amex_instructions.zip');raw={}
for n in z.namelist():
    if n.endswith('.json'):
        d=json.loads(z.read(n));raw[str(d['episode_id'])]=d
choices=[]
for r in rows:
    if r['source'] not in ('amex','odyssey') or r['action']['action_type']!='scroll':continue
    if r['source']=='amex':
        s=next(s for s in raw[r['episode_id']]['steps'] if s['step_id']==r['step_idx'])
        p=[af.px_to_norm(*s[k],*s['device_dim']) for k in ['touch_coord','lift_coord']]
    else:
        file=BASE/'sources/odyssey_annotations'/f'{r["episode_id"].zfill(16)}.json'
        if not file.exists():continue
        d=json.loads(file.read_text());s=next(s for s in d['steps'] if int(s['step'])==r['step_idx'])
        p=ast.literal_eval(s['info']) if isinstance(s['info'],str) else s['info'];p=p[:2]
    vertical=r['action']['direction'] in ('up','down')
    deviation=abs((p[0][0]+p[1][0])/2-500) if vertical else abs((p[0][1]+p[1][1])/2-500)
    distance=abs(p[1][1]-p[0][1]) if vertical else abs(p[1][0]-p[0][0])
    choices.append(dict(r,raw_path=p,score=deviation+max(0,400-distance)))
selected=[]
for source in ['amex','odyssey']:
    pool=sorted([r for r in choices if r['source']==source],key=lambda r:-r['score'])[:8]
    for i,r in enumerate(pool):selected.append(dict(r,visual_id=f'scroll_{source}_{i+1:02d}'))
merge_ids = ['train/odyssey/4265287532604248/12','train/odyssey/4265287532604248/15',
 'train/odyssey/5391718871142315/23','train/odyssey/5994133452263654/31',
 'train/odyssey/6951686067814574/5','train/odyssey/4912446279173881/5',
 'train/odyssey/2809140271430652/20','train/odyssey/6214607096360440/13']
for r in rows:
    if r['id'] in merge_ids:selected.append(dict(r,visual_id=f'merge_{merge_ids.index(r["id"])+1:02d}'))
out=CACHE/'visual';out.mkdir(exist_ok=True)
want={(r['file'],r['row']):r for r in selected};pics={}
for f in sorted({r['file'] for r in selected}):
    pos=0
    for batch in pq.ParquetFile(CACHE/'v2'/f).iter_batches(batch_size=64,columns=['images']):
        for r in batch.to_pylist():
            if (f,pos) in want:
                m=want[(f,pos)];im=Image.open(io.BytesIO(r['images'][0]['bytes'])).convert('RGB');draw=ImageDraw.Draw(im)
                if m['action']['action_type'] in af.POINT_TYPES:
                    x,y=af.norm_to_px(m['action']['point_2d'],im.width,im.height);draw.ellipse((x-12,y-12,x+12,y+12),outline='red',width=3)
                if 'raw_path' in m:
                    p=[af.norm_to_px(pt,im.width,im.height) for pt in m['raw_path']]
                    draw.line(p,fill='red',width=4)
                    for x,y in p:draw.ellipse((x-5,y-5,x+5,y+5),fill='red')
                    dr=m['action']['direction'];w,h=im.size
                    pts={'up':[(w//2,h//2),(w//2,h-1)],'down':[(w//2,h//2),(w//2,0)],'left':[(w//2,h//2),(w-1,h//2)],'right':[(w//2,h//2),(0,h//2)]}[dr]
                    draw.line(pts,fill='#00cc00',width=4)
                im.save(out/(m['visual_id']+'.png'));pics[m['visual_id']]=im
            pos+=1
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',16)
for group in ['scroll_amex','scroll_odyssey','merge']:
    group_rows=[r for r in selected if r['visual_id'].startswith(group)]
    for page in range(math.ceil(len(group_rows)/4)):
        sheet=Image.new('RGB',(1536,1190),'white');draw=ImageDraw.Draw(sheet)
        for i,r in enumerate(group_rows[page*4:page*4+4]):
            x=i*384;im=pics[r['visual_id']].copy();im.thumbnail((376,850));sheet.paste(im,(x+(384-im.width)//2,30))
            draw.text((x+4,3),r['visual_id'],font=font,fill='black')
            text=r['id']+'\nGoal: '+r['goal']+'\nLabel: '+r['messages'][-1]['content']
            if 'raw_path' in r:text+='\nSource path (red): '+str(r['raw_path'])+'\nExecutor path: green'
            draw.multiline_text((x+4,890),'\n'.join(textwrap.fill(line,43) for line in text.splitlines()),font=font,fill='black',spacing=2)
        sheet.save(out/f'{group}_supplement_{page+1}.jpg',quality=95)
(CACHE/'target_samples.json').write_text(json.dumps(selected,indent=2,ensure_ascii=False))
print('Targeted rows:',len(selected))

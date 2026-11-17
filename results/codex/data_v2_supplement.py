"""Targeted review images, kept distinct from the random 40/source sample."""
from pathlib import Path
import io,json,random,sys,textwrap
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];CACHE=ROOT/'results/codex/data_v2_cache'
sys.path[:0]=[str(CACHE/'python'),str(ROOT/'train')]
import pyarrow.parquet as pq
import agent_format as af
rows=[json.loads(l) for l in (CACHE/'rows.jsonl').read_text().splitlines()];idx={r['id']:r for r in rows}
checks=json.loads((CACHE/'checks.json').read_text());chosen=[]
for j,pair in enumerate(checks['pixel_leakage']):
    for tag,ident in [('train',pair['train'][0]),('dev',pair['dev'])]:
        chosen.append(dict(idx[ident],visual_id=f'leak{j+1}_{tag}'))
chosen.append(dict(idx['train/amex/ba060ad1f8c04af1afad922de5f78906/9'],visual_id='amex_rotation'))
for source,typ,n in [('amex','input_text',8),('odyssey','status',8)]:
    pool=[r for r in rows if r['split']=='train' and r['source']==source and r['action']['action_type']==typ and (typ!='status' or r['action'].get('goal_status')=='complete')]
    for j,r in enumerate(random.Random(190).sample(pool,n)):chosen.append(dict(r,visual_id=f'extra_{source}_{j+1:02d}'))
want={(r['file'],r['row']):r for r in chosen};pics={};out=CACHE/'visual';out.mkdir(exist_ok=True)
for f in sorted({r['file'] for r in chosen}):
    k=0
    for batch in pq.ParquetFile(CACHE/'v2'/f).iter_batches(batch_size=64,columns=['images']):
        for r in batch.to_pylist():
            if (f,k) in want:
                m=want[(f,k)];im=Image.open(io.BytesIO(r['images'][0]['bytes'])).convert('RGB');d=ImageDraw.Draw(im)
                if m['action']['action_type'] in af.POINT_TYPES:
                    x,y=af.norm_to_px(m['action']['point_2d'],im.width,im.height);d.ellipse((x-13,y-13,x+13,y+13),outline='red',width=3);d.line((x-20,y,x+20,y),fill='red',width=2);d.line((x,y-20,x,y+20),fill='red',width=2)
                im.save(out/(m['visual_id']+'.png'));pics[m['visual_id']]=im
            k+=1
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',15);title=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',19)
for name,subset in [('leaks',chosen[:10]),('types',[r for r in chosen if r['visual_id'].startswith('extra_amex')]),('terminals',[r for r in chosen if r['visual_id'].startswith('extra_odyssey')])]:
    for page in range((len(subset)+7)//8):
        sheet=Image.new('RGB',(1536,2300),'#eeeeee');d=ImageDraw.Draw(sheet)
        for slot,r in enumerate(subset[page*8:(page+1)*8]):
            x=slot%4*384;y=slot//4*1150;im=pics[r['visual_id']].copy();im.thumbnail((374,835));sheet.paste(im,(x+(384-im.width)//2,y+30));d.text((x+6,y+4),r['visual_id'],font=title,fill='black')
            text='Goal: '+r['goal']+'\nIntent: '+r['messages'][-1]['reasoning_content']+'\nLabel: '+r['messages'][-1]['content']
            d.multiline_text((x+7,y+870),'\n'.join(textwrap.fill(t,47) for t in text.splitlines()),font=font,fill='black',spacing=2)
        sheet.save(out/f'{name}_sheet_{page+1}.jpg',quality=95)
(CACHE/'supplement_samples.json').write_text(json.dumps(chosen,indent=2,ensure_ascii=False))
print(len(chosen),'targeted review rows')

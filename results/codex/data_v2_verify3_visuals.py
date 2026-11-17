"""Deterministic random visual audit; exact-coordinate overlays, no generated pixels."""
from pathlib import Path
import io
import json
import random
import sys
import textwrap
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'results/codex/data_v2_cache'
CACHE=BASE/'verify3_836e401958'
sys.path[:0]=[str(BASE/'python'),str(ROOT/'train')]
import pyarrow.parquet as pq
import agent_format as af

def main():
    rows=[json.loads(s) for s in (CACHE/'pre_metadata.jsonl').read_text().splitlines()]
    selected=[]
    for j,source in enumerate(['odyssey','amex','screenqa']):
        pool=sorted([r for r in rows if r['source']==source and r['split']=='train'],key=lambda r:r['id'])
        sample=random.Random(20261131+j).sample(pool,32)
        for i,r in enumerate(sample):
            r['visual_id']=f'{source}_{i+1:02d}'
        selected+=sample
    (CACHE/'visual_samples.json').write_text(json.dumps(selected,indent=2,ensure_ascii=False))
    want={(r['file'],r['row']):r for r in selected}
    pics={}
    for f in sorted({r['file'] for r in selected}):
        pos=0
        for batch in pq.ParquetFile(CACHE/'v2'/f).iter_batches(batch_size=64,columns=['images']):
            for r in batch.to_pylist():
                if (f,pos) in want:
                    m=want[(f,pos)]
                    im=Image.open(io.BytesIO(r['images'][0]['bytes'])).convert('RGB')
                    if m['action']['action_type'] in af.POINT_TYPES:
                        x,y=af.norm_to_px(m['action']['point_2d'],im.width,im.height)
                        d=ImageDraw.Draw(im);d.ellipse((x-13,y-13,x+13,y+13),outline='red',width=3)
                        d.line((x-20,y,x+20,y),fill='red',width=2);d.line((x,y-20,x,y+20),fill='red',width=2)
                    pics[m['visual_id']]=im
                pos+=1
    out=CACHE/'visual';out.mkdir(exist_ok=True)
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',15)
    title=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',19)
    for source in ['odyssey','amex','screenqa']:
        samples=[r for r in selected if r['source']==source]
        for page in range(4):
            sheet=Image.new('RGB',(1536,2300),'#eeeeee');draw=ImageDraw.Draw(sheet)
            for slot,r in enumerate(samples[page*8:(page+1)*8]):
                x=(slot%4)*384;y=(slot//4)*1150
                draw.rectangle((x+1,y+1,x+382,y+1149),fill='white',outline='#777777')
                draw.text((x+6,y+4),r['visual_id']+' / '+r['action']['action_type'],font=title,fill='black')
                im=pics[r['visual_id']].copy();im.thumbnail((374,835))
                sheet.paste(im,(x+(384-im.width)//2,y+30))
                pics[r['visual_id']].save(out/(r['visual_id']+'.png'))
                text='Goal: '+r['goal']+'\nIntent: '+r['messages'][-1]['reasoning_content']+'\nLabel: '+r['messages'][-1]['content']
                wrapped='\n'.join(textwrap.fill(line,width=47) for line in text.splitlines())
                draw.multiline_text((x+7,y+870),wrapped,font=font,fill='black',spacing=2)
            sheet.save(out/f'{source}_sheet_{page+1}.jpg',quality=95)
    print('96 random training rows; 12 contact sheets; visual_samples.json',flush=True)

if __name__=='__main__': main()

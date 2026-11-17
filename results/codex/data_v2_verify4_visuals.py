"""Reviewable pinned images with source/executor paths and merge context."""
from data_v2_verify4_rules import *
import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont
import math, textwrap

selected=json.loads((CACHE/'target_samples.json').read_text())['rows']
out=CACHE/'visual';out.mkdir(exist_ok=True)
want=collections.defaultdict(list)
for r in selected:want[(r['file'],r['row'])].append(r)
pics={}
for file in sorted({r['file'] for r in selected}):
    pos=0
    for batch in pq.ParquetFile(CACHE/'v2'/file).iter_batches(batch_size=64,columns=['images']):
        for row in batch.to_pylist():
            if (file,pos) in want:
                for r in want[(file,pos)]:
                    im=Image.open(io.BytesIO(row['images'][0]['bytes'])).convert('RGB');draw=ImageDraw.Draw(im)
                    if r['action']['action_type'] in af.POINT_TYPES:
                        x,y=af.norm_to_px(r['action']['point_2d'],im.width,im.height)
                        draw.ellipse((x-12,y-12,x+12,y+12),outline='red',width=3)
                    if 'raw_path' in r:
                        dr=r['action']['direction'];w,h=im.size
                        pts={'up':[(w//2,h//2),(w//2,h-1)],'down':[(w//2,h//2),(w//2,0)],
                             'left':[(w//2,h//2),(w-1,h//2)],'right':[(w//2,h//2),(0,h//2)]}[dr]
                        draw.line(pts,fill='#00b500',width=4)
                        p=[af.norm_to_px(pt,w,h) for pt in r['raw_path']]
                        draw.line(p,fill='red',width=4)
                        for x,y in p:draw.ellipse((x-5,y-5,x+5,y+5),fill='red')
                    im.save(out/(r['visual_id']+'.png'));pics[r['visual_id']]=im
            pos+=1
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
for group in ['merge','scroll_odyssey','scroll_amex']:
    rs=[r for r in selected if r['visual_id'].startswith(group)]
    for page in range(math.ceil(len(rs)/4)):
        sheet=Image.new('RGB',(1600,1400),'white');draw=ImageDraw.Draw(sheet)
        for i,r in enumerate(rs[page*4:page*4+4]):
            x=i*400;im=pics[r['visual_id']].copy();im.thumbnail((392,880))
            sheet.paste(im,(x+(400-im.width)//2,30))
            draw.text((x+4,4),r['visual_id'],font=font,fill='black')
            caption=r['id']+'\nGoal: '+r['goal'][:230]+'\nTarget: '+r['messages'][-1]['content']
            if 'raw_path' in r:
                caption+='\nSource RED: '+str(r['raw_path'])+'\nExecutor GREEN\nInstruction: '+str(r['raw'].get('low_level_instruction','(AMEX has none)'))
            else:
                m=r['merged_before'][-1]
                caption+='\nMerged raw step '+str(m['step'])+': '+m['raw']['action']
                if m['action']:caption+=' '+str(m['action'])
                caption+='\nSubmit wording: '+str(m['raw'].get('low_level_instruction','(AMEX has none)'))
                caption+='\nRetained history source steps: '+str(r['retained_source_steps'])
            text='\n'.join(textwrap.fill(line,44) for line in caption.splitlines())
            draw.multiline_text((x+4,930),text,font=font,fill='black',spacing=3)
        sheet.save(out/f'{group}_sheet_{page+1}.jpg',quality=95)
print('Saved',len(pics),'rows and 11 contact sheets',flush=True)

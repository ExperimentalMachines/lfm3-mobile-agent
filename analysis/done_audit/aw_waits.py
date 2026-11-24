"""Wait behaviour of AndroidWorld runs (round 9): share of `wait` steps, how many left the next screen unchanged
(train/screen_change.py on the run's 360x800 thumbnails), wait streak lengths and the action before each wait.
Diagnosis only: nothing from AndroidWorld runs is trained on. Usage: python aw_waits.py <results/androidworld run name> ...
"""
import collections
import glob
import gzip
import os
import pickle
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'train'))
import screen_change as sc
for name in sys.argv[1:]:
    runs=sorted(glob.glob(f'results/androidworld/{name}/run_*'))
    R=runs[-1]
    files=sorted(glob.glob(R+'/*.pkl.gz'))
    steps=waits=0; wait_noop=0; wait_chg=0; runs3=0; eps_with_wait=0; succ=0
    wait_after=collections.Counter(); streaks=collections.Counter(); fc=0
    ex=[]
    for f in files:
        d=pickle.load(gzip.open(f))[0]; e=d["episode_data"]
        if not isinstance(e,dict): continue
        succ+=d['is_successful']>0
        acts=e.get('parsed_action') or []
        thumbs=e.get('screenshot_thumb_jpg') or []
        types=[]
        for a in acts:
            t=None
            if isinstance(a,dict): t=a.get('action_type')
            elif isinstance(a,str):
                m=re.search(r'"action_type"\s*:\s*"(\w+)"',a); t=m.group(1) if m else None
            types.append(t)
        steps+=len(types)
        had=False; streak=0
        for i,t in enumerate(types):
            if t=='wait':
                waits+=1; had=True; streak+=1
                prev=types[i-1] if i else None
                wait_after[prev]+=1
                if i+1<len(thumbs) and thumbs[i] is not None and thumbs[i+1] is not None:
                    ch=sc.changed(sc.prep(thumbs[i]),sc.prep(thumbs[i+1]))
                    wait_noop+= (not ch); wait_chg+=ch
            else:
                if streak: streaks[min(streak,5)]+=1
                streak=0
        if streak: streaks[min(streak,5)]+=1
        eps_with_wait+=had
    print(name, 'episodes',len(files),'success',succ,'steps',steps,'waits',waits,f'({100*waits/max(steps,1):.1f}%)',
          'eps_with_wait',eps_with_wait,'wait->next screen unchanged',wait_noop,'changed',wait_chg,
          'streak lengths',dict(sorted(streaks.items())),'prev action before wait',dict(wait_after.most_common(6)))

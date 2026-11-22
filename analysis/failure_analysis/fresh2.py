import json, collections
R = json.load(open('aw_features.json'))
def st(eps):
    c = collections.Counter()
    for e in eps:
        if e['label'] == 'exception' or not e['intents']: continue
        d = e['diffs']; it = e['intents']; ty = e['types']
        for i in range(len(d)):
            if ty[i] != 'click': continue
            if i > 0 and it[i] == it[i-1]: continue   # only the first click under a new intent
            g = 'succ' if e['success'] else 'fail'
            c[(g, d[i] < 1.0)] += 1; c[('all', d[i] < 1.0)] += 1
    return {g: f"{c[(g,True)]}/{c[(g,True)]+c[(g,False)]}={c[(g,True)]/max(1,c[(g,True)]+c[(g,False)]):.2f}" for g in ['all','succ','fail']}
for k in ['lfm3vl2b_ft','lfm3vl2b_v3','lfm3vl2b_v4','lfm3vl2b_v4_guards','lfm3vl2b_v41','lfm3vl2b_v42']:
    print(k, st(R['dev'][k]['episodes'].values()))
for arm in ['v4','v1']:
    print('sealed', arm, st([e for s in [7,1234,2026] for e in R['sealed'][f'{arm}_s{s}']['episodes'].values()]))

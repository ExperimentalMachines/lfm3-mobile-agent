"""Reuse the prior independent every-row checks on exactly this audit's five files."""
from data_v2_verify4_rules import ROOT, CACHE, PIN, ns, write_json
import collections, json

prior = (ROOT/'results/codex/data_v2_verify3_checks.py').read_text()
assert prior.count("CACHE = BASE / 'verify3_836e401958'") == 1
assert prior.count('[2,5,9,13]') == 1
prior = prior.replace("CACHE = BASE / 'verify3_836e401958'", "CACHE = BASE / 'verify4_42f7f76364'").replace('[2,5,9,13]', '[2,13]')
env = {'__file__': str(ROOT/'results/codex/data_v2_verify3_checks.py'), '__name__':'verify4_adapter'}
exec(compile(prior, 'verify4-independent-checks', 'exec'), env)
env['main']()
rows = [json.loads(s) for s in (CACHE/'metadata.jsonl').read_text().splitlines()]
class Rows:
    def __init__(self, rows): self.rows = rows
    def __getitem__(self, key): return [r[key] for r in self.rows]
    def select_columns(self, keys): return [{k:r[k] for k in keys} for r in self.rows]
splits = {s:Rows([r for r in rows if r['split']==s]) for s in {r['split'] for r in rows}}
checks = ns['verify'](splits['train'], {s:v for s,v in splits.items() if s!='train'})
maxima = {}
for s, v in splits.items():
    for src in {r['source'] for r in v.rows}:
        c = collections.Counter(r['episode_id'] for r in v.rows if r['source']==src)
        maxima[s+'/'+src] = max(c.values())
        cap = 1 if s=='dev_odyssey' else 4 if s=='dev_amex' else 2 if src=='screenqa' else 3
        if src!='androidcontrol': assert max(c.values())<=cap, (s,src,c)
write_json('sample_builder_assertions.json', {'revision':PIN, 'actual_verify_function_passed':True,
           'counters':checks,'observed_max_rows_per_episode':maxima})

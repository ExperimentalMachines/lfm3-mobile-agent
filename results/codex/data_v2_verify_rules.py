"""Load only pure builder rules and preserve separate re-verification evidence."""
from pathlib import Path
import ast, collections, hashlib, json, random, re, sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/codex/data_v2_cache'
CACHE = BASE / 'verify_d33cb3c217'
sys.path[:0] = [str(ROOT / 'train'), str(BASE / 'python')]
import agent_format as af

source = (ROOT / 'data/build_v2_mix.py').read_text()
tree = ast.parse(source)
constants = {'AW_APP_RE','ODY_EXTRA_RE','MIN_SWIPE','KEY_TEXT','INFO_GOAL_RE','PENDING_RE'}
functions = {'is_aw','h01','swipe_dir','bad_text','near_miss','sample_rows'}
nodes = [n for n in tree.body if
         isinstance(n, ast.FunctionDef) and n.name in functions or
         isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in n.targets)]
rules = dict(re=re, Counter=collections.Counter, hashlib=hashlib)
exec(compile(ast.Module(body=nodes, type_ignores=[]), 'builder-pure-rules', 'exec'), rules)

if __name__ == '__main__':
    probe = (ROOT / 'results/codex/data_v2_executor_probe.py').read_text()
    probe = probe.replace("CACHE=ROOT/'results/codex/data_v2_cache'", "CACHE=ROOT/'results/codex/data_v2_cache/verify_d33cb3c217'")
    # Preserve the original executor probe and run its real function again.
    ns = {'__file__': str(ROOT / 'results/codex/data_v2_executor_probe.py')}
    exec(compile(probe, 'rerun-executor-probe', 'exec'), ns)
    ns['calls'].clear()
    ns['ns']['execute_adb_action'](ns['action']('input_text', text='Art'), [], (1440,3040), None)
    out = json.loads((CACHE / 'executor_probe.json').read_text())
    out['merged_input_text_calls'] = list(ns['calls'])
    normalized = af.px_to_norm(946,725,1440,3040) + af.px_to_norm(967,1547,1440,3040)
    out['dropdown_normalized'] = normalized
    out['dropdown_new_rule'] = rules['swipe_dir'](*normalized)
    out['band_is_not_center_region_proof'] = {'source_path':[360,600,360,400], 'accepted':rules['swipe_dir'](360,600,360,400), 'executor_x':500}
    out['key_text_fixtures'] = {x:rules['bad_text'](x) for x in ['esc','\n',' Enter ','hello\nworld','Space']}
    out['typo_fixtures'] = [{'text':t,'goal':g,'reject':rules['near_miss'](t,g)} for t,g in [
        ('morning mediation','Create a reminder called Morning Meditation'),
        ('mark.tylor@gmail.com','Email mark.taylor@gmail.com'),
        ('Art','Search for Art'), ('1923529264','Subscribe to the YouTube channel 1923529264')]]
    fixture = [{'episode_id':'same','action':{'action_type':t}} for t in ['keyboard_enter']*4+['input_text']*4+['click']*4]
    picked = rules['sample_rows'](fixture,10,random.Random(0),per_episode=3,quotas=[(lambda r:r['action']['action_type']=='keyboard_enter',5),(lambda r:r['action']['action_type']=='input_text',5)])
    out['sampler_fixture'] = {'rows':len(picked),'max_per_episode':max(collections.Counter(r['episode_id'] for r in picked).values()),'unique':len({id(r) for r in picked})}
    out['builder_sha256'] = hashlib.sha256(source.encode()).hexdigest()
    (CACHE / 'rule_probes.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

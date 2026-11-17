"""Exercise the actual current Odyssey/AMEX source loops, with image I/O stubbed."""
from data_v2_verify4_rules import *
from types import SimpleNamespace
import tempfile

REAL_SAMPLER = ns['sample_rows']

def run_loop(source_name, documents, capture_all=True):
    saved, candidates, stats, events = {}, [], {}, []
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == source_name)
    step_loop = next(n for n in ast.walk(fn) if isinstance(n, ast.For) and
                     isinstance(n.target, ast.Name) and n.target.id == 's')
    sites = {n.lineno: type(n).__name__ for n in ast.walk(step_loop) if isinstance(n, (ast.Break, ast.Continue))}
    lines = source.splitlines()
    def trace(frame, event, arg):
        if frame.f_code.co_filename != str(BUILDER) or frame.f_code.co_name != source_name: return None
        if event == 'line' and frame.f_lineno in sites:
            loc = frame.f_locals; s = loc['s']
            events.append({'episode_id': str(loc['eid']), 'step': s.get('step', s.get('step_id')),
                           'branch': sites[frame.f_lineno], 'line': frame.f_lineno,
                           'context': lines[frame.f_lineno-3:frame.f_lineno],
                           'action': loc.get('act'), 'kind': loc.get('kind'), 'raw': s})
        return trace
    def sample(rows, n, rng, **kw):
        candidates.extend(rows)
        return REAL_SAMPLER(rows, n, rng, **kw)
    with tempfile.TemporaryDirectory(dir=CACHE) as td:
        root = Path(td)
        ns['args'] = SimpleNamespace(root=td, out=td, seed=0)
        ns['sample_rows'] = sample
        ns['save_stats'] = lambda name, st: stats.update({name: dict(st)})
        ns['materialize'] = lambda rows, name, st: saved.update({name: rows})
        if source_name == 'odyssey':
            (root/'odyssey/splits').mkdir(parents=True)
            (root/'odyssey/screenshots').mkdir()
            ann = root/'odyssey_git/annotations'; ann.mkdir(parents=True)
            split = json.loads((BASE/'sources/odyssey_split.json').read_text())
            train_ids = {str(int(str(e).removesuffix('.json'))) for e in split['train']}
            test_ids = {str(int(str(e).removesuffix('.json'))) for e in split['test']}
            # Fixture IDs are intentionally assigned explicitly; real IDs retain official splits.
            tr, dev = [], []
            for d in documents:
                e = str(d['episode_id'])
                (dev if e == '2' or e.lstrip('0') in test_ids else tr).append(e)
                assert e in ('1', '2') or e.lstrip('0') in train_ids | test_ids
                (ann/(e+'.json')).write_text(json.dumps(d))
            (root/'odyssey/splits/random_split.json').write_text(json.dumps({'train': tr, 'test': dev}))
            zpath = root/'odyssey/screenshots/joined.zip'
            names = {os.path.basename(s['screenshot']) for d in documents for s in d['steps']}
        else:
            ann = root/'amex/anno/instruction_anno'; ann.mkdir(parents=True)
            (root/'amex/AMEX').mkdir()
            for d in documents: (ann/(str(d['episode_id'])+'.json')).write_text(json.dumps(d))
            zpath = root/'amex/AMEX/joined.zip'
            names = {os.path.basename(s['image_path']) for d in documents for s in d['steps']}
        with zipfile.ZipFile(zpath, 'w') as z:
            for name in sorted(names): z.writestr(name, b'fixture: only source-loop filename membership is tested')
        old_trace = sys.gettrace()
        try:
            sys.settrace(trace)
            ns[source_name]()
        finally:
            sys.settrace(old_trace)
            ns['sample_rows'] = REAL_SAMPLER
    return candidates, events, stats, saved

def od_documents(steps):
    return [dict(episode_id=e, device_info={'device_name':'Pixel 7'},
                 task_info={'instruction':'Search for Art', 'app':['Chrome']},
                 steps=[dict(step=i, action=t, info=info, low_level_instruction=ins,
                             screenshot=f'{e}_{i}.png') for i,(t,info,ins) in enumerate(steps)]) for e in ['1','2']]

def am_documents(steps):
    return [dict(episode_id='fixture',instruction='Search for Art',steps=[
        dict(step_id=i+1,action=t,touch_coord=p or [0,0],lift_coord=lift or [0,0],
             device_dim=[1000,2000],type_text='Art',image_path=f'{i}.png')
        for i,(t,p,lift) in enumerate(steps)])]

def fixtures():
    typ = ('TEXT','Art','Type Art into the search field')
    result = ('CLICK',[[500,300]],'Tap a result')
    submit = ('CLICK',[[920,930]],'Tap the Search key on the keyboard')
    cases = {
      'odyssey_hide_keyboard': ('odyssey',od_documents([typ,('CLICK',[[500,950]],'Tap to hide the keyboard'),result]),[0]),
      'odyssey_toolbar_above_keyboard': ('odyssey',od_documents([typ,('CLICK',[[686,499]],'Tap the icon in the toolbar above the keyboard'),result]),[0]),
      'odyssey_keyboard_suggestion': ('odyssey',od_documents([typ,('CLICK',[[249,453]],'Tap the suggestion above the keyboard'),result]),[0]),
      'odyssey_bottom_right_search': ('odyssey',od_documents([typ,submit,result]),[0,2]),
      'odyssey_bottom_right_enter': ('odyssey',od_documents([typ,('CLICK',[[920,930]],'Press Enter on the keyboard'),result]),[0,2]),
      'odyssey_negative_wording_overrides_corner': ('odyssey',od_documents([typ,('CLICK',[[920,930]],'Dismiss the keyboard'),result]),[0]),
      'odyssey_second_submit_cuts': ('odyssey',od_documents([typ,submit,submit,result]),[0]),
      'odyssey_ordinary_app_tap_kept': ('odyssey',od_documents([typ,result]),[0,1]),
      'odyssey_control_drag_words': ('odyssey',od_documents([result,('SCROLL',[[500,700],[500,300]],'Swipe to adjust the slider'),result]),[0]),
      'odyssey_selection_after_long_press': ('odyssey',od_documents([('LONG_PRESS',[[500,700]],'Long press text'),('SCROLL',[[500,700],[500,300]],'Swipe up'),result]),[0]),
      'odyssey_page_scroll_kept': ('odyssey',od_documents([result,('SCROLL',[[500,700],[500,300]],'Scroll down the page'),result]),[0,1,2]),
      'amex_soft_search': ('amex',am_documents([('TYPE',None,None),('TAP',[920,1860],None),('TAP',[500,600],None)]),[1,3]),
      'amex_explicit_enter': ('amex',am_documents([('TYPE',None,None),('PRESS_ENTER',None,None),('TAP',[500,600],None)]),[1,3]),
      'amex_second_submit_cuts': ('amex',am_documents([('TYPE',None,None),('TAP',[920,1860],None),('TAP',[920,1860],None),('TAP',[500,600],None)]),[1]),
      'amex_short_drag_cuts': ('amex',am_documents([('TAP',[500,600],None),('SWIPE',[507,918],[389,936]),('TAP',[500,600],None)]),[1]),
      'amex_diagonal_drag_cuts': ('amex',am_documents([('TAP',[500,600],None),('SWIPE',[291,1286],[580,1492]),('TAP',[500,600],None)]),[1]),
      'amex_page_scroll_kept': ('amex',am_documents([('TAP',[500,600],None),('SWIPE',[500,1400],[500,600]),('TAP',[500,600],None)]),[1,2,3]),
    }
    out = {}
    for name,(src,docs,expected) in cases.items():
        rows,events,stats,_ = run_loop(src,docs)
        rows = [r for r in rows if r['episode_id'] in ('1','fixture')]
        got = sorted(r['step_idx'] for r in rows)
        assert got == expected, (name,got,expected)
        if 'bottom_right' in name or name in ('amex_soft_search','amex_explicit_enter'):
            final = max(rows,key=lambda r:r['step_idx'])
            assert len(final['history']) == 1 and json.loads(final['history'][0][1]) == {'action_type':'input_text','text':'Art'}
        out[name] = {'pass': True,'retained_steps':got,'rows':rows,'events':events,'stats':stats}
    raw_sample = [{'episode_id':'same','action':{'action_type':t}} for t in ['keyboard_enter']*4+['input_text']*4+['click']*4]
    picked = REAL_SAMPLER(raw_sample,10,random.Random(0),per_episode=3,quotas=[
        (lambda r:r['action']['action_type']=='keyboard_enter',5),(lambda r:r['action']['action_type']=='input_text',5)])
    assert len(picked) == len({id(x) for x in picked}) == 3
    write_json('actual_loop_fixtures.json', {'builder_sha256':hashlib.sha256(source.encode()).hexdigest(),
               'fixtures':out,'quota_cap_fixture':{'selected':len(picked),'unique':len({id(x) for x in picked})}})
    print('Actual-loop fixtures passed:',len(out),'plus cap fixture',flush=True)

if __name__ == '__main__': fixtures()

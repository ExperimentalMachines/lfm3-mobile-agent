"""Run the real executor function with recorded ADB calls; no device interaction."""
from pathlib import Path
from types import SimpleNamespace
import ast,hashlib,json,logging
ROOT=Path(__file__).resolve().parents[2];CACHE=ROOT/'results/codex/data_v2_cache'
source=(ROOT/'android_world/android_world/env/actuation.py').read_text()
tree=ast.parse(source);fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='execute_adb_action')
for arg in fn.args.args: arg.annotation=None
fn.returns=None
calls=[]
adb=SimpleNamespace(
    type_text=lambda text,env,**kwargs:calls.append(['type_text',text]),
    press_enter_button=lambda env:calls.append(['keyboard_enter']),
    generate_swipe_command=lambda *args:['swipe',*args],
    issue_generic_request=lambda cmd,env:calls.append(cmd),
)
ns={'adb_utils':adb,'logging':logging}
exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-executor-extracted','exec'),ns)
def action(t,**kw): return SimpleNamespace(action_type=t,index=None,x=None,y=None,clear_text=False,**kw)
ns['execute_adb_action'](action('input_text',text='Art'),[],(1440,3040),None)
ns['execute_adb_action'](action('keyboard_enter'),[],(1440,3040),None)
out={'executor_sha256':hashlib.sha256(source.encode()).hexdigest(),'type_then_enter_calls':list(calls)}
calls.clear()
ns['execute_adb_action'](action('scroll',direction='up'),[],(1440,3040),None)
out['time_dropdown_scroll_calls']=list(calls)
out['time_dropdown_source_finger_path']=[[946,725],[967,1547]]
(CACHE/'executor_probe.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))

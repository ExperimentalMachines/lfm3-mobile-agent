"""Compare real executor functions with every device operation replaced by a recorder."""
import __future__
import ast
import base64
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path('/Users/alpha/lfm3-android')
OUT = ROOT/'results/codex/session_1118_audit'


def extract(path, name, ns):
    tree = ast.parse((ROOT/path).read_text())
    f = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    f.decorator_list = []
    exec(compile(ast.Module(body=[f], type_ignores=[]), path, 'exec',
                 flags=__future__.annotations.compiler_flag), ns)
    return ns[name]


aw_events, mw_events = [], []
adb_fake = SimpleNamespace(
    generate_swipe_command=lambda *a: {'swipe': list(a)},
    issue_generic_request=lambda command, env: aw_events.append(command),
    type_text=lambda text, env, **kw: aw_events.append({'text': text}),
    press_enter_button=lambda env: aw_events.append({'key': 'Enter'}))
aw = extract('android_world/android_world/env/actuation.py', 'execute_adb_action', {'adb_utils': adb_fake})


class Response:
    def __init__(self, command): self.output = command


def record_command(command):
    mw_events.append(command)
    return Response(command)


ns = {'execute_adb': record_command, 'base64': base64}
swipe = extract('tools/MobileWorld/src/mobile_world/runtime/controller.py', 'swipe', ns)
text = extract('tools/MobileWorld/src/mobile_world/runtime/controller.py', 'text', ns)
ctr = SimpleNamespace(width=1080, height=2400, device='FAKE_DEVICE')
ctr.swipe = lambda x,y,direction: swipe(ctr,x,y,direction)
ctr.text = lambda value: text(ctr,value)
logger = SimpleNamespace(info=lambda *a: None, error=lambda *a: None, warning=lambda *a: None)
ns = dict(logger=logger, ensure_controller=lambda *a: ctr, AdbResponse=Response)
for k in ('CLICK','SWIPE','INPUT_TEXT','NAVIGATE_BACK','NAVIGATE_HOME','KEYBOARD_ENTER',
          'LONG_PRESS','DOUBLE_TAP','DRAG','SCROLL','OPEN_APP','WAIT','ANSWER','STATUS','ASK_USER','UNKNOWN'):
    ns[k] = k.lower()
mw = extract('tools/MobileWorld/src/mobile_world/core/server.py', 'step', ns)
out = {}
for direction in ('up','down','left','right'):
    aw_events.clear();mw_events.clear()
    a = SimpleNamespace(action_type='scroll',direction=direction,index=None,x=None,y=None)
    aw(a, [], (1080,2400), None)
    mw(SimpleNamespace(device='FAKE_DEVICE', action=a))
    out[direction] = {'androidworld': list(aw_events), 'mobileworld': list(mw_events)}
aw_events.clear();mw_events.clear()
a = SimpleNamespace(action_type='input_text',text='example query',index=None,x=None,y=None,clear_text=None)
aw(a, [], (1080,2400), None)
mw(SimpleNamespace(device='FAKE_DEVICE',action=a))
out['input_text'] = {'androidworld': list(aw_events), 'mobileworld': list(mw_events)}
out['real_processes_or_connections'] = 0
(OUT/'executor_checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))

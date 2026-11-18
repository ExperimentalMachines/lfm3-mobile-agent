"""Exercise extracted real functions with all external operations replaced by recorders."""
import __future__
import ast
import base64
import copy
import json
import io
import types
from types import SimpleNamespace as NS
from audit_common import ROOT, txt, save, manifest

def extract(path, name, ns):
    node=next(n for n in ast.walk(ast.parse(txt(path))) if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
    node.decorator_list=[]
    exec(compile(ast.Module(body=[node],type_ignores=[]),path,'exec',flags=__future__.annotations.compiler_flag),ns)
    return ns[name]

logger=NS(**{k:lambda *a,**kw:None for k in ['debug','info','error','warning','exception']})
clock=NS(sleep=lambda *a:None,time=lambda:0)
class Action(NS):
    def __getattr__(self,name): return None
    def model_dump(self,**kw): return dict(vars(self))
class Response:
    def __init__(self,command): self.output=command;self.success=True
class HTTPError(Exception):
    def __init__(self,status_code,detail): self.status_code=status_code;self.detail=detail;super().__init__(detail)

af=types.ModuleType('offline_agent_format')
exec(compile(txt('train/agent_format.py'),'train/agent_format.py','exec'),af.__dict__)
base_ns={'logger':logger,'time':clock}
Base=extract('tools/MobileWorld/src/mobile_world/agents/base.py','BaseAgent',
    dict(base_ns,ABC=object,abstractmethod=lambda f:f))
ag_ns=dict(BaseAgent=Base,JSONAction=Action,af=af,logger=logger,os=__import__('os'),MW_APPS=[
    'Calendar','Camera','Chrome','Clock','Contacts','Files','Gallery','Mail','Maps','Mastodon','Mattermost','Settings','SMS','Taodian'])
Agent=extract('eval/mobileworld/lfm3_mw_agent.py','LFM3MobileWorldAgent',ag_ns)
# No real screenshots or model call is needed. Only mapping uses this object.
af.resize_screenshot=lambda image,*args:image
shot=NS(size=(1080,2400))
query_events=[]
def agent(actions):
    obj=Agent();obj.initialize('offline synthetic goal');seq=iter(actions)
    def query(goal,img):
        query_events.append(dict(goal=goal,history=copy.deepcopy(obj.history)))
        return dict(content=json.dumps(next(seq)),reasoning='intent',latency_s=0)
    obj._query=query
    return obj

aw_events,mw_events=[],[]
aw_api=NS(issue_generic_request=lambda command,env,*a:aw_events.append(command),
          type_text=lambda text,env,**kw:aw_events.append({'text':text}))
aw_api.generate_swipe_command=extract('android_world/android_world/env/adb_utils.py','generate_swipe_command',{})
aw_api.long_press=extract('android_world/android_world/env/adb_utils.py','long_press',
    dict(logging=logger,issue_generic_request=aw_api.issue_generic_request,_DEFAULT_TIMEOUT_SECS=10))
for name,key in [('press_enter_button','KEYCODE_ENTER'),('press_home_button','KEYCODE_HOME'),('press_back_button','KEYCODE_BACK')]:
    setattr(aw_api,name,lambda env,key=key:aw_events.append({'key':key}))
aw=extract('android_world/android_world/env/actuation.py','execute_adb_action',dict(adb_utils=aw_api,copy=copy,logging=logger,time=clock))
ctr=NS(device='OFFLINE_RECORDING_ONLY',width=1080,height=2400)
controller_ns=dict(execute_adb=lambda command:(mw_events.append(command) or Response(command)),base64=base64,logger=logger,time=clock)
tree=ast.parse(txt('tools/MobileWorld/src/mobile_world/runtime/utils/models.py'))
apps=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='APP_DICT' for t in n.targets)))
controller_ns['APP_LOWER_DICT']={k.lower():v for k,v in apps.items()}
for name in ['drag','text','enter','long_press','back','home','tap','answer','launch_app']:
    fn=extract('tools/MobileWorld/src/mobile_world/runtime/controller.py',name,controller_ns)
    setattr(ctr,name,types.MethodType(fn,ctr))
ns=dict(logger=logger,ensure_controller=lambda *_:ctr,AdbResponse=Response,HTTPException=HTTPError,time=clock)
for name in ['CLICK','SWIPE','INPUT_TEXT','NAVIGATE_BACK','NAVIGATE_HOME','KEYBOARD_ENTER','LONG_PRESS','DOUBLE_TAP','DRAG','SCROLL','OPEN_APP','WAIT','ANSWER','STATUS','ASK_USER','UNKNOWN']:ns[name]=name.lower()
step=extract('tools/MobileWorld/src/mobile_world/core/server.py','step',ns)
out={'scroll':[]}
for size in [(1080,2400),(1081,2401),(2400,1080)]:
    shot.size=size
    for d in ['up','down','left','right']:
        aw_events.clear();mw_events.clear()
        raw=dict(action_type='scroll',direction=d)
        obj=agent([raw]);_,mapped=obj.predict({'screenshot':shot})
        aw(Action(**raw),[],size,None)
        step(NS(device=ctr.device,action=mapped))
        assert aw_events[0][3:7]==mw_events[0].split()[6:10]
        assert aw_events[0][-1]=='' and mw_events[0].endswith(' 400')
        out['scroll'].append(dict(size=size,direction=d,androidworld=aw_events.copy(),mobileworld=mw_events.copy()))
shot.size=(1080,2400)

out['deferred_enter']={}
for ending in [dict(action_type='answer',text='42'),dict(action_type='status',goal_status='complete')]:
    query_events.clear();mw_events.clear()
    obj=agent([dict(action_type='input_text',text='hello'),ending])
    _,a=obj.predict({'screenshot':shot});step(NS(device=ctr.device,action=a))
    hist=copy.deepcopy(obj.history)
    _,b=obj.predict({}) # Pending Enter does not require or inspect the screenshot.
    step(NS(device=ctr.device,action=b))
    assert len(query_events)==1 and obj.history==hist and not obj._pending_enter
    _,c=obj.predict({'screenshot':shot})
    if c.action_type=='answer':step(NS(device=ctr.device,action=c));assert ctr.interaction_cache=='42'
    assert len(query_events)==2 and len(obj.history)==2
    out['deferred_enter'][ending['action_type']]=dict(actions=[vars(a),vars(b),vars(c)],query_count=2,
        history_unchanged_during_enter=True,history_seen_by_next_query=query_events[-1]['history'],commands=mw_events.copy())

obj=agent([dict(action_type='input_text',text='')]);_,empty=obj.predict({'screenshot':shot})
assert not obj._pending_enter
aw_events.clear();aw(empty,[],shot.size,None);assert not aw_events
try:
    step(NS(device=ctr.device,action=empty))
    raise AssertionError('Expected the observed real empty-text bug')
except HTTPError as e:
    assert e.status_code==500 and 'ret' in e.detail
    out['empty_text']=dict(mapped=vars(empty),pending_enter=obj._pending_enter,
                          androidworld_events=aw_events.copy(),mobileworld_status=e.status_code,error=e.detail)
for reset in ['reset','initialize_hook','initialize','done']:
    obj=agent([dict(action_type='input_text',text='hello')]);obj.predict({'screenshot':shot})
    assert obj._pending_enter and obj.history
    getattr(obj,reset)(*(['new goal'] if reset in ['initialize','initialize_hook'] else []))
    assert not obj._pending_enter and not obj.history
out['reset_methods_clear_pending_and_history']=['reset','initialize_hook','initialize','done']

out['other_actions']={}
for raw in [dict(action_type='long_press',point_2d=[500,500]),dict(action_type='navigate_back'),dict(action_type='navigate_home'),dict(action_type='keyboard_enter')]:
    aw_events.clear();mw_events.clear()
    obj=agent([raw]);_,mapped=obj.predict({'screenshot':shot})
    aw(mapped,[],shot.size,None);step(NS(device=ctr.device,action=mapped))
    out['other_actions'][raw['action_type']]=dict(androidworld=aw_events.copy(),mobileworld=mw_events.copy())
assert out['other_actions']['long_press']['androidworld'][0][-1]=='1000'
assert out['other_actions']['long_press']['mobileworld'][0].endswith(' 1000')
assert all(a.lower() in controller_ns['APP_LOWER_DICT'] for a in ag_ns['MW_APPS'])
out['all_advertised_apps_resolve']=True

# Real runner, fake environment: quantify budget usage and the terminal-boundary loss of Enter.
runner=extract('tools/MobileWorld/src/mobile_world/core/runner.py','_execute_single_task',
    dict(logger=logger,ENV_FAIL='env_fail',FINISHED='finished',UNKNOWN='unknown',ANSWER='answer'))
traj=NS(log_traj=lambda *a:None,log_score=lambda **kw:None)
def budget_check(actions):
    executed=[];obj=agent(actions);n0=len(query_events)
    obs=NS(screenshot=shot,tool_call=None,ask_user_response=None)
    env=NS(get_task_goal=lambda **kw:'offline goal',initialize_task=lambda **kw:obs,
        execute_action=lambda a:(executed.append(a.action_type) or obs),
        get_task_score=lambda **kw:(0,'offline'),tear_down_task=lambda **kw:None)
    steps,score=runner(env,obj,'offline',50,traj)
    return dict(environment_steps=steps,model_queries=len(query_events)-n0,executed=executed,
                type_count=executed.count('input_text'),enter_count=executed.count('keyboard_enter'))
out['budget_25_text_actions']=budget_check([dict(action_type='input_text',text='hello')]*25)
out['budget_text_at_step50']=budget_check([dict(action_type='wait')]*49+[dict(action_type='input_text',text='hello')])
assert out['budget_25_text_actions']['model_queries']==25
assert out['budget_text_at_step50']['enter_count']==0

attempts=[]
def fail(**kw):attempts.append(kw);raise TimeoutError('offline synthetic failure')
retry=extract('tools/MobileWorld/src/mobile_world/agents/base.py','openai_chat_completions_create',dict(logger=logger,time=clock))
retry(NS(openai_client=NS(max_retries=0,chat=NS(completions=NS(create=fail)))),'local',[])
assert len(attempts)==3
out['outer_sends_despite_sdk_retries_zero']=len(attempts)
# A synthetic abrupt interruption after receipt, before transport returns, leaves no durable start.
# This is an ordinary Python exception in this offline test, not an OS/process signal.
class MockAbandon(BaseException):pass
records=[]
def abandon(*a):raise MockAbandon()
handler=extract('eval/devicestream/record_proxy_adb.py','_handle',dict(time=clock,json=json,
    phone_http=abandon,common=NS(write=lambda *a:records.append(a)),a=NS(log='unused',device='mock',model='mock'),LOCK=None))
try:handler(NS(headers={'Content-Length':'2'},rfile=io.BytesIO(b'{}'),path='/v1/chat/completions'),'POST')
except MockAbandon:pass
assert not records
out['proxy_records_before_transport_completes']=len(records)
out['real_network_device_or_process_calls']=0
save('contract_checks.json',out);manifest('contract_read_manifest.json')
print(json.dumps(dict(scroll_cases=len(out['scroll']),empty_text=out['empty_text'],
    retry_sends=len(attempts),budget25={k:v for k,v in out['budget_25_text_actions'].items() if k!='executed'},
    budget50={k:v for k,v in out['budget_text_at_step50'].items() if k!='executed'},other_actions=out['other_actions']),indent=2))

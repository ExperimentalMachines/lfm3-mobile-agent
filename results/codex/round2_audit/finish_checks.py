"""Final offline rendering, input identity and evidence checks."""
import io
import json
import re
import statistics as st
from audit_common import ROOT,DOCS,OUT,checked,read,txt,js,jl,save,manifest

rendered={}
class Writer:
    def __init__(self,path):self.path=str(path)
    def write(self,s):rendered[self.path]=rendered.get(self.path,'')+s;return len(s)
def memory_open(path,mode='r',*args,**kw):
    p=checked(path)
    if mode=='w':
        assert p in [ROOT/'results/qdc/speed_qdc_v6.json',ROOT/'results/qdc/speed_qdc_v6.md']
        return Writer(p)
    assert mode=='r';return io.StringIO(txt(p))
exec(compile(txt('scripts/qdc_report_v6.py'),'scripts/qdc_report_v6.py','exec'),dict(open=memory_open,print=lambda *a:None))
out={'qdc_renderer_exact':{p:txt(p)==s for p,s in rendered.items()}}
assert all(out['qdc_renderer_exact'].values())
r=js(OUT/'qdc_recomputed.json');identities={}
for model in ['v4','guiowl','maiui']:
    a=r['parts']['opt2_pass1']['models'][model]['rows'];b=r['parts']['opt2_pass2']['models'][model]['rows']
    identities[model+'_pass1_pass2']=all(x['image']==y['image'] and x['task']==y['task'] and x['text_chars']==y['text_chars'] for x,y in zip(a,b))
for part in ['opt1_eval','opt2_pass1','opt2_pass2']:
    a=r['parts'][part]['models']['guiowl']['rows'];b=r['parts'][part]['models']['maiui']['rows']
    identities[part+'_guiowl_maiui_images']=all(x['image']==y['image'] for x,y in zip(a,b))
identities['adapter_copy']=read('eval/mobileworld/lfm3_mw_agent.py')==read('eval/devicestream/agents/lfm3_mw_agent.py')
identities['format_copy']=read('train/agent_format.py')==read('eval/devicestream/agents/agent_format.py')
assert all(identities.values());out['input_identities']=identities

p='results/devstream/run_20261118_1519/dev0/'
rows=jl(p+'requests_v4.jsonl');th=jl(p+'thermal.jsonl');dv=js(p+'device.json')
out['pixel']=dict(device=dv,calls=len(rows)-1,latency_median=st.median(r['latency_s'] for r in rows[1:]),
    latency_range=[min(r['latency_s'] for r in rows[1:]),max(r['latency_s'] for r in rows[1:])],
    last_latency=rows[-1]['latency_s'],fourth_timed=rows[4]['latency_s'],
    fourth_timed_prompt_tok_s=rows[4]['response']['timings']['prompt_per_second'],
    thermal_transition=[dict(line=i,**v) for i,v in enumerate(th,1) if 21<=i<=25])

models={
    'LFM3 v4':['models/lfm3vl2b_v4-GGUF/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf','models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf'],
    'GUI-Owl-1.5-2B':['models/GUI-Owl-1.5-2B-GGUF/GUI-Owl-1.5-2B-Instruct.Q4_K_M.gguf','models/GUI-Owl-1.5-2B-GGUF/GUI-Owl-1.5-2B-Instruct.mmproj-Q8_0.gguf'],
    'MAI-UI-2B':['models/MAI-UI-2B-GGUF/MAI-UI-2B-Q4_K_M.gguf','models/MAI-UI-2B-GGUF/mmproj-MAI-UI-2B-Q8_0.gguf'],
    'MAI-UI-2B Q8_0':['models/MAI-UI-2B-GGUF/MAI-UI-2B-Q8_0.gguf','models/MAI-UI-2B-GGUF/mmproj-MAI-UI-2B-Q8_0.gguf']}
out['model_sizes_gb']={k:round(sum(checked(f).stat().st_size for f in files)/1e9,3) for k,files in models.items()}
assert out['model_sizes_gb']==js(DOCS/'data/runs.json')['gguf_sizes_gb']

# Hash additional source text explicitly cited in the report; none is executed.
paths=['results/codex/session_1118_audit/report.md','scripts/devstream_device_v6.sh','scripts/qdc_chain2.sh',
       'eval/devicestream/record_proxy_adb.py','eval/devicestream/record_proxy_common.py','eval/mobileworld/bench_speed.py',
       'scripts/build_runs_registry.py','scripts/sealed_analysis.py','docs/PREREG_v4.md','scripts/local_maiui_aw.sh',
       'scripts/colab_mw_models.sh','scripts/mw_snapshot_r2.sh','tools/MobileWorld/src/mobile_world/runtime/client.py',
       'tools/MobileWorld/src/mobile_world/runtime/utils/docker.py','tools/MobileWorld/src/mobile_world/core/subcommands/eval.py',
       'android_world/android_world/env/interface.py','eval/androidworld/lfm_agent.py',
       'tools/MobileWorld/src/mobile_world/agents/implementations/gui_owl_1_5.py',
       'tools/MobileWorld/src/mobile_world/agents/implementations/mai_ui_agent.py']
for p in paths:read(p)
save('final_checks.json',out);manifest('additional_read_manifest.json')
print(json.dumps({'qdc_renderer_exact':out['qdc_renderer_exact'],'input_identities':identities,
                  'pixel':{k:v for k,v in out['pixel'].items() if k not in ['device','thermal_transition']},
                  'model_sizes_gb':out['model_sizes_gb']},indent=2))

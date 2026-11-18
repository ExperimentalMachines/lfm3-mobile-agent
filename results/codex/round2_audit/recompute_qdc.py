"""Independent arithmetic; never imports or runs a benchmark/proxy/server."""
import collections
import datetime
import json
import re
import statistics as s
from audit_common import ROOT, js, jl, txt, save, manifest

R = 'results/qdc/run_20261118_1808_v6'
models = ['v4','guiowl','maiui']
report = js('results/qdc/speed_qdc_v6.json')
all_rows, output, checks = {}, {}, []

def compare(a, b, path):
    if isinstance(a, dict):
        for k in a:
            compare(a[k], b[k], path + '.' + k)
    elif isinstance(a, list):
        for i, x in enumerate(a):
            compare(x, b[i], path + f'[{i}]')
    else:
        checks.append({'path': path, 'computed': a, 'saved': b, 'match': a == b})

def calc(rows, thermal=None):
    assert rows and all(r['status'] == 200 and 'timings' in r['response'] for r in rows)
    times = [r['response']['timings'] for r in rows]
    lat = [r['latency_s'] for r in rows]
    out = dict(calls=len(rows), e2e_median_s=round(s.median(lat),1),
       e2e_min_max_s=[round(min(lat),1), round(max(lat),1)],
       phone_median_s=round(s.median((t['prompt_ms']+t['predicted_ms'])/1000 for t in times),1),
       prompt_s_median=round(s.median(t['prompt_ms'] for t in times)/1000,1),
       prompt_tokens_median=int(s.median(t['prompt_n'] for t in times)),
       prompt_tok_s=round(sum(t['prompt_n'] for t in times)*1000/sum(t['prompt_ms'] for t in times),1),
       gen_tokens_median=int(s.median(t['predicted_n'] for t in times)),
       gen_tok_s_llamacpp_median=round(s.median(t['predicted_per_second'] for t in times),1),
       finished_normally=f"{sum(r['response']['choices'][0]['finish_reason']=='stop' for r in rows)}/{len(rows)}")
    if thermal is not None:
        freq = [max(map(int,p['cur_freq_khz'].split()))/1e6 for p in thermal
                if any(r['t_start'] <= p['t'] <= r['t_end'] for r in rows)]
        out['fastest_core_ghz_median_sampled'] = round(s.median(freq),2)
    return out

for part in ['opt1_eval','opt2_pass1','opt2_pass2','smoke_v6_1806']:
    d = f'{R}/{part}' if not part.startswith('smoke') else 'results/qdc/'+part
    thermal = jl(d+'/thermal.jsonl')
    settings = js(d+'/settings.json')
    device = js(d+'/device.json')
    worker = txt(d+'/worker.log')
    version = txt(d+'/llama_version.txt')
    output[part] = {'settings':settings,'device':device,'version':version,'models':{}}
    if part in report['settings']:
        compare(settings,report['settings'][part],part+'.settings')
    for m in (['v4'] if part.startswith('smoke') else models):
        rows = jl(d+'/requests_'+m+'.jsonl')
        bench = jl(d+'/bench_'+m+'.jsonl')
        bench_json = js(d+'/bench_'+m+'.json')
        server = txt(d+'/server_'+m+'.log')
        client = txt(d+'/client_'+m+'.log')
        assert len(rows)==len(bench)==len(bench_json['rows'])
        assert bench[0]['rep']==0 and all(b['rep']==1 for b in bench[1:])
        assert len(rows)==1+len(settings['shots'].split())*settings['reps']
        assert len(re.findall(r'stop processing:',server))==len(rows)
        prompt_lines = re.findall(r'prompt eval time =\s*([\d.]+) ms /\s*(\d+) tokens',server)
        decode_lines = re.findall(r'        eval time =\s*([\d.]+) ms /\s*(\d+) tokens',server)
        assert len(prompt_lines)==len(decode_lines)==len(rows)
        details=[]
        for i,(r,b,pr,ge) in enumerate(zip(rows,bench,prompt_lines,decode_lines),1):
            t=r['response']['timings']; u=r['response']['usage']; q=r['request']
            assert r['status']==200 and r['t_end']<=b['t'] and b['t']-r['t_end']<2
            if i>1: assert rows[i-2]['t_end'] < r['t_start']
            assert abs(float(pr[0])-t['prompt_ms']) <= .0051 and int(pr[1])==t['prompt_n']
            assert abs(float(ge[0])-t['predicted_ms']) <= .0051 and int(ge[1])==t['predicted_n']
            assert u['prompt_tokens']==t['cache_n']+t['prompt_n']
            assert abs(t['predicted_per_second']-(t['predicted_n']-1)*1000/t['predicted_ms']) < 1e-8
            details.append(dict(record=i,task=b['task'],rep=b['rep'],latency_s=r['latency_s'],
                client_latency_s=b['latency_s'],prompt_total=u['prompt_tokens'],prompt_processed=t['prompt_n'],
                cached=t['cache_n'],output=t['predicted_n'],cap=q['max_tokens'],action=b['action'],
                image=[v for v in q['messages'] if 'image_sha256' in v],
                text_chars=sum(v.get('text_len',0) for v in q['messages']),
                request_start=r['t_start'],request_end=r['t_end']))
        if len(rows)>1:
            assert details[0]['image'][0]['image_sha256']!=details[1]['image'][0]['image_sha256']
        diag=dict(rows=details,all_successful=True,ordered_one_proxy_record_per_predict=True,
                  server_timing_and_completion_count_match=True,
                  explicit_FA_lines=[l for l in server.splitlines() if re.search(r'flash_attn|flash.attention',l,re.I)],
                  explicit_image_counts=[l for l in server.splitlines() if re.search(r'image.*(?:n_tokens|tokens\s*=)',l,re.I)],
                  retry_error_lines=[l for l in client.splitlines() if re.search(r'Error calling OpenAI|Failed to parse|unparseable|Traceback|Request timed out',l)])
        if len(rows)>1:
            timed=rows[1:]; all_rows[(part,m)]=timed
            summ=calc(timed,thermal)
            actual=report['option1'][m] if part=='opt1_eval' else report['option2'][part.replace('opt2_','')][m]
            compare(summ,actual,part+'.'+m)
            ps=[(i,p) for i,p in enumerate(thermal,1) if any(r['t_start']<=p['t']<=r['t_end'] for r in timed)]
            fq=[list(map(int,p['cur_freq_khz'].split())) for i,p in ps]
            diag.update(summary=summ,
                exact_medians=dict(proxy_latency_s=s.median(r['latency_s'] for r in timed),
                    client_latency_s=s.median(b['latency_s'] for b in bench[1:]),
                    prompt_processed=s.median(r['response']['timings']['prompt_n'] for r in timed),
                    prompt_total=s.median(r['response']['usage']['prompt_tokens'] for r in timed),
                    cached=s.median(r['response']['timings']['cache_n'] for r in timed),
                    output=s.median(r['response']['timings']['predicted_n'] for r in timed)),
                thermal=dict(sample_count=len(ps),first_line=ps[0][0],last_line=ps[-1][0],
                    max_freq_counts=dict(collections.Counter(max(f) for f in fq)),
                    per_core_median_khz=[s.median(f[j] for f in fq) for j in range(8)],
                    battery_temp_dC=sorted({p['battery_temp_dC'] for _,p in ps}),
                    status=sorted({p['thermal'] for _,p in ps})))
        output[part]['models'][m]=diag
    if part=='opt1_eval':
        output[part]['frequency_timeline']=[dict(line=i,t=p['t'],max_khz=max(map(int,p['cur_freq_khz'].split())))
          for i,p in enumerate(thermal,1)]

r1=jl('results/qdc/run_20261118_1554/dev0/requests_v4.jsonl')
compare(calc(r1[1:]),report['round1']['v4'],'round1.v4')
probe=jl('results/qdc/run_20261118_1554/fa_probe/requests_maiui_fa.jsonl')[0]
compare(dict(e2e_s=round(probe['latency_s'],1),prompt_s=round(probe['response']['timings']['prompt_ms']/1000,1),
   gen_tokens=probe['response']['timings']['predicted_n'],finish_reason=probe['response']['choices'][0]['finish_reason']),
   report['round1']['maiui_q4_fa_probe'],'round1.probe')
compare(js('results/qdc/run_20261118_1554/dev0/device.json'),report['device'],'device')
combined={m:all_rows[('opt2_pass1',m)]+all_rows[('opt2_pass2',m)] for m in models}
head={m:s.median(r['latency_s'] for r in rows) for m,rows in combined.items()}
ratios={m:head[m]/head['v4'] for m in models[1:]}
paired={m:[all_rows[(p,m)][i]['latency_s']/all_rows[(p,'v4')][i]['latency_s'] for p in ['opt2_pass1','opt2_pass2'] for i in range(5)] for m in models[1:]}
v4avg=sum(report['option2'][p]['v4']['e2e_median_s'] for p in ['pass1','pass2'])/2
headline=dict(generator_v4_mean_of_rounded_pass_medians=v4avg,pooled_option2_medians=head,
   pooled_option2_ratios=ratios,paired_case_ratios=paired,
   option1_vs_v4_option2={m:s.median(r['latency_s'] for r in all_rows[('opt1_eval',m)])/v4avg for m in models[1:]},
   v4_two_shared_screens={p:s.median(r['latency_s'] for r in all_rows[(p,'v4')][:2]) for p in ['opt1_eval','opt2_pass1','opt2_pass2']})
save('qdc_recomputed.json',dict(parts=output,headline=headline,checks=checks,mismatches=[c for c in checks if not c['match']]))
manifest('qdc_read_manifest.json')
print(json.dumps(dict(comparisons=len(checks),mismatches=[c for c in checks if not c['match']],headline=headline),indent=2))

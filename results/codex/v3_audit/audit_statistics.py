"""Exact paired power and sensitivity. No normal-approximation significance tests."""
import json
import math
from pathlib import Path
from statistics import NormalDist

OUT=Path(__file__).resolve().parent

def exact(b,c):
    return min(1., 2*sum(math.comb(b+c,i) for i in range(min(b,c)+1))/2**(b+c))

def binomial(n,p):
    return [math.comb(n,k)*p**k*(1-p)**(n-k) for k in range(n+1)]

def conditional_power(m,theta):
    return sum(prob for k,prob in enumerate(binomial(m,theta)) if exact(k,m-k)<=.05)

def unconditional_power(n,q,delta):
    # D=+1 with probability (q+delta)/2, -1 with (q-delta)/2, 0 otherwise.
    # M discordants is Bin(n,q); conditional on M, positive differences are Bin(M,theta).
    theta=(1+delta/q)/2
    return sum(prob*conditional_power(m,theta) for m,prob in enumerate(binomial(n,q)))

def root(fun,upper):
    assert fun(upper)>=.8
    lo,hi=0.,upper
    for _ in range(55):
        mid=(lo+hi)/2
        if fun(mid)<.8:lo=mid
        else:hi=mid
    return hi

def main():
    aw=json.loads((OUT/'verified_aw.json').read_text())
    eps=json.loads((OUT/'verified_aw_episodes.json').read_text())
    runs={e['run'] for e in eps}
    index={r:{e['task']:e for e in eps if e['run']==r} for r in runs}
    selected=[('lfm3vl2b_ft','lfm3vl2b_v3'),('lfm3vl2b_v2','lfm3vl2b_v3'),('lfm3vl2b_v3','guiowl15_2b_matched'),('lfm3vl2b_ft','lfm3vl2b_v2_forcethink')]
    sensitivity=[]; power=[]
    for a,b in selected:
        strict=next(x for x in aw['comparisons'] if x['A']==a and x['B']==b)
        ia,ib=index[a],index[b]
        for rule in ('strict_seed_and_goal','equal_goal_allow_missing_seed','all_task_ids_sensitivity_only'):
            keys=[k for k in ia if rule=='all_task_ids_sensitivity_only' or (ia[k]['goal']==ib[k]['goal'] and (rule=='equal_goal_allow_missing_seed' or ia[k]['seed']==ib[k]['seed']))]
            ao=sum(ia[k]['full_success'] and not ib[k]['full_success'] for k in keys)
            bo=sum(ib[k]['full_success'] and not ia[k]['full_success'] for k in keys)
            sensitivity.append({'A':a,'B':b,'rule':rule,'n':len(keys),'A_only':ao,'B_only':bo,'p':exact(ao,bo)})
        if (a,b) not in (selected[0],selected[2]):continue
        m=strict['A_only']+strict['B_only']
        for n in (116,strict['n_pairs']):
            q=m/n
            mde=root(lambda d:unconditional_power(n,q,d),q)
            cmde=root(lambda d:conditional_power(m,(1+d/q)/2),q)
            z=NormalDist().inv_cdf(.975)+NormalDist().inv_cdf(.8)
            power.append({'A':a,'B':b,'n':n,'discordants':m,'assumed_discordance_probability':q,
                'alpha':.05,'target_power':.8,'two_sided':True,'exact_unconditional_mde_pp':100*mde,
                'expected_net_tasks_at_mde':n*mde,'conditional_on_observed_discordants_mde_pp':100*cmde,
                'normal_approx_mde_pp':100*z*math.sqrt(q/n),
                'minimum_significant_net_tasks_if_discordants_fixed':min(abs(2*k-m) for k in range(m+1) if exact(k,m-k)<=.05),
                'observed_effect_power':unconditional_power(n,q,abs(strict['A_only']-strict['B_only'])/n)})
    out={'method':'80% power, alpha=.05, two-sided exact McNemar; unconditional enumeration over M~Bin(n,q), then K~Bin(M,(1+delta/q)/2). q estimated from observed discordance and held fixed; illustrative prospective power, not evidence of equivalence. No unique MDE from n alone.','power':power,'sensitivity':sensitivity}
    with (OUT/'statistics.json').open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()

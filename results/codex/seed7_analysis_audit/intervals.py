"""Independent inversion using sign-sum interval endpoints, plus exact weighted enumeration."""
import json
import math
from pathlib import Path
import numpy as np
from recompute import load, success, paired, OUT

def inversion(d):
    d=np.asarray(d,dtype=int);n=len(d);D=int(d.sum())
    # The published RNG is reused only to check its numerical output; no analysis code is imported.
    s=np.random.default_rng(0).choice([-1,1],size=(10000,n))
    A=(s*d).sum(axis=1);B=s.sum(axis=1)
    p=lambda delta:float((1+np.count_nonzero(np.abs(A-delta*B)>=abs(D-delta*n)-1e-10))/10001)
    # Each sign draw accepts delta between its two equality roots.
    lo=np.minimum((D-A)/(n-B),(D+A)/(n+B))
    hi=np.maximum((D-A)/(n-B),(D+A)/(n+B))
    lower=float(np.sort(lo)[499]);upper=float(np.sort(hi)[9500])
    grid=[math.ceil((lower-1e-12)*1000)/10,math.floor((upper+1e-12)*1000)/10]
    a=int((d==1).sum());b=int((d==-1).sum());c=n-a-b
    endpoints=[]
    for i in range(a+1):
        for j in range(b+1):
            for k in range(c+1):
                u=2*i-a;v=2*j-b;w=2*k-c
                AA=u-v;BB=u+v+w
                prob=math.comb(a,i)*math.comb(b,j)*math.comb(c,k)/2**n
                if abs(BB)==n:
                    L,R=-math.inf,math.inf
                else:
                    roots=((D-AA)/(n-BB),(D+AA)/(n+BB));L,R=min(roots),max(roots)
                endpoints.append((L,R,prob,AA,BB))
    def quantile(ix):
        total=0
        for x in sorted(endpoints,key=lambda e:e[ix],reverse=bool(ix)):
            total+=x[2]
            if total>=.05-1e-14:return x[ix]
    def ep(delta):
        return min(1.0, math.fsum(x[2] for x in endpoints if abs(x[3]-delta*x[4])>=abs(D-delta*n)-1e-10))
    return {'mean_pp':100*D/n,'counts':{'+1':a,'-1':b,'0':c},'mc_p0':p(0),
            'mc_grid_ci_pp':grid,'mc_continuous_ci_pp':[100*lower,100*upper],
            'exact_signflip_p0':ep(0),'exact_inversion_ci_pp':[100*quantile(0),100*quantile(1)],
            'mc_p_minus_6_9':p(-.069),'exact_p_minus_6_9':ep(-.069),
            'mc_p_minus_8_over_116':p(-8/116),
            'mc_non_inferior':lower>-.069,'exact_non_inferior':quantile(0)>-.069}

def main():
    original={a:load(a) for a in ('v4','guiowl','v1')}
    final={a:{**e,**(load(a,True) if a!='v1' else {})} for a,e in original.items()}
    out={}
    for stage,runs in [('prelim',original),('final',final)]:
        out[stage]={}
        for x,y in [('v4','guiowl'),('v1','guiowl'),('v4','v1')]:
            d=[success(runs[x][t])-success(runs[y][t]) for t in sorted(runs[x])]
            out[stage][x+'-'+y]=inversion(d)
        both=[t for t in runs['v4'] if not runs['v4'][t]['exception_info'] and not runs['guiowl'][t]['exception_info']]
        out[stage]['secondary']=paired({t:runs['v4'][t] for t in both},{t:runs['guiowl'][t] for t in both})
    ds=[success(final['v4'][t])-success(final['guiowl'][t]) for t in sorted(final['v4'])]
    ds[sorted(final['v4']).index('ClockStopWatchPausedVerify')]-=1
    out['clock_sensitivity']=inversion(ds)
    (OUT/'interval_recomputed.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()

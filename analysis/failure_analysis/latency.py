import json, sys, statistics as st
R = json.load(open(sys.argv[1]))
def q(xs, p): xs = sorted(xs); return xs[min(len(xs)-1, int(p*len(xs)))]
for k in ["lfm3vl2b_v4", "lfm3vl2b_v4_guards", "lfm3vl2b_v41", "lfm3vl2b_v42", "lfm3vl2b_v42_guards", "guiowl15_2b_matched"]:
    P, D, N, PN, C, L, TOT, CALLS = [], [], [], [], [], [], [], []
    for e in R["dev"][k]["episodes"].values():
        for pm, dm, n, pn, c in zip(e["prompt_ms"], e["pred_ms"], e["pred_n"], e["prompt_n"], e["cache_n"]):
            if pm is None or dm is None: continue
            P.append(pm); D.append(dm); N.append(n); PN.append(pn); C.append(c or 0)
        L += e["latency"]
    per_tok = [d / n for d, n in zip(D, N) if n]
    share = [d / (p + d) for p, d in zip(P, D) if p + d > 0]
    mt = st.median(per_tok); ml = st.median(L)
    print(f"{k}: steps {len(P)}; median prompt_ms {st.median(P):.0f} (prompt_n {st.median(PN):.0f} uncached, cache_n {st.median(C):.0f}); "
          f"median decode_ms {st.median(D):.0f} for {st.median(N):.0f} tokens ({mt:.1f} ms/token); decode share of model time median {st.median(share):.1%}, "
          f"pooled {sum(D)/(sum(P)+sum(D)):.1%}; latency_s median {ml:.2f} p90 {q(L,0.9):.2f}; +20 tok = {20*mt/1000:.2f}s ({20*mt/1000/ml:.1%}), +40 tok = {40*mt/1000:.2f}s ({40*mt/1000/ml:.1%})")
    # output token distribution
    print(f"    output tokens p10/50/90: {q(N,0.1)}/{q(N,0.5)}/{q(N,0.9)}; sum decode s {sum(D)/1000:.0f} vs prompt s {sum(P)/1000:.0f}; total latency s {sum(L):.0f}")

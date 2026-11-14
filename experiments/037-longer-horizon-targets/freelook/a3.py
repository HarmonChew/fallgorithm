import numpy as np
from pathlib import Path
from block_stack_ai import experiment023 as e23, experiment034 as e34, experiment033 as e33
R=Path('/home/harmon-chew/projects/code/fallgorithm'); S=R/'experiments/036-20hz-full-reteach'
nets={'s0':R/'experiments/032-v18-search-taught/value_sweep9.bin'}
for n in range(1,7): nets[f's{n}']=S/f'stage2/value_sweep{n}.bin'
for rnd in (0,5):
    d=e23._load_npz(R/f'runs/036-data/stage2/round{rnd}.npz')
    m=d['lines']<230
    d=e33._split(d,m)
    rng=np.random.default_rng(2); keep=rng.random(len(d['lines']))<0.25
    d=e33._split(d,keep)
    V={k:e34._values(p,d) for k,p in nets.items()}
    h=d['features'][:,0]; L=d['lines']//10
    print(f'round {rnd} boards {len(h)}; holes share>=1 {np.mean(h>=1):.3f}')
    def dm(v):
        out=v.copy()
        for s in np.unique(L): out[L==s]-=v[L==s].mean()
        return out
    for k in V:
        diff=dm(V[k]-V['s2'])
        # value vs holes slope within step: regress demeaned value on demeaned holes
        vh=dm(V[k]); hh=dm(h.astype(float))
        slope=float((vh*hh).sum()/(hh*hh).sum())
        ah=dm(d['features'][:,3].astype(float)); sa=float((vh*ah).sum()/(ah*ah).sum())
        print(f'  {k}: diff vs s2 (demeaned) by holes 0/1/2/3+: '+' '.join(f'{diff[(h==j) if j<3 else (h>=3)].mean():+.3f}' for j in range(4)), f'| value slope per hole {slope:+.3f}, per agg-height cell {sa:+.4f}')

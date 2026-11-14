import numpy as np
from pathlib import Path
R=Path('/home/harmon-chew/projects/code/fallgorithm')
for n in range(1,7):
    with np.load(R/f'runs/036-data/stage2/targets{n}.npz') as d:
        f=d['features']; k=d['kind']; g=d['goal']; L=d['lines']; rest=d['rest']
    h=f[:,0]
    early=L<130
    msg=[]
    for lo,hi in ((0,1),(1,5),(5,10),(10,20),(20,999)):
        m=early&(h>=lo)&(h<hi)
        msg.append(f'h{lo}-{hi}: n {m.sum():6d} ({m.mean()*100:.3f}%) goal {g[m].mean() if m.any() else float("nan"):.2f}')
    pm=early&(k==0)&(h>=10)
    print(f'sweep {n} rows {len(g)} played {(k==0).sum()} | '+' | '.join(msg), f'| played h>=10 early: {pm.sum()} goal {g[pm].mean() if pm.any() else 0:.2f} actual {np.nanmean(rest[pm]) if pm.any() else 0:.2f}')

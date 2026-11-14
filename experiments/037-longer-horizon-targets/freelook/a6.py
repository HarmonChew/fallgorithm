import numpy as np, sys
from pathlib import Path
from block_stack_ai import experiment023 as e23, experiment034 as e34, native
SP='./'
R=Path('/home/harmon-chew/projects/code/fallgorithm'); S=R/'experiments/036-20hz-full-reteach'
nets={'s0':R/'experiments/032-v18-search-taught/value_sweep9.bin'}
for n in range(1,7): nets[f's{n}']=S/f'stage2/value_sweep{n}.bin'
d=np.load(SP+f'open{sys.argv[1]}.npz'); W=native.WIDTH
for arm in ('s2','s6'):
    rows=d[arm][:14]; b=e23._boards(rows)
    V={k:e34._values(p,b) for k,p in nets.items()}
    print('== boards from',arm,'game; cols: piece, lines, holes, agg, maxh, then value under s0..s6')
    for i in range(len(rows)):
        f=rows[i,W+4:]
        print(f'{i:2d} L{rows[i,W]:3d} dr{rows[i,W+2]:2d} last{rows[i,W+3]} holes {f[0]:2d} agg {f[3]:3d} maxh {f[5]:2d} |', ' '.join(f'{V[k][i]:6.2f}' for k in V))

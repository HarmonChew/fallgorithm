import json, numpy as np, sys
from pathlib import Path
from multiprocessing import Pool
from block_stack_ai import experiment036 as x, experiment023 as e23, experiment034 as e34, experiment033 as e33, native
R=Path('/home/harmon-chew/projects/code/fallgorithm')
S=R/'experiments/036-20hz-full-reteach'
nets={'s0_032':R/'experiments/032-v18-search-taught/value_sweep9.bin'}
for n in range(1,7): nets[f's{n}']=S/f'stage2/value_sweep{n}.bin'
zero=e23._load_npz(R/'runs/036-data/stage2/round0.npz')
held=np.isin(zero['seed'],np.array(x.round_seeds(2,0)[:x.CHECK_SEEDS]))
ck=e33._split(zero, held&(zero['lines']<230))
print('check boards',len(ck['lines']))
V={k:e34._values(p,ck) for k,p in nets.items()}
np.savez('./checkvals.npz',**V)
rest=(ck['final']-ck['score'])/x.TETRIS_18
keys=list(V)
print('mean value by step (Tetrises); actual')
for lo in (0,50,100,130,150,200,220):
    m=(ck['lines']>=lo)&(ck['lines']<lo+10)
    print(lo,[round(float(V[k][m].mean()),2) for k in keys], round(float(rest[m].mean()),2))
print('rms diff vs s2 / vs previous')
prev=None
for k in keys:
    print(k, round(float(np.sqrt(((V[k]-V['s2'])**2).mean())),3), None if prev is None else round(float(np.sqrt(((V[k]-V[prev])**2).mean())),3),
      'demeaned-by-step rms vs prev', None if prev is None else round(float(np.sqrt((((V[k]-V[prev]) - np.array([ (V[k]-V[prev])[(ck['lines']//10)==s].mean() for s in ck['lines']//10]))**2).mean())),3))
    prev=k

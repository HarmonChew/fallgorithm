import numpy as np
from pathlib import Path
from multiprocessing import Pool
from block_stack_ai import experiment036 as x, experiment023 as e23, experiment033 as e33, native
R=Path('/home/harmon-chew/projects/code/fallgorithm')
S=R/'experiments/036-20hz-full-reteach'
nets={'s0_032':R/'experiments/032-v18-search-taught/value_sweep9.bin'}
for n in range(1,7): nets[f's{n}']=S/f'stage2/value_sweep{n}.bin'
zero=e23._load_npz(R/'runs/036-data/stage2/round0.npz')
held=np.isin(zero['seed'],np.array(x.round_seeds(2,0)[:x.CHECK_SEEDS]))
ck=e33._split(zero, held&(zero['lines']<230))
rng=np.random.default_rng(1)
idx=np.sort(rng.choice(len(ck['lines']),3000,replace=False))
sub=e33._split(ck,np.isin(np.arange(len(ck['lines'])),idx))
rows=e23._rows(sub)
c=e33._config()
args=dict(line_cap=c["line_cap"], start_level=c["start_level"], double_killscreen=c["double_killscreen"], tap_interval=x.TAP_INTERVAL)
def job(a):
    w,r=a
    v,k=native.backup_values(w, r, children=True, **args)
    return np.array(v), np.frombuffer(k,np.int32).reshape(-1,native.DUMP_STRIDE)
W=native.WIDTH
out={}
with Pool(8) as p:
    for name,path in nets.items():
        data=path.read_bytes()
        res=p.map(job,[(data,np.ascontiguousarray(ch).tobytes()) for ch in np.array_split(rows,32)])
        kids=np.concatenate([k for _,k in res]).reshape(len(rows),7,-1)
        out[name]=kids
np.savez('./kids.npz',**out,parent=rows)
plines=rows[:,W]
for band,(lo,hi) in {'0-129':(0,130),'130-229':(130,230)}.items():
    m=(plines>=lo)&(plines<hi)
    print('band',band,'boards',m.sum())
    for name,k in out.items():
        k=k[m]; valid=k[:,:,W]>=0
        cleared=(k[:,:,W]-plines[m][:,None])
        cl=cleared[valid]
        same=(out[name][m]==out['s2'][m]).all(axis=2)[valid].mean()
        f=k[:,:,W+4:][valid]
        print(f"  {name}: same child as s2 {same:.3f}; clears: any {np.mean(cl>0):.3f} single {np.mean(cl==1):.4f} tetris {np.mean(cl==4):.4f}; child holes {f[:,0].mean():.3f} maxh {f[:,5].mean():.2f} agg {f[:,3].mean():.1f}")

import numpy as np, sys
from multiprocessing import Pool
from pathlib import Path
from block_stack_ai import experiment036 as x, experiment023 as e23, experiment034 as e34, native
SP='./'
MID='experiments/036-20hz-full-reteach/stage1/value_sweep7.bin'
def job(a):
    seed,early=a
    played,rows=x._game(seed,early,MID,dump=True)
    return np.frombuffer(rows,np.int32).reshape(-1,native.DUMP_STRIDE)[:40].copy(), played['result']['score'] if 'result' in played else None
if __name__=='__main__':
    seed=int(sys.argv[1])
    E={k:f'experiments/036-20hz-full-reteach/stage2/value_sweep{k}.bin' for k in (2,6)}
    with Pool(2) as p: res=p.map(job,[(seed,E[2]),(seed,E[6])])
    np.savez(SP+f'open{seed}.npz',s2=res[0][0],s6=res[1][0])

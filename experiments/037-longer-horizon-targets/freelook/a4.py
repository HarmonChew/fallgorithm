import gzip,json,base64,sys
import numpy as np
from block_stack_ai import experiment033 as e33, experiment035 as e35, wellplan
from block_stack_ai.engine import create_game
from block_stack_ai.pathaware import grid_columns
def trace(path,seed):
    d=json.load(gzip.open(path)); e=[x for x in d['episodes'] if str(x['seed'])==str(seed)][0]
    inputs=base64.b64decode(e['inputs']); frozen=e33._frozen()[0]
    out=[];count=-1
    with create_game(**frozen['game'],seed=int(seed)) as game:
        st=game.state
        for m in inputs:
            if st.phase=='active' and st.piece_count!=count:
                count=st.piece_count; c=grid_columns(wellplan.visible_grid(st.board))
                h=e35._heights(c)
                out.append((st.lines,e35._holes(c),max(h),sum(h),st.current_piece,h))
            st,_=game.step(m)
    return out
for name in sys.argv[2:]:
    t=trace(f'runs/036/games/stage2-sweep{name}-A.json.gz',sys.argv[1])
    print('== sweep',name,'pieces',len(t))
    for i in list(range(0,60,3))+list(range(60,len(t),25)):
        if i<len(t): l,ho,mh,ag,p,h=t[i]; print(f'{i:4d} lines {l:3d} holes {ho:2d} maxh {mh:2d} agg {ag:3d} {p} {h}')

"""Free look: how v36's and v29r20d's held-out games go from 230 lines on. No games played."""
import base64, gzip, json, sys
from multiprocessing import Pool
from block_stack_ai import experiment033 as e33, experiment035 as e35, wellplan
from block_stack_ai.engine import create_game
from block_stack_ai.pathaware import grid_columns

def job(a):
    seed, inputs = a
    frozen = e33._frozen()[0]
    spawns, count = [], -1
    with create_game(**frozen["game"], seed=seed) as game:
        state = game.state
        for mask in inputs:
            if state.phase == "active" and state.piece_count != count:
                count = state.piece_count
                cols = grid_columns(wellplan.visible_grid(state.board))
                h = e35._heights(cols)
                spawns.append({"lines": state.lines, "level": state.level, "piece": state.current_piece,
                               "holes": e35._holes(cols), "max_height": max(h), "agg": sum(h),
                               "drought": state.stats.current_i_drought})
            state, _ = game.step(mask)
        lines = state.lines
    ent = next((s for s in spawns if s["lines"] >= 230), None)
    out = {"seed": seed, "lines": lines, "entry230": ent}
    # stack profile through 230-319: mean agg/max height, max drought
    mid = [s for s in spawns if 230 <= s["lines"] < 320]
    if mid:
        out["mid_mean_agg"] = sum(s["agg"] for s in mid) / len(mid)
        out["mid_max_drought"] = max(s["drought"] for s in mid)
        out["mid_mean_holes"] = sum(s["holes"] for s in mid) / len(mid)
    if 230 <= lines < 320:
        out |= e35.classify(spawns)
    return out

if __name__ == "__main__":
    res = {}
    for name, path in [("v36", "experiments/036-20hz-full-reteach/games/heldout-v36.json.gz"),
                       ("v29r20d", "experiments/035-20hz-search-probes/games/heldout-v29r20d.json.gz")]:
        eps = json.load(gzip.open(path, "rt"))["episodes"]
        with Pool(16) as p:
            res[name] = p.map(job, [(int(e["seed"]), base64.b64decode(e["inputs"])) for e in eps], chunksize=4)
        print(name, len(res[name]), file=sys.stderr)
    json.dump(res, open(sys.argv[1], "w"))

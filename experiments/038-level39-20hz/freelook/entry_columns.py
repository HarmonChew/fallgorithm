"""Free look: v36's column heights at each band's entry and at death, and lines at 39 against
column 0's height at 330 lines. 012's 1,000 held-out seeds, stored games replayed; no games played.

Run from the repository root: PYTHONPATH=src python .../entry_columns.py out.json.gz
"""
import base64, gzip, json, statistics as st, sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from block_stack_ai import experiment033 as e33, experiment035 as e35, wellplan
from block_stack_ai.engine import create_game
from block_stack_ai.pathaware import grid_columns

GAMES = "experiments/036-20hz-full-reteach/games/heldout-v36.json.gz"
ENTRIES = (("e230", 230), ("e280", 280), ("e320", 320), ("e330", 330))


def job(a):
    seed, inputs = a
    frozen = e33._frozen()[0]
    count, snaps, last, clears = -1, {}, None, Counter()
    with create_game(**frozen["game"], seed=seed) as game:
        state = game.state
        before = state.lines
        for mask in inputs:
            if state.phase == "active" and state.piece_count != count:
                count = state.piece_count
                if state.lines > before and before >= 330:
                    clears[state.lines - before] += 1
                before = state.lines
                if state.lines >= 200:
                    h = e35._heights(grid_columns(wellplan.visible_grid(state.board)))
                    for key, lo in ENTRIES:
                        if key not in snaps and state.lines >= lo:
                            snaps[key] = list(h)
                    last = (list(h), state.stats.current_i_drought)
            state, _ = game.step(mask)
        if state.lines > before and before >= 330:
            clears[state.lines - before] += 1
        return {"seed": seed, "lines": state.lines, "snaps": snaps, "last": last,
                "clears39": dict(clears)}


def heights(rows):
    return " ".join(f"{sum(h[c] for h in rows) / len(rows):.1f}" for c in range(10))


if __name__ == "__main__":
    eps = json.load(gzip.open(GAMES, "rt"))["episodes"]
    with Pool(24) as p:
        res = p.map(job, [(int(e["seed"]), base64.b64decode(e["inputs"])) for e in eps], chunksize=4)
    json.dump(res, gzip.open(sys.argv[1], "wt"))
    for key, _ in ENTRIES:
        hs = [r["snaps"][key] for r in res if key in r["snaps"]]
        low = Counter(min(range(10), key=lambda c: (h[c], -c)) for h in hs)
        print(key, len(hs), "mean column heights", heights(hs), "| lowest column", dict(sorted(low.items())))
    r39 = [r for r in res if r["lines"] >= 330]
    after = [r["lines"] - 330 for r in r39]
    clears = Counter()
    for r in r39:
        clears.update({int(k): v for k, v in r["clears39"].items()})
    print("reach 330:", len(r39), "mean lines after 330", round(st.mean(after), 2), "median", st.median(after),
          "max", max(after), "| clears by size at 39+", dict(sorted(clears.items())))
    print("last spawn of games ending at 39+: heights", heights([r["last"][0] for r in r39]),
          "| I drought", round(st.mean(r["last"][1] for r in r39), 1))
    mid = [r for r in res if 230 <= r["lines"] < 320]
    print("deaths 230-319:", len(mid), "last spawn heights", heights([r["last"][0] for r in mid]))
    late = [r for r in res if 320 <= r["lines"] < 330]
    print("deaths 320-329:", len(late), "last spawn heights", heights([r["last"][0] for r in late]))
    col0 = [r["snaps"]["e330"][0] for r in r39]
    rest = [sum(r["snaps"]["e330"][1:]) / 9 for r in r39]
    by = defaultdict(list)
    for c, a in zip(col0, after):
        by[min(c, 9)].append(a)
    for c in sorted(by):
        print(f"column 0 at {c}{'+' if c == 9 else ''}: {len(by[c])} games, {st.mean(by[c]):.2f} lines after 330")
    lead = [c - m for c, m in zip(col0, rest)]
    by = defaultdict(list)
    for d, a in zip(lead, after):
        by[max(-3, min(4, round(d)))].append(a)
    for d in sorted(by):
        print(f"column 0 minus the mean of columns 1-9 = {d:+d}: {len(by[d])} games, {st.mean(by[d]):.2f} lines after 330")
    print("correlation with lines after 330: column 0", round(st.correlation(col0, after), 3),
          "| mean of columns 1-9", round(st.correlation(rest, after), 3),
          "| column 0 minus that mean", round(st.correlation(lead, after), 3))

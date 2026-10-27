"""Development comparison of level-29 survival variants of Experiment 005's search.

Each variant patches the well plan's phase (and optionally the SPEND hole charge)
once the current level reaches the variant's onset level. Development seeds only:
Experiment 005's ten published seeds, whose outcomes were already known, plus ten
seeds from SHA256("fallgorithm006/dev/<i>"). The held-out evaluation seeds were
selected afterwards and excluded these.

Usage: variants.py OUTPUT.json [VARIANT,...]
"""

import hashlib
import json
import sys
from multiprocessing import Pool

from block_stack_ai import runner, searchplan, wellplan
from block_stack_ai.engine import create_game
from block_stack_ai.pathaware import column_features

GAME = {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 18, "height": 0}
FRAME_LIMIT = 200000
SEEDS = [39497, 2918, 42114, 18319, 54626, 22909, 30033, 53641, 8833, 62362] + [
    int.from_bytes(hashlib.sha256(f"fallgorithm006/dev/{i}".encode()).digest()[:2], "big")
    for i in range(10)]
# budget: height budget once active; spend: never hold the well once active;
# holes: extra SPEND charge per hole once active; level: onset level.
VARIANTS = {
    "base": dict(budget=None, spend=False, holes=0.0, level=29),
    "spend": dict(budget=None, spend=True, holes=0.0, level=29),
    "spend28": dict(budget=None, spend=True, holes=0.0, level=28),
    "spend27": dict(budget=None, spend=True, holes=0.0, level=27),
    "spend_h3": dict(budget=None, spend=True, holes=-2.0, level=29),
    "b4": dict(budget=4, spend=False, holes=0.0, level=29),
    "b5": dict(budget=5, spend=False, holes=0.0, level=29),
    "b6": dict(budget=6, spend=False, holes=0.0, level=29),
    "b5_28": dict(budget=5, spend=False, holes=0.0, level=28),
    "b5_h3": dict(budget=5, spend=False, holes=-2.0, level=29),
}
ORIGINAL_PHASE, ORIGINAL_VALUE = wellplan.initial_phase, wellplan.plan_value
ACTIVE = {"on": False, "variant": None}


def phase(drought, columns):
    variant = ACTIVE["variant"]
    if ACTIVE["on"]:
        if variant["spend"]:
            return wellplan.SPEND
        if variant["budget"] is not None:
            holds = (drought < wellplan.DROUGHT_BOUND
                     and wellplan.stack_height(columns) < variant["budget"])
            return wellplan.BUILD if holds else wellplan.SPEND
    return ORIGINAL_PHASE(drought, columns)


def value(current_phase, cleared, columns):
    result = ORIGINAL_VALUE(current_phase, cleared, columns)
    if ACTIVE["on"] and current_phase == wellplan.SPEND and ACTIVE["variant"]["holes"]:
        result += ACTIVE["variant"]["holes"] * column_features(columns).holes
    return result


class VariantAgent(searchplan.SearchAgent):
    def _choose(self, state, grid):
        ACTIVE["on"] = state.level >= ACTIVE["variant"]["level"]
        return super()._choose(state, grid)


def play(job):
    name, seed = job
    ACTIVE["variant"] = VARIANTS[name]
    wellplan.initial_phase, wellplan.plan_value = phase, value
    episode = runner._play(dict(GAME, seed=seed), FRAME_LIMIT, VariantAgent(), create_game)
    result = episode["result"]
    return {"variant": name, "seed": seed, "lines": result["lines"], "score": result["score"],
            "stopping_reason": result["stopping_reason"],
            "tetrises": episode["clear_sizes"]["tetrises"]}


def main():
    output = sys.argv[1]
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else list(VARIANTS)
    with Pool(30) as pool:
        rows = pool.map(play, [(name, seed) for name in names for seed in SEEDS])
    summary = {}
    for name in names:
        mine = [row for row in rows if row["variant"] == name]
        lines = sum(row["lines"] for row in mine)
        summary[name] = {
            **VARIANTS[name],
            "top_outs": sum(row["stopping_reason"] != "frame_limit" for row in mine),
            "mean_lines": lines / len(mine),
            "min_lines": min(row["lines"] for row in mine),
            "mean_score": sum(row["score"] for row in mine) / len(mine),
            "tetris_line_rate": 4 * sum(row["tetrises"] for row in mine) / lines,
        }
        print(name, json.dumps(summary[name]))
    document = {"game": GAME, "frame_limit": FRAME_LIMIT, "seeds": SEEDS,
                "summary": summary, "episodes": rows}
    with open(output, "w") as handle:
        json.dump(document, handle, indent=1)
        handle.write("\n")


if __name__ == "__main__":
    main()

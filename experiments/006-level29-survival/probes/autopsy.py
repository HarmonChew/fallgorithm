"""Replay retained Experiment 005 search games and print the board at each spawn.

Usage: autopsy.py RECORD.json.gz SEED [LAST_N]
"""

import gzip
import json
import sys

from block_stack_ai import wellplan
from block_stack_ai.engine import create_game
from block_stack_ai.pathaware import _reachable, gravity_period, grid_columns


def spawn_rows(record_path, seed, agent="search_plan"):
    record = json.load(gzip.open(record_path))
    episode = next(e for e in record["episodes"] if e["seed"] == seed and e["agent"] == agent)
    game_config = dict(record["configuration"]["game"], seed=seed)
    rows = []
    with create_game(**game_config) as game:
        state = game.state
        inputs = iter(episode["inputs"])
        while True:
            columns = grid_columns(wellplan.visible_grid(state.board))
            heights = wellplan.column_heights(columns)
            reachable = _reachable(columns, state.current_piece,
                                   gravity_period(state.level), state.first_delay_remaining)
            rows.append({
                "piece": state.current_piece, "lines": state.lines, "level": state.level,
                "height": wellplan.stack_height(columns),
                "holes": wellplan.field_features(columns).holes,
                "well": heights[wellplan.WELL_COLUMN],
                "heights": heights,
                "reachable": len(reachable),
                "reach_cols": sorted({p.x for p, _ in reachable}),
            })
            for action in inputs:
                state, events = game.step(action)
                if events.spawned:
                    break
            else:
                return rows


def main():
    path, seed = sys.argv[1], int(sys.argv[2])
    last = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    rows = spawn_rows(path, seed)
    for row in rows[-last:]:
        print(json.dumps(row))


if __name__ == "__main__":
    main()

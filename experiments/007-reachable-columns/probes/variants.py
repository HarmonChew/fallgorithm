"""Development comparison of an unfillable-column penalty on Experiment 006's agent.

From level 28 the search charges each beam path ``weight`` per column on which no
reachable placement of any of the seven pieces lands a cell on the board the preview
leaves, and extends ``beam`` paths. Development seeds only: Experiment 006's 30
published seeds, whose outcomes were already known.

Usage: variants.py OUTPUT.json [VARIANT,...]
"""

import json
import sys
from multiprocessing import Pool

from block_stack_ai import runner, searchplan, survivalplan, wellplan
from block_stack_ai.engine import create_game
from block_stack_ai.pathaware import grid_columns, gravity_period, level_for_lines
from block_stack_ai.heuristic import GRID_ROWS, HIDDEN_ROWS
from block_stack_ai.pieces import cells

CONFIG = json.load(open("experiments/006-level29-survival/config.json"))
FRAME_LIMIT = 200000
VARIANTS = {
    "base": dict(weight=0.0, beam=2),
    "w0_b4": dict(weight=0.0, beam=4),
    "w0_b8": dict(weight=0.0, beam=8),
    "w5": dict(weight=5.0, beam=2),
    "w20": dict(weight=20.0, beam=2),
    "w5_b8": dict(weight=5.0, beam=8),
    "w20_b8": dict(weight=20.0, beam=8),
}


def fillable(board, reachable):
    """Columns some reachable placement lands a cell directly on top of."""
    tops = [(column & -column).bit_length() - 1 if column else GRID_ROWS for column in board]
    columns = set()
    for placement, _ in reachable:
        lowest = {}
        for dx, dy in cells(placement.piece, placement.orientation):
            column = placement.x + dx
            lowest[column] = max(lowest.get(column, -1), placement.y + dy + HIDDEN_ROWS)
        columns.update(column for column, row in lowest.items() if row == tops[column] - 1)
    return columns


def search_choice(grid, piece, next_piece, *, drought, level, lines, start_level,
                  first_delay_remaining, ruleset, mode, weight, beam_width):
    phase_of = survivalplan.survival_phase
    budget = searchplan._Budget(10 ** 6)
    columns = grid_columns(grid)
    current = searchplan._expand(columns, piece, gravity_period(level), first_delay_remaining, budget)
    if not current:
        return None
    phase = phase_of(drought, columns)
    paths = []
    for order, (placement, settled) in enumerate(current):
        own = wellplan.plan_value(phase, placement.lines_cleared, settled)
        next_level = level_for_lines(lines + placement.lines_cleared, start_level)
        preview_reachable = searchplan._expand(settled, next_piece, gravity_period(next_level),
                                               first_delay_remaining, budget)
        preview, board, value = searchplan._best(
            preview_reachable, phase_of(wellplan.next_drought(drought, next_piece), settled))
        paths.append((own + value, order, placement, preview, board))
    paths.sort(key=lambda item: (-item[0], item[1]))
    best, best_total = paths[0][2], None
    for value, _, placement, preview, board in paths[:beam_width]:
        if preview is None:
            continue
        unknown_level = level_for_lines(lines + placement.lines_cleared + preview.lines_cleared,
                                        start_level)
        leaves, reach = [], set()
        for unknown in searchplan.unknown_pieces():
            reachable = searchplan._expand(board, unknown, gravity_period(unknown_level),
                                           first_delay_remaining, budget)
            reach |= fillable(board, reachable)
            leaves.append(searchplan._best(reachable, phase_of(
                wellplan.next_drought(wellplan.next_drought(drought, next_piece), unknown),
                board))[2])
        total = value + searchplan.unknown_value(leaves) - weight * (10 - len(reach))
        if best_total is None or total > best_total:
            best, best_total = placement, total
    return best


class VariantAgent(survivalplan.SurvivalAgent):
    variant = None

    def _choose(self, state, grid):
        if state.level < survivalplan.SURVIVAL_LEVEL:
            return super()._choose(state, grid)
        self._drought = 0 if state.current_piece == "I" or state.next_piece == "I" \
            else self._drought + 1
        return search_choice(
            wellplan.visible_grid(state.board), state.current_piece, state.next_piece,
            drought=self._drought, level=state.level, lines=state.lines,
            start_level=state.start_level, first_delay_remaining=state.first_delay_remaining,
            ruleset=state.ruleset, mode=state.mode,
            weight=self.variant["weight"], beam_width=self.variant["beam"])


def play(job):
    name, seed = job
    agent = VariantAgent()
    agent.variant = VARIANTS[name]
    episode = runner._play(dict(CONFIG["game"], seed=seed), FRAME_LIMIT, agent, create_game)
    result = episode["result"]
    return {"variant": name, "seed": seed, "lines": result["lines"], "score": result["score"],
            "stopping_reason": result["stopping_reason"],
            "tetrises": episode["clear_sizes"]["tetrises"]}


def main():
    output = sys.argv[1]
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else list(VARIANTS)
    with Pool(30) as pool:
        rows = pool.map(play, [(name, seed) for name in names for seed in CONFIG["seeds"]])
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
        print(name, json.dumps(summary[name]), flush=True)
    with open(output, "w") as handle:
        json.dump({"game": CONFIG["game"], "frame_limit": FRAME_LIMIT, "seeds": CONFIG["seeds"],
                   "summary": summary, "episodes": rows}, handle, indent=1)
        handle.write("\n")


if __name__ == "__main__":
    main()

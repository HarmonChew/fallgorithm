"""Run Experiment 035: search probes at 20 Hz / 300 ms before the full re-teach (no training).

    python -m block_stack_ai.experiment035 freelook [--jobs N]
    python -m block_stack_ai.experiment035 check [--jobs N]
    python -m block_stack_ai.experiment035 play ARM [--jobs N]
    python -m block_stack_ai.experiment035 time-d3
    python -m block_stack_ai.experiment035 combine [--jobs N]
    python -m block_stack_ai.experiment035 summarize

Every agent is 033's record agent ``v29r20`` (023's v15 below 230 lines, 033's sweep 6
V29@20 at 230-319, 031b's V39' from 320) with one search setting (``ARMS``): ``base`` is
``v29r20``'s own search, ``c18`` and ``c18_d18`` start the deeper commit (and the second
unknown piece) at level 18, ``adj12`` widens the adjust, ``d3`` adds a third unknown piece
at the commit from level 29 (NetSearcher::set_deep3, ABI 29). ``base`` plays 035's 1,000
training seeds once; every arm is paired against it by seed (plan.md, predeclared.md).
``combine`` plays the gaining arms as one setting, if two or more gain. ``freelook``
classifies 033's stored held-out ``v29r20`` games that end before 230 lines (no games).
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment013 as e13, experiment025 as e25, experiment028 as e28
from . import experiment029 as e29, experiment033 as e33, experiment034 as e34
from . import native, runner, wellplan
from .engine import create_game
from .limits import Flight
from .pathaware import grid_columns, settle_columns
from .reach import GRID_ROWS

OUT = runner.PROJECT_ROOT / "experiments" / "035-20hz-search-probes"
GAMES = OUT / "games"
PARTIAL = runner.PROJECT_ROOT / "runs" / "035"
SEEDS = OUT / "seeds.json"
WIRING = OUT / "wiring_check.json"
TIMING = OUT / "d3_timing.json"
RESULTS = OUT / "results.json"
EARLY = OUT / "early_deaths.json"
SCHEMA = "fallgorithm.register.games/1"
FIRST_UNUSED, PROBE_SEEDS, D3_SEEDS = 14_200, 1_000, 500
NEVER = e28.NEVER
BASE, COMBINED = "base", "combined"
BASE_WEIGHTS = e34.BASE_WEIGHTS  # 033's chosen V29@20 (sweep 6)
# v29r20's search (033's _game): the deeper commit from 29, the adjust on the best 8 x 8 up
# to level 28, the second unknown piece from 29 with k 4, no third piece.
BASE_SEARCH: dict[str, Any] = {"commit_level": 29, "adjust_k": 8, "adjust_max_level": 28,
                               "deep2_level": 29, "deep2_k": 4, "deep3": None}
D3_ROOTS, D3_K, D3_K2 = 2, 2, 2
D3_FULL = [29, NEVER, D3_ROOTS, D3_K, D3_K2]  # from level 29 to the end
D3_CUT = [34, 38, D3_ROOTS, D3_K, D3_K2]      # predeclared.md: if d3 is slower than the limit
D3_LIMIT_SECONDS, D3_TIMING_GAMES = 900.0, 4
ARMS: dict[str, dict[str, Any]] = {
    "c18": {"commit_level": 18},
    "c18_d18": {"commit_level": 18, "deep2_level": 18},
    "adj12": {"adjust_k": 12},
    "d3": {"deep3": D3_FULL},
}
MIN_EFFECT = 15_000
SLOW_SECONDS = 300.0
RULE = ("An arm gains if its mean final score minus base's, paired by seed (95% bootstrap "
        "interval of experiment012.paired, 10,000 resamples, RNG seed 12), is +15,000 or more "
        "with the interval's lower end above 0. Screening only: no record is claimed.")
# the free look
EARLY_BELOW, HOLES_KEPT, DROUGHT_LONG, TALL, LAST_PIECES = 230, 3, 13, 12, 40

_load, _write = e13._load, e13._write


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- seeds

def make_seeds() -> dict[str, Any]:
    """029's training seeds after the slice 029-034 used (from index 14,200): 1,000 probe
    seeds (``d3`` plays the first 500)."""
    start = e34._seeds()["used_slice"][1]
    if start != FIRST_UNUSED:
        raise ValueError(f"034 used training seeds up to {start}, not {FIRST_UNUSED}")
    seeds = e29._seeds()["training_seeds"][start:start + PROBE_SEEDS]
    if len(seeds) < PROBE_SEEDS:
        raise ValueError(f"only {len(seeds)} unused training seeds, {PROBE_SEEDS} needed")
    result = {"selection": f"029's training seeds (029's seeds.json) from index {start} on "
                           f"(029-034 used 0-{start - 1}): 1,000 probe seeds; d3 plays the "
                           f"first {D3_SEEDS}",
              "used_slice": [start, start + PROBE_SEEDS], "probe_seeds": seeds}
    _write(SEEDS, result)
    return result


def _seeds() -> list[int]:
    stored = _load(SEEDS) if SEEDS.exists() else make_seeds()
    seeds = stored["probe_seeds"]
    if stored["used_slice"] != [FIRST_UNUSED, FIRST_UNUSED + PROBE_SEEDS] or \
            len(seeds) != PROBE_SEEDS or len(set(seeds)) != PROBE_SEEDS:
        raise ValueError(f"{SEEDS} is not the reserved slice of {PROBE_SEEDS} seeds")
    return seeds


def arm_seeds(arm: str) -> list[int]:
    return _seeds()[:D3_SEEDS] if arm == "d3" else _seeds()


# ---------------------------------------------------------------- settings

def base_search() -> dict[str, Any]:
    """``BASE_SEARCH``, checked against the constants 033's games were played with."""
    played = {"commit_level": e28.COMMIT_LEVEL, "adjust_k": e28.ADJUST_K,
              "adjust_max_level": e28.ADJUST_MAX_LEVEL, "deep2_level": e28.DEEP2_LEVEL,
              "deep2_k": e28.DEEP2_K, "deep3": None}
    if played != BASE_SEARCH:
        raise ValueError(f"v29r20's search is {played}, not {BASE_SEARCH}")
    return dict(BASE_SEARCH)


def d3_setting() -> list[int]:
    """``d3``'s third-piece setting as ``time-d3`` decided it (predeclared.md)."""
    if not TIMING.exists():
        raise ValueError(f"{TIMING} is missing: run time-d3 first")
    setting = _load(TIMING)["deep3"]
    if setting not in (D3_FULL, D3_CUT):
        raise ValueError(f"{TIMING} names another d3 setting: {setting}")
    return setting


def changes(arm: str) -> dict[str, Any]:
    """What ``arm`` changes in the base search."""
    if arm == BASE:
        return {}
    if arm == COMBINED:
        return decision()["combined_changes"] or {}
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    return {"deep3": d3_setting()} if arm == "d3" else dict(ARMS[arm])


def search_of(arm: str) -> dict[str, Any]:
    return base_search() | changes(arm)


def combine_changes(gaining: dict[str, float]) -> dict[str, Any] | None:
    """predeclared.md: the combined setting takes every gaining arm (``gaining``: arm ->
    paired mean); of ``c18`` and ``c18_d18`` only the one with the higher mean (``c18`` on a
    tie). None unless two or more arms are left to combine."""
    chosen = dict(gaining)
    if "c18" in chosen and "c18_d18" in chosen:
        del chosen["c18_d18" if chosen["c18"] >= chosen["c18_d18"] else "c18"]
    if len(chosen) < 2:
        return None
    merged: dict[str, Any] = {}
    for arm in ARMS:  # a fixed order; the arms left never set the same key
        if arm in chosen:
            for key, value in changes(arm).items():
                if key in merged:
                    raise ValueError(f"two arms set {key}")
                merged[key] = value
    return merged


# ---------------------------------------------------------------- games

def _game(seed: int, search: dict[str, Any]) -> dict[str, Any]:
    """033's ``_game`` (v29r20's networks, the 20 Hz format, the tap-spacing check) with
    ``search`` as the native search's setting. ``deep3`` None is fn_late_hybrid_game, the
    function 033 played with."""
    frozen, net = e33._frozen()
    deep3 = search["deep3"]
    played, _ = native.late_hybrid_game(
        net, frozen["game"], seed, late=e33.v39r_late_path().read_bytes(),
        late_from_lines=e33.LATE_FROM, mid=e34.base_path().read_bytes(),
        mid_from_lines=e33.MID_FROM, commit_level=search["commit_level"],
        adjust_k=search["adjust_k"], adjust_max_level=search["adjust_max_level"],
        deep2_level=search["deep2_level"], deep2_k=search["deep2_k"], switch_level=NEVER,
        line_cap=frozen["line_cap"], frame_cap=frozen["frame_cap"],
        limits=e13._limits(frozen), params=native.params(frozen["params"]),
        deep3=None if deep3 is None else tuple(deep3))
    e33.check_tap_spacing(played["inputs"], e13._limits(frozen).tap_interval)
    return played


def play_game(job: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    """One checked game (register.checked_game and the 20 Hz tap-spacing check)."""
    arm, seed, search = job
    return e33.checked_game(e33._frozen()[0], seed, lambda: _game(seed, search), agent=arm)


def games_path(arm: str) -> Path:
    return GAMES / f"{arm}.json.gz"


def load_games(arm: str) -> dict[str, Any]:
    path = games_path(arm)
    if not path.exists():
        raise ValueError(f"{path} is missing: play {arm} first")
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        record = json.load(handle)
    if [e["seed"] for e in record["episodes"]] != arm_seeds(arm):
        raise ValueError(f"{path} does not cover exactly {arm}'s seeds in order")
    return record


def library_record() -> dict[str, Any]:
    path = native.library_path()
    return {"path": str(path), "sha256": _sha(path), "abi_version": native.ABI_VERSION}


def _require_clean() -> None:
    found = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", f":!{OUT.relative_to(runner.PROJECT_ROOT)}"],
        cwd=runner.PROJECT_ROOT, capture_output=True, text=True, check=True).stdout
    if found.strip():
        raise ValueError(f"the git tree is dirty outside {OUT.name}: commit before playing")


def _require_ready() -> None:
    """A clean tree outside the experiment, the plan, protocol and seeds committed, and the
    wiring check matched on this very library."""
    _require_clean()
    e34._require_committed(OUT / "plan.md", OUT / "predeclared.md", SEEDS)
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("library") != library_record():
        raise ValueError(f"{WIRING} is missing or not matched on this library: run check")


def prefix_check(mine: list[dict[str, Any]], base: list[dict[str, Any]]) -> dict[str, Any]:
    """Every seed: the arm's inputs equal ``base``'s before the base game first has 230
    lines (the whole game if it never does). ``d3`` changes nothing below level 29."""
    frozen = e33._frozen()[0]
    by_seed = {e["seed"]: e for e in base}
    bad = [e["seed"] for e in mine
           if not e34.prefix_matches(frozen, e["seed"],
                                     base64.b64decode(by_seed[e["seed"]]["inputs"]),
                                     base64.b64decode(e["inputs"]))]
    return {"games": len(mine), "matched": len(mine) - len(bad), "mismatched_seeds": bad}


def play(arm: str, jobs: int) -> Path:
    """Play ``arm`` on its seeds (resuming from the partial file) and store the games.
    ``base`` first; ``d3`` must pass the prefix check against it."""
    if arm not in (BASE, COMBINED, *ARMS):
        raise ValueError(f"unknown arm {arm!r}")
    target = games_path(arm)
    if target.exists():
        return target
    _require_ready()
    if arm != BASE:
        load_games(BASE)
    search, seeds = search_of(arm), arm_seeds(arm)
    versions, library = runner._record_versions(), library_record()
    fmt = e33.format_of(e33._frozen()[0])
    header = {"header": {"arm": arm, "search": search, "format": fmt,
                         "weights_sha256": _sha(e34.base_path()),
                         "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                         "library": library, "versions": versions}}
    PARTIAL.mkdir(parents=True, exist_ok=True)
    partial = PARTIAL / f"{arm}.partial.jsonl"
    done = e25._resume(partial, header)
    todo = [(arm, seed, search) for seed in seeds if seed not in done]
    print(f"{arm}: {len(done)} games already done, {len(todo)} to play", flush=True)
    tick = time.perf_counter()
    base = load_games(BASE)["episodes"] if arm == "d3" else []
    with partial.open("a", encoding="utf-8") as handle, Pool(jobs) as pool:
        for episode in pool.imap_unordered(play_game, todo, chunksize=1):
            handle.write(json.dumps(episode, separators=(",", ":")) + "\n")
            handle.flush()
            done[episode["seed"]] = episode
            if arm == "d3" and prefix_check([episode], base)["mismatched_seeds"]:
                raise ValueError(f"d3 differs from base before 230 lines on seed "
                                 f"{episode['seed']}: stopped (the games stay in {partial})")
            if len(done) % 20 == 0 or len(done) == len(seeds):
                mean = sum(e["result"]["score"] for e in done.values()) / len(done)
                print(f"{arm} {len(done)}/{len(seeds)} {mean:,.0f}", flush=True)
    episodes = [done[seed] for seed in seeds]
    record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "versions": versions, "library": library, "arm": arm, "search": search,
              "format": fmt, "weights": BASE_WEIGHTS, "weights_sha256": _sha(e34.base_path()),
              "seeds": seeds, "wall_seconds": round(time.perf_counter() - tick, 1),
              "episodes": episodes}
    if arm == "d3":
        record["prefix_check"] = prefix_check(episodes, base)
        if record["prefix_check"]["mismatched_seeds"]:
            raise ValueError(f"d3 differs from base before 230 lines on seeds "
                             f"{record['prefix_check']['mismatched_seeds'][:5]}: stopped "
                             f"(the games stay in {partial})")
    GAMES.mkdir(parents=True, exist_ok=True)
    staged = PARTIAL / target.name
    with gzip.open(staged, "wt", encoding="utf-8") as out:
        json.dump(record, out, separators=(",", ":"))
    staged.replace(target)
    partial.unlink()
    return target


# ---------------------------------------------------------------- d3's timing

def time_d3() -> dict[str, Any]:
    """predeclared.md: ``d3`` (third piece from level 29) on the first 4 seeds, 4 games at
    once; over 15 minutes a game on average, the third piece runs at levels 34-38 only."""
    if TIMING.exists():
        return _load(TIMING)
    _require_ready()
    seeds = _seeds()[:D3_TIMING_GAMES]
    search = base_search() | {"deep3": D3_FULL}
    with Pool(D3_TIMING_GAMES) as pool:
        played = pool.map(play_game, [("d3", seed, search) for seed in seeds], chunksize=1)
    seconds = [e["result"]["decision_seconds"] for e in played]
    mean = sum(seconds) / len(seconds)
    cut = mean > D3_LIMIT_SECONDS
    result = {"experiment": OUT.name, "seeds": seeds, "search": search,
              "seconds": seconds, "mean_seconds": round(mean, 1),
              "limit_seconds": D3_LIMIT_SECONDS, "cut_to_levels_34_38": cut,
              "deep3": D3_CUT if cut else D3_FULL,
              "scores": [e["result"]["score"] for e in played],
              "library": library_record(), "versions": runner._record_versions()}
    _write(TIMING, result)
    return result


# ---------------------------------------------------------------- summaries

def band_stats(episodes: list[dict[str, Any]], low: int, high: int,
               from_lines: int) -> dict[str, Any]:
    """Per game with ``from_lines`` lines or more: lines, Tetrises and singles cleared at
    levels ``low`` to ``high``, and the share of those lines cleared by Tetrises."""
    reached = [e for e in episodes if e["result"]["lines"] >= from_lines]
    totals = {"four_line": 0, "triple": 0, "double": 0, "single": 0}
    for e in reached:
        for level, v in e["stats"]["by_level"].items():
            if low <= int(level) <= high:
                for key in totals:
                    totals[key] += v[key]
    n = max(1, len(reached))
    lines = 4 * totals["four_line"] + 3 * totals["triple"] + 2 * totals["double"] + \
        totals["single"]
    return {"games": len(reached), "lines": round(lines / n, 2),
            "tetrises": round(totals["four_line"] / n, 3),
            "singles": round(totals["single"] / n, 2),
            "tetris_line_share": round(4 * totals["four_line"] / max(1, lines), 4)}


def style(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """predeclared.md's reported figures: points by band, P(130), P(230), P(320), deaths by
    10-line step, Tetrises / singles / Tetris share by band, the boards at 29's and 39's
    entry, seconds a game."""
    s = e25._summary(episodes)
    n = len(episodes)
    lines = [e["result"]["lines"] for e in episodes]
    deaths: dict[str, int] = {}
    for x in sorted(lines):
        key = f"{x // 10 * 10}-{x // 10 * 10 + 9}"
        deaths[key] = deaths.get(key, 0) + 1
    return {"games": n, "mean_score": s["mean_score"], "mean_lines": s["mean_lines"],
            "median_lines": s["median_lines"],
            "points_by_band": {band: round(sum(e["stats"]["bands"].get(band, 0)
                                               for e in episodes) / n, 1)
                               for band in ("18", "19-28", "29-38", "39+")},
            "p_reach_130": sum(x >= 130 for x in lines) / n,
            "p_reach_230": sum(x >= e33.MID_FROM for x in lines) / n,
            "p_reach_320": sum(x >= e33.LATE_FROM for x in lines) / n,
            "p_reach_39": s["p_reach_39"],
            "deaths_by_10_lines": deaths,
            "band_18": band_stats(episodes, 18, 18, 0),
            "band_19_28": band_stats(episodes, 19, 28, 130),
            "band_29_38": band_stats(episodes, 29, 38, e33.MID_FROM),
            "entry_29": s["entry_29"], "entry_39": s["entry_39"],
            "seconds_per_game": s["seconds_per_game"]}


def gains(paired: dict[str, Any]) -> bool:
    score = paired["total"]["score"]
    return bool(score["mean"] >= MIN_EFFECT and score["ci95_low"] > 0)


def compare(arm: str, base_record: dict[str, Any]) -> dict[str, Any]:
    """``arm``'s stored games against the base's on the arm's seeds. The arm must have been
    played on the base's library and (the combined setting is checked by ``summarize``) with
    the arm's current setting."""
    record = load_games(arm)
    if record["library"] != base_record["library"]:
        raise ValueError(f"{arm} and base were played on different native libraries")
    if arm != COMBINED and record["search"] != search_of(arm):
        raise ValueError(f"{arm}'s stored games were played with another setting")
    episodes, base = record["episodes"], base_record["episodes"]
    by_seed = {e["seed"]: e for e in base}
    paired = e25._paired(episodes, [by_seed[e["seed"]] for e in episodes])
    result = {"search": record["search"], "changes": {k: v for k, v in record["search"].items()
                                                      if BASE_SEARCH[k] != v},
              "style": style(episodes), "paired_vs_base": paired, "gains": gains(paired),
              "library": record["library"], "versions": record["versions"]}
    if arm == "d3":
        result["base_style_same_seeds"] = style([by_seed[e["seed"]] for e in episodes])
        result["prefix_check"] = record["prefix_check"]
    return result


def summarize() -> dict[str, Any]:
    """results.json: base's figures, every played arm against it, and (once all four arms
    are played) which arms gain, what the combined setting is, and 036's search."""
    base = load_games(BASE)
    arms = {arm: compare(arm, base) for arm in ARMS if games_path(arm).exists()}
    result: dict[str, Any] = {
        "experiment": OUT.name, "rule": RULE, "format": base["format"],
        "weights": BASE_WEIGHTS, "seeds": {"all": len(_seeds()), "d3": D3_SEEDS},
        "base": {"search": base["search"], "style": style(base["episodes"]),
                 "library": base["library"], "versions": base["versions"]},
        "arms": arms}
    if TIMING.exists():
        result["d3_timing"] = {k: _load(TIMING)[k] for k in
                               ("mean_seconds", "cut_to_levels_34_38", "deep3")}
    if len(arms) == len(ARMS):
        gaining = {arm: found["paired_vs_base"]["total"]["score"]["mean"]
                   for arm, found in arms.items() if found["gains"]}
        merged = combine_changes(gaining)
        result["gaining"] = gaining
        result["combined_changes"] = merged
        chosen: str | None = None
        if merged is None:
            chosen = max(gaining, key=gaining.get) if gaining else BASE
        elif games_path(COMBINED).exists():
            found = compare(COMBINED, base)
            if found["changes"] != merged:
                raise ValueError("the combined games were played with another setting")
            result["combined"] = found
            chosen = COMBINED if found["gains"] else max(gaining, key=gaining.get)
        if chosen is not None:
            search = base["search"] if chosen == BASE else \
                (result["combined"] if chosen == COMBINED else arms[chosen])["search"]
            seconds = (result["base"] if chosen == BASE else result["combined"]
                       if chosen == COMBINED else arms[chosen])["style"]["seconds_per_game"]
            result["search_for_036"] = {
                "arm": chosen, "search": search, "seconds_per_game": seconds,
                "float32_speed_up_first": bool(seconds > SLOW_SECONDS)}
    _write(RESULTS, result)
    return result


def decision() -> dict[str, Any]:
    """results.json once all four arms are in it."""
    result = _load(RESULTS) if RESULTS.exists() else {}
    if "combined_changes" not in result:
        raise ValueError(f"{RESULTS} has no decision yet: play every arm and summarize")
    return result


def combine(jobs: int) -> dict[str, Any]:
    """predeclared.md: with two or more gaining arms, their combined setting on all 1,000
    seeds; otherwise no game."""
    result = summarize()
    if "combined_changes" not in result:
        raise ValueError("not every arm is played yet")
    if result["combined_changes"] is not None:
        play(COMBINED, jobs)
        result = summarize()
    return result


# ---------------------------------------------------------------- wiring

def _stored_screening() -> list[dict[str, Any]]:
    """033's stored v29r20 screening games."""
    return e34._stored_base("screening")


def _rerun_job(job: tuple[int, dict[str, Any]]) -> bytes:
    seed, search = job
    return _game(seed, search)["inputs"]


def wiring_check(jobs: int) -> dict[str, Any]:
    """The first 3 stored v29r20 screening games re-run on this library with every arm off,
    input for input: through fn_late_hybrid_game (``deep3`` None) and through fn_deep3_game
    with 0 roots; and ``d3``'s setting on the first of them (a game past 230 lines) leaves the
    inputs before 230 lines alone and changes the game after, so the setting reaches the
    native search."""
    stored = _stored_screening()[:3]
    frozen = e33._frozen()[0]
    off = base_search()
    zero = off | {"deep3": [0, 0, 0, 0, 0]}
    work = [(e["seed"], s) for s in (off, zero) for e in stored]
    work.append((stored[0]["seed"], off | {"deep3": D3_FULL}))
    with Pool(jobs) as pool:
        played = pool.map(_rerun_job, work, chunksize=1)
    want = [base64.b64decode(e["inputs"]) for e in stored]
    part = {name: [e["seed"] for e, got, w in zip(stored, played[i:i + 3], want) if got != w]
            for name, i in (("late_hybrid_game", 0), ("deep3_game_0_roots", 3))}
    d3 = {"seed": stored[0]["seed"],
          "prefix_before_230_matches": e34.prefix_matches(frozen, stored[0]["seed"], want[0],
                                                          played[6]),
          "differs_after": played[6] != want[0]}
    result = {"experiment": OUT.name, "format": e33.format_of(frozen), "games": 3,
              "search": off, "mismatched_seeds": part, "d3_on_one_game": d3,
              "matched": bool(not part["late_hybrid_game"] and not part["deep3_game_0_roots"]
                              and d3["prefix_before_230_matches"] and d3["differs_after"]),
              "library": library_record(), "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


# ---------------------------------------------------------------- the free look

def _heights(columns: tuple[int, ...]) -> list[int]:
    return [0 if not bits else GRID_ROWS - ((bits & -bits).bit_length() - 1) for bits in columns]


def _holes(columns: tuple[int, ...]) -> int:
    return sum(height - bin(bits).count("1") for height, bits in zip(_heights(columns), columns))


def _options(columns: tuple[int, ...], piece: str, level: int, ruleset: str,
             interval: int) -> list[tuple[int, int]]:
    """Every placement from the spawn at tap ``interval``: (the stack's height under the
    piece afterwards, 0 if it clears a line; the lines it clears)."""
    period, rows = native.gravity(level, ruleset)
    before, found = _heights(columns), []
    for orientation, x, y, _ in native.reachable(columns, piece, Flight(), period=period,
                                                 rows=rows, interval=interval):
        settled, cleared = settle_columns(columns, piece, orientation, x, y)
        after = _heights(settled)
        found.append((0 if cleared else max((b for a, b in zip(before, after) if a != b),
                                            default=0), cleared))
    return found


def classify(spawns: list[dict[str, Any]]) -> dict[str, Any]:
    """One game's class from its piece spawns (each: holes, max_height, drought, level,
    lines). The hole event is the last spawn at which the board has ``HOLES_KEPT`` holes or
    fewer: the piece placed there leaves holes that are never dug out again. ``i_drought``
    if no I had come for ``DROUGHT_LONG`` pieces or more by then; else ``tall_stack`` if the
    stack was ``TALL`` rows or more; else ``low_hole``."""
    clean = [i for i, s in enumerate(spawns) if s["holes"] <= HOLES_KEPT]
    at = clean[-1] if clean else 0
    event = spawns[at]
    end = at
    while end + 1 < len(spawns) and spawns[end + 1]["drought"] > spawns[end]["drought"]:
        end += 1
    kind = "i_drought" if event["drought"] >= DROUGHT_LONG else \
        "tall_stack" if event["max_height"] >= TALL else "low_hole"
    return {"class": kind, "pieces_from_event_to_end": len(spawns) - at,
            "event": {k: event[k] for k in ("lines", "level", "drought", "max_height", "holes")},
            "drought_when_it_ended": spawns[end]["drought"]}


def _early_job(job: tuple[int, bytes]) -> dict[str, Any]:
    """Replay one stored game: its spawns, its class, and on its last ``LAST_PIECES``
    pieces what 20 Hz reach (tap interval 3) could not do that a tap every frame could."""
    seed, inputs = job
    frozen = e33._frozen()[0]
    ruleset = frozen["game"]["ruleset"]
    spawns, count = [], -1
    with create_game(**frozen["game"], seed=seed) as game:
        state = game.state
        for mask in inputs:
            if state.phase == "active" and state.piece_count != count:
                count = state.piece_count
                columns = grid_columns(wellplan.visible_grid(state.board))
                spawns.append({"lines": state.lines, "level": state.level,
                               "piece": state.current_piece, "columns": columns,
                               "holes": _holes(columns), "max_height": max(_heights(columns)),
                               "drought": state.stats.current_i_drought})
            state, _ = game.step(mask)
        final = {"lines": state.lines, "level": state.level}
    blocked = i_blocked = 0
    for s in spawns[-LAST_PIECES:]:
        slow = _options(s["columns"], s["piece"], s["level"], ruleset, e33.TAP_INTERVAL)
        fast = _options(s["columns"], s["piece"], s["level"], ruleset, 1)
        if fast and max(c for _, c in fast) >= 1 and max((c for _, c in slow), default=0) == 0:
            blocked += 1
            i_blocked += s["piece"] == "I"
    return {"seed": seed, **final, "pieces": len(spawns)} | classify(spawns) | {
        "last_pieces_a_clear_out_of_20hz_reach": blocked,
        "of_which_i_pieces": i_blocked}


def freelook(jobs: int) -> dict[str, Any]:
    """predeclared.md's free look: 033's stored held-out v29r20 games that end before 230
    lines, by how they end. No game is played."""
    with gzip.open(e33.OUT / "games" / "heldout-v29r20.json.gz", "rt",
                   encoding="utf-8") as handle:
        episodes = json.load(handle)["episodes"]
    early = [e for e in episodes if e["result"]["lines"] < EARLY_BELOW]
    with Pool(jobs) as pool:
        games = pool.map(_early_job, [(e["seed"], base64.b64decode(e["inputs"])) for e in early],
                         chunksize=1)
    table = {}
    for kind in ("i_drought", "tall_stack", "low_hole"):
        g = [x for x in games if x["class"] == kind]
        if not g:
            table[kind] = {"games": 0}
            continue
        table[kind] = {
            "games": len(g), "share": round(len(g) / len(games), 3),
            "ended_at_level_18": sum(x["level"] == 18 for x in g),
            "ended_at_levels_19_28": sum(x["level"] > 18 for x in g),
            "median_pieces_from_event_to_end":
                statistics.median(x["pieces_from_event_to_end"] for x in g),
            "mean_drought_at_event": round(statistics.mean(x["event"]["drought"] for x in g), 1),
            "mean_drought_when_it_ended":
                round(statistics.mean(x["drought_when_it_ended"] for x in g), 1),
            "mean_max_height_at_event":
                round(statistics.mean(x["event"]["max_height"] for x in g), 1),
            "games_with_a_clear_out_of_reach":
                sum(x["last_pieces_a_clear_out_of_20hz_reach"] > 0 for x in g),
            "games_with_an_i_clear_out_of_reach": sum(x["of_which_i_pieces"] > 0 for x in g)}
    result = {"experiment": OUT.name,
              "source": "experiments/033-v29-20hz/games/heldout-v29r20.json.gz",
              "games": len(episodes), "ending_before_230_lines": len(games),
              "rule": " ".join(classify.__doc__.split()), "holes_kept": HOLES_KEPT, "drought_long": DROUGHT_LONG,
              "tall": TALL, "last_pieces": LAST_PIECES, "classes": table,
              "by_game": sorted(games, key=lambda x: x["lines"])}
    _write(EARLY, result)
    return result


# ---------------------------------------------------------------- command line

def _line(arm: str, found: dict[str, Any]) -> str:
    score = found["paired_vs_base"]["total"]["score"]
    return (f"{arm}: {score['mean']:+,.0f} ({score['ci95_low']:+,.0f}, "
            f"{score['ci95_high']:+,.0f}) gains {found['gains']}; "
            f"{found['style']['seconds_per_game']:.0f} s a game")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment035")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("freelook", help="classify 033's early held-out deaths (no games)")
    commands.add_parser("check", help="the wiring check")
    player = commands.add_parser("play", help="play one arm on its seeds")
    player.add_argument("arm", choices=(BASE, *ARMS))
    commands.add_parser("time-d3", help="time d3 on 4 seeds and fix its levels")
    commands.add_parser("combine", help="play the combined setting if two or more arms gain")
    commands.add_parser("summarize", help="write results.json")
    for name, sub in commands.choices.items():
        if name not in ("time-d3", "summarize"):
            sub.add_argument("--jobs", type=int, default=28)
    args = parser.parse_args(argv)
    try:
        if args.command == "freelook":
            found = freelook(args.jobs)
            print(json.dumps(found["classes"], indent=1))
        elif args.command == "check":
            found = wiring_check(args.jobs)
            print(f"Wrote {WIRING}: matched {found['matched']}")
            return 0 if found["matched"] else 1
        elif args.command == "play":
            play(args.arm, args.jobs)
            result = summarize()
            if args.arm == BASE:
                print(f"base: {result['base']['style']['mean_score']:,.0f}")
            else:
                print(_line(args.arm, result["arms"][args.arm]))
        elif args.command == "time-d3":
            found = time_d3()
            print(f"d3: {found['mean_seconds']:.0f} s a game; setting {found['deep3']}")
        else:
            result = combine(args.jobs) if args.command == "combine" else summarize()
            for arm, found in result["arms"].items():
                print(_line(arm, found))
            if "combined" in result:
                print(_line(COMBINED, result["combined"]))
            print(json.dumps(result.get("search_for_036")))
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Run bounded episodes and replay exactly the inputs that were executed.

Six record versions share this module and all replay against the native engine.
Versions 1 (one scripted episode) and 2 (a suite of placement-agent episodes over
fixed seeds) are the older formats of each shape: the verifier accepts the
placed-piece count, the clear-size histogram and the declared objective absent
there and compares each one when present. Versions 3 (a
scripted episode), 4, 5 and 6 (suites) are written after them and must carry every
section their writer emits — the placed-piece count, the clear-size histogram,
and, for a suite that uses the Tetris agent, that agent's declared objective.
Version 4's writer recorded that objective without the source identity its
successor adds, so version 4 records require everything except the identity;
version 5's writer recorded the identity as the modules the objective's own code
reaches, which cannot include the agent wrapper that drives it, and version 6
records the wrapper beside them. The numbers are reused rather than a schema
history — the base commit's writer emitted the placed-piece count at versions 1
and 2, and an earlier writer wrote the same numbers without it — so a version
says which sections the verifier must require: a legacy version's may be absent
and are compared when present, and only the current version's must be present.

The version is the marker that makes the two cases distinguishable, because
absence alone cannot tell a record that predates a section from a current record
whose section was deleted after it was written: both are the same JSON, and
accepting the second means a record keeps verifying under a schema weaker than
the one it was written with — no metric, and no way to tell. The replay requires
the recorded inputs and compares them alongside the recorded initial state hash
and every ``result`` field. Both verifiers compare a recorded value only after
its type — and, for mappings, its keys — equals the replayed value's, so JSON
booleans, which compare equal to ``0``/``1`` and ``0.0``, are rejected instead of
verifying.

The piece count is ``pieces_placed``: the number of pieces the engine actually
wrote to the board. It is counted from the engine's ``locked`` events minus the
failed lock that ends an endless game: ``Game::lock`` raises ``locked`` before
its ``fits`` check and only writes the board when the piece fits, so the
topping-out lock places nothing. A piece still in play at a frame-limit stop has
not locked and is not counted either, and the RNG/preview selection counter
``state.piece_count`` is always above the count. Records written before that
field existed carry the legacy ``pieces`` key instead, which held
``state.piece_count``; the replay compares it against that counter so those
records keep verifying under their original semantics. A record that carries
neither key is older still and keeps verifying at a legacy version; a version 3,
4, 5 or 6 record must carry ``pieces_placed``, because that is the key its writer
emits and its absence there is a deleted section rather than an older record. The
per-agent summary reports the key the record as a whole carries, read from every
episode: one writer emits one shape for a whole record, so a record whose first
episode lost the key while the later ones kept it is reported instead of being
summarised without the metric its own episodes carry.

The clear-size histogram is ``clear_sizes``: per episode, how many locks cleared
one, two, three and four rows, tallied from the engine's own per-step
``lines_cleared`` event (the same event ``result.event_counts`` sums, so the
sizes add up to that total). It is a top-level per-episode field beside
``pieces_placed``, never a leaf inside ``result``: ``_compare_fields`` requires
a ``result`` object's keys to equal the replay's exactly, so a new key there
would invalidate every record written before it. Like the piece count a legacy
record may omit it — a record that carries neither the field nor the entry in its
summary is older and keeps verifying — and a present one is compared with the
same type-and-key rules as the mandatory sections. In a version 3, 4, 5 or 6
record the histogram is required: a scripted episode carries it, and a suite
carries it on every episode and every agent summary. Presence is all-or-nothing
in a legacy suite too: every episode and every agent summary in one record
carries the histogram, or a record older than the metric carries it nowhere. A
per-agent rule would accept a record that stripped the histogram from one agent
while another kept it, and such a record verifies while reporting a fraction of
the lines it cleared. The per-agent totals are derived from the episodes rather
than assumed: ``_summarize`` reports the section exactly when the episodes it
summarises carry it, so a legacy record's summary re-derives without it and
matches the summary that record already carries, which Experiment 002's own
replay probe compares directly.

A suite that uses the Tetris agent records that agent's declared objective as
``objective``: the module that declares it, the mapping its ``weights_record()``
returns and the source identity of the modules the objective's decisions are
computed from, mirroring the ``heuristic`` section beside it. The frozen
heuristic mapping is written for every suite because every placement agent scores
through it, and the Tetris agent's choices come from a second, separately
declared objective instead; without the section a tetris suite verifies under
whatever objective is current whenever the change happens to preserve its
replayed choices. The identity closes the case the weights cannot: they are
constants, so a formula change that leaves them alone changes every value the
objective computes while the weights still compare equal, and the recorded
choices only catch it when the change happens to move one of them. A version 5
or 6 suite that uses the agent must carry the identity, because its writer always
emits it; the version 4 writer emitted the objective without it and the
version 2 writer emitted no objective at all, so those records keep verifying —
the runs of this experiment written by both writers do — and a present identity
is compared with the same type-and-key rules in every case. The identity names
every module whose code produces a choice, the agent wrapper that hands the
objective its state included: the wrapper imports the objective rather than the
other way round, so an identity walked outward from the objective alone could not
reach it, and a wrapper change that kept the replayed choices was certified. A
version 5 record is compared against that older shape, which is the identity its
writer recorded.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import fmean, median
import sys
from types import ModuleType
from typing import Any, Callable
from uuid import uuid4

from . import tetris
from .agents import (
    AGENT_NAMES, TETRIS_AGENT, ScriptedAgent, Segment, create_agent, parse_script,
)
from .engine import PROJECT_ROOT, create_game, engine_root, git_info
from .heuristic import weights_record
from .sourceidentity import loaded_source_digest


LEGACY_FORMAT_VERSION = 1  # a scripted episode written before the new sections
FORMAT_VERSION = 3  # a scripted episode, which always records its sections
LEGACY_SUITE_FORMAT_VERSION = 2  # a suite written before the new sections
# A suite written after the sections and before the objective's source identity:
# its writer recorded the objective's module and weights, which do not identify
# the objective's formula. Superseded by SUITE_FORMAT_VERSION.
PRIOR_SUITE_FORMAT_VERSION = 4
# A suite written while the identity was walked outward from the module that
# declares the objective. The agent wrapper that drives the objective imports it,
# so that walk cannot reach the wrapper — the dependency runs the other way — and
# a wrapper change that preserved the replayed choices was certified. Superseded
# by SUITE_FORMAT_VERSION.
OUTWARD_IDENTITY_SUITE_FORMAT_VERSION = 5
SUITE_FORMAT_VERSION = 6  # a suite, which always records the sections and the identity
# The two shapes the objective's source identity has been written in, named for
# the walk that produces it. ``_IDENTITY_OUTWARD`` is the modules the module that
# declares the objective reaches: itself, and the package modules its own code
# calls. ``_IDENTITY_CHOICE`` adds the agent wrapper that produces the choices —
# the class whose ``_choose`` hands the objective its state and the factory that
# selects it — because the wrapper imports the objective, so no walk outward from
# the objective can reach it.
_IDENTITY_OUTWARD = "outward"
_IDENTITY_CHOICE = "choice"
# What each suite version's own writer always emitted, as ``(sections,
# identity)``: the placed-piece count, the clear-size histogram and the declared
# objective, then the objective's source identity inside that objective. Inferring
# "legacy" from an absent section instead would accept a current record whose
# section was deleted, because a stripped record and a pre-section record are the
# same JSON. The prior version stays strict about everything its writer did emit —
# its records carry the objective, so its verifier still requires it — and gates
# only the identity, which its writer never recorded. The identity is the newer
# of the two: a version whose writer emitted the sections therefore also requires
# the ones that preceded it. The identity's second element names which modules
# that version's identity covered, or ``None`` for a version whose writer emitted
# none — an identity such a record carries anyway is an edit, and is compared
# against the current shape, because no writer ever emitted another one there.
_SUITE_FORMAT_VERSIONS = {
    LEGACY_SUITE_FORMAT_VERSION: (False, None),
    PRIOR_SUITE_FORMAT_VERSION: (True, None),
    OUTWARD_IDENTITY_SUITE_FORMAT_VERSION: (True, _IDENTITY_OUTWARD),
    SUITE_FORMAT_VERSION: (True, _IDENTITY_CHOICE),
}
_SCRIPTED_FORMAT_VERSIONS = {LEGACY_FORMAT_VERSION: False, FORMAT_VERSION: True}
_EVENT_FIELDS = (
    "moved", "rotated", "locked", "spawned", "gravity_drop", "soft_drop",
    "game_over", "challenge_completed", "lines_cleared", "score_delta",
)
# One histogram field per number of rows a single lock can clear, so index
# ``size - 1`` is that size. The engine clears between zero and four rows in a
# lock, which the binding reports in the step's ``lines_cleared`` event.
_CLEAR_SIZE_FIELDS = ("singles", "doubles", "triples", "tetrises")
_CLEAR_SIZES_FIELD = "clear_sizes"
# The piece count in the two forms a record can carry: the placed-piece count
# every current writer emits, and the legacy ``pieces`` key, which held the
# engine's RNG/preview selection counter. Which one a record carries is a
# property of its writer, so it is read from the record rather than guessed from
# one episode.
_PIECES_PLACED_FIELD = "pieces_placed"
_LEGACY_PIECES_FIELD = "pieces"
_PIECE_FIELDS = (_PIECES_PLACED_FIELD, _LEGACY_PIECES_FIELD)
# The declared objective of the one agent that does not score through the frozen
# heuristic mapping. The section names the module that declares it, so the
# mapping cannot be read as the heuristic's own.
_OBJECTIVE_FIELD = "objective"
# The objective's semantic identity, beside its weights: the sha256 of the source
# of every package module its decisions are computed from. The weights are
# constants and cannot identify the formula around them, so without this a record
# kept verifying under an objective whose formula changed whenever the replayed
# choices happened to be preserved.
_OBJECTIVE_SOURCES_FIELD = "sources"
# Every package module belongs to this namespace; the objective's modules are
# discovered from its own namespace rather than hand-listed.
_PACKAGE_PREFIX = f"{__package__}."


class VerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunConfig:
    game: dict[str, Any]
    frame_limit: int
    script: tuple[Segment, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game": self.game.copy(),
            "frame_limit": self.frame_limit,
            "script": [asdict(segment) for segment in self.script],
        }


@dataclass(frozen=True)
class SuiteConfig:
    """Fixed game settings, frame bound, seeds and agents of one comparison."""

    game: dict[str, Any]
    frame_limit: int
    seeds: tuple[int, ...]
    agents: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game": self.game.copy(),
            "frame_limit": self.frame_limit,
            "seeds": list(self.seeds),
            "agents": list(self.agents),
        }


Config = RunConfig | SuiteConfig


def _parse_game(value: Any, *, with_seed: bool) -> dict[str, Any]:
    keys = {"ruleset", "mode", "start_level", "height"} | ({"seed"} if with_seed else set())
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"game must contain exactly {', '.join(sorted(keys))}")
    if value["ruleset"] not in ("classic_ntsc_strict", "classic_ntsc_extended"):
        raise ValueError("game.ruleset must be a supported Block Stack ruleset")
    if value["mode"] not in ("endless", "challenge"):
        raise ValueError("game.mode must be endless or challenge")
    for name, minimum, maximum in (("start_level", 0, 19), ("height", 0, 5), ("seed", 0, 65535)):
        if name not in keys:
            continue
        item = value[name]
        if type(item) is not int or not minimum <= item <= maximum:
            raise ValueError(f"game.{name} must be an integer from {minimum} to {maximum}")
    return value.copy()


def _parse_frame_limit(value: Any) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError("frame_limit must be a positive integer")
    return value


def _parse_script_config(value: dict[str, Any]) -> RunConfig:
    return RunConfig(_parse_game(value["game"], with_seed=True),
                     _parse_frame_limit(value["frame_limit"]), parse_script(value["script"]))


def _parse_suite_config(value: dict[str, Any]) -> SuiteConfig:
    seeds = value["seeds"]
    if not isinstance(seeds, list) or not seeds:
        raise ValueError("seeds must be a nonempty list of 16-bit integers")
    for seed in seeds:
        if type(seed) is not int or not 0 <= seed <= 65535:
            raise ValueError("every seed must be an integer from 0 to 65535")
    agents = value["agents"]
    if not isinstance(agents, list) or not agents:
        raise ValueError("agents must be a nonempty list of agent names")
    for agent in agents:
        if agent not in AGENT_NAMES:
            raise ValueError(f"agents must be chosen from {', '.join(AGENT_NAMES)}")
    return SuiteConfig(_parse_game(value["game"], with_seed=False),
                       _parse_frame_limit(value["frame_limit"]), tuple(seeds), tuple(agents))


def parse_config(value: Any) -> Config:
    if isinstance(value, dict) and set(value) == {"game", "frame_limit", "script"}:
        return _parse_script_config(value)
    if isinstance(value, dict) and set(value) == {"game", "frame_limit", "seeds", "agents"}:
        return _parse_suite_config(value)
    raise ValueError(
        "config must contain exactly game, frame_limit and script, "
        "or exactly game, frame_limit, seeds and agents"
    )


def load_config(path: Path) -> Config:
    return parse_config(json.loads(path.read_text(encoding="utf-8")))


def _hash(game: Any) -> str:
    return f"{game.state_hash():016x}"


def _terminal_reason(state: Any) -> str | None:
    if not state.terminal:
        return None
    if state.phase == "challenge_complete":
        return "challenge_complete"
    return "game_over"


def _empty_event_counts() -> dict[str, int]:
    return {name: 0 for name in _EVENT_FIELDS}


def _count_events(counts: dict[str, int], events: Any) -> None:
    for name in _EVENT_FIELDS:
        counts[name] += int(getattr(events, name))


def _empty_clear_sizes() -> dict[str, int]:
    return {name: 0 for name in _CLEAR_SIZE_FIELDS}


def _count_clear_sizes(counts: dict[str, int], events: Any) -> None:
    """Tally one step's clear size from the engine's own ``lines_cleared`` event.

    The engine clears between zero and four rows per lock, which is exactly the
    range the histogram names. A size outside it is a broken connection rather
    than a play outcome, so it is rejected instead of being dropped: a silent
    drop would leave the histogram and ``result.lines`` disagreeing.
    """
    lines = int(events.lines_cleared)
    if not 0 <= lines <= len(_CLEAR_SIZE_FIELDS):
        raise ValueError(f"engine reported an impossible clear size: {lines}")
    if lines:
        counts[_CLEAR_SIZE_FIELDS[lines - 1]] += 1


def _placed_pieces(event_counts: dict[str, int]) -> int:
    """Pieces written to the board: lock events minus the failed top-out lock.

    ``Game::lock`` raises ``locked`` before its ``fits`` check and writes the
    board only when the piece fits, so the lock that ends an endless game places
    nothing. A frame-limit stop has no such lock, so its count is the lock count.
    """
    return event_counts["locked"] - event_counts["game_over"]


def _compare_piece_count(record: dict[str, Any], field: str, replayed: int, where: str,
                         *, required: bool = False) -> str | None:
    """A difference message for a recorded piece count, or raise on a bad type.

    ``where`` names the record location. JSON ``false``/``true`` compare equal to
    the integers ``0``/``1``, so the type is checked before the value; a record
    that omits the field is older and is left alone, unless ``required`` says this
    record's version always records it — then the absence is a difference, because
    a version 3, 4 or 5 writer emits the count and a current record without it had
    the section deleted.
    """
    if field not in record:
        if not required:
            return None
        return (f"{field}{where}: absent, but a record of this format version always "
                "carries the placed-piece count")
    value = record[field]
    if type(value) is not int:
        raise VerificationError(f"Recorded {field}{where} must be an integer, not {value!r}")
    if value != replayed:
        return f"{field}: recorded {value!r}, replayed {replayed!r}"
    return None


def _compare_section(record: dict[str, Any], field: str, replayed: Any, where: str,
                     *, required: bool = False) -> list[str]:
    """Differences for a section, including its absence when the version requires it.

    ``clear_sizes`` and the objective's source identity are both written by the
    current writer and may be absent only from a record whose version predates
    them, which ``required`` distinguishes: presence alone cannot tell a record
    that predates the section from a current record whose section was deleted. The
    identity is the newer of the two, so a record that carries the first need not
    carry it; each caller passes the flag its own version dictates. A present
    section is compared with the same type-and-key rules as the mandatory ones, so
    a wrong type, a missing key or an extra one is reported.
    """
    if field not in record:
        if not required:
            return []
        return [f"{where}: absent, but a record of this format version always carries it"]
    return _compare_fields(record[field], replayed, where)


def _compare_fields(recorded: Any, replayed: Any, where: str) -> list[str]:
    """Differences between a recorded value and its replay, after a type check.

    JSON ``false``/``true`` compare equal to the integers ``0``/``1`` and to
    ``0.0``, so plain equality accepts a boolean wherever the writer recorded a
    number. The recorded type must equal the replayed type exactly at every leaf,
    and every mapping must carry exactly the replayed keys, before any value is
    compared; a mismatch raises instead of producing a difference. The expected
    types come from the replayed value the writer produced, so the check stays in
    step with what ``_play`` and ``_summarize`` actually emit: a metric ``median``
    is an ``int`` for an odd-sized group and a ``float`` for an even one, and both
    are accepted as recorded.
    """
    if type(recorded) is not type(replayed):
        raise VerificationError(
            f"Recorded {where} must be {type(replayed).__name__}, not {recorded!r}"
        )
    if isinstance(replayed, dict):
        if set(recorded) != set(replayed):
            raise VerificationError(
                f"Recorded {where} keys {sorted(recorded)} do not match {sorted(replayed)}"
            )
        differences = []
        for key, value in replayed.items():
            differences.extend(_compare_fields(recorded[key], value, f"{where}.{key}"))
        return differences
    if recorded != replayed:
        return [f"{where}: recorded {recorded!r}, replayed {replayed!r}"]
    return []


def _play(
    game_config: dict[str, Any],
    frame_limit: int,
    agent: Any,
    game_factory: Callable[..., Any],
) -> dict[str, Any]:
    agent.reset()
    actual_inputs: list[int] = []
    event_counts = _empty_event_counts()
    clear_sizes = _empty_clear_sizes()
    with game_factory(**game_config) as game:
        state = game.state
        initial_hash = _hash(game)
        while True:
            reason = _terminal_reason(state)
            if reason:
                break
            if agent.done:
                reason = "script_complete"
                break
            if len(actual_inputs) >= frame_limit:
                reason = "frame_limit"
                break
            action = agent.act(state)
            state, events = game.step(action)
            actual_inputs.append(action)
            _count_events(event_counts, events)
            _count_clear_sizes(clear_sizes, events)
        result = {
            "score": state.score,
            "lines": state.lines,
            "frame_count": state.frame,
            "stopping_reason": reason,
            "final_phase": state.phase,
            "final_state_hash": _hash(game),
            "event_counts": event_counts,
        }
        pieces_placed = _placed_pieces(event_counts)
        # The engine's RNG/preview selection counter, always above pieces_placed.
        # Kept only to replay legacy records; _persisted drops it from new ones.
        piece_count = state.piece_count
    return {
        "initial_state_hash": initial_hash,
        "inputs": actual_inputs,
        "result": result,
        "pieces_placed": pieces_placed,
        _CLEAR_SIZES_FIELD: clear_sizes,
        "piece_count": piece_count,
    }


def _persisted(episode: dict[str, Any]) -> dict[str, Any]:
    """The saved episode: every recorded field, without the engine RNG counter."""
    return {key: value for key, value in episode.items() if key != "piece_count"}


def run_episode(config: RunConfig, game_factory: Callable[..., Any] = create_game) -> dict[str, Any]:
    return _persisted(_play(config.game, config.frame_limit, ScriptedAgent(config.script), game_factory))


def run_suite(config: SuiteConfig, game_factory: Callable[..., Any] = create_game) -> list[dict[str, Any]]:
    """One episode per agent and seed, in the configured order."""
    episodes = []
    for name in config.agents:
        for seed in config.seeds:
            agent = create_agent(name, seed)
            episode = _play({**config.game, "seed": seed}, config.frame_limit, agent, game_factory)
            episodes.append({"agent": name, "seed": seed, **_persisted(episode)})
    return episodes


def _metric(values: list[int]) -> dict[str, float | int]:
    return {
        "mean": round(fmean(values), 3),
        "median": round(median(values), 3),
        "min": min(values),
        "max": max(values),
    }


def _piece_metric_field(episodes: list[dict[str, Any]]) -> str | None:
    """Which piece count a record's episodes carry, read from all of them.

    A writer emits one piece-count key for a whole record, so the metric the
    summary reports is a property of the record and not of one episode. Reading
    it from the first episode of each group accepted a mixed record — the first
    episode of every group stripped while the later ones kept the count — and
    reported a summary with no piece metric at all, hiding counts the record
    itself carries. The key must therefore be one every episode in the record
    carries: the current ``pieces_placed``, the legacy ``pieces``, or neither in
    a record older than both.
    """
    if not episodes:
        # No episode carries anything, so there is no metric to report. No writer
        # emits an empty suite (a config needs an agent and a seed), so this is
        # the empty case rather than a record shape.
        return None
    for field in _PIECE_FIELDS:
        if all(field in episode for episode in episodes):
            return field
    carried = sum(1 for episode in episodes
                  for field in _PIECE_FIELDS if field in episode)
    if carried:
        raise VerificationError(
            "The piece count must be recorded on every episode of a record or on none: "
            f"{sum(1 for episode in episodes if _PIECES_PLACED_FIELD in episode)} of "
            f"{len(episodes)} episodes carry {_PIECES_PLACED_FIELD}, "
            f"{sum(1 for episode in episodes if _LEGACY_PIECES_FIELD in episode)} carry "
            f"{_LEGACY_PIECES_FIELD}, and no key covers every episode"
        )
    return None


def _clear_sizes_carried(episodes: list[dict[str, Any]]) -> bool:
    """Whether the episodes being summarized carry the clear-size histogram.

    A record written before the metric existed carries it neither per episode nor
    in the summary, and its summary must stay that way: the totals are a claim
    about clear sizes, so reporting zeros for episodes that recorded none would
    state a measurement no run made — and Experiment 002's own replay probe
    compares the summary it re-derives with the recorded one, so a synthesized
    section would reject records that experiment still publishes. Presence is
    all-or-nothing across a record, which ``_compare_summary`` enforces with its
    own message, so this reads "any episode carries it" rather than raising a
    second shape check here: a record that carries the histogram on only some
    episodes is reported there instead.
    """
    return any(_CLEAR_SIZES_FIELD in episode for episode in episodes)


def _summarize(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for episode in episodes:
        grouped.setdefault(episode["agent"], []).append(episode)
    # ``pieces_placed`` is the current key and ``pieces`` the legacy one; a record
    # that carries neither predates both, so its summary reports no piece metric
    # instead of raising, and a record whose episodes disagree on the key is not a
    # shape any writer emits and is reported rather than summarised. The
    # clear-size totals are read the same way from the episodes, so a summary
    # reports exactly the sections the record it summarises carries.
    pieces_field = _piece_metric_field(episodes)
    clear_sizes = _clear_sizes_carried(episodes)
    summary = {}
    for name, group in grouped.items():
        reasons: dict[str, int] = {}
        for episode in group:
            reason = episode["result"]["stopping_reason"]
            reasons[reason] = reasons.get(reason, 0) + 1
        entry: dict[str, Any] = {
            "games": len(group),
            "stopping_reasons": reasons,
            "score": _metric([episode["result"]["score"] for episode in group]),
            "lines": _metric([episode["result"]["lines"] for episode in group]),
            "frames": _metric([episode["result"]["frame_count"] for episode in group]),
        }
        if clear_sizes:
            # The clear sizes add up to each episode's ``result.lines``. An episode
            # that does not carry the histogram contributes nothing: that partial
            # shape is not one any writer emits, and ``_compare_summary``'s
            # suite-wide presence rule reports it rather than this summation.
            entry[_CLEAR_SIZES_FIELD] = {
                field: sum(episode[_CLEAR_SIZES_FIELD][field]
                           for episode in group if _CLEAR_SIZES_FIELD in episode)
                for field in _CLEAR_SIZE_FIELDS
            }
        if pieces_field is not None:
            entry[pieces_field] = _metric([episode[pieces_field] for episode in group])
        summary[name] = entry
    return summary


def _compare_summary(recorded: Any, replayed: dict[str, Any], where: str,
                     episodes: list[dict[str, Any]], required: bool) -> list[str]:
    """Compare a recorded per-agent summary with the replayed one.

    Every pre-existing section — the game count, the stopping reasons, the four
    metrics and the legacy ``pieces`` count — is compared exactly as
    ``_compare_fields`` compared the whole summary before, with the same type and
    key rules. Two per-agent sections are newer and have their own presence rule:
    the clear-size totals and the placed-piece count. A version 3, 4 or 5 record
    must carry both on every agent summary, because its writer always does; a
    legacy record may carry either nowhere and still verifies, and one that
    carries it must carry it everywhere. Presence is all-or-nothing across the
    complete suite — every episode and every agent summary in one record — because
    one writer emits one shape for the whole record: a record that stripped a
    section from one agent's episodes while another agent kept it would verify
    under a per-agent rule while reporting only part of the suite. The rule is
    read from the record's own version and its episodes, never from a single
    episode, so a record whose first episode lacks a section the later ones carry
    is reported instead of being summarised without it. The replayed summary is
    ``_summarize``'s own output, which carries each of those sections exactly when
    the record's episodes do, so a legacy record whose episodes never recorded
    the histogram is compared with a summary that has none either.
    """
    if type(recorded) is not dict:
        raise VerificationError(f"Recorded {where} must be dict, not {recorded!r}")
    if set(recorded) != set(replayed):
        raise VerificationError(
            f"Recorded {where} keys {sorted(recorded)} do not match {sorted(replayed)}"
        )
    sections = (
        (_CLEAR_SIZES_FIELD, "clear-size histogram"),
        (_PIECES_PLACED_FIELD, "placed-piece count"),
    )
    presence = {}
    for field, _ in sections:
        in_episodes = sum(1 for episode in episodes if field in episode)
        in_agents = 0
        for name, agent in recorded.items():
            if type(agent) is not dict:
                raise VerificationError(f"Recorded {where}.{name} must be dict, not {agent!r}")
            in_agents += int(field in agent)
        presence[field] = (in_episodes, in_agents)
    differences = []
    for field, noun in sections:
        in_episodes, in_agents = presence[field]
        complete = (in_episodes, in_agents) == (len(episodes), len(recorded))
        if required and not complete:
            differences.append(
                f"{where}.{field}: absent from "
                f"{len(episodes) - in_episodes} of {len(episodes)} episodes and "
                f"{len(recorded) - in_agents} of {len(recorded)} agent summaries, but a "
                "record of this format version carries it on every one"
            )
        elif not required and (
            in_episodes not in (0, len(episodes))
            or in_agents not in (0, len(recorded))
            or bool(in_episodes) != bool(in_agents)
        ):
            differences.append(
                f"{where}.{field}: the {noun} must be recorded on every episode and every "
                f"agent summary, or on none: {in_episodes} of {len(episodes)} episodes and "
                f"{in_agents} of {len(recorded)} agent summaries carry it"
            )
    own_rule = {field for field, _ in sections}
    for name, replayed_agent in replayed.items():
        recorded_agent = recorded[name]
        recorded_base = {key: value for key, value in recorded_agent.items()
                         if key not in own_rule}
        replayed_base = {key: value for key, value in replayed_agent.items()
                         if key not in own_rule}
        differences.extend(_compare_fields(recorded_base, replayed_base, f"{where}.{name}"))
        # The suite-wide rules above have already rejected a record where only some
        # agents or episodes carry a section; an agent that carries one on both
        # sides is compared key-for-key. The replayed summary carries the section
        # exactly when the record's episodes do, so an agent whose section survived
        # only in the record has already been reported by those rules rather than
        # compared against a section the replay does not have.
        for field in own_rule:
            if field in recorded_agent and field in replayed_agent:
                differences.extend(_compare_fields(
                    recorded_agent[field], replayed_agent[field],
                    f"{where}.{name}.{field}",
                ))
    return differences


def _choice_walk_seeds() -> list[ModuleType]:
    """The package modules a choice's code starts from: the objective and its driver.

    The module that declares the objective is only half of the code a placement
    choice runs through. The agent wrapper hands the objective every state
    parameter it reads and executes the placement it returns, and it imports the
    objective rather than the other way round, so a walk outward from the
    objective can never reach it. It is found from the code instead of
    hand-listed: the factory the runner builds agents with is what selects the
    wrapper, so the walk starts from the module that defines that factory, and
    the class the factory returns is reached from there like any other name that
    module's code holds. A wrapper moved to another module is followed there, and
    a module that stops producing choices drops out of the walk by itself.
    """
    return [tetris, sys.modules[create_agent.__module__]]


def _module_source_digest(module: ModuleType, *, loaded: bool) -> str:
    """One module's source digest, as the loaded code or as the tree now.

    ``loaded=True`` is the writer's view: the digest the interpreter's own loader
    fixed when it read the module's source (``sourceidentity``), so an edit that
    lands afterwards cannot be recorded as the code that chose the inputs. It is
    never a fresh read of the file, which is the defect this closes: ``__file__``
    is only a path, so reading it later can describe source that never ran.

    ``loaded=False`` is the verifier's view: the file on the tree now, which is
    what a record is compared against. The two agree exactly while the tree still
    holds the code that was loaded, which is the normal case; they differ exactly
    when a covered file moved on, and that difference is what verification
    reports.

    A module the recorder never saw loaded has no loaded bytes to name, and this
    raises rather than reading its file: a writer that substituted the file would
    be making the very claim this view exists to stop making.
    """
    if loaded:
        digest = loaded_source_digest(module.__name__)
        if digest is None:
            raise VerificationError(
                f"No loaded source identity was recorded for {module.__name__}: it did not "
                "load through the package's own recorder, so the bytes that ran are not "
                "available and a record cannot honestly name them"
            )
        return digest
    return hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()


def _objective_sources(shape: str = _IDENTITY_CHOICE, *,
                       loaded: bool = False) -> dict[str, str]:
    """sha256 of the source of every package module the objective's choices run.

    The objective's decisions are computed from the module that declares it, the
    package modules its code calls — the frozen geometry and board model it
    imports, and Experiment 002's reachable-set enumeration it reuses — and the
    agent wrapper that drives it: the class whose ``_choose`` supplies the state
    (the board, the current and preview pieces, the level, the ruleset and the
    mode) and the factory that selects that class. Hashing only the declaring
    module would leave the same hole one level deeper — a helper's change alters
    every value the objective computes while the declaring module's own text is
    unchanged — so the closure is walked from the objective's own namespace and
    from the wrapper's, instead of being hand-listed, and a module that stops
    being used drops out of it by itself.

    ``shape`` names which of those walks a caller means. ``_IDENTITY_CHOICE`` is
    the current one, above. ``_IDENTITY_OUTWARD`` is the shape the version-5
    writer emitted, which stops at what the objective's own namespace reaches and
    therefore misses the wrapper: a record of that version is compared against
    that shape, because it is the identity its writer recorded.

    ``loaded`` selects which of the two views above each digest is: the writer's
    loaded identity, or the verifier's tree. One function serves both so the
    closure cannot drift between the two — both enumerate the same modules — and
    only the bytes each digest is taken over differ.
    """
    pending = [tetris] if shape == _IDENTITY_OUTWARD else _choice_walk_seeds()
    sources: dict[str, str] = {}
    while pending:
        module = pending.pop()
        if module.__name__ in sources:
            continue
        sources[module.__name__] = _module_source_digest(module, loaded=loaded)
        for name, value in vars(module).items():
            # The interpreter sets its own scaffolding on every module object under
            # dunder names — ``__loader__``, ``__spec__``, ``__builtins__`` and the
            # rest. Those are bookkeeping rather than names the module's own code
            # binds, and an object's ``__module__`` would otherwise name the module
            # that defines its class: the loader of a covered module is itself such
            # an object, so following it would put the loader's own module into the
            # identity of every module it loaded.
            if name.startswith("__") and name.endswith("__"):
                continue
            origin = getattr(value, "__module__", None)
            if isinstance(origin, str) and origin.startswith(_PACKAGE_PREFIX):
                pending.append(sys.modules[origin])
    return {name: sources[name] for name in sorted(sources)}


def _stale_loaded_references(sources: dict[str, str]) -> list[str]:
    """Cross-module references a partial reload left pointing at replaced code.

    A module that imports a name from another module binds the *object*, not the
    module: ``from .tetris import tetris_choice`` puts that function in the
    importing module's namespace, and ``from .agents import create_agent`` puts the
    factory that selects the agent class in the writer's own. Reloading only the
    module the object was defined in replaces that module's binding and updates the
    loader's digest for it, while every importer keeps the old object — so the code
    that would compute the next choice, or select the agent that computes it, is the
    old function, and an identity naming the reloaded module's source would
    describe an implementation nothing ran. Reloading the importers as well is what
    makes the closure consistent again, because they re-read the names from the
    modules as they now stand.

    Every loaded module of this package is scanned, not only the closure's own
    modules: the modules that *drive* a run hold the factory and the objective by
    value — ``runner`` and ``live`` import ``create_agent`` — so a reload of the
    module that defines them leaves those callers on the previous objects, and no
    walk of the closure alone can see it. A reference whose origin is not part of
    the identity is not reported: only the code the recorded identity claims to
    describe has to be the code that runs.

    Returns the references that no longer appear anywhere in the namespace of the
    module they were defined in, as ``module.attribute (defined in module)``.
    """
    stale = []
    for name in sorted(sys.modules):
        if not name.startswith(_PACKAGE_PREFIX):
            continue
        holding = sys.modules[name]
        if not isinstance(holding, ModuleType):
            continue
        for attribute, value in vars(holding).items():
            if attribute.startswith("__") and attribute.endswith("__"):
                continue
            origin = getattr(value, "__module__", None)
            if not isinstance(origin, str) or origin not in sources or origin == name:
                continue
            if not any(value is bound for bound in vars(sys.modules[origin]).values()):
                stale.append(f"{name}.{attribute} (defined in {origin})")
    return stale


def _loaded_objective_sources(shape: str = _IDENTITY_CHOICE) -> dict[str, str]:
    """The loaded identity of the objective's closure, read at this moment.

    Every writer records this, and it is read when the run or live session is
    constructed — the moment the implementation that will compute the choices is
    fixed — rather than bound once at import. The value comes from the loader that
    read each module's source (``sourceidentity``), not from ``module.__file__``
    read here, and that record is revised by exactly one event: a load. So a
    module this process *reloaded* before the run was built is recorded as the
    code that will choose the placements, which is the only honest value for a
    long-lived process that reloads an objective — a menu, a REPL, a test that
    reloads a module after editing it. A plain file edit is not that event: it
    never revises the loader's record, so the module imported before the edit and
    still executing is still what is recorded (the interactive menu imports the
    modules, waits for a selection, and only then starts a game), and a file
    edited between a module's own import and this line is still executed as it was
    loaded. Binding the value once at import got the reload case wrong in the
    other direction: the reloaded module drove every later choice while the record
    kept naming the code the process no longer ran.

    A *partial* reload is neither of those cases, and is refused rather than
    recorded: reloading one module of the closure updates its digest while the
    modules that imported its objects keep the objects they bound, so the code
    that would run and the module the identity would name are two different
    implementations (``_stale_loaded_references``). No single digest describes
    both, so the writer raises instead of stamping a record with the reloaded
    source of code nothing ran; a caller that wants the reloaded implementation
    reloads the modules that import it too, and then the closure is consistent
    again.
    """
    sources = _objective_sources(shape, loaded=True)
    stale = _stale_loaded_references(sources)
    if stale:
        raise VerificationError(
            "The loaded modules a choice runs through are inconsistent: "
            + ", ".join(stale)
            + " no longer appear in the namespace of the module that defined them, because "
            "that module was reloaded while the module holding the reference was not. The "
            "recorded identity has to name the code that computes the choices, and one "
            "digest cannot describe both the reloaded module and the object the running "
            "code still calls; reload the modules that import it as well, or start a fresh "
            "process"
        )
    return sources


def _objective_record(config: SuiteConfig, *, loaded: bool = False,
                      shape: str = _IDENTITY_CHOICE) -> dict[str, Any] | None:
    """The declared objective a suite record must carry, or ``None`` without the agent.

    The ``heuristic`` mapping is written for every suite because every placement
    agent scores through it; the Tetris agent's choices come from a second,
    separately declared objective, so a suite that uses it records that objective
    too: the module that declares it, the weights its ``weights_record()``
    publishes, and the source identity of the modules its decisions are computed
    from. A suite without the agent has no such objective to record. A writer
    passes ``loaded=True`` so the identity is the code the interpreter loaded as
    of the moment the record is built — the run's own construction — through
    ``_loaded_objective_sources``; the verifier leaves it ``False`` so the
    identity is compared against the files on the tree now, and passes the
    ``shape`` the record's own version's writer emitted, because a version-5
    record's identity stops at what the objective's own namespace reaches.
    """
    if TETRIS_AGENT not in config.agents:
        return None
    return {
        "module": tetris.__name__,
        "weights": tetris.weights_record(),
        _OBJECTIVE_SOURCES_FIELD: (_loaded_objective_sources(shape) if loaded
                                   else _objective_sources(shape)),
    }


def _objective_section(config: SuiteConfig, *, loaded: bool = False) -> dict[str, Any]:
    """The record entry that declares a suite's Tetris objective, if it has one."""
    objective = _objective_record(config, loaded=loaded)
    return {} if objective is None else {_OBJECTIVE_FIELD: objective}


def _compare_objective(record: dict[str, Any], config: SuiteConfig,
                       required: bool, identity_shape: str | None) -> list[str]:
    """Differences for the declared-objective section of a suite record.

    A suite that uses the Tetris agent records the module, the weights and the
    source identity of the objective that chose its placements, so a record
    cannot keep verifying under a different objective merely because the changed
    weights or the changed formula happen to preserve the replayed choices: the
    weight mapping is compared value for value, and the identity is compared
    against the source of the modules the objective's code runs. The section is
    required at the current version, whose writer always emits it for such a
    suite: a record of that version which lacks it had the section deleted, and
    accepting that would verify the record under whatever objective is current —
    exactly the hole the section closes. The identity inside it is gated the same
    way, because the writer that emitted the prior version recorded no identity
    and the writer that emitted the legacy version recorded no section at all;
    both keep verifying, and a present identity is compared in every case. A
    section in a record whose configuration has no Tetris agent is a difference
    too, because no writer emits one.

    ``identity_shape`` is the shape the record's own version's writer emitted, as
    the version table gives it: the modules the objective's own code reaches, or
    those plus the agent wrapper that drives it. A version whose writer emitted no
    identity at all gives ``None``, and the record is compared against the current
    shape, because an identity such a record carries is an edit and no writer ever
    emitted another shape under that version.
    """
    expected = _objective_record(config, shape=identity_shape or _IDENTITY_CHOICE)
    if expected is None:
        if _OBJECTIVE_FIELD in record:
            return [
                f"{_OBJECTIVE_FIELD}: the configuration has no Tetris agent, so the "
                "record must not declare an objective"
            ]
        return []
    if _OBJECTIVE_FIELD not in record:
        if not required:
            return []
        return [
            f"{_OBJECTIVE_FIELD}: absent, but a record of this format version declares the "
            "objective of the Tetris agent whose placements it replayed"
        ]
    recorded = record[_OBJECTIVE_FIELD]
    if not isinstance(recorded, dict):
        raise VerificationError(
            f"Recorded {_OBJECTIVE_FIELD} must be dict, not {recorded!r}"
        )
    differences = _compare_fields(
        {key: value for key, value in recorded.items() if key != _OBJECTIVE_SOURCES_FIELD},
        {key: value for key, value in expected.items() if key != _OBJECTIVE_SOURCES_FIELD},
        _OBJECTIVE_FIELD,
    )
    differences.extend(_compare_section(
        recorded, _OBJECTIVE_SOURCES_FIELD, expected[_OBJECTIVE_SOURCES_FIELD],
        f"{_OBJECTIVE_FIELD}.{_OBJECTIVE_SOURCES_FIELD}",
        required=identity_shape is not None,
    ))
    return differences


def _record_versions() -> dict[str, Any]:
    return {"engine": git_info(engine_root()), "fallgorithm": git_info(PROJECT_ROOT)}


def run_and_save(
    config_path: Path,
    runs_dir: Path = PROJECT_ROOT / "runs",
    game_factory: Callable[..., Any] = create_game,
) -> Path:
    config = load_config(config_path)
    record: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config.to_dict(),
        "versions": _record_versions(),
    }
    if isinstance(config, SuiteConfig):
        record["format_version"] = SUITE_FORMAT_VERSION
        record["heuristic"] = weights_record()
        # A suite that uses the Tetris agent declares its objective beside the
        # frozen heuristic mapping, so the record names the weights that chose
        # its placements and the source identity the interpreter had loaded when
        # this run was built — read here, before the first choice, and re-read at
        # nothing later: a covered module the process reloads after this point
        # cannot have chosen the inputs already recorded.
        record.update(_objective_section(config, loaded=True))
        episodes = run_suite(config, game_factory)
        record["episodes"] = episodes
        record["summary"] = _summarize(episodes)
    else:
        record["format_version"] = FORMAT_VERSION
        record.update(run_episode(config, game_factory))
    return save_record(record, runs_dir)


def save_record(record: dict[str, Any], runs_dir: Path = PROJECT_ROOT / "runs") -> Path:
    """Persist a completed headless or live episode in the existing run layout."""
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]
    run_dir = runs_dir / name
    run_dir.mkdir(parents=True, exist_ok=False)
    path = run_dir / "run.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _engine_warnings(recorded: Any) -> list[str]:
    if not isinstance(recorded, dict):
        raise VerificationError("Malformed engine version in run record")
    current = git_info(engine_root())
    warnings = []
    dirty = recorded.get("dirty")
    # ``git_info`` records a boolean, or ``null`` when there is no Git checkout,
    # and JSON ``0``/``1`` compare equal to ``False``/``True``: plain equality let
    # an edited flag match the current checkout and suppress this warning. The
    # fields stay advisory, so a wrong type is reported as a difference rather
    # than raised, and an older record that omits the field keeps verifying.
    if (
        (dirty is not None and type(dirty) is not bool)
        or dirty != current["dirty"]
        or recorded.get("commit") != current["commit"]
    ):
        warnings.append("Engine Git version or dirty status differs from the recorded run.")
    if recorded.get("kind") != "committed" or current["kind"] != "committed":
        warnings.append("The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.")
    return warnings


def _record_sections(record: dict[str, Any], path: Path) -> tuple[Any, Any]:
    try:
        return record["versions"]["engine"], record["configuration"]
    except (KeyError, TypeError) as error:
        raise VerificationError(f"Malformed run record in {path}: {error}") from error


def _verify_scripted(record: dict[str, Any], path: Path, sections_required: bool,
                     game_factory: Callable[..., Any]) -> list[str]:
    recorded_engine, configuration = _record_sections(record, path)
    try:
        config = parse_config(configuration)
        inputs = record["inputs"]
        expected = record["result"]
        expected_initial = record["initial_state_hash"]
    except (KeyError, TypeError, ValueError) as error:
        raise VerificationError(f"Malformed run record in {path}: {error}") from error
    if not isinstance(config, RunConfig):
        raise VerificationError(f"Malformed run record in {path}: not a scripted configuration")
    if not isinstance(inputs, list) or any(type(mask) is not int or not 0 <= mask <= 31 for mask in inputs):
        raise VerificationError("Recorded inputs must be a list of gameplay masks from 0 to 31")
    if len(inputs) > config.frame_limit:
        raise VerificationError("Recorded inputs exceed the frame limit")
    agent = ScriptedAgent(config.script)
    for index, mask in enumerate(inputs):
        if agent.done or agent.act(None) != mask:
            raise VerificationError(f"Recorded input at frame {index + 1} does not match the scripted agent")

    event_counts = _empty_event_counts()
    clear_sizes = _empty_clear_sizes()
    with game_factory(**config.game) as game:
        state = game.state
        actual_initial = _hash(game)
        for index, mask in enumerate(inputs):
            if state.terminal:
                raise VerificationError(f"Recorded input at frame {index + 1} follows a terminal state")
            state, events = game.step(mask)
            _count_events(event_counts, events)
            _count_clear_sizes(clear_sizes, events)
        reason = _terminal_reason(state)
        if reason is None:
            if agent.done:
                reason = "script_complete"
            elif len(inputs) >= config.frame_limit:
                reason = "frame_limit"
            else:
                reason = "stopped_early"
        if reason == "stopped_early":
            raise VerificationError(
                "Recorded inputs stop before script completion, frame limit, or a terminal state"
            )
        actual = {
            "score": state.score,
            "lines": state.lines,
            "frame_count": state.frame,
            "stopping_reason": reason,
            "final_phase": state.phase,
            "final_state_hash": _hash(game),
            "event_counts": event_counts,
        }
        actual_pieces_placed = _placed_pieces(event_counts)
        actual_piece_count = state.piece_count
    differences = []
    if expected_initial != actual_initial:
        differences.append(f"initial_state_hash: recorded {expected_initial!r}, replayed {actual_initial!r}")
    # ``pieces_placed`` counts pieces written to the board; the legacy ``pieces``
    # key held the RNG/preview selection counter, which is always above it. Each
    # present key is replayed against its own value, so older records keep
    # verifying, and a record of this version must carry the count its writer
    # emits.
    for field, replayed in ((_PIECES_PLACED_FIELD, actual_pieces_placed),
                            (_LEGACY_PIECES_FIELD, actual_piece_count)):
        difference = _compare_piece_count(
            record, field, replayed, "",
            required=sections_required and field == _PIECES_PLACED_FIELD,
        )
        if difference:
            differences.append(difference)
    differences.extend(_compare_section(
        record, _CLEAR_SIZES_FIELD, clear_sizes, _CLEAR_SIZES_FIELD,
        required=sections_required,
    ))
    differences.extend(_compare_fields(expected, actual, "result"))
    warnings = _engine_warnings(recorded_engine)
    if differences:
        context = "\n" + "\n".join(f"Warning: {warning}" for warning in warnings) if warnings else ""
        raise VerificationError("Replay mismatch:\n  " + "\n  ".join(differences) + context)
    return warnings


def _verify_suite(record: dict[str, Any], path: Path, sections_required: bool,
                  identity_shape: str | None, game_factory: Callable[..., Any]) -> list[str]:
    recorded_engine, configuration = _record_sections(record, path)
    # ``weights_record()`` carries the writer's float weights and the tie-break
    # string, so the same type-and-key comparison the episodes and summary get
    # applies here too: a weight saved as JSON ``true`` compares equal to ``1.0``,
    # and the plain comparison that used to run here certified it.
    heuristic_differences = _compare_fields(record.get("heuristic"), weights_record(), "heuristic")
    if heuristic_differences:
        raise VerificationError(
            "Recorded heuristic weights differ from the current implementation:\n  "
            + "\n  ".join(heuristic_differences)
        )
    try:
        config = parse_config(configuration)
        episodes = record["episodes"]
        summary = record["summary"]
    except (KeyError, TypeError, ValueError) as error:
        raise VerificationError(f"Malformed run record in {path}: {error}") from error
    if not isinstance(config, SuiteConfig):
        raise VerificationError(f"Malformed run record in {path}: not a suite configuration")
    objective_differences = _compare_objective(record, config, sections_required,
                                               identity_shape)
    if objective_differences:
        raise VerificationError(
            "Recorded objective differs from the current implementation:\n  "
            + "\n  ".join(objective_differences)
        )
    # The record must carry exactly the sequence run_suite emits: agent order,
    # then seed order. Membership alone would accept a record that duplicates one
    # configured pair and omits another.
    expected = [(name, seed) for name in config.agents for seed in config.seeds]
    if not isinstance(episodes, list) or len(episodes) != len(expected):
        raise VerificationError("Recorded episodes do not match the configured agents and seeds")
    replayed = []
    for index, (episode, identity) in enumerate(zip(episodes, expected)):
        try:
            recorded_agent = episode["agent"]
            recorded_seed = episode["seed"]
        except (KeyError, TypeError) as error:
            raise VerificationError(f"Malformed episode {index} in {path}: {error}") from error
        # JSON true compares equal to the integer 1, so a boolean seed would pass
        # plain equality against a configured seed of 1. Require the recorded
        # identity types the writer emits before comparing the values.
        if type(recorded_agent) is not str or type(recorded_seed) is not int:
            raise VerificationError(
                f"Episode {index} identity must be an agent name and an integer seed: "
                f"recorded agent {recorded_agent!r} with seed {recorded_seed!r}"
            )
        if (recorded_agent, recorded_seed) != identity:
            raise VerificationError(
                f"Episode {index} is not the configured suite entry: recorded agent "
                f"{recorded_agent!r} with seed {recorded_seed!r}, expected agent "
                f"{identity[0]!r} with seed {identity[1]!r}"
            )
        # The same guard the scripted verifier applies. Plain equality would accept
        # booleans for the 0/1 masks, and a non-list input would make the difference
        # message below raise TypeError instead of a controlled VerificationError.
        inputs = episode.get("inputs")
        if not isinstance(inputs, list) or any(
            type(mask) is not int or not 0 <= mask <= 31 for mask in inputs
        ):
            raise VerificationError(
                f"Recorded inputs in episode {index} must be a list of gameplay masks from 0 to 31"
            )
        name, seed = identity
        actual = _play({**config.game, "seed": seed}, config.frame_limit,
                       create_agent(name, seed), game_factory)
        differences = []
        if episode.get("initial_state_hash") != actual["initial_state_hash"]:
            differences.append(
                f"initial_state_hash: recorded {episode.get('initial_state_hash')!r}, "
                f"replayed {actual['initial_state_hash']!r}"
            )
        if episode.get("inputs") != actual["inputs"]:
            differences.append(f"inputs: recorded {len(inputs)}, replayed {len(actual['inputs'])}")
        differences.extend(
            _compare_fields(episode.get("result"), actual["result"], f"episode {index} result")
        )
        for field, actual_value in ((_PIECES_PLACED_FIELD, actual[_PIECES_PLACED_FIELD]),
                                    (_LEGACY_PIECES_FIELD, actual["piece_count"])):
            difference = _compare_piece_count(
                episode, field, actual_value, f" in episode {index}",
                required=sections_required and field == _PIECES_PLACED_FIELD,
            )
            if difference:
                differences.append(difference)
        differences.extend(_compare_section(
            episode, _CLEAR_SIZES_FIELD, actual[_CLEAR_SIZES_FIELD],
            f"episode {index} {_CLEAR_SIZES_FIELD}", required=sections_required,
        ))
        if differences:
            raise VerificationError(
                f"Replay mismatch in episode {index} ({name}, seed {seed}):\n  " + "\n  ".join(differences)
            )
        replayed.append(episode)
    summary_differences = _compare_summary(
        summary, _summarize(replayed), "summary", replayed, sections_required,
    )
    if summary_differences:
        raise VerificationError(
            "Recorded summary does not match the replayed episodes:\n  "
            + "\n  ".join(summary_differences)
        )
    return _engine_warnings(recorded_engine)


def verify_run(path: Path, game_factory: Callable[..., Any] = create_game) -> list[str]:
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise VerificationError(f"Unsupported run record format in {path}")
    version = record.get("format_version")
    # JSON booleans and floats compare equal to the integers 1 and 2 under plain
    # equality (``True == 1``, ``2.0 == 2``), so a record whose discriminator was
    # edited to ``2.0`` used to dispatch to the suite verifier and one edited to
    # ``true`` to the scripted verifier. The writer records only an ``int``.
    if type(version) is not int:
        raise VerificationError(f"Recorded format_version in {path} must be an integer, not {version!r}")
    if version in _SCRIPTED_FORMAT_VERSIONS:
        return _verify_scripted(record, path, _SCRIPTED_FORMAT_VERSIONS[version], game_factory)
    if version in _SUITE_FORMAT_VERSIONS:
        sections_required, identity_shape = _SUITE_FORMAT_VERSIONS[version]
        return _verify_suite(record, path, sections_required, identity_shape, game_factory)
    raise VerificationError(f"Unsupported run record format in {path}")

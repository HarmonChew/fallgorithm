"""Run bounded episodes and replay exactly the inputs that were executed.

Eight record versions share this module and all replay against the native engine.
Versions 1 (one scripted episode) and 2 (a suite of placement-agent episodes over
fixed seeds) are the older formats of each shape: the verifier accepts the
placed-piece count, the clear-size histogram and the declared objective absent
there and compares each one when present. Versions 3 (a
scripted episode), 4, 5, 6, 7 and 8 (suites) are written after them and must carry
every section their writer emits — the placed-piece count, the clear-size
histogram, and, for a suite that selects an agent with its own declared
objective, that agent's declared objective.
Version 4's writer recorded that objective without the source identity its
successor adds, so version 4 records require everything except the identity;
version 5's writer recorded the identity as the modules the objective's own code
reaches, which cannot include the agent wrapper that drives it; version 6 records
the wrapper beside them, but names the shared factory rather than the runner's
dispatch as the builder of an agent the factory defines, so a Tetris record of
that version does not cover the code that selects its implementation; version
7 records the dispatch for every agent, which is the code that decides which
implementation is built; and version 8 is the live-suite format, whose identity
is the version-7 walk plus the module that drives the interactive live session
(``block_stack_ai.live``). The live writer emits version 8 and the headless
writer emits version 7, so the live entry is additive: a headless record keeps
the identity version 7 recorded, and only a record the live session wrote is
compared against the walk that includes the controller that handed its agent
every observation. The numbers are reused rather than a schema
history — the base commit's writer emitted the placed-piece count at versions 1
and 2, and an earlier writer wrote the same numbers without it — so a version
says which sections the verifier must require and which walk produced the
identity: a legacy version's sections may be absent and are compared when
present, and only the current version's must be present.

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
4, 5, 6, 7 or 8 record must carry ``pieces_placed``, because that is the key its writer
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
same type-and-key rules as the mandatory sections. In a version 3, 4, 5, 6, 7 or 8
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

A suite whose configuration includes an agent with a separately declared
objective records that objective as ``objective``: the module that declares it,
the mapping its ``weights_record()`` returns and the source identity of the
modules its decisions are computed from, mirroring the ``heuristic`` section
beside it. The frozen heuristic mapping is written for every suite because every
placement agent scores through it; an agent whose choices come from a second,
separately declared objective instead is named by this section, and without it
such a suite verifies under whatever objective is current whenever the change
happens to preserve its replayed choices. The identity closes the case the
weights cannot: they are constants, so a formula change that leaves them alone
changes every value the objective computes while the weights still compare
equal, and the recorded choices only catch it when the change happens to move
one of them. A version 5 or 6 suite that uses such an agent must carry the
identity, because its writer always emits it; the version 4 writer emitted the
objective without it and the version 2 writer emitted no objective at all, so
those records keep verifying — the runs of Experiment 003 written by both
writers do — and a present identity is compared with the same type-and-key rules
in every case. The identity names every module whose code produces a choice, the
agent wrapper that hands the objective its state included: the wrapper imports
the objective rather than the other way round, so an identity walked outward
from the objective alone could not reach it, and a wrapper change that kept the
replayed choices was certified. A version 5 record is compared against that
older shape, which is the identity its writer recorded. Beside the wrapper, the
walk covers the module that selects which implementation is built. From version 7
that module is the runner's dispatch for every agent, because ``build_agent`` is
what decides every agent's implementation — a change there can build a different
implementation for the same agent name while still replaying the recorded inputs,
whether or not the objective's own module owns the agent. The version-6 writer
named the shared factory for an agent the factory defines instead, which left the
dispatch out of a Tetris record while it still selected that agent, so those
records are compared against the walk their own writer recorded:
the retained fixture and Experiment 003's capture are the version-6 shape,
and the current writer's Tetris identity covers the dispatch as well.

The live session is the second writer of suite records, and its decisions run
through one module more than a headless run's: ``LiveSession.receive`` reads
each desktop observation, hands it to the agent and executes the mask the agent
returns, while the headless runner drives the same agent through ``_play``. The
live module imports the runner rather than the other way round, so no walk from
the objective or the dispatch can reach it, and a change to ``receive`` that
altered how or when observations reached the agent stayed invisible whenever the
replayed masks and result fields still matched. The live writer therefore emits
version 8, whose identity seeds the live module beside the dispatch, and the
version keys the shape because the headless writer must keep emitting exactly
the identity its retained records were written with.

Every version-8 record also carries the controller's own ``controller``
section, because the live session drives agents that declare no objective:
``greedy``, ``random`` and ``lookahead`` all take a version-8 record, and
without that section none of them would carry a source map at all. The
controller's walk starts from the live module and stops before the declared
objectives, which none of those choices runs, and the objective-bearing agents
carry both sections — the objective's identity, which includes the live module
because the session drives it, and the controller's, which covers the shared
agent code every live game also runs.

The section is keyed by the agent, not by one hard-wired objective: the module
it names is the one that declares the configured agent's objective, whichever
agent the suite selects, and the walk that produces the identity starts from
that module. A suite configures at most one such agent, because a suite record
carries exactly one ``objective`` section; ``_parse_suite_config``
rejects a configuration that names two rather than writing a record whose
sections could not be told apart.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from importlib import import_module
import json
from pathlib import Path
from statistics import fmean, median
import sys
from types import ModuleType
from typing import Any, Callable
from uuid import uuid4

from . import tetris, wellplan
from .agents import (
    AGENT_NAMES as FACTORY_AGENT_NAMES, TETRIS_AGENT, ScriptedAgent, Segment, create_agent,
    parse_script,
)
from .engine import PROJECT_ROOT, create_game, engine_root, git_info
from .heuristic import weights_record
from .sourceidentity import loaded_source_digest
from .wellplan import PLAN_AGENT


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
# A suite whose identity covered the objective, the wrapper and the module that
# *builds* the agent, but seeded that last module from the shared factory for an
# agent the factory defines. The runner's dispatch decides which implementation
# every agent is built from — it routes an agent a declared objective owns to that
# objective's module and every other agent to the shared factory — so a Tetris
# record of this version named no code that selects its implementation, and a
# change to the dispatch that still replayed the recorded inputs was invisible to
# it. Superseded by SUITE_FORMAT_VERSION.
WRAPPER_IDENTITY_SUITE_FORMAT_VERSION = 6
SUITE_FORMAT_VERSION = 7  # a suite, which always records the sections and the identity
# A suite written by the interactive live session. Its writer emits the version-7
# sections and the same dispatch-seeded identity, plus the module that drives the
# live game: ``block_stack_ai.live`` reads each desktop observation, hands it to
# the agent and executes the placement it returns, so a change there that kept
# the replayed masks was otherwise invisible to verification. Every version-8
# record also carries a ``controller`` section of its own, because the live
# session drives agents whose choices no declared objective computes: without it
# a greedy, random or lookahead live record would carry no source identity at
# all. A new version rather than a wider version-7 walk, because every retained
# headless record is compared against the identity its own writer emitted.
# Superseded by ``SUITE_FORMAT_VERSION`` for headless runs only; the live session
# keeps emitting this version.
LIVE_SUITE_FORMAT_VERSION = 8
# The shapes the objective's source identity has been written in, named for the
# walk that produces it. ``_IDENTITY_OUTWARD`` is the modules the module that
# declares the objective reaches: itself, and the package modules its own code
# calls. ``_IDENTITY_CHOICE`` adds the agent wrapper that produces the choices —
# the class whose ``_choose`` hands the objective its state — and the module that
# builds the agent, seeded from the shared agent factory for an agent it defines
# itself and from the runner's dispatch for an agent a declared objective owns.
# ``_IDENTITY_DISPATCH`` seeds that second module from the dispatch for *every*
# agent, which is the code that decides which implementation is built at all: the
# wrapper imports the objective, so no walk outward from the objective can reach
# the wrapper, and the dispatch runs before any choice exists, so the objective's
# own namespace cannot reach it either; for an agent the factory defines, seeding
# the factory instead left the dispatch out while it still selected the agent.
# ``_IDENTITY_LIVE`` is version 8's objective walk: the dispatch-seeded walk
# plus the module that drives the live session, which imports the dispatch rather
# than the other way round and so is reachable from no seed the other shapes use.
# ``_IDENTITY_CONTROLLER`` is the walk behind the live controller's own section:
# seeded from the live module alone and stopping before the declared objectives,
# because it has to cover the agents that declare none. Each shape is keyed by
# the format version whose writer emitted it, so the records written under a
# narrower walk — Experiment 003's capture and the retained version 6 fixture
# among them — keep verifying against the walk they recorded.
_IDENTITY_OUTWARD = "outward"
_IDENTITY_CHOICE = "choice"
_IDENTITY_DISPATCH = "dispatch"
_IDENTITY_LIVE = "live"
_IDENTITY_CONTROLLER = "controller"
# What each suite version's own writer always emitted, as ``(sections,
# identity, controller)``: the placed-piece count, the clear-size histogram and
# the declared objective, then the objective's source identity inside that
# objective, then whether the record carries the live controller's own identity
# section. Inferring "legacy" from an absent section instead would accept a
# current record whose section was deleted, because a stripped record and a
# pre-section record are the same JSON. The prior version stays strict about
# everything its writer did emit — its records carry the objective, so its
# verifier still requires it — and gates only the identity, which its writer
# never recorded. The identity is the newer of the two: a version whose writer
# emitted the sections therefore also requires the ones that preceded it. The
# identity's second element names which modules that version's identity covered,
# or ``None`` for a version whose writer emitted none — an identity such a
# record carries anyway is an edit, and is compared against the current shape,
# because no writer ever emitted another one there. The third element is the
# controller section the version-8 live writer emits for every live game: the
# objective section is absent whenever a greedy, random or lookahead agent is
# driven, so the controller's identity cannot live inside it. What a version's
# writer emitted is only half of what a record can be asked for: the version is
# also a claim about which writer wrote it, so a record that configures an agent
# no writer of that version could build is an edit rather than a legacy record,
# and is reported by ``_check_declared_agent_versions`` before this table's
# requirements are applied.
_SUITE_FORMAT_VERSIONS = {
    LEGACY_SUITE_FORMAT_VERSION: (False, None, False),
    PRIOR_SUITE_FORMAT_VERSION: (True, None, False),
    OUTWARD_IDENTITY_SUITE_FORMAT_VERSION: (True, _IDENTITY_OUTWARD, False),
    WRAPPER_IDENTITY_SUITE_FORMAT_VERSION: (True, _IDENTITY_CHOICE, False),
    SUITE_FORMAT_VERSION: (True, _IDENTITY_DISPATCH, False),
    LIVE_SUITE_FORMAT_VERSION: (True, _IDENTITY_LIVE, True),
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
# The declared objective of the agents that do not score through the frozen
# heuristic mapping, keyed by agent name. The section names the module that
# declares the configured agent's objective, so the mapping cannot be read as
# the heuristic's own and is not hard-wired to one agent: the module, its
# weights and the identity of the code behind its choices all come from this
# entry. A record carries one ``objective`` section, so a suite configures at
# most one of these agents.
_OBJECTIVE_FIELD = "objective"
# The live controller's own identity, beside the objective section: every
# version-8 record carries it, because the live session also drives agents whose
# choices no separately declared objective computes, and those records would
# otherwise carry no source identity at all.
_CONTROLLER_FIELD = "controller"
# The objective's semantic identity, beside its weights: the sha256 of the source
# of every package module its decisions are computed from. The weights are
# constants and cannot identify the formula around them, so without this a record
# kept verifying under an objective whose formula changed whenever the replayed
# choices happened to be preserved.
_OBJECTIVE_SOURCES_FIELD = "sources"
# Every package module belongs to this namespace; the objective's modules are
# discovered from its own namespace rather than hand-listed.
_PACKAGE_PREFIX = f"{__package__}."
# The package modules that are never part of a choice's identity, by name. The
# provenance recorder is the one: it fixes every other module's digest as it
# loads, so it computes no placement, and it cannot record its own load because
# it is the module that installs the recorder — a record that named it could
# never be written. Its absence is not a gap in the identity of a *choice*: no
# choice reads a byte of it. A module that merely failed to load through the
# recorder still raises (``_module_source_digest``), so this excludes the
# recorder alone rather than papering over a missing digest.
_IDENTITY_EXCLUDED_MODULES = frozenset({f"{__package__}.sourceidentity"})

@dataclass(frozen=True)
class DeclaredObjective:
    """One agent's declared objective, and the writer version that introduced it.

    ``module`` declares the objective's weights and formula, ``owner`` is the
    module that builds the agent when the objective's own module does (``None``
    when the shared agent factory does), and ``introduced_in`` is the suite
    format version whose writer first made the agent configurable. The last is a
    property of the agent, not of the writer that runs now: it is what stops a
    record from claiming a version that never knew the agent it configures, which
    would otherwise decide the objective section's required-ness — and the
    identity's — by the version the record itself chose.
    """

    module: ModuleType
    owner: ModuleType | None
    introduced_in: int


# The agents whose choices a separately declared objective computes: for each
# one, the module that declares its weights and formula, and — when its objective
# module also owns the agent — the module that builds it. ``None`` means the
# shared agent factory defines it, and that factory's own module drives it.
# Registering an agent here is what makes a suite that configures it record, and
# verify, its objective.
DECLARED_OBJECTIVES: dict[str, DeclaredObjective] = {
    # The version-2 writer already built the Tetris agent: Experiment 003's early
    # rounds wrote such suites, before the objective section existed, so a
    # version-2 record of a Tetris suite legitimately carries no objective. The
    # plan agent is declared beside the objective that computes its choices and
    # was added by the writer that emits version 6, which always records the
    # objective, the identity behind it and the dispatch that builds the agent —
    # no older version's writer ever emitted one, so a record that claims an older
    # version while configuring the plan is an edit, not a legacy record. The
    # version is the writer's version when the agent was introduced, not the
    # writer's current one: a later writer that moves ``SUITE_FORMAT_VERSION`` —
    # the version-7 writer did, to record the identity the dispatch-seeded walk
    # produces — keeps verifying the records the version-6 writer emitted.
    TETRIS_AGENT: DeclaredObjective(tetris, None, LEGACY_SUITE_FORMAT_VERSION),
    PLAN_AGENT: DeclaredObjective(wellplan, wellplan, 6),
}
# Every agent a suite may configure: the shared factory's own, then the agents a
# declared objective owns. The runner is the registry the configuration is
# validated against, so an agent that lives beside its objective is still a
# first-class agent name here.
AGENT_NAMES = FACTORY_AGENT_NAMES + (PLAN_AGENT,)


def _declared_agents(names: Iterable[str]) -> tuple[str, ...]:
    """The distinct agents in ``names`` whose choices a declared objective computes.

    Each name is reported once: a suite may configure the same agent twice — its
    episodes repeat in the configured order, which the writer and the verifier
    both carry — and a repeated agent still declares one objective. What a record
    cannot carry is two *different* declared objectives.
    """
    return tuple(name for name in dict.fromkeys(names) if name in DECLARED_OBJECTIVES)


def build_agent(name: str, seed: int) -> Any:
    """Build the agent a suite names; the random stream is seeded by its factory.

    The shared factory builds the agents declared in its own module. An agent a
    declared objective owns is built by that objective's module instead, which is
    what keeps the shared factory's source — and therefore its digest in a frozen
    record's identity — fixed while a new agent is added: the factory's bytes are
    covered by every record of every agent it dispatches, so an agent added to it
    would invalidate them all. Each agent is still built by exactly one factory,
    and the name is validated here, before either factory sees it.
    """
    if name not in AGENT_NAMES:
        raise ValueError(f"unknown agent: {name!r}")
    objective = DECLARED_OBJECTIVES.get(name)
    if objective is not None and objective.owner is not None:
        return objective.owner.build_agent(name, seed)
    return create_agent(name, seed)


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
    declared = _declared_agents(agents)
    if len(declared) > 1:
        # A record carries one ``objective`` section, which names the module
        # that declares the configured agent's objective. Two such agents would
        # need two sections of a shape the version-6 writer does not emit, so
        # the configuration is refused here rather than recorded ambiguously.
        raise ValueError(
            "a suite configures at most one agent with its own objective: "
            f"{', '.join(declared)}"
        )
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
            agent = build_agent(name, seed)
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


def _choice_walk_seeds(agent: str, shape: str = _IDENTITY_CHOICE) -> list[ModuleType]:
    """The package modules a choice's code starts from: the objective and its driver.

    The module that declares the objective is only half of the code a placement
    choice runs through. The agent wrapper hands the objective every state
    parameter it reads and executes the placement it returns, and it imports the
    objective rather than the other way round, so a walk outward from the
    objective can never reach it. It is found from the code instead of
    hand-listed: the selection that decides which implementation is built is what
    picks the wrapper, so the walk starts from the module that makes that
    selection, and the class it returns is reached from there like any other name
    that module's code holds. A wrapper moved to another module is followed
    there, and a module that stops producing choices drops out of the walk by
    itself.

    Both seeds are selected by the agent name: the objective module is the one
    that declares *this* agent's objective, and the driver is the module that
    selects the implementation for the shape's walk (``_choice_driver``). A record
    of the well plan therefore covers the dispatch that selects its agent, and so
    does a current record of every other agent: the dispatch builds them all.

    ``shape`` names which walk the caller means, and the walk of a record's own
    version is the one its writer emitted: ``_IDENTITY_OUTWARD`` stops at the
    objective's own namespace, ``_IDENTITY_CHOICE`` adds the wrapper and the
    module the version-6 writer named as its builder, ``_IDENTITY_DISPATCH``
    names the dispatch for every agent, which is what decides which
    implementation is built, ``_IDENTITY_LIVE`` is that dispatch-seeded walk
    plus the module that drives the interactive live session, and
    ``_IDENTITY_CONTROLLER`` is the live module alone — the controller's own
    section, which has to cover the greedy, random and lookahead agents that
    declare no objective. The default is ``_IDENTITY_CHOICE``, the shape callers
    that predate the version keying mean (``_objective_sources``); a caller that
    means the walk the current headless writer emits passes
    ``_IDENTITY_DISPATCH``, and the live session passes ``_IDENTITY_LIVE`` for
    its objective and ``_IDENTITY_CONTROLLER`` for its controller section.
    """
    if shape == _IDENTITY_CONTROLLER:
        return [_live_controller_module()]
    seeds = [DECLARED_OBJECTIVES[agent].module]
    if shape == _IDENTITY_OUTWARD:
        return seeds
    seeds.append(_choice_driver(agent, shape))
    if shape == _IDENTITY_LIVE:
        seeds.append(_live_controller_module())
    return seeds


def _choice_driver(agent: str, shape: str = _IDENTITY_CHOICE) -> ModuleType:
    """The package module that selects which implementation builds this agent.

    ``_IDENTITY_DISPATCH`` — the walk the current writer emits — is the runner's
    dispatch for every agent: ``build_agent`` reads ``DECLARED_OBJECTIVES`` and
    routes an agent a declared objective owns to that objective's module, and
    every other agent to the shared factory. That dispatch is the code that
    decides which implementation is built, whichever agent the record names, so a
    change to it is code the choice runs through whether or not the objective's
    own module owns the agent.

    ``_IDENTITY_CHOICE`` — the walk the version-6 writer emitted — is the module
    that writer named as the builder: an agent the shared factory defines was
    seeded from the factory, because the factory's ``create_agent`` is the branch
    that returns its class, and an agent a declared objective owns from the
    dispatch, because the factory never builds that one. Records of that version
    are compared against that walk, which is the identity their writer recorded,
    and it is the default here for the same reason it is the default of
    ``_objective_sources``.

    ``_IDENTITY_LIVE`` uses the dispatch for every agent too, because the live
    session builds its agent through the same dispatch as a headless run; the
    live module is an additional seed of that walk rather than a different
    driver.
    """
    if shape in (_IDENTITY_DISPATCH, _IDENTITY_LIVE) \
            or DECLARED_OBJECTIVES[agent].owner is not None:
        return sys.modules[build_agent.__module__]
    return sys.modules[create_agent.__module__]


def _live_controller_module() -> ModuleType:
    """The module that drives the interactive live session, imported on demand.

    ``block_stack_ai.live`` imports this module rather than the other way round,
    so it cannot be imported at module load time here. A record of version 8 names
    it as the code that handed its agent every observation, and the verifier
    derives the same seed without depending on whether the caller already
    imported it: the walk must enumerate the same modules on both sides.
    """
    return import_module(f"{__package__}.live")


def _sibling_objective_modules(agent: str) -> set[int]:
    """The other agents' objective modules, which this agent's identity excludes.

    The shared factory imports every objective module, so a walk from the
    wrapper would otherwise swallow its siblings' sources: a Tetris record would
    be invalidated by an edit to the well plan, whose code no Tetris choice ever
    runs. Excluding them also states the invariant the registration relies on —
    a declared objective does not compute its choices with another agent's
    objective module — because a sibling reached *from the seed objective's own
    namespace* would be dropped as well.
    """
    return {id(DECLARED_OBJECTIVES[name].module) for name in DECLARED_OBJECTIVES
            if name != agent}


def _declared_objective_modules() -> set[int]:
    """Every declared objective's module, which the controller walk excludes.

    The controller section covers agents that declare no objective and the
    shared agent code beside them; a ``greedy``, ``random`` or ``lookahead``
    choice runs neither objective's module, so an edit to one must not
    invalidate a controller record that never called it. The objective-bearing
    agents carry the objective's own identity for that half of their code path.
    """
    return {id(objective.module) for objective in DECLARED_OBJECTIVES.values()}


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


def _objective_sources(shape: str = _IDENTITY_CHOICE, *, agent: str = TETRIS_AGENT,
                       loaded: bool = False) -> dict[str, str]:
    """sha256 of the source of every package module the objective's choices run.

    The objective's decisions are computed from the module that declares it, the
    package modules its code calls — the frozen geometry and board model it
    imports, and Experiment 002's reachable-set enumeration it reuses — and the
    agent wrapper that drives it: the class whose ``_choose`` supplies the state
    (the board, the current and preview pieces, the level, the ruleset and the
    mode), the module that decides which implementation is built, and the factory
    that selects that class. Hashing only the declaring module would leave the
    same hole one level deeper — a helper's change alters every value the
    objective computes while the declaring module's own text is unchanged — so the
    closure is walked from the objective's own namespace and from the wrapper's,
    instead of being hand-listed, and a module that stops being used drops out of
    it by itself. A change to the dispatch that still replays the recorded inputs
    is caught by the same walk, because the dispatch module is one of the seeds of
    the current shape and its bytes are hashed with the rest.

    ``agent`` selects which objective that is: the walk is seeded from the module
    that declares *that* agent's objective, so the identity follows the
    configuration rather than one hard-wired agent. The other agents' objective
    modules are excluded (``_sibling_objective_modules``), because the shared
    factory imports them all and none of them computes this agent's choices.

    ``shape`` names which of those walks a caller means. ``_IDENTITY_DISPATCH`` is
    the current headless one, above: the dispatch that builds every agent is a
    seed, so a record of any agent covers the code that selects its
    implementation. ``_IDENTITY_LIVE`` is that walk plus the live-driving module,
    which the live session's writer emits under version 8: the session hands the
    agent every observation through ``LiveSession.receive``, and that module's
    dependency on the dispatch runs the other way, so it is an added seed rather
    than something the existing walk can reach. ``_IDENTITY_CONTROLLER`` is the
    live controller's own walk — the live module alone, with the declared
    objectives dropped from what it reaches — and needs no ``agent``: it exists
    for the agents that declare no objective. ``_IDENTITY_CHOICE`` is the shape
    the version-6 writer emitted, which named the shared factory for an agent the
    factory defines and the dispatch only for an agent a declared objective owns;
    ``_IDENTITY_OUTWARD`` is the shape the version-5 writer emitted, which stops
    at what the objective's own namespace reaches and therefore misses the
    wrapper. A record of any version is compared against the shape its own writer
    recorded.

    The default is the version-6 shape, and deliberately so: it is what callers
    that predate the version keying mean by "the Tetris objective's identity" —
    Experiment 003's own probe among them, whose retained capture recorded exactly
    that walk, so leaving the default there keeps that evidence checkable without
    editing it. A caller that means the walk the current writer emits passes
    ``_IDENTITY_DISPATCH``; the writer and the verifier both do.

    ``loaded`` selects which of the two views above each digest is: the writer's
    loaded identity, or the verifier's tree. One function serves both so the
    closure cannot drift between the two — both enumerate the same modules — and
    only the bytes each digest is taken over differ.
    """
    seeds = _choice_walk_seeds(agent, shape)
    excluded = (_declared_objective_modules() if shape == _IDENTITY_CONTROLLER
                else _sibling_objective_modules(agent))
    pending = list(seeds)
    sources: dict[str, str] = {}
    while pending:
        module = pending.pop()
        if (id(module) in excluded or module.__name__ in sources
                or module.__name__ in _IDENTITY_EXCLUDED_MODULES):
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


def _stale_loaded_references(sources: dict[str, str],
                             excluded: set[int]) -> list[str]:
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

    The other declared objectives' modules are skipped, exactly as the walk skips
    them: a module that computes a *different* agent's choices is not part of this
    record's code path, so a reference it holds into this closure — the one it
    holds to this closure's code because its own agent runs on it — cannot make
    this record name code that will not run. It is scanned for its own agent's
    records, where it is not skipped.

    Returns the references that no longer appear anywhere in the namespace of the
    module they were defined in, as ``module.attribute (defined in module)``.
    ``excluded`` names the modules whose references are not part of this record's
    code path and are therefore neither walked nor scanned: the *other* declared
    objective for an objective's identity, and *every* declared objective for the
    controller's.
    """
    stale = []
    for name in sorted(sys.modules):
        if not name.startswith(_PACKAGE_PREFIX):
            continue
        holding = sys.modules[name]
        if id(holding) in excluded or not isinstance(holding, ModuleType):
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


def _loaded_objective_sources(shape: str = _IDENTITY_CHOICE, *,
                              agent: str = TETRIS_AGENT) -> dict[str, str]:
    """The loaded identity of the objective's closure, read at this moment.

    Every writer records this before the run's first choice, including at each
    live game's BEGIN, rather than binding it once at import or session creation.
    The value comes from the loader that read each module's source
    (``sourceidentity``), not from ``module.__file__``
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
    sources = _objective_sources(shape, agent=agent, loaded=True)
    excluded = (_declared_objective_modules() if shape == _IDENTITY_CONTROLLER
                else _sibling_objective_modules(agent))
    stale = _stale_loaded_references(sources, excluded)
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
                      shape: str = _IDENTITY_DISPATCH) -> dict[str, Any] | None:
    """The declared objective a suite record must carry, or ``None`` without one.

    The ``heuristic`` mapping is written for every suite because every placement
    agent scores through it; an agent whose choices come from a second,
    separately declared objective instead is named here: the module that declares
    *that* agent's objective — the one the configuration selects, not a fixed
    one — the weights its ``weights_record()`` publishes, and the source identity
    of the modules its decisions are computed from. A suite whose agents all
    score through the frozen mapping has no such objective to record. A writer
    passes ``loaded=True`` so the identity is the code the interpreter loaded as
    of the moment the record is built — the run's own construction — through
    ``_loaded_objective_sources``; the verifier leaves it ``False`` so the
    identity is compared against the files on the tree now, and passes the
    ``shape`` the record's own version's writer emitted, because a version-6
    record's identity names the shared factory instead of the dispatch for an
    agent the factory defines, a version-5 record's stops at what the objective's
    own namespace reaches, and the live writer's adds the module that drives the
    session beside the dispatch those two writers already seed.
    """
    agent = _declared_agent(config)
    if agent is None:
        return None
    module = DECLARED_OBJECTIVES[agent].module
    return {
        "module": module.__name__,
        "weights": module.weights_record(),
        _OBJECTIVE_SOURCES_FIELD: (_loaded_objective_sources(shape, agent=agent) if loaded
                                   else _objective_sources(shape, agent=agent)),
    }


def _declared_agent(config: SuiteConfig) -> str | None:
    """The one configured agent whose choices its own objective computes, if any.

    A record carries one ``objective`` section, and ``_parse_suite_config``
    refuses a configuration that names two such agents, so more than one here is
    a configuration no writer could have produced and is reported rather than
    resolved by picking one.
    """
    agents = _declared_agents(config.agents)
    if not agents:
        return None
    if len(agents) > 1:
        raise VerificationError(
            "the configuration names more than one agent with its own objective "
            f"({', '.join(agents)}), which no record format carries"
        )
    return agents[0]


def _objective_section(config: SuiteConfig, *, loaded: bool = False,
                       shape: str = _IDENTITY_DISPATCH) -> dict[str, Any]:
    """The record entry that declares a suite's objective of its own, if it has one.

    ``shape`` is the walk the caller's writer emits: the headless writer leaves
    the default dispatch-seeded shape, and the live writer passes
    ``_IDENTITY_LIVE`` so the record also covers the module that drove the
    session. A caller that predates the live shape keeps emitting exactly the
    identity it always emitted.
    """
    objective = _objective_record(config, loaded=loaded, shape=shape)
    return {} if objective is None else {_OBJECTIVE_FIELD: objective}


def _controller_identity(*, loaded: bool = False) -> dict[str, Any]:
    """The live controller's own identity: the module that drives the session.

    The walk starts from ``block_stack_ai.live`` and stops before the declared
    objectives, because the live session also drives the agents that declare
    none and neither objective's code is on their path. The section exists for
    exactly those agents: version 8 has to cover every live game, and the
    objective section is absent whenever ``greedy``, ``random`` or ``lookahead``
    was driven, so the controller's identity cannot live inside it. The shared
    agent code, the dispatch that builds the agent and the helpers an agent calls
    are all reached from the live module and are hashed with it.

    ``loaded`` selects the writer's view (the bytes the interpreter loaded) or
    the verifier's (the tree now), exactly as it does for the objective's
    identity; both enumerate the same closure through ``_objective_sources``.
    """
    return {
        "module": _live_controller_module().__name__,
        _OBJECTIVE_SOURCES_FIELD: _objective_sources(
            _IDENTITY_CONTROLLER, loaded=loaded),
    }


def _controller_section(*, loaded: bool = False) -> dict[str, Any]:
    """The record entry that declares the live controller's identity."""
    return {_CONTROLLER_FIELD: _controller_identity(loaded=loaded)}


def _check_declared_agent_versions(config: SuiteConfig, version: int, path: Path) -> None:
    """A record cannot claim a version whose writer never knew the agent it configures.

    The section requirements are read from the record's own format version, so a
    record could otherwise be relabelled to a version before the objective section
    existed and verified with its objective — and, one version later, the identity
    behind it and the dispatch that builds the agent — all dropped. The agent
    names a suite may configure are not version-gated, so nothing else notices:
    the verifier would compare the record against whatever objective is current
    while the record's own text claims the older writer chose it. The version is a
    claim about the writer, and the writer that first made an agent configurable
    is a property of that agent (``DeclaredObjective.introduced_in``), not of the
    version the record carries. The Tetris agent predates the objective section —
    the version-2 writer already built it, so its version-2 records legitimately
    carry no objective — while the plan agent was introduced by the version-6
    writer, which always records it; a record that configures the plan below
    version 6 is therefore an edit, not a record of an older writer, and is
    reported before any section is compared.
    """
    for agent in _declared_agents(config.agents):
        introduced = DECLARED_OBJECTIVES[agent].introduced_in
        if version < introduced:
            raise VerificationError(
                f"Recorded format_version {version} in {path} predates the agent it "
                f"configures: {agent} was introduced by the writer that emits version "
                f"{introduced}"
            )


def _compare_objective(record: dict[str, Any], config: SuiteConfig,
                       required: bool, identity_shape: str | None) -> list[str]:
    """Differences for the declared-objective section of a suite record.

    A suite that selects an agent with its own objective records the module, the
    weights and the source identity of the objective that chose its placements,
    so a record cannot keep verifying under a different objective merely because
    the changed weights or the changed formula happen to preserve the replayed
    choices: the weight mapping is compared value for value, the identity is
    compared against the source of the modules the objective's code runs, and the
    module name is compared too, so a record of a Tetris suite cannot verify
    against the well plan's objective even if that objective happened to publish
    the same weights. The section is required at the current version, whose
    writer always emits it for such a suite: a record of that version which lacks
    it had the section deleted, and accepting that would verify the record under
    whatever objective is current — exactly the hole the section closes. The
    identity inside it is gated the same way, because the writer that emitted the
    prior version recorded no identity and the writer that emitted the legacy
    version recorded no section at all; both keep verifying, and a present
    identity is compared in every case. A section in a record whose configuration
    declares no objective of its own is a difference too, because no writer emits
    one.

    Which version's requirements apply is not the record's to choose: the writer
    that could have configured the agent it names is a property of that agent, and
    ``_check_declared_agent_versions`` reports a record below it before this
    comparison runs, so a record cannot be relabelled out of the section — or, one
    version later, out of the identity inside it.

    ``identity_shape`` is the shape the record's own version's writer emitted, as
    the version table gives it: the modules the objective's own code reaches, or
    those plus the agent wrapper and the module that builds the agent, or — for
    the live suite format — that dispatch-seeded walk plus the module that drives
    the live session. A version whose writer emitted no identity at all gives
    ``None``, and the record is compared against the current shape, because an
    identity such a record carries is an edit and no writer ever emitted another
    shape under that version.
    """
    expected = _objective_record(config, shape=identity_shape or _IDENTITY_DISPATCH)
    if expected is None:
        if _OBJECTIVE_FIELD in record:
            return [
                f"{_OBJECTIVE_FIELD}: the configuration declares no agent whose choices "
                "an objective of its own computes, so the record must not declare one"
            ]
        return []
    if _OBJECTIVE_FIELD not in record:
        if not required:
            return []
        return [
            f"{_OBJECTIVE_FIELD}: absent, but a record of this format version declares the "
            "objective of the agent whose placements it replayed"
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


def _compare_controller(record: dict[str, Any], required: bool) -> list[str]:
    """Differences for the live controller's identity section of a suite record.

    Every version-8 record carries this section, including the records whose
    agents declare no objective: the live session writes every live game under
    that version, and a greedy, random or lookahead record has no ``objective``
    section for the controller's module to hide in. The section names the live
    module and the sha256 of every package module its walk reaches, minus the
    declared objectives. It is required at the version whose writer emits it; a
    record below that version which carries one had it added, because no older
    writer emitted the section, and is reported rather than accepted — the same
    rule the objective section follows.
    """
    if _CONTROLLER_FIELD not in record:
        if not required:
            return []
        return [
            f"{_CONTROLLER_FIELD}: absent, but a record of this format version carries "
            "the live controller's identity"
        ]
    if not required:
        return [
            f"{_CONTROLLER_FIELD}: no writer of this format version emits one, so the "
            "section was added"
        ]
    recorded = record[_CONTROLLER_FIELD]
    if not isinstance(recorded, dict):
        raise VerificationError(
            f"Recorded {_CONTROLLER_FIELD} must be dict, not {recorded!r}"
        )
    return _compare_fields(recorded, _controller_identity(), _CONTROLLER_FIELD)


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
    # The version the writer records is the headless writer's own, or the live
    # writer's for a record the interactive session wrote; the two key different
    # identity shapes, so neither writer can silently inherit the other's walk.
    if isinstance(config, SuiteConfig):
        record["format_version"] = SUITE_FORMAT_VERSION
        record["heuristic"] = weights_record()
        # A suite that selects an agent with its own objective declares that
        # objective beside the frozen heuristic mapping, so the record names the
        # weights that chose its placements and the source identity the
        # interpreter had loaded when this run was built — read here, before the
        # first choice, and re-read at nothing later: a covered module the process
        # reloads after this point cannot have chosen the inputs already recorded.
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


def _verify_suite(record: dict[str, Any], path: Path, version: int,
                  game_factory: Callable[..., Any]) -> list[str]:
    sections_required, identity_shape, controller_required = _SUITE_FORMAT_VERSIONS[version]
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
    _check_declared_agent_versions(config, version, path)
    objective_differences = _compare_objective(record, config, sections_required,
                                               identity_shape)
    if objective_differences:
        raise VerificationError(
            "Recorded objective differs from the current implementation:\n  "
            + "\n  ".join(objective_differences)
        )
    # The controller section is compared after the objective so a record that
    # carries both reports the objective's half of a changed live controller
    # first; the live module's digest belongs to both sections, and the shared
    # section answers for the records that declare no objective at all.
    controller_differences = _compare_controller(record, controller_required)
    if controller_differences:
        raise VerificationError(
            "Recorded controller differs from the current implementation:\n  "
            + "\n  ".join(controller_differences)
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
                       build_agent(name, seed), game_factory)
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
        return _verify_suite(record, path, version, game_factory)
    raise VerificationError(f"Unsupported run record format in {path}")

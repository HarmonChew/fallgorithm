# Experiment records

Create the next numbered directory (`001-short-name/`, and so on) with a small
`config.json`, a compact `result.json`, and `notes.md`. State the question, the
evaluation used, the observed result, and what you learned. Keep useful failures
as well as successes.

Record the fallgorithm and Block Stack Git commits and dirty flags. A run from
uncommitted code is a **working-tree run**: a commit hash alone cannot recreate
those edits. Keep small configurations and summaries here; the source code in
`src/` is the maintained implementation, and Git history holds earlier versions.

Run `block-stack-ai` (or `block-stack-ai menu`) in a terminal for a selectable
experiment launcher. It offers live-play options or the full evaluation with
the experiment's configured agents and seeds, and shows the command before
starting. A live game also asks for a frame limit, defaulting to the
experiment's configured value, and starts paused by default so the first board
is visible before the game runs. It does not edit saved experiment
configurations.

Use `block-stack-ai experiments` to list the recorded experiments, and
`block-stack-ai run --experiment NNN` (or the full `NNN-name`), then
`block-stack-ai verify runs/<run-id>/run.json`. Mention the temporary run path in
the notes along with the code versions and commands. To reproduce later, restore
both recorded code versions (and any uncommitted edits, if possible), rebuild the
native engine, rerun the configuration, and verify the new record. `runs/` is
disposable ignored output. Deliberately copy any artifact needed for a lasting
experiment into a suitable retained location; do not depend on the temporary
run directory remaining available.

Experiment 005's `search_plan` agent is registered at runtime so the source files
Experiment 004's retained identity covers stay byte-identical. The normal
`run`, `play`, `verify`, `watch` and `export-replay` commands load the
experiment's module and register the agent for the duration of the command, so
Experiment 005 is a normal launcher choice; the dedicated launcher remains the
exact path the retained manifests name:

```sh
python -m block_stack_ai.experiment005 run experiments/005-search-plan/config-search.json
python -m block_stack_ai.experiment005 verify runs/<run-id>/run.json
```

The retained records under `experiments/005-search-plan/records/` carry their own
manifests with the exact verification commands.

For a fresh game controlled live, use `block-stack-ai play --experiment NNN`.
`--agent` selects one of that experiment's placement agents, and defaults to
`search_plan` when the experiment offers it, otherwise `greedy` when it offers
that, otherwise the experiment's first agent, so an experiment without greedy
starts with an agent it has; fixed-script experiments support `run` and replay
only. The launcher starts every live agent paused by default. The direct `play`
command starts the search agent paused and other agents playing; `--paused` or
`--no-paused` chooses explicitly. Select Playing in the launcher to start
immediately. `--frame-limit N` overrides the saved limit for this live game. An
explicit `--config` file is also accepted by both commands in place of
`--experiment`.

Future "best" references can point to a selected experiment for each approach.
Choose one using a stated evaluation over enough games, rather than one lucky
score. This index is maintained by hand; there is no promotion service or model
registry in Stage 0.

## Index

| Number | Question | Outcome |
| --- | --- | --- |
| [000-connection](000-connection/notes.md) | Can the project control and replay the sibling engine? | See its measured result. |
| [001-greedy-heuristic](001-greedy-heuristic/notes.md) | Does a one-piece greedy placement heuristic beat a random legal-placement baseline on fixed seeds? | The heuristic survived about 20x longer and cleared about 119 lines per game against none; 3328 of its 3357 locks matched the placement model. |
| [002-path-aware-lookahead](002-path-aware-lookahead/notes.md) | Does path-aware reachability plus one piece of lookahead on the player-visible next piece beat 001's straight-drop greedy on the same seeds? | The new agent survived about 5.8x longer and cleared about 7.7x the lines per game, and 23144 of its 23153 locks landed exactly as modelled against greedy's 3328 of 3357; one of its ten games stopped at the configured 200000-frame safety cap. |
| [003-tetris-aware-agent](003-tetris-aware-agent/notes.md) | Can the per-step clear-size breakdown be recorded and replayed, and does a predeclared Tetris-oriented objective on 002's reachable set raise the Tetris rate over the frozen 002 `lookahead` baseline? | The histogram is recorded as a top-level per-episode field whose presence is one suite-wide invariant and whose per-agent totals are derived from the episodes, so a legacy record's summary re-derives unchanged, the Tetris agent's declared objective is recorded beside the frozen heuristic mapping — its weights *and* the source identity of every module its choices run, the agent wrapper that hands it the state included, taken from the source the loader read and compiled rather than from an independent read beside the load, so neither an edit after a module is imported nor a valid-but-stale bytecode cache can make the record name code that did not run — and compared on replay, and the record's own `format_version` says which sections its writer always emitted — the current versions require them, the legacy versions may omit them, and older records still verify, and the publication snapshot retained in `result.json` is one probe run's — its state line and counts are reconstructed from the record's own fields, every count it cites is a length of the run's captured path list, the base-refresh snapshot is that run's captured commands and fields, the declared objective's capture covers every module the recorded identity covers — the wrapper beside the objective and its helpers — and the base refresh asserts that the observed remote main contains the recorded base rather than equalling a fixed tip; and every retained claim that was once a copy of itself is derived from evidence outside it — the published tree and the base snapshot's two trees from this repository's own objects, the comparison-set prose from the captured per-path states, the order sentence from the capture and the cited run, the version prose from the writer's constants, and the objective's loaded identity from the loader's record before the run's first choice and at each live game's BEGIN, with a closure a partial reload left inconsistent refused rather than named. The new agent's Tetris line rate is 13.1x the baseline's (1.1445% against 0.0876%, 10 Tetrises against 2) and it never hit the frame cap, but it cleared 0.38x the lines and every one of its ten games topped out; the frozen `lookahead` side reproduces 002's published summary exactly. |
| [004-bounded-well-plan](004-bounded-well-plan/notes.md) | Can an explicit visible-information well plan — one designated well column, an explicit stack-height budget and a spend-or-abandon rule at a self-tracked I-drought bound — keep Experiment 003's Tetris rate while surviving longer and scoring more on the same ten seeds? | Yes, on all three acceptance thresholds and with the baseline re-derived rather than carried over: `tetris_plan` clears 6200 lines in ten games with 60 Tetrises (a Tetris line rate of 0.038710, 3.38x Experiment 003's 0.011445), 620.0 mean lines (1.77x its 349.5) and 1,665,036.0 mean score (2.94x its 567,266.2), with no game stopped at the frame cap. Two objective changes produce that and the result is attributed to both: the plan, and a composition that scores the current placement's whole plan value where Experiment 003 scores only its clear term — the retained record derives one reachable board per phase on which the two compositions select different placements, and a reserve can be earned with the designated well column already occupied, which is derived too. The declared-objective section of the run record is generalised from a hard-wired Tetris identity to the objective of the agent the configuration selects, resolved through a registry that dispatches each agent to the module that builds it, and a record written now covers that dispatch module for *every* declared agent (the walk is keyed by the record's own format version: version 7 seeds the dispatch that builds every agent, while the version-6 shape Experiment 003's records carry is unchanged). The new agent is declared in its objective module, so the shared factory's source is untouched and a version-6 record written by the frozen Experiment 003-era writer, retained as `probes/legacy_v6_tetris_record.json`, still verifies here. The plan's objective is predeclared in `probes/predeclared_objective.json` before the run and re-checked against the record. Experiment 003's own configuration re-run here reproduces every published row field by field, and the plan does not reach the frozen `lookahead` agent's 912.8 mean lines, which is reported as an aspirational comparison rather than met. The retained record's own claims are now recomputed from their artifacts: the predeclaration binds the cited run's per-episode outcomes as well as its inputs, the comparison against every superseded run is made against those runs' rows retained in `probes/superseded_run_rows.json`, the capture history has to pair one distinct design per superseded run and each capture must precede the run it is paired with, the evaluation configuration — for the replay and the baseline as well as the record — is the experiment's own `config.json` rather than the copy a result embeds, and the record's conclusion, limitations and counts are generated from the same derivation `check-record` re-makes, so a claim no check derives cannot enter the certified record. Every retained outcome comparison is type- and value-sensitive as well, so a number edited to a boolean is reported instead of reproducing the integer it compares equal to, and the objective module's own descriptions of its preview phase, drought boundary and overflow term are each pinned by a regression that derives the code's behaviour rather than restating the prose. |
| [005-search-plan](005-search-plan/notes.md) | Does a deterministic visible-information search one piece deeper than Experiment 004 improve mean lines and preserve its Tetris rate? | Yes on both unchanged predeclared rules, over ten fresh seeds disjoint by native initial state: search averages 1654.8 lines versus the unchanged plan's 557.9 (2.97x), with Tetris line rate 0.051003 versus 0.032264. Four search games reach the 200000-frame cap. The previous even-seed comparison is exploratory because 42/43 and 44/45 alias. Eight record sets and all 132 replays are retained; result checks bind their digests, producer commits, configuration files and predeclaration, source recording refuses partial reloads, and replay checks the complete deterministic budget. |
| [006-level29-survival](006-level29-survival/notes.md) | Does lowering the well plan's height budget from 8 to 5 at level 28 reduce `search_plan`'s top-outs without lowering mean lines? | Yes, on 30 fresh seeds: 13 top-outs against 30, 3,446.2 mean lines against 1,737.3 and 2.6x the score, with 17 games at the 400,000-frame cap. The Tetris line rate fell from 4.6% to 0.7%. |
| [008-benchmark-format](008-benchmark-format/notes.md) | How strong is `survival_plan`'s evaluation under BetaTetris's benchmark format (30 Hz tapping, 300 ms reaction, level 39 double killscreen, level 49 line cap), and how much did it depend on instant reactions? | On 300 fresh seeds per format: 358.5 mean lines with instant reactions, 319.8 at 300 ms (benchmark format; BetaTetris's hybrid averages 399.9), 234.3 at 15 Hz. 2.4M mean score for BetaTetris against 0.41M here. Nearly every game tops out soon after level 39. |
| [009-cem-score](009-cem-score/notes.md) | Can CEM-learned evaluation parameters (20 numbers of `bench_plan`) raise the mean score at 30 Hz / 300 ms on held-out seeds? | Yes: on 008's 300 seeds mean score 590,203 against 411,676 (paired +178,527, 95% CI 165,371 to 191,225), lines 332.8 against 319.8, Tetris rate 10.2% against 3.2%. Every game still tops out. One run, 24 training seeds, 4 iterations (12 predeclared; cut for time). |
| [010-complete-reach](010-complete-reach/notes.md) | Does finding every placement the tap and reaction limits allow (instead of one fixed route per target) raise `tuned_plan`'s score and survival, with 009's numbers unchanged? | Slightly: mean score 607,113 against 590,203 (paired +16,911, 95% CI 3,191 to 30,499), so the predeclared rule is met; lines 330.9 against 332.8 (CI -6.4 to 2.4), level-39 reach 92.7% both, every game still tops out. Reach finds only about 0.1 extra placement per piece, and the death pieces have no placement under either model. |
| [011-native-speed](011-native-speed/notes.md) | Can a C++ port of `reach_plan` play exactly the same games as the Python one, at least 50x faster? | Yes: all 300 held-out games identical to Experiment 010's (and 40 training games), 133.3x faster per game (107.2 s to 0.81 s on 24 workers); the 300-game evaluation takes 16 s instead of about 25 minutes. The agent is no stronger. |

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
starting. It does not edit saved experiment configurations.

Use `block-stack-ai experiments` to list the recorded experiments, and
`block-stack-ai run --experiment NNN` (or the full `NNN-name`), then
`block-stack-ai verify runs/<run-id>/run.json`. Mention the temporary run path in
the notes along with the code versions and commands. To reproduce later, restore
both recorded code versions (and any uncommitted edits, if possible), rebuild the
native engine, rerun the configuration, and verify the new record. `runs/` is
disposable ignored output. Deliberately copy any artifact needed for a lasting
experiment into a suitable retained location; do not depend on the temporary
run directory remaining available.

For a fresh game controlled live, use `block-stack-ai play --experiment NNN`.
`--agent` selects one of that experiment's placement agents; fixed-script
experiments support `run` and replay only. An explicit `--config` file is also
accepted by both commands in place of `--experiment`.

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

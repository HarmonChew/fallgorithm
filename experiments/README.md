# Experiment records

Create the next numbered directory (`001-short-name/`, and so on) with a small
`config.json`, a compact `result.json`, and `notes.md`. State the question, the
evaluation used, the observed result, and what you learned. Keep useful failures
as well as successes.

Record the fallgorithm and Block Stack Git commits and dirty flags. A run from
uncommitted code is a **working-tree run**: a commit hash alone cannot recreate
those edits. Keep small configurations and summaries here; the source code in
`src/` is the maintained implementation, and Git history holds earlier versions.

Use `block-stack-ai run --config experiments/NNN-name/config.json`, then
`block-stack-ai verify runs/<run-id>/run.json`. Mention the temporary run path in
the notes along with the code versions and commands. To reproduce later, restore
both recorded code versions (and any uncommitted edits, if possible), rebuild the
native engine, rerun the configuration, and verify the new record. `runs/` is
disposable ignored output. Deliberately copy any artifact needed for a lasting
experiment into a suitable retained location; do not depend on the temporary
run directory remaining available.

Future "best" references can point to a selected experiment for each approach.
Choose one using a stated evaluation over enough games, rather than one lucky
score. This index is maintained by hand; there is no promotion service or model
registry in Stage 0.

## Index

| Number | Question | Outcome |
| --- | --- | --- |
| [000-connection](000-connection/notes.md) | Can the project control and replay the sibling engine? | See its measured result. |

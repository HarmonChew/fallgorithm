# 000: Connection and replay

**Question:** Can fallgorithm load the sibling Block Stack engine, control it
through frame inputs, and reproduce a recorded run?

**What was tested:** A Release build of `blocks_native` and
`block_stack_headless` in this project's ignored `.build/engine/` directory;
the installed local Python binding; the CLI doctor check; 16 unit tests; three
native integration tests; and the 31-frame script in [config.json](config.json).
The script taps left, releases, rotates clockwise twice with a release between
presses, taps right, holds Down, then releases. Every mask goes through
`Game.step()` on the actual native engine.

**Observed result:** Setup and doctor succeeded. All 16 unit and three native
integration tests passed. The run ended by completing the script after 31
frames, at score 0 and lines 0. The native engine reported two moves, two
rotations, nine soft-drop events, and one gravity drop. Initial state hash:
`04cccfd1b5b72607`; final state hash: `41dfca77676d6d79`. The `verify`
command replayed the recorded inputs in a fresh game and matched the final
hash and outcome fields. The full temporary record is
`runs/20260923T082257031259Z-76932b9a/run.json`; the compact retained summary
is [result.json](result.json).

**Reproduce:** From the project root, create the virtual environment and run
the setup commands in the [project README](../../README.md), then:

```sh
.venv/bin/block-stack-ai doctor
.venv/bin/block-stack-ai run --config experiments/000-connection/config.json
.venv/bin/block-stack-ai verify runs/<new-run-id>/run.json
```

The script configuration and seed should produce the stated outcome with the
same engine code. The run record captures the Git commit and dirty status of
both repositories. The engine was dirty at commit
`0e56c3beb7e4165e793ff326e3600d973e236cb8`; fallgorithm was a new local
repository with no commit. This is a **working-tree run**, so the Git metadata
cannot reconstruct the uncommitted source. Preserve those source edits if an
exact future rebuild is needed. The ignored `runs/` directory is disposable;
retain important artifacts deliberately elsewhere. This JSON record is a
fallgorithm format, not the game's desktop replay format.

**Lesson:** The native frame API and state hash are enough for a small,
repeatable input experiment. Later agents can use the same connection and
recording path while changing only how masks are chosen.

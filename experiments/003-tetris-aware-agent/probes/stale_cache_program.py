"""Does the recorded identity name the code that actually ran, beside a stale cache?

A loader that reads a module's source for the digest and then delegates execution
to the loader that read it can run something else entirely: Python's import system
uses a ``__pycache__`` entry while the source it was built from still matches by
integer-second mtime and size, so a same-length edit inside that mtime's second
leaves a cache that is executed while a separate read of the file returns the
edited text. The identity then names source the process did not run — and a
verifier, which reads the same file, certifies it.

This program measures the three values apart, so a driver can require them to be
one: it imports the package (running whatever the loader chose), reads the file on
the tree, and asks the writer what it recorded. Invoke it with ``PYTHONPATH``
pointing at the tree under test, whose ``tetris.py`` the driver has compiled,
edited to the same size and restored to its old mtime::

    PYTHONPATH=<tree>/src python stale_cache_program.py

It prints one JSON object and exits 0:

* ``executed`` — ``block_stack_ai.tetris.WELL_DEPTH_CAP`` as the interpreter
  loaded it: the value the code that ran declares;
* ``source`` — the same constant as the file on the tree declares it;
* ``recorded`` — the writer's identity entry for that module (the tree's own
  writer view: ``runner._loaded_objective_sources()`` where the writer reads it
  when a run is built, or the import-time ``runner._LOADED_OBJECTIVE_SOURCES``
  where it binds it once);
* ``file`` — sha256 of the file on the tree;
* ``agrees`` — whether ``recorded`` is that file's digest.

A tree that digests one read and executes another reports ``executed`` different
from ``source`` with ``agrees`` true; a tree that compiles what it digests reports
all three equal.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

CONSTANT = "WELL_DEPTH_CAP"


def main() -> int:
    from block_stack_ai import runner  # noqa: F401  (imports the covered modules)
    from block_stack_ai import tetris

    source = Path(sys.modules["block_stack_ai.tetris"].__file__)
    declared = re.search(rf"^{CONSTANT} = (\d+)$", source.read_text(encoding="utf-8"),
                         re.MULTILINE)
    assert declared is not None, f"{source} declares no {CONSTANT}"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    # The writer's view of the loaded identity, as the tree under test carries it.
    reader = getattr(runner, "_loaded_objective_sources", None)
    recorded = (reader() if reader is not None
                else runner._LOADED_OBJECTIVE_SOURCES)["block_stack_ai.tetris"]
    print(json.dumps({
        "executed": getattr(tetris, CONSTANT),
        "source": int(declared.group(1)),
        "recorded": recorded,
        "file": digest,
        "agrees": recorded == digest,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

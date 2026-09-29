"""The source identity of a module, fixed when the interpreter loaded it.

A run executes the module objects the interpreter loaded, not whatever the files
named by ``module.__file__`` hold when a record is written. ``__file__`` is only a
path: reading it later returns the source as it stands *then*, so a digest read
from it can name code that never ran. A process that imports the objective's
modules, has one of their files edited, and only then imports the module that
writes the record would otherwise record the edited bytes while ``sys.modules``
still executes the loaded ones, and a later verification — which reads the edited
file too — would certify that provenance instead of reporting it.

This module closes that gap by fixing each package module's digest at the moment
its loader reads the source, and holding it for the process's lifetime:

* the recorder is a meta-path finder installed when the package is first
  imported, so it observes every ``block_stack_ai`` module loaded after that.
  That is every submodule: importing a submodule loads its package first, so the
  finder is in place before any of them is found. Only this package's names are
  claimed; every other import is answered exactly as it was before.
* the recorded value is the sha256 of the source bytes the loader read — the same
  value a verifier computes from the file on the tree. A record written from the
  loaded code therefore agrees with the tree while the tree still holds that
  code, and once a covered file moves on the record is *reported* rather than
  certified, because its identity no longer matches the file.

A module whose loader read a valid ``__pycache__`` entry still matches this
definition under Python's own import trust model: such an entry is used only
while the source it was built from is unchanged, which is the same assumption the
interpreter itself makes.

``loaded_source_digest`` is the writer's view. The verifier deliberately does not
use it — it compares a record against the files on the tree now, which is what
``runner._objective_sources`` computes without ``loaded=True``.
"""

from __future__ import annotations

import hashlib
import sys
from typing import Any

from importlib import _bootstrap
from importlib.machinery import SourceFileLoader

_PACKAGE = __package__
# Every module of this package, and only those: the package's own ``__init__`` is
# not part of any objective's identity, so it is not claimed either.
_PACKAGE_PREFIX = f"{_PACKAGE}."

# Module name -> sha256 of the source bytes its loader read when it was loaded.
# Written once per load and never revised, so a later edit cannot reach it.
_LOADED_SOURCE_DIGESTS: dict[str, str] = {}


def loaded_source_digest(name: str) -> str | None:
    """The digest fixed when ``name`` was loaded, or ``None`` if it was not observed.

    ``None`` means this process never saw the module loaded through this package's
    recorder — it was already in ``sys.modules`` when the recorder was installed,
    or something replaced it directly — so the loaded bytes are not available. A
    writer that needs the loaded identity treats that as the gap it is rather than
    substituting a later read of the file.
    """
    return _LOADED_SOURCE_DIGESTS.get(name)


class _RecordingLoader:
    """A source loader that executes, and records, one and the same source read.

    The wrapper owns ``exec_module`` and compiles the bytes it has just read,
    instead of delegating to the wrapped loader's own ``exec_module``: that one
    may execute a cached ``__pycache__`` entry rather than the source beside it,
    and Python validates such an entry by the source's integer-second mtime and
    size. A same-length edit inside that mtime's second therefore leaves a cache
    the inner loader would execute while a separate read of the file returns the
    edited text — and recording a digest from that independent read would name
    source the process did not run, which is the defect this module exists to
    close. Compiling what is digested and executing the result makes the identity
    true by construction. Every other attribute is the wrapped loader's, so the
    import system sees the loader it would otherwise have used.
    """

    def __init__(self, inner: SourceFileLoader) -> None:
        self._inner = inner

    def create_module(self, spec: Any) -> Any:
        return self._inner.create_module(spec)

    def exec_module(self, module: Any) -> None:
        name = module.__name__
        path = self._inner.get_filename(name)
        data = self._inner.get_data(path)
        digest = hashlib.sha256(data).hexdigest()
        try:
            # Exactly what ``_LoaderBasics.exec_module`` does with the code the
            # wrapped loader would have chosen, on the code these bytes compile to.
            code = self._inner.source_to_code(data, path)
            _LOADED_SOURCE_DIGESTS[name] = digest
            _bootstrap._call_with_frames_removed(exec, code, module.__dict__)
        except BaseException:
            # The module did not load, so it contributes no code to identify; a
            # value left behind for a name nothing executes could only mislead.
            _LOADED_SOURCE_DIGESTS.pop(name, None)
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _RecordingFinder:
    """A meta-path finder that wraps this package's source loaders as they load."""

    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
        if fullname != _PACKAGE and not fullname.startswith(_PACKAGE_PREFIX):
            return None
        # The finders after this one answer exactly as they would have; this one
        # only wraps the loader they return for this package's own modules. Every
        # recorder is skipped, so installing the hook twice cannot wrap twice.
        for finder in sys.meta_path:
            if isinstance(finder, _RecordingFinder):
                continue
            spec = finder.find_spec(fullname, path, target)
            if spec is not None:
                break
        else:
            return None
        loader = spec.loader
        if loader is not None and isinstance(loader, SourceFileLoader):
            spec.loader = _RecordingLoader(loader)
        return spec


_FINDER = _RecordingFinder()


def install() -> None:
    """Record this package's source digests from load time on. Idempotent."""
    if not any(isinstance(finder, _RecordingFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _FINDER)

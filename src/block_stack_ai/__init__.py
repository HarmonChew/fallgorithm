"""Stage 0 tools for reproducible Block Stack frame-input experiments."""

from .sourceidentity import install as _install_source_identity

# Installed before any submodule can be imported, so every ``block_stack_ai``
# module loaded in this process has its source identity fixed at load time.
_install_source_identity()

__version__ = "0.1.0"

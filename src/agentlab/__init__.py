"""agentlab: a terminal coding-assistant agent with a pluggable model provider."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentlab")
except PackageNotFoundError:
    # running from a source tree that was never installed
    __version__ = "0+unknown"

__all__ = ["__version__"]

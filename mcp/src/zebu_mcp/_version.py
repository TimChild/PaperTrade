"""Single source of truth for the package version.

Kept separate from ``__init__.py`` so the build backend doesn't have to
import the whole package to compute the version (the package imports
``mcp`` and ``httpx``, which we don't want as build-time deps).
"""

__version__ = "0.1.0"

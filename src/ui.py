"""HTML frontend loader for NiyamAI.

The actual HTML/CSS/JS lives in templates/index.html so it can be edited
without touching Python code. This module exposes a single HTMLPage.get_html()
method for the FastAPI route.
"""

from pathlib import Path

_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "index.html"


class HTMLPage:
    _cached: str | None = None

    @classmethod
    def get_html(cls) -> str:
        """Return the frontend HTML, caching after first read."""
        if cls._cached is None:
            cls._cached = _TEMPLATE_PATH.read_text(encoding="utf-8")
        return cls._cached

    @classmethod
    def invalidate_cache(cls) -> None:
        """Force re-read of template on next request (useful in dev)."""
        cls._cached = None

"""Vendored third-party assets."""

from store.paths import VENDOR_DIR

AXE_VERSION = "4.14.1"


def axe_source() -> str:
    """Source of the vendored axe-core (MPL-2.0; licence beside it)."""
    return (VENDOR_DIR / "axe-core" / "axe.min.js").read_text(encoding="utf-8")

"""Provider-terms gate (FR35): no LLM Run starts without a dated, filled-in record."""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from contract.errors import ProviderTermsError
from store.paths import CONFIG_DIR

REQUIRED_TOPICS = ("Data retention", "Training use", "Zero data retention")
_DATE = re.compile(r"^Read on:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ProviderTerms:
    read_on: str  # ISO date
    topics: dict[str, str]


_PLACEHOLDERS = ("TODO", "TBD", "N/A", "NA", "?", "FILL")


def _is_placeholder(text: str) -> bool:
    t = text.strip().upper().rstrip(".")
    return not t or t.startswith("TODO") or t in _PLACEHOLDERS


def load_provider_terms(config_dir: Path = CONFIG_DIR, today: date | None = None) -> ProviderTerms:
    """Parse `provider_terms.md`; raise ProviderTermsError naming what is missing."""
    path = config_dir / "provider_terms.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ProviderTermsError(f"cannot read {path.name} in {config_dir}: {exc}") from exc
    match = _DATE.search(text)
    if not match:
        raise ProviderTermsError(
            f"{path.name}: set 'Read on: YYYY-MM-DD' to the date you read the terms"
        )
    try:
        read_on = date.fromisoformat(match.group(1))
    except ValueError as exc:
        raise ProviderTermsError(
            f"{path.name}: 'Read on' is not a real date: {match.group(1)}"
        ) from exc
    if read_on > (today or date.today()):
        raise ProviderTermsError(f"{path.name}: 'Read on' {read_on} is in the future")
    topics: dict[str, str] = {}
    missing = []
    for topic in REQUIRED_TOPICS:
        found = re.search(rf"^\s*[-*]\s*{re.escape(topic)}:[ \t]*(.*)$", text, re.MULTILINE)
        if not found or _is_placeholder(found.group(1)):
            missing.append(topic)
        else:
            topics[topic] = found.group(1).strip()
    if missing:
        raise ProviderTermsError(
            f"{path.name}: fill in {', '.join(missing)} before the first LLM Run"
        )
    return ProviderTerms(read_on.isoformat(), topics)


def require_provider_terms(config_dir: Path = CONFIG_DIR, today: date | None = None) -> str:
    """The gate. Returns the ISO date to store in the Run, or raises ProviderTermsError."""
    return load_provider_terms(config_dir, today).read_on

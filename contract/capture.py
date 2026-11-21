"""Capture models and the capture_hash rule (AD-3). Pure; no I/O."""

import hashlib
import re
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints

from contract.models import ContractModel

PAGE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"  # no separators, no leading dot
CAPTURE_HASH_PATTERN = r"^[0-9a-f]{64}$"
PageId = Annotated[str, StringConstraints(pattern=PAGE_ID_PATTERN)]
CaptureHash = Annotated[str, StringConstraints(pattern=CAPTURE_HASH_PATTERN)]


def is_valid_page_id(value: str) -> bool:
    return re.fullmatch(PAGE_ID_PATTERN, value) is not None


def is_valid_capture_hash(value: str) -> bool:
    return re.fullmatch(CAPTURE_HASH_PATTERN, value) is not None


# Artifact file names inside a Capture directory.
HTML = "page.html"
STYLES = "computed_styles.json"
A11Y = "accessibility_tree.yaml"
AXE = "axe_results.json"
FOCUS = "focus_trace.json"
CONTRAST = "contrast.json"
SCREENSHOT = "screenshot.png"

# capture_hash covers exactly these (AD-3): not screenshot bytes, not timestamps.
HASHED_ARTIFACTS = (HTML, A11Y, STYLES, AXE, FOCUS)
ALL_ARTIFACTS = (HTML, STYLES, A11Y, AXE, FOCUS, CONTRAST, SCREENSHOT)


class ArtifactEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    sha256: str
    size: int
    in_capture_hash: bool


class CaptureManifest(ContractModel):
    """Contents of capture.json: every artifact plus tool and focus-script versions."""

    page_id: PageId
    capture_hash: CaptureHash
    source: str  # page file name only, no local path
    viewport: tuple[int, int]
    artifacts: list[ArtifactEntry]
    versions: dict[str, str]
    blocked_requests: int = 0  # network requests the capture refused
    created_at: str  # ISO 8601 UTC; not part of capture_hash


class Capture(ContractModel):
    """A loaded Capture: what tools and auditors read."""

    manifest: CaptureManifest
    html: str
    computed_styles: dict[str, dict[str, Any]]  # canonical element path -> properties
    accessibility_tree: str
    axe_results: dict[str, Any]
    focus_trace: dict[str, Any]
    contrast: list[dict[str, Any]]
    screenshot_file: str  # file name inside the Capture directory


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_capture_hash(files: dict[str, bytes]) -> str:
    """Hash of the deterministic artifact list, in fixed order, names included."""
    digest = hashlib.sha256()
    for name in HASHED_ARTIFACTS:
        digest.update(name.encode() + b"\0" + sha256_hex(files[name]).encode() + b"\0")
    return digest.hexdigest()

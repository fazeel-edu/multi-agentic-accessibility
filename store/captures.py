"""Write and read immutable Captures at data/captures/{page_id}/{capture_hash}/ (AD-3)."""

import json
import os
import shutil
import tempfile
from pathlib import Path

from contract import capture as cap
from contract.capture import ArtifactEntry, Capture, CaptureManifest
from contract.errors import ContractError
from store.paths import CAPTURES_DIR

MANIFEST = "capture.json"


class CaptureError(ContractError):
    """A Capture is missing, incomplete or fails its integrity check."""


def capture_dir(page_id: str, capture_hash: str, root: Path = CAPTURES_DIR) -> Path:
    return root / page_id / capture_hash


def write_capture(
    page_id: str,
    files: dict[str, bytes],
    *,
    source: str,
    viewport: tuple[int, int],
    versions: dict[str, str],
    blocked_requests: int,
    created_at: str,
    root: Path = CAPTURES_DIR,
) -> CaptureManifest:
    """Write a Capture once. An existing Capture with the same hash is left untouched."""
    missing = set(cap.ALL_ARTIFACTS) - set(files)
    if missing:
        raise CaptureError(f"capture is missing artifacts: {sorted(missing)}")
    capture_hash = cap.compute_capture_hash(files)
    target = capture_dir(page_id, capture_hash, root)
    if (target / MANIFEST).exists():
        return read_manifest(page_id, capture_hash, root)
    manifest = CaptureManifest(
        page_id=page_id,
        capture_hash=capture_hash,
        source=source,
        viewport=viewport,
        artifacts=[
            ArtifactEntry(
                name=name,
                sha256=cap.sha256_hex(files[name]),
                size=len(files[name]),
                in_capture_hash=name in cap.HASHED_ARTIFACTS,
            )
            for name in cap.ALL_ARTIFACTS
        ],
        versions=versions,
        blocked_requests=blocked_requests,
        created_at=created_at,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".capture-", dir=target.parent))
    try:
        for name in cap.ALL_ARTIFACTS:
            (staging / name).write_bytes(files[name])
        (staging / MANIFEST).write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
        if target.exists():  # leftover of an interrupted write: no manifest, so not a Capture
            shutil.rmtree(target)
        os.replace(staging, target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def read_manifest(page_id: str, capture_hash: str, root: Path = CAPTURES_DIR) -> CaptureManifest:
    path = capture_dir(page_id, capture_hash, root) / MANIFEST
    try:
        return CaptureManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CaptureError(f"cannot read capture manifest {path}: {exc}") from exc


def capture_hashes(page_id: str, root: Path = CAPTURES_DIR) -> list[str]:
    """Hashes of all complete Captures stored for a page."""
    base = root / page_id
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if (p / MANIFEST).is_file())


def read_capture(page_id: str, capture_hash: str, root: Path = CAPTURES_DIR) -> Capture:
    """Load a Capture from files only, verifying every artifact against the manifest."""
    manifest = read_manifest(page_id, capture_hash, root)
    base = capture_dir(page_id, capture_hash, root)
    files: dict[str, bytes] = {}
    for entry in manifest.artifacts:
        try:
            files[entry.name] = (base / entry.name).read_bytes()
        except OSError as exc:
            raise CaptureError(f"capture {capture_hash} lacks {entry.name}: {exc}") from exc
        if cap.sha256_hex(files[entry.name]) != entry.sha256:
            raise CaptureError(
                f"capture {capture_hash}: {entry.name} does not match its recorded hash"
            )
    if cap.compute_capture_hash(files) != capture_hash or manifest.capture_hash != capture_hash:
        raise CaptureError(f"capture {capture_hash}: contents do not hash to the directory name")
    return Capture(
        manifest=manifest,
        html=files[cap.HTML].decode("utf-8"),
        computed_styles=json.loads(files[cap.STYLES]),
        accessibility_tree=files[cap.A11Y].decode("utf-8"),
        axe_results=json.loads(files[cap.AXE]),
        focus_trace=json.loads(files[cap.FOCUS]),
        contrast=json.loads(files[cap.CONTRAST]),
        screenshot_file=cap.SCREENSHOT,
    )

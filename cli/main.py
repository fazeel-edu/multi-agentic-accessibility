"""One command per stage. Usage: uv run systemc capture data/pages/fixture-01.html"""

import argparse
import sys
from pathlib import Path

from contract.errors import ContractError


def _capture(args: argparse.Namespace) -> int:
    from capture.capture import capture_page  # imported late: starts no browser until used

    manifest = capture_page(Path(args.page), args.page_id)
    if manifest.blocked_requests:
        sys.stderr.write(
            f"warning: {manifest.blocked_requests} remote or out-of-folder requests were blocked; "
            "the capture may be degraded\n"
        )
    sys.stdout.write(f"{manifest.page_id} {manifest.capture_hash}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="systemc")
    sub = parser.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture", help="capture a local page into data/captures/")
    cap.add_argument("page", help="path to a local HTML file")
    cap.add_argument("--page-id", help="defaults to the file name without extension")
    cap.set_defaults(func=_capture)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ContractError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

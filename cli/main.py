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


def make_runner():
    """The live session runner. Tests replace this; it needs ANTHROPIC_API_KEY."""
    from auditors.role_auditor.sdk_runner import SdkSessionRunner, require_api_key

    require_api_key()
    return SdkSessionRunner()


def _audit(args: argparse.Namespace) -> int:
    import asyncio
    import uuid
    from datetime import UTC, datetime

    from auditors.role_auditor.orchestrator import audit, run_state
    from auditors.role_auditor.role_runner import AgentContext
    from auditors.role_auditor.sdk_runner import versions
    from contract.enums import Phase, Role, System
    from contract.models import Run
    from postprocess import run as postprocess
    from store import captures, runs
    from store.config import load
    from store.ledger import Ledger, estimate_cost
    from store.roles import load_role_specs
    from store.terms import require_provider_terms

    phase = Phase(args.phase)
    loaded = load()
    specs = load_role_specs()
    exclude = frozenset(Role(r) for r in args.exclude)
    terms_date = require_provider_terms()  # refuses until the terms are read and dated
    hashes = captures.capture_hashes(args.page_id)
    if not hashes:
        raise ContractError(f"no capture for {args.page_id}; run `systemc capture` first")
    if not args.capture_hash and len(hashes) > 1:
        raise ContractError(f"{args.page_id} has {len(hashes)} captures; pass --capture-hash")
    capture_hash = args.capture_hash or hashes[0]
    capture = captures.read_capture(args.page_id, capture_hash)
    settings = loaded.config.settings
    estimate = estimate_cost(1, 1, settings.max_budget_usd, settings.cost_cap_usd, 7 - len(exclude))
    sys.stdout.write(estimate.describe() + "\n")
    if not estimate.within_cap:
        raise ContractError(
            "estimated cost is above the Cost Cap; raise the cap in config/settings.toml"
        )
    runner = make_runner()
    run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    ledger = Ledger.for_phase(phase.value, settings.cost_cap_usd, settings.max_budget_usd)
    model = loaded.config.model_for(phase)
    ctx = AgentContext(
        runner=runner,
        ledger=ledger,
        run_id=run_id,
        model=model,
        matrix=loaded.config.matrix,
        max_turns=settings.max_turns,
        max_budget_usd=settings.max_budget_usd,
        allow_resume=args.resume,
    )
    result = asyncio.run(audit(capture, specs, ctx, exclude))
    run = Run(
        run_id=run_id,
        system=System.ROLE_MULTI_AGENT,
        page_id=args.page_id,
        phase=phase,
        group_id=args.group_id or run_id,
        state=run_state(result.role_status),
        model_id=model.model_id,
        config_hash=loaded.config_hash,
        capture_hash=capture_hash,
        versions=versions(),
        variant=sorted(exclude),
        provider_terms_date=terms_date,
        role_status=result.role_status,
        priority_notes=result.priority_notes,
        usage=result.usage,
        seconds=result.seconds,
        started_at=started_at,
    )
    directory = runs.write_run(run, result)
    report = postprocess(result, capture, loaded.config.matrix, run)
    path = runs.write_report(report)
    failed = [s.role.value for s in result.role_status if s.state.value == "failed"]
    sys.stdout.write(
        f"{run_id} {run.state.value}: {len(report.issues)} issues, {len(report.unmapped_issues)} unmapped, "
        f"cost USD {result.usage.cost_usd:.2f} (SDK estimate)\n{path}\n"
    )
    if failed:
        sys.stderr.write(f"warning: failed roles: {', '.join(failed)}\n")
    _ = directory
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="systemc")
    sub = parser.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture", help="capture a local page into data/captures/")
    cap.add_argument("page", help="path to a local HTML file")
    cap.add_argument("--page-id", help="defaults to the file name without extension")
    cap.set_defaults(func=_capture)
    aud = sub.add_parser(
        "audit", help="audit a captured page with System C (needs ANTHROPIC_API_KEY)"
    )
    aud.add_argument("page_id")
    aud.add_argument("--capture-hash", help="defaults to the newest capture of the page")
    aud.add_argument("--phase", choices=["dev", "eval"], default="dev")
    aud.add_argument("--group-id", help="shared by repeated Runs of one page")
    aud.add_argument(
        "--exclude", action="append", default=[], help="ablation: leave a role out (repeatable)"
    )
    aud.add_argument(
        "--resume", action="store_true", help="allow a Run stopped at the Cost Cap to continue"
    )
    aud.set_defaults(func=_audit)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ContractError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

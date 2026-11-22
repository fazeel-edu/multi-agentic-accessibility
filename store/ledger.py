"""The one spend record: append-only JSONL, file-locked, reserve then settle (AD-8, FR32).

Every session reserves its `max_budget_usd` before it starts and settles with the final
cumulative cost the SDK reported when it ends. The Cost Cap check keeps a margin of one
session's budget because a session can overshoot its own budget. All costs are SDK estimates.
"""

import fcntl
import json
import os
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from contract.errors import CostCapReached, LedgerError, RunStopped

SCHEMA_VERSION = "1"
SESSIONS_PER_RUN = 7  # six Role Agents plus the Synthesis Agent


@dataclass(frozen=True)
class Reservation:
    reservation_id: str
    run_id: str
    session: str
    amount_usd: float


@dataclass(frozen=True)
class CostEstimate:
    sessions: int  # sessions if nothing is retried
    upper_bound_usd: float  # each of those sessions spends its whole budget
    worst_case_usd: float  # every session retried to the limit
    available_usd: float  # cap, or what is left of it
    margin_usd: float  # one session budget the cap check keeps free

    @property
    def within_cap(self) -> bool:
        return self.upper_bound_usd + self.margin_usd <= self.available_usd

    def describe(self) -> str:
        verdict = "within" if self.within_cap else "ABOVE"
        return (
            f"{self.sessions} sessions without retries, up to USD {self.upper_bound_usd:.2f} "
            f"(SDK estimate: per-session budgets summed); worst case with retries USD {self.worst_case_usd:.2f}. "
            f"{verdict} the USD {self.available_usd:.2f} available under the Cost Cap"
        )


def estimate_cost(
    pages: int,
    runs_per_page: int,
    session_budget_usd: float,
    cap_usd: float,
    sessions_per_run: int = SESSIONS_PER_RUN,
    max_attempts: int = 1,
    remaining_usd: float | None = None,
) -> CostEstimate:
    """Spend printed before any LLM stage. `max_attempts` is how many sessions one role can
    start at most (output-gate retry times provider retries); `remaining_usd` is the ledger's
    free budget when a ledger exists."""
    sessions = pages * runs_per_page * sessions_per_run
    return CostEstimate(
        sessions=sessions,
        upper_bound_usd=round(sessions * session_budget_usd, 2),
        worst_case_usd=round(sessions * max_attempts * session_budget_usd, 2),
        available_usd=cap_usd if remaining_usd is None else remaining_usd,
        margin_usd=session_budget_usd,
    )


def last_result_cost(results: Iterable[dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    """(total_cost_usd, model_usage) from the LAST result message of a session.

    The SDK reports cumulative values, so earlier messages are never added to later ones.
    """
    last: dict[str, Any] | None = None
    for r in results:
        if r.get("total_cost_usd") is not None:
            last = r
    if last is None:
        raise LedgerError("no result message with total_cost_usd to settle from")
    return float(last["total_cost_usd"]), dict(last.get("model_usage") or {})


class Ledger:
    @classmethod
    def for_phase(cls, phase: str, cap_usd: float, session_budget_usd: float) -> "Ledger":
        from store.paths import ledger_path

        return cls(ledger_path(phase), cap_usd, session_budget_usd)

    def __init__(self, path: Path, cap_usd: float, session_budget_usd: float) -> None:
        if cap_usd <= 0 or session_budget_usd <= 0:
            raise LedgerError("cap_usd and session_budget_usd must be positive")
        self.path = Path(path)
        self.cap_usd = cap_usd
        self.session_budget_usd = session_budget_usd

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path.with_name(self.path.name + ".lock"), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise LedgerError(f"{self.path.name} line {number} is not valid JSON") from exc
        return events

    def _append(self, event: dict[str, Any]) -> None:
        event = {
            "schema_version": SCHEMA_VERSION,
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            **event,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())

    @staticmethod
    def _totals(events: list[dict[str, Any]]) -> tuple[float, float]:
        """(settled cost, outstanding reserved amounts)."""
        reserved: dict[str, float] = {}
        settled = 0.0
        for e in events:
            if e["event"] == "reserve":
                reserved[e["reservation_id"]] = e["amount_usd"]
            elif e["event"] == "settle":
                reserved.pop(e["reservation_id"], None)
                settled += e["cost_usd"]
        return settled, sum(reserved.values())

    @staticmethod
    def _stopped(events: list[dict[str, Any]]) -> bool:
        """A stop applies to the whole phase ledger and lasts until an explicit resume."""
        state = False
        for e in events:
            if e["event"] in ("stop", "resume"):
                state = e["event"] == "stop"
        return state

    def spent(self) -> float:
        with self._locked():
            return self._totals(self._events())[0]

    def remaining(self) -> float:
        """Cap minus settled cost and outstanding reservations."""
        with self._locked():
            settled, outstanding = self._totals(self._events())
        return self.cap_usd - settled - outstanding

    def is_stopped(self) -> bool:
        with self._locked():
            return self._stopped(self._events())

    def reserve(
        self,
        run_id: str,
        session: str,
        amount_usd: float | None = None,
        *,
        allow_resume: bool = False,
    ) -> Reservation:
        """Reserve budget before a session starts.

        Raises RunStopped if the Run already stopped at the cap (unless `allow_resume`, the
        explicit flag), and CostCapReached, recording the stop, if the reservation does not fit.
        """
        amount = self.session_budget_usd if amount_usd is None else amount_usd
        if amount <= 0:
            raise LedgerError("reservation must be positive")
        with self._locked():
            events = self._events()
            if self._stopped(events):
                if not allow_resume:
                    raise RunStopped(
                        f"{self.path.name} stopped at the Cost Cap; raise the cap and pass --resume to continue"
                    )
                self._append({"event": "resume", "run_id": run_id})
            settled, outstanding = self._totals(events)
            if settled + outstanding + amount + self.session_budget_usd > self.cap_usd:
                self._append({"event": "stop", "run_id": run_id, "reason": "cost_cap"})
                raise CostCapReached(
                    f"cannot reserve USD {amount:.2f}: spent {settled:.2f}, reserved {outstanding:.2f}, "
                    f"cap {self.cap_usd:.2f} (margin of one session budget kept)"
                )
            reservation = Reservation(f"{run_id}:{session}:{len(events)}", run_id, session, amount)
            self._append(
                {
                    "event": "reserve",
                    "reservation_id": reservation.reservation_id,
                    "run_id": run_id,
                    "session": session,
                    "amount_usd": amount,
                }
            )
            return reservation

    def settle(
        self,
        reservation: Reservation,
        total_cost_usd: float,
        model_usage: dict[str, Any] | None = None,
    ) -> None:
        """Record the final cumulative cost of a session. Costs above the reservation are kept."""
        if total_cost_usd < 0:
            raise LedgerError("cost cannot be negative")
        with self._locked():
            events = self._events()
            open_ids = {e["reservation_id"] for e in events if e["event"] == "reserve"} - {
                e["reservation_id"] for e in events if e["event"] == "settle"
            }
            if reservation.reservation_id not in open_ids:
                raise LedgerError(
                    f"reservation {reservation.reservation_id} is unknown or already settled"
                )
            self._append(
                {
                    "event": "settle",
                    "reservation_id": reservation.reservation_id,
                    "run_id": reservation.run_id,
                    "session": reservation.session,
                    "cost_usd": float(total_cost_usd),
                    "model_usage": model_usage or {},
                }
            )

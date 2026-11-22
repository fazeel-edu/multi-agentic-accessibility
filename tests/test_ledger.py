import json
import threading

import pytest

from contract.errors import CostCapReached, LedgerError, RunStopped
from store.ledger import Ledger, estimate_cost, last_result_cost


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "results" / "ledger-dev.jsonl", cap_usd=10.0, session_budget_usd=1.0)


def lines(ledger):
    return [json.loads(x) for x in ledger.path.read_text().splitlines()]


def test_reserve_then_settle_updates_spend(ledger):
    r = ledger.reserve("run-1", "screen_reader")
    assert ledger.remaining() == pytest.approx(9.0) and ledger.spent() == 0
    ledger.settle(r, 0.4, {"claude-haiku-5-5": {"input_tokens": 10}})
    assert ledger.spent() == pytest.approx(0.4) and ledger.remaining() == pytest.approx(9.6)
    events = lines(ledger)
    assert [e["event"] for e in events] == ["reserve", "settle"]
    assert events[1]["model_usage"] == {"claude-haiku-5-5": {"input_tokens": 10}}
    assert all(e["schema_version"] == "1" and e["ts"].endswith("+00:00") for e in events)


def test_file_is_append_only(ledger):
    r = ledger.reserve("run-1", "a")
    first = ledger.path.read_text()
    ledger.settle(r, 0.1)
    assert ledger.path.read_text().startswith(first)


def test_settle_uses_the_last_cumulative_value_never_a_sum():
    results = [
        {"total_cost_usd": 0.10, "model_usage": {"m": {"output_tokens": 5}}},
        {"total_cost_usd": 0.30, "model_usage": {"m": {"output_tokens": 15}}},
        {"total_cost_usd": 0.50, "model_usage": {"m": {"output_tokens": 30}}},
        {"type": "assistant"},
    ]
    cost, usage = last_result_cost(results)
    assert cost == 0.50 and usage == {"m": {"output_tokens": 30}}
    with pytest.raises(LedgerError):
        last_result_cost([{"type": "assistant"}])


def test_double_settle_and_unknown_reservation_rejected(ledger, tmp_path):
    r = ledger.reserve("run-1", "a")
    ledger.settle(r, 0.2)
    with pytest.raises(LedgerError):
        ledger.settle(r, 0.2)
    other = Ledger(tmp_path / "other.jsonl", 10.0, 1.0)
    with pytest.raises(LedgerError):
        other.settle(r, 0.1)
    with pytest.raises(LedgerError):
        ledger.settle(ledger.reserve("run-1", "b"), -1)


def test_cap_blocks_new_sessions_but_not_settling_in_flight(ledger):
    held = [ledger.reserve("run-1", f"s{i}") for i in range(9)]  # 9 held + 1 margin = cap 10
    with pytest.raises(CostCapReached):
        ledger.reserve("run-1", "s9")
    assert ledger.is_stopped()
    for r in held:  # in-flight sessions finish and settle
        ledger.settle(r, 0.9)
    assert ledger.spent() == pytest.approx(8.1)


def test_margin_of_one_session_budget_is_kept(tmp_path):
    ledger = Ledger(tmp_path / "l.jsonl", cap_usd=3.0, session_budget_usd=1.0)
    ledger.reserve("r", "a")
    ledger.reserve("r", "b")  # 1 + 1 + margin 1 = 3: fits exactly
    with pytest.raises(CostCapReached):
        ledger.reserve("r", "c")


def test_overshoot_is_recorded_and_counts_against_the_cap(ledger):
    r = ledger.reserve("run-1", "a")
    ledger.settle(r, 1.7)  # session overshot its own budget
    assert ledger.spent() == pytest.approx(1.7) and ledger.remaining() == pytest.approx(8.3)


def test_stopped_run_does_not_resume_silently(ledger):
    for i in range(9):
        ledger.reserve("run-1", f"s{i}")
    with pytest.raises(CostCapReached):
        ledger.reserve("run-1", "x")
    with pytest.raises(RunStopped):
        ledger.reserve("run-1", "y")
    assert ledger.is_stopped()  # the stop covers the whole phase ledger, not one run id
    with pytest.raises(RunStopped):
        ledger.reserve("run-2", "y")
    with pytest.raises(CostCapReached):  # explicit flag lifts the stop, but the cap still applies
        ledger.reserve("run-1", "z", allow_resume=True)
    assert [e["event"] for e in lines(ledger)].count("resume") == 1


def test_resume_flag_allows_work_once_budget_frees_up(tmp_path):
    ledger = Ledger(tmp_path / "l.jsonl", cap_usd=3.0, session_budget_usd=1.0)
    a = ledger.reserve("r", "a")
    ledger.reserve("r", "b")
    with pytest.raises(CostCapReached):
        ledger.reserve("r", "c")
    ledger.settle(a, 0.0)  # a finished without cost, freeing its reservation
    with pytest.raises(RunStopped):
        ledger.reserve("r", "c")
    assert ledger.reserve("r", "c", allow_resume=True).session == "c"
    assert not ledger.is_stopped()


def test_parallel_reservations_never_exceed_the_cap(tmp_path):
    path = tmp_path / "l.jsonl"
    granted, refused = [], []

    def worker(i):
        ledger = Ledger(path, cap_usd=10.0, session_budget_usd=1.0)  # separate handle per thread
        try:
            granted.append(ledger.reserve("run-1", f"s{i}", allow_resume=True))
        except (CostCapReached, RunStopped):
            refused.append(i)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(40)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(granted) == 9 and len(refused) == 31  # 9 + margin 1 = cap 10
    events = [json.loads(x) for x in path.read_text().splitlines()]  # every line intact
    assert sum(e["amount_usd"] for e in events if e["event"] == "reserve") == 9.0


def test_corrupt_ledger_line_is_an_error_not_silently_ignored(ledger):
    ledger.reserve("run-1", "a")
    with open(ledger.path, "a") as f:
        f.write("{not json\n")
    with pytest.raises(LedgerError, match="line 2"):
        ledger.remaining()


def test_invalid_construction_and_amounts(tmp_path, ledger):
    with pytest.raises(LedgerError):
        Ledger(tmp_path / "x.jsonl", 0, 1)
    with pytest.raises(LedgerError):
        ledger.reserve("r", "a", 0)


def test_estimate_before_an_llm_stage():
    est = estimate_cost(pages=10, runs_per_page=3, session_budget_usd=1.0, cap_usd=50.0)
    assert est.sessions == 210 and est.upper_bound_usd == 210.0 and not est.within_cap
    assert est.worst_case_usd == 210.0
    text = est.describe()
    assert "210 sessions" in text and "ABOVE" in text and "SDK estimate" in text
    small = estimate_cost(1, 1, 1.0, 50.0)
    assert small.sessions == 7 and small.within_cap and "within" in small.describe()


def test_ledger_is_built_from_config_and_phase(tmp_path, monkeypatch):
    from store import paths
    from store.config import load

    monkeypatch.setattr(paths, "RESULTS_DIR", tmp_path)
    cfg = load().config.settings
    led = Ledger.for_phase("dev", cfg.cost_cap_usd, cfg.max_budget_usd)
    assert led.path == tmp_path / "ledger-dev.jsonl" and led.cap_usd == cfg.cost_cap_usd


def test_estimate_shows_worst_case_and_uses_what_is_left():
    est = estimate_cost(1, 1, 1.0, 50.0, max_attempts=6, remaining_usd=8.0)
    assert (est.upper_bound_usd, est.worst_case_usd, est.available_usd) == (7.0, 42.0, 8.0)
    assert est.within_cap  # 7 plus one session of margin is exactly 8
    assert "worst case with retries USD 42.00" in est.describe()


def test_estimate_checks_the_margin():
    assert estimate_cost(1, 1, 1.0, 50.0, remaining_usd=8.0).within_cap
    assert not estimate_cost(1, 1, 1.0, 50.0, remaining_usd=7.5).within_cap

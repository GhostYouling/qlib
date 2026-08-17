import ast
import importlib.util
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign124_new_share.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "a_share_three_day_walkforward_campaign124_new_share", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(**updates):
    value = {
        "ts_code": "600519.SH",
        "ipo_date": "20250102",
        "issue_date": "20250106",
        "ballot": 0.05,
    }
    value.update(updates)
    return value


def weekday_calendar(start: date, count: int) -> list[str]:
    sessions = []
    current = start
    while len(sessions) < count:
        if current.weekday() < 5:
            sessions.append(current.isoformat())
        current += timedelta(days=1)
    return sessions


def test_contract_is_bound_and_module_has_no_transport_or_credentials() -> None:
    module = load_module()
    module.assert_frozen_contract()
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported.isdisjoint(
        {"requests", "httpx", "urllib", "socket", "tushare", "dotenv", "os"}
    )


def test_exact_projection_forbids_name_price_pe_size_and_funds() -> None:
    module = load_module()
    events, stats = module.canonicalize_new_share_rows([row(), row()])
    assert events == [
        {
            "instrument": "SH600519",
            "ipo_date": "20250102",
            "issue_date": "20250106",
            "ballot": 0.05,
            "provider": "tushare_new_share",
        }
    ]
    assert stats["exact_repeated_events_collapsed"] == 1
    for forbidden in ("name", "price", "pe", "amount", "funds"):
        with pytest.raises(module.Campaign124ContractError):
            module.canonicalize_new_share_rows([dict(row(), **{forbidden: 1})])


@pytest.mark.parametrize(
    "ballot", [None, "0.05", True, float("nan"), float("inf"), 0.0, -0.1, 100.1]
)
def test_ballot_must_be_finite_numeric_positive_percentage(ballot) -> None:
    module = load_module()
    with pytest.raises(module.Campaign124ContractError, match="ballot"):
        module.canonicalize_new_share_rows([row(ballot=ballot)])


def test_dates_codes_duplicates_and_conflicts_fail_closed() -> None:
    module = load_module()
    with pytest.raises(module.Campaign124ContractError, match="issue_date"):
        module.canonicalize_new_share_rows([row(issue_date="20250101")])
    with pytest.raises(module.Campaign124ContractError, match="ipo_date"):
        module.canonicalize_new_share_rows([row(ipo_date="2025-01-02")])
    with pytest.raises(module.Campaign124ContractError):
        module.canonicalize_new_share_rows([row(ts_code="000001.SH")])
    _, stats = module.canonicalize_new_share_rows([row(ts_code="688001.SH")])
    assert stats["unsupported_complete_codes_excluded"] == 1
    with pytest.raises(module.Campaign124ContractError, match="conflicting"):
        module.canonicalize_new_share_rows([row(), row(ballot=0.06)])


def test_score_is_negative_ballot_only_at_listing_ages_20_through_79() -> None:
    module = load_module()
    events, _ = module.canonicalize_new_share_rows([row(ballot=0.05)])
    calendar = weekday_calendar(date(2025, 1, 6), 90)
    assert (
        module.ipo_ballot_scarcity_on_session(
            events, calendar, "SH600519", calendar[18]
        )
        is None
    )
    assert module.ipo_ballot_scarcity_on_session(
        events, calendar, "SH600519", calendar[19]
    ) == pytest.approx(-0.05)
    assert module.ipo_ballot_scarcity_on_session(
        events, calendar, "SH600519", calendar[78]
    ) == pytest.approx(-0.05)
    assert (
        module.ipo_ballot_scarcity_on_session(
            events, calendar, "SH600519", calendar[79]
        )
        is None
    )


def test_listing_age_does_not_change_score_inside_support() -> None:
    module = load_module()
    events, _ = module.canonicalize_new_share_rows([row(ballot=0.08)])
    calendar = weekday_calendar(date(2025, 1, 6), 80)
    scores = [
        module.ipo_ballot_scarcity_on_session(
            events, calendar, "SH600519", calendar[index]
        )
        for index in (19, 40, 78)
    ]
    assert scores == pytest.approx([-0.08, -0.08, -0.08])


def test_issue_date_must_be_calendar_session_and_absence_is_missing() -> None:
    module = load_module()
    events, _ = module.canonicalize_new_share_rows(
        [row(issue_date="20250105", ipo_date="20250102")]
    )
    calendar = weekday_calendar(date(2025, 1, 6), 30)
    with pytest.raises(module.Campaign124ContractError, match="issue_date"):
        module.ipo_ballot_scarcity_on_session(
            events, calendar, "SH600519", calendar[20]
        )
    assert (
        module.ipo_ballot_scarcity_on_session([], calendar, "SH600519", calendar[20])
        is None
    )

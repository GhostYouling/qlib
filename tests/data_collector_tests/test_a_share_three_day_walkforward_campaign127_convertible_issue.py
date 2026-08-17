import ast
import importlib.util
import math
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign127_convertible_issue.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "a_share_three_day_walkforward_campaign127_convertible_issue", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def basic_row(**updates):
    value = {
        "ts_code": "110001.SH",
        "stk_code": "600519.SH",
        "cb_type": "CB",
    }
    value.update(updates)
    return value


def issue_row(**updates):
    value = {
        "ts_code": "110001.SH",
        "ann_date": "20240102",
        "res_ann_date": "20240105",
        "onl_pch_excess": 125.0,
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


def test_exact_projections_join_and_collapse_identical_repeats() -> None:
    module = load_module()
    events, stats = module.canonicalize_convertible_issue_rows(
        [basic_row(), basic_row()], [issue_row(), issue_row()]
    )
    assert events == [
        {
            "instrument": "SH600519",
            "bond_code": "110001.SH",
            "ann_date": "20240102",
            "res_ann_date": "20240105",
            "online_excess_multiple": 125.0,
            "provider": "tushare_cb_issue",
        }
    ]
    assert stats["exact_basic_repeats_collapsed"] == 1
    assert stats["exact_issue_repeats_collapsed"] == 1
    assert stats["network_or_credential_access_performed"] is False


def test_extra_or_missing_source_fields_fail_closed() -> None:
    module = load_module()
    with pytest.raises(module.Campaign127ContractError, match="three-field"):
        module.canonicalize_convertible_issue_rows(
            [dict(basic_row(), bond_short_name="x")], [issue_row()]
        )
    with pytest.raises(module.Campaign127ContractError, match="four-field"):
        module.canonicalize_convertible_issue_rows(
            [basic_row()], [dict(issue_row(), issue_size=10.0)]
        )


@pytest.mark.parametrize(
    "multiple", [None, "125", True, float("nan"), float("inf"), 0.0, -1.0]
)
def test_online_excess_multiple_must_be_finite_numeric_positive(multiple) -> None:
    module = load_module()
    with pytest.raises(module.Campaign127ContractError, match="onl_pch_excess"):
        module.canonicalize_convertible_issue_rows(
            [basic_row()], [issue_row(onl_pch_excess=multiple)]
        )


def test_non_cb_and_unsupported_underlyings_are_excluded_and_counted() -> None:
    module = load_module()
    basics = [
        basic_row(ts_code="132001.SH", cb_type="EB"),
        basic_row(ts_code="110002.SH", stk_code="688001.SH"),
    ]
    issues = [
        issue_row(ts_code="132001.SH"),
        issue_row(ts_code="110002.SH"),
    ]
    events, stats = module.canonicalize_convertible_issue_rows(basics, issues)
    assert events == []
    assert stats["non_cb_issues_excluded"] == 1
    assert stats["unsupported_underlying_issues_excluded"] == 1


def test_missing_mapping_and_conflicting_duplicates_fail_closed() -> None:
    module = load_module()
    with pytest.raises(module.Campaign127ContractError, match="lacks cb_basic"):
        module.canonicalize_convertible_issue_rows([], [issue_row()])
    with pytest.raises(module.Campaign127ContractError, match="conflicting cb_basic"):
        module.canonicalize_convertible_issue_rows(
            [basic_row(), basic_row(stk_code="600000.SH")], [issue_row()]
        )
    with pytest.raises(module.Campaign127ContractError, match="conflicting cb_issue"):
        module.canonicalize_convertible_issue_rows(
            [basic_row()], [issue_row(), issue_row(onl_pch_excess=126.0)]
        )


def test_codes_types_and_dates_are_strict() -> None:
    module = load_module()
    with pytest.raises(module.Campaign127ContractError, match="prefix conflicts"):
        module.canonicalize_convertible_issue_rows(
            [basic_row(ts_code="128001.SH")], [issue_row(ts_code="128001.SH")]
        )
    with pytest.raises(module.Campaign127ContractError, match="stk_code"):
        module.canonicalize_convertible_issue_rows(
            [basic_row(stk_code="000001.SH")], [issue_row()]
        )
    with pytest.raises(module.Campaign127ContractError, match="cb_type"):
        module.canonicalize_convertible_issue_rows(
            [basic_row(cb_type=" CB")], [issue_row()]
        )
    with pytest.raises(module.Campaign127ContractError, match="ann_date"):
        module.canonicalize_convertible_issue_rows(
            [basic_row()], [issue_row(ann_date="2024-01-02")]
        )
    with pytest.raises(module.Campaign127ContractError, match="must not precede"):
        module.canonicalize_convertible_issue_rows(
            [basic_row()], [issue_row(res_ann_date="20240101")]
        )


def test_score_uses_strictly_prior_result_and_180_calendar_day_support() -> None:
    module = load_module()
    events, _ = module.canonicalize_convertible_issue_rows(
        [basic_row()], [issue_row(onl_pch_excess=9.0)]
    )
    calendar = weekday_calendar(date(2024, 1, 5), 160)
    assert (
        module.convertible_issue_online_demand_on_session(
            events, calendar, "SH600519", "2024-01-05"
        )
        is None
    )
    assert module.convertible_issue_online_demand_on_session(
        events, calendar, "SH600519", "2024-01-08"
    ) == pytest.approx(math.log1p(9.0))
    assert module.convertible_issue_online_demand_on_session(
        events, calendar, "SH600519", "2024-07-03"
    ) == pytest.approx(math.log1p(9.0))
    assert (
        module.convertible_issue_online_demand_on_session(
            events, calendar, "SH600519", "2024-07-04"
        )
        is None
    )


def test_latest_supported_event_is_used_without_age_weighting() -> None:
    module = load_module()
    basics = [basic_row(), basic_row(ts_code="110002.SH")]
    issues = [
        issue_row(onl_pch_excess=9.0),
        issue_row(
            ts_code="110002.SH",
            ann_date="20240201",
            res_ann_date="20240205",
            onl_pch_excess=99.0,
        ),
    ]
    events, _ = module.canonicalize_convertible_issue_rows(basics, issues)
    calendar = weekday_calendar(date(2024, 1, 2), 180)
    score_a = module.convertible_issue_online_demand_on_session(
        events, calendar, "SH600519", "2024-02-06"
    )
    score_b = module.convertible_issue_online_demand_on_session(
        events, calendar, "SH600519", "2024-03-06"
    )
    assert score_a == pytest.approx(math.log1p(99.0))
    assert score_b == pytest.approx(score_a)


def test_same_stock_same_latest_result_date_multi_bond_tie_is_fatal() -> None:
    module = load_module()
    basics = [basic_row(), basic_row(ts_code="110002.SH")]
    issues = [issue_row(), issue_row(ts_code="110002.SH")]
    events, _ = module.canonicalize_convertible_issue_rows(basics, issues)
    calendar = weekday_calendar(date(2024, 1, 2), 30)
    with pytest.raises(module.Campaign127ContractError, match="multiple bonds"):
        module.convertible_issue_online_demand_on_session(
            events, calendar, "SH600519", "2024-01-08"
        )


def test_absence_wrong_provider_and_invalid_calendar_fail_or_stay_missing() -> None:
    module = load_module()
    calendar = weekday_calendar(date(2024, 1, 2), 30)
    assert (
        module.convertible_issue_online_demand_on_session(
            [], calendar, "SH600519", "2024-01-08"
        )
        is None
    )
    events, _ = module.canonicalize_convertible_issue_rows([basic_row()], [issue_row()])
    events[0]["provider"] = "other"
    with pytest.raises(module.Campaign127ContractError, match="provider"):
        module.convertible_issue_online_demand_on_session(
            events, calendar, "SH600519", "2024-01-08"
        )
    with pytest.raises(module.Campaign127ContractError, match="strictly increasing"):
        module.convertible_issue_online_demand_on_session(
            [], ["2024-01-03", "2024-01-02"], "SH600519", "2024-01-02"
        )

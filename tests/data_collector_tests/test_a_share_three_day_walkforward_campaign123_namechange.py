import ast
import importlib.util
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign123_namechange.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "a_share_three_day_walkforward_campaign123_namechange", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(**updates):
    value = {
        "ts_code": "600519.SH",
        "start_date": "20250103",
        "end_date": None,
        "ann_date": "20250102",
        "change_reason": "改名",
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


def test_contract_is_bound_and_module_has_no_transport_or_credential_access() -> None:
    module = load_module()
    module.assert_frozen_contract()
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots.isdisjoint(
        {"requests", "httpx", "urllib", "socket", "tushare", "dotenv"}
    )
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "os.environ" not in source
    assert "__main__" not in source


def test_projection_is_exact_and_name_field_is_mechanically_forbidden() -> None:
    module = load_module()
    events, stats = module.canonicalize_pure_rename_rows([row(), row()])
    assert events == [
        {
            "instrument": "SH600519",
            "start_date": "20250103",
            "ann_date": "20250102",
            "end_date": None,
            "change_reason": "改名",
            "provider": "tushare_namechange",
        }
    ]
    assert stats["exact_repeated_events_collapsed"] == 1
    assert stats["security_name_read_requested_or_persisted"] is False
    with pytest.raises(module.NamechangeContractError):
        module.canonicalize_pure_rename_rows([dict(row(), name="forbidden")])
    with pytest.raises(module.NamechangeContractError):
        incomplete = row()
        incomplete.pop("ann_date")
        module.canonicalize_pure_rename_rows([incomplete])


def test_exact_reason_filter_excludes_st_share_reform_and_unknown_rows() -> None:
    module = load_module()
    reasons = ["ST", "撤销ST", "完成股改", "未股改加S", "其他", " 改名"]
    events, stats = module.canonicalize_pure_rename_rows(
        [
            row(start_date=f"202501{index + 3:02d}", change_reason=reason)
            for index, reason in enumerate(reasons)
        ]
    )
    assert events == []
    assert stats["non_pure_reason_rows_excluded"] == len(reasons)
    with pytest.raises(module.NamechangeContractError):
        module.canonicalize_pure_rename_rows([row(change_reason=None)])


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"start_date": "2025-01-03"}, "start_date"),
        ({"start_date": "20250230"}, "start_date"),
        ({"ann_date": ""}, "ann_date"),
        ({"end_date": "20250102"}, "end_date"),
    ],
)
def test_dates_are_strict_and_end_cannot_precede_start(updates, message) -> None:
    module = load_module()
    with pytest.raises(module.NamechangeContractError, match=message):
        module.canonicalize_pure_rename_rows([row(**updates)])


def test_supported_unsupported_and_cross_exchange_codes_fail_closed() -> None:
    module = load_module()
    events, stats = module.canonicalize_pure_rename_rows(
        [
            row(ts_code="000001.SZ"),
            row(ts_code="300750.SZ", start_date="20250104"),
            row(ts_code="688001.SH", start_date="20250105"),
        ]
    )
    assert [event["instrument"] for event in events] == ["SZ000001", "SZ300750"]
    assert stats["unsupported_complete_codes_excluded"] == 1
    with pytest.raises(module.NamechangeContractError):
        module.canonicalize_pure_rename_rows([row(ts_code="000001.SH")])
    with pytest.raises(module.NamechangeContractError):
        module.canonicalize_pure_rename_rows([row(ts_code="600519.SZ")])


def test_same_identity_conflicts_are_fatal_even_across_reason_categories() -> None:
    module = load_module()
    with pytest.raises(module.NamechangeContractError):
        module.canonicalize_pure_rename_rows([row(), row(ann_date="20250104")])
    with pytest.raises(module.NamechangeContractError):
        module.canonicalize_pure_rename_rows([row(), row(change_reason="ST")])


def test_availability_is_strictly_after_max_start_and_announcement_date() -> None:
    module = load_module()
    events, _ = module.canonicalize_pure_rename_rows(
        [row(start_date="20250103", ann_date="20250106")]
    )
    calendar = weekday_calendar(date(2025, 1, 2), 65)
    assert (
        module.pure_rename_recency_on_session(
            events, calendar, "SH600519", "2025-01-06"
        )
        is None
    )
    assert module.pure_rename_recency_on_session(
        events, calendar, "SH600519", "2025-01-07"
    ) == pytest.approx(1.0)


def test_age_zero_age_59_age_60_and_latest_event_rules_are_exact() -> None:
    module = load_module()
    calendar = weekday_calendar(date(2025, 1, 2), 90)
    first, _ = module.canonicalize_pure_rename_rows(
        [row(start_date="20250102", ann_date="20250102")]
    )
    assert module.pure_rename_recency_on_session(
        first, calendar, "SH600519", calendar[1]
    ) == pytest.approx(1.0)
    assert module.pure_rename_recency_on_session(
        first, calendar, "SH600519", calendar[60]
    ) == pytest.approx(0.0)
    assert (
        module.pure_rename_recency_on_session(first, calendar, "SH600519", calendar[61])
        is None
    )

    latest, _ = module.canonicalize_pure_rename_rows(
        [
            row(start_date="20250102", ann_date="20250102"),
            row(start_date="20250110", ann_date="20250110"),
        ]
    )
    assert module.pure_rename_recency_on_session(
        latest, calendar, "SH600519", "2025-01-13"
    ) == pytest.approx(1.0)
    assert (
        module.pure_rename_recency_on_session(
            latest, calendar, "SZ000001", "2025-01-13"
        )
        is None
    )


def test_calendar_and_normalized_event_shape_are_strict() -> None:
    module = load_module()
    events, _ = module.canonicalize_pure_rename_rows([row()])
    with pytest.raises(module.NamechangeContractError):
        module.pure_rename_recency_on_session(
            events, ["2025-01-06", "2025-01-03"], "SH600519", "2025-01-03"
        )
    with pytest.raises(module.NamechangeContractError):
        module.pure_rename_recency_on_session(
            [dict(events[0], extra="forbidden")],
            ["2025-01-03", "2025-01-06"],
            "SH600519",
            "2025-01-06",
        )

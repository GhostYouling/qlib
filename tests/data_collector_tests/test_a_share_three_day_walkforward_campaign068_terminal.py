from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CAMPAIGN_ROOT = (
    ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_068"
)
AUDIT = (
    CAMPAIGN_ROOT
    / "no_return/20260805T185838Z_campaign068_no_return_audit.json"
)
ATTEMPTS = CAMPAIGN_ROOT / "research_attempt_ledger_v3.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_068_research_record.json"
FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_068_terminal_completion_freeze_20260806.json"
)
STATUS = ROOT / "docs/a_share_three_day_iteration_status_20260806_campaign068_terminal_v2.json"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
FACTOR = "quarterly_profit_revenue_acceleration_rank_gap_2r"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign068_terminal_artifact_bindings_are_current() -> None:
    assert _sha256(RECORD) == "e8711163c8bce0136dc44b7fe42daa07655b43a37fb325798b75a8c351cafbfc"
    assert _sha256(FREEZE) == "a0ff4bfd89bfe27b404567a8d1aca9544df4192cdbfacd7d3f7212e5846ca9b0"
    assert _sha256(STATUS) == "ec9ee183c729410e55061e82f62ba3cab21bccc86e2097767bb03778be734f1e"
    for path, count in ((RECORD, 22), (FREEZE, 6), (STATUS, 12)):
        receipt = validator.validate_record(path, data_root=DATA_ROOT)
        assert receipt["all_bindings_passed"] is True
        assert receipt["binding_count"] == count


def test_campaign068_coverage_failure_stops_before_cache_and_returns() -> None:
    assert _sha256(AUDIT) == "897e308897f5adf83361914bc9543b437ed125d1c34839babe86cdd7f8676c16"
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    assert coverage["median_coverage"] == 0.9945939627713977
    assert coverage["p05_coverage"] == 0.0
    assert coverage["eligible_names_p05"] == 0.0
    assert coverage["gate_passed_before_comparison_values"] is False
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is False
    assert uniqueness["compact_cache_values_read"] is False
    assert uniqueness["comparison_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["admissible_factor_count"] == 0


def test_campaign068_attempt_accounting_is_append_only() -> None:
    assert _sha256(ATTEMPTS) == "c344deb24710ec66aa0dbc160bb685e70e93c07526236a14ca2f1d199d9f8351"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign068_attempt_count"] == 6
    assert ledger["campaign068_ledger_entry_count"] == 6
    assert ledger["campaign068_infrastructure_or_synthetic_failure_count"] == 5
    assert ledger["campaign068_complete_factor_attempt_count"] == 1
    assert ledger["campaign068_historical_return_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 408
    assert ledger["cumulative_return_reading_development_trial_count"] == 274


def test_campaign068_candidate49_ledgers_are_unchanged() -> None:
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(SIGNAL_LEDGER).get("entries", []) == []
    assert _load(EXECUTION_LEDGER).get("entries", []) == []


def test_unified_report_has_one_campaign068_terminal_section() -> None:
    report = UNIFIED_REPORT.read_text(encoding="utf-8")
    assert _sha256(UNIFIED_REPORT) == "131db25a3b9865c798c94ead4c2d815d55a11cdfabfd75412baddac6b6fc69df"
    assert report.count("## 历史滚动 Campaign068 权威追加") == 1
    assert "中位覆盖为 `99.459396%`" in report
    assert "P05 覆盖与 P05 合格名称数均为 `0`" in report

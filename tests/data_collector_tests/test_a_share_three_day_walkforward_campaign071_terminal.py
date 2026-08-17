from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator
from scripts import a_share_tushare_candidate49_future_execution as execution


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CAMPAIGN_ROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_071"
AUDIT = CAMPAIGN_ROOT / "no_return/20260805T211659Z_campaign071_no_return_audit.json"
ATTEMPTS = CAMPAIGN_ROOT / "research_attempt_ledger_v2.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_071_research_record.json"
CAMPAIGN_REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_071_report.md"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
SIGNAL_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FACTOR = "quarterly_net_profit_scale_rank"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign071_research_record_bindings_are_current() -> None:
    assert _sha256(RECORD) == "414ea6ae1083e3b5e21c91de9719c0c2b201ba11e6b8af0fe77889da46d1ce56"
    receipt = validator.validate_record(RECORD, data_root=DATA_ROOT)
    assert receipt["all_bindings_passed"] is True
    assert receipt["binding_count"] == 12


def test_campaign071_snapshot_identity_is_current_without_rebuilding() -> None:
    manifest = _load(
        DATA_ROOT
        / "derived/a_share/rich/tushare/minute_walkforward_campaign071_feature_library"
        / "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign071_feature_library_v1"
        / "snapshot_manifest.json"
    )
    assert manifest["dataset_sha256"] == "8c6f1eff1b2238132f429eaeae13d9a7fbd9956e89f3499fa1cf68d54435528d"
    assert len(manifest["files"]) == 33015
    assert sum(int(item["rows"]) for item in manifest["files"]) == 7724498
    assert manifest["factor_eligible_rows"][FACTOR] == 7081458


def test_campaign071_no_return_rejection_is_exact() -> None:
    assert _sha256(AUDIT) == "5f54b96477a7d0003c42545b49c0bae46257f15f908f6b9475bfa1e5ded5e5fc"
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert coverage["eligible_names_p05"] == 138.0
    assert uniqueness["comparison_factor_count"] == 101
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert len(failed) == 1
    assert failed[0]["comparison_factor"] == "quarterly_roe_profit_scale_efficiency_gap_2r"
    assert failed[0]["median_daily_rank_correlation"] == -0.8058886587328898
    assert failed[0]["absolute_median_daily_rank_correlation"] == 0.8058886587328898
    assert failed[0]["pairwise_sessions"] == 1623
    assert audit["admissible_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["provider_request_issued"] is False


def test_campaign071_attempt_accounting_and_reports_are_current() -> None:
    assert _sha256(ATTEMPTS) == "52ff8595367035ea2025eb8c3d8c075329fdd3bd6e0622eafa178e6e53966883"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign071_ledger_entry_count"] == 7
    assert ledger["campaign071_infrastructure_failure_count"] == 6
    assert ledger["campaign071_complete_factor_attempt_count"] == 1
    assert ledger["campaign071_attempt_count"] == 7
    assert ledger["cumulative_historical_research_attempt_count"] == 426
    assert ledger["cumulative_return_reading_development_trial_count"] == 275
    assert _sha256(CAMPAIGN_REPORT) == "019d17028184ebc04b4529d499bed2348f3737363ab3f91b29d113304fd14752"
    assert _sha256(UNIFIED_REPORT) == "433355db6c4e448633ff73e6e6ea6473860421f1a381e24dd1037f4a3ef2ffe8"
    report = UNIFIED_REPORT.read_text(encoding="utf-8")
    assert report.count("## 历史滚动 Campaign071 权威追加") == 1
    assert "中位日秩相关为 `-0.805889`" in report
    assert "未创建开发预注册" in report
    assert "累计历史研究尝试 426" in report


def test_campaign071_preserves_candidate49_semantics_and_empty_ledgers() -> None:
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(SIGNAL_LEDGER)["entries"] == []
    assert _load(EXECUTION_LEDGER)["entries"] == []
    payload = execution.validate_reporting_state(
        signal_path=SIGNAL_LEDGER,
        execution_path=EXECUTION_LEDGER,
        evaluation_root=SIGNAL_LEDGER.parent / "candidate49_future_evaluations",
    )
    assert payload["signal_entries"] == []
    assert payload["execution_entries"] == []
    assert payload["status"] == "candidate49_reporting_state_semantically_validated_read_only"
    assert payload["filesystem_write_performed"] is False
    assert payload["provider_request_issued"] is False
    assert payload["live_order_performed"] is False

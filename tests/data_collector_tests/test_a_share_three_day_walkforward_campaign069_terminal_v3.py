from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_069_terminal_completion_freeze_v3_20260806.json"
CORRECTION = ROOT / "docs/a_share_three_day_walkforward_campaign_069_postcompletion_accounting_correction_v2_20260806.json"
ATTEMPTS = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_069/research_attempt_ledger_v4.json"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign069_v3_terminal_bindings_are_current() -> None:
    assert _sha256(FREEZE) == "06cc6a9b020254af4d6ef7e46fd3bc9fa1296a9d737cb9fc82da3d6e798f7739"
    receipt = validator.validate_record(FREEZE, data_root=DATA_ROOT)
    assert receipt["all_bindings_passed"] is True
    assert receipt["binding_count"] == 12


def test_campaign069_v2_correction_counts_failed_commands_not_nodes() -> None:
    assert _sha256(CORRECTION) == "40704800d8edd33fef47188eb2df76ced116f784557ddd1577d4d7c1a7efa32e"
    correction = _load(CORRECTION)
    assert correction["corrected_accounting"]["postcompletion_failed_command_count"] == 2
    assert correction["corrected_accounting"]["postcompletion_failed_node_count"] == 5
    assert correction["corrected_accounting"]["campaign069_attempt_count"] == 6
    assert correction["corrected_accounting"]["corrected_cumulative_historical_research_attempt_count"] == 414


def test_campaign069_v4_attempt_ledger_and_unified_report_are_current() -> None:
    assert _sha256(ATTEMPTS) == "92756fc2a80777d4234368d2532b5476172810b446f3404bc4de825b664c651b"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign069_ledger_entry_count"] == 7
    assert ledger["campaign069_infrastructure_or_synthetic_failure_count"] == 5
    assert ledger["campaign069_complete_factor_attempt_count"] == 1
    assert ledger["campaign069_historical_return_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 414
    assert ledger["cumulative_return_reading_development_trial_count"] == 275
    assert _sha256(UNIFIED_REPORT) == "464c58855dc0606d6f61d58146bae0ffe78c0373dfb2774bf1b9b4c77dccfe49"
    report = UNIFIED_REPORT.read_text(encoding="utf-8")
    assert report.count("## 历史滚动 Campaign069 权威追加") == 1
    assert "最终口径为 Campaign069 五次基础设施失败" in report
    assert "累计历史研究尝试 414" in report

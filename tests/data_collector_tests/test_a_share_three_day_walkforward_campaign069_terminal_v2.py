from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_069_terminal_completion_freeze_v2_20260806.json"
CORRECTION = ROOT / "docs/a_share_three_day_walkforward_campaign_069_postcompletion_accounting_correction_20260806.json"
ATTEMPTS = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_069/research_attempt_ledger_v3.json"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign069_v2_terminal_bindings_are_current() -> None:
    assert _sha256(FREEZE) == "82df41002a0a6874a3b977b8f8d64e8d2604e1b0927b2fb6303b44242a7e03b5"
    receipt = validator.validate_record(FREEZE, data_root=DATA_ROOT)
    assert receipt["all_bindings_passed"] is True
    assert receipt["binding_count"] == 13


def test_campaign069_postcompletion_accounting_is_append_only_and_current() -> None:
    assert _sha256(CORRECTION) == "0096f4595633eb8e1327f327a7d5b4e5f33621170f71f746571c19608e83f460"
    correction = _load(CORRECTION)
    assert correction["corrected_accounting"]["campaign069_attempt_count"] == 5
    assert correction["corrected_accounting"]["corrected_cumulative_historical_research_attempt_count"] == 413
    assert _sha256(ATTEMPTS) == "adbf8d3100e4df24c5ea89f22533d5240f3f30cb107e0221c2f1e23c7a25494d"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign069_ledger_entry_count"] == 6
    assert ledger["campaign069_infrastructure_or_synthetic_failure_count"] == 4
    assert ledger["campaign069_complete_factor_attempt_count"] == 1
    assert ledger["campaign069_historical_return_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 413
    assert ledger["cumulative_return_reading_development_trial_count"] == 275


def test_campaign069_current_unified_report_contains_one_terminal_section_and_correction() -> None:
    assert _sha256(UNIFIED_REPORT) == "a6d5b4e57c01c5ae4d8d6e7e03e05608cfbcbbbea1e219449ac9ef1393c2f552"
    report = UNIFIED_REPORT.read_text(encoding="utf-8")
    assert report.count("## 历史滚动 Campaign069 权威追加") == 1
    assert "最终累计历史研究尝试据此为 413" in report
    assert "零 survivor 与压力区间关闭结论不变" in report

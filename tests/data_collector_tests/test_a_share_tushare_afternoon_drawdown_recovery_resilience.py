import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import (
    a_share_tushare_afternoon_drawdown_recovery_resilience as RESEARCH,
)


def source_frame(date: str, afternoon: np.ndarray | None = None) -> pd.DataFrame:
    day = pd.Timestamp(date)
    timestamps = [
        day + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in RESEARCH.SOURCE_MINUTE_CODES
    ]
    close = np.full(241, 100.0)
    if afternoon is not None:
        assert afternoon.shape == (120,)
        close[RESEARCH.AFTERNOON_START_INDEX :] = afternoon
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "close": close,
        }
    )


def base_frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(list(dates)),
            "symbol": "SH600000",
        }
    )


def test_preregistration_freezes_distinct_close_path_before_values_or_returns():
    spec = RESEARCH.load_preregistration()
    assert spec["candidate"]["name"] == RESEARCH.FACTOR_NAME
    assert spec["candidate"]["diagnostic_direction"] == "higher"
    assert spec["candidate"]["source_fields_allowed"] == [
        "datetime",
        "symbol",
        "provider",
        "close",
    ]
    assert spec["candidate"]["source_fields_forbidden"] == [
        "open",
        "high",
        "low",
        "volume",
        "amount",
        "any_daily_price",
        "any_forward_return",
    ]
    assert [
        item["name"]
        for item in spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
            "comparison_factors"
        ]
    ] == list(RESEARCH.COMPARISON_FACTORS)
    assert (
        spec["research_boundary"][
            "candidate_factor_values_observed_before_registration"
        ]
        is False
    )
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_diagnostic_preregistration_binds_passed_no_return_evidence():
    spec = RESEARCH.load_diagnostic_preregistration()
    evidence = spec["no_return_evidence"]
    assert evidence["protocol"]["sha256"] == RESEARCH.PREREGISTRATION_SHA256
    assert (
        evidence["candidate_snapshot"]["sha256"] == RESEARCH.CANDIDATE_MANIFEST_SHA256
    )
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert evidence["coverage_and_capacity"]["gate_passed"] is True
    assert evidence["uniqueness"]["all_five_comparisons_passed"] is True
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_diagnostic_consumption_marker_blocks_before_source_or_prices(tmp_path):
    marker = tmp_path / RESEARCH.CONSUMPTION_FILENAME
    marker.write_text("{}", encoding="utf-8")
    with pytest.raises(RESEARCH.RecoveryResilienceError, match="already consumed"):
        RESEARCH.require_diagnostic_unconsumed(tmp_path)


def test_terminal_record_binds_failed_fixed_direction_without_promotion():
    path = (
        RESEARCH.REPO_ROOT
        / "docs/a_share_tushare_afternoon_drawdown_recovery_resilience_research_record.json"
    )
    record = json.loads(path.read_text(encoding="utf-8"))
    assert RESEARCH.foundation.file_digest(path) == (
        "b608fd9c8bbe3ba40aa433c39b2c31ff7a0bbff9abb31aa1905acf26ee9f48d5"
    )
    assert (
        record["status"]
        == "terminal_rejected_at_association_stability_and_executable_topk_gates"
    )
    assert record["factor"]["direction"] == "higher"
    assert record["factor"]["source_fields"] == list(RESEARCH.RAW_COLUMNS)
    assert record["return_results"]["association_stability_gate_passed"] is False
    assert record["return_results"]["topk_viability_gate_passed"] is False
    assert record["return_results"]["dual_gate_passed"] is False
    assert record["decision"]["aggregation_candidate_added"] is False
    assert record["decision"]["selection_allowed"] is False
    assert (
        record["decision"][
            "invert_rewindow_threshold_subset_reweight_or_retest_on_2019_2025_allowed"
        ]
        is False
    )


def test_compute_partition_frame_measures_recovery_relative_to_drawdown():
    full_recovery = np.full(120, 100.0)
    full_recovery[0] = 90.0
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", full_recovery),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.5)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality == {
        "base_rows": 1,
        "eligible_rows": 1,
        "zero_drawdown_rows": 0,
        "invalid_required_value_rows": 0,
        "recovery_identity_violation_rows": 0,
    }


def test_compute_partition_frame_rewards_recovery_overshoot_without_amount():
    overshoot = np.full(120, 110.0)
    overshoot[0] = 90.0
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", overshoot),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    drawdown = np.log(100.0 / 90.0)
    recovery = np.log(110.0 / 90.0)
    expected = recovery / (drawdown + recovery)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(expected)
    assert 0.5 < output.loc[0, RESEARCH.FACTOR_NAME] < 1.0


def test_compute_partition_frame_keeps_zero_drawdown_missing():
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02"),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["zero_drawdown_rows"] == 1


def test_compute_partition_frame_keeps_invalid_close_missing():
    afternoon = np.full(120, 100.0)
    afternoon[0] = 90.0
    raw = source_frame("2024-01-02", afternoon)
    raw.loc[RESEARCH.AFTERNOON_START_INDEX + 10, "close"] = np.nan
    output, quality = RESEARCH.compute_partition_frame(
        raw,
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["invalid_required_value_rows"] == 1


def test_compute_partition_frame_rejects_grid_loss():
    raw = source_frame("2024-01-02").iloc[:-1].copy()
    with pytest.raises(RESEARCH.RecoveryResilienceError, match="241-row grid"):
        RESEARCH.compute_partition_frame(
            raw,
            base_frame("2024-01-02"),
            symbol="SH600000",
        )


def test_daily_directional_rank_correlation_respects_lower_comparison_direction():
    rows = []
    for date in pd.date_range("2024-01-02", periods=3, freq="D"):
        for position in range(60):
            rows.append(
                {
                    "trade_date": date,
                    RESEARCH.FACTOR_NAME: float(position),
                    "intraday_realized_volatility": float(60 - position),
                }
            )
    daily = RESEARCH._daily_directional_rank_correlations(
        pd.DataFrame(rows),
        "intraday_realized_volatility",
        "lower",
        50,
    )
    assert len(daily) == 3
    assert daily["pairwise_names"].eq(60).all()
    assert daily["rank_correlation"].tolist() == pytest.approx([1.0, 1.0, 1.0])


def test_no_return_audit_never_loads_comparisons_when_coverage_fails(
    tmp_path, monkeypatch
):
    data_root = tmp_path / "external"
    experiment_root = tmp_path / "experiments"
    manifest_path = RESEARCH.output_root(data_root) / "snapshot_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest = {
        "kind": "a_share_tushare_afternoon_drawdown_recovery_resilience_snapshot",
        "status": "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness",
        "protocol_sha256": RESEARCH.PREREGISTRATION_SHA256,
        "raw_manifest_sha256": RESEARCH.RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": RESEARCH.JOINT_MANIFEST_SHA256,
        "dataset_sha256": "candidate-dataset",
        "rows": 7_724_498,
        "eligible_rows": 1,
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    spec = {
        "preregistered_at": "2026-07-22T13:41:46Z",
        "candidate": {"formula": RESEARCH.FACTOR_FORMULA},
    }
    candidate = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["SH600000"],
            RESEARCH.FACTOR_NAME: [0.5],
            f"{RESEARCH.FACTOR_NAME}_eligible": [True],
        }
    )
    eligible = candidate[["trade_date", "symbol"]].copy()
    coverage = {
        "gate_passed_before_comparison_values": False,
        "candidate_eligible_rows": 1,
    }
    monkeypatch.setattr(RESEARCH, "load_preregistration", lambda: spec)
    monkeypatch.setattr(RESEARCH, "validate_repository_chain", lambda ignored: {})
    monkeypatch.setattr(
        RESEARCH,
        "validate_external_chain",
        lambda ignored, root: (
            {},
            {"dataset_sha256": "joint-dataset"},
            root / "raw.json",
            root / "joint.json",
            {},
            root / "comparison.json",
        ),
    )
    monkeypatch.setattr(RESEARCH, "verify_snapshot_files", lambda *args: {})
    monkeypatch.setattr(RESEARCH, "load_candidate_frame", lambda *args: candidate)
    monkeypatch.setattr(
        RESEARCH.foundation,
        "quality_listing_eligible_keys",
        lambda ignored: eligible,
    )
    monkeypatch.setattr(
        RESEARCH,
        "coverage_and_capacity",
        lambda candidate_frame, eligible_frame, ignored: (
            candidate_frame[["trade_date", "symbol", RESEARCH.FACTOR_NAME]],
            coverage,
        ),
    )
    monkeypatch.setattr(
        RESEARCH,
        "uniqueness_audit",
        lambda *args, **kwargs: pytest.fail(
            "comparison values must not load after a failed coverage gate"
        ),
    )
    audit_path = RESEARCH.run_no_return_audit(
        data_root=data_root,
        experiment_root=experiment_root,
        workers=1,
    )
    audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    assert audit["status"] == "terminal_rejected_at_no_return_coverage_or_capacity_gate"
    assert audit["comparison_fields_loaded"] == []
    assert audit["forward_return_fields_read"] is False
    assert (
        audit["decision"]["separate_return_diagnostic_preregistration_allowed"] is False
    )

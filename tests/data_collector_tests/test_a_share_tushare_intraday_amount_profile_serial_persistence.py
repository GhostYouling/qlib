import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import (
    a_share_tushare_intraday_amount_profile_serial_persistence as RESEARCH,
)


def source_frame(date: str, continuous_amounts: np.ndarray) -> pd.DataFrame:
    assert continuous_amounts.shape == (240,)
    day = pd.Timestamp(date)
    timestamps = [
        day + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in RESEARCH.SOURCE_MINUTE_CODES
    ]
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "amount": np.concatenate(([123456789.0], continuous_amounts)),
        }
    )


def base_frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(list(dates)),
            "symbol": "SH600000",
        }
    )


def test_preregistration_freezes_order_sensitive_amount_path_before_values():
    spec = RESEARCH.load_preregistration()
    candidate = spec["candidate"]
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["source_fields_forbidden"] == [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "any_daily_price",
        "any_forward_return",
    ]
    assert candidate["bar_grid"]["continuous_bars"] == 240
    assert candidate["bar_grid"]["lag_pairs"] == 239
    assert candidate["bar_grid"]["excluded_source_bar_end"] == "09:30"
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert [item["name"] for item in comparisons] == list(
        RESEARCH.COMPARISON_FACTORS
    )
    assert [item["score_direction"] for item in comparisons] == list(
        RESEARCH.COMPARISON_DIRECTIONS
    )
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
    assert evidence["candidate_snapshot"]["sha256"] == (
        RESEARCH.CANDIDATE_MANIFEST_SHA256
    )
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert evidence["coverage_and_capacity"]["gate_passed"] is True
    assert evidence["uniqueness"]["all_seven_comparisons_passed"] is True
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_diagnostic_consumption_marker_blocks_before_source_or_prices(tmp_path):
    marker = tmp_path / RESEARCH.CONSUMPTION_FILENAME
    marker.write_text("{}", encoding="utf-8")
    with pytest.raises(RESEARCH.AmountProfilePersistenceError, match="consumed"):
        RESEARCH.require_diagnostic_unconsumed(tmp_path)


def test_terminal_record_binds_failed_fixed_direction_without_promotion():
    path = (
        RESEARCH.REPO_ROOT
        / "docs/a_share_tushare_intraday_amount_profile_serial_persistence_research_record.json"
    )
    record = json.loads(path.read_text(encoding="utf-8"))
    assert RESEARCH.foundation.file_digest(path) == (
        "197899381a59f7a528c575e11a21310c15a41ac8b06232b1c8174648f2117b04"
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
            "invert_relag_rewindow_threshold_subset_reweight_or_retest_on_2019_2025_allowed"
        ]
        is False
    )


def test_compute_partition_frame_monotone_log_amount_has_unit_persistence():
    logged = np.linspace(0.0, 2.0, 240)
    amounts = np.expm1(logged)
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1
    assert quality["constant_profile_rows"] == 0
    assert quality["invalid_required_value_rows"] == 0
    assert quality["correlation_range_violation_rows"] == 0


def test_compute_partition_frame_alternating_log_amount_has_negative_persistence():
    amounts = np.tile([0.0, 100.0], 120)
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(-1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]


def test_serial_persistence_changes_under_permutation_while_entropy_does_not():
    values = np.repeat(np.arange(1.0, 121.0), 2)
    grouped = np.sort(values)
    alternating = np.concatenate((values[::2], values[1::2]))
    first, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", grouped),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    second, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", alternating),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    entropy_first, _ = RESEARCH.previous.compute_partition_frame(
        source_frame("2024-01-02", grouped),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    entropy_second, _ = RESEARCH.previous.compute_partition_frame(
        source_frame("2024-01-02", alternating),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert first.loc[0, RESEARCH.FACTOR_NAME] != pytest.approx(
        second.loc[0, RESEARCH.FACTOR_NAME]
    )
    assert entropy_first.loc[0, RESEARCH.previous.FACTOR_NAME] == pytest.approx(
        entropy_second.loc[0, RESEARCH.previous.FACTOR_NAME]
    )


def test_compute_partition_frame_excludes_standalone_0930_amount():
    raw = source_frame("2024-01-02", np.arange(1.0, 241.0))
    first, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    raw.loc[0, "amount"] = 9.9e99
    second, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_compute_partition_frame_keeps_constant_profile_missing():
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", np.ones(240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["constant_profile_rows"] == 1
    assert quality["invalid_required_value_rows"] == 0


@pytest.mark.parametrize("invalid", [np.nan, -1.0, np.inf])
def test_compute_partition_frame_keeps_invalid_required_amount_missing(invalid):
    amounts = np.arange(1.0, 241.0)
    amounts[20] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", amounts),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["invalid_required_value_rows"] == 1


def test_compute_partition_frame_rejects_grid_loss():
    raw = source_frame("2024-01-02", np.arange(1.0, 241.0)).iloc[:-1].copy()
    with pytest.raises(RESEARCH.AmountProfilePersistenceError, match="241-row grid"):
        RESEARCH.compute_partition_frame(
            raw, base_frame("2024-01-02"), symbol="SH600000"
        )


def test_no_return_audit_never_loads_comparisons_when_coverage_fails(
    tmp_path, monkeypatch
):
    data_root = tmp_path / "external"
    experiment_root = tmp_path / "experiments"
    manifest_path = RESEARCH.output_root(data_root) / "snapshot_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest = {
        "kind": "a_share_tushare_intraday_amount_profile_serial_persistence_snapshot",
        "status": "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness",
        "protocol_sha256": RESEARCH.PREREGISTRATION_SHA256,
        "raw_manifest_sha256": RESEARCH.RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": RESEARCH.JOINT_MANIFEST_SHA256,
        "dataset_sha256": "candidate-dataset",
        "rows": 7_724_498,
        "eligible_rows": 1,
        "source_open_high_low_close_or_volume_read": False,
        "source_amount_read": True,
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    spec = {
        "preregistered_at": "2026-07-22T15:32:57Z",
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
            root / "efficiency.json",
            {},
            root / "recovery.json",
            {},
            root / "entropy.json",
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
        data_root=data_root, experiment_root=experiment_root, workers=1
    )
    audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    assert audit["status"] == "terminal_rejected_at_no_return_coverage_or_capacity_gate"
    assert audit["comparison_fields_loaded"] == []
    assert audit["forward_return_fields_read"] is False
    assert (
        audit["decision"]["separate_return_diagnostic_preregistration_allowed"]
        is False
    )

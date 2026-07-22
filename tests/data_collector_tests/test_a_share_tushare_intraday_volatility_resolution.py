import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_volatility_resolution as RESEARCH


def source_frame(date: str, continuous_closes: np.ndarray) -> pd.DataFrame:
    assert continuous_closes.shape == (240,)
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
            "close": np.concatenate(([99.0], continuous_closes)),
        }
    )


def base_frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(list(dates)),
            "symbol": "SH600000",
        }
    )


def closes_from_half_returns(
    morning_returns: np.ndarray,
    afternoon_returns: np.ndarray,
    *,
    morning_start: float = 100.0,
    afternoon_start: float = 100.0,
) -> np.ndarray:
    assert morning_returns.shape == (119,)
    assert afternoon_returns.shape == (119,)
    morning = morning_start * np.exp(
        np.concatenate(([0.0], np.cumsum(morning_returns)))
    )
    afternoon = afternoon_start * np.exp(
        np.concatenate(([0.0], np.cumsum(afternoon_returns)))
    )
    return np.concatenate((morning, afternoon))


def test_preregistration_freezes_volatility_resolution_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    grid = candidate["bar_grid"]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 35
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert grid["morning_close_observations"] == 120
    assert grid["afternoon_close_observations"] == 120
    assert grid["within_morning_log_returns"] == 119
    assert grid["within_afternoon_log_returns"] == 119
    assert grid["total_log_returns_used"] == 238
    assert grid["lunch_break_return_included"] is False
    assert grid["excluded_source_bar_end"] == "09:30"
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 11
    assert [item["name"] for item in comparisons] == list(
        RESEARCH.COMPARISON_FACTORS
    )
    assert [item["score_direction"] for item in comparisons] == list(
        RESEARCH.COMPARISON_DIRECTIONS
    )
    assert spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "all_eleven_comparisons_must_pass"
    ] is True
    assert spec["point_in_time_context"] == (
        RESEARCH.previous.load_preregistration()["point_in_time_context"]
    )
    assert spec["research_boundary"][
        "candidate_factor_values_observed_before_registration"
    ] is False
    assert spec["research_boundary"][
        "forward_return_fields_read_before_registration"
    ] is False


def test_diagnostic_protocol_binds_passed_no_return_evidence():
    spec = RESEARCH.load_diagnostic_preregistration()
    evidence = spec["no_return_evidence"]
    snapshot = evidence["candidate_snapshot"]
    audit = evidence["ordered_audit"]
    coverage = evidence["coverage_and_capacity"]
    uniqueness = evidence["uniqueness"]

    assert evidence["protocol"]["sha256"] == RESEARCH.PREREGISTRATION_SHA256
    assert snapshot["sha256"] == RESEARCH.CANDIDATE_MANIFEST_SHA256
    assert snapshot["eligible_rows"] == 7_695_088
    assert snapshot["zero_total_variance_rows"] == 29_410
    assert audit["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert coverage["gate_passed"] is True
    assert uniqueness["all_eleven_comparisons_passed"] is True
    assert spec["research_boundary"][
        "forward_return_fields_read_before_registration"
    ] is False


def test_terminal_record_binds_single_diagnostic_and_dual_gate_rejection():
    record = RESEARCH.load_terminal_record_if_present()
    assert record is not None
    assert record["factor"]["name"] == RESEARCH.FACTOR_NAME
    assert record["factor"]["direction"] == "higher"
    assert record["historical_artifacts"]["diagnostic"]["sha256"] == (
        RESEARCH.DIAGNOSTIC_SHA256
    )
    assert record["return_results"]["cohorts"] == 539
    assert record["return_results"]["association_stability_gate_passed"] is False
    assert record["return_results"]["topk_viability_gate_passed"] is False
    assert record["return_results"]["dual_gate_passed"] is False
    assert record["decision"]["aggregation_candidate_added"] is False
    assert record["decision"]["aggregation_allowed"] is False
    assert record["research_boundary"][
        "same_history_combination_return_evaluation_performed"
    ] is False


def test_repository_chain_distinguishes_preregistered_predecessor_from_current_state():
    evidence = RESEARCH.validate_repository_chain(RESEARCH.load_preregistration())
    predecessor = evidence["preregistered_current_research_state"]
    current = evidence["current_research_state"]
    assert predecessor["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert predecessor["terminal_mechanism_count_before_this_candidate"] == 35
    assert predecessor[
        "historical_binding_not_reinterpreted_as_current_file_bytes"
    ] is True
    assert current["sha256"] == RESEARCH.research.THREE_DAY_ITERATION_STATUS_SHA256


def test_diagnostic_consumption_marker_blocks_before_source_or_prices(tmp_path):
    marker = tmp_path / RESEARCH.CONSUMPTION_FILENAME
    marker.write_text("{}", encoding="utf-8")
    with pytest.raises(RESEARCH.IntradayVolatilityResolutionError, match="consumed"):
        RESEARCH.require_diagnostic_unconsumed(tmp_path)


def test_compute_partition_frame_morning_only_variance_is_one():
    closes = closes_from_half_returns(
        np.full(119, 0.001), np.zeros(119)
    )
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality == {
        "base_rows": 1,
        "eligible_rows": 1,
        "zero_total_variance_rows": 0,
        "invalid_required_value_rows": 0,
        "nonfinite_log_return_rows": 0,
        "numerical_endpoint_canonicalization_rows": 0,
        "volatility_resolution_range_violation_rows": 0,
    }


def test_compute_partition_frame_afternoon_only_variance_is_zero():
    closes = closes_from_half_returns(
        np.zeros(119), np.full(119, -0.001)
    )
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]


def test_compute_partition_frame_equal_half_variances_is_one_half():
    closes = closes_from_half_returns(
        np.full(119, 0.001), np.full(119, -0.001)
    )
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.5)


def test_compute_partition_frame_uses_squared_return_magnitude():
    closes = closes_from_half_returns(
        np.full(119, 0.002), np.full(119, 0.001)
    )
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.8)


def test_compute_partition_frame_is_invariant_to_common_price_scale():
    closes = closes_from_half_returns(
        np.linspace(-0.002, 0.002, 119),
        np.linspace(0.001, -0.001, 119),
    )
    first, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    second, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", 17.0 * closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_compute_partition_frame_excludes_lunch_break_return():
    morning_returns = np.full(119, 0.001)
    afternoon_returns = np.full(119, 0.001)
    first_closes = closes_from_half_returns(
        morning_returns, afternoon_returns, afternoon_start=100.0
    )
    second_closes = closes_from_half_returns(
        morning_returns, afternoon_returns, afternoon_start=10000.0
    )
    first, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", first_closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    second, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", second_closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert first.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.5)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.5)


def test_compute_partition_frame_excludes_standalone_0930_close():
    closes = closes_from_half_returns(
        np.full(119, 0.001), np.full(119, -0.001)
    )
    raw = source_frame("2024-01-02", closes)
    first, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    raw.loc[0, "close"] = 9.9e99
    second, _ = RESEARCH.compute_partition_frame(
        raw, base_frame("2024-01-02"), symbol="SH600000"
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_compute_partition_frame_constant_closes_stay_missing():
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", np.ones(240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["zero_total_variance_rows"] == 1
    assert quality["invalid_required_value_rows"] == 0


@pytest.mark.parametrize("invalid", [np.nan, 0.0, -1.0, np.inf])
def test_compute_partition_frame_keeps_invalid_required_close_missing(invalid):
    closes = closes_from_half_returns(
        np.full(119, 0.001), np.full(119, -0.001)
    )
    closes[20] = invalid
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["invalid_required_value_rows"] == 1


def test_compute_partition_frame_rejects_grid_loss():
    closes = closes_from_half_returns(
        np.full(119, 0.001), np.full(119, -0.001)
    )
    raw = source_frame("2024-01-02", closes).iloc[:-1].copy()
    with pytest.raises(RESEARCH.IntradayVolatilityResolutionError, match="241-row grid"):
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
        "kind": "a_share_tushare_intraday_volatility_resolution_snapshot",
        "status": "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness",
        "protocol_sha256": RESEARCH.PREREGISTRATION_SHA256,
        "raw_manifest_sha256": RESEARCH.RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": RESEARCH.JOINT_MANIFEST_SHA256,
        "dataset_sha256": "candidate-dataset",
        "rows": 7_724_498,
        "eligible_rows": 1,
        "source_close_read": True,
        "source_open_high_low_volume_or_amount_read": False,
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(
        RESEARCH,
        "CANDIDATE_MANIFEST_SHA256",
        RESEARCH.foundation.file_digest(manifest_path),
    )
    spec = {
        "preregistered_at": "2026-07-22T18:10:59Z",
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
    monkeypatch.setattr(RESEARCH, "load_terminal_record_if_present", lambda: None)
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
            {},
            root / "profile.json",
            {},
            root / "upside.json",
            {},
            root / "terminal.json",
            {},
            root / "sign_run.json",
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
    assert audit["decision"][
        "separate_return_diagnostic_preregistration_allowed"
    ] is False

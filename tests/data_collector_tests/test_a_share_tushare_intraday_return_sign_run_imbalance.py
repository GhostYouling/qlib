import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_return_sign_run_imbalance as RESEARCH


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


def closes_from_signs(signs: np.ndarray, step: float = 0.001) -> np.ndarray:
    assert signs.shape == (239,)
    returns = signs.astype(float) * step
    return 100.0 * np.exp(np.concatenate(([0.0], np.cumsum(returns))))


def test_preregistration_freezes_sign_run_imbalance_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 34
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["bar_grid"]["continuous_bars"] == 240
    assert candidate["bar_grid"]["adjacent_close_to_close_log_returns"] == 239
    assert candidate["bar_grid"]["adjacent_return_sign_pairs"] == 238
    assert candidate["bar_grid"]["excluded_source_bar_end"] == "09:30"
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 10
    assert [item["name"] for item in comparisons] == list(
        RESEARCH.COMPARISON_FACTORS
    )
    assert [item["score_direction"] for item in comparisons] == list(
        RESEARCH.COMPARISON_DIRECTIONS
    )
    assert spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "all_ten_comparisons_must_pass"
    ] is True
    assert spec["research_boundary"][
        "candidate_factor_values_observed_before_registration"
    ] is False
    assert spec["research_boundary"][
        "forward_return_fields_read_before_registration"
    ] is False


def test_context_repair_only_supplies_the_previous_frozen_point_in_time_context():
    repair = json.loads(RESEARCH.DEFAULT_CONTEXT_REPAIR.read_text(encoding="utf-8"))
    previous_spec = RESEARCH.previous.load_preregistration()
    assert RESEARCH.foundation.file_digest(RESEARCH.DEFAULT_CONTEXT_REPAIR) == (
        RESEARCH.CONTEXT_REPAIR_SHA256
    )
    assert repair["omitted_protocol"]["sha256"] == RESEARCH.PREREGISTRATION_SHA256
    assert repair["point_in_time_context"] == previous_spec["point_in_time_context"]
    assert repair["repair_scope"]["candidate_changed"] is False
    assert repair["repair_scope"]["formula_changed"] is False
    assert repair["repair_scope"]["ordered_gate_or_threshold_changed"] is False
    assert repair["research_boundary"][
        "historical_candidate_factor_values_observed_before_repair"
    ] is False


def test_return_diagnostic_entry_point_exists_only_after_separate_preregistration():
    assert hasattr(RESEARCH, "load_diagnostic_preregistration")
    assert hasattr(RESEARCH, "run_diagnostic")


def test_diagnostic_preregistration_binds_passed_no_return_evidence():
    spec = RESEARCH.load_diagnostic_preregistration()
    evidence = spec["no_return_evidence"]
    snapshot = evidence["candidate_snapshot"]
    assert evidence["protocol"]["sha256"] == RESEARCH.PREREGISTRATION_SHA256
    assert evidence["context_repair"]["sha256"] == RESEARCH.CONTEXT_REPAIR_SHA256
    assert snapshot["sha256"] == RESEARCH.CANDIDATE_MANIFEST_SHA256
    assert snapshot["eligible_rows"] == 7_605_471
    assert snapshot["zero_same_sign_pair_count_rows"] == 119_027
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert evidence["coverage_and_capacity"]["gate_passed"] is True
    assert evidence["uniqueness"]["all_ten_comparisons_passed"] is True
    assert spec["research_boundary"][
        "forward_return_fields_read_before_registration"
    ] is False


def test_diagnostic_consumption_marker_blocks_before_source_or_prices(tmp_path):
    marker = tmp_path / RESEARCH.CONSUMPTION_FILENAME
    marker.write_text("{}", encoding="utf-8")
    with pytest.raises(RESEARCH.ReturnSignRunImbalanceError, match="consumed"):
        RESEARCH.require_diagnostic_unconsumed(tmp_path)


def test_terminal_record_binds_both_failed_gates_without_promotion():
    path = (
        RESEARCH.REPO_ROOT
        / "docs/a_share_tushare_intraday_return_sign_run_imbalance_research_record.json"
    )
    record = json.loads(path.read_text(encoding="utf-8"))
    assert RESEARCH.foundation.file_digest(path) == (
        "ef325c59c061109248c360bcd836eea70ac4531dd29c1028bf74d5e599108139"
    )
    assert record["status"] == (
        "terminal_rejected_at_association_stability_and_executable_topk_gates"
    )
    assert record["factor"]["direction"] == "higher"
    assert record["factor"]["source_fields"] == list(RESEARCH.RAW_COLUMNS)
    assert record["no_return_results"]["coverage_and_capacity_gate_passed"] is True
    assert record["no_return_results"]["all_ten_uniqueness_gates_passed"] is True
    assert record["return_results"]["association_stability_gate_passed"] is False
    assert record["return_results"]["topk_viability_gate_passed"] is False
    assert record["return_results"]["dual_gate_passed"] is False
    assert record["return_results"][
        "pilot_net_cumulative_return_at_ten_bp_each_side"
    ] == pytest.approx(-0.07793701057064739)
    assert record["decision"]["aggregation_candidate_added"] is False
    assert record["decision"]["selection_allowed"] is False
    assert record["decision"][
        "invert_reformulate_rewindow_threshold_subset_reweight_or_retest_on_2019_2025_allowed"
    ] is False


def test_compute_partition_frame_all_positive_continuations_is_one():
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes_from_signs(np.ones(239))),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality == {
        "base_rows": 1,
        "eligible_rows": 1,
        "zero_same_sign_pair_count_rows": 0,
        "invalid_required_value_rows": 0,
        "nonfinite_log_return_rows": 0,
        "sign_run_imbalance_range_violation_rows": 0,
    }


def test_compute_partition_frame_all_negative_continuations_is_minus_one():
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes_from_signs(-np.ones(239))),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(-1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]


def test_compute_partition_frame_balanced_positive_and_negative_runs_is_zero():
    signs = np.concatenate((np.ones(119), -np.ones(119), np.zeros(1)))
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes_from_signs(signs)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)


def test_compute_partition_frame_alternating_signs_has_zero_denominator():
    signs = np.where(np.arange(239) % 2 == 0, 1.0, -1.0)
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes_from_signs(signs)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["zero_same_sign_pair_count_rows"] == 1


def test_compute_partition_frame_zero_and_opposite_pairs_are_ignored():
    signs = np.zeros(239)
    signs[:6] = np.array([1.0, 1.0, 0.0, -1.0, -1.0, 0.0])
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes_from_signs(signs)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]


def test_compute_partition_frame_is_invariant_to_common_price_scale():
    signs = np.concatenate((np.ones(80), -np.ones(60), np.zeros(99)))
    closes = closes_from_signs(signs)
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


def test_compute_partition_frame_excludes_standalone_0930_close():
    raw = source_frame("2024-01-02", closes_from_signs(np.ones(239)))
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
    assert quality["zero_same_sign_pair_count_rows"] == 1
    assert quality["invalid_required_value_rows"] == 0


@pytest.mark.parametrize("invalid", [np.nan, 0.0, -1.0, np.inf])
def test_compute_partition_frame_keeps_invalid_required_close_missing(invalid):
    closes = closes_from_signs(np.ones(239))
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
    raw = source_frame("2024-01-02", closes_from_signs(np.ones(239))).iloc[
        :-1
    ].copy()
    with pytest.raises(RESEARCH.ReturnSignRunImbalanceError, match="241-row grid"):
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
        "kind": "a_share_tushare_intraday_return_sign_run_imbalance_snapshot",
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

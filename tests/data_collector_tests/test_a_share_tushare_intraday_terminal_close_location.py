import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_intraday_terminal_close_location as RESEARCH


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


def test_preregistration_freezes_terminal_close_location_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 33
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert candidate["source_fields_forbidden"] == [
        "open",
        "high",
        "low",
        "volume",
        "amount",
        "any_daily_price",
        "any_forward_return",
    ]
    assert candidate["bar_grid"]["continuous_bars"] == 240
    assert candidate["bar_grid"]["terminal_bar_end"] == "15:00"
    assert candidate["bar_grid"]["excluded_source_bar_end"] == "09:30"
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 9
    assert [item["name"] for item in comparisons] == list(
        RESEARCH.COMPARISON_FACTORS
    )
    assert [item["score_direction"] for item in comparisons] == list(
        RESEARCH.COMPARISON_DIRECTIONS
    )
    assert spec["research_boundary"][
        "candidate_factor_values_observed_before_registration"
    ] is False
    assert spec["research_boundary"][
        "forward_return_fields_read_before_registration"
    ] is False


def test_terminal_record_binds_no_return_near_synonym_rejection():
    path = (
        RESEARCH.REPO_ROOT
        / "docs/a_share_tushare_intraday_terminal_close_location_research_record.json"
    )
    record = json.loads(path.read_text(encoding="utf-8"))
    assert RESEARCH.foundation.file_digest(path) == (
        "b5c0f740353e35df27d7f0390dbee7e500990fb4d7986550faadd632ab0ef0c9"
    )
    assert record["status"] == "terminal_rejected_at_no_return_uniqueness_gate"
    assert record["factor"]["direction"] == "higher"
    assert record["factor"]["source_fields"] == list(RESEARCH.RAW_COLUMNS)
    assert record["no_return_results"]["coverage_and_capacity_gate_passed"] is True
    assert record["no_return_results"]["all_nine_uniqueness_gates_passed"] is False
    assert record["no_return_results"]["failed_comparison_factor"] == (
        "late_vwap_to_day_vwap_30m"
    )
    assert record["decision"]["return_diagnostic_allowed"] is False
    assert record["decision"]["aggregation_candidate_added"] is False
    assert record["research_boundary"]["forward_return_fields_read"] is False


def test_return_diagnostic_entry_point_is_absent_after_uniqueness_failure():
    assert not hasattr(RESEARCH, "load_diagnostic_preregistration")
    assert not hasattr(RESEARCH, "run_diagnostic")


def test_compute_partition_frame_monotone_increase_finishes_at_high():
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", np.linspace(1.0, 240.0, 240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality == {
        "base_rows": 1,
        "eligible_rows": 1,
        "zero_close_range_rows": 0,
        "invalid_required_value_rows": 0,
        "ieee_boundary_canonicalization_rows": 0,
        "location_range_violation_rows": 0,
    }


def test_compute_partition_frame_monotone_decrease_finishes_at_low():
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", np.linspace(240.0, 1.0, 240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]


def test_compute_partition_frame_terminal_midpoint_has_half_location():
    closes = np.full(240, 2.0)
    closes[0] = 1.0
    closes[1] = 3.0
    output, _ = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", closes),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.5)


def test_compute_partition_frame_is_invariant_to_common_price_scale():
    closes = 5.0 + np.sin(np.linspace(0.0, 4.0 * np.pi, 240))
    closes[-1] = 5.25
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
    raw = source_frame("2024-01-02", np.linspace(1.0, 240.0, 240))
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


def test_compute_partition_frame_keeps_zero_range_session_missing():
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", np.ones(240)),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["zero_close_range_rows"] == 1
    assert quality["invalid_required_value_rows"] == 0


@pytest.mark.parametrize("invalid", [np.nan, 0.0, -1.0, np.inf])
def test_compute_partition_frame_keeps_invalid_required_close_missing(invalid):
    closes = np.linspace(1.0, 240.0, 240)
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
    raw = source_frame("2024-01-02", np.linspace(1.0, 240.0, 240)).iloc[
        :-1
    ].copy()
    with pytest.raises(RESEARCH.TerminalCloseLocationError, match="241-row grid"):
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
        "kind": "a_share_tushare_intraday_terminal_close_location_snapshot",
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
        "preregistered_at": "2026-07-22T17:20:43Z",
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

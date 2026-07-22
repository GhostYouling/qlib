import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_afternoon_signed_amount_efficiency as RESEARCH


def source_frame(date: str, *, direction: int = 1, flat: bool = False) -> pd.DataFrame:
    day = pd.Timestamp(date)
    timestamps = [
        day + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in RESEARCH.SOURCE_MINUTE_CODES
    ]
    close = np.full(241, 100.0)
    if not flat:
        afternoon_steps = np.arange(1, 121, dtype=float) * 0.001 * direction
        close[RESEARCH.AFTERNOON_START_INDEX :] = 100.0 + afternoon_steps
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "close": close,
            "amount": np.ones(241, dtype=float),
        }
    )


def base_frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(list(dates)),
            "symbol": "SH600000",
        }
    )


def test_preregistration_freezes_factor_before_values_or_returns():
    spec = RESEARCH.load_preregistration()
    assert spec["candidate"]["name"] == RESEARCH.FACTOR_NAME
    assert spec["candidate"]["diagnostic_direction"] == "higher"
    assert spec["candidate"]["source_fields_allowed"] == [
        "datetime",
        "symbol",
        "provider",
        "close",
        "amount",
    ]
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
    assert (
        evidence["candidate_snapshot"]["sha256"] == RESEARCH.CANDIDATE_MANIFEST_SHA256
    )
    assert evidence["ordered_audit"]["sha256"] == RESEARCH.NO_RETURN_AUDIT_SHA256
    assert (
        evidence["quality_semantics_repair"]["sha256"]
        == RESEARCH.QUALITY_SEMANTICS_REPAIR_SHA256
    )
    assert (
        evidence["superseded_ordered_audit"]["sha256"]
        == RESEARCH.SUPERSEDED_NO_RETURN_AUDIT_SHA256
    )
    assert evidence["coverage_and_capacity"]["gate_passed"] is True
    assert evidence["uniqueness"]["all_four_comparisons_passed"] is True
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_diagnostic_consumption_marker_blocks_before_source_or_prices(tmp_path):
    marker = tmp_path / RESEARCH.CONSUMPTION_FILENAME
    marker.write_text("{}", encoding="utf-8")
    with pytest.raises(RESEARCH.AfternoonEfficiencyError, match="already consumed"):
        RESEARCH.require_diagnostic_unconsumed(tmp_path)


def test_compute_partition_frame_obeys_signed_amount_efficiency_formula():
    raw = pd.concat(
        [
            source_frame("2024-01-02", direction=1),
            source_frame("2024-01-03", direction=-1),
        ],
        ignore_index=True,
    )
    output, quality = RESEARCH.compute_partition_frame(
        raw,
        base_frame("2024-01-02", "2024-01-03"),
        symbol="SH600000",
    )
    assert output[RESEARCH.FACTOR_NAME].tolist() == pytest.approx([1.0, -1.0])
    assert output[f"{RESEARCH.FACTOR_NAME}_eligible"].tolist() == [True, True]
    assert quality == {
        "base_rows": 2,
        "eligible_rows": 2,
        "zero_denominator_rows": 0,
        "invalid_required_value_rows": 0,
    }


def test_compute_partition_frame_keeps_zero_denominator_missing():
    output, quality = RESEARCH.compute_partition_frame(
        source_frame("2024-01-02", flat=True),
        base_frame("2024-01-02"),
        symbol="SH600000",
    )
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["zero_denominator_rows"] == 1


def test_compute_partition_frame_rejects_grid_loss():
    raw = source_frame("2024-01-02").iloc[:-1].copy()
    with pytest.raises(RESEARCH.AfternoonEfficiencyError, match="241-row grid"):
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


def test_quality_listing_eligibility_forward_fills_each_known_field(tmp_path):
    calendar_path = tmp_path / "calendar.txt"
    calendar_path.write_text(
        "2019-01-02\n2019-01-03\n2019-01-04\n2019-01-07\n",
        encoding="utf-8",
    )
    holding_path = tmp_path / "holding.txt"
    holding_path.write_text(
        "SH600000\t2019-01-02\t2019-01-07\n",
        encoding="utf-8",
    )
    quality_path = tmp_path / "quality.parquet"
    pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000"],
            "report_date": ["2018-06-30", "2018-09-30"],
            "announcement_date": ["2019-01-02", "2019-01-03"],
            "roe": [6.0, 7.0],
            "net_profit": [1.0, 2.0],
            "revenue_yoy": [3.0, np.nan],
            "profit_yoy": [4.0, np.nan],
        }
    ).to_parquet(quality_path, index=False)
    spec = {
        "point_in_time_context": {
            "calendar": {"path": str(calendar_path)},
            "holding_universe": {"path": str(holding_path)},
            "quarterly_quality": {
                "path": str(quality_path),
                "maximum_age_days": 550,
            },
            "minimum_listing_sessions": 1,
        }
    }

    eligible = RESEARCH.quality_listing_eligible_keys(spec)

    assert eligible["trade_date"].tolist() == [
        pd.Timestamp("2019-01-03"),
        pd.Timestamp("2019-01-04"),
        pd.Timestamp("2019-01-07"),
    ]
    assert eligible["symbol"].astype(str).tolist() == ["SH600000"] * 3


def test_no_return_audit_never_loads_comparisons_when_coverage_fails(
    tmp_path, monkeypatch
):
    data_root = tmp_path / "external"
    experiment_root = tmp_path / "experiments"
    manifest_path = RESEARCH.output_root(data_root) / "snapshot_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest = {
        "kind": "a_share_tushare_afternoon_signed_amount_efficiency_snapshot",
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
        "preregistered_at": "2026-07-22T12:26:52Z",
        "candidate": {"formula": "frozen-formula"},
    }
    candidate = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["SH600000"],
            RESEARCH.FACTOR_NAME: [1.0],
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
        ),
    )
    monkeypatch.setattr(RESEARCH, "verify_snapshot_files", lambda *args: {})
    monkeypatch.setattr(RESEARCH, "load_candidate_frame", lambda *args: candidate)
    monkeypatch.setattr(
        RESEARCH, "quality_listing_eligible_keys", lambda ignored: eligible
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

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign017_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign017 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_changes() -> np.ndarray:
    return np.resize(
        np.array([0.0010, -0.0010, 0.0, -0.0020, 0.0020], dtype=float),
        FEATURES.WITHIN_HALF_PAIR_COUNT,
    )


def _path(
    *,
    midrange_changes: np.ndarray | None = None,
    width_changes: np.ndarray | None = None,
    afternoon_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    if midrange_changes is None or width_changes is None:
        default = _default_changes()
        midrange_changes = (
            default if midrange_changes is None else midrange_changes
        )
        width_changes = default if width_changes is None else width_changes
    midrange_changes = np.asarray(midrange_changes, dtype=float)
    width_changes = np.asarray(width_changes, dtype=float)
    assert midrange_changes.shape == (FEATURES.WITHIN_HALF_PAIR_COUNT,)
    assert width_changes.shape == (FEATURES.WITHIN_HALF_PAIR_COUNT,)

    highs = np.empty(FEATURES.SELECTED_BAR_COUNT, dtype=float)
    lows = np.empty(FEATURES.SELECTED_BAR_COUNT, dtype=float)
    pair_offset = 0
    for start, scale in ((0, 1.0), (120, afternoon_scale)):
        midrange = np.log(100.0 * scale)
        width = 0.02
        highs[start] = np.exp(midrange + width / 2.0)
        lows[start] = np.exp(midrange - width / 2.0)
        for position in range(start + 1, start + 120):
            midrange += midrange_changes[pair_offset]
            width += width_changes[pair_offset]
            assert width >= 0.0
            highs[position] = np.exp(midrange + width / 2.0)
            lows[position] = np.exp(midrange - width / 2.0)
            pair_offset += 1
    assert pair_offset == FEATURES.WITHIN_HALF_PAIR_COUNT
    return highs, lows


def _compute(
    arrays: tuple[np.ndarray, np.ndarray],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    return FEATURES.compute_factor_values(
        highs=arrays[0].reshape(1, -1),
        lows=arrays[1].reshape(1, -1),
    )


def test_matching_and_opposite_changes_hit_closed_endpoints() -> None:
    changes = _default_changes()
    positive = _path(
        midrange_changes=changes,
        width_changes=changes,
    )
    negative = _path(
        midrange_changes=-changes,
        width_changes=changes,
    )
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack([positive[0], negative[0]]),
        lows=np.vstack([positive[1], negative[1]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0, -1.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 2


def test_exact_zero_changes_remain_in_fixed_support() -> None:
    changes = _default_changes()
    assert int((changes == 0.0).sum()) > 0
    values, eligible, _ = _compute(
        _path(midrange_changes=changes, width_changes=changes)
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])


def test_zero_midrange_or_width_change_variance_is_missing() -> None:
    changes = _default_changes()
    values, eligible, quality = _compute(
        _path(
            midrange_changes=np.zeros_like(changes),
            width_changes=changes,
        )
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__zero_midrange_change_variance_rows"
        ]
        == 1
    )

    values, eligible, quality = _compute(
        _path(
            midrange_changes=changes,
            width_changes=np.zeros_like(changes),
        )
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__zero_width_change_variance_rows"]
        == 1
    )


def test_lunch_boundary_is_not_a_transition() -> None:
    base = _path(afternoon_scale=1.0)
    large_lunch_jump = _path(afternoon_scale=7.0)
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=np.vstack([base[0], large_lunch_jump[0]]),
        lows=np.vstack([base[1], large_lunch_jump[1]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(
        values[FEATURES.FACTOR_NAME][1]
    )


def test_common_price_scale_does_not_change_factor() -> None:
    arrays = _path()
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=np.vstack([arrays[0], arrays[0] * 13.0]),
        lows=np.vstack([arrays[1], arrays[1] * 13.0]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(
        values[FEATURES.FACTOR_NAME][1]
    )


def test_invalid_shapes_ordering_nonpositive_and_nonfinite_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign017FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )

    arrays = [array.copy() for array in _path()]
    arrays[1][3] = arrays[0][3] + 1.0
    values, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__low_high_ordering_violation_rows"]
        == 1
    )

    arrays = [array.copy() for array in _path()]
    arrays[1][4] = 0.0
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert quality["invalid_required_high_low_rows"] == 1

    arrays = [array.copy() for array in _path()]
    arrays[0][5] = np.nan
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert quality["invalid_required_high_low_rows"] == 1


def test_partition_reads_only_high_low_and_excludes_0930() -> None:
    arrays = _path()
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamps = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    raw = pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "high": np.concatenate([[-1.0], arrays[0]]),
            "low": np.concatenate([[-1.0], arrays[1]]),
        }
    ).loc[:, FEATURES.RAW_COLUMNS]
    base = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2020-01-02")],
            "symbol": ["SH600000"],
        }
    )
    frame, quality = FEATURES.compute_partition_frame(
        raw,
        base,
        None,
        symbol="SH600000",
    )
    assert tuple(frame.columns) == FEATURES.OUTPUT_COLUMNS
    assert frame[f"{FEATURES.FACTOR_NAME}_eligible"].tolist() == [True]
    assert frame[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])
    assert quality["base_rows"] == 1
    assert FEATURES.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "high",
        "low",
    )


def test_concept_audit_parent_and_protocol_are_fingerprint_bound() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_017_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_017_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN016_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN016_FEATURE_RUNNER_SHA256
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["candidate_values_computed_or_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["within_half_pair_count"] == 238
    assert audit["comparison_catalog"]["semantic_registered_mechanism_count"] == 40
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 38
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 38
    assert comparisons[-1]["name"] == (
        "intraday_interbar_gap_body_confirmation_238p"
    )
    assert protocol["finite_post_admissibility_search"][
        "expected_trial_count_if_admitted"
    ] == 1


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "f4fa96727e42f7eafdd959a3f26979096b4c1dbc18dae2915f3abd77615796be"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": (
                "wf017_single__intraday_midrange_width_change_coupling_238p"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_terminal_record_and_additive_state_preserve_closed_stress() -> None:
    record = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_017_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_iteration_status_20260729_campaign017.json"
        ).read_text()
    )
    repair = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_017_feature_manifest_semantic_repair_20260729.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_017"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_017"
            / "walkforward/exposed_stress_consumption_record.json"
        ).read_text()
    )
    assert record["status"] == (
        "completed_zero_development_survivors_stress_interval_not_opened"
    )
    assert record["development_result"]["frozen_trial_count"] == 1
    assert record["development_result"]["operationally_admissible_trial_count"] == 1
    assert (
        record["development_result"]["trial"][
            "development_survivor_gate_passed"
        ]
        is False
    )
    assert (
        record["development_result"]["trial"][
            "positive_validation_mean_rank_ic_fold_count"
        ]
        == 0
    )
    assert survivors["selected_survivor_count"] == 0
    assert survivors["stress_return_fields_read"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert repair["observed_mismatch"]["partition_factor_values_or_eligibility_changed"] is False
    assert (
        repair["affected_snapshot"]["dataset_sha256_before_and_after"]
        == FEATURES.SNAPSHOT_DATASET_SHA256
    )
    assert state["research_counts"]["recorded_historical_development_trial_count"] == 240
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"][
        "campaign018_concept_scouting_and_separate_no_return_research_allowed"
    ] is True

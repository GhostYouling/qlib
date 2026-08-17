import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign019_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _compute(
    signs: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    opens = np.full(FEATURES.SELECTED_BAR_COUNT, 100.0)
    closes = opens * np.exp(signs.astype(float) * 0.001)
    return FEATURES.compute_factor_values(
        opens=opens.reshape(1, -1),
        closes=closes.reshape(1, -1),
    )


def test_all_continuation_and_all_alternation_hit_exact_endpoints() -> None:
    continuation = np.ones(FEATURES.SELECTED_BAR_COUNT, dtype=int)
    alternating = np.tile([1, -1], FEATURES.SELECTED_BAR_COUNT // 2)
    opens = np.full((2, FEATURES.SELECTED_BAR_COUNT), 100.0)
    closes = opens * np.exp(
        np.vstack([continuation, alternating]).astype(float) * 0.001
    )
    values, eligible, quality = FEATURES.compute_factor_values(
        opens=opens,
        closes=closes,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0, 0.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 2


def test_lunch_transition_is_never_counted() -> None:
    signs = np.ones(FEATURES.SELECTED_BAR_COUNT, dtype=int)
    signs[120:] = -1
    values, eligible, _ = _compute(signs)
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])


def test_zero_body_breaks_incident_pairs_without_bridging_neighbors() -> None:
    signs = np.ones(FEATURES.SELECTED_BAR_COUNT, dtype=int)
    signs[1] = 0
    signs[2] = -1
    values, eligible, quality = _compute(signs)
    # The zero removes pairs (0,1) and (1,2); it must not create pair (0,2).
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([235 / 236])
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_body_observations"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__rows_with_zero_body"] == 1


def test_minimum_120_informative_pairs_is_enforced() -> None:
    signs = np.zeros(FEATURES.SELECTED_BAR_COUNT, dtype=int)
    signs[:120] = 1
    signs[120:122] = 1
    values, eligible, quality = _compute(signs)
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])

    signs[121] = 0
    values, eligible, quality = _compute(signs)
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__insufficient_informative_pair_rows"
        ]
        == 1
    )


def test_invalid_shape_nonfinite_and_nonpositive_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign019FeatureError):
        FEATURES.compute_factor_values(
            opens=np.ones((1, 239)),
            closes=np.ones((1, 239)),
        )

    opens = np.full((2, FEATURES.SELECTED_BAR_COUNT), 100.0)
    closes = np.full((2, FEATURES.SELECTED_BAR_COUNT), 101.0)
    opens[0, 3] = 0.0
    closes[1, 4] = np.nan
    values, eligible, quality = FEATURES.compute_factor_values(
        opens=opens,
        closes=closes,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert quality[f"{FEATURES.FACTOR_NAME}__nonpositive_open_close_rows"] == 1
    assert quality["invalid_required_open_close_rows"] == 1


def test_partition_reads_only_open_close_and_excludes_0930() -> None:
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
            "open": [-1.0] + [100.0] * FEATURES.SELECTED_BAR_COUNT,
            "close": [-1.0] + [101.0] * FEATURES.SELECTED_BAR_COUNT,
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
        "open",
        "close",
    )


def test_protocol_and_mechanism_are_fingerprint_bound_before_values() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_019_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_019_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN018_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN018_FEATURE_RUNNER_SHA256
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["campaign019_candidate_values_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["within_half_pair_count"] == 238
    assert audit["candidate"]["minimum_nonzero_pair_count"] == 120
    assert audit["comparison_catalog"]["semantic_registered_mechanism_count"] == 42
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 40
    assert audit["research_boundary"]["forward_return_fields_read"] is False
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 40
    assert comparisons[-1]["name"] == (
        "intraday_range_share_volume_confirmation_240m"
    )
    assert protocol["finite_post_admissibility_search"][
        "expected_trial_count_if_admitted"
    ] == 1


def test_generated_source_records_open_close_only_boundary() -> None:
    source = FEATURES._source
    assert '"minute_open_read": True' in source
    assert '"minute_close_read": True' in source
    assert '"minute_volume_read": False' in source
    assert 'value["source_close_read"] = True' in source
    assert 'value["source_volume_read"] = False' in source


def test_terminal_coverage_rejection_stops_before_comparisons_and_returns() -> None:
    record = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_019_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_iteration_status_20260729_campaign019.json"
        ).read_text()
    )
    no_return_path = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_019"
        / "no_return/20260729T014807Z_campaign019_no_return_audit.json"
    )
    no_return = json.loads(no_return_path.read_text())
    manifest = json.loads(
        (
            FEATURES.output_root(Path("/Volumes/DIsk/qlib-a-share-tushare-1m"))
            / "snapshot_manifest.json"
        ).read_text()
    )
    assert FEATURES._sha256(no_return_path) == FEATURES.NO_RETURN_AUDIT_SHA256
    assert manifest["source_fields_read"] == list(FEATURES.RAW_COLUMNS)
    assert manifest["source_close_read"] is True
    assert manifest["source_volume_read"] is False
    assert manifest["forward_return_fields_read"] is False
    assert manifest["factor_eligible_rows"][FEATURES.FACTOR_NAME] == 2_623_556
    assert manifest["quality"][
        f"{FEATURES.FACTOR_NAME}__insufficient_informative_pair_rows"
    ] == 5_100_942
    coverage = no_return["coverage_and_capacity"][FEATURES.FACTOR_NAME]
    uniqueness = no_return["uniqueness"][FEATURES.FACTOR_NAME]
    assert coverage["gate_passed_before_comparison_values"] is False
    assert coverage["median_coverage"] == pytest.approx(0.5629049174432891)
    assert coverage["p05_coverage"] == pytest.approx(0.39160894200061813)
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is False
    assert uniqueness["comparisons"] == []
    assert no_return["admissible_factor_count"] == 0
    assert no_return["historical_forward_return_fields_read"] is False
    assert no_return["training_or_model_fitting_performed"] is False
    assert record["decision"]["factor_terminal"] is True
    assert record["development_result"]["development_trial_count"] == 0
    assert state["research_counts"][
        "recorded_historical_development_trial_count"
    ] == 241
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"][
        "campaign020_concept_scouting_and_separate_no_return_research_allowed"
    ] is True

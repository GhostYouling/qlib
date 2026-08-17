from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign097_no_return_audit as audit


def test_protocol_has_frozen_v41_complete_and_numeric_orders() -> None:
    spec = audit.load_protocol()
    complete = audit.definitions.reconstruct_complete_definitions()
    comparisons = audit.definitions.reconstruct_comparisons()
    assert spec["candidate"]["name"] == audit.FACTOR_NAME
    assert len(complete) == audit.EXPECTED_COMPLETE_DEFINITION_COUNT == 128
    assert len(comparisons) == audit.EXPECTED_COMPARISON_COUNT == 125
    assert comparisons[-1] == {
        "name": audit.C96_FACTOR_NAME,
        "score_direction": "higher",
    }
    assert all(
        name not in {item["name"] for item in comparisons}
        for name in audit.STRUCTURALLY_NONNUMERIC_FACTORS
    )


def test_snapshot_and_identity_constants_are_frozen() -> None:
    assert audit.SNAPSHOT_MANIFEST_SHA256 == (
        "12e43008b4595a338bdd67ac21dcd543772e0517993623837770bec3bd31e0df"
    )
    assert audit.SNAPSHOT_DATASET_SHA256 == (
        "ab5b0f747600a4040c38e1d6453a0ec4242342803bc7acff257cc88f95ccfdb5"
    )
    assert audit.ELIGIBILITY_MANIFEST_SHA256 == (
        "3d81068f07ac61fe4cd04bd1a893e58759c06d88213263135fec5244e309b57b"
    )
    assert audit.EXPECTED_RAW_PARTITIONS == 33_015
    assert audit.EXPECTED_RAW_ROWS == 7_724_498
    assert audit.EXPECTED_ROWS == 1_331_759
    assert audit.EXPECTED_SESSIONS == 1_632


def test_compact_stock_day_keys_match_frozen_encoding() -> None:
    dates = pd.Series(pd.to_datetime(["2019-01-02", "2019-01-02", "2019-01-03"]))
    symbols = pd.Series(["SH600000", "sz000001", "BJ430047"])
    day_numbers = dates.to_numpy(dtype="datetime64[D]").astype(np.int64)
    expected = day_numbers * 4_000_000 + np.array(
        [1_600_000, 2_000_001, 3_430_047], dtype=np.int64
    )
    assert np.array_equal(audit.compact_stock_day_keys(dates, symbols), expected)


def test_align_candidate_year_uses_frozen_key_order_and_retains_missing() -> None:
    eligible = np.array([10, 20, 40], dtype=np.int64)
    observed_keys = np.array([40, 30, 10, 20], dtype=np.int64)
    observed_values = np.array([0.4, 0.3, 0.1, np.nan])
    keys, values, years = audit.align_candidate_year(
        eligible_keys=eligible,
        candidate_keys=observed_keys,
        candidate_values=observed_values,
        year=2019,
    )
    assert np.array_equal(keys, eligible)
    assert np.allclose(values[[0, 2]], [0.1, 0.4])
    assert np.isnan(values[1])
    assert np.array_equal(years, np.full(3, 2019, dtype=np.int64))


def test_align_candidate_year_fails_closed_on_missing_eligible_key() -> None:
    with pytest.raises(audit.Campaign097NoReturnAuditError, match="misses"):
        audit.align_candidate_year(
            eligible_keys=np.array([10, 20], dtype=np.int64),
            candidate_keys=np.array([10, 30], dtype=np.int64),
            candidate_values=np.array([0.1, 0.3]),
            year=2019,
        )


def test_candidate_range_is_frozen_without_loading_comparators() -> None:
    class Engine:
        FACTOR_RANGES: dict[str, tuple[float, float]] = {}

    engine = Engine()
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (-1.0, 1.0)


def test_comparison_loader_rejects_precoverage_call() -> None:
    with pytest.raises(audit.Campaign097NoReturnAuditError, match="before coverage"):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False},
            candidate_keys=np.array([1], dtype=np.int64),
            candidate_values=np.array([0.0]),
            gate={},
            engine=object(),
            comparison_engine=object(),
            workers=1,
        )

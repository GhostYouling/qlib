from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign096_no_return_audit as audit


def test_protocol_has_v39_complete_and_numeric_orders() -> None:
    spec = audit.load_protocol()
    assert spec["candidate"]["name"] == audit.FACTOR_NAME
    complete = audit.definitions.reconstruct_complete_definitions()
    comparisons = audit.definitions.reconstruct_comparisons()
    assert len(complete) == audit.EXPECTED_COMPLETE_DEFINITION_COUNT == 127
    assert len(comparisons) == audit.EXPECTED_COMPARISON_COUNT == 124
    assert complete[-1]["name"] == audit.C95_SEMANTIC_FACTOR
    assert audit.C95_SEMANTIC_FACTOR not in {item["name"] for item in comparisons}
    assert comparisons[-1]["name"] == "intraday_range_local_peak_clock_dispersion_236p"


def test_snapshot_constants_match_immutable_binding() -> None:
    assert audit.SNAPSHOT_MANIFEST_SHA256 == (
        "1b205f1b6d3b28248b765860b8cf0e4aecee07f960fa535402e316ba13c39a3a"
    )
    assert audit.SNAPSHOT_DATASET_SHA256 == (
        "67106bd4f5d4382b770cb79355c27ea4d8ca179296841b7bd9fa2963a46e09f3"
    )
    assert audit.SNAPSHOT_BINDING_SHA256 == (
        "c5a96fbcc3c9c2927aedc0b855c0eddf1633c1ea1cae1a9fd65de87a9389a68c"
    )
    assert audit.EXPECTED_ROWS == 1_331_759
    assert audit.EXPECTED_ELIGIBLE_ROWS == 1_193_690
    assert audit.EXPECTED_PARTITIONS == 7
    assert audit.EXPECTED_SESSIONS == 1_632


def test_candidate_range_is_frozen_without_loading_comparators() -> None:
    class Engine:
        FACTOR_RANGES: dict[str, tuple[float, float]] = {}

    engine = Engine()
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)

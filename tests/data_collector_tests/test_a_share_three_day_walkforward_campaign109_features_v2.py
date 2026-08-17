from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign109_features_v2 as feature


def test_recovery_binds_only_generated_extractor_symbol() -> None:
    assert (
        feature._generated["extract_intrabar_body_magnitude_serial_persistence"]
        is feature.extract_body_magnitude_serial_persistence
    )
    assert feature._generated["__file__"] == str(Path(feature.__file__).resolve())
    assert (
        feature.base.DEFAULT_IMPLEMENTATION_FREEZE
        == feature.DEFAULT_IMPLEMENTATION_FREEZE
    )
    assert (
        feature._generated["_validate_implementation_freeze"]
        is feature._validate_implementation_freeze
    )


def test_recovery_preserves_frozen_scientific_contract() -> None:
    assert feature.FACTOR_NAME == (
        "intraday_intrabar_body_magnitude_serial_persistence_238p"
    )
    assert feature.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "open",
        "close",
    )
    assert feature.NUMERIC_COMPARATOR_COUNT == 132
    assert feature.COMPLETE_DEFINITION_COUNT == 138

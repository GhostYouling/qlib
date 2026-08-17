from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign086_features as c86
from scripts import a_share_three_day_walkforward_campaign087_features as v1
from scripts import a_share_three_day_walkforward_campaign087_features_v2 as v2


def test_repair_inputs_are_immutable() -> None:
    assert v2._sha256(v2.REPAIR_PROTOCOL) == v2.REPAIR_PROTOCOL_SHA256
    assert v2._sha256(v1.DEFAULT_IMPLEMENTATION_FREEZE) == v2.V1_FREEZE_SHA256
    assert v2._sha256(v1.Path(v1.__file__).resolve()) == v2.V1_RUNNER_SHA256


def test_protocol_validation_temporarily_restores_predecessor_identity() -> None:
    original = c86.FACTOR_NAME
    c86.FACTOR_NAME = v1.FACTOR_NAME
    try:
        spec = v2._load_protocol_with_predecessor_identity()
        assert spec["candidate"]["name"] == v1.FACTOR_NAME
        assert c86.FACTOR_NAME == v1.FACTOR_NAME
    finally:
        c86.FACTOR_NAME = original


def test_corrected_builder_context_restores_every_campaign086_global() -> None:
    names = (
        "__file__",
        "DEFAULT_PROTOCOL",
        "DEFAULT_IMPLEMENTATION_FREEZE",
        "FACTOR_NAME",
        "FACTOR_FORMULA",
        "OUTPUT_RUN_ID",
        "RAW_COLUMNS",
        "OUTPUT_COLUMNS",
        "load_protocol",
        "_load_implementation_freeze",
        "extract_serial_persistence",
        "compact_stock_day_keys",
        "output_root",
    )
    before = {name: getattr(c86, name) for name in names}
    with v2._corrected_campaign086_builder():
        assert c86.FACTOR_NAME == v1.FACTOR_NAME
        assert c86.load_protocol is v2._load_protocol_with_predecessor_identity
        assert c86.output_root is v1.output_root
    assert all(getattr(c86, name) is value for name, value in before.items())


def test_repair_does_not_change_formula_fields_or_gates() -> None:
    assert v1.FACTOR_NAME == "intraday_range_amount_profile_alignment_js_240m"
    assert v1.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "high",
        "low",
        "amount",
    )
    assert v1.COMPARISON_COUNT == 116
    assert v1.FULL_DEFINITION_COUNT == 118

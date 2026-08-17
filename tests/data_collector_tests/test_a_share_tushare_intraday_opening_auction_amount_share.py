import numpy as np
import pandas as pd
import pytest

from scripts import (
    a_share_tushare_intraday_opening_auction_amount_share as RESEARCH,
)


TRADE_DATE = pd.Timestamp("2024-01-02")
SYMBOL = "SH600000"


def source_frame(
    *,
    opening_amount: float = 100.0,
    continuous_amounts: np.ndarray | None = None,
) -> pd.DataFrame:
    if continuous_amounts is None:
        continuous_amounts = np.arange(1.0, 241.0)
    continuous_amounts = np.asarray(continuous_amounts, dtype=float)
    assert continuous_amounts.shape == (240,)
    timestamps = [
        TRADE_DATE + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in RESEARCH.SOURCE_MINUTE_CODES
    ]
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": SYMBOL,
            "provider": "tushare",
            "amount": np.r_[opening_amount, continuous_amounts],
        }
    ).loc[:, RESEARCH.RAW_COLUMNS]


def base_frame() -> pd.DataFrame:
    return pd.DataFrame({"trade_date": [TRADE_DATE], "symbol": [SYMBOL]})


def compute(raw: pd.DataFrame):
    return RESEARCH.compute_partition_frame(raw, base_frame(), symbol=SYMBOL)


def test_preregistration_freezes_auction_mechanism_before_values():
    spec = RESEARCH.load_preregistration()
    current = spec["current_research_state"]
    candidate = spec["candidate"]
    validity = candidate["validity"]
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert current["sha256"] == RESEARCH.CURRENT_STATUS_SHA256
    assert current["terminal_mechanism_count_before_this_candidate"] == 46
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["diagnostic_direction"] == "higher"
    assert candidate["formula"] == RESEARCH.FACTOR_FORMULA
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert validity["zero_opening_auction_amount_policy"] == "valid_zero"
    assert len(comparisons) == 22
    assert [item["name"] for item in comparisons] == list(RESEARCH.COMPARISON_FACTORS)
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


def test_repository_chain_accepts_current_terminal_state():
    evidence = RESEARCH.validate_repository_chain(RESEARCH.load_preregistration())
    assert (
        evidence["authoritative_current_research_state"]["sha256"]
        == RESEARCH.CURRENT_STATUS_SHA256
    )
    assert (
        evidence["authoritative_current_research_state"]["terminal_mechanism_count"]
        == 46
    )


def test_opening_amount_is_numerator_and_all_241_amounts_are_denominator():
    raw = source_frame(opening_amount=100.0, continuous_amounts=np.ones(240))
    output, quality = compute(raw)
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(100.0 / 340.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1
    assert quality["invalid_required_amount_rows"] == 0
    assert quality["nonpositive_total_amount_rows"] == 0


def test_zero_opening_amount_is_valid_zero_not_missing():
    output, quality = compute(
        source_frame(opening_amount=0.0, continuous_amounts=np.ones(240))
    )
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1


def test_candidate_is_invariant_to_common_amount_scale():
    raw = source_frame(opening_amount=17.0)
    scaled = raw.copy()
    scaled["amount"] *= 1_000_000.0
    first, _ = compute(raw)
    second, _ = compute(scaled)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


def test_candidate_is_invariant_to_continuous_amount_permutation():
    continuous = np.arange(1.0, 241.0)
    first, _ = compute(source_frame(opening_amount=17.0, continuous_amounts=continuous))
    second, _ = compute(
        source_frame(opening_amount=17.0, continuous_amounts=continuous[::-1])
    )
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -1.0])
def test_invalid_required_amount_stays_missing(invalid):
    raw = source_frame()
    raw.loc[20, "amount"] = invalid
    output, quality = compute(raw)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["invalid_required_amount_rows"] == 1


def test_nonpositive_full_session_total_stays_missing():
    raw = source_frame(
        opening_amount=0.0,
        continuous_amounts=np.zeros(240),
    )
    output, quality = compute(raw)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["nonpositive_total_amount_rows"] == 1


def test_duplicate_timestamp_is_rejected():
    raw = source_frame()
    raw.loc[1, "datetime"] = raw.loc[0, "datetime"]
    with pytest.raises(
        RESEARCH.IntradayOpeningAuctionAmountShareError,
        match="identity or timestamp",
    ):
        compute(raw)


def test_missing_source_minute_is_rejected():
    raw = source_frame().iloc[:-1].copy()
    with pytest.raises(
        RESEARCH.IntradayOpeningAuctionAmountShareError,
        match="241-row grid",
    ):
        compute(raw)


def test_price_or_volume_column_cannot_enter_candidate_builder():
    raw = source_frame()
    raw["close"] = 10.0
    with pytest.raises(
        RESEARCH.IntradayOpeningAuctionAmountShareError,
        match="unexpected raw columns",
    ):
        RESEARCH.compute_partition_frame(raw, base_frame(), symbol=SYMBOL)


def test_unbound_snapshot_cannot_start_no_return_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(RESEARCH, "CANDIDATE_MANIFEST_SHA256", "")
    with pytest.raises(
        RESEARCH.IntradayOpeningAuctionAmountShareError,
        match="fingerprint must be bound",
    ):
        RESEARCH.run_no_return_audit(
            data_root=tmp_path,
            experiment_root=tmp_path / "experiments",
            workers=1,
        )


def test_unbound_manifest_validator_accepts_only_frozen_shape():
    manifest = {
        "kind": "a_share_tushare_intraday_opening_auction_amount_share_snapshot",
        "status": (
            "candidate_feature_complete_pending_ordered_no_return_"
            "coverage_capacity_and_uniqueness"
        ),
        "protocol_sha256": RESEARCH.PREREGISTRATION_SHA256,
        "raw_manifest_sha256": RESEARCH.RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": RESEARCH.JOINT_MANIFEST_SHA256,
        "output_run_id": RESEARCH.OUTPUT_RUN_ID,
        "factor_name": RESEARCH.FACTOR_NAME,
        "factor_direction": "higher",
        "factor_formula": RESEARCH.FACTOR_FORMULA,
        "partitions": 33_015,
        "rows": 7_724_498,
        "eligible_rows": 7_724_498,
        "dataset_sha256": "unit-test",
        "quality": {
            "base_rows": 7_724_498,
            "eligible_rows": 7_724_498,
            "invalid_required_amount_rows": 0,
            "nonpositive_total_amount_rows": 0,
            "endpoint_canonicalized_rows": 0,
            "range_violation_rows": 0,
        },
        "source_fields_read": list(RESEARCH.RAW_COLUMNS),
        "source_amount_read": True,
        "source_price_or_volume_read": False,
        "standalone_09_30_amount_in_numerator": True,
        "all_241_amounts_in_denominator": True,
        "source_rows_merged": False,
        "zero_09_30_amount_is_valid_zero": True,
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    RESEARCH._validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=False,
    )
    manifest["source_price_or_volume_read"] = True
    with pytest.raises(RESEARCH.IntradayOpeningAuctionAmountShareError):
        RESEARCH._validate_snapshot_manifest(
            manifest,
            require_fingerprint_constants=False,
        )


def test_diagnostic_preregistration_is_bound_before_return_read():
    spec = RESEARCH.load_diagnostic_preregistration()
    assert spec["factor"]["name"] == RESEARCH.FACTOR_NAME
    assert spec["factor"]["direction"] == "higher"
    assert (
        spec["no_return_evidence"]["ordered_audit"]["sha256"]
        == RESEARCH.NO_RETURN_AUDIT_SHA256
    )
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_registration"]
        is False
    )


def test_consumption_marker_prevents_second_diagnostic(tmp_path):
    marker = tmp_path / RESEARCH.CONSUMPTION_FILENAME
    marker.write_text("{}\n", encoding="utf-8")
    with pytest.raises(
        RESEARCH.IntradayOpeningAuctionAmountShareError,
        match="already consumed",
    ):
        RESEARCH.require_diagnostic_unconsumed(tmp_path)

import argparse
import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest

from scripts import (
    a_share_tushare_intraday_cumulative_vwap_crossing_rate as RESEARCH,
)


TRADE_DATE = pd.Timestamp("2024-01-02")
SYMBOL = "SH600000"


def source_frame(
    *,
    closes: np.ndarray | None = None,
    volumes: np.ndarray | None = None,
    amounts: np.ndarray | None = None,
) -> pd.DataFrame:
    if closes is None:
        closes = np.where(np.arange(240) % 2 == 0, 11.0, 9.0)
    if volumes is None:
        volumes = np.full(240, 100.0)
    if amounts is None:
        amounts = np.full(240, 1000.0)
    closes = np.asarray(closes, dtype=float)
    volumes = np.asarray(volumes, dtype=float)
    amounts = np.asarray(amounts, dtype=float)
    assert closes.shape == volumes.shape == amounts.shape == (240,)
    timestamps = [
        TRADE_DATE + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in RESEARCH.CONTINUOUS_MINUTE_CODES
    ]
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": SYMBOL,
            "provider": "tushare",
            "close": closes,
            "volume": volumes,
            "amount": amounts,
        }
    ).loc[:, RESEARCH.RAW_COLUMNS]


def base_frame() -> pd.DataFrame:
    return pd.DataFrame({"trade_date": [TRADE_DATE], "symbol": [SYMBOL]})


def compute(raw: pd.DataFrame):
    return RESEARCH.compute_partition_frame(raw, base_frame(), symbol=SYMBOL)


def test_preregistration_freezes_future_only_candidate_49():
    spec = RESEARCH.load_preregistration()
    candidate = spec["candidate"]
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert candidate["ordinal"] == 49
    assert candidate["name"] == RESEARCH.FACTOR_NAME
    assert candidate["prospective_direction"] == "higher"
    assert candidate["source_fields_allowed"] == list(RESEARCH.RAW_COLUMNS)
    assert len(comparisons) == 24
    assert [item["name"] for item in comparisons] == list(RESEARCH.COMPARISON_FACTORS)
    assert (
        spec["post_no_return_decision"]["historical_return_diagnostic_allowed"] is False
    )
    assert spec["research_boundary"]["historical_daily_price_fields_read"] is False
    assert spec["research_boundary"]["historical_forward_return_fields_read"] is False


def test_repository_chain_accepts_current_state_and_future_policy():
    evidence = RESEARCH.validate_repository_chain(RESEARCH.load_preregistration())
    assert (
        evidence["future-only_minute_research_policy"]["sha256"]
        == RESEARCH.POLICY_SHA256
    )
    assert (
        evidence["current_three-day_iteration_state"]["sha256"]
        == RESEARCH.CURRENT_STATUS_SHA256
    )


def test_alternating_around_constant_cumulative_vwap_has_full_crossing_rate():
    output, quality = compute(source_frame())
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1


def test_one_sided_path_has_zero_crossing_rate():
    output, quality = compute(source_frame(closes=np.full(240, 11.0)))
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(0.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["eligible_rows"] == 1


def test_exact_zero_deviation_signs_are_removed_without_fill():
    closes = np.full(240, 10.0)
    closes[[0, 2, 4]] = [11.0, 9.0, 11.0]
    output, quality = compute(source_frame(closes=closes))
    assert output.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(1.0)
    assert output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["fewer_than_two_nonzero_deviation_sign_rows"] == 0


def test_fewer_than_two_nonzero_deviation_signs_stays_missing():
    closes = np.full(240, 10.0)
    closes[0] = 11.0
    output, quality = compute(source_frame(closes=closes))
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["fewer_than_two_nonzero_deviation_sign_rows"] == 1


def test_joint_zero_activity_bar_is_inactive_and_retained():
    volumes = np.full(240, 100.0)
    amounts = np.full(240, 1000.0)
    volumes[1] = 0.0
    amounts[1] = 0.0
    raw = source_frame(volumes=volumes, amounts=amounts)
    first, quality = compute(raw)
    changed = raw.copy()
    changed.loc[1, "close"] = 1000.0
    second, _ = compute(changed)
    assert first.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        second.loc[0, RESEARCH.FACTOR_NAME]
    )
    assert quality["one_sided_zero_volume_or_amount_rows"] == 0


def test_one_sided_zero_activity_invalidates_whole_stock_day():
    volumes = np.full(240, 100.0)
    amounts = np.full(240, 1000.0)
    volumes[10] = 0.0
    output, quality = compute(source_frame(volumes=volumes, amounts=amounts))
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]
    assert quality["one_sided_zero_volume_or_amount_rows"] == 1


def test_common_volume_and_amount_scale_does_not_change_candidate():
    raw = source_frame()
    scaled = raw.copy()
    scaled["volume"] *= 1000.0
    scaled["amount"] *= 1000.0
    first, _ = compute(raw)
    second, _ = compute(scaled)
    assert second.loc[0, RESEARCH.FACTOR_NAME] == pytest.approx(
        first.loc[0, RESEARCH.FACTOR_NAME]
    )


@pytest.mark.parametrize(
    ("column", "invalid"),
    [
        ("close", np.nan),
        ("close", 0.0),
        ("volume", np.inf),
        ("volume", -1.0),
        ("amount", np.nan),
        ("amount", -1.0),
    ],
)
def test_invalid_required_value_stays_missing(column, invalid):
    raw = source_frame()
    raw.loc[20, column] = invalid
    output, _ = compute(raw)
    assert np.isnan(output.loc[0, RESEARCH.FACTOR_NAME])
    assert not output.loc[0, f"{RESEARCH.FACTOR_NAME}_eligible"]


def test_duplicate_timestamp_is_rejected():
    raw = source_frame()
    raw.loc[1, "datetime"] = raw.loc[0, "datetime"]
    with pytest.raises(
        RESEARCH.IntradayCumulativeVwapCrossingRateError,
        match="identity or timestamp",
    ):
        compute(raw)


def test_missing_source_minute_is_rejected():
    with pytest.raises(
        RESEARCH.IntradayCumulativeVwapCrossingRateError,
        match="240-row grid",
    ):
        compute(source_frame().iloc[:-1].copy())


def test_forbidden_source_column_cannot_enter_candidate_builder():
    raw = source_frame()
    raw["open"] = raw["close"]
    with pytest.raises(
        RESEARCH.IntradayCumulativeVwapCrossingRateError,
        match="unexpected raw columns",
    ):
        RESEARCH.compute_partition_frame(raw, base_frame(), symbol=SYMBOL)


def test_unbound_snapshot_cannot_start_no_return_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(RESEARCH, "CANDIDATE_MANIFEST_SHA256", "")
    with pytest.raises(
        RESEARCH.IntradayCumulativeVwapCrossingRateError,
        match="fingerprint must be bound",
    ):
        RESEARCH.run_no_return_audit(
            data_root=tmp_path,
            experiment_root=tmp_path / "experiments",
            workers=1,
        )


def test_unbound_manifest_validator_accepts_only_frozen_shape():
    quality = {
        "base_rows": 7_724_498,
        "eligible_rows": 7_000_000,
        "invalid_required_close_rows": 0,
        "invalid_required_volume_amount_rows": 0,
        "one_sided_zero_volume_or_amount_rows": 0,
        "fewer_than_two_valid_cumulative_vwap_positions_rows": 0,
        "fewer_than_two_nonzero_deviation_sign_rows": 724_498,
        "endpoint_canonicalized_rows": 0,
        "range_violation_rows": 0,
    }
    manifest = {
        "kind": "a_share_tushare_intraday_cumulative_vwap_crossing_rate_snapshot",
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
        "eligible_rows": 7_000_000,
        "dataset_sha256": "unit-test",
        "quality": quality,
        "source_fields_read": list(RESEARCH.RAW_COLUMNS),
        "source_close_volume_amount_read": True,
        "source_open_high_low_read": False,
        "standalone_09_30_row_excluded_from_formula": True,
        "cumulative_vwap_is_causal": True,
        "one_sided_zero_invalidates_stock_day": True,
        "joint_zero_bar_retained_as_inactive": True,
        "exact_zero_deviation_sign_removed": True,
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
        "historical_return_diagnostic_allowed": False,
    }
    RESEARCH._validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=False,
    )
    manifest["historical_return_diagnostic_allowed"] = True
    with pytest.raises(RESEARCH.IntradayCumulativeVwapCrossingRateError):
        RESEARCH._validate_snapshot_manifest(
            manifest,
            require_fingerprint_constants=False,
        )


def test_future_registration_is_bound_before_first_eligible_session():
    registration = RESEARCH.load_future_registration()
    assert registration["factor"]["name"] == RESEARCH.FACTOR_NAME
    assert registration["factor"]["direction"] == "higher"
    assert (
        registration["source_evidence"]["ordered_no_return_audit"]["sha256"]
        == RESEARCH.NO_RETURN_AUDIT_SHA256
    )
    assert (
        registration["future_data_boundary"]["earliest_eligible_signal_session"]
        == "the first accepted local provider-calendar session on or after 2026-07-27"
    )
    assert registration["decision"]["historical_return_diagnostic_allowed"] is False
    assert registration["decision"]["current_signal_exists"] is False


def test_future_execution_protocol_is_bound_before_any_real_outcome():
    protocol = RESEARCH.load_future_execution_protocol()
    assert (
        RESEARCH.foundation.file_digest(RESEARCH.DEFAULT_FUTURE_EXECUTION_PROTOCOL)
        == RESEARCH.FUTURE_EXECUTION_PROTOCOL_SHA256
    )
    assert protocol["portfolio"]["paper_only"] is True
    assert protocol["current_state"] == {
        "real_future_signal_count": 0,
        "real_entry_count": 0,
        "real_exit_count": 0,
        "completed_future_rank_ic_count": 0,
        "portfolio_return_exists": False,
        "investment_advice": False,
    }


def test_future_ledgers_initialize_idempotently_and_reject_partial_state(tmp_path):
    signal_path = tmp_path / "signal.json"
    execution_path = tmp_path / "execution.json"
    first = RESEARCH.initialize_future_ledgers(
        signal_path=signal_path,
        execution_path=execution_path,
    )
    second = RESEARCH.initialize_future_ledgers(
        signal_path=signal_path,
        execution_path=execution_path,
    )
    assert first["signal_entries"] == second["signal_entries"] == 0
    assert first["execution_entries"] == second["execution_entries"] == 0
    assert first["provider_request_issued"] is False
    execution_path.unlink()
    with pytest.raises(
        RESEARCH.IntradayCumulativeVwapCrossingRateError,
        match="partial initialization",
    ):
        RESEARCH.initialize_future_ledgers(
            signal_path=signal_path,
            execution_path=execution_path,
        )


def test_future_ledger_append_is_hash_linked_and_cannot_backfill(tmp_path):
    signal_path = tmp_path / "signal.json"
    execution_path = tmp_path / "execution.json"
    RESEARCH.initialize_future_ledgers(
        signal_path=signal_path,
        execution_path=execution_path,
    )
    entry = RESEARCH.append_future_ledger_entry(
        path=signal_path,
        kind=RESEARCH.FUTURE_SIGNAL_LEDGER_KIND,
        payload={
            "entry_id": "signal-20260727",
            "session_date": "2026-07-27",
            "entry_kind": "unit_test_signal",
        },
    )
    record = RESEARCH.validate_future_ledger(
        signal_path,
        RESEARCH.FUTURE_SIGNAL_LEDGER_KIND,
    )
    assert entry["ordinal"] == 1
    assert record["entries"] == [entry]
    assert record["chain_tip_sha256"] == entry["entry_sha256"]
    with pytest.raises(
        RESEARCH.IntradayCumulativeVwapCrossingRateError,
        match="identity or date boundary",
    ):
        RESEARCH.append_future_ledger_entry(
            path=signal_path,
            kind=RESEARCH.FUTURE_SIGNAL_LEDGER_KIND,
            payload={
                "entry_id": "signal-20260724",
                "session_date": "2026-07-24",
                "entry_kind": "unit_test_signal",
            },
        )


def test_future_preflight_is_local_only_and_requires_accepted_daily_session(tmp_path):
    provider_uri = tmp_path / "provider"
    (provider_uri / "calendars").mkdir(parents=True)
    (provider_uri / "instruments").mkdir()
    (provider_uri / "price_basis.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "price_basis": RESEARCH.research.REQUIRED_PRICE_BASIS,
                "failures": {},
                "daily_sources": ["baostock"],
            }
        ),
        encoding="utf-8",
    )
    (provider_uri / "calendars" / "day.txt").write_text(
        "2026-07-27\n",
        encoding="utf-8",
    )
    instruments = "\n".join(
        f"SZ{index:06d}\t2026-01-01\t2026-07-27" for index in range(1, 51)
    )
    (provider_uri / "instruments" / "buyable_main_chinext.txt").write_text(
        f"{instruments}\n",
        encoding="utf-8",
    )
    signal_path = tmp_path / "signal.json"
    execution_path = tmp_path / "execution.json"
    RESEARCH.initialize_future_ledgers(
        signal_path=signal_path,
        execution_path=execution_path,
    )
    result = RESEARCH.future_session_preflight(
        session_date=dt.date(2026, 7, 27),
        data_root=tmp_path / "external",
        provider_uri=provider_uri,
        now=dt.datetime(2026, 7, 27, 17, 0, tzinfo=RESEARCH.CHINA_TZ),
        token_configured=True,
        signal_path=signal_path,
        execution_path=execution_path,
    )
    assert result["ready"] is True
    assert result["recommended_cli_exit_code"] == 0
    assert result["active_buyable_symbol_count"] == 50
    assert result["provider_request_issued"] is False
    assert result["minute_rows_read"] is False
    assert result["signal_or_execution_entry_written"] is False
    assert result["new_source_to_signal_collection_requires_same_local_date"] is True

    delayed = RESEARCH.future_session_preflight(
        session_date=dt.date(2026, 7, 27),
        data_root=tmp_path / "external",
        provider_uri=provider_uri,
        now=dt.datetime(2026, 7, 28, 17, 0, tzinfo=RESEARCH.CHINA_TZ),
        token_configured=True,
        signal_path=signal_path,
        execution_path=execution_path,
    )
    assert delayed["ready"] is False
    assert delayed["recommended_cli_exit_code"] == 2
    assert (
        "past_session_delayed_source_to_signal_backfill_forbidden"
        in delayed["failures"]
    )
    assert "session_not_yet_complete_after_close_buffer" not in delayed["failures"]
    assert delayed["provider_request_issued"] is False

    before_boundary = RESEARCH.future_session_preflight(
        session_date=dt.date(2026, 7, 24),
        data_root=tmp_path / "external",
        provider_uri=provider_uri,
        now=dt.datetime(2026, 7, 27, 17, 0, tzinfo=RESEARCH.CHINA_TZ),
        token_configured=True,
        signal_path=signal_path,
        execution_path=execution_path,
    )
    assert before_boundary["ready"] is False
    assert before_boundary["recommended_cli_exit_code"] == 2
    assert "session_precedes_immutable_future_boundary" in before_boundary["failures"]
    assert before_boundary["provider_request_issued"] is False

    (provider_uri / "price_basis.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "price_basis": RESEARCH.research.REQUIRED_PRICE_BASIS,
                "failures": {},
                "daily_sources": ["tushare"],
            }
        ),
        encoding="utf-8",
    )
    tushare_daily_source = RESEARCH.future_session_preflight(
        session_date=dt.date(2026, 7, 27),
        data_root=tmp_path / "external",
        provider_uri=provider_uri,
        now=dt.datetime(2026, 7, 27, 17, 0, tzinfo=RESEARCH.CHINA_TZ),
        token_configured=True,
        signal_path=signal_path,
        execution_path=execution_path,
    )
    assert tushare_daily_source["ready"] is True
    assert tushare_daily_source["accepted_daily_sources"] == ["tushare"]
    assert tushare_daily_source["provider_request_issued"] is False

    (provider_uri / "price_basis.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "price_basis": RESEARCH.research.REQUIRED_PRICE_BASIS,
                "failures": {},
                "daily_sources": ["baostock", "eastmoney"],
            }
        ),
        encoding="utf-8",
    )
    mixed_source = RESEARCH.future_session_preflight(
        session_date=dt.date(2026, 7, 27),
        data_root=tmp_path / "external",
        provider_uri=provider_uri,
        now=dt.datetime(2026, 7, 27, 17, 0, tzinfo=RESEARCH.CHINA_TZ),
        token_configured=True,
        signal_path=signal_path,
        execution_path=execution_path,
    )
    assert mixed_source["ready"] is False
    assert mixed_source["recommended_cli_exit_code"] == 2
    assert (
        "local_daily_source_not_single_accepted_provider"
        in mixed_source["failures"]
    )
    assert mixed_source["provider_request_issued"] is False


@pytest.mark.parametrize(("ready", "expected"), [(True, 0), (False, 2)])
def test_future_preflight_cli_exit_code_matches_readiness(
    tmp_path, monkeypatch, capsys, ready, expected
):
    monkeypatch.setattr(
        RESEARCH,
        "parse_args",
        lambda: argparse.Namespace(
            command="future-preflight",
            data_root=tmp_path,
            session=dt.date(2026, 7, 27),
        ),
    )
    monkeypatch.setattr(
        RESEARCH,
        "future_session_preflight",
        lambda **_: {
            "status": (
                "ready_for_explicit_future_session_collection"
                if ready
                else "not_ready_no_provider_request"
            ),
            "ready": ready,
            "recommended_cli_exit_code": expected,
        },
    )

    assert RESEARCH.main() == expected
    assert json.loads(capsys.readouterr().out)["ready"] is ready

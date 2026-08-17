#!/usr/bin/env python3
"""Build Campaign120's frozen return-direction phrase snapshot without returns."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "a_share_three_day_walkforward_campaign117_features.py"
)
_TEMPLATE_SHA256 = "7b9edced1298e69c29cd20699087cf9695d94f1ba01909b9b081365f55c5d197"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign117 feature-builder template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "Build Campaign117's frozen amount weak-order entropy snapshot without returns.",
        "Build Campaign120's frozen return-direction phrase snapshot without returns.",
    ),
    (
        "intraday_amount_weak_order_entropy_236t",
        "intraday_return_direction_dictionary_phrase_count_238s",
    ),
    (
        "normalized Shannon entropy over the frozen 13-state exact weak-order "
        '"\n    "distribution of 118 morning plus 118 afternoon overlapping raw-amount triples',
        "sum of frozen incremental dictionary phrase counts over separate morning "
        '"\n    "and afternoon 119-symbol exact close-direction sequences',
    ),
    ("amount weak-order entropy", "return-direction dictionary phrase count"),
    (
        "``datetime,symbol,provider,amount``",
        "``datetime,symbol,provider,close``",
    ),
    (
        "extract_amount_weak_order_entropy",
        "extract_direction_dictionary_phrase_count",
    ),
    ("attach_entropy_values", "attach_dictionary_values"),
    ("amount_weak_order_entropy", "direction_dictionary_phrase_count"),
    ("valid_entropy_sessions", "valid_dictionary_sessions"),
    ("invalid_amount_sessions", "invalid_close_sessions"),
    ("nonpositive_total_amount_sessions", "parser_support_mismatch_sessions"),
    (
        "recognized_state_observations",
        "recognized_direction_symbol_observations",
    ),
    (
        "exact_tie_triple_observations",
        "exact_zero_direction_symbol_observations",
    ),
    ("entropy_rule", "dictionary_rule"),
    ("weak_order_state_count", "dictionary_parser_count"),
    ("positive_total_amount_required", "exact_symbol_support_required"),
    (
        "amount_magnitude_used_after_ordinal_encoding",
        "return_magnitude_used_after_direction_encoding",
    ),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "close")',
    ),
    (
        "a_share_three_day_walkforward_campaign116_features as c116",
        "a_share_three_day_walkforward_campaign119_features as c119",
    ),
    ("c116.reconstruct_comparisons()", "c119.reconstruct_comparisons()"),
    (
        "items = [dict(item) for item in c119.reconstruct_comparisons()]",
        "items = [dict(item) for item in c119.reconstruct_comparisons()]\n"
        '    items.append({"name": c119.FACTOR_NAME, "score_direction": "higher"})',
    ),
    (
        "c116.reconstruct_complete_definitions()",
        "c119.reconstruct_complete_definitions()",
    ),
    (
        "01cda2c9ec8646ca3d8db86f20e2720514c26c0a6a6044faeac01e6420f9fcb7",
        "eb23880c27d2e0a575d0f28218794872cb66bf681940bdb790f1bee865020a6e",
    ),
    (
        "c42b5d7624c48964cdc95605bf439b18664b1a8912622b0c7a888d8676988407",
        "183fd92c1b5511017332b904d48db3e2e2370ae1e1101f37c8d4377305557adb",
    ),
    (
        "a9d44ce8b383a9ecb29f96b8df19ac1bc28e7cceaac8397c609be6130e4ef03b",
        "a3deaf480b084fc97f556c642db539b9672636a2a38c69664bc4cba94ee5d685",
    ),
    ("numeric_policy_v104", "numeric_policy_v109"),
    ("NUMERIC_COMPARATOR_COUNT = 134", "NUMERIC_COMPARATOR_COUNT = 137"),
    (
        "31d788db467f558a0ac538315343090f1b3ad4cb27a26136a49ebaa88b2fdbf2",
        "aaac5973c5f93e4cb6275f0b5ae92bc04ce1f7968b100785d8763565fa095621",
    ),
    (
        "f7612c7dd7d4a0c015146d60a86e244d91b21a8b6638e4f84e7a18d035581d21",
        "a5d850195b0aab697dc60b1331816ca7e557e4389d17290eafee5a036fb8950f",
    ),
    (
        "ed61b10f3acb939c10ae5759f33aafde377cc921dd99c642300603b50a4851c5",
        "51c96c7cd0344f70433d2401bfd38ca9e6b5901f62e8ad2fd27714957431fc17",
    ),
    (
        "a_share_three_day_walkforward_campaign_117_no_return_preregistration_20260813.json",
        "a_share_three_day_walkforward_campaign_120_no_return_preregistration_20260814.json",
    ),
    (
        "a_share_three_day_walkforward_campaign_117_no_return_implementation_freeze_20260813.json",
        "a_share_three_day_walkforward_campaign_120_no_return_implementation_freeze_20260814.json",
    ),
    ("COMPLETE_DEFINITION_COUNT = 143", "COMPLETE_DEFINITION_COUNT = 146"),
    ("PRIOR_COMPLETE_DEFINITION_COUNT = 142", "PRIOR_COMPLETE_DEFINITION_COUNT = 145"),
    (
        "_source = _source.replace(\n"
        "    '\"exact_symbol_support_required\": False',\n"
        "    '\"exact_symbol_support_required\": True',\n"
        ")",
        "_source = _source.replace(\n"
        "    '\"exact_symbol_support_required\": False',\n"
        "    '\"exact_symbol_support_required\": True',\n"
        ")\n"
        "_source = _source.replace(\n"
        '    "values.ge(0.0) & values.le(1.0)",\n'
        '    "values.ge(2.0) & values.le(238.0)",\n'
        ")\n"
        "_source = _source.replace(\n"
        '    "{FACTOR_NAME: [0.0, 1.0]}",\n'
        '    "{FACTOR_NAME: [2.0, 238.0]}",\n'
        ")",
    ),
    ("Campaign117", "Campaign120"),
    ("campaign117", "campaign120"),
    ("campaign_117", "campaign_120"),
):
    if _old not in _source:
        raise RuntimeError(f"Campaign120 feature transformation token absent: {_old!r}")
    _source = _source.replace(_old, _new)

_source = _source.replace(
    '"dictionary_parser_count": 0', '"dictionary_parser_count": 1'
)
_source = _source.replace(
    '"exact_symbol_support_required": False',
    '"exact_symbol_support_required": True',
)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign120_features_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)


def extract_direction_dictionary_phrase_count(
    raw: Any, *, symbol: str
) -> tuple[Any, dict[str, int]]:
    """Validate exact 241-row grids and compute the frozen phrase count."""

    pd = _implementation["pd"]
    np = _implementation["np"]
    formula = _implementation["formula"]
    error = _implementation["Campaign120FeatureError"]
    raw_columns = _implementation["RAW_COLUMNS"]
    factor_short_name = _implementation["FACTOR_SHORT_NAME"]
    generated = _implementation["_generated"]
    if tuple(raw.columns) != raw_columns:
        raise error(f"unexpected raw columns for {symbol}: {tuple(raw.columns)}")
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            factor_short_name: pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_dictionary_sessions": 0,
        "invalid_close_sessions": 0,
        "parser_support_mismatch_sessions": 0,
        "recognized_direction_symbol_observations": 0,
        "exact_zero_direction_symbol_observations": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise error(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(generated["SOURCE_BAR_COUNT"]).all()
        or not distinct.eq(generated["SOURCE_BAR_COUNT"]).all()
        or not work["minute_code"].isin(generated["SOURCE_MINUTE_CODE_SET"]).all()
    ):
        raise error(f"raw minute grid changed for {symbol}")
    selected = work.loc[
        work["minute_code"].isin(generated["CONTINUOUS_MINUTE_CODE_SET"]),
        ["trade_date", "minute_code", "close"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"],
        categories=generated["CONTINUOUS_MINUTE_CODES"],
        ordered=True,
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(selected) != len(dates) * formula.SELECTED_BAR_COUNT:
        raise error(f"continuous minute grid changed for {symbol}")
    closes = selected["close"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    values, eligible, formula_quality = (
        formula.compute_direction_dictionary_phrase_count(closes)
    )
    return pd.DataFrame({"trade_date": dates, factor_short_name: values}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_dictionary_sessions": int(eligible.sum()),
        "invalid_close_sessions": int(formula_quality["invalid_close_rows"]),
        "parser_support_mismatch_sessions": 0,
        "recognized_direction_symbol_observations": int(
            formula_quality["recognized_direction_symbol_observations"]
        ),
        "exact_zero_direction_symbol_observations": int(
            formula_quality["exact_zero_direction_symbol_observations"]
        ),
    }


def validate_value_semantics(frame: Any) -> tuple[int, int]:
    pd = _implementation["pd"]
    np = _implementation["np"]
    error = _implementation["Campaign120FeatureError"]
    factor_name = _implementation["FACTOR_NAME"]
    expected = (
        "trade_date",
        "symbol",
        "provider",
        factor_name,
        f"{factor_name}_eligible",
    )
    if tuple(frame.columns) != expected:
        raise error("Campaign120 output columns changed")
    values = pd.to_numeric(frame[factor_name], errors="coerce")
    eligible = frame[f"{factor_name}_eligible"].astype(bool)
    observed = values[eligible].to_numpy(dtype=np.float64)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < 2.0) | (values[eligible] > 238.0)).any()
        or not np.equal(observed, np.floor(observed)).all()
        or values[~eligible].notna().any()
    ):
        raise error("Campaign120 value semantics changed")
    return int(len(frame)), int(eligible.sum())


_implementation["extract_direction_dictionary_phrase_count"] = (
    extract_direction_dictionary_phrase_count
)
_implementation["validate_value_semantics"] = validate_value_semantics
_implementation["_generated"][
    "extract_direction_dictionary_phrase_count"
] = extract_direction_dictionary_phrase_count
_implementation["_generated"]["validate_value_semantics"] = validate_value_semantics
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())

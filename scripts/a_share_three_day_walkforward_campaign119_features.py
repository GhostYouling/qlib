#!/usr/bin/env python3
"""Build Campaign119's frozen range-boundary state snapshot without returns."""

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
        "Build Campaign119's frozen range-boundary state entropy snapshot without returns.",
    ),
    (
        "intraday_amount_weak_order_entropy_236t",
        "intraday_range_boundary_direction_state_entropy_238p",
    ),
    (
        "normalized Shannon entropy over the frozen 13-state exact weak-order "
        '"\n    "distribution of 118 morning plus 118 afternoon overlapping raw-amount triples',
        "normalized Shannon entropy over the frozen nine exact joint low/high direction "
        '"\n    "states from 119 morning plus 119 afternoon adjacent pairs',
    ),
    ("amount weak-order entropy", "range-boundary direction-state entropy"),
    (
        "``datetime,symbol,provider,amount``",
        "``datetime,symbol,provider,high,low``",
    ),
    (
        "extract_amount_weak_order_entropy",
        "extract_range_boundary_direction_state_entropy",
    ),
    ("attach_entropy_values", "attach_state_entropy_values"),
    ("amount_weak_order_entropy", "range_boundary_direction_state_entropy"),
    ("invalid_amount_sessions", "invalid_range_value_sessions"),
    ("nonpositive_total_amount_sessions", "invalid_high_below_low_sessions"),
    ("exact_tie_triple_observations", "exact_joint_tie_pair_observations"),
    ("weak_order_state_count", "range_boundary_direction_state_count"),
    ("positive_total_amount_required", "exact_pair_support_required"),
    (
        "amount_magnitude_used_after_ordinal_encoding",
        "range_magnitude_used_after_state_encoding",
    ),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    ),
    (
        "a_share_three_day_walkforward_campaign116_features as c116",
        "a_share_three_day_walkforward_campaign118_features as c118",
    ),
    ("c116.reconstruct_comparisons()", "c118.reconstruct_comparisons()"),
    (
        "items = [dict(item) for item in c118.reconstruct_comparisons()]",
        "items = [dict(item) for item in c118.reconstruct_comparisons()]\n"
        '    items.append({"name": c118.FACTOR_NAME, "score_direction": "higher"})',
    ),
    (
        "c116.reconstruct_complete_definitions()",
        "c118.reconstruct_complete_definitions()",
    ),
    (
        "01cda2c9ec8646ca3d8db86f20e2720514c26c0a6a6044faeac01e6420f9fcb7",
        "41d10d618c59e1c7f61b075ff1d14d4d6045d763cbdb15f487dcb4a801094f19",
    ),
    (
        "c42b5d7624c48964cdc95605bf439b18664b1a8912622b0c7a888d8676988407",
        "8e3ac7729d90f92c2b59a334704f1152f4b1932e194697b5f4e10b239c2b83a0",
    ),
    (
        "a9d44ce8b383a9ecb29f96b8df19ac1bc28e7cceaac8397c609be6130e4ef03b",
        "9fdf7df6ccf9fab631a7b56f0e4769b8d684f93a3c3cc0455e504cf2299b473a",
    ),
    ("numeric_policy_v104", "numeric_policy_v107"),
    ("NUMERIC_COMPARATOR_COUNT = 134", "NUMERIC_COMPARATOR_COUNT = 136"),
    (
        "31d788db467f558a0ac538315343090f1b3ad4cb27a26136a49ebaa88b2fdbf2",
        "bb1b850f4277919eb1866e9bfb014577efca6d0f81b184a31b3c202f50eb0282",
    ),
    (
        "f7612c7dd7d4a0c015146d60a86e244d91b21a8b6638e4f84e7a18d035581d21",
        "51c96c7cd0344f70433d2401bfd38ca9e6b5901f62e8ad2fd27714957431fc17",
    ),
    (
        "ed61b10f3acb939c10ae5759f33aafde377cc921dd99c642300603b50a4851c5",
        "077e6c79356fe70193df4d424a004de5734ea395ef06df52e11e3804915d56f7",
    ),
    ("COMPLETE_DEFINITION_COUNT = 143", "COMPLETE_DEFINITION_COUNT = 145"),
    ("PRIOR_COMPLETE_DEFINITION_COUNT = 142", "PRIOR_COMPLETE_DEFINITION_COUNT = 144"),
    (
        "_source.replace('\"range_boundary_direction_state_count\": 0', '\"range_boundary_direction_state_count\": 13')",
        "_source.replace('\"range_boundary_direction_state_count\": 0', '\"range_boundary_direction_state_count\": 9')",
    ),
    ('tests.get("passed") == 16', 'tests.get("passed") == 17'),
    ("Campaign117", "Campaign119"),
    ("campaign117", "campaign119"),
    ("campaign_117", "campaign_119"),
):
    if _old not in _source:
        raise RuntimeError(f"Campaign119 feature transformation token absent: {_old!r}")
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign119_features_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)


def extract_range_boundary_direction_state_entropy(
    raw: Any, *, symbol: str
) -> tuple[Any, dict[str, int]]:
    """Validate exact 241-row grids and compute the frozen 238-pair entropy."""

    pd = _implementation["pd"]
    np = _implementation["np"]
    formula = _implementation["formula"]
    error = _implementation["Campaign119FeatureError"]
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
        "valid_entropy_sessions": 0,
        "invalid_range_value_sessions": 0,
        "invalid_high_below_low_sessions": 0,
        "recognized_state_observations": 0,
        "exact_joint_tie_pair_observations": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["high"] = pd.to_numeric(work["high"], errors="coerce")
    work["low"] = pd.to_numeric(work["low"], errors="coerce")
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
        ["trade_date", "minute_code", "high", "low"],
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
    highs = selected["high"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    lows = selected["low"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    values, eligible, _state_counts, _state_codes, formula_quality = (
        formula.compute_range_boundary_direction_state_entropy(highs, lows)
    )
    return pd.DataFrame({"trade_date": dates, factor_short_name: values}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_entropy_sessions": int(eligible.sum()),
        "invalid_range_value_sessions": int(
            formula_quality["nonfinite_high_low_rows"]
            + formula_quality["nonpositive_high_low_rows"]
        ),
        "invalid_high_below_low_sessions": int(formula_quality["high_below_low_rows"]),
        "recognized_state_observations": int(
            formula_quality["recognized_state_observations"]
        ),
        "exact_joint_tie_pair_observations": int(
            formula_quality["exact_joint_tie_pair_observations"]
        ),
    }


_implementation["extract_range_boundary_direction_state_entropy"] = (
    extract_range_boundary_direction_state_entropy
)
_implementation["_generated"][
    "extract_range_boundary_direction_state_entropy"
] = extract_range_boundary_direction_state_entropy
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())

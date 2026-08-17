#!/usr/bin/env python3
"""Run Campaign136's exact one-trial 2019-2023 historical walk-forward."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset

from scripts import a_share_three_day_walkforward_campaign136_features as feature_source


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign128.py"
TEMPLATE_SHA256 = "10a4b1da7e2f5d62f9ea785a4d918e6db3662225c2d66d0b74fcc2bf56d276dc"
ADMITTED_FACTOR = "daily_realized_price_basis_adjustment_magnitude_1d"
FROZEN_TRIAL_ID = (
    "wf136_daily_realized_price_basis_adjustment_magnitude_1d_single_higher"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(TEMPLATE_PATH) != TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign128 development-runner template changed")


_source = TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "intraday_transaction_price_dispersion_resolution_2h",
        ADMITTED_FACTOR,
    ),
    (
        "7661112a503f8930cba5fd79c03815b8c830d39f98703746362b85b37fa14cef",
        "7fe07ccabc3162e232806e542d104d4df2b8d480a79b9eee7d22cce904af1983",
    ),
    (
        "6ddc6358bffbfd6ae412744e96479b7bc6bc179ee0ae20cff9b3cb3e85b86e2f",
        "9a5c9ff824de22af6595d312b76230a3e4cf283c6e1d42e882aae96d11367b93",
    ),
    (
        "4644fdbf8ddbd046def730c9eaf848fdc56874f617ea2aefb50dedcffbc9bb4f",
        "c84b1f85eec3731736a4da411691c144a70a81e38b5013e5aeea5370f3c417ec",
    ),
    (
        'audit.get("numeric_comparisons_passed") == 139',
        'audit.get("numeric_comparisons_passed") == 140',
    ),
    ("Campaign128", "Campaign136"),
    ("campaign128", "campaign136"),
    ("campaign_128", "campaign_136"),
    ("wf128", "wf136"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign136 development transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign136_implementation",
}
exec(compile(_source, str(TEMPLATE_PATH), "exec"), _implementation)  # noqa: S102


_snapshot_verified = False


def _campaign136_load_factor_panel(
    campaign: dict[str, Any],
    years: Iterable[int],
    signal_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Adapt the immutable per-symbol daily snapshot to the inherited engine."""

    global _snapshot_verified
    factors = list(campaign.get("factor_library") or [])
    if not (
        len(factors) == 1
        and factors[0].get("name") == ADMITTED_FACTOR
        and factors[0].get("direction") == "higher"
        and Path(str(factors[0].get("partition_root"))).resolve()
        == feature_source.DEFAULT_OUTPUT_ROOT.resolve()
    ):
        raise RuntimeError("Campaign136 frozen factor adapter contract changed")
    if not _snapshot_verified:
        verification = feature_source.verify_snapshot(verify_source=True)
        if not (
            verification.get("manifest_sha256")
            == "9a5c9ff824de22af6595d312b76230a3e4cf283c6e1d42e882aae96d11367b93"
            and verification.get("dataset_sha256")
            == "c84b1f85eec3731736a4da411691c144a70a81e38b5013e5aeea5370f3c417ec"
            and verification.get("rows") == 7751950
            and verification.get("eligible_rows") == 7750120
        ):
            raise RuntimeError("Campaign136 factor snapshot verification changed")
        _snapshot_verified = True

    selected_years = sorted(set(int(year) for year in years))
    if not selected_years or min(selected_years) < 2019 or max(selected_years) > 2025:
        raise RuntimeError("Campaign136 factor adapter year range changed")
    manifest = json.loads(
        (feature_source.DEFAULT_OUTPUT_ROOT / feature_source.MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
    )
    paths = [
        str(feature_source.DEFAULT_OUTPUT_ROOT / str(item["path"]))
        for item in manifest["partitions"]
    ]
    dataset = pa_dataset.dataset(paths, format="parquet")
    start = pd.Timestamp(f"{selected_years[0]}-01-01").to_pydatetime()
    end = pd.Timestamp(f"{selected_years[-1]}-12-31").to_pydatetime()
    table = dataset.to_table(
        columns=[
            "trade_date",
            "symbol",
            ADMITTED_FACTOR,
            f"{ADMITTED_FACTOR}_eligible",
        ],
        filter=(pa_dataset.field("trade_date") >= start)
        & (pa_dataset.field("trade_date") <= end),
        use_threads=True,
    )
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"], errors="coerce"
    ).dt.normalize()
    frame["instrument"] = frame.pop("symbol").astype(str).str.upper()
    eligible = (
        frame.pop(f"{ADMITTED_FACTOR}_eligible")
        .astype("boolean")
        .fillna(False)
        .astype(bool)
    )
    values = pd.to_numeric(frame[ADMITTED_FACTOR], errors="coerce")
    values = values.where(eligible)
    finite = values.dropna().to_numpy(dtype=np.float64)
    allowed_dates = set(pd.DatetimeIndex(signal_dates).normalize())
    frame[ADMITTED_FACTOR] = values
    frame = frame.loc[frame["trade_date"].isin(allowed_dates)].copy()
    if (
        frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "instrument"]).any()
        or not np.isfinite(finite).all()
        or (finite < 0.0).any()
    ):
        raise RuntimeError("Campaign136 adapted factor panel is invalid")
    return frame[["trade_date", "instrument", ADMITTED_FACTOR]]


base = _implementation["base"]
base.load_factor_panel = _campaign136_load_factor_panel
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__", "base"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())

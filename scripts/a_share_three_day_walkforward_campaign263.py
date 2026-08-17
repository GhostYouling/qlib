#!/usr/bin/env python3
"""Run Campaign263's exact one-trial 2019-2023 historical walk-forward."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset

from scripts import a_share_three_day_walkforward_campaign263_features as feature_source


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign128.py"
TEMPLATE_SHA256 = "10a4b1da7e2f5d62f9ea785a4d918e6db3662225c2d66d0b74fcc2bf56d276dc"
ADMITTED_FACTOR = "intraday_amount_profile_spectral_entropy_60f"
FROZEN_TRIAL_ID = "wf263_intraday_amount_profile_spectral_entropy_60f_single_higher"
VERIFICATION_RECEIPT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_feature_snapshot_verification_result_20260816.json"
)
VERIFICATION_RECEIPT_SHA256 = (
    "612a394807499124a488b9cfb00c1725a0c141494354342b18e678b4ba0c1c8a"
)
CAMPAIGN263_DEVELOPMENT_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_development_activation_binding_20260816.json"
)
CAMPAIGN263_DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_preregistration_v2.json"
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
        "ba7f84b8601614af54e66d25dc27cb5fa42b4091bb4fad4126274e9dd832f380",
    ),
    (
        "6ddc6358bffbfd6ae412744e96479b7bc6bc179ee0ae20cff9b3cb3e85b86e2f",
        "fea163cfc8ec9fd2d389597ea33579b7cb1e0becd60a23be74694c7cddcefdc4",
    ),
    (
        "4644fdbf8ddbd046def730c9eaf848fdc56874f617ea2aefb50dedcffbc9bb4f",
        "e9ee03f036cedd5a98badd64533ff9605e0d2bab046392a3ccd2afcbc3a225e7",
    ),
    (
        'audit.get("numeric_comparisons_passed") == 139',
        'audit.get("numeric_comparisons_passed") == 142',
    ),
    ("Campaign128", "Campaign263"),
    ("campaign128", "campaign263"),
    ("campaign_128", "campaign_263"),
    ("wf128", "wf263"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign263 development transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign263_implementation",
}
exec(compile(_source, str(TEMPLATE_PATH), "exec"), _implementation)  # noqa: S102
_generated = _implementation
_generated["DEVELOPMENT_ACTIVATION"] = CAMPAIGN263_DEVELOPMENT_ACTIVATION
_generated["run_development"].__globals__[
    "DEVELOPMENT_ACTIVATION"
] = CAMPAIGN263_DEVELOPMENT_ACTIVATION
_generated["DEFAULT_PREREGISTRATION"] = CAMPAIGN263_DEFAULT_PREREGISTRATION
_generated["run_development"].__globals__[
    "DEFAULT_PREREGISTRATION"
] = CAMPAIGN263_DEFAULT_PREREGISTRATION


_snapshot_verified = False


def _campaign263_load_factor_panel(
    campaign: dict[str, Any],
    years: Iterable[int],
    signal_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Adapt the immutable per-symbol-year Campaign263 snapshot to the engine."""

    global _snapshot_verified
    factors = list(campaign.get("factor_library") or [])
    expected_root = feature_source.output_root(feature_source.DEFAULT_DATA_ROOT)
    if not (
        len(factors) == 1
        and factors[0].get("name") == ADMITTED_FACTOR
        and factors[0].get("direction") == "higher"
        and Path(str(factors[0].get("partition_root"))).resolve()
        == expected_root.resolve()
    ):
        raise RuntimeError("Campaign263 frozen factor adapter contract changed")
    if not _snapshot_verified:
        if (
            not VERIFICATION_RECEIPT.is_file()
            or _sha256(VERIFICATION_RECEIPT) != VERIFICATION_RECEIPT_SHA256
        ):
            raise RuntimeError("Campaign263 snapshot verification receipt changed")
        receipt = json.loads(VERIFICATION_RECEIPT.read_text(encoding="utf-8"))
        manifest_path = expected_root / "snapshot_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not (
            receipt.get("status") == "all_partitions_byte_frame_and_aggregate_verified"
            and receipt.get("manifest_sha256")
            == "fea163cfc8ec9fd2d389597ea33579b7cb1e0becd60a23be74694c7cddcefdc4"
            and receipt.get("dataset_sha256")
            == "e9ee03f036cedd5a98badd64533ff9605e0d2bab046392a3ccd2afcbc3a225e7"
            and receipt.get("partitions") == 33_015
            and receipt.get("rows") == 7_724_498
            and receipt.get("eligible_rows") == 7_724_491
            and receipt.get("verification_exit_code") == 0
            and receipt.get("comparison_values_read") is False
            and receipt.get("historical_daily_price_or_forward_return_values_read")
            is False
            and receipt.get("provider_request_issued") is False
            and len(manifest.get("files") or []) == 33_015
        ):
            raise RuntimeError("Campaign263 snapshot verification semantics changed")
        _snapshot_verified = True

    selected_years = sorted(set(int(year) for year in years))
    if not selected_years or min(selected_years) < 2019 or max(selected_years) > 2025:
        raise RuntimeError("Campaign263 factor adapter year range changed")
    manifest = json.loads(
        (expected_root / "snapshot_manifest.json").read_text(encoding="utf-8")
    )
    paths = [str(Path(str(item["path"])).resolve()) for item in manifest["files"]]
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
    values = pd.to_numeric(frame[ADMITTED_FACTOR], errors="coerce").where(eligible)
    finite = values.dropna().to_numpy(dtype=np.float64)
    allowed_dates = set(pd.DatetimeIndex(signal_dates).normalize())
    frame[ADMITTED_FACTOR] = values
    frame = frame.loc[frame["trade_date"].isin(allowed_dates)].copy()
    if (
        frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "instrument"]).any()
        or not np.isfinite(finite).all()
        or (finite < 0.0).any()
        or (finite > 1.0).any()
    ):
        raise RuntimeError("Campaign263 adapted factor panel is invalid")
    return frame[["trade_date", "instrument", ADMITTED_FACTOR]]


base = _generated["base"]
base.load_factor_panel = _campaign263_load_factor_panel
for _name, _value in _generated.items():
    if _name not in {
        "__builtins__",
        "__file__",
        "__name__",
        "_implementation",
        "base",
    }:
        globals()[_name] = _value
DEVELOPMENT_ACTIVATION = CAMPAIGN263_DEVELOPMENT_ACTIVATION


if __name__ == "__main__":
    raise SystemExit(_generated["main"]())

#!/usr/bin/env python3
"""Run Campaign146's exact one-trial 2019-2023 historical walk-forward."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset

from scripts import a_share_three_day_walkforward_campaign146_features as feature_source
from scripts import (
    a_share_three_day_walkforward_campaign146_snapshot_verify_recovery as recovery,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign128.py"
TEMPLATE_SHA256 = "10a4b1da7e2f5d62f9ea785a4d918e6db3662225c2d66d0b74fcc2bf56d276dc"
ADMITTED_FACTOR = "intraday_return_amount_cross_spectral_phase_lead_59f"
FROZEN_TRIAL_ID = (
    "wf146_intraday_return_amount_cross_spectral_phase_lead_59f_single_higher"
)
RECOVERY_RECEIPT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_snapshot_recovery_verification_20260814.json"
)
RECOVERY_RECEIPT_SHA256 = (
    "0098f33fb5759aafcfd39a97be086e849caa179e5d825f5d06d90bc0481dc44b"
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
        "22a81e2be318669f3a673f7deb4228e06fe8f87da55d069d9cd9dcfc97216d6b",
    ),
    (
        "6ddc6358bffbfd6ae412744e96479b7bc6bc179ee0ae20cff9b3cb3e85b86e2f",
        "951872dbdcfa2b00e9603d3be44b059c7d24204fba5757551afbcd46ee8a3f74",
    ),
    (
        "4644fdbf8ddbd046def730c9eaf848fdc56874f617ea2aefb50dedcffbc9bb4f",
        "7278ae76407215eab75e9ff0119d8c6a073e4d7ac9df5b7d349bc09e6cf889c4",
    ),
    (
        'audit.get("numeric_comparisons_passed") == 139',
        'audit.get("numeric_comparisons_passed") == 141',
    ),
    ("Campaign128", "Campaign146"),
    ("campaign128", "campaign146"),
    ("campaign_128", "campaign_146"),
    ("wf128", "wf146"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign146 development transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign146_implementation",
}
exec(compile(_source, str(TEMPLATE_PATH), "exec"), _implementation)  # noqa: S102


_snapshot_verified = False


def _campaign146_load_factor_panel(
    campaign: dict[str, Any],
    years: Iterable[int],
    signal_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Adapt the immutable per-symbol-year minute snapshot to the engine."""

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
        raise RuntimeError("Campaign146 frozen factor adapter contract changed")
    if not _snapshot_verified:
        recovery.require_file(
            RECOVERY_RECEIPT, RECOVERY_RECEIPT_SHA256, "recovery receipt"
        )
        manifest = recovery.load_and_validate_manifest_metadata()
        receipt = json.loads(RECOVERY_RECEIPT.read_text(encoding="utf-8"))
        snapshot = receipt.get("snapshot_manifest") or {}
        verification = receipt.get("verification") or {}
        if not (
            snapshot.get("sha256") == recovery.SNAPSHOT_MANIFEST_SHA256
            and snapshot.get("dataset_sha256") == recovery.SNAPSHOT_DATASET_SHA256
            and snapshot.get("rows") == recovery.EXPECTED_ROWS
            and snapshot.get("eligible_rows") == recovery.EXPECTED_ELIGIBLE_ROWS
            and len(manifest.get("files") or []) == recovery.EXPECTED_PARTITIONS
            and verification.get("exit_code") == 0
            and verification.get("all_partition_byte_sha256_verified") is True
            and verification.get("all_partition_frame_sha256_verified") is True
        ):
            raise RuntimeError("Campaign146 factor snapshot verification changed")
        _snapshot_verified = True

    selected_years = sorted(set(int(year) for year in years))
    if not selected_years or min(selected_years) < 2019 or max(selected_years) > 2025:
        raise RuntimeError("Campaign146 factor adapter year range changed")
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
        or (finite < -1.0).any()
        or (finite > 1.0).any()
    ):
        raise RuntimeError("Campaign146 adapted factor panel is invalid")
    return frame[["trade_date", "instrument", ADMITTED_FACTOR]]


base = _implementation["base"]
base.load_factor_panel = _campaign146_load_factor_panel
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__", "base"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())

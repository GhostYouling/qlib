#!/usr/bin/env python3
"""Authorized isolated Campaign054 candidate-frame loader repair."""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset

try:
    import scripts.a_share_three_day_walkforward_campaign054_features_v6 as failed
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign054_features_v6 as failed


audited = failed.audited
runner = failed.runner
REPAIR_AUTHORIZATION = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_054_no_return_audit_candidate_loader_failure_repair_20260803.json"
)
EXPECTED_FAILED_ENTRYPOINT_SHA256 = (
    "3b28ba76d31c81860f9948fd5acf3b744fb3767975458743bb29513982174387"
)
EXPECTED_REPAIR_AUTHORIZATION_SHA256 = (
    "52b9de36ae5d8c547afc0811d8e18162c5d1eb6862e30f68cfed69a628f2b0d9"
)
EXPECTED_PARTITIONS = 33015
EXPECTED_ROWS = 7724498

if (
    runner._sha256(Path(failed.__file__).resolve())
    != EXPECTED_FAILED_ENTRYPOINT_SHA256
):
    raise runner.Campaign054FeatureError(
        "Campaign054 failed v6 audit entrypoint changed"
    )
runner._require_file(
    REPAIR_AUTHORIZATION,
    EXPECTED_REPAIR_AUTHORIZATION_SHA256,
    "Campaign054 candidate-loader repair authorization",
)


def load_candidate_frame(
    manifest_path: Path, manifest: dict[str, Any]
) -> pd.DataFrame:
    """Load Campaign054 explicitly without shared generic range globals."""

    manifest_path = manifest_path.expanduser().resolve()
    records = list(manifest.get("files") or [])
    if (
        manifest_path
        != runner.output_root(runner.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
        or len(records) != EXPECTED_PARTITIONS
        or manifest.get("partitions") != EXPECTED_PARTITIONS
        or manifest.get("rows") != EXPECTED_ROWS
    ):
        raise runner.Campaign054FeatureError(
            "Campaign054 candidate-loader manifest identity changed"
        )
    root = (manifest_path.parent / "partitions").resolve()
    paths: list[str] = []
    for record in records:
        path = Path(str(record.get("path"))).expanduser().resolve()
        if path.parent.parent != root:
            raise runner.Campaign054FeatureError(
                f"Campaign054 candidate partition escapes root: {path}"
            )
        paths.append(str(path))
    factor = runner.FACTOR_NAME
    columns = ["trade_date", "symbol", factor, f"{factor}_eligible"]
    dataset = pa_dataset.dataset(paths, format="parquet")
    table = dataset.to_table(columns=columns, use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(frame) != EXPECTED_ROWS:
        raise runner.Campaign054FeatureError(
            "Campaign054 candidate-loader row count changed"
        )
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"], errors="coerce"
    ).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame[f"{factor}_eligible"] = (
        frame[f"{factor}_eligible"]
        .astype("boolean")
        .fillna(False)
        .astype(bool)
    )
    frame[factor] = pd.to_numeric(frame[factor], errors="coerce")
    eligible = frame[f"{factor}_eligible"]
    values = frame.loc[eligible, factor].to_numpy(dtype=float)
    if (
        frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "symbol"]).any()
        or not np.isfinite(values).all()
        or (values < runner.LOWER_BOUND).any()
        or (values > runner.UPPER_BOUND).any()
        or frame.loc[~eligible, factor].notna().any()
        or int(eligible.sum()) != 7675743
    ):
        raise runner.Campaign054FeatureError(
            "Campaign054 candidate-loader values or keys are invalid"
        )
    frame["symbol"] = frame["symbol"].astype("category")
    return frame


audited._load_candidate_frame = load_candidate_frame
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(audited.main())

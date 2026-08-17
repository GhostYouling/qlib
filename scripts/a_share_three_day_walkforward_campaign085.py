#!/usr/bin/env python3
"""Run Campaign085's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign083.py"
BASE_RUNNER_SHA256 = "0a527a67fb4674eefec816f13442f07fa740f90c08a91a33d97db79fd5727640"
BASE_FACTOR = "intraday_close_frontier_innovation_share_238p"
ADMITTED_FACTOR = (
    "quarterly_freshness_market_neutral_late_drift_confirmation_product_2r"
)
FROZEN_TRIAL_ID = "wf085_quarterly_freshness_market_neutral_late_drift_confirmation_product_2r_single_higher"
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_085_preregistration_v2.json"
)
CANDIDATE_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign085_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign085_feature_library_v1/"
    "snapshot_manifest.json"
)
CANDIDATE_MANIFEST_SHA256 = (
    "fb8ea4bdb2b2f783a8c1d4e020f1dcdfca1697c779c732e50233fe7b040b4d28"
)
CANDIDATE_DATASET_SHA256 = (
    "368f7cb96c15186cd511ccd4120e89b577141aa9687df8b39f9dd17320db8fb9"
)
EXPECTED_ROWS = 1_331_759
EXPECTED_ELIGIBLE_ROWS = 1_328_065


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign083 development runner changed")

_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign083", "Campaign085"),
    ("campaign083", "campaign085"),
    ("campaign_083", "campaign_085"),
    ("wf083", "wf085"),
    (BASE_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign085_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

engine_namespace: dict[str, Any] = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION
base = _generated["base"]
Campaign085Error = _generated["Campaign085Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
status = _generated["status"]
_inherited_run_development = _generated["run_development"]
_inherited_run_exposed_stress = _generated["run_exposed_stress"]
_inherited_main = _generated["main"]


def _decode_stock_day_keys(keys: np.ndarray) -> tuple[pd.DatetimeIndex, pd.Series]:
    compact = np.asarray(keys, dtype=np.int64)
    if compact.ndim != 1 or len(compact) == 0:
        raise Campaign085Error("Campaign085 compact stock-day keys changed")
    day_numbers = compact // 4_000_000
    security_numbers = compact % 4_000_000
    exchanges = security_numbers // 1_000_000
    codes = security_numbers % 1_000_000
    if not np.isin(exchanges, np.array([1, 2, 3], dtype=np.int64)).all():
        raise Campaign085Error("Campaign085 compact exchange code changed")
    dates = pd.to_datetime(day_numbers, unit="D", origin="unix").normalize()
    prefixes = pd.Series(exchanges).map({1: "SH", 2: "SZ", 3: "BJ"})
    instruments = prefixes + pd.Series(codes).astype("string").str.zfill(6)
    if dates.isna().any() or instruments.isna().any():
        raise Campaign085Error("Campaign085 compact identity decode failed")
    return pd.DatetimeIndex(dates), instruments


def _load_compact_factor_panel(
    campaign: dict[str, Any],
    years: Any,
    signal_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    factors = list(campaign.get("factor_library") or [])
    requested_years = sorted({int(year) for year in years})
    if not (
        len(factors) == 1
        and factors[0].get("name") == ADMITTED_FACTOR
        and factors[0].get("dataset_group") == "campaign085_new_factors"
        and Path(str(factors[0].get("partition_root") or "")).resolve()
        == CANDIDATE_MANIFEST.parent / "partitions"
        and requested_years
        and set(requested_years).issubset(set(range(2019, 2026)))
    ):
        raise Campaign085Error("Campaign085 compact factor request changed")
    if not CANDIDATE_MANIFEST.is_file() or _sha256(CANDIDATE_MANIFEST) != (
        CANDIDATE_MANIFEST_SHA256
    ):
        raise Campaign085Error("Campaign085 candidate manifest changed")
    manifest = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
    records = {int(item["year"]): item for item in manifest.get("files") or []}
    if not (
        manifest.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and manifest.get("rows") == EXPECTED_ROWS
        and (manifest.get("factor_eligible_rows") or {}).get(ADMITTED_FACTOR)
        == EXPECTED_ELIGIBLE_ROWS
        and set(records) == set(range(2019, 2026))
    ):
        raise Campaign085Error("Campaign085 candidate snapshot semantics changed")
    frames: list[pd.DataFrame] = []
    for year in requested_years:
        record = records[year]
        path = (CANDIDATE_MANIFEST.parent / str(record["path"])).resolve()
        if not path.is_file() or _sha256(path) != str(record["sha256"]):
            raise Campaign085Error(f"Campaign085 candidate partition changed: {year}")
        source = pd.read_parquet(path, columns=["stock_day_key", ADMITTED_FACTOR])
        keys = source["stock_day_key"].to_numpy(dtype=np.int64)
        dates, instruments = _decode_stock_day_keys(keys)
        if not (dates.year == year).all():
            raise Campaign085Error(
                f"Campaign085 candidate partition year changed: {year}"
            )
        frames.append(
            pd.DataFrame(
                {
                    "trade_date": dates,
                    "instrument": instruments.to_numpy(dtype=str),
                    ADMITTED_FACTOR: pd.to_numeric(
                        source[ADMITTED_FACTOR], errors="coerce"
                    ).to_numpy(dtype=np.float64),
                }
            )
        )
    panel = pd.concat(frames, ignore_index=True)
    if panel.duplicated(["trade_date", "instrument"]).any():
        raise Campaign085Error("Campaign085 decoded factor keys are not unique")
    dates = set(pd.DatetimeIndex(signal_dates).normalize())
    return panel.loc[panel["trade_date"].isin(dates)].reset_index(drop=True)


@contextmanager
def _temporary_compact_factor_loader() -> Iterator[None]:
    original = base.load_factor_panel
    if original is _load_compact_factor_panel:
        raise Campaign085Error("Campaign085 compact factor loader was prepatched")
    base.load_factor_panel = _load_compact_factor_panel
    try:
        yield
    finally:
        base.load_factor_panel = original


def run_development(args: Any) -> dict[str, Any]:
    with _temporary_compact_factor_loader():
        return _inherited_run_development(args)


def run_exposed_stress(args: Any) -> dict[str, Any]:
    with _temporary_compact_factor_loader():
        return _inherited_run_exposed_stress(args)


engine_namespace["run_development"] = run_development
engine_namespace["run_exposed_stress"] = run_exposed_stress


def main() -> int:
    return _inherited_main()


if __name__ == "__main__":
    raise SystemExit(main())

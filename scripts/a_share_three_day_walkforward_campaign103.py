#!/usr/bin/env python3
"""Run Campaign103's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign101.py"
BASE_RUNNER_SHA256 = "8353c819b0c1a0edd98eb0999849a626d5a97c913655e2068ec18fb05b9c9b27"
BASE_FACTOR = "full_numeric_library_directional_lower_quartile_consensus_129f"
ADMITTED_FACTOR = "full_numeric_library_directional_rank_improvement_breadth_130f"
CANDIDATE_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign103_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign103_feature_library_v1/snapshot_manifest.json"
)
CANDIDATE_MANIFEST_SHA256 = "8a939feb53edfb31be8f133c2683920ed13424e716a4f4b5ed0d1a300588603b"
CANDIDATE_DATASET_SHA256 = "57afdd9f8a246fb9f513f85b3b631f70cf734655bd226ff211201bf7e084ea13"
EXPECTED_CAMPAIGN103_ELIGIBLE_ROWS = 1_315_573


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign101 development runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign101", "Campaign103"),
    ("campaign101", "campaign103"),
    ("campaign_101", "campaign_103"),
    ("wf101", "wf103"),
    (BASE_FACTOR, ADMITTED_FACTOR),
    (
        "7a2db929fff69f46edbc93d57cdca9cc4427c47dd542291b4f58d879dd91a3b6",
        CANDIDATE_MANIFEST_SHA256,
    ),
    (
        "ed024ab2736b9766e1adb122b155189029f30a5d14e11d4d67a403ff9befef24",
        CANDIDATE_DATASET_SHA256,
    ),
    (
        "minute_walkforward_campaign103_feature_library",
        "minute_walkforward_campaign103_feature_library",
    ),
    (
        "walkforward_campaign103_feature_library_v1",
        "walkforward_campaign103_feature_library_v1",
    ),
    ("1_327_637", "1_315_573"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign103_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

CAMPAIGN103_PREREGISTRATION_V2 = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_103_preregistration_v11.json"
)
_generated["CANDIDATE_MANIFEST"] = CANDIDATE_MANIFEST
_generated["CANDIDATE_MANIFEST_SHA256"] = CANDIDATE_MANIFEST_SHA256
_generated["CANDIDATE_DATASET_SHA256"] = CANDIDATE_DATASET_SHA256
_generated["EXPECTED_ELIGIBLE_ROWS"] = EXPECTED_CAMPAIGN103_ELIGIBLE_ROWS
_generated["DEFAULT_PREREGISTRATION"] = CAMPAIGN103_PREREGISTRATION_V2
_cursor: dict[str, Any] | None = _generated
_engine_binding_ids: set[int] = set()
while isinstance(_cursor, dict):
    if "DEFAULT_PREREGISTRATION" in _cursor:
        _cursor["DEFAULT_PREREGISTRATION"] = CAMPAIGN103_PREREGISTRATION_V2
    _engine = _cursor.get("engine_namespace")
    if isinstance(_engine, dict):
        _engine["DEFAULT_CAMPAIGN"] = CAMPAIGN103_PREREGISTRATION_V2
        _engine_binding_ids.add(id(_engine))
    _next = _cursor.get("_generated")
    _cursor = _next if isinstance(_next, dict) and _next is not _cursor else None
if len(_engine_binding_ids) != 1:
    raise RuntimeError("Campaign103 inherited engine namespace changed")


def _load_campaign103_factor_panel(
    campaign: dict[str, Any],
    years: Any,
    signal_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    factors = list(campaign.get("factor_library") or [])
    requested_years = sorted({int(year) for year in years})
    if not (
        len(factors) == 1
        and factors[0].get("name") == ADMITTED_FACTOR
        and factors[0].get("dataset_group") == "campaign103_new_factors"
        and Path(str(factors[0].get("partition_root") or "")).resolve()
        == CANDIDATE_MANIFEST.parent / "partitions"
        and requested_years
        and set(requested_years).issubset(set(range(2019, 2026)))
    ):
        raise RuntimeError("Campaign103 compact factor request changed")
    if not CANDIDATE_MANIFEST.is_file() or _sha256(CANDIDATE_MANIFEST) != (
        CANDIDATE_MANIFEST_SHA256
    ):
        raise RuntimeError("Campaign103 candidate manifest changed")
    manifest = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
    records = {int(item["year"]): item for item in manifest.get("files") or []}
    if not (
        manifest.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and manifest.get("rows") == _generated["EXPECTED_ROWS"]
        and manifest.get("eligible_rows") == EXPECTED_CAMPAIGN103_ELIGIBLE_ROWS
        and manifest.get("factor") == ADMITTED_FACTOR
        and set(records) == set(range(2019, 2026))
    ):
        raise RuntimeError("Campaign103 candidate snapshot semantics changed")
    frames: list[pd.DataFrame] = []
    decoder = _generated["_decode_stock_day_keys"]
    for year in requested_years:
        record = records[year]
        path = (CANDIDATE_MANIFEST.parent / str(record["path"])).resolve()
        if not path.is_file() or _sha256(path) != str(record["sha256"]):
            raise RuntimeError(f"Campaign103 candidate partition changed: {year}")
        source = pd.read_parquet(path, columns=["stock_day_key", ADMITTED_FACTOR])
        keys = source["stock_day_key"].to_numpy(dtype=np.int64)
        dates, instruments = decoder(keys)
        if not (dates.year == year).all():
            raise RuntimeError(f"Campaign103 candidate partition year changed: {year}")
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
        raise RuntimeError("Campaign103 decoded factor keys are not unique")
    dates = set(pd.DatetimeIndex(signal_dates).normalize())
    return panel.loc[panel["trade_date"].isin(dates)].reset_index(drop=True)


_generated["_load_compact_factor_panel"] = _load_campaign103_factor_panel
_loader_context = _generated["_temporary_compact_factor_loader"]
_loader_generator = getattr(_loader_context, "__wrapped__", None)
if not callable(_loader_generator):
    raise RuntimeError("Campaign103 compact loader context generator changed")
_loader_generator.__globals__["_load_compact_factor_panel"] = (
    _load_campaign103_factor_panel
)
if _loader_generator.__globals__.get("_load_compact_factor_panel") is not (
    _load_campaign103_factor_panel
):
    raise RuntimeError("Campaign103 compact loader generator binding changed")

LEDGER_PREDECESSOR_PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_103_preregistration_v8.json"
)
LEDGER_PREDECESSOR_PREREGISTRATION_SHA256 = (
    "9485fd9e7773c6d489ead653ae66536445079425c7135dc7f4849d5733f66bbe"
)
_engine_namespace = _generated["status"].__globals__
_inherited_validate_ledger = _engine_namespace["_validate_ledger"]


def _validate_campaign103_ledger(
    ledger: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
) -> dict[str, Any]:
    """Preserve the exact v8 ledger header across the additive v10 repair."""
    resolved_campaign_path = Path(campaign_path).resolve()
    header = ledger.get("campaign") or {}
    predecessor_header = {
        "path": str(LEDGER_PREDECESSOR_PREREGISTRATION.resolve()),
        "sha256": LEDGER_PREDECESSOR_PREREGISTRATION_SHA256,
        "campaign_id": "a_share_three_day_walkforward_campaign_103",
    }
    if (
        resolved_campaign_path == CAMPAIGN103_PREREGISTRATION_V2.resolve()
        and CAMPAIGN103_PREREGISTRATION_V2.is_file()
        and campaign_sha == _sha256(CAMPAIGN103_PREREGISTRATION_V2)
        and header == predecessor_header
    ):
        if (
            not LEDGER_PREDECESSOR_PREREGISTRATION.is_file()
            or _sha256(LEDGER_PREDECESSOR_PREREGISTRATION)
            != LEDGER_PREDECESSOR_PREREGISTRATION_SHA256
        ):
            raise RuntimeError("Campaign103 predecessor preregistration changed")
        return _inherited_validate_ledger(
            ledger,
            LEDGER_PREDECESSOR_PREREGISTRATION.resolve(),
            LEDGER_PREDECESSOR_PREREGISTRATION_SHA256,
        )
    return _inherited_validate_ledger(
        ledger,
        resolved_campaign_path,
        campaign_sha,
    )


_engine_namespace["_validate_ledger"] = _validate_campaign103_ledger
if _generated["status"].__globals__.get("_validate_ledger") is not (
    _validate_campaign103_ledger
):
    raise RuntimeError("Campaign103 ledger validator binding changed")

DEVELOPMENT_IMPLEMENTATION_FREEZE_V2 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_103_development_implementation_freeze_v4_20260808.json"
)
DEVELOPMENT_ACTIVATION_BINDING_V2 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_103_development_activation_binding_v4_20260808.json"
)
_activation_loader = _generated["_load_development_activation"]
_activation_loader.__globals__["DEVELOPMENT_IMPLEMENTATION_FREEZE"] = (
    DEVELOPMENT_IMPLEMENTATION_FREEZE_V2
)
_activation_loader.__globals__["DEVELOPMENT_ACTIVATION_BINDING"] = (
    DEVELOPMENT_ACTIVATION_BINDING_V2
)
_generated["DEVELOPMENT_IMPLEMENTATION_FREEZE"] = (
    DEVELOPMENT_IMPLEMENTATION_FREEZE_V2
)
_generated["DEVELOPMENT_ACTIVATION_BINDING"] = DEVELOPMENT_ACTIVATION_BINDING_V2

DEFAULT_PREREGISTRATION = _generated["DEFAULT_PREREGISTRATION"]
DEVELOPMENT_IMPLEMENTATION_FREEZE = DEVELOPMENT_IMPLEMENTATION_FREEZE_V2
DEVELOPMENT_ACTIVATION_BINDING = DEVELOPMENT_ACTIVATION_BINDING_V2
TEST_PATH = _generated["TEST_PATH"]
base = _generated["base"]
Campaign103Error = _generated["Campaign103Error"]
FROZEN_TRIAL_ID = _generated["FROZEN_TRIAL_ID"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_ELIGIBLE_ROWS = _generated["EXPECTED_ELIGIBLE_ROWS"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
status = _generated["status"]
_decode_stock_day_keys = _generated["_decode_stock_day_keys"]
_load_compact_factor_panel = _load_campaign103_factor_panel
_temporary_compact_factor_loader = _generated["_temporary_compact_factor_loader"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
_load_development_activation = _generated["_load_development_activation"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run Campaign097 with the additive compact-loader namespace repair."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign097 as v1


REPO_ROOT = Path(__file__).resolve().parents[1]
V1_RUNNER_SHA256 = "e48bc07f5c004558a98cae9e3f12a18b3c79bc62ffb0bae654109bbc78d45e40"
V1_DEVELOPMENT_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_development_implementation_freeze_20260807.json"
)
V1_DEVELOPMENT_FREEZE_SHA256 = (
    "b987ee75c8773b0067a59655cc2177f12ff9d598b25bbf801eb155300a7ad0d8"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_development_compact_namespace_failure_20260807.json"
)
FAILURE_RECORD_SHA256 = (
    "9637fbca52c4b3e8125cce799b2c105cdf2e3833cfbbbe7977afd364b3e1215c"
)
TEST_FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_development_v1_prevalue_status_test_failure_20260807.json"
)
TEST_FAILURE_RECORD_SHA256 = (
    "b6a8e8dbdb1e01a45dad85f1a4b6fbdcf38a520ad9a4a9e157e98456e452aece"
)
FAILED_LEDGER_SHA256 = (
    "1c93bf410fd1f384313552d804275325aef9579bc8c5b8cf5edb49deab0cf7f6"
)
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_development_implementation_freeze_v2_20260807.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_development_activation_binding_v2_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign097_development_v2.py"
)
COMPACT_MANIFEST = v1.COMPACT_MANIFEST
COMPACT_MANIFEST_SHA256 = v1.COMPACT_MANIFEST_SHA256
COMPACT_DATASET_SHA256 = v1.COMPACT_DATASET_SHA256


class Campaign097DevelopmentV2Error(RuntimeError):
    """Fail-closed Campaign097 development v2 error."""


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign097DevelopmentV2Error(
            f"Campaign097 development v2 {label} changed: {path}"
        )


def _load_implementation_freeze() -> dict[str, Any]:
    _require(Path(v1.__file__).resolve(), V1_RUNNER_SHA256, "v1 runner")
    _require(
        V1_DEVELOPMENT_FREEZE,
        V1_DEVELOPMENT_FREEZE_SHA256,
        "v1 development freeze",
    )
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "v1 failure record")
    _require(
        TEST_FAILURE_RECORD,
        TEST_FAILURE_RECORD_SHA256,
        "v1 status test failure record",
    )
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign097DevelopmentV2Error("v2 implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_development_implementation_freeze_v2"
        and record.get("status")
        == "compact_namespace_repair_frozen_after_one_append_only_failure_before_complete_development_trial"
        and (record.get("v2_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v2_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("v1_failure_record") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and (record.get("v1_status_test_failure") or {}).get("sha256")
        == TEST_FAILURE_RECORD_SHA256
        and record.get("repair_scope")
        == "replace only the inherited compact loader dataset_group and manifest namespace"
        and record.get("complete_development_trial_count_before_v2_freeze") == 0
        and record.get("stress_2024_2025_read_before_v2_freeze") is False
        and record.get("provider_request_issued_before_v2_freeze") is False
    ):
        raise Campaign097DevelopmentV2Error("v2 implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign097DevelopmentV2Error("v2 activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    ledger = REPO_ROOT / str(
        (record.get("append_only_internal_ledger") or {}).get("path")
    )
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_development_activation_binding_v2"
        and record.get("status")
        == "compact_namespace_repair_frozen_after_one_append_only_failure_before_complete_development_trial"
        and (record.get("implementation_freeze_v2") or {}).get("sha256")
        == _sha256(AUDIT_IMPLEMENTATION_FREEZE)
        and (record.get("v1_failure_record") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and ledger.is_file()
        and _sha256(ledger) == FAILED_LEDGER_SHA256
        and record.get("remaining_complete_development_trials_authorized") == 1
        and record.get("stress_2024_2025_authorized") is False
    ):
        raise Campaign097DevelopmentV2Error("v2 activation binding changed")
    return record


def _load_compact_factor_panel(
    campaign: dict[str, Any],
    years: Any,
    signal_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    factors = list(campaign.get("factor_library") or [])
    requested_years = sorted({int(year) for year in years})
    if not (
        len(factors) == 1
        and factors[0].get("name") == v1.ADMITTED_FACTOR
        and factors[0].get("dataset_group") == "campaign097_new_factors"
        and Path(str(factors[0].get("partition_root") or "")).resolve()
        == COMPACT_MANIFEST.parent / "partitions"
        and requested_years
        and set(requested_years).issubset(set(range(2019, 2026)))
    ):
        raise Campaign097DevelopmentV2Error(
            "Campaign097 compact factor request changed"
        )
    _require(COMPACT_MANIFEST, COMPACT_MANIFEST_SHA256, "compact manifest")
    manifest = json.loads(COMPACT_MANIFEST.read_text(encoding="utf-8"))
    records = {int(item["year"]): item for item in manifest.get("files") or []}
    if not (
        manifest.get("dataset_sha256") == COMPACT_DATASET_SHA256
        and manifest.get("rows") == v1.EXPECTED_ROWS
        and (manifest.get("factor_eligible_rows") or {}).get(v1.ADMITTED_FACTOR)
        == v1.EXPECTED_ELIGIBLE_ROWS
        and set(records) == set(range(2019, 2026))
    ):
        raise Campaign097DevelopmentV2Error("compact snapshot semantics changed")
    frames: list[pd.DataFrame] = []
    for year in requested_years:
        record = records[year]
        path = (COMPACT_MANIFEST.parent / str(record["path"])).resolve()
        _require(path, str(record["sha256"]), f"compact partition {year}")
        source = pd.read_parquet(path, columns=["stock_day_key", v1.ADMITTED_FACTOR])
        keys = source["stock_day_key"].to_numpy(dtype=np.int64)
        dates, instruments = v1._decode_stock_day_keys(keys)
        if not (dates.year == year).all():
            raise Campaign097DevelopmentV2Error(
                f"compact partition year changed: {year}"
            )
        frames.append(
            pd.DataFrame(
                {
                    "trade_date": dates,
                    "instrument": instruments.to_numpy(dtype=str),
                    v1.ADMITTED_FACTOR: pd.to_numeric(
                        source[v1.ADMITTED_FACTOR], errors="coerce"
                    ).to_numpy(dtype=np.float64),
                }
            )
        )
    panel = pd.concat(frames, ignore_index=True)
    if panel.duplicated(["trade_date", "instrument"]).any():
        raise Campaign097DevelopmentV2Error("decoded factor keys are not unique")
    dates = set(pd.DatetimeIndex(signal_dates).normalize())
    return panel.loc[panel["trade_date"].isin(dates)].reset_index(drop=True)


@contextmanager
def _temporary_repaired_compact_loader() -> Iterator[None]:
    namespace = v1._generated
    original = namespace["_load_compact_factor_panel"]
    namespace["_load_compact_factor_panel"] = _load_compact_factor_panel
    try:
        yield
    finally:
        namespace["_load_compact_factor_panel"] = original


def main() -> int:
    _load_activation_binding()
    with _temporary_repaired_compact_loader():
        return v1.main()


if __name__ == "__main__":
    raise SystemExit(main())

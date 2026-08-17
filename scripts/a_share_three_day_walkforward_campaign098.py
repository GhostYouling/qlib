#!/usr/bin/env python3
"""Run Campaign098's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign089.py"
BASE_RUNNER_SHA256 = "591d89e0d50b88b5664c521ec6473b8acc05b29f700c2e3c8678d4e6535ef6b8"
BASE_FACTOR = "intraday_directional_amount_timing_spread_238m"
ADMITTED_FACTOR = "intraday_range_clock_variance_240m"
COMPACT_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign098_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign098_feature_library_v1/snapshot_manifest.json"
)
COMPACT_MANIFEST_SHA256 = (
    "371429a81292a91ef2bfa1292f467c81bf73e176fbfbc9888084f74eaaac1dc5"
)
COMPACT_DATASET_SHA256 = (
    "921f06fad98aed942550d86b1475c888aea6d2025c37d53ec55917401bd34b33"
)
DEFAULT_PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_098_preregistration.json"
)
DEVELOPMENT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_098_development_implementation_freeze_20260807.json"
)
DEVELOPMENT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_098_development_activation_binding_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign098_development.py"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign089 development runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign089", "Campaign098"),
    ("campaign089", "campaign098"),
    ("campaign_089", "campaign_098"),
    ("wf089", "wf098"),
    (BASE_FACTOR, ADMITTED_FACTOR),
    (
        "3ab55cc6f61bebb6713aeacb9e54125c20183295b862717617be0b13c9d0a204",
        COMPACT_MANIFEST_SHA256,
    ),
    (
        "c4f8794f42f1fffe2847ade875232827c8ca532a7fd75dd1123686c41456655a",
        COMPACT_DATASET_SHA256,
    ),
    ("EXPECTED_ELIGIBLE_ROWS = 1_327_577", "EXPECTED_ELIGIBLE_ROWS = 1_328_449"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign098_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

_generated["DEFAULT_PREREGISTRATION"] = DEFAULT_PREREGISTRATION
engine_namespace: dict[str, Any] = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION
base = _generated["base"]
Campaign098Error = _generated["Campaign098Error"]
FROZEN_TRIAL_ID = _generated["FROZEN_TRIAL_ID"]
CANDIDATE_MANIFEST = _generated["CANDIDATE_MANIFEST"]
CANDIDATE_MANIFEST_SHA256 = _generated["CANDIDATE_MANIFEST_SHA256"]
CANDIDATE_DATASET_SHA256 = _generated["CANDIDATE_DATASET_SHA256"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_ELIGIBLE_ROWS = _generated["EXPECTED_ELIGIBLE_ROWS"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
status = _generated["status"]
_decode_stock_day_keys = _generated["_decode_stock_day_keys"]
_load_compact_factor_panel = _generated["_load_compact_factor_panel"]
_temporary_compact_factor_loader = _generated["_temporary_compact_factor_loader"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
_inherited_main = _generated["main"]


def _load_development_activation() -> dict[str, Any]:
    if not DEVELOPMENT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign098Error(
            "Campaign098 development implementation freeze is absent"
        )
    freeze = json.loads(DEVELOPMENT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign098_development_implementation_freeze"
        and freeze.get("status")
        == "frozen_before_campaign098_development_daily_price_or_forward_return_read"
        and (freeze.get("runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (freeze.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and freeze.get("complete_development_trial_count_before_freeze") == 0
        and freeze.get("stress_2024_2025_read_before_freeze") is False
        and freeze.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign098Error("Campaign098 development implementation freeze changed")

    if not DEVELOPMENT_ACTIVATION_BINDING.is_file():
        raise Campaign098Error("Campaign098 development activation binding is absent")
    activation = json.loads(DEVELOPMENT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    preregistration = REPO_ROOT / str(
        (activation.get("development_preregistration") or {}).get("path")
    )
    ledger = REPO_ROOT / str(
        (activation.get("append_only_internal_ledger") or {}).get("path")
    )
    if not (
        activation.get("kind")
        == "a_share_three_day_walkforward_campaign098_development_activation_binding"
        and activation.get("status")
        == "one_frozen_development_trial_authorized_before_return_read"
        and (activation.get("implementation_freeze") or {}).get("sha256")
        == _sha256(DEVELOPMENT_IMPLEMENTATION_FREEZE)
        and preregistration == DEFAULT_PREREGISTRATION
        and preregistration.is_file()
        and (activation.get("development_preregistration") or {}).get("sha256")
        == _sha256(preregistration)
        and ledger.is_file()
        and (activation.get("append_only_internal_ledger") or {}).get("sha256")
        == _sha256(ledger)
        and activation.get("remaining_complete_development_trials_authorized") == 1
        and activation.get("stress_2024_2025_authorized") is False
        and activation.get("provider_request_authorized") is False
    ):
        raise Campaign098Error("Campaign098 development activation binding changed")
    return activation


def main() -> int:
    _load_development_activation()
    return _inherited_main()


if __name__ == "__main__":
    raise SystemExit(main())

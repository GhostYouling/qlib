#!/usr/bin/env python3
"""Run Campaign109's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign080.py"
BASE_RUNNER_SHA256 = "b4c4b781392c87f01b9542c2317611a936d431b0328cea9d21ea90b8f68a324b"
BASE_FACTOR = "intraday_above_median_amount_longest_run_240m"
ADMITTED_FACTOR = "intraday_intrabar_body_magnitude_serial_persistence_238p"
FROZEN_TRIAL_ID = (
    "wf109_intraday_intrabar_body_magnitude_serial_persistence_238p_single_higher"
)
DEFAULT_PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_109_preregistration.json"
)
DEVELOPMENT_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_109_development_activation_binding_20260808.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign080 development runner changed")

_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign080", "Campaign109"),
    ("campaign080", "campaign109"),
    ("campaign_080", "campaign_109"),
    ("wf080", "wf109"),
    (BASE_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign109_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

engine_namespace: dict[str, Any] = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION

base = _generated["base"]
Campaign109Error = _generated["Campaign109Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
status = _generated["status"]
_inherited_run_development = _generated["run_development"]
_inherited_run_exposed_stress = _generated["run_exposed_stress"]
_inherited_main = _generated["main"]


def _validate_development_activation() -> dict[str, Any]:
    if not DEVELOPMENT_ACTIVATION.is_file():
        raise Campaign109Error("Campaign109 development activation is absent")
    record = json.loads(DEVELOPMENT_ACTIVATION.read_text(encoding="utf-8"))
    prereg = record.get("development_preregistration") or {}
    runner = record.get("runner") or {}
    freeze = record.get("implementation_freeze") or {}
    audit = record.get("no_return_admission") or {}
    snapshot = record.get("candidate_snapshot") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign109_development_activation_binding"
        and record.get("status")
        == "single_use_frozen_before_campaign109_2019_2023_daily_price_or_return_values"
        and prereg.get("path")
        == str(DEFAULT_PREREGISTRATION.relative_to(REPO_ROOT))
        and prereg.get("sha256") == _sha256(DEFAULT_PREREGISTRATION)
        and runner.get("path")
        == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and len(str(freeze.get("sha256") or "")) == 64
        and _sha256(REPO_ROOT / str(freeze.get("path")))
        == freeze.get("sha256")
        and audit.get("path")
        == "data/experiments/short_horizon/historical_walkforward/campaign_109/no_return/20260807T222738Z_campaign109_no_return_audit.json"
        and audit.get("sha256")
        == "50f7586d006464c055eab4e58c95a30711fb0680c3fcb611e9e3db7ed0cd183d"
        and audit.get("admissible_factor_count") == 1
        and audit.get("numeric_comparisons_passed") == 132
        and snapshot.get("sha256")
        == "b212eac0921bbca2c3a84c6eceb7f6741939c52ccb96a21e3897d1533c8b6aba"
        and snapshot.get("dataset_sha256")
        == "f222c80e80acb9872cc7e29a0fc89ab37e51bc1ee02f40f19f683c3757fcdb90"
        and record.get("trial_count") == 1
        and record.get("trial_id") == FROZEN_TRIAL_ID
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_activation"
        )
        is False
        and record.get("stress_2024_2025_opened_before_activation") is False
        and record.get("candidate49_ledgers_changed_before_activation") is False
        and record.get("provider_request_issued_before_activation") is False
        and record.get("single_use") is True
    ):
        raise Campaign109Error("Campaign109 development activation changed")
    return record


def run_development(args: Any) -> dict[str, Any]:
    _validate_development_activation()
    return _inherited_run_development(args)


def run_exposed_stress(args: Any) -> dict[str, Any]:
    _validate_development_activation()
    return _inherited_run_exposed_stress(args)


engine_namespace["run_development"] = run_development
engine_namespace["run_exposed_stress"] = run_exposed_stress


def main() -> int:
    return _inherited_main()


if __name__ == "__main__":
    raise SystemExit(main())

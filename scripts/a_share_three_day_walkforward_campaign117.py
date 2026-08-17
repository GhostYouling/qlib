#!/usr/bin/env python3
"""Run Campaign117's exact one-trial 2019-2023 historical walk-forward."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign080.py"
BASE_RUNNER_SHA256 = "b4c4b781392c87f01b9542c2317611a936d431b0328cea9d21ea90b8f68a324b"
BASE_FACTOR = "intraday_above_median_amount_longest_run_240m"
ADMITTED_FACTOR = "intraday_amount_weak_order_entropy_236t"
FROZEN_TRIAL_ID = "wf117_intraday_amount_weak_order_entropy_236t_single_higher"
DEFAULT_PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_117_preregistration.json"
)
DEVELOPMENT_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_development_activation_binding_20260813.json"
)
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_development_implementation_freeze_20260813.json"
)
AUTHORITATIVE_NO_RETURN_AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_117/uniqueness/campaign117_ordered_uniqueness_audit.json"
)
AUTHORITATIVE_NO_RETURN_AUDIT_SHA256 = (
    "cb5d77b8fe81fce0464b1c3fe7d93ab345d9b7b1a78f045447e0bf2b6197f084"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "114bb5dd2ac28d8e51e6a35c234cfe06f7d3810b4d7c46303e38af33d4566879"
)
SNAPSHOT_DATASET_SHA256 = (
    "4f5bf6ee2c26f6956178d6954aae92821530c90a6334375e8cf0e9938fa71c18"
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
    ("Campaign080", "Campaign117"),
    ("campaign080", "campaign117"),
    ("campaign_080", "campaign_117"),
    ("wf080", "wf117"),
    (BASE_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign117_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

engine_namespace: dict[str, Any] = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION

base = _generated["base"]
Campaign117Error = _generated["Campaign117Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
status = _generated["status"]
_inherited_run_development = _generated["run_development"]
_inherited_run_exposed_stress = _generated["run_exposed_stress"]
_inherited_main = _generated["main"]


def _validate_development_activation() -> dict[str, Any]:
    if not DEVELOPMENT_ACTIVATION.is_file():
        raise Campaign117Error("Campaign117 development activation is absent")
    record = json.loads(DEVELOPMENT_ACTIVATION.read_text(encoding="utf-8"))
    prereg = record.get("development_preregistration") or {}
    runner = record.get("runner") or {}
    freeze = record.get("implementation_freeze") or {}
    audit = record.get("no_return_admission") or {}
    snapshot = record.get("candidate_snapshot") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign117_development_activation_binding"
        and record.get("status")
        == "single_use_frozen_before_campaign117_2019_2023_daily_price_or_return_values"
        and prereg.get("path") == str(DEFAULT_PREREGISTRATION.relative_to(REPO_ROOT))
        and prereg.get("sha256") == _sha256(DEFAULT_PREREGISTRATION)
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and freeze.get("path") == str(IMPLEMENTATION_FREEZE.relative_to(REPO_ROOT))
        and freeze.get("sha256") == _sha256(IMPLEMENTATION_FREEZE)
        and audit.get("path")
        == str(AUTHORITATIVE_NO_RETURN_AUDIT.relative_to(REPO_ROOT))
        and audit.get("sha256") == AUTHORITATIVE_NO_RETURN_AUDIT_SHA256
        and audit.get("admissible_factor_count") == 1
        and audit.get("numeric_comparisons_passed") == 134
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and record.get("trial_count") == 1
        and record.get("trial_id") == FROZEN_TRIAL_ID
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_activation"
        )
        is False
        and boundary.get("stress_2024_2025_opened_before_activation") is False
        and boundary.get("candidate49_ledgers_changed_before_activation") is False
        and boundary.get("provider_request_issued_before_activation") is False
        and record.get("single_use") is True
    ):
        raise Campaign117Error("Campaign117 development activation changed")
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

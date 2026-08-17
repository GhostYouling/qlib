#!/usr/bin/env python3
"""Run Campaign110's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign080.py"
BASE_RUNNER_SHA256 = "b4c4b781392c87f01b9542c2317611a936d431b0328cea9d21ea90b8f68a324b"
BASE_FACTOR = "intraday_above_median_amount_longest_run_240m"
ADMITTED_FACTOR = "intraday_open_reference_directional_occupancy_240m"
FROZEN_TRIAL_ID = (
    "wf110_intraday_open_reference_directional_occupancy_240m_single_higher"
)
DEFAULT_PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_110_preregistration.json"
)
DEVELOPMENT_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_development_activation_binding_20260808.json"
)
AUTHORITATIVE_NO_RETURN_AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_110/no_return_recovery_v1/20260808T155731Z_campaign110_no_return_audit.json"
)
AUTHORITATIVE_NO_RETURN_AUDIT_SHA256 = (
    "4b6dc87f01e3ad2645a44c1556d138d9d3efcb8fb4a809a439f47371bd7143ae"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "e3ae3c01e0a6eadd8dfce0362520e13bc4c047ff8357cdc7be2d1f9b31e93b72"
)
SNAPSHOT_DATASET_SHA256 = (
    "9082b74891ea2e1c107309637941e42acdc9afeec0b44748e2242506c1a68c4b"
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
    ("Campaign080", "Campaign110"),
    ("campaign080", "campaign110"),
    ("campaign_080", "campaign_110"),
    ("wf080", "wf110"),
    (BASE_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign110_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

engine_namespace: dict[str, Any] = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION

base = _generated["base"]
Campaign110Error = _generated["Campaign110Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
status = _generated["status"]
_inherited_run_development = _generated["run_development"]
_inherited_run_exposed_stress = _generated["run_exposed_stress"]
_inherited_main = _generated["main"]


def _validate_development_activation() -> dict[str, Any]:
    if not DEVELOPMENT_ACTIVATION.is_file():
        raise Campaign110Error("Campaign110 development activation is absent")
    record = json.loads(DEVELOPMENT_ACTIVATION.read_text(encoding="utf-8"))
    prereg = record.get("development_preregistration") or {}
    runner = record.get("runner") or {}
    freeze = record.get("implementation_freeze") or {}
    audit = record.get("no_return_admission") or {}
    snapshot = record.get("candidate_snapshot") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign110_development_activation_binding"
        and record.get("status")
        == "single_use_frozen_before_campaign110_2019_2023_daily_price_or_return_values"
        and prereg.get("path")
        == str(DEFAULT_PREREGISTRATION.relative_to(REPO_ROOT))
        and prereg.get("sha256") == _sha256(DEFAULT_PREREGISTRATION)
        and runner.get("path")
        == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and len(str(freeze.get("sha256") or "")) == 64
        and _sha256(REPO_ROOT / str(freeze.get("path"))) == freeze.get("sha256")
        and audit.get("path")
        == str(AUTHORITATIVE_NO_RETURN_AUDIT.relative_to(REPO_ROOT))
        and audit.get("sha256") == AUTHORITATIVE_NO_RETURN_AUDIT_SHA256
        and audit.get("admissible_factor_count") == 1
        and audit.get("numeric_comparisons_passed") == 133
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
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
        raise Campaign110Error("Campaign110 development activation changed")
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

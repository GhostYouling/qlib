#!/usr/bin/env python3
"""Run Campaign105's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign080.py"
BASE_RUNNER_SHA256 = "b4c4b781392c87f01b9542c2317611a936d431b0328cea9d21ea90b8f68a324b"
BASE_FACTOR = "intraday_above_median_amount_longest_run_240m"
ADMITTED_FACTOR = "intraday_active_trading_bar_share_240m"
FROZEN_TRIAL_ID = "wf105_intraday_active_trading_bar_share_240m_single_higher"
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_preregistration_v3.json"
)
DEVELOPMENT_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_development_activation_binding_20260808.json"
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
    ("Campaign080", "Campaign105"),
    ("campaign080", "campaign105"),
    ("campaign_080", "campaign_105"),
    ("wf080", "wf105"),
    (BASE_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign105_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

engine_namespace: dict[str, Any] = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION

base = _generated["base"]
Campaign105Error = _generated["Campaign105Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
status = _generated["status"]
_inherited_run_development = _generated["run_development"]
_inherited_run_exposed_stress = _generated["run_exposed_stress"]
_inherited_main = _generated["main"]


def _validate_development_activation() -> dict[str, Any]:
    if not DEVELOPMENT_ACTIVATION.is_file():
        raise Campaign105Error("Campaign105 development activation is absent")
    record = json.loads(DEVELOPMENT_ACTIVATION.read_text(encoding="utf-8"))
    prereg = record.get("development_preregistration") or {}
    runner = record.get("runner") or {}
    freeze = record.get("implementation_freeze") or {}
    audit = record.get("no_return_admission") or {}
    snapshot = record.get("candidate_snapshot") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign105_development_activation_binding"
        and record.get("status")
        == "single_use_frozen_before_campaign105_2019_2023_daily_price_or_return_values"
        and prereg.get("path") == str(DEFAULT_PREREGISTRATION.relative_to(REPO_ROOT))
        and len(str(prereg.get("sha256") or "")) == 64
        and _sha256(DEFAULT_PREREGISTRATION) == prereg.get("sha256")
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and len(str(freeze.get("sha256") or "")) == 64
        and _sha256(REPO_ROOT / str(freeze.get("path"))) == freeze.get("sha256")
        and audit.get("path")
        == "data/experiments/short_horizon/historical_walkforward/campaign_105/no_return/20260807T182638Z_campaign105_no_return_audit.json"
        and audit.get("sha256")
        == "b310912ecd43e2012907bd33b465e584aee9201c1560224ef44d9966917bcc54"
        and audit.get("admissible_factor_count") == 1
        and snapshot.get("sha256")
        == "56e2d016087ff09643ef98dd00cad0ac9c771e815d19ec9941cea9f5904824a5"
        and snapshot.get("dataset_sha256")
        == "912625c3763fe3868adb4c4f410b6a6ab72c9272f78b8b57db620daaf970018c"
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
        raise Campaign105Error("Campaign105 development activation changed")
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

#!/usr/bin/env python3
"""Run the one frozen Campaign048 three-session development trial.

Campaign048 byte-binds the terminal Campaign047 orchestration and changes only
the deterministic campaign namespace, admitted factor, and the trial identifier
already frozen by the Campaign048 no-return preregistration.  The three folds,
execution assumptions, survivor gates, and conditional exposed-stress boundary
remain inherited unchanged.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN047_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign047.py"
)
CAMPAIGN047_RUNNER_SHA256 = (
    "f22728ffe96aae25f039f7179be0b981defb42fd734786236306e9b93389e784"
)
OLD_FACTOR = "intraday_body_next_microgap_reversal_238p"
ADMITTED_FACTOR = "intraday_two_sided_wick_absorption_balance_240m"
FROZEN_TRIAL_ID = (
    "wf048_intraday_two_sided_wick_absorption_balance_240m_single_higher"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN047_RUNNER) != CAMPAIGN047_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign047 orchestration fingerprint changed")

_source = CAMPAIGN047_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign047", "Campaign048"),
    ("campaign047", "campaign048"),
    ("campaign_047", "campaign_048"),
    ("wf047", "wf048"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign048_generated",
}
exec(compile(_source, str(CAMPAIGN047_RUNNER), "exec"), _generated)

_inherited_build_trial_catalog = _generated["build_trial_catalog"]


def build_trial_catalog(campaign: dict[str, Any]) -> list[dict[str, Any]]:
    """Preserve the exact trial identifier frozen before candidate values."""

    catalog = _inherited_build_trial_catalog(campaign)
    if (
        len(catalog) != 1
        or catalog[0].get("kind") != "single_factor"
        or catalog[0].get("feature_set") != [ADMITTED_FACTOR]
        or catalog[0].get("weights") != [1.0]
        or catalog[0].get("complexity") != 1
    ):
        raise RuntimeError("Campaign048 inherited finite catalog changed")
    exact = dict(catalog[0])
    exact["trial_id"] = FROZEN_TRIAL_ID
    return [exact]


# Functions defined by the generated engine resolve globals through this dict.
# Rebinding here makes load, status, development, and stress use the same exact
# pre-value trial identifier rather than the older display convention.
_generated["build_trial_catalog"] = build_trial_catalog

base = _generated["base"]
Campaign048Error = _generated["Campaign048Error"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]
engine_namespace = _generated
_inherited_survivor_decision = _generated[
    "_inherited_survivor_decision"
]
_survivor_decision_with_canonical_complexity = _generated[
    "_survivor_decision_with_canonical_complexity"
]


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the single frozen Campaign033 three-session walk-forward trial.

Campaign033 reuses the byte-bound Campaign031 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited. The
shared reporting repair canonicalizes displayed complexity from feature_set.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_reporting as reporting  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN031_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign031.py"
)
CAMPAIGN031_RUNNER_SHA256 = (
    "888bb4e29cef275fa8b55dd354610596d5cc9f1312d7757d8a378741055f7758"
)
REPORTING_HELPER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_reporting.py"
)
REPORTING_HELPER_SHA256 = (
    "6291a8bfd11bd90dbef42edd6252368f67498bdc2be39661ebf4b7d08f0ac969"
)
OLD_FACTOR = "intraday_market_dispersion_decoupling_238m"
ADMITTED_FACTOR = "intraday_return_spectral_entropy_59f"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN031_RUNNER) != CAMPAIGN031_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign031 orchestration fingerprint changed")
if _sha256(REPORTING_HELPER) != REPORTING_HELPER_SHA256:
    raise RuntimeError("frozen walk-forward reporting helper changed")

_source = CAMPAIGN031_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign031", "Campaign033"),
    ("campaign031", "campaign033"),
    ("campaign_031", "campaign_033"),
    ("wf031", "wf033"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign033_generated",
}
exec(compile(_source, str(CAMPAIGN031_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign033Error = _generated["Campaign033Error"]
build_trial_catalog = _generated["build_trial_catalog"]
_inherited_load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]
engine_namespace = run_exposed_stress.__globals__


def _load_campaign_with_single_trial_stress_semantics(
    path: Path,
) -> tuple[dict[str, Any], str]:
    spec, observed_sha256 = _inherited_load_campaign(path)
    replay = spec.get("exposed_stress_replay") or {}
    if (
        len(build_trial_catalog(spec)) != 1
        or replay.get("opening_rule")
        != (
            "Open only after all 42 development trials are retained and "
            "the survivor record is frozen."
        )
    ):
        raise Campaign033Error(
            "inherited Campaign033 stress-opening context changed"
        )
    effective = copy.deepcopy(spec)
    effective["exposed_stress_replay"]["opening_rule"] = (
        "Open only after the single frozen Campaign033 development trial is "
        "retained and the survivor record is frozen."
    )
    return effective, observed_sha256


load_campaign = _load_campaign_with_single_trial_stress_semantics
engine_namespace["load_campaign"] = load_campaign

_inherited_survivor_decision = (
    engine_namespace["campaign002"].survivor_decision
)


def _survivor_decision_with_canonical_complexity(
    entry: dict[str, Any],
    campaign: dict[str, Any],
) -> dict[str, Any]:
    inherited = _inherited_survivor_decision(entry, campaign)
    return reporting.with_canonical_complexity(inherited, entry)


engine_namespace["campaign002"] = SimpleNamespace(
    survivor_decision=_survivor_decision_with_canonical_complexity
)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the single frozen Campaign045 three-session walk-forward trial.

Campaign045 reuses the byte-bound Campaign043 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited. The
shared reporting repair keeps displayed complexity equal to the feature set.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN043_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign043.py"
)
CAMPAIGN043_RUNNER_SHA256 = (
    "55aa5ea4df9a266695bda7474839310ce18568950995fde349dc3a0db9e021a0"
)
OLD_FACTOR = "intraday_transaction_vwap_consensus_240m"
ADMITTED_FACTOR = "intraday_volatility_activity_lead_lag_asymmetry_236p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN043_RUNNER) != CAMPAIGN043_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign043 orchestration fingerprint changed")

_source = CAMPAIGN043_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign043", "Campaign045"),
    ("campaign043", "campaign045"),
    ("campaign_043", "campaign_045"),
    ("wf043", "wf045"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign045_generated",
}
exec(compile(_source, str(CAMPAIGN043_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign045Error = _generated["Campaign045Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]
engine_namespace = _generated["engine_namespace"]
_inherited_survivor_decision = _generated[
    "_inherited_survivor_decision"
]
_survivor_decision_with_canonical_complexity = _generated[
    "_survivor_decision_with_canonical_complexity"
]


if __name__ == "__main__":
    raise SystemExit(main())

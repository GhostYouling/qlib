#!/usr/bin/env python3
"""Run the single frozen Campaign043 three-session walk-forward trial.

Campaign043 reuses the byte-bound Campaign042 orchestration and unchanged
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
CAMPAIGN042_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign042.py"
)
CAMPAIGN042_RUNNER_SHA256 = (
    "921e77cd1e972e0d4910200e73d213eab76abcde8abad593824949371cb19a3a"
)
OLD_FACTOR = "intraday_lunch_repricing_persistence_2r"
ADMITTED_FACTOR = "intraday_transaction_vwap_consensus_240m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN042_RUNNER) != CAMPAIGN042_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign042 orchestration fingerprint changed")

_source = CAMPAIGN042_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign042", "Campaign043"),
    ("campaign042", "campaign043"),
    ("campaign_042", "campaign_043"),
    ("wf042", "wf043"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign043_generated",
}
exec(compile(_source, str(CAMPAIGN042_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign043Error = _generated["Campaign043Error"]
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

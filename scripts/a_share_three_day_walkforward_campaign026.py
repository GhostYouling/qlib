#!/usr/bin/env python3
"""Run the single frozen Campaign026 three-session walk-forward trial.

Campaign026 reuses the byte-bound Campaign025 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN025_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign025.py"
)
CAMPAIGN025_RUNNER_SHA256 = (
    "8d3d15d2d4a9bca2ad64e19d505f8d67bd98f29303b0d2e85bafc54b5f6d5659"
)
OLD_FACTOR = "intraday_extreme_arrival_order_240m"
ADMITTED_FACTOR = "intraday_market_up_down_correlation_asymmetry_238m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN025_RUNNER) != CAMPAIGN025_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign025 orchestration fingerprint changed")

_source = CAMPAIGN025_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign025", "Campaign026"),
    ("campaign025", "campaign026"),
    ("campaign_025", "campaign_026"),
    ("wf025", "wf026"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign026_generated",
}
exec(compile(_source, str(CAMPAIGN025_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign026Error = _generated["Campaign026Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]
engine_namespace = run_exposed_stress.__globals__


if __name__ == "__main__":
    raise SystemExit(main())

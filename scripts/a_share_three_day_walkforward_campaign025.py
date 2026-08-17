#!/usr/bin/env python3
"""Run the single frozen Campaign025 three-session walk-forward trial.

Campaign025 reuses the byte-bound Campaign024 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN024_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign024.py"
)
CAMPAIGN024_RUNNER_SHA256 = (
    "934b562358c50ba9afd6e61ce3bcdc1644f626caca17b38aca0b8fc17b3ddda0"
)
OLD_FACTOR = "intraday_directional_range_response_coupling_238p"
ADMITTED_FACTOR = "intraday_extreme_arrival_order_240m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN024_RUNNER) != CAMPAIGN024_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign024 orchestration fingerprint changed")

_source = CAMPAIGN024_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign024", "Campaign025"),
    ("campaign024", "campaign025"),
    ("campaign_024", "campaign_025"),
    ("wf024", "wf025"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign025_generated",
}
exec(compile(_source, str(CAMPAIGN024_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign025Error = _generated["Campaign025Error"]
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

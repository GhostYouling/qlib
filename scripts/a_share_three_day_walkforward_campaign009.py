#!/usr/bin/env python3
"""Run the single frozen Campaign009 three-session walk-forward trial.

Campaign009 reuses the byte-bound Campaign007 orchestration wrapper and the
unchanged Campaign006 execution engine. Only deterministic campaign namespace
and admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN007_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign007.py"
)
CAMPAIGN007_RUNNER_SHA256 = (
    "3c54a1a9db9d5a59d7ef9cac95bbc0260cf168ec9e386fd61f63fd75fe16dd35"
)
OLD_FACTOR = "intraday_share_volume_transaction_price_coupling_238p"
ADMITTED_FACTOR = "intraday_intrabar_body_range_efficiency_240m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN007_RUNNER) != CAMPAIGN007_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign007 orchestration fingerprint changed")

_source = CAMPAIGN007_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign007", "Campaign009"),
    ("campaign007", "campaign009"),
    ("campaign_007", "campaign_009"),
    ("wf007", "wf009"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign009_generated",
}
exec(compile(_source, str(CAMPAIGN007_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign009Error = _generated["Campaign009Error"]
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

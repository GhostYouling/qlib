#!/usr/bin/env python3
"""Run the single frozen Campaign006 three-session walk-forward trial.

Campaign006 reuses the byte-bound Campaign005 orchestration layer and its
byte-bound Campaign004 execution engine.  Only the deterministic namespace and
admitted-factor substitutions below are allowed; folds, execution assumptions,
survivor gates, and exposed-stress rules remain inherited unchanged.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN005_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign005.py"
)
CAMPAIGN005_RUNNER_SHA256 = (
    "00815ecb8ccf2b68ab3297a2f4d4ddd96c9fdf64b7416bb46c41d3f3376ae4f6"
)
OLD_FACTOR = "intraday_zero_return_amount_intensity_238m"
ADMITTED_FACTOR = "intraday_transaction_price_path_confirmation_238p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN005_RUNNER) != CAMPAIGN005_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign005 orchestration fingerprint changed")

_source = CAMPAIGN005_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign005", "Campaign006"),
    ("campaign005", "campaign006"),
    ("campaign_005", "campaign_006"),
    ("wf005", "wf006"),
    (OLD_FACTOR, ADMITTED_FACTOR),
    (
        "completed_with_admissible_factors_pending_walkforward_preregistration",
        "completed_with_one_admissible_factor_pending_walkforward_preregistration",
    ),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign006_generated",
}
exec(compile(_source, str(CAMPAIGN005_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign006Error = _generated["Campaign006Error"]
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

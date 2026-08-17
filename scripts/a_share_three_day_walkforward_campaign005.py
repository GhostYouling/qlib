#!/usr/bin/env python3
"""Run the single frozen Campaign005 three-session walk-forward trial.

Campaign005 deliberately reuses the terminal Campaign004 execution engine
without modifying that file.  The exact Campaign004 source fingerprint and
the deterministic Campaign004-to-Campaign005 namespace transformation below
are fail-closed.  A compact Campaign005 preregistration overlays only the new
admitted factor and trial catalog; all folds, execution assumptions, survivor
gates, and exposed-stress rules are inherited byte-bound from Campaign004.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN004_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign004.py"
)
CAMPAIGN004_RUNNER_SHA256 = (
    "cb489806524a78a9687e70762242ad31f2cedf7c1834b066cb55ba09c312cc15"
)
DEFAULT_CAMPAIGN = (
    REPO_ROOT / "docs" / "a_share_three_day_walkforward_campaign_005_preregistration.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_005"
    / "walkforward"
)
CAMPAIGN_ID = "a_share_three_day_walkforward_campaign_005"
CAMPAIGN_KIND = "a_share_three_day_walkforward_campaign005_preregistration"
CAMPAIGN_STATUS = "frozen_before_campaign005_2019_2023_development_return_read"
ADMITTED_FACTOR = "intraday_zero_return_amount_intensity_238m"
EXPECTED_FIELDS = {
    "version",
    "kind",
    "campaign_id",
    "status",
    "frozen_at",
    "purpose",
    "evidence_classification",
    "template_binding",
    "governance_bindings",
    "no_return_bindings",
    "implementation",
    "factor_library",
    "search_space",
    "candidate49_boundary",
    "research_output_boundary",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN004_RUNNER) != CAMPAIGN004_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign004 execution engine fingerprint changed")

_source = CAMPAIGN004_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign004", "Campaign005"),
    ("campaign004", "campaign005"),
    ("campaign_004", "campaign_005"),
    ("wf004", "wf005"),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign005_generated",
}
exec(compile(_source, str(CAMPAIGN004_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign005Error = _generated["Campaign005Error"]
build_trial_catalog = _generated["build_trial_catalog"]


def _validate_binding(binding: dict[str, Any], label: str) -> Path:
    try:
        return base.validate_file_binding(binding, label)
    except base.WalkForwardError as error:
        raise Campaign005Error(str(error)) from error


def _validate_closed_boundaries(spec: dict[str, Any]) -> None:
    boundary = spec.get("candidate49_boundary") or {}
    if (
        boundary.get("included_in_feature_library") is not False
        or boundary.get("historical_return_read_allowed") is not False
        or boundary.get("prospective_ledgers_changed_by_campaign") is not False
    ):
        raise Campaign005Error("Candidate49 boundary is not fail-closed")
    output = spec.get("research_output_boundary") or {}
    required_false = (
        "current_scoring_allowed",
        "selection_allowed",
        "sizing_allowed",
        "orders_allowed",
        "prospective_candidate_activation_allowed",
        "campaign004_rescue_or_reweight_allowed",
    )
    if not all(output.get(key) is False for key in required_false):
        raise Campaign005Error("Campaign005 output boundary is not closed")


def load_campaign(path: Path) -> tuple[dict[str, Any], str]:
    path = path.expanduser().resolve()
    spec = base.load_json(path)
    if (
        spec.get("version") != 1
        or spec.get("kind") != CAMPAIGN_KIND
        or spec.get("campaign_id") != CAMPAIGN_ID
        or spec.get("status") != CAMPAIGN_STATUS
    ):
        raise Campaign005Error("Campaign005 preregistration header is invalid")
    unexpected = sorted(set(spec) - EXPECTED_FIELDS)
    missing = sorted(EXPECTED_FIELDS - set(spec))
    if unexpected or missing:
        raise Campaign005Error(
            f"Campaign005 preregistration fields changed: missing={missing}, "
            f"unexpected={unexpected}"
        )

    template_path = _validate_binding(
        spec["template_binding"], "Campaign004 template preregistration"
    )
    template = base.load_json(template_path)
    if (
        template.get("kind")
        != "a_share_three_day_walkforward_campaign004_preregistration"
        or template.get("campaign_id")
        != "a_share_three_day_walkforward_campaign_004"
        or template.get("status")
        != "frozen_before_campaign004_2019_2023_development_return_read"
    ):
        raise Campaign005Error("Campaign004 template is not the frozen terminal campaign")

    for group_name in ("governance_bindings", "no_return_bindings"):
        for name, binding in sorted((spec.get(group_name) or {}).items()):
            _validate_binding(binding, f"{group_name}.{name}")

    implementation = spec.get("implementation") or {}
    if set(implementation) != {
        "script",
        "development_command",
        "exposed_stress_command",
        "output_root",
    }:
        raise Campaign005Error("Campaign005 implementation binding is incomplete")
    if _validate_binding(
        implementation["script"], "Campaign005 runner"
    ) != Path(__file__).resolve():
        raise Campaign005Error("Campaign005 runner binding identifies another file")
    if Path(str(implementation["output_root"])).resolve() != DEFAULT_OUTPUT_ROOT:
        raise Campaign005Error("Campaign005 output root changed")

    audit_path = _validate_binding(
        (spec.get("no_return_bindings") or {}).get("audit") or {},
        "Campaign005 no-return audit",
    )
    audit = base.load_json(audit_path)
    admissible = sorted(str(value) for value in audit.get("admissible_factor_names") or [])
    if (
        audit.get("kind")
        != "a_share_three_day_walkforward_campaign005_no_return_audit"
        or audit.get("status")
        != "completed_with_admissible_factors_pending_walkforward_preregistration"
        or admissible != [ADMITTED_FACTOR]
        or audit.get("admissible_factor_count") != 1
        or audit.get("historical_forward_return_fields_read") is not False
        or audit.get("candidate49_historical_return_read") is not False
    ):
        raise Campaign005Error("Campaign005 no-return audit is not admissible")

    factors = list(spec.get("factor_library") or [])
    if (
        len(factors) != 1
        or factors[0].get("name") != ADMITTED_FACTOR
        or factors[0].get("direction") != "higher"
        or factors[0].get("dataset_group") != "campaign005_new_factors"
        or not Path(str(factors[0].get("partition_root") or "")).is_absolute()
    ):
        raise Campaign005Error("Campaign005 factor library changed from no-return audit")
    for index, binding in enumerate(factors[0].get("bindings") or []):
        _validate_binding(binding, f"factor_library[0].bindings[{index}]")

    search = spec.get("search_space") or {}
    if (
        search.get("admissible_factor_names_canonical") != [ADMITTED_FACTOR]
        or search.get("expected_single_trial_count") != 1
        or search.get("expected_pair_trial_count") != 0
        or search.get("expected_trial_count") != 1
        or search.get("weight_fitting") is not False
        or search.get("threshold_search") is not False
        or search.get("year_subset_search") is not False
        or search.get("filter_search") is not False
        or search.get("triple_or_higher_order_combinations") is not False
        or search.get("old_terminal_factor_rescue_combinations") is not False
        or search.get("record_every_trial_and_infrastructure_failure") is not True
    ):
        raise Campaign005Error("Campaign005 finite search boundary changed")
    _validate_closed_boundaries(spec)

    effective = copy.deepcopy(template)
    for key in (
        "version",
        "kind",
        "campaign_id",
        "status",
        "frozen_at",
        "purpose",
        "evidence_classification",
        "governance_bindings",
        "no_return_bindings",
        "implementation",
        "factor_library",
        "search_space",
        "candidate49_boundary",
        "research_output_boundary",
    ):
        effective[key] = copy.deepcopy(spec[key])
    build_trial_catalog(effective)
    return effective, base.file_sha256(path)


_generated["DEFAULT_CAMPAIGN"] = DEFAULT_CAMPAIGN
_generated["DEFAULT_OUTPUT_ROOT"] = DEFAULT_OUTPUT_ROOT
_generated["load_campaign"] = load_campaign

parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())

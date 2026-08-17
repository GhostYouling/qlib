#!/usr/bin/env python3
"""Audit the completed Campaign003 low-volatility-gate research artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign as base  # noqa: E402
import a_share_three_day_walkforward_campaign003 as campaign003  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAMPAIGN = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_003_preregistration.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_003"
)
DEFAULT_RESEARCH_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_003_research_record.json"
)
SIGNAL_LEDGER = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "candidate49_future_execution_ledger.json"
)
EXPECTED_SIGNAL_LEDGER_SHA = (
    "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
)
EXPECTED_EXECUTION_LEDGER_SHA = (
    "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
)


class AuditError(RuntimeError):
    """Campaign003 completion audit failure."""


def check(name: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "evidence": evidence}


def _ledger_entry_count(path: Path) -> int:
    data = base.load_json(path)
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise AuditError(f"ledger entries are invalid: {path}")
    return len(entries)


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    campaign_path = Path(args.campaign).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    record_path = Path(args.research_record).expanduser().resolve()
    campaign, _spec, campaign_sha = campaign003.load_campaign(campaign_path)
    catalog = campaign003.build_trial_catalog(campaign)
    ledger_path = output_root / campaign003.LEDGER_FILENAME
    survivor_path = output_root / campaign003.SURVIVOR_FILENAME
    stress_path = output_root / campaign003.STRESS_RECORD_FILENAME
    report_path = output_root / campaign003.REPORT_FILENAME
    ledger = campaign003.validate_ledger(
        base.load_json(ledger_path), campaign_path, campaign_sha
    )
    survivors = base.load_json(survivor_path)
    expected_survivors = campaign003.build_survivor_record(
        campaign, campaign_path, campaign_sha, ledger
    )
    stress = base.load_json(stress_path)
    report = base.load_json(report_path)
    record = base.load_json(record_path)
    checks: list[dict[str, Any]] = []

    factor_names = sorted(
        str(item["name"]) for item in campaign["factor_library"]
    )
    modes: dict[str, int] = {}
    thresholds: dict[str, int] = {}
    for trial in catalog:
        modes[trial["score_mode"]] = modes.get(trial["score_mode"], 0) + 1
        thresholds[trial["gate_threshold_id"]] = (
            thresholds.get(trial["gate_threshold_id"], 0) + 1
        )
    checks.append(
        check(
            "complete_finite_gate_library_and_search_frozen",
            (
                len(catalog) == 42
                and len({item["trial_id"] for item in catalog}) == 42
                and modes
                == {
                    "primary_within_gate_rank": 21,
                    "primary_75_low_vol_25_within_gate_rank": 21,
                }
                and thresholds
                == {
                    "retain_75pct": 14,
                    "retain_60pct": 14,
                    "retain_45pct": 14,
                }
            ),
            {
                "factor_count": len(factor_names),
                "primary_signal_count": 7,
                "trial_count": len(catalog),
                "mode_counts": dict(sorted(modes.items())),
                "threshold_counts": dict(sorted(thresholds.items())),
            },
        )
    )
    checks.append(
        check(
            "prior_terminal_conclusions_preserved_and_candidate49_excluded",
            (
                len(factor_names) == 8
                and "intraday_realized_volatility" in factor_names
                and "intraday_cumulative_vwap_crossing_rate_240m"
                not in factor_names
                and all(
                    item.get("prior_terminal_conclusion_unchanged") is True
                    for item in campaign["factor_library"]
                )
            ),
            {
                "factor_names": factor_names,
                "candidate49_factor_present": (
                    "intraday_cumulative_vwap_crossing_rate_240m"
                    in factor_names
                ),
            },
        )
    )

    development = [
        entry
        for entry in ledger["entries"]
        if entry.get("phase") == campaign003.DEVELOPMENT_PHASE
    ]
    infrastructure = [
        entry
        for entry in ledger["entries"]
        if (
            entry.get("status_and_rejection_reason") or {}
        ).get("status")
        == "infrastructure_failed"
    ]
    checks.append(
        check(
            "all_42_development_trials_retained_once_without_infrastructure_failure",
            (
                len(ledger["entries"]) == 42
                and len(development) == 42
                and len(infrastructure) == 0
                and {entry["trial_id"] for entry in development}
                == {trial["trial_id"] for trial in catalog}
            ),
            {
                "ledger_entry_count": len(ledger["entries"]),
                "development_entry_count": len(development),
                "infrastructure_failure_count": len(infrastructure),
            },
        )
    )

    catalog_by_id = {item["trial_id"]: item for item in catalog}
    semantic_entry_count = 0
    for entry in development:
        trial = catalog_by_id[entry["trial_id"]]
        configuration = (
            entry.get(
                "window_transform_threshold_filter_and_weight_configuration"
            )
            or {}
        )
        if (
            entry.get("campaign_id") == campaign003.CAMPAIGN_ID
            and entry.get("candidate49_historical_return_read") is False
            and entry.get(
                "current_scoring_selection_sizing_or_orders_performed"
            )
            is False
            and entry.get("feature_set") == trial["feature_set"]
            and configuration.get("primary_factor") == trial["primary_factor"]
            and configuration.get("risk_gate_factor") == trial["gate_factor"]
            and configuration.get(
                "risk_gate_minimum_directional_percentile_rank"
            )
            == trial["gate_threshold"]
            and configuration.get("score_mode") == trial["score_mode"]
            and configuration.get("score_weights_primary_then_low_vol")
            == trial["score_weights"]
            and len(entry.get("training_metrics") or []) == 3
            and len(entry.get("validation_metrics") or []) == 3
            and isinstance(entry.get("development_aggregate_metrics"), dict)
            and entry.get("locked_backtest_metrics_when_opened") is None
        ):
            semantic_entry_count += 1
    checks.append(
        check(
            "development_entries_match_catalog_folds_and_research_boundaries",
            semantic_entry_count == 42,
            {"checked_development_entries": semantic_entry_count},
        )
    )

    checks.append(
        check(
            "survivor_record_replays_exactly",
            survivors == expected_survivors,
            {
                "trial_decision_count": len(
                    survivors.get("trial_decisions") or []
                ),
                "selected_survivor_count": survivors.get(
                    "selected_survivor_count"
                ),
                "ledger_prefix_entry_count": (
                    survivors.get("ledger_prefix") or {}
                ).get("entry_count"),
            },
        )
    )
    decisions = list(survivors.get("trial_decisions") or [])
    operational_count = sum(
        item.get("operationally_admissible") is True for item in decisions
    )
    quality_count = sum(
        item.get("validation_quality_gate_passed") is True for item in decisions
    )
    aggregate_20bp_nonpositive_count = sum(
        float(item.get("development_aggregate_20bp_return") or 0.0) <= 0.0
        for item in decisions
    )
    checks.append(
        check(
            "zero_survivors_is_frozen_gate_result_not_post_result_relaxation",
            (
                len(decisions) == 42
                and operational_count == 21
                and quality_count == 0
                and aggregate_20bp_nonpositive_count == 42
                and survivors.get("selected_survivor_count") == 0
                and survivors.get("selected_exposed_stress_survivor_trial_ids")
                == []
            ),
            {
                "decision_count": len(decisions),
                "operationally_admissible_count": operational_count,
                "validation_quality_gate_passed_count": quality_count,
                "nonpositive_development_aggregate_20bp_count": (
                    aggregate_20bp_nonpositive_count
                ),
                "selected_survivor_count": survivors.get(
                    "selected_survivor_count"
                ),
            },
        )
    )

    stress_entries = [
        entry
        for entry in ledger["entries"]
        if entry.get("phase") == campaign003.STRESS_PHASE
    ]
    checks.append(
        check(
            "historically_exposed_2024_2025_interval_was_not_opened",
            (
                stress.get("stress_interval_opened") is False
                and stress.get("reason") == "zero_development_survivors"
                and stress.get("selected_survivor_trial_ids") == []
                and stress.get("completed_stress_trial_ids") == []
                and len(stress_entries) == 0
                and not (output_root / campaign003.STRESS_INTENT_FILENAME).exists()
            ),
            {
                "stress_interval_opened": stress.get(
                    "stress_interval_opened"
                ),
                "stress_ledger_entry_count": len(stress_entries),
                "stress_intent_exists": (
                    output_root / campaign003.STRESS_INTENT_FILENAME
                ).exists(),
            },
        )
    )
    checks.append(
        check(
            "campaign_report_matches_closed_zero_survivor_state",
            (
                report.get("kind")
                == "a_share_three_day_walkforward_campaign003_report"
                and report.get("campaign_sha256") == campaign_sha
                and report.get("development_trial_count") == 42
                and report.get("infrastructure_failure_count") == 0
                and report.get("development_gate_passer_count") == 0
                and report.get("selected_exposed_stress_survivor_count") == 0
                and (report.get("exposed_stress") or {}).get(
                    "stress_interval_opened"
                )
                is False
            ),
            {
                "development_trial_count": report.get(
                    "development_trial_count"
                ),
                "development_gate_passer_count": report.get(
                    "development_gate_passer_count"
                ),
                "stress_interval_opened": (
                    report.get("exposed_stress") or {}
                ).get("stress_interval_opened"),
            },
        )
    )

    actual_files = sorted(
        item.name for item in output_root.iterdir() if item.is_file()
    )
    expected_files = sorted(
        [
            campaign003.LEDGER_FILENAME,
            campaign003.SURVIVOR_FILENAME,
            campaign003.STRESS_RECORD_FILENAME,
            campaign003.REPORT_FILENAME,
        ]
    )
    checks.append(
        check(
            "campaign_created_only_declared_research_artifacts",
            actual_files == expected_files,
            {
                "actual_output_filenames": actual_files,
                "expected_output_filenames": expected_files,
            },
        )
    )

    signal_sha = base.file_sha256(SIGNAL_LEDGER)
    execution_sha = base.file_sha256(EXECUTION_LEDGER)
    checks.append(
        check(
            "candidate49_ledgers_remain_empty_and_unchanged",
            (
                signal_sha == EXPECTED_SIGNAL_LEDGER_SHA
                and execution_sha == EXPECTED_EXECUTION_LEDGER_SHA
                and _ledger_entry_count(SIGNAL_LEDGER) == 0
                and _ledger_entry_count(EXECUTION_LEDGER) == 0
            ),
            {
                "signal_ledger_sha256": signal_sha,
                "signal_entry_count": _ledger_entry_count(SIGNAL_LEDGER),
                "execution_ledger_sha256": execution_sha,
                "execution_entry_count": _ledger_entry_count(EXECUTION_LEDGER),
            },
        )
    )

    bindings = record.get("completed_artifacts") or {}
    expected_artifacts = {
        "trial_ledger": ledger_path,
        "development_survivors": survivor_path,
        "exposed_stress_consumption_record": stress_path,
        "campaign_report": report_path,
    }
    artifact_bindings_match = all(
        (bindings.get(name) or {}).get("path")
        == str(path.relative_to(REPO_ROOT))
        and (bindings.get(name) or {}).get("sha256") == base.file_sha256(path)
        for name, path in expected_artifacts.items()
    )
    price_audit_binding = bindings.get("fresh_price_basis_audit") or {}
    price_audit_path = REPO_ROOT / str(price_audit_binding.get("path") or "")
    price_audit_matches = (
        price_audit_path.is_file()
        and price_audit_binding.get("sha256") == base.file_sha256(price_audit_path)
        and base.load_json(price_audit_path).get("status") == "passed"
        and base.load_json(price_audit_path).get("forward_return_fields_read")
        is False
    )
    checks.append(
        check(
            "research_record_binds_completed_artifacts_and_fresh_price_audit",
            (
                record.get("kind")
                == "a_share_three_day_walkforward_campaign003_research_record"
                and record.get("status")
                == "completed_zero_development_survivors_stress_interval_not_opened"
                and artifact_bindings_match
                and price_audit_matches
            ),
            {
                "artifact_binding_names": sorted(expected_artifacts),
                "all_required_bindings_match": artifact_bindings_match,
                "fresh_price_basis_audit_matches": price_audit_matches,
            },
        )
    )
    boundary = record.get("research_boundary") or {}
    boundary_keys = (
        "candidate49_historical_return_read",
        "candidate49_ledgers_changed",
        "candidate50_prospective_activation_created",
        "stress_2024_2025_return_fields_read",
        "current_scoring_performed",
        "selection_sizing_or_orders_performed",
        "provider_request_issued",
        "investment_advice",
    )
    checks.append(
        check(
            "research_record_preserves_candidate_and_action_boundaries",
            all(boundary.get(name) is False for name in boundary_keys),
            {name: boundary.get(name) for name in boundary_keys},
        )
    )

    failed = [item["name"] for item in checks if not item["passed"]]
    return {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign003_completion_audit",
        "status": "passed" if not failed else "failed",
        "campaign_sha256": campaign_sha,
        "research_record_sha256": base.file_sha256(record_path),
        "ledger_sha256": base.file_sha256(ledger_path),
        "ledger_chain_tip_sha256": ledger["chain_tip_sha256"],
        "requirement_check_count": len(checks),
        "failed_requirement_checks": failed,
        "checks": checks,
        "limitations": [
            "All historical evidence remains exposed rather than pristine.",
            (
                "The holding universe derives from a current listing snapshot "
                "and may contain survivorship bias."
            ),
            (
                "The audit proves repository artifacts and declared boundaries, "
                "not actions outside the workspace."
            ),
        ],
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN))
    value.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    value.add_argument("--research-record", default=str(DEFAULT_RESEARCH_RECORD))
    value.add_argument("--compact", action="store_true")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        result = run_audit(args)
    except Exception as error:
        result = {
            "version": 1,
            "kind": "a_share_three_day_walkforward_campaign003_completion_audit",
            "status": "failed",
            "error": f"{type(error).__name__}: {error}",
        }
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=args.compact,
        )
    )
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

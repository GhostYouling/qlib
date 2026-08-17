#!/usr/bin/env python3
"""Append Campaign263's sole development trial to the research ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PREDEVELOPMENT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v7.json"
)
TRIAL_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/walkforward/trial_ledger.json"
)
SURVIVORS = TRIAL_LEDGER.parent / "development_survivors.json"
STRESS_RECORD = TRIAL_LEDGER.parent / "exposed_stress_consumption_record.json"
CAMPAIGN_REPORT = TRIAL_LEDGER.parent / "campaign_report.json"
OUTPUT = TRIAL_LEDGER.parents[1] / "research_attempt_ledger_v8.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict[str, Any]) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    payload = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def build() -> dict[str, Any]:
    predecessor = json.loads(PREDEVELOPMENT.read_text(encoding="utf-8"))
    survivors = json.loads(SURVIVORS.read_text(encoding="utf-8"))
    decision = survivors["trial_decisions"][0]
    if not (
        _sha256(PREDEVELOPMENT)
        == "cd2ea26d309c2193f0ba200a1545288f084b07302cb18c91ff11231d41f110c1"
        and _sha256(TRIAL_LEDGER)
        == "31402f4cb7f95f88d443411a983845ba22a676670e69b232213b3f5fbd14145a"
        and _sha256(SURVIVORS)
        == "ce753ac4711ed67016480a58818d552e12ee4ab2fefbeb12c0d20cc658f5b3e0"
        and _sha256(STRESS_RECORD)
        == "28a7991dddd88d68862f2e17b5bdc855a5fcf64e664d1b89a91c7cad4ed34a36"
        and _sha256(CAMPAIGN_REPORT)
        == "67548202734847a6cc294a7dad4e4269379922eb5bfda50f0d9fdb3f1c728002"
        and survivors["selected_survivor_count"] == 0
        and survivors["stress_return_fields_read"] is False
        and decision["development_survivor_gate_passed"] is False
    ):
        raise RuntimeError("Campaign263 terminal development evidence changed")
    entry: dict[str, Any] = {
        "ordinal": 29,
        "attempt_id": "campaign263_development_001",
        "attempt_class": "return_reading_development_trial",
        "phase": "frozen_2019_2023_expanding_walkforward_development",
        "status": "terminal_zero_survivors_after_one_frozen_trial",
        "scientific_attempt": True,
        "result_consumed": True,
        "trial_id": "wf263_intraday_amount_profile_spectral_entropy_60f_single_higher",
        "formula_direction_parameter_filter_subset_combination_or_model_changed": False,
        "rejection_reasons": decision["validation_quality_rejection_reasons"],
        "artifact": {
            "path": str(TRIAL_LEDGER.relative_to(REPO_ROOT)),
            "sha256": _sha256(TRIAL_LEDGER),
        },
        "terminal_bindings": {
            "development_survivors": {
                "path": str(SURVIVORS.relative_to(REPO_ROOT)),
                "sha256": _sha256(SURVIVORS),
            },
            "exposed_stress_consumption_record": {
                "path": str(STRESS_RECORD.relative_to(REPO_ROOT)),
                "sha256": _sha256(STRESS_RECORD),
            },
            "campaign_report": {
                "path": str(CAMPAIGN_REPORT.relative_to(REPO_ROOT)),
                "sha256": _sha256(CAMPAIGN_REPORT),
            },
        },
        "previous_entry_sha256": predecessor["chain_tip_sha256"],
    }
    entry["entry_sha256"] = _entry_hash(entry)
    return {
        "schema_version": 8,
        "kind": "a_share_three_day_walkforward_campaign263_append_only_research_attempt_ledger",
        "status": "campaign263_terminal_twenty_infrastructure_failures_eight_prevalue_routes_one_return_reading_development_trial_zero_survivors_stress_closed",
        "recorded_at": "2026-08-16T14:10:00Z",
        "timestamp_semantics": "monotonic logical append time after the sole frozen development trial and before any terminal policy publication",
        "chain_hash_algorithm": "sha256_of_canonical_json_without_entry_sha256",
        "authoritative_predecessor": {
            "path": str(PREDEVELOPMENT.relative_to(REPO_ROOT)),
            "sha256": _sha256(PREDEVELOPMENT),
            "effective_entry_count": predecessor["effective_entry_count"],
            "chain_tip_sha256": predecessor["chain_tip_sha256"],
            "cumulative_historical_research_attempt_count": predecessor[
                "cumulative_historical_research_attempt_count"
            ],
            "cumulative_return_reading_development_trial_count": predecessor[
                "cumulative_return_reading_development_trial_count"
            ],
        },
        "delta_entries": [entry],
        "effective_entry_count": 29,
        "effective_infrastructure_failure_attempt_count": 20,
        "effective_prevalue_scientific_attempt_count": 8,
        "effective_complete_factor_attempt_count": 1,
        "effective_return_reading_development_trial_count": 1,
        "cumulative_historical_research_attempt_count": 2592,
        "cumulative_return_reading_development_trial_count": 315,
        "library_state": {
            "complete_definition_appended_once": True,
            "complete_factor_definition_count": 162,
            "complete_factor_definition_order_sha256": "974f2c1f16a85eb43a0bd1e8db768dbe120cd8826c1754d5f220bf9f1d4a3ea0",
            "numeric_comparator_appended_after_all_142_uniqueness_gates": True,
            "eligible_numeric_comparator_count": 143,
            "eligible_numeric_comparator_order_sha256": "f4fbf3d578e2c80c29425716a30d60a3df01d67d04e37f1651236c4dff899588",
        },
        "research_boundary": {
            "candidate_snapshot_values_read": True,
            "numeric_comparator_values_read": True,
            "historical_2019_2023_daily_price_or_forward_return_values_read": True,
            "return_reading_development_trial_count": 1,
            "stress_2024_2025_opened": False,
            "provider_or_web_request_issued": False,
            "provider_credential_presence_value_or_digest_read": False,
            "candidate49_plan_or_run_executed": False,
            "candidate49_historical_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "second_prospective_candidate_created": False,
            "current_scoring_selection_sizing_positions_or_orders_performed": False,
            "investment_advice": False,
        },
        "candidate49": predecessor["candidate49"],
        "chain_tip_sha256": entry["entry_sha256"],
    }


def main() -> int:
    value = build()
    OUTPUT.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"path": str(OUTPUT), "sha256": _sha256(OUTPUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

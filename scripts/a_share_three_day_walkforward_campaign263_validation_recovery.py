#!/usr/bin/env python3
"""Append Campaign263's failed first terminal regression."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v9.json"
)
FAILURE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_deselect_failure_20260816.json"
)
OUTPUT = PREDECESSOR.with_name("research_attempt_ledger_v10.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict[str, Any]) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    payload = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    prior = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if (
        _sha256(PREDECESSOR)
        != "dea448279b10f0321a4d250e3dc870529a17136b7304fae5b17ba9759b4d07c0"
    ):
        raise RuntimeError("Campaign263 terminal ledger v9 changed")
    entry: dict[str, Any] = {
        "ordinal": 31,
        "attempt_id": "campaign263_infrastructure_022",
        "attempt_class": "infrastructure_failure",
        "phase": "focused_terminal_regression",
        "status": "failed_45_passed_1_failed_pre_activation_only_test_not_deselected",
        "scientific_attempt": False,
        "result_consumed": False,
        "artifact": {
            "path": str(FAILURE.relative_to(REPO_ROOT)),
            "sha256": _sha256(FAILURE),
        },
        "previous_entry_sha256": prior["chain_tip_sha256"],
    }
    entry["entry_sha256"] = _entry_hash(entry)
    value = {
        "schema_version": 10,
        "kind": "a_share_three_day_walkforward_campaign263_append_only_research_attempt_ledger",
        "status": "campaign263_terminal_validation_recovery_twenty_two_infrastructure_failures_zero_survivors_stress_closed",
        "recorded_at": "2026-08-16T14:23:00Z",
        "chain_hash_algorithm": "sha256_of_canonical_json_without_entry_sha256",
        "authoritative_predecessor": {
            "path": str(PREDECESSOR.relative_to(REPO_ROOT)),
            "sha256": _sha256(PREDECESSOR),
            "effective_entry_count": prior["effective_entry_count"],
            "chain_tip_sha256": prior["chain_tip_sha256"],
            "cumulative_historical_research_attempt_count": prior[
                "cumulative_historical_research_attempt_count"
            ],
            "cumulative_return_reading_development_trial_count": prior[
                "cumulative_return_reading_development_trial_count"
            ],
        },
        "delta_entries": [entry],
        "effective_entry_count": 31,
        "effective_infrastructure_failure_attempt_count": 22,
        "effective_prevalue_scientific_attempt_count": 8,
        "effective_complete_factor_attempt_count": 1,
        "effective_return_reading_development_trial_count": 1,
        "cumulative_historical_research_attempt_count": 2594,
        "cumulative_return_reading_development_trial_count": 315,
        "library_state": prior["library_state"],
        "research_boundary": prior["research_boundary"],
        "candidate49": prior["candidate49"],
        "chain_tip_sha256": entry["entry_sha256"],
    }
    OUTPUT.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"path": str(OUTPUT), "sha256": _sha256(OUTPUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

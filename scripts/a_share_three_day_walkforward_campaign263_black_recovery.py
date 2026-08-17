#!/usr/bin/env python3
"""Append Campaign263's terminal Black-check failure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRIOR = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v10.json"
)
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_black_failure_20260816.json"
)
OUTPUT = PRIOR.with_name("research_attempt_ledger_v11.json")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict[str, Any]) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    return hashlib.sha256(
        json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def main() -> int:
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    if (
        _sha(PRIOR)
        != "1b5d08d4b5062b442b741c5e57363107296923eee5581cfb7858d0ab5135470d"
    ):
        raise RuntimeError("Campaign263 ledger v10 changed")
    entry: dict[str, Any] = {
        "ordinal": 32,
        "attempt_id": "campaign263_infrastructure_023",
        "attempt_class": "infrastructure_failure",
        "phase": "terminal_static_validation",
        "status": "black_check_terminal_test_would_reformat",
        "scientific_attempt": False,
        "result_consumed": False,
        "artifact": {"path": str(FAILURE.relative_to(ROOT)), "sha256": _sha(FAILURE)},
        "previous_entry_sha256": prior["chain_tip_sha256"],
    }
    entry["entry_sha256"] = _entry_hash(entry)
    value = {
        "schema_version": 11,
        "kind": "a_share_three_day_walkforward_campaign263_append_only_research_attempt_ledger",
        "status": "campaign263_terminal_static_recovery_twenty_three_infrastructure_failures_zero_survivors_stress_closed",
        "recorded_at": "2026-08-16T14:29:00Z",
        "chain_hash_algorithm": "sha256_of_canonical_json_without_entry_sha256",
        "authoritative_predecessor": {
            "path": str(PRIOR.relative_to(ROOT)),
            "sha256": _sha(PRIOR),
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
        "effective_entry_count": 32,
        "effective_infrastructure_failure_attempt_count": 23,
        "effective_prevalue_scientific_attempt_count": 8,
        "effective_complete_factor_attempt_count": 1,
        "effective_return_reading_development_trial_count": 1,
        "cumulative_historical_research_attempt_count": 2595,
        "cumulative_return_reading_development_trial_count": 315,
        "library_state": prior["library_state"],
        "research_boundary": prior["research_boundary"],
        "candidate49": prior["candidate49"],
        "chain_tip_sha256": entry["entry_sha256"],
    }
    OUTPUT.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"path": str(OUTPUT), "sha256": _sha(OUTPUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Append Campaign263's post-Black patch-context failure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRIOR = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v11.json"
)
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_post_black_patch_failure_20260816.json"
)
OUTPUT = PRIOR.with_name("research_attempt_ledger_v12.json")


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
        != "fabbfa757863f8389ed30c55a3b7a5f8c1f73267167ad1b7b7678bd38a73bb5e"
    ):
        raise RuntimeError("Campaign263 ledger v11 changed")
    entry: dict[str, Any] = {
        "ordinal": 33,
        "attempt_id": "campaign263_infrastructure_024",
        "attempt_class": "infrastructure_failure",
        "phase": "post_black_terminal_authority_update",
        "status": "failed_apply_patch_pre_black_assertion_context_without_file_change",
        "scientific_attempt": False,
        "result_consumed": False,
        "artifact": {"path": str(FAILURE.relative_to(ROOT)), "sha256": _sha(FAILURE)},
        "previous_entry_sha256": prior["chain_tip_sha256"],
    }
    entry["entry_sha256"] = _entry_hash(entry)
    value = {
        "schema_version": 12,
        "kind": "a_share_three_day_walkforward_campaign263_append_only_research_attempt_ledger",
        "status": "campaign263_terminal_patch_recovery_twenty_four_infrastructure_failures_zero_survivors_stress_closed",
        "recorded_at": "2026-08-16T14:34:00Z",
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
        "effective_entry_count": 33,
        "effective_infrastructure_failure_attempt_count": 24,
        "effective_prevalue_scientific_attempt_count": 8,
        "effective_complete_factor_attempt_count": 1,
        "effective_return_reading_development_trial_count": 1,
        "cumulative_historical_research_attempt_count": 2596,
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

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_campaign069_status_is_terminal_after_the_only_authorized_trial() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "scripts.a_share_three_day_walkforward_campaign069", "status"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    status = json.loads(result.stdout)
    assert status["expected_trial_count"] == 1
    assert status["ledger_entry_count"] == 1
    assert status["selected_survivor_count"] == 0
    assert status["stress_intent_exists"] is False
    assert status["stress_record_exists"] is True
    assert status["stress_status"] == "not_opened_zero_development_survivors"
    assert status["candidate49_historical_return_read"] is False
    assert status["current_scoring_selection_sizing_or_orders_allowed"] is False

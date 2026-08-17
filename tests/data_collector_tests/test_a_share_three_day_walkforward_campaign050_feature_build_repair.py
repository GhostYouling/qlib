from __future__ import annotations

import json
import subprocess
import sys


def _run_isolated(source: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-c", source],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_campaign050_empty_joint_base_returns_canonical_empty_partition() -> None:
    result = _run_isolated(
        """
import json
import pandas as pd
import scripts.a_share_three_day_walkforward_campaign050_features_v3 as entry

runner = entry.runner
raw = pd.DataFrame(columns=runner.RAW_COLUMNS)
base = pd.DataFrame(columns=runner.BASE_COLUMNS)
frame, quality = runner.compute_partition_frame(
    raw, base, None, symbol="SH600145"
)
print(json.dumps({
    "columns": list(frame.columns),
    "rows": len(frame),
    "quality": quality,
}))
"""
    )
    assert result == {
        "columns": [
            "trade_date",
            "symbol",
            "provider",
            "intraday_half_session_extreme_shock_reversal_completion_2h",
            "intraday_half_session_extreme_shock_reversal_completion_2h_eligible",
        ],
        "rows": 0,
        "quality": {"base_rows": 0},
    }


def test_campaign050_repair_wrapper_binds_frozen_entrypoint_and_authorization() -> None:
    result = _run_isolated(
        """
import json
import scripts.a_share_three_day_walkforward_campaign050_features_v3 as entry

runner = entry.runner
print(json.dumps({
    "frozen_entrypoint": runner._sha256(runner.Path(entry.frozen.__file__).resolve()),
    "repair_authorization": runner._sha256(entry.REPAIR_AUTHORIZATION),
    "implementation_freeze_bound": bool(runner.IMPLEMENTATION_FREEZE_SHA256),
    "source_fields": list(runner.RAW_COLUMNS),
}))
"""
    )
    assert result == {
        "frozen_entrypoint": "f450a953e44f4a9fd325d1aea7dc113dbd84fa9079761079ac6a1fa9a3292b97",
        "repair_authorization": "4e514d9283ffd2e3878aa0b9d7bf0625ca45f3b13b8f08ab006f934667ea5443",
        "implementation_freeze_bound": True,
        "source_fields": ["datetime", "symbol", "provider", "close"],
    }

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign288_recovery as recovery


def test_factor_frame_preserves_precomputed_ordinals_without_reranking() -> None:
    identities = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-01", "2020-01-01"]),
            "instrument": ["SZ000001", "SZ000002"],
        }
    )
    matrix = np.zeros((2, 158), dtype=np.float32)
    matrix[:, 0] = [-0.4, 0.3]
    eligible = np.asarray([True, False])

    frame = recovery.factor_frame(identities, matrix, eligible)

    assert frame["alpha158_000"].tolist() == matrix[:, 0].tolist()
    assert frame["model_support_eligible"].tolist() == [True, False]


def test_original_failure_is_preserved_and_bound() -> None:
    recovery.validate_failure_bindings()

    failure = recovery.campaign.load_json(recovery.ORIGINAL_FAILURE_PATH)
    assert failure["error"] == "training projection center differs from zero-return design"
    assert not failure["lockbox_2024_2025_return_fields_read"]

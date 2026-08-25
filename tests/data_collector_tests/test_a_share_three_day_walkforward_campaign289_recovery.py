from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign289 as campaign
from scripts import a_share_three_day_walkforward_campaign289_recovery as recovery


def test_failure_bindings_preserve_original_root() -> None:
    recovery.validate_failure_bindings()


def test_factor_frame_preserves_frozen_binary_states() -> None:
    identities = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02", "2020-01-02"]),
            "instrument": ["sh600000", "sz000001"],
        }
    )
    matrix = np.zeros((2, campaign.FEATURE_COUNT), dtype=np.float32)
    matrix[0, 0] = -1.0
    matrix[1, 0] = 1.0
    eligible = np.asarray([True, False])

    frame = recovery.factor_frame(identities, matrix, eligible)

    assert frame["alpha158_000"].tolist() == [-1.0, 1.0]
    assert frame["model_support_eligible"].tolist() == [True, False]
    assert (
        len([column for column in frame if column.startswith("alpha158_")])
        == campaign.FEATURE_COUNT
    )


def test_recovery_is_bounded_to_peer_set_ordering() -> None:
    failure = campaign.load_json(recovery.FAILURE_RECORD_PATH)
    rule = failure["bounded_recovery_rule"]
    assert rule["fold1_training_return_reread_required"] is True
    assert (
        rule[
            "sample_keys_hash_bits_hyperplanes_bit_rule_cell_estimator_target_costs_folds_and_survivor_gates_unchanged"
        ]
        is True
    )
    assert rule["new_hyperparameter_or_return_driven_change_allowed"] is False

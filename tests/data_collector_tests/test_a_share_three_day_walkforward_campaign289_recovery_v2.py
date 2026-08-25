from __future__ import annotations

import numpy as np

from scripts import a_share_three_day_walkforward_campaign289 as campaign
from scripts import a_share_three_day_walkforward_campaign289_recovery_v2 as recovery


def test_recovery_v1_failure_bindings_are_immutable() -> None:
    recovery.validate_v1_failure_bindings()


def test_neutralize_ineligible_rows_changes_only_ineligible_rows() -> None:
    matrix = np.zeros((3, campaign.FEATURE_COUNT), dtype=np.float32)
    matrix[0] = -1.0
    matrix[1] = 1.0
    matrix[2] = np.nan
    eligible = np.asarray([True, True, False])
    before = matrix[eligible].copy()

    stats = recovery.neutralize_ineligible_rows(matrix, eligible)

    assert np.array_equal(matrix[eligible], before)
    assert np.all(matrix[~eligible] == 0.0)
    assert stats["eligible_values_changed"] is False
    assert stats["nonfinite_ineligible_cells_replaced"] == campaign.FEATURE_COUNT


def test_recovery_v2_change_is_frozen_to_non_support_fill() -> None:
    failure = campaign.load_json(recovery.FAILURE_V2_RECORD_PATH)
    rule = failure["bounded_recovery_v2_rule"]
    assert rule["eligible_row_binary_state_or_cell_change_allowed"] is False
    assert rule["fold1_training_return_reread_required"] is True
    assert (
        rule[
            "sample_keys_hash_bits_hyperplanes_bit_rule_cell_estimator_target_costs_folds_and_survivor_gates_unchanged"
        ]
        is True
    )
    assert rule["new_hyperparameter_or_return_driven_change_allowed"] is False

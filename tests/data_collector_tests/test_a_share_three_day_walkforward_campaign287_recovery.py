from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign287_recovery as recovery


def test_fold1_model_loads_without_refit_or_training_return_read() -> None:
    model = recovery.load_fold1_model()

    prediction = model.predict(
        np.zeros((3, recovery.campaign.FEATURE_COUNT), dtype=np.float32)
    )

    assert np.isfinite(prediction).all()
    assert model.loss_curve_ is not None
    assert len(model.loss_curve_) == recovery.campaign.MODEL_PARAMETERS["epochs"]


def test_repaired_datetimeindex_comparison_is_elementwise() -> None:
    dates = pd.DatetimeIndex(["2021-01-04", "2021-01-05"]).normalize()

    mask = dates == pd.Timestamp("2021-01-05")

    assert mask.tolist() == [False, True]


def test_infrastructure_entry_preserves_no_validation_read() -> None:
    entry = recovery.infrastructure_entry()

    assert entry["attempt_id"] == "c287_infra_01"
    assert entry["fold1_training_return_fields_read"]
    assert not entry["validation_return_fields_read_before_failure"]
    assert not entry["scientific_result_changed"]


def test_recovery_artifacts_are_exactly_bound() -> None:
    recovery.validate_artifacts()

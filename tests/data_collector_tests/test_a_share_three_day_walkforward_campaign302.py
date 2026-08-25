from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign302 as campaign


def test_complete_alpha360_library_keeps_frozen_order_and_count() -> None:
    fields, names = campaign.alpha360_config()

    assert len(fields) == len(names) == campaign.FEATURE_COUNT
    assert campaign.canonical_feature_library_sha256() == campaign.ALPHA360_LIBRARY_SHA256
    assert names[:2] == ["CLOSE59", "CLOSE58"]
    assert names[-2:] == ["VOLUME1", "VOLUME0"]


def test_deterministic_sample_is_stable_and_precedes_feature_values() -> None:
    sessions = pd.date_range("2020-01-02", periods=60, freq="B")
    rows: list[dict[str, object]] = []
    for session_number, session in enumerate(sessions):
        for instrument_number in range(70):
            rows.append(
                {
                    "trade_date": session,
                    "instrument": f"SH{600000 + instrument_number:06d}",
                    "stock_day_key": session_number * 100 + instrument_number,
                }
            )
    identities = pd.DataFrame(rows)
    eligible = np.ones(len(identities), dtype=bool)

    first, first_stats = campaign.deterministic_sample(identities, eligible)
    second, second_stats = campaign.deterministic_sample(identities, eligible)

    assert first.equals(second)
    assert first_stats == second_stats
    assert first.groupby("trade_date").size().eq(campaign.SAMPLE_SIZE_PER_SESSION).all()
    assert first_stats["sampled_rows"] == 60 * campaign.SAMPLE_SIZE_PER_SESSION
    assert first_stats["minimum_base_eligible_names"] == 70


def test_frozen_preprocessing_is_finite_clipped_and_missing_filled() -> None:
    generator = np.random.default_rng(302)
    matrix = generator.normal(size=(1024, campaign.FEATURE_COUNT)).astype(np.float32)
    matrix[0, 0] = np.nan
    matrix[1, 1] = np.inf
    matrix[2, 2] = -np.inf
    matrix[3, 3] = 1e9

    centers, scales, statistics = campaign.preprocessing_statistics(matrix)
    transformed = campaign.transform_features(matrix, centers, scales)

    assert centers.shape == scales.shape == (campaign.FEATURE_COUNT,)
    assert transformed.shape == matrix.shape
    assert np.isfinite(transformed).all()
    assert transformed.min() >= -8.0
    assert transformed.max() <= 8.0
    assert transformed[0, 0] == 0.0
    assert statistics["minimum_finite_observations_per_feature"] >= 1023
    assert statistics["clip"] == [-8.0, 8.0]


def test_protocol_keeps_one_model_three_folds_and_closed_lockbox() -> None:
    protocol = json.loads(campaign.PROTOCOL_PATH.read_text(encoding="utf-8"))

    assert protocol["model_trial"]["configuration_count"] == 1
    assert protocol["model_trial"]["trial_id"] == campaign.TRIAL_ID
    assert protocol["complete_feature_library"]["feature_count"] == 360
    assert len(protocol["walkforward_folds"]) == 3
    assert protocol["locked_2024_2025_campaign_backtest"]["initially_closed"] is True
    assert protocol["research_boundary"]["provider_request_issued"] is False
    assert protocol["research_boundary"]["candidate49_ledgers_changed"] is False


def test_append_only_ledger_keeps_all_concepts_failures_and_model_trial() -> None:
    ledger = campaign.build_ledger(
        {
            "attempt_id": campaign.TRIAL_ID,
            "status": "synthetic_test_only",
            "historical_return_value_read": False,
        }
    )

    assert ledger["entry_count"] == 11
    assert ledger["prevalue_concept_attempt_count"] == 8
    assert ledger["infrastructure_failure_attempt_count"] == 2
    assert ledger["model_trial_attempt_count"] == 1
    assert ledger["entries"][0]["previous_entry_sha256"] == campaign.CHAIN_GENESIS
    for previous, current in zip(ledger["entries"], ledger["entries"][1:]):
        assert current["previous_entry_sha256"] == previous["entry_sha256"]


def test_fixed_torch_worker_trains_and_scores_without_validation_feedback(
    tmp_path: Path,
) -> None:
    generator = np.random.default_rng(302)
    matrix = generator.normal(size=(1024, campaign.FEATURE_COUNT)).astype(np.float32)
    target = generator.uniform(size=1024).astype(np.float32)
    weight = np.full(1024, 1.0 / 1024.0, dtype=np.float32)
    input_path = tmp_path / "training.npz"
    model_path = tmp_path / "model.pt"
    report_path = tmp_path / "training_report.json"
    score_input_path = tmp_path / "score.npy"
    score_output_path = tmp_path / "scores.npy"
    campaign.atomic_npz(input_path, matrix=matrix, target=target, weight=weight)

    trained = campaign.run_worker(
        [
            "train",
            "--input",
            str(input_path),
            "--model",
            str(model_path),
            "--report",
            str(report_path),
        ]
    )
    campaign.atomic_npy(score_input_path, matrix[:19])
    scored = campaign.run_worker(
        [
            "score",
            "--input",
            str(score_input_path),
            "--model",
            str(model_path),
            "--output",
            str(score_output_path),
        ]
    )
    predictions = np.load(score_output_path, allow_pickle=False)

    assert trained["epochs"] == 5
    assert trained["validation_return_feedback_used"] is False
    assert len(trained["loss_curve"]) == 5
    assert scored["rows"] == 19
    assert predictions.shape == (19,)
    assert np.isfinite(predictions).all()

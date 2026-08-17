import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign134 as campaign


def test_protocol_binding_and_single_graph_configuration_are_exact() -> None:
    assert campaign.base.file_sha256(campaign.PROTOCOL_PATH) == campaign.PROTOCOL_SHA256
    protocol = campaign.base.load_json(campaign.PROTOCOL_PATH)
    assert [item["trial_id"] for item in protocol["trial_catalog"]] == [
        campaign.TRIAL_ID
    ]
    assert protocol["search_multiplicity"]["positive_correlation_threshold"] == 0.8
    assert protocol["frozen_graph_fit"]["return_or_target_fields_used"] is False
    assert (
        protocol["frozen_score_algorithm"]["negative_or_zero_source_weights"] is False
    )


def test_connected_components_use_positive_threshold_and_deterministic_chaining() -> (
    None
):
    size = campaign.design.FEATURE_COUNT
    correlations = np.full((size, size), np.nan)
    counts = np.zeros((size, size), dtype=np.uint16)
    np.fill_diagonal(correlations, 1.0)
    np.fill_diagonal(counts, 120)
    correlations[0, 1] = correlations[1, 0] = 0.81
    correlations[1, 2] = correlations[2, 1] = 0.80
    correlations[2, 3] = correlations[3, 2] = -0.99
    counts[0, 1] = counts[1, 0] = 120
    counts[1, 2] = counts[2, 1] = 120
    counts[2, 3] = counts[3, 2] = 120
    components, edges = campaign.connected_components(correlations, counts)
    assert components[0] == [0, 1, 2]
    assert components[1] == [3]
    assert edges == [(0, 1), (1, 2)]


def test_component_weights_preserve_every_feature_and_equalize_components() -> None:
    components = [[0, 1], [2], *[[index] for index in range(3, 140)]]
    weights = campaign.component_weights(components)
    assert np.all(weights > 0.0)
    assert np.isclose(weights.sum(), 1.0)
    assert np.isclose(weights[0] + weights[1], weights[2])
    assert weights[0] == weights[1]


def test_fit_graph_groups_identical_but_not_reversed_features() -> None:
    rng = np.random.default_rng(134)
    session_rows = 10
    sessions = 3
    values = rng.uniform(size=(session_rows * sessions, campaign.design.FEATURE_COUNT))
    for session in range(sessions):
        positions = slice(session * session_rows, (session + 1) * session_rows)
        base = np.linspace(0.0, 1.0, session_rows)
        values[positions, 0] = base
        values[positions, 1] = base
        values[positions, 2] = base[::-1]
    dates = np.repeat(pd.date_range("2020-01-01", periods=sessions), session_rows)
    graph, medians, counts = campaign.fit_graph(
        dates,
        values,
        minimum_names=5,
        minimum_sessions=3,
        threshold=0.8,
    )
    component_for_zero = next(group for group in graph["components"] if 0 in group)
    assert 1 in component_for_zero
    assert 2 not in component_for_zero
    assert medians[0, 1] == 1.0
    assert medians[0, 2] == -1.0
    assert counts[0, 1] == 3
    assert graph["return_or_target_fields_used"] is False


def test_graph_scores_use_neutral_fill_and_ineligible_nan() -> None:
    components = [[index] for index in range(campaign.design.FEATURE_COUNT)]
    matrix = np.full((2, campaign.design.FEATURE_COUNT), 0.5)
    matrix[0, 0] = np.nan
    scores = campaign.graph_scores(
        components, matrix, np.array([True, False], dtype=bool)
    )
    assert np.isclose(scores[0], 0.5)
    assert np.isnan(scores[1])


def test_campaign134_runner_has_no_lockbox_command() -> None:
    parser = campaign.parser()
    actions = next(
        action for action in parser._actions if getattr(action, "choices", None)
    )
    assert set(actions.choices) == {"status", "plan", "run-development"}

from __future__ import annotations

import hashlib
import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign120_formula as formula


def _reference_phrase_count(symbols: tuple[int, ...]) -> int:
    dictionary: set[tuple[int, ...]] = set()
    cursor = 0
    count = 0
    while cursor < len(symbols):
        length = 0
        while (
            cursor + length < len(symbols)
            and symbols[cursor : cursor + length + 1] in dictionary
        ):
            length += 1
        if cursor + length < len(symbols):
            dictionary.add(symbols[cursor : cursor + length + 1])
            cursor += length + 1
        else:
            cursor = len(symbols)
        count += 1
    return count


def test_frozen_protocol_binding_and_single_search_choice() -> None:
    spec = formula.load_protocol()
    assert hashlib.sha256(formula.PROTOCOL_PATH.read_bytes()).hexdigest() == (
        formula.PROTOCOL_SHA256
    )
    assert spec["candidate"]["name"] == formula.FACTOR_NAME
    assert spec["candidate"]["direction"] == formula.SCORE_DIRECTION
    assert spec["candidate"]["search_space"]["candidate_count"] == 1


def _closes_from_symbols(morning: list[int], afternoon: list[int]) -> np.ndarray:
    halves = []
    for symbols in (morning, afternoon):
        current = 100.0
        closes = [current]
        for symbol in symbols:
            current += float(symbol)
            closes.append(current)
        halves.extend(closes)
    return np.asarray([halves], dtype=np.float64)


def test_parser_matches_independent_reference_on_seeded_ternary_sequences() -> None:
    rng = np.random.default_rng(20260814)
    for _ in range(50):
        symbols = tuple(
            int(item)
            for item in rng.integers(-1, 2, size=formula.SYMBOL_COUNT_PER_HALF)
        )
        assert formula.dictionary_phrase_count(symbols) == _reference_phrase_count(
            symbols
        )


def test_constant_paths_are_valid_and_lunch_is_reset() -> None:
    closes = np.full((1, formula.SELECTED_BAR_COUNT), 100.0)
    scores, eligible, quality = formula.compute_direction_dictionary_phrase_count(
        closes
    )
    half_score = _reference_phrase_count((0,) * formula.SYMBOL_COUNT_PER_HALF)
    assert eligible.tolist() == [True]
    assert scores.tolist() == [float(2 * half_score)]
    assert quality["recognized_direction_symbol_observations"] == 238
    assert quality["exact_zero_direction_symbol_observations"] == 238


def test_longer_order_changes_score_despite_same_marginal_and_pair_counts() -> None:
    first = [-1, -1, -1, -1, -1, -1, 0, -1]
    second = [-1, -1, -1, -1, -1, 0, -1, -1]
    shared_suffix = [-1] * 7
    first = first * 14 + shared_suffix
    second = second * 14 + shared_suffix
    assert sorted(first) == sorted(second)

    def pair_counts(values: list[int]) -> dict[tuple[int, int], int]:
        return {
            pair: sum(
                1 for left, right in zip(values, values[1:]) if (left, right) == pair
            )
            for pair in ((a, b) for a in formula.ALPHABET for b in formula.ALPHABET)
        }

    assert pair_counts(first) == pair_counts(second)
    assert formula.dictionary_phrase_count(first) != formula.dictionary_phrase_count(
        second
    )


def test_magnitude_changes_that_preserve_direction_leave_score_unchanged() -> None:
    morning = ([1, -1, 0, 1, 1, -1, 0] * 17)[:119]
    afternoon = ([-1, 0, 1, -1, 1, 0, 0] * 17)[:119]
    base = _closes_from_symbols(morning, afternoon)
    transformed = np.empty_like(base)
    transformed[0, :120] = np.exp(np.log(base[0, :120]) * 1.7)
    transformed[0, 120:] = np.exp(np.log(base[0, 120:]) * 0.8)
    first, _, _ = formula.compute_direction_dictionary_phrase_count(base)
    second, _, _ = formula.compute_direction_dictionary_phrase_count(transformed)
    assert first.tolist() == second.tolist()


def test_invalid_shape_values_and_alphabet_fail_closed() -> None:
    with pytest.raises(formula.Campaign120FormulaError, match="shape"):
        formula.compute_direction_dictionary_phrase_count(np.ones((1, 239)))
    invalid = np.ones((3, 240), dtype=np.float64)
    invalid[0, 10] = np.nan
    invalid[1, 10] = 0.0
    invalid[2, 10] = -1.0
    scores, eligible, quality = formula.compute_direction_dictionary_phrase_count(
        invalid
    )
    assert eligible.tolist() == [False, False, False]
    assert np.isnan(scores).all()
    assert quality["invalid_close_rows"] == 3
    with pytest.raises(formula.Campaign120FormulaError, match="119"):
        formula.dictionary_phrase_count([0] * 118)
    with pytest.raises(formula.Campaign120FormulaError, match="ternary"):
        formula.dictionary_phrase_count([0] * 118 + [2])

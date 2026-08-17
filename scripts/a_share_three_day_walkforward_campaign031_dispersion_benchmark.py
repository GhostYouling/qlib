#!/usr/bin/env python3
"""Build Campaign031's deterministic no-return market-dispersion benchmark."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gc
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_tushare_intraday_market_idiosyncratic_share as market
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_tushare_intraday_market_idiosyncratic_share as market


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_031_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
PROTOCOL_SHA256 = (
    "95951a357ffef3eee46f8d220d150fd00223b32f27f6cf93a92c4f6c17452f6d"
)
SOURCE_RUN_ID = market.SOURCE_RUN_ID
OUTPUT_RUN_ID = (
    f"{SOURCE_RUN_ID}_walkforward_campaign031_dispersion_benchmark_v1"
)
BENCHMARK_FILENAME = "market_dispersion_benchmark_238m.parquet"
BENCHMARK_COLUMNS = (
    "trade_date",
    "return_position",
    "return_sum",
    "return_sum_squares",
    "valid_stock_count",
)
RETURN_POSITIONS = 238
EXPECTED_PARTITIONS = 33_015
EXPECTED_SYMBOLS = 5_396
EXPECTED_TRADE_DATES = 1_699

# Bound after the first deterministic build and before any candidate value.
BENCHMARK_MANIFEST_SHA256 = (
    "bbb82784b4daa21080045a17239868b1063d233607f125d03acab2aefb4fee50"
)
BENCHMARK_BYTE_SHA256 = (
    "317aa3cb1793498bbce03018b692e6252939e689f0b9982e7c991a0da82d8827"
)
BENCHMARK_FRAME_SHA256 = (
    "c4933078610a4a14597a35d54ac98f9089a90522b73d8d428cde9e5eec79201f"
)


class Campaign031DispersionBenchmarkError(RuntimeError):
    """Fail-closed error for the Campaign031 dispersion benchmark."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/"
        "minute_walkforward_campaign031_dispersion_benchmark"
        / OUTPUT_RUN_ID
    )


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the complete frozen chain before opening a source partition."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign031DispersionBenchmarkError(
            "Campaign031 no-return protocol changed"
        )
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign031DispersionBenchmarkError(
            "Campaign031 no-return protocol has a failed file binding"
        )
    spec = json.loads(path.read_text(encoding="utf-8"))
    benchmark = spec.get("dispersion_benchmark") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign031_no_return_preregistration"
        and spec.get("status")
        == (
            "frozen_before_campaign031_dispersion_benchmark_candidate_"
            "comparison_or_return_values"
        )
        and tuple(benchmark.get("columns") or ()) == BENCHMARK_COLUMNS
        and tuple(benchmark.get("source_fields_allowed") or ())
        == market.RAW_COLUMNS
        and benchmark.get("return_positions_per_date") == RETURN_POSITIONS
        and benchmark.get("standalone_0930_excluded") is True
        and benchmark.get("lunch_transition_excluded") is True
        and benchmark.get("daily_price_fields_read") is False
        and benchmark.get("comparison_values_read") is False
        and benchmark.get("forward_returns_read") is False
        and benchmark.get("provider_request_allowed") is False
        and boundary.get(
            "binding_validation_required_before_dispersion_benchmark_or_"
            "candidate_values"
        )
        is True
        and boundary.get("provider_request_allowed") is False
    ):
        raise Campaign031DispersionBenchmarkError(
            "Campaign031 dispersion benchmark semantics changed"
        )
    return spec


def _accumulator_path(partial_root: Path) -> Path:
    return partial_root / ".metadata/dispersion_accumulator.npz"


def _write_accumulator(
    path: Path,
    *,
    dates: pd.DatetimeIndex,
    return_sums: np.ndarray,
    return_sum_squares: np.ndarray,
    valid_counts: np.ndarray,
    processed_symbols: set[str],
    invalid_stock_days: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.npz")
    np.savez_compressed(
        temporary,
        schema_version=np.array([1], dtype=np.int16),
        protocol_sha256=np.array([PROTOCOL_SHA256]),
        raw_manifest_sha256=np.array([market.RAW_MANIFEST_SHA256]),
        joint_manifest_sha256=np.array([market.JOINT_MANIFEST_SHA256]),
        dates=dates.to_numpy(dtype="datetime64[ns]"),
        return_sums=return_sums,
        return_sum_squares=return_sum_squares,
        valid_counts=valid_counts,
        processed_symbols=np.array(sorted(processed_symbols), dtype="U16"),
        invalid_stock_days=np.array([invalid_stock_days], dtype=np.int64),
    )
    temporary.replace(path)


def _load_accumulator(
    path: Path,
    dates: pd.DatetimeIndex,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, set[str], int]:
    shape = (len(dates), RETURN_POSITIONS)
    if not path.is_file():
        return (
            np.zeros(shape, dtype=np.float64),
            np.zeros(shape, dtype=np.float64),
            np.zeros(shape, dtype=np.int32),
            set(),
            0,
        )
    try:
        with np.load(path, allow_pickle=False) as state:
            observed_dates = state["dates"].astype("datetime64[ns]")
            sums = state["return_sums"].astype(np.float64, copy=True)
            sum_squares = state["return_sum_squares"].astype(
                np.float64, copy=True
            )
            counts = state["valid_counts"].astype(np.int32, copy=True)
            processed = {
                str(value) for value in state["processed_symbols"].tolist()
            }
            invalid = int(state["invalid_stock_days"].tolist()[0])
            valid = (
                state["schema_version"].tolist() == [1]
                and state["protocol_sha256"].tolist() == [PROTOCOL_SHA256]
                and state["raw_manifest_sha256"].tolist()
                == [market.RAW_MANIFEST_SHA256]
                and state["joint_manifest_sha256"].tolist()
                == [market.JOINT_MANIFEST_SHA256]
                and np.array_equal(
                    observed_dates, dates.to_numpy(dtype="datetime64[ns]")
                )
                and sums.shape == shape
                and sum_squares.shape == shape
                and counts.shape == shape
                and np.isfinite(sums).all()
                and np.isfinite(sum_squares).all()
                and (sum_squares >= 0.0).all()
                and (counts >= 0).all()
                and invalid >= 0
            )
    except (OSError, ValueError, KeyError, IndexError) as exc:
        raise Campaign031DispersionBenchmarkError(
            f"dispersion accumulator is unreadable: {path}"
        ) from exc
    if not valid:
        raise Campaign031DispersionBenchmarkError(
            f"dispersion accumulator changed: {path}"
        )
    return sums, sum_squares, counts, processed, invalid


def accumulate_returns(
    *,
    indices: np.ndarray,
    returns: np.ndarray,
    return_sums: np.ndarray,
    return_sum_squares: np.ndarray,
    valid_counts: np.ndarray,
) -> int:
    """Accumulate only complete return vectors in deterministic caller order."""

    indices = np.asarray(indices, dtype=np.int64)
    returns = np.asarray(returns, dtype=np.float64)
    if (
        returns.ndim != 2
        or returns.shape[1] != RETURN_POSITIONS
        or indices.shape != (len(returns),)
    ):
        raise Campaign031DispersionBenchmarkError(
            "dispersion contribution shapes changed"
        )
    valid = np.isfinite(returns).all(axis=1)
    if valid.any():
        rows = indices[valid]
        values = returns[valid]
        return_sums[rows, :] += values
        return_sum_squares[rows, :] += values * values
        valid_counts[rows, :] += 1
    return int((~valid).sum())


def _validate_published_manifest(
    manifest: dict[str, Any],
    *,
    require_bound_fingerprints: bool,
) -> None:
    evidence = manifest.get("benchmark") or {}
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign031_dispersion_benchmark"
        and manifest.get("status")
        == "complete_pending_fingerprint_freeze_before_candidate_values"
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("raw_manifest_sha256") == market.RAW_MANIFEST_SHA256
        and manifest.get("joint_manifest_sha256")
        == market.JOINT_MANIFEST_SHA256
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(market.RAW_COLUMNS)
        and manifest.get("source_open_high_low_volume_amount_read") is False
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("candidate_values_computed") is False
        and manifest.get("provider_request_issued") is False
        and evidence.get("columns") == list(BENCHMARK_COLUMNS)
        and evidence.get("rows") == EXPECTED_TRADE_DATES * RETURN_POSITIONS
        and evidence.get("trade_dates") == EXPECTED_TRADE_DATES
        and evidence.get("return_positions_per_date") == RETURN_POSITIONS
        and evidence.get("processed_symbol_count") == EXPECTED_SYMBOLS
        and evidence.get("valid_stock_count_minimum", 0) >= 51
    ):
        raise Campaign031DispersionBenchmarkError(
            "published dispersion benchmark semantics changed"
        )
    if require_bound_fingerprints and not (
        BENCHMARK_MANIFEST_SHA256
        and BENCHMARK_BYTE_SHA256
        and BENCHMARK_FRAME_SHA256
        and evidence.get("output_byte_sha256") == BENCHMARK_BYTE_SHA256
        and evidence.get("output_frame_sha256") == BENCHMARK_FRAME_SHA256
    ):
        raise Campaign031DispersionBenchmarkError(
            "dispersion benchmark fingerprints are not bound"
        )


def build(*, data_root: Path, workers: int) -> Path:
    """Build only the frozen no-return dispersion benchmark."""

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    data_root = data_root.expanduser().resolve()
    spec = load_protocol()
    final_root = output_root(data_root)
    final_manifest = final_root / "snapshot_manifest.json"
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    if final_root.exists():
        if not final_manifest.is_file() or not BENCHMARK_MANIFEST_SHA256:
            raise Campaign031DispersionBenchmarkError(
                "published benchmark exists but its fingerprint is not bound"
            )
        if _sha256(final_manifest) != BENCHMARK_MANIFEST_SHA256:
            raise Campaign031DispersionBenchmarkError(
                "published dispersion benchmark manifest changed"
            )
        manifest = json.loads(final_manifest.read_text(encoding="utf-8"))
        _validate_published_manifest(
            manifest, require_bound_fingerprints=True
        )
        return final_manifest
    if shutil.disk_usage(data_root).free < 2 * 1024**3:
        raise Campaign031DispersionBenchmarkError(
            "external data root has less than 2 GiB free"
        )
    prior_spec = market.previous.load_preregistration()
    chain = market.previous.validate_external_chain(prior_spec, data_root)
    raw, joint, raw_manifest_path, joint_manifest_path = chain[:4]
    _, joint_by_key, by_symbol = market._partition_maps(raw, joint)
    if (
        len(joint_by_key) != EXPECTED_PARTITIONS
        or len(by_symbol) != EXPECTED_SYMBOLS
    ):
        raise Campaign031DispersionBenchmarkError(
            "Campaign031 source partition map changed"
        )
    dates = market._calendar_dates(spec)
    if len(dates) != EXPECTED_TRADE_DATES:
        raise Campaign031DispersionBenchmarkError(
            "Campaign031 frozen calendar length changed"
        )
    lock_path = (
        data_root / ".a_share_walkforward_campaign031_dispersion_benchmark.lock"
    )
    with market.foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        accumulator_path = _accumulator_path(partial_root)
        sums, sum_squares, counts, processed, invalid = _load_accumulator(
            accumulator_path, dates
        )
        if processed - set(by_symbol):
            raise Campaign031DispersionBenchmarkError(
                "dispersion accumulator contains unknown symbols"
            )
        date_to_index = {
            pd.Timestamp(value): index for index, value in enumerate(dates)
        }
        symbols = [
            symbol for symbol in sorted(by_symbol) if symbol not in processed
        ]
        batch_size = max(8, workers * 8)
        print(
            f"building Campaign031 dispersion benchmark for "
            f"{len(by_symbol):,} symbols; resumed={len(processed):,}",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=workers
        ) as pool:
            for offset in range(0, len(symbols), batch_size):
                batch = symbols[offset : offset + batch_size]
                results = list(
                    pool.map(
                        market._symbol_market_contribution,
                        [by_symbol[symbol] for symbol in batch],
                    )
                )
                for symbol, contribution_dates, returns, observed_invalid in (
                    results
                ):
                    try:
                        indices = np.fromiter(
                            (
                                date_to_index[
                                    pd.Timestamp(value).normalize()
                                ]
                                for value in contribution_dates
                            ),
                            dtype=np.int64,
                            count=len(contribution_dates),
                        )
                    except KeyError as exc:
                        raise Campaign031DispersionBenchmarkError(
                            "dispersion contribution date is outside the "
                            f"frozen calendar: {exc}"
                        ) from exc
                    counted_invalid = accumulate_returns(
                        indices=indices,
                        returns=returns,
                        return_sums=sums,
                        return_sum_squares=sum_squares,
                        valid_counts=counts,
                    )
                    if counted_invalid != int(observed_invalid):
                        raise Campaign031DispersionBenchmarkError(
                            f"return-validity count changed for {symbol}"
                        )
                    invalid += counted_invalid
                    processed.add(symbol)
                del results
                gc.collect()
                if (
                    (offset // batch_size + 1) % 5 == 0
                    or offset + batch_size >= len(symbols)
                ):
                    _write_accumulator(
                        accumulator_path,
                        dates=dates,
                        return_sums=sums,
                        return_sum_squares=sum_squares,
                        valid_counts=counts,
                        processed_symbols=processed,
                        invalid_stock_days=invalid,
                    )
                    print(
                        f"Campaign031 dispersion progress "
                        f"symbols={len(processed):,}/{len(by_symbol):,}",
                        flush=True,
                    )
        if processed != set(by_symbol):
            raise Campaign031DispersionBenchmarkError(
                "dispersion benchmark did not consume every source symbol"
            )
        nonempty = counts.max(axis=1) > 0
        if (
            int(nonempty.sum()) != EXPECTED_TRADE_DATES
            or not np.equal(counts, counts[:, :1]).all()
        ):
            raise Campaign031DispersionBenchmarkError(
                "dispersion benchmark date support or peer counts changed"
            )
        active_dates = dates[nonempty]
        active_sums = sums[nonempty]
        active_sum_squares = sum_squares[nonempty]
        active_counts = counts[nonempty]
        frame = pd.DataFrame(
            {
                "trade_date": np.repeat(
                    active_dates.to_numpy(), RETURN_POSITIONS
                ),
                "return_position": np.tile(
                    np.arange(RETURN_POSITIONS, dtype=np.int16),
                    len(active_dates),
                ),
                "return_sum": active_sums.reshape(-1),
                "return_sum_squares": active_sum_squares.reshape(-1),
                "valid_stock_count": active_counts.reshape(-1),
            }
        ).loc[:, BENCHMARK_COLUMNS]
        benchmark_path = partial_root / BENCHMARK_FILENAME
        market.foundation.atomic_write_frame(frame, benchmark_path)
        per_date_counts = active_counts[:, 0]
        evidence = {
            "path": str(final_root / BENCHMARK_FILENAME),
            "columns": list(BENCHMARK_COLUMNS),
            "rows": int(len(frame)),
            "trade_dates": int(len(active_dates)),
            "return_positions_per_date": RETURN_POSITIONS,
            "output_byte_sha256": _sha256(benchmark_path),
            "output_frame_sha256": market.foundation.frame_digest(frame),
            "valid_stock_count_minimum": int(per_date_counts.min()),
            "valid_stock_count_p05": float(
                np.quantile(per_date_counts, 0.05)
            ),
            "valid_stock_count_median": float(
                np.median(per_date_counts)
            ),
            "valid_stock_count_maximum": int(per_date_counts.max()),
            "invalid_complete_return_stock_days": int(invalid),
            "processed_symbol_count": int(len(processed)),
        }
        manifest = {
            "schema_version": 1,
            "kind": (
                "a_share_three_day_walkforward_campaign031_"
                "dispersion_benchmark"
            ),
            "status": (
                "complete_pending_fingerprint_freeze_before_candidate_values"
            ),
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
            "protocol_sha256": PROTOCOL_SHA256,
            "raw_manifest_path": str(raw_manifest_path),
            "raw_manifest_sha256": market.RAW_MANIFEST_SHA256,
            "joint_manifest_path": str(joint_manifest_path),
            "joint_manifest_sha256": market.JOINT_MANIFEST_SHA256,
            "output_run_id": OUTPUT_RUN_ID,
            "benchmark": evidence,
            "source_fields_read": list(market.RAW_COLUMNS),
            "source_open_high_low_volume_amount_read": False,
            "daily_price_fields_read": [],
            "comparison_factor_values_read": False,
            "forward_return_fields_read": False,
            "candidate_values_computed": False,
            "candidate49_historical_return_read": False,
            "candidate49_signal_or_execution_ledger_changed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "provider_request_issued": False,
            "accumulation_order": (
                "lexicographically_sorted_symbol_then_ascending_year_and_date"
            ),
            "population_denominator": "n",
            "bessel_correction_used": False,
        }
        _validate_published_manifest(
            manifest, require_bound_fingerprints=False
        )
        market.foundation.atomic_write_json(
            manifest, partial_root / "snapshot_manifest.json"
        )
        final_root.parent.mkdir(parents=True, exist_ok=True)
        partial_root.replace(final_root)
        return final_manifest


def status(data_root: Path) -> dict[str, Any]:
    root = output_root(data_root.expanduser().resolve())
    manifest = root / "snapshot_manifest.json"
    result: dict[str, Any] = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256": PROTOCOL_SHA256,
        "benchmark_manifest_path": str(manifest),
        "benchmark_exists": manifest.is_file(),
        "benchmark_fingerprints_bound": bool(
            BENCHMARK_MANIFEST_SHA256
            and BENCHMARK_BYTE_SHA256
            and BENCHMARK_FRAME_SHA256
        ),
        "candidate_values_computed": False,
        "forward_return_fields_read": False,
        "provider_request_issued": False,
    }
    if manifest.is_file():
        result["benchmark_manifest_observed_sha256"] = _sha256(manifest)
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    subparsers = value.add_subparsers(dest="command", required=True)
    for name in ("build", "status"):
        command = subparsers.add_parser(name)
        command.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
        if name == "build":
            command.add_argument("--workers", type=int, default=4)
    return value


def main() -> int:
    args = parser().parse_args()
    data_root = Path(args.data_root)
    if args.command == "build":
        result: Any = {
            "status": "dispersion_benchmark_ready",
            "manifest_path": str(
                build(data_root=data_root, workers=int(args.workers))
            ),
            "candidate_values_computed": False,
            "forward_return_fields_read": False,
            "provider_request_issued": False,
        }
    else:
        result = status(data_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

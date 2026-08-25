#!/usr/bin/env python3
"""Run Campaign302's frozen streamed Alpha360 temporal Transformer."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from qlib.config import REG_CN
from qlib.contrib.data.loader import Alpha360DL
from qlib.data import D

import qlib
from scripts import a_share_three_day_walkforward_campaign as engine
from scripts import a_share_three_day_walkforward_campaign286 as campaign286


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_302_preregistration_20260825.json"
)
PROTOCOL_SHA256 = "050d570869ae4588b20de37882fa23ae755a1425287daf4d760c2550e12c1248"
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_302_concept_scouting_20260825.json"
)
CONCEPT_SHA256 = "730083e266641ce2c331bd9d7dad89d9e8ba496000861df8ca80416cb38a512c"
OVERLAP_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_302_model_overlap_audit_20260825.json"
)
OVERLAP_SHA256 = "5e3ace6cafae813ad9c2440a4e01ba1949279f0e9e9975f21a1957b70b734a12"
DESIGN_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_302_design_implementation_freeze_20260825.json"
)
DEVELOPMENT_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_302_development_execution_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign302.py"
)
WORKER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign302_torch_worker.py"
)
ALPHA360_LOADER_PATH = REPO_ROOT / "qlib/contrib/data/loader.py"
ALPHA360_LOADER_SHA256 = (
    "814b7f7ab3d418ae3c87ce352220080b239eba2670eac9e38376b794be4075cb"
)
ENGINE_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign.py"
ENGINE_SHA256 = "301f5fe665422b94c9fa110e67995ff0999584a5f323ecdd5f56151a3529f5a7"
CAMPAIGN286_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign286.py"
CAMPAIGN286_SHA256 = (
    "ef454870c19cf5fa6306251775c3e04dd2e955b5f68fb6aeaedb467433d47f86"
)
WORKER_PYTHON = Path("/Volumes/DIsk/Coding/anaconda3/envs/arcloop/bin/python")
WORKER_PYTHON_SHA256 = (
    "3011a6bcfeaef78d633bb26e93069fe3a531581e4c99ca6fdd9426517e90904a"
)
WORKER_TORCH_INIT = Path(
    "/Volumes/DIsk/Coding/anaconda3/envs/arcloop/lib/python3.11/site-packages/torch/__init__.py"
)
WORKER_TORCH_INIT_SHA256 = (
    "51c90fe34a7cf869517d1bab4cd114498790e169ec668f1a154c35ec64117a5e"
)
PROVIDER_URI = Path("/Volumes/DIsk/Disk-Coding/qlib/data/qlib/cn_a_share")
PRICE_BASIS_PATH = PROVIDER_URI / "price_basis.json"
PRICE_BASIS_SHA256 = (
    "68e9dbb83749779b34d5cf3b116195074c154ff74cb6de95ba67695bedc1f14f"
)
CALENDAR_PATH = PROVIDER_URI / "calendars/day.txt"
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
UNIVERSE_PATH = PROVIDER_URI / "instruments/buyable_main_chinext.txt"
UNIVERSE_SHA256 = "77ccf8de2ed1e447e73b5d5ff1703fc2a8656d6adab34ef44017481730249db1"
DESIGN_MANIFEST_PATH = Path(
    "/Volumes/DIsk/Disk-Coding/qlib-data/recovery-worktree/experiments/short_horizon/"
    "historical_walkforward/campaign_286/alpha158_development_design_recovery_v3/"
    "snapshot_manifest.json"
)
DESIGN_MANIFEST_SHA256 = (
    "31cba0be801ac1421ef9555b862575089589ec08397c1420be3fc4f43b111d4e"
)
DESIGN_DATASET_SHA256 = (
    "714f4ccbdf4bfbaccfd04f543ec8c6a0bc345d3cc567ab621d01905130c46252"
)
DESIGN_PARTITION_SHA256 = {
    2019: "5860735e85cca233841168ffa4ec49257d122a91348ede4214be4130ccfd2d5a",
    2020: "a49c8dc6c564714a8a9755c20619ca7b88de39a51b992240600ca9369ed719cb",
    2021: "6cc0536673438dae0ba81a9b91e498092d19d7255f6f67e0031f3e3df7baa456",
    2022: "ca91585aa8010f1395c7371af6df5cd746db19ea55144255e175d1fa95ba018d",
    2023: "a0476b145987a5698b989880979f28ee1a6be65435787a1df911d531c3a6ec25",
}
INFRASTRUCTURE_FAILURE_PATHS = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_302_active_root_status_failure_20260825.json",
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_302_rich_status_lock_permission_failure_20260825.json",
)
INFRASTRUCTURE_FAILURE_SHA256 = (
    "cee4ecadf3c793f9b2750128d71ad5bfeb59a5b5eef89accb21176a5f62c9052",
    "ad09e28bf7842fdcc4849dbaf1f42cbc132e9304fa9695c3a037f696cda70bc2",
)
OUTPUT_ROOT = (
    REPO_ROOT
    / ".local-research/campaign_302/alpha360_streamed_transformer_8d_1l_v1"
)
DESIGN_EVIDENCE_PATH = OUTPUT_ROOT / "design_evidence.json"
DEVELOPMENT_REPORT_PATH = OUTPUT_ROOT / "development_report.json"
TRIAL_LEDGER_PATH = OUTPUT_ROOT / "trial_ledger.json"
SURVIVORS_PATH = OUTPUT_ROOT / "development_survivors.json"

TRIAL_ID = "wf302_alpha360_streamed_transformer_8d_1l"
FEATURE_COUNT = 360
MINIMUM_FINITE_FEATURES = 270
SAMPLE_SIZE_PER_SESSION = 64
MINIMUM_SUPPORTED_SAMPLE_PER_SESSION = 50
MINIMUM_RETAINED_TRAINING_SESSIONS = 60
MINIMUM_PREPROCESSING_OBSERVATIONS = 512
VALIDATION_INSTRUMENT_BATCH_SIZE = 32
MINIMUM_WORKSPACE_FREE_BYTES = 8_589_934_592
MAXIMUM_PERSISTED_FEATURE_BYTES = 536_870_912
MAXIMUM_TEMPORARY_FEATURE_BYTES = 134_217_728
PURGE_SIGNAL_SESSIONS = 3
CHAIN_GENESIS = "0" * 64
ALPHA360_LIBRARY_SHA256 = (
    "3a1cc68c98b24575e210514c43575d3f284868a30aab9b6e12b45a84d0539175"
)
FOLDS = (
    {
        "fold": 1,
        "train": ("2019-01-01", "2020-12-31"),
        "validation": ("2021-01-01", "2021-12-31"),
    },
    {
        "fold": 2,
        "train": ("2019-01-01", "2021-12-31"),
        "validation": ("2022-01-01", "2022-12-31"),
    },
    {
        "fold": 3,
        "train": ("2019-01-01", "2022-12-31"),
        "validation": ("2023-01-01", "2023-12-31"),
    },
)

_QLIB_INITIALIZED = False


class Campaign302Error(RuntimeError):
    """Fail closed when a frozen Campaign302 invariant changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_array(values: np.ndarray, dtype: str) -> str:
    array = np.asarray(values).astype(dtype, copy=False)
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Campaign302Error(f"JSON binding unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Campaign302Error(f"JSON binding is not an object: {path}")
    return value


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign302Error(f"{label} fingerprint changed")


def atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_npy(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            np.save(handle, values, allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def canonical_feature_library_sha256() -> str:
    fields, names = Alpha360DL.get_feature_config()
    payload = json.dumps(
        list(zip(names, fields, strict=True)),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_worker_runtime() -> None:
    require_file(WORKER_PYTHON, WORKER_PYTHON_SHA256, "worker Python")
    require_file(WORKER_TORCH_INIT, WORKER_TORCH_INIT_SHA256, "worker torch")
    if not WORKER_PATH.is_file():
        raise Campaign302Error("worker script is missing")
    command = [
        str(WORKER_PYTHON),
        "-c",
        "import sys,torch; assert sys.version_info[:3] == (3,11,14); "
        "assert torch.__version__ == '2.10.0'; assert not torch.cuda.is_available()",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise Campaign302Error("worker runtime preflight failed")


def validate_static_context() -> tuple[dict[str, Any], dict[str, Any]]:
    bindings = (
        (PROTOCOL_PATH, PROTOCOL_SHA256, "Campaign302 protocol"),
        (CONCEPT_PATH, CONCEPT_SHA256, "Campaign302 concept catalog"),
        (OVERLAP_PATH, OVERLAP_SHA256, "Campaign302 overlap audit"),
        (ALPHA360_LOADER_PATH, ALPHA360_LOADER_SHA256, "Alpha360 loader"),
        (ENGINE_PATH, ENGINE_SHA256, "three-session execution engine"),
        (CAMPAIGN286_PATH, CAMPAIGN286_SHA256, "Campaign286 evaluation engine"),
        (PRICE_BASIS_PATH, PRICE_BASIS_SHA256, "accepted historical price basis"),
        (CALENDAR_PATH, CALENDAR_SHA256, "historical calendar"),
        (UNIVERSE_PATH, UNIVERSE_SHA256, "buyable universe"),
        (DESIGN_MANIFEST_PATH, DESIGN_MANIFEST_SHA256, "base design manifest"),
    )
    for path, expected, label in bindings:
        require_file(path, expected, label)
    for path, expected in zip(
        INFRASTRUCTURE_FAILURE_PATHS, INFRASTRUCTURE_FAILURE_SHA256, strict=True
    ):
        require_file(path, expected, "Campaign302 infrastructure failure")
    protocol = load_json(PROTOCOL_PATH)
    manifest = load_json(DESIGN_MANIFEST_PATH)
    price_basis = load_json(PRICE_BASIS_PATH)
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign302_preregistration"
        and protocol.get("status")
        == "frozen_one_complete_alpha360_streamed_transformer_before_alpha360_feature_or_return_values"
        and (protocol.get("complete_feature_library") or {}).get("feature_count")
        == FEATURE_COUNT
        and (protocol.get("complete_feature_library") or {}).get(
            "minimum_finite_features_per_row"
        )
        == MINIMUM_FINITE_FEATURES
        and canonical_feature_library_sha256() == ALPHA360_LIBRARY_SHA256
        and manifest.get("dataset_sha256") == DESIGN_DATASET_SHA256
        and manifest.get("development_years") == [2019, 2020, 2021, 2022, 2023]
        and price_basis.get("status") == "passed"
        and price_basis.get("daily_sources") == ["baostock"]
        and price_basis.get("future_corporate_actions_used") is False
        and PROVIDER_URI.is_dir()
    ):
        raise Campaign302Error("Campaign302 frozen context changed")
    validate_worker_runtime()
    return protocol, manifest


def validate_freeze(path: Path, kind: str, status: str) -> dict[str, Any]:
    if not path.is_file():
        raise Campaign302Error(f"missing Campaign302 freeze: {path}")
    record = load_json(path)
    runner = record.get("runner") or {}
    worker = record.get("worker") or {}
    tests = record.get("tests") or {}
    dependencies = record.get("dependencies") or {}
    if not (
        record.get("kind") == kind
        and record.get("status") == status
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == file_sha256(Path(__file__).resolve())
        and worker.get("path") == str(WORKER_PATH.relative_to(REPO_ROOT))
        and worker.get("sha256") == file_sha256(WORKER_PATH)
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == file_sha256(TEST_PATH)
        and dependencies.get("alpha360_loader_sha256") == ALPHA360_LOADER_SHA256
        and dependencies.get("execution_engine_sha256") == ENGINE_SHA256
        and dependencies.get("campaign286_engine_sha256") == CAMPAIGN286_SHA256
    ):
        raise Campaign302Error("Campaign302 implementation freeze changed")
    return record


def validate_design_freeze() -> dict[str, Any]:
    record = validate_freeze(
        DESIGN_FREEZE_PATH,
        "a_share_three_day_walkforward_campaign302_design_implementation_freeze",
        "frozen_before_first_alpha360_feature_or_return_value",
    )
    boundary = record.get("research_boundary") or {}
    if not (
        boundary.get("alpha360_feature_value_read_before_freeze") is False
        and boundary.get("historical_return_value_read_before_freeze") is False
        and boundary.get("model_fit_before_freeze") is False
    ):
        raise Campaign302Error("Campaign302 design boundary changed")
    return record


def validate_development_freeze() -> dict[str, Any]:
    record = validate_freeze(
        DEVELOPMENT_FREEZE_PATH,
        "a_share_three_day_walkforward_campaign302_development_execution_freeze",
        "frozen_after_alpha360_design_before_training_or_validation_return_read",
    )
    evidence = record.get("design_evidence") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        evidence.get("path") == str(DESIGN_EVIDENCE_PATH.relative_to(REPO_ROOT))
        and evidence.get("sha256") == file_sha256(DESIGN_EVIDENCE_PATH)
        and boundary.get("training_or_validation_return_read_before_freeze") is False
        and boundary.get("model_fit_before_freeze") is False
    ):
        raise Campaign302Error("Campaign302 development boundary changed")
    return record


def local_calendar() -> pd.DatetimeIndex:
    values = [
        line.strip()
        for line in CALENDAR_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    calendar = pd.DatetimeIndex(pd.to_datetime(values, errors="raise")).normalize()
    if not calendar.is_monotonic_increasing or calendar.has_duplicates:
        raise Campaign302Error("calendar identity changed")
    return calendar


def design_record(year: int, manifest: Mapping[str, Any]) -> Path:
    matches = [item for item in manifest["files"] if int(item["year"]) == year]
    if len(matches) != 1:
        raise Campaign302Error(f"base design partition changed: {year}")
    path = (DESIGN_MANIFEST_PATH.parent / str(matches[0]["path"])).resolve()
    require_file(path, DESIGN_PARTITION_SHA256[year], f"base design {year}")
    return path


def load_base_identities(
    years: Iterable[int],
    manifest: Mapping[str, Any],
    *,
    allowed_dates: Iterable[Any] | None = None,
) -> tuple[pd.DataFrame, np.ndarray]:
    allowed_days: np.ndarray | None = None
    if allowed_dates is not None:
        allowed_days = (
            pd.DatetimeIndex(list(allowed_dates))
            .normalize()
            .to_numpy(dtype="datetime64[D]")
            .astype(np.int64)
        )
    key_parts: list[np.ndarray] = []
    eligible_parts: list[np.ndarray] = []
    for year in sorted({int(value) for value in years}):
        path = design_record(year, manifest)
        for batch in pq.ParquetFile(path).iter_batches(
            batch_size=131_072,
            columns=["stock_day_key", "model_support_eligible"],
        ):
            frame = batch.to_pandas()
            keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
            mask = np.ones(len(keys), dtype=bool)
            if allowed_days is not None:
                mask = np.isin(keys // 4_000_000, allowed_days)
            if mask.any():
                key_parts.append(keys[mask])
                eligible_parts.append(
                    frame["model_support_eligible"].to_numpy(dtype=bool)[mask]
                )
    if not key_parts:
        raise Campaign302Error("base identity selection is empty")
    keys = np.concatenate(key_parts)
    eligible = np.concatenate(eligible_parts)
    if len(np.unique(keys)) != len(keys) or np.any(keys[1:] < keys[:-1]):
        raise Campaign302Error("base identity order changed")
    dates, instruments = campaign286.decode_keys(keys)
    identities = pd.DataFrame(
        {"trade_date": dates, "instrument": instruments, "stock_day_key": keys}
    )
    return identities, eligible


def deterministic_sample(
    identities: pd.DataFrame, eligible: np.ndarray
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = identities.loc[
        np.asarray(eligible, dtype=bool),
        ["trade_date", "instrument", "stock_day_key"],
    ].copy()
    selected: list[int] = []
    retained_counts: list[int] = []
    excluded = 0
    for session, group in frame.groupby("trade_date", sort=True):
        if len(group) < SAMPLE_SIZE_PER_SESSION:
            excluded += 1
            continue
        date_text = pd.Timestamp(session).strftime("%Y-%m-%d")
        ordered = sorted(
            (
                hashlib.sha256(
                    f"302|{date_text}|{instrument}".encode()
                ).digest(),
                str(instrument),
                int(index),
            )
            for index, instrument in zip(group.index, group["instrument"], strict=True)
        )
        selected.extend(item[2] for item in ordered[:SAMPLE_SIZE_PER_SESSION])
        retained_counts.append(len(group))
    if (
        len(retained_counts) < MINIMUM_RETAINED_TRAINING_SESSIONS
        or len(selected) != len(retained_counts) * SAMPLE_SIZE_PER_SESSION
    ):
        raise Campaign302Error("deterministic sample gate failed")
    sample = identities.loc[selected].reset_index(drop=True)
    if sample["stock_day_key"].duplicated().any():
        raise Campaign302Error("sample identity duplicated")
    return sample, {
        "retained_base_sessions": len(retained_counts),
        "excluded_small_base_sessions": excluded,
        "sampled_rows": len(sample),
        "sample_size_per_session": SAMPLE_SIZE_PER_SESSION,
        "minimum_base_eligible_names": min(retained_counts),
        "maximum_base_eligible_names": max(retained_counts),
        "sample_stock_day_keys_sha256": hash_array(
            sample["stock_day_key"].to_numpy(dtype=np.int64), "<i8"
        ),
    }


def initialize_qlib() -> None:
    global _QLIB_INITIALIZED
    if not _QLIB_INITIALIZED:
        qlib.init(provider_uri=str(PROVIDER_URI), region=REG_CN, kernels=1)
        _QLIB_INITIALIZED = True


def alpha360_config() -> tuple[list[str], list[str]]:
    fields, names = Alpha360DL.get_feature_config()
    if len(fields) != FEATURE_COUNT or len(names) != FEATURE_COUNT:
        raise Campaign302Error("Alpha360 feature count changed")
    return list(fields), list(names)


def query_alpha360(identities: pd.DataFrame) -> np.ndarray:
    if identities.empty or identities["stock_day_key"].duplicated().any():
        raise Campaign302Error("Alpha360 query identity changed")
    initialize_qlib()
    fields, names = alpha360_config()
    instruments = sorted(identities["instrument"].astype(str).unique())
    start = pd.Timestamp(identities["trade_date"].min()).strftime("%Y-%m-%d")
    end = pd.Timestamp(identities["trade_date"].max()).strftime("%Y-%m-%d")
    frame = D.features(instruments, fields, start_time=start, end_time=end, freq="day")
    if frame.shape[1] != FEATURE_COUNT:
        raise Campaign302Error("Alpha360 provider column count changed")
    frame = frame.copy()
    frame.columns = names
    observed = frame.reset_index()
    if not {"instrument", "datetime"}.issubset(observed.columns):
        raise Campaign302Error("Alpha360 provider index changed")
    observed["instrument"] = observed["instrument"].astype(str)
    observed["datetime"] = pd.to_datetime(observed["datetime"]).dt.normalize()
    if observed.duplicated(["instrument", "datetime"]).any():
        raise Campaign302Error("Alpha360 provider keys duplicated")
    observed = observed.set_index(["instrument", "datetime"])
    target = pd.MultiIndex.from_arrays(
        [
            identities["instrument"].astype(str).to_numpy(),
            pd.DatetimeIndex(identities["trade_date"]).normalize(),
        ],
        names=["instrument", "datetime"],
    )
    return observed[names].reindex(target).to_numpy(dtype=np.float32, copy=True)


def preprocessing_statistics(
    matrix: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    values = np.asarray(matrix, dtype=np.float64).copy()
    values[~np.isfinite(values)] = np.nan
    finite_counts = np.isfinite(values).sum(axis=0).astype(np.int64)
    if int(finite_counts.min()) < MINIMUM_PREPROCESSING_OBSERVATIONS:
        raise Campaign302Error("Alpha360 preprocessing finite-count gate failed")
    centers = np.nanmedian(values, axis=0)
    q25 = np.nanpercentile(values, 25.0, axis=0)
    q75 = np.nanpercentile(values, 75.0, axis=0)
    scales = np.maximum(q75 - q25, 1e-6)
    if not (
        np.isfinite(centers).all()
        and np.isfinite(scales).all()
        and (scales > 0).all()
    ):
        raise Campaign302Error("Alpha360 preprocessing statistics changed")
    return centers, scales, {
        "minimum_finite_observations_per_feature": int(finite_counts.min()),
        "maximum_finite_observations_per_feature": int(finite_counts.max()),
        "finite_counts_sha256": hash_array(finite_counts, "<i8"),
        "centers_sha256": hash_array(centers, "<f8"),
        "scales_sha256": hash_array(scales, "<f8"),
        "minimum_scale": float(scales.min()),
        "maximum_scale": float(scales.max()),
        "missing_fill_after_scaling": 0.0,
        "clip": [-8.0, 8.0],
    }


def transform_features(
    matrix: np.ndarray, centers: np.ndarray, scales: np.ndarray
) -> np.ndarray:
    values = np.asarray(matrix, dtype=np.float32).copy()
    values[~np.isfinite(values)] = np.nan
    values = (values - centers.astype(np.float32)) / scales.astype(np.float32)
    values[~np.isfinite(values)] = 0.0
    return np.clip(values, -8.0, 8.0).astype(np.float32, copy=False)


def design_fold(
    fold: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    schedule = engine.global_signal_schedule(local_calendar())
    contained = engine.purged_period_schedule(
        schedule, fold["train"][0], fold["train"][1], PURGE_SIGNAL_SESSIONS
    )
    years = range(2019, pd.Timestamp(fold["train"][1]).year + 1)
    identities, eligible = load_base_identities(
        years, manifest, allowed_dates=contained["signal_date"]
    )
    sample, sample_stats = deterministic_sample(identities, eligible)
    raw = query_alpha360(sample)
    finite_counts = np.isfinite(raw).sum(axis=1).astype(np.int16)
    support = finite_counts >= MINIMUM_FINITE_FEATURES
    dates = pd.DatetimeIndex(sample["trade_date"]).normalize()
    supported_by_session = pd.Series(support).groupby(dates).sum()
    retained_dates = supported_by_session[
        supported_by_session >= MINIMUM_SUPPORTED_SAMPLE_PER_SESSION
    ].index
    support &= dates.isin(retained_dates)
    if len(retained_dates) < MINIMUM_RETAINED_TRAINING_SESSIONS:
        raise Campaign302Error("Alpha360 sampled session-support gate failed")
    centers, scales, preprocessing = preprocessing_statistics(raw)
    transformed = transform_features(raw, centers, scales)
    path = OUTPUT_ROOT / f"fold_{fold['fold']}_design.npz"
    atomic_npz(
        path,
        stock_day_key=sample["stock_day_key"].to_numpy(dtype=np.int64),
        trade_day=dates.to_numpy(dtype="datetime64[D]").astype(np.int64),
        matrix=transformed,
        support=support.astype(np.uint8),
        finite_feature_count=finite_counts,
        centers=centers.astype(np.float64),
        scales=scales.astype(np.float64),
    )
    if path.stat().st_size > MAXIMUM_PERSISTED_FEATURE_BYTES:
        raise Campaign302Error("persisted fold design exceeds resource contract")
    record = {
        "fold": int(fold["fold"]),
        "training": list(fold["train"]),
        "scheduled_signal_count_after_containment_and_purge": len(contained),
        "base_rows": len(identities),
        "base_model_support_eligible_rows": int(eligible.sum()),
        "sample": sample_stats,
        "alpha360": {
            "raw_sample_matrix_sha256": hash_array(raw, "<f4"),
            "finite_feature_count_sha256": hash_array(finite_counts, "<i2"),
            "minimum_finite_features_per_supported_row": MINIMUM_FINITE_FEATURES,
            "supported_rows": int(support.sum()),
            "retained_supported_sessions": len(retained_dates),
            "minimum_supported_rows_in_retained_session": int(
                supported_by_session.loc[retained_dates].min()
            ),
            "all_sampled_session_dates_sha256": hash_array(
                supported_by_session.index.to_numpy(dtype="datetime64[D]").astype(
                    np.int64
                ),
                "<i8",
            ),
            "all_sampled_session_support_counts_sha256": hash_array(
                supported_by_session.to_numpy(dtype=np.int64), "<i8"
            ),
            "retained_session_dates_sha256": hash_array(
                pd.DatetimeIndex(retained_dates)
                .to_numpy(dtype="datetime64[D]")
                .astype(np.int64),
                "<i8",
            ),
        },
        "preprocessing": preprocessing,
        "transformed_matrix_sha256": hash_array(transformed, "<f4"),
        "design_artifact": {
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": file_sha256(path),
            "bytes": path.stat().st_size,
        },
        "historical_return_value_read": False,
    }
    record["fold_design_sha256"] = engine.value_sha256(record)
    del raw, transformed, identities
    gc.collect()
    return record


def plan_design() -> dict[str, Any]:
    validate_design_freeze()
    validate_static_context()
    free = shutil.disk_usage(REPO_ROOT).free
    ready = bool(not OUTPUT_ROOT.exists() and free >= MINIMUM_WORKSPACE_FREE_BYTES)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign302_design_plan",
        "status": "ready_for_zero_return_alpha360_design" if ready else "not_ready",
        "ready": ready,
        "workspace_free_bytes": free,
        "minimum_workspace_free_bytes": MINIMUM_WORKSPACE_FREE_BYTES,
        "alpha360_feature_value_read_by_plan": False,
        "historical_return_value_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_changed": False,
    }


def build_design(confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise Campaign302Error("build-design requires --confirm-build")
    plan = plan_design()
    if plan["ready"] is not True:
        raise Campaign302Error("Campaign302 design plan is not ready")
    _, manifest = validate_static_context()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    try:
        folds = [design_fold(fold, manifest) for fold in FOLDS]
        persisted = sum(item["design_artifact"]["bytes"] for item in folds)
        if persisted > MAXIMUM_PERSISTED_FEATURE_BYTES:
            raise Campaign302Error("all-fold persisted design exceeds resource contract")
        evidence = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign302_zero_return_design_evidence",
            "status": "passed_complete_alpha360_sample_design_ready_for_development_freeze",
            "created_at": campaign286.utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "design_implementation_freeze_sha256": file_sha256(DESIGN_FREEZE_PATH),
            "feature_library_sha256": ALPHA360_LIBRARY_SHA256,
            "alpha360_loader_sha256": ALPHA360_LOADER_SHA256,
            "runner_sha256": file_sha256(Path(__file__).resolve()),
            "worker_sha256": file_sha256(WORKER_PATH),
            "worker_python_sha256": WORKER_PYTHON_SHA256,
            "worker_torch_init_sha256": WORKER_TORCH_INIT_SHA256,
            "execution_engine_sha256": ENGINE_SHA256,
            "campaign286_engine_sha256": CAMPAIGN286_SHA256,
            "source_price_basis_sha256": PRICE_BASIS_SHA256,
            "base_design_dataset_sha256": DESIGN_DATASET_SHA256,
            "folds": folds,
            "persisted_training_feature_bytes": persisted,
            "dense_five_year_snapshot_created": False,
            "alpha360_sample_feature_values_read": True,
            "candidate_or_comparator_values_read": False,
            "historical_daily_price_or_forward_return_values_read": False,
            "model_fit_performed": False,
            "stress_2024_2025_opened": False,
            "provider_request_issued": False,
            "candidate49_changed": False,
        }
        engine.atomic_write_json(DESIGN_EVIDENCE_PATH, evidence)
        return {
            "status": evidence["status"],
            "fold_count": len(folds),
            "persisted_training_feature_bytes": persisted,
            "design_evidence_path": str(DESIGN_EVIDENCE_PATH),
            "design_evidence_sha256": file_sha256(DESIGN_EVIDENCE_PATH),
            "historical_return_value_read": False,
        }
    except BaseException as error:
        engine.atomic_write_json(
            OUTPUT_ROOT / "design_failure.json",
            {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign302_design_failure",
                "status": "failed_preserved_no_unfrozen_recovery",
                "created_at": campaign286.utc_now(),
                "error_type": type(error).__name__,
                "error": str(error),
                "alpha360_values_may_have_been_read": True,
                "historical_return_value_read": False,
                "provider_request_issued": False,
                "candidate49_changed": False,
            },
        )
        raise


def load_fold_design(fold_number: int, evidence: Mapping[str, Any]) -> dict[str, Any]:
    matches = [item for item in evidence["folds"] if int(item["fold"]) == fold_number]
    if len(matches) != 1:
        raise Campaign302Error("fold design evidence changed")
    record = matches[0]
    path = REPO_ROOT / str(record["design_artifact"]["path"])
    require_file(path, str(record["design_artifact"]["sha256"]), "fold design")
    with np.load(path, allow_pickle=False) as payload:
        result = {name: payload[name].copy() for name in payload.files}
    if not (
        result["matrix"].ndim == 2
        and result["matrix"].shape[1] == FEATURE_COUNT
        and len(result["matrix"]) == len(result["stock_day_key"])
        and hash_array(result["matrix"], "<f4")
        == record["transformed_matrix_sha256"]
    ):
        raise Campaign302Error("fold design arrays changed")
    return result


def training_target_bundle(
    fold: Mapping[str, Any], manifest: Mapping[str, Any], design: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    context = campaign286.model_context()
    market, calendar = engine.load_market_context(
        context, fold["train"][1], fold["train"][0], 512
    )
    schedule = engine.global_signal_schedule(calendar)
    contained = engine.purged_period_schedule(
        schedule, fold["train"][0], fold["train"][1], PURGE_SIGNAL_SESSIONS
    )
    years = range(2019, pd.Timestamp(fold["train"][1]).year + 1)
    identities, eligible = load_base_identities(
        years, manifest, allowed_dates=contained["signal_date"]
    )
    factors = identities[["trade_date", "instrument"]].copy()
    factors["model_support_eligible"] = eligible
    panel = engine.build_signal_panel(market, factors, schedule)
    panel_keys = campaign286.design.compact_stock_day_keys(
        panel["signal_date"], panel["instrument"]
    )
    base_support = panel["model_support_eligible"].fillna(False).to_numpy(dtype=bool)
    returns = pd.to_numeric(panel["forward_gross_return"], errors="coerce").copy()
    returns.loc[~base_support] = np.nan
    target = campaign286.target_percentiles(panel["signal_date"], returns)
    sample_keys = np.asarray(design["stock_day_key"], dtype=np.int64)
    positions = pd.Index(panel_keys).get_indexer(sample_keys)
    if (positions < 0).any():
        raise Campaign302Error("sample target alignment changed")
    sample_target = target[positions]
    sample_dates = np.asarray(design["trade_day"], dtype=np.int64)
    support = np.asarray(design["support"], dtype=bool)
    valid = support & np.isfinite(sample_target)
    unique, inverse, counts = np.unique(
        sample_dates[valid], return_inverse=True, return_counts=True
    )
    keep_dates = unique[counts >= MINIMUM_SUPPORTED_SAMPLE_PER_SESSION]
    valid &= np.isin(sample_dates, keep_dates)
    if len(keep_dates) < MINIMUM_RETAINED_TRAINING_SESSIONS:
        raise Campaign302Error("training target session gate failed")
    unique, inverse, counts = np.unique(
        sample_dates[valid], return_inverse=True, return_counts=True
    )
    weight = np.zeros(len(valid), dtype=np.float64)
    weight[valid] = 1.0 / (len(unique) * counts[inverse])
    if not math.isclose(float(weight.sum()), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise Campaign302Error("session-equal target weights changed")
    result = {
        "retained_training_sessions": len(unique),
        "training_rows": int(valid.sum()),
        "minimum_rows_per_retained_session": int(counts.min()),
        "maximum_rows_per_retained_session": int(counts.max()),
        "target_sha256": hash_array(sample_target[valid], "<f8"),
        "weight_sha256": hash_array(weight[valid], "<f8"),
    }
    return (
        np.asarray(design["matrix"], dtype=np.float32)[valid],
        sample_target[valid].astype(np.float32),
        weight[valid].astype(np.float32),
        result,
    )


def run_worker(arguments: list[str]) -> dict[str, Any]:
    command = [str(WORKER_PYTHON), str(WORKER_PATH), *arguments]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise Campaign302Error(
            f"torch worker failed with exit {result.returncode}: "
            f"{result.stderr.strip().splitlines()[-1:] or ['no stderr']}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise Campaign302Error("torch worker output changed") from exc
    if not isinstance(payload, dict):
        raise Campaign302Error("torch worker output is not an object")
    return payload


def train_fold_model(
    fold: Mapping[str, Any], manifest: Mapping[str, Any], evidence: Mapping[str, Any]
) -> tuple[dict[str, Any], Path, np.ndarray, np.ndarray]:
    design = load_fold_design(int(fold["fold"]), evidence)
    matrix, target, weight, target_stats = training_target_bundle(
        fold, manifest, design
    )
    model_dir = OUTPUT_ROOT / f"fold_{fold['fold']}_model"
    model_path = model_dir / f"{TRIAL_ID}.pt"
    worker_report_path = model_dir / "training_report.json"
    worker_input = model_dir / ".training_input.npz"
    atomic_npz(worker_input, matrix=matrix, target=target, weight=weight)
    try:
        run_worker(
            [
                "train",
                "--input",
                str(worker_input),
                "--model",
                str(model_path),
                "--report",
                str(worker_report_path),
            ]
        )
    finally:
        worker_input.unlink(missing_ok=True)
    worker_report = load_json(worker_report_path)
    fit = {
        "fold": int(fold["fold"]),
        "trial_id": TRIAL_ID,
        "training": target_stats,
        "worker_report": {
            "path": str(worker_report_path.relative_to(REPO_ROOT)),
            "sha256": file_sha256(worker_report_path),
        },
        "model": {
            "path": str(model_path.relative_to(REPO_ROOT)),
            "sha256": file_sha256(model_path),
            "bytes": model_path.stat().st_size,
        },
        "loss_curve": worker_report["loss_curve"],
        "validation_return_feedback_used": False,
    }
    return (
        fit,
        model_path,
        np.asarray(design["centers"], dtype=np.float64),
        np.asarray(design["scales"], dtype=np.float64),
    )


def stream_validation_scores(
    fold: Mapping[str, Any],
    manifest: Mapping[str, Any],
    model_path: Path,
    centers: np.ndarray,
    scales: np.ndarray,
) -> tuple[np.ndarray, pd.DataFrame, dict[str, Any]]:
    year = pd.Timestamp(fold["validation"][0]).year
    identities, base_eligible = load_base_identities([year], manifest)
    scores = np.full(len(identities), np.nan, dtype=np.float64)
    digest = hashlib.sha256()
    queried_rows = 0
    supported_rows = 0
    instruments = sorted(identities.loc[base_eligible, "instrument"].unique())
    temp_root = OUTPUT_ROOT / f"fold_{fold['fold']}_stream"
    temp_root.mkdir(parents=True, exist_ok=False)
    try:
        for begin in range(0, len(instruments), VALIDATION_INSTRUMENT_BATCH_SIZE):
            selected = set(
                instruments[begin : begin + VALIDATION_INSTRUMENT_BATCH_SIZE]
            )
            positions = np.flatnonzero(
                base_eligible & identities["instrument"].isin(selected).to_numpy()
            )
            batch_identities = identities.iloc[positions].reset_index(drop=True)
            raw = query_alpha360(batch_identities)
            finite = np.isfinite(raw).sum(axis=1)
            support = finite >= MINIMUM_FINITE_FEATURES
            transformed = transform_features(raw, centers, scales)
            digest.update(
                batch_identities["stock_day_key"].to_numpy(dtype="<i8").tobytes()
            )
            digest.update(raw.astype("<f4", copy=False).tobytes(order="C"))
            queried_rows += len(raw)
            supported_rows += int(support.sum())
            if int(support.sum()) > 0:
                input_path = temp_root / "input.npy"
                output_path = temp_root / "scores.npy"
                supported_matrix = transformed[support]
                if supported_matrix.nbytes > MAXIMUM_TEMPORARY_FEATURE_BYTES:
                    raise Campaign302Error("validation batch exceeds resource contract")
                atomic_npy(input_path, supported_matrix)
                run_worker(
                    [
                        "score",
                        "--input",
                        str(input_path),
                        "--model",
                        str(model_path),
                        "--output",
                        str(output_path),
                    ]
                )
                predicted = np.load(output_path, allow_pickle=False)
                if len(predicted) != int(support.sum()):
                    raise Campaign302Error("validation score alignment changed")
                scores[positions[support]] = predicted
                input_path.unlink(missing_ok=True)
                output_path.unlink(missing_ok=True)
            del raw, transformed
            gc.collect()
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    schedule = engine.purged_period_schedule(
        engine.global_signal_schedule(local_calendar()),
        fold["validation"][0],
        fold["validation"][1],
        PURGE_SIGNAL_SESSIONS,
    )
    dates = pd.DatetimeIndex(identities["trade_date"]).normalize()
    counts: list[int] = []
    uniques: list[int] = []
    good = 0
    for session in schedule["signal_date"]:
        mask = dates.eq(pd.Timestamp(session)) & np.isfinite(scores)
        count = int(mask.sum())
        unique_count = int(np.unique(scores[mask]).size)
        counts.append(count)
        uniques.append(unique_count)
        if count >= 50 and unique_count >= 2:
            good += 1
    gate_passed = bool(
        len(counts) > 0
        and min(counts) >= 50
        and min(uniques) >= 2
        and good >= 60
    )
    evidence = {
        "validation_year": year,
        "queried_base_eligible_rows": queried_rows,
        "alpha360_supported_rows": supported_rows,
        "streamed_alpha360_dataset_sha256": digest.hexdigest(),
        "scheduled_validation_signals": len(schedule),
        "good_nonconstant_score_sessions": good,
        "minimum_finite_scores_per_scheduled_signal": min(counts) if counts else 0,
        "minimum_unique_scores_per_scheduled_signal": min(uniques) if uniques else 0,
        "passed": gate_passed,
        "validation_return_value_read": False,
    }
    return scores, identities, evidence


def freeze_validation_scores(
    fold: Mapping[str, Any],
    scores: np.ndarray,
    identities: pd.DataFrame,
    fit: Mapping[str, Any],
    score_gate: Mapping[str, Any],
) -> dict[str, Any]:
    snapshot_path = OUTPUT_ROOT / f"fold_{fold['fold']}_validation_scores.parquet"
    snapshot = campaign286.write_score_snapshot(
        snapshot_path, identities, {TRIAL_ID: scores}
    )
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign302_fold_prefit_scores",
        "status": (
            "frozen_score_gate_passed_before_validation_return_read"
            if score_gate["passed"]
            else "frozen_score_gate_failed_validation_returns_unread"
        ),
        "created_at": campaign286.utc_now(),
        "fold": int(fold["fold"]),
        "training": list(fold["train"]),
        "validation": list(fold["validation"]),
        "fit": fit,
        "validation_score_snapshot": snapshot,
        "score_gate": score_gate,
        "validation_daily_price_fields_read_before_record": [],
        "validation_forward_return_fields_read_before_record": False,
        "stress_2024_2025_opened": False,
        "candidate49_changed": False,
    }
    path = OUTPUT_ROOT / f"fold_{fold['fold']}_prefit_scores.json"
    engine.atomic_write_json(path, payload)
    payload["record_binding"] = {
        "path": str(path.relative_to(REPO_ROOT)),
        "sha256": file_sha256(path),
    }
    return payload


def prevalue_entries() -> list[dict[str, Any]]:
    catalog = load_json(CONCEPT_PATH)["finite_prevalue_concept_catalog"]
    entries = [
        {
            "attempt_id": item["catalog_id"],
            "phase": "prevalue_concept_scouting",
            "name": item["name"],
            "outcome": item["decision"],
            "reason": item["reason"],
            "alpha360_feature_value_read": False,
            "historical_return_value_read": False,
        }
        for item in catalog
    ]
    for path in INFRASTRUCTURE_FAILURE_PATHS:
        record = load_json(path)
        entries.append(
            {
                "attempt_id": record["attempt_id"],
                "phase": "infrastructure_failure",
                "name": path.name,
                "outcome": record["status"],
                "reason": record["interpretation"],
                "alpha360_feature_value_read": False,
                "historical_return_value_read": False,
            }
        )
    return entries


def build_ledger(trial: Mapping[str, Any]) -> dict[str, Any]:
    previous = CHAIN_GENESIS
    entries: list[dict[str, Any]] = []
    for record in [*prevalue_entries(), dict(trial)]:
        entry = {**record, "previous_entry_sha256": previous}
        entry["entry_sha256"] = engine.value_sha256(entry)
        previous = entry["entry_sha256"]
        entries.append(entry)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign302_trial_ledger",
        "append_only": True,
        "chain_genesis": CHAIN_GENESIS,
        "entries": entries,
        "entry_count": len(entries),
        "prevalue_concept_attempt_count": 8,
        "infrastructure_failure_attempt_count": 2,
        "model_trial_attempt_count": 1,
        "chain_tip_sha256": previous,
        "candidate49_changed": False,
    }


def plan_development() -> dict[str, Any]:
    validate_development_freeze()
    validate_static_context()
    evidence = load_json(DESIGN_EVIDENCE_PATH)
    allowed = {"design_evidence.json", *{f"fold_{i}_design.npz" for i in (1, 2, 3)}}
    existing = sorted(path.name for path in OUTPUT_ROOT.iterdir() if path.name not in allowed)
    ready = bool(
        not existing
        and evidence.get("status")
        == "passed_complete_alpha360_sample_design_ready_for_development_freeze"
    )
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign302_development_plan",
        "status": "ready_to_open_2019_2023_returns" if ready else "not_ready",
        "ready": ready,
        "existing_non_design_outputs": existing,
        "historical_return_value_read_by_plan": False,
        "stress_2024_2025_opened": False,
        "provider_request_issued": False,
        "candidate49_changed": False,
    }


def run_development(confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise Campaign302Error("run-development requires --confirm-run")
    plan = plan_development()
    if plan["ready"] is not True:
        raise Campaign302Error("Campaign302 development plan is not ready")
    _, manifest = validate_static_context()
    evidence = load_json(DESIGN_EVIDENCE_PATH)
    intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign302_development_intent",
        "status": "training_return_open_pending_chronological_completion",
        "opened_at": campaign286.utc_now(),
        "protocol_sha256": PROTOCOL_SHA256,
        "design_evidence_sha256": file_sha256(DESIGN_EVIDENCE_PATH),
        "validation_scores_frozen_before_each_validation_return_read": True,
        "stress_2024_2025_remains_closed": True,
        "candidate49_changed": False,
    }
    engine.atomic_write_json(OUTPUT_ROOT / "development_intent.json", intent)
    trial: dict[str, Any] = {
        "attempt_id": TRIAL_ID,
        "trial_id": TRIAL_ID,
        "campaign_id": "campaign_302",
        "phase": "development_walkforward",
        "economic_hypothesis": "Position-sensitive interactions across the complete sixty-session six-channel Alpha360 sequence may contain short-horizon information absent from Alpha158 summary operators.",
        "formula": "one fixed 8-dimensional one-layer two-head temporal Transformer over all 360 Alpha360 coordinates",
        "direction": "higher predicted within-session gross-return percentile",
        "feature_set": "complete Alpha360 in frozen order",
        "configuration_count": 1,
        "folds": [],
        "validation_metrics": [],
        "historical_return_value_read": True,
        "stress_2024_2025_opened": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    try:
        for fold in FOLDS:
            print(f"fold {fold['fold']}: training fixed Alpha360 Transformer", flush=True)
            fit, model_path, centers, scales = train_fold_model(
                fold, manifest, evidence
            )
            print(f"fold {fold['fold']}: streaming and freezing validation scores", flush=True)
            scores, identities, score_gate = stream_validation_scores(
                fold, manifest, model_path, centers, scales
            )
            prefit = freeze_validation_scores(
                fold, scores, identities, fit, score_gate
            )
            fold_record: dict[str, Any] = {
                "fold": int(fold["fold"]),
                "fit": fit,
                "prefit_score_record": prefit["record_binding"],
                "score_gate": score_gate,
            }
            if score_gate["passed"] is not True:
                fold_record["validation_metrics"] = None
                trial["folds"].append(fold_record)
                trial["decision"] = {
                    "passed": False,
                    "operationally_admissible": False,
                    "rejection_reasons": [
                        f"fold_{fold['fold']}_prefit_score_gate_failed"
                    ],
                }
                break
            print(f"fold {fold['fold']}: reading contained validation returns", flush=True)
            validation = campaign286.evaluate_validation(
                campaign286.model_context(), fold, {TRIAL_ID: scores}, identities, 512
            )[TRIAL_ID]
            metrics_payload = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign302_fold_validation_metrics",
                "status": "completed_after_bound_prefit_scores",
                "created_at": campaign286.utc_now(),
                "fold": int(fold["fold"]),
                "prefit_score_record": prefit["record_binding"],
                "validation_metrics": {TRIAL_ID: validation},
                "stress_2024_2025_opened": False,
                "candidate49_changed": False,
            }
            metrics_path = OUTPUT_ROOT / f"fold_{fold['fold']}_validation_metrics.json"
            engine.atomic_write_json(metrics_path, metrics_payload)
            fold_record["validation_metrics"] = validation
            fold_record["validation_metrics_binding"] = {
                "path": str(metrics_path.relative_to(REPO_ROOT)),
                "sha256": file_sha256(metrics_path),
            }
            trial["folds"].append(fold_record)
            trial["validation_metrics"].append(validation)
            del scores, identities, validation
            gc.collect()
        if "decision" not in trial:
            trial["decision"] = campaign286.survivor_decision(trial)
        trial["status"] = (
            "development_survivor_gate_passed"
            if trial["decision"]["passed"]
            else "development_rejected"
        )
        survivors = [TRIAL_ID] if trial["decision"]["passed"] else []
        ledger = build_ledger(trial)
        engine.atomic_write_json(TRIAL_LEDGER_PATH, ledger)
        survivor_record = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign302_development_survivors",
            "status": "frozen_before_2024_2025_return_read",
            "created_at": campaign286.utc_now(),
            "trial_decision": trial["decision"],
            "selected_survivor_trial_ids": survivors,
            "selected_survivor_count": len(survivors),
            "stress_2024_2025_opened": False,
            "candidate49_changed": False,
        }
        engine.atomic_write_json(SURVIVORS_PATH, survivor_record)
        report = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign302_development_report",
            "status": "development_complete_survivors_frozen",
            "created_at": campaign286.utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "design_evidence_sha256": file_sha256(DESIGN_EVIDENCE_PATH),
            "trial_count": 1,
            "ledger_entry_count": ledger["entry_count"],
            "validation_return_reading_trial_count": (
                1 if trial["validation_metrics"] else 0
            ),
            "model_fold_validation_return_reads": len(trial["validation_metrics"]),
            "survivor_count": len(survivors),
            "selected_survivor_trial_ids": survivors,
            "trial_decision": trial["decision"],
            "ledger": {
                "path": str(TRIAL_LEDGER_PATH.relative_to(REPO_ROOT)),
                "sha256": file_sha256(TRIAL_LEDGER_PATH),
            },
            "survivors": {
                "path": str(SURVIVORS_PATH.relative_to(REPO_ROOT)),
                "sha256": file_sha256(SURVIVORS_PATH),
            },
            "stress_2024_2025_opened": False,
            "provider_request_issued": False,
            "candidate49_changed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "investment_advice": False,
        }
        engine.atomic_write_json(DEVELOPMENT_REPORT_PATH, report)
        return {
            "status": report["status"],
            "survivor_count": len(survivors),
            "selected_survivor_trial_ids": survivors,
            "model_fold_validation_return_reads": len(trial["validation_metrics"]),
            "report_path": str(DEVELOPMENT_REPORT_PATH),
            "report_sha256": file_sha256(DEVELOPMENT_REPORT_PATH),
        }
    except BaseException as error:
        engine.atomic_write_json(
            OUTPUT_ROOT / "development_failure.json",
            {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign302_development_failure",
                "status": "failed_preserved_no_unfrozen_recovery",
                "created_at": campaign286.utc_now(),
                "error_type": type(error).__name__,
                "error": str(error),
                "training_or_validation_returns_may_have_been_read": True,
                "stress_2024_2025_opened": False,
                "provider_request_issued": False,
                "candidate49_changed": False,
            },
        )
        raise


def verify() -> dict[str, Any]:
    validate_static_context()
    validate_design_freeze()
    if DESIGN_EVIDENCE_PATH.exists():
        validate_development_freeze()
        evidence = load_json(DESIGN_EVIDENCE_PATH)
        for fold in FOLDS:
            load_fold_design(int(fold["fold"]), evidence)
    if DEVELOPMENT_REPORT_PATH.exists():
        report = load_json(DEVELOPMENT_REPORT_PATH)
        require_file(
            TRIAL_LEDGER_PATH,
            str((report.get("ledger") or {})["sha256"]),
            "Campaign302 trial ledger",
        )
        require_file(
            SURVIVORS_PATH,
            str((report.get("survivors") or {})["sha256"]),
            "Campaign302 survivors",
        )
    return {
        "status": "verified_campaign302_current_stage",
        "design_exists": DESIGN_EVIDENCE_PATH.exists(),
        "development_exists": DEVELOPMENT_REPORT_PATH.exists(),
        "stress_2024_2025_opened": False,
        "candidate49_changed": False,
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)
    subcommands.add_parser("plan-design")
    design = subcommands.add_parser("build-design")
    design.add_argument("--confirm-build", action="store_true")
    subcommands.add_parser("plan-development")
    development = subcommands.add_parser("run-development")
    development.add_argument("--confirm-run", action="store_true")
    subcommands.add_parser("verify")
    return command


def main() -> int:
    args = parser().parse_args()
    if args.command == "plan-design":
        payload = plan_design()
    elif args.command == "build-design":
        payload = build_design(args.confirm_build)
    elif args.command == "plan-development":
        payload = plan_development()
    elif args.command == "run-development":
        payload = run_development(args.confirm_run)
    elif args.command == "verify":
        payload = verify()
    else:
        raise Campaign302Error(f"unsupported command: {args.command}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

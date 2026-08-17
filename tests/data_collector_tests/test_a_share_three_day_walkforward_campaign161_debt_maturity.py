from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign161_debt_maturity as campaign161,
)


def _row(
    code: str = "600519",
    *,
    report_date: Any = "2023-12-31 00:00:00",
    notice_date: Any = "2024-03-31 00:00:00",
    short_loan: Any = 10.0,
    short_bond: Any = 20.0,
    due_one_year: Any = 30.0,
    long_loan: Any = 30.0,
    bond_payable: Any = 10.0,
) -> dict[str, Any]:
    exchange = "SH" if code.startswith("6") else "SZ"
    return {
        "SECUCODE": f"{code}.{exchange}",
        "SECURITY_CODE": code,
        "REPORT_DATE": report_date,
        "NOTICE_DATE": notice_date,
        "SHORT_LOAN": short_loan,
        "SHORT_BOND_PAYABLE": short_bond,
        "NONCURRENT_LIAB_1YEAR": due_one_year,
        "LONG_LOAN": long_loan,
        "BOND_PAYABLE": bond_payable,
    }


def _isolated_paths(tmp_path: Path) -> campaign161.AcceptancePaths:
    root = tmp_path / "source"
    accepted = root / "acceptance_2023q4_v1"
    return campaign161.AcceptancePaths(
        source_root=root,
        accepted_root=accepted,
        intent=root / "intent.json",
        acceptance_record=root / "record.json",
        failure_record=root / "failure.json",
        lock=root / ".lock",
    )


def test_frozen_formula_uses_all_five_components_and_higher_is_more_long_term() -> None:
    base = campaign161.compute_debt_maturity_resilience(_row())
    more_long = campaign161.compute_debt_maturity_resilience(
        _row(long_loan=70.0, bond_payable=10.0)
    )

    assert base == pytest.approx((60.0, 40.0, 0.4))
    assert more_long == pytest.approx((60.0, 80.0, 80.0 / 140.0))
    assert more_long is not None and base is not None
    assert more_long[2] > base[2]


def test_missing_negative_and_zero_total_rows_are_missing_not_repaired() -> None:
    rows = [
        _row("600519"),
        _row("000001", short_loan=None),
        _row("300750", bond_payable=-1.0),
        _row(
            "002345",
            short_loan=0.0,
            short_bond=0.0,
            due_one_year=0.0,
            long_loan=0.0,
            bond_payable=0.0,
        ),
    ]

    frame, quality = campaign161.canonicalize_rows(rows)

    assert frame["instrument"].tolist() == ["SH600519"]
    assert quality["missing_nonfinite_or_negative_component_rows_excluded"] == 2
    assert quality["nonpositive_total_borrowing_rows_excluded"] == 1
    assert frame.loc[0, "eastmoney_debt_maturity_resilience"] == pytest.approx(0.4)


def test_missing_key_duplicate_or_partition_date_mismatch_fails_closed() -> None:
    missing = _row()
    missing.pop("SHORT_BOND_PAYABLE")
    with pytest.raises(campaign161.Campaign161SchemaError, match="missing_required"):
        campaign161.canonicalize_rows([missing])

    with pytest.raises(campaign161.Campaign161SchemaError, match="duplicate"):
        campaign161.canonicalize_rows([_row(), _row()])

    with pytest.raises(campaign161.Campaign161SchemaError, match="inconsistent"):
        campaign161.canonicalize_rows([_row(report_date="2023-09-30")])


def test_count_complete_fetch_uses_exact_projection_without_live_network() -> None:
    calls: list[tuple[str, dict[str, str], int]] = []
    page_rows = [[_row("600519")], [_row("000001")]]

    class Response:
        def __init__(self, page_number: int):
            self.page_number = page_number

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "result": {
                    "pages": 2,
                    "count": 2,
                    "data": page_rows[self.page_number - 1],
                }
            }

    class Session:
        def get(self, url: str, *, params: dict[str, str], timeout: int) -> Response:
            calls.append((url, dict(params), timeout))
            return Response(int(params["pageNumber"]))

    clock_value = [0.0]

    def clock() -> float:
        return clock_value[0]

    def sleep(seconds: float) -> None:
        clock_value[0] += seconds

    rows, receipt = campaign161.fetch_partition(
        session=Session(), sleeper=sleep, monotonic=clock
    )

    assert rows == page_rows[0] + page_rows[1]
    assert receipt["requested_pages"] == [1, 2]
    assert receipt["advertised_rows"] == receipt["received_rows"] == 2
    assert receipt["http_attempts"] == 2
    assert [call[1]["pageNumber"] for call in calls] == ["1", "2"]
    assert all(call[0] == campaign161.ENDPOINT for call in calls)
    assert all(
        call[1]["columns"] == ",".join(campaign161.RAW_COLUMNS) for call in calls
    )
    assert all("REPORT_DATE='2023-12-31'" in call[1]["filter"] for call in calls)


def test_fetch_rejects_missing_required_key_without_retry() -> None:
    row = _row()
    row.pop("LONG_LOAN")
    calls = [0]

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"result": {"pages": 1, "count": 1, "data": [row]}}

    class Session:
        def get(self, *args: Any, **kwargs: Any) -> Response:
            calls[0] += 1
            return Response()

    with pytest.raises(campaign161.Campaign161SchemaError, match="missing_required"):
        campaign161.fetch_partition(
            session=Session(), sleeper=lambda _: None, monotonic=lambda: 0.0
        )
    assert calls[0] == 1


def test_plan_is_local_only_and_one_shot_paths_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _isolated_paths(tmp_path)
    monkeypatch.setattr(
        campaign161,
        "fetch_partition",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("plan must not fetch")
        ),
    )

    plan = campaign161.build_plan(paths)

    assert plan["ready"] is True
    assert plan["provider_request_issued"] is False
    assert plan["credential_presence_value_or_digest_read"] is False
    assert plan["price_or_return_value_read"] is False
    paths.intent.parent.mkdir(parents=True)
    paths.intent.write_text("{}\n", encoding="utf-8")
    consumed = campaign161.build_plan(paths)
    assert consumed["ready"] is False
    assert "intent_absent" in consumed["blockers"]


def test_run_rejection_persists_no_raw_response_and_cannot_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _isolated_paths(tmp_path)
    monkeypatch.setattr(
        campaign161,
        "fetch_partition",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            campaign161.Campaign161SchemaError("synthetic_schema_failure")
        ),
    )

    with pytest.raises(campaign161.Campaign161Error, match="synthetic_schema"):
        campaign161.run_acceptance(confirm_run=True, paths=paths)

    failure = campaign161._load_json(paths.failure_record, "test")
    assert failure["provider_raw_response_persisted"] is False
    assert failure["price_or_return_value_read"] is False
    assert failure["acceptance_retry_allowed"] is False
    assert campaign161.build_plan(paths)["ready"] is False


def test_contract_rejects_semantic_mutation_even_if_json_remains_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = copy.deepcopy(campaign161.load_contract())
    contract["factor"]["direction"] = "lower_is_better"
    changed = tmp_path / "contract.json"
    changed.write_text(
        campaign161._json_bytes(contract).decode("utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(campaign161, "CONTRACT_PATH", changed)
    monkeypatch.setattr(
        campaign161, "CONTRACT_SHA256", campaign161.file_sha256(changed)
    )

    with pytest.raises(campaign161.Campaign161Error, match="semantics_changed"):
        campaign161.load_contract()

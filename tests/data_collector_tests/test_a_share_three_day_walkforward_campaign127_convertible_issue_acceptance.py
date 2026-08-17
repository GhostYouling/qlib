import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign127_convertible_issue_acceptance.py"
)
RESULT_DATE = {
    2018: "20180105",
    2019: "20190104",
    2020: "20200103",
    2021: "20210105",
    2022: "20220105",
    2023: "20230104",
    2024: "20240105",
    2025: "20250106",
}


def load_module():
    spec = importlib.util.spec_from_file_location(
        "a_share_three_day_walkforward_campaign127_convertible_issue_acceptance",
        MODULE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bond_code(index: int) -> str:
    return f"{110000 + index:06d}.SH"


def stock_code(index: int) -> str:
    return f"{600000 + index:06d}.SH"


def basic_row(index: int) -> dict:
    return {
        "ts_code": bond_code(index),
        "stk_code": stock_code(index),
        "cb_type": "CB",
    }


def issue_row(index: int, year: int) -> dict:
    return {
        "ts_code": bond_code(index),
        "ann_date": RESULT_DATE[year],
        "res_ann_date": RESULT_DATE[year],
        "onl_pch_excess": 10.0 + index,
    }


class Client:
    def __init__(self, basic_rows, issues_by_year):
        self.basic_rows = basic_rows
        self.issues_by_year = issues_by_year
        self.calls = []

    def cb_basic(self, **kwargs):
        self.calls.append(("cb_basic", kwargs))
        return pd.DataFrame(self.basic_rows, columns=("ts_code", "stk_code", "cb_type"))

    def cb_issue(self, **kwargs):
        self.calls.append(("cb_issue", kwargs))
        year = int(kwargs["start_date"][:4])
        return pd.DataFrame(
            self.issues_by_year.get(year, []),
            columns=("ts_code", "ann_date", "res_ann_date", "onl_pch_excess"),
        )


def complete_source():
    basics = []
    issues_by_year = {year: [] for year in range(2018, 2026)}
    index = 1
    for year in range(2018, 2026):
        count = 30 if year in range(2019, 2024) else 5
        for _ in range(count):
            basics.append(basic_row(index))
            issues_by_year[year].append(issue_row(index, year))
            index += 1
    return basics, issues_by_year


def test_collect_uses_one_basic_and_eight_nonretrying_annual_calls() -> None:
    module = load_module()
    client = Client([], {})
    basic_rows, issue_rows, receipts = module.collect_projected_rows(client)
    assert basic_rows == []
    assert issue_rows == []
    assert len(receipts) == len(client.calls) == 9
    assert client.calls[0] == (
        "cb_basic",
        {"fields": "ts_code,stk_code,cb_type"},
    )
    assert [call[1]["start_date"] for call in client.calls[1:]] == [
        f"{year}0101" for year in range(2018, 2026)
    ]
    assert all(
        call[1]["fields"] == "ts_code,ann_date,res_ann_date,onl_pch_excess"
        for call in client.calls[1:]
    )


def test_projection_mismatch_and_suspected_truncation_fail_closed() -> None:
    module = load_module()

    class BadBasic(Client):
        def cb_basic(self, **kwargs):
            return pd.DataFrame(columns=["ts_code", "bond_short_name"])

    with pytest.raises(module.Campaign127AcceptanceError, match="projection"):
        module.collect_projected_rows(BadBasic([], {}))

    class Truncated(Client):
        def cb_basic(self, **kwargs):
            return pd.DataFrame([basic_row(1)] * 2000, columns=module.BASIC_FIELDS)

    with pytest.raises(module.Campaign127AcceptanceError, match="truncation"):
        module.collect_projected_rows(Truncated([], {}))


def test_provider_call_counter_preserves_partial_failure_position() -> None:
    module = load_module()

    class FailsOnSecondIssue(Client):
        def cb_issue(self, **kwargs):
            self.calls.append(("cb_issue", kwargs))
            if len(self.calls) == 3:
                raise RuntimeError("synthetic provider failure")
            return pd.DataFrame(columns=module.ISSUE_FIELDS)

    client = FailsOnSecondIssue([], {})
    counter = [0]
    with pytest.raises(RuntimeError, match="synthetic provider failure"):
        module.collect_projected_rows(client, provider_call_counter=counter)
    assert counter == [3]
    assert len(client.calls) == 3


def test_fixed_source_coverage_acceptance_passes_without_factor_panel_or_returns() -> (
    None
):
    module = load_module()
    basics, issues_by_year = complete_source()
    basic_rows, issue_rows, receipts = module.collect_projected_rows(
        Client(basics, issues_by_year)
    )
    events, evidence = module.evaluate_source_acceptance(
        basic_rows, issue_rows, receipts
    )
    assert len(events) == 165
    assert evidence["supported_events_total_2019_2023"] == 150
    assert all(evidence["checks"].values())
    assert (
        evidence["factor_panel_comparator_price_or_forward_return_values_read"] is False
    )
    assert (
        evidence["adapter_stats"]["forbidden_fields_read_requested_or_persisted"]
        is False
    )


def test_coverage_and_receipt_sequence_fail_closed() -> None:
    module = load_module()
    receipts = [{"api": "cb_basic", "year": None, "rows": 0}] + [
        {"api": "cb_issue", "year": year, "rows": 0} for year in range(2018, 2026)
    ]
    with pytest.raises(module.Campaign127AcceptanceError, match="coverage"):
        module.evaluate_source_acceptance([], [], receipts)
    bad = list(receipts)
    bad[1] = {"api": "cb_issue", "year": 2019, "rows": 0}
    with pytest.raises(module.Campaign127AcceptanceError, match="year"):
        module.evaluate_source_acceptance([], [], bad)


def test_plan_does_not_create_client_or_provider_request(monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(
        module,
        "_provider_client",
        lambda token: (_ for _ in ()).throw(AssertionError("provider called")),
    )
    plan = module.build_plan(inspect_credential=False)
    assert plan["provider_request_issued"] is False
    assert plan["maximum_provider_calls"] == 9
    assert plan["cb_basic_request_fields"] == list(module.BASIC_FIELDS)
    assert plan["cb_issue_request_fields"] == list(module.ISSUE_FIELDS)


def test_safe_dotenv_requires_mode_unique_nonempty_token_and_prints_nothing(
    tmp_path, capsys
) -> None:
    module = load_module()
    dotenv = tmp_path / ".env"
    dotenv.write_text('TUSHARE_TOKEN="secret-value"\n', encoding="utf-8")
    dotenv.chmod(0o600)
    assert module._safe_dotenv_token(dotenv) == "secret-value"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    dotenv.write_text("TUSHARE_TOKEN=a\nTUSHARE_TOKEN=b\n", encoding="utf-8")
    with pytest.raises(module.Campaign127AcceptanceError, match="duplicate"):
        module._safe_dotenv_token(dotenv)
    dotenv.write_text("TUSHARE_TOKEN=x\n", encoding="utf-8")
    dotenv.chmod(0o644)
    with pytest.raises(module.Campaign127AcceptanceError, match="mode"):
        module._safe_dotenv_token(dotenv)


def test_run_requires_both_explicit_confirmation_flags() -> None:
    module = load_module()
    with pytest.raises(module.Campaign127AcceptanceError, match="confirmation"):
        module.run_acceptance(confirm_run=True, confirm_provider_request=False)
    with pytest.raises(module.Campaign127AcceptanceError, match="confirmation"):
        module.run_acceptance(confirm_run=False, confirm_provider_request=True)


def test_failure_record_is_sanitized_and_exclusive(tmp_path, monkeypatch) -> None:
    module = load_module()
    failure = tmp_path / "failure.json"
    monkeypatch.setattr(module, "FAILURE_PATH", failure)
    module._write_failure("provider_permission_or_request_failure", 1)
    record = json.loads(failure.read_text(encoding="utf-8"))
    assert record["exception_message_persisted"] is False
    assert record["credential_value_printed_hashed_or_persisted"] is False
    assert record["raw_provider_rows_or_counts_persisted"] is False
    module._write_failure("different", 2)
    assert json.loads(failure.read_text(encoding="utf-8")) == record

#!/usr/bin/env python3
"""Ingest auditable A-share intraday and event data from licensed providers.

This tool deliberately does not replace ``a_share_data_pipeline.py``.  The
existing pipeline remains the daily OHLCV source used by the production-like
selection workflow.  This script stores paid/credentialed data separately,
with a manifest for each immutable download snapshot, so that a research run
can always identify its provider, retrieval time, and raw input files.

Supported providers
-------------------
* ``baostock``: anonymous raw five-minute OHLCV/amount candidate history.
* ``tushare``: minute OHLCV plus end-of-day moneyflow, limit prices,
  historical ST status, and top-list events.  The richer limit-list table is
  optional because it requires a higher entitlement.
* ``jqdata``: minute OHLCV plus separately licensed professional daily moneyflow.
* ``rqdata``: minute OHLCV.

Credentials are read only from environment variables.  Never place a token or
password in a command line, a config file committed to git, or a run manifest.
"""

from __future__ import annotations

import argparse
import atexit
import concurrent.futures
import datetime as dt
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import shutil
import tempfile
import time
import unicodedata
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw" / "a_share" / "rich"
METADATA_ROOT = DATA_ROOT / "metadata" / "rich_data"
RUNS_ROOT = METADATA_ROOT / "runs"
ALIGNMENTS_ROOT = METADATA_ROOT / "alignments"
FEATURE_RUNS_ROOT = METADATA_ROOT / "feature_runs"
DERIVED_ROOT = DATA_ROOT / "derived" / "a_share" / "rich"
DAILY_RAW_DIR = DATA_ROOT / "raw" / "a_share" / "daily"
DEFAULT_MINUTE_FACTOR_SPEC = (
    REPO_ROOT / "docs" / "a_share_minute_factor_preregistration.json"
)
DEFAULT_JQDATA_MONEYFLOW_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_jqdata_moneyflow_data_contract.json"
)
DEFAULT_TUSHARE_MONEYFLOW_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_moneyflow_data_contract.json"
)
DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_northbound_top10_data_contract.json"
)
DEFAULT_TUSHARE_TOP_INST_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_top_inst_data_contract.json"
)
DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_top10_float_concentration_data_contract.json"
)
DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_cash_conversion_data_contract.json"
)
DEFAULT_TUSHARE_CASH_CONVERSION_ACCEPTANCE_RECORD = (
    REPO_ROOT / "docs" / "a_share_tushare_cash_conversion_source_acceptance_record.json"
)
DEFAULT_TUSHARE_CASH_CONVERSION_COMPANY_TYPE_REPAIR = (
    REPO_ROOT / "docs" / "a_share_tushare_cash_conversion_company_type_repair.json"
)
DEFAULT_TUSHARE_CASH_CONVERSION_RESEARCH_RECORD = (
    REPO_ROOT / "docs" / "a_share_tushare_cash_conversion_research_record.json"
)
DEFAULT_TUSHARE_EARNINGS_FORECAST_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_earnings_forecast_data_contract.json"
)
DEFAULT_TUSHARE_EARNINGS_FORECAST_ACCEPTANCE_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_earnings_forecast_source_acceptance_record.json"
)
DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_disclosure_promptness_data_contract.json"
)
DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_ACCEPTANCE_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_disclosure_promptness_source_acceptance_record.json"
)
DEFAULT_TUSHARE_AUDIT_OPINION_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_audit_opinion_data_contract.json"
)
DEFAULT_TUSHARE_AUDIT_OPINION_ACCEPTANCE_RECORD = (
    REPO_ROOT / "docs" / "a_share_tushare_audit_opinion_source_acceptance_record.json"
)
DEFAULT_TUSHARE_GROSS_MARGIN_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_gross_margin_data_contract.json"
)
DEFAULT_TUSHARE_GROSS_MARGIN_ACCEPTANCE_RECORD = (
    REPO_ROOT / "docs" / "a_share_tushare_gross_margin_source_acceptance_record.json"
)
DEFAULT_TUSHARE_GROSS_MARGIN_RESEARCH_RECORD = (
    REPO_ROOT / "docs" / "a_share_tushare_gross_margin_research_record.json"
)
DEFAULT_TUSHARE_MANAGEMENT_CONTINUITY_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_management_continuity_data_contract.json"
)
DEFAULT_TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_management_continuity_source_acceptance_record.json"
)
DEFAULT_TUSHARE_ST_RECOVERY_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_st_recovery_data_contract.json"
)
DEFAULT_TUSHARE_ST_RECOVERY_ACCEPTANCE_RECORD = (
    REPO_ROOT / "docs" / "a_share_tushare_stock_st_source_acceptance_record.json"
)
DEFAULT_TUSHARE_ST_RECOVERY_NO_RETURN_SPEC = (
    REPO_ROOT / "docs" / "a_share_tushare_st_recovery_no_return_preregistration.json"
)
DEFAULT_TUSHARE_ST_RECOVERY_RESEARCH_RECORD = (
    REPO_ROOT / "docs" / "a_share_tushare_st_recovery_research_record.json"
)
DEFAULT_TUSHARE_DAILY_PB_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_daily_pb_data_contract.json"
)
DEFAULT_TUSHARE_DAILY_PB_CAPACITY_SPEC = (
    REPO_ROOT / "docs" / "a_share_tushare_daily_pb_capacity_preregistration.json"
)
DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_free_float_scarcity_data_contract.json"
)
DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_ACCEPTANCE_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_free_float_scarcity_source_acceptance_record.json"
)
DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_NO_RETURN_SPEC = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_free_float_scarcity_no_return_preregistration.json"
)
DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_FULL_SOURCE_RECORD = (
    REPO_ROOT / "docs" / "a_share_tushare_free_float_scarcity_full_source_record.json"
)
DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_eastmoney_balance_sheet_resilience_data_contract.json"
)
DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_ACCEPTANCE_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_eastmoney_balance_sheet_resilience_source_acceptance_record.json"
)
DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_NO_RETURN_SPEC = (
    REPO_ROOT
    / "docs"
    / "a_share_eastmoney_balance_sheet_resilience_no_return_preregistration.json"
)
DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_FULL_SOURCE_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_eastmoney_balance_sheet_resilience_full_source_record.json"
)
DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_eastmoney_core_profit_consistency_data_contract.json"
)
DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_ACCEPTANCE_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_eastmoney_core_profit_consistency_source_acceptance_record.json"
)
DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_NO_RETURN_SPEC = (
    REPO_ROOT
    / "docs"
    / "a_share_eastmoney_core_profit_consistency_no_return_preregistration.json"
)
DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_FULL_SOURCE_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_eastmoney_core_profit_consistency_full_source_record.json"
)
DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_sw_industry_breadth_data_contract.json"
)
DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_sw_industry_breadth_capacity_preregistration.json"
)
DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR = (
    REPO_ROOT / "docs" / "a_share_tushare_sw_industry_breadth_symbol_repair.json"
)
DEFAULT_BAOSTOCK_5M_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_baostock_5m_data_contract.json"
)
DEFAULT_BAOSTOCK_5M_FACTOR_SPEC = (
    REPO_ROOT / "docs" / "a_share_baostock_5m_factor_preregistration.json"
)
DEFAULT_BAOSTOCK_5M_SUSPENSION_AUDIT = (
    REPO_ROOT / "docs" / "a_share_baostock_5m_suspension_placeholder_audit.json"
)
DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT = (
    REPO_ROOT / "docs" / "a_share_baostock_5m_request_throttle_audit.json"
)
DEFAULT_FACTOR_UNIVERSE = (
    DATA_ROOT / "qlib" / "cn_a_share" / "instruments" / "factor_main_chinext_star.txt"
)
DEFAULT_BUYABLE_UNIVERSE = (
    DATA_ROOT / "qlib" / "cn_a_share" / "instruments" / "buyable_main_chinext.txt"
)
DEFAULT_LOCAL_CALENDAR = DATA_ROOT / "qlib" / "cn_a_share" / "calendars" / "day.txt"

DEFAULT_ACCEPTANCE_SYMBOLS = ("600519", "000001", "300750", "688981")
PROVIDER_REQUIREMENTS = {
    "baostock": {"package": "baostock", "environment": ()},
    "tushare": {"package": "tushare", "environment": ("TUSHARE_TOKEN",)},
    "jqdata": {
        "package": "jqdatasdk",
        "environment": ("JQDATA_USERNAME", "JQDATA_PASSWORD"),
    },
    "rqdata": {
        "package": "rqdatac",
        "environment": ("RQDATA_USERNAME", "RQDATA_PASSWORD"),
    },
}
DEFAULT_EVENT_DATASETS = ("moneyflow", "limit-price", "stock-st", "top-list")
EVENT_DATASETS = DEFAULT_EVENT_DATASETS + ("limit-list",)
TUSHARE_EVENT_PERMISSION_POINTS = {
    "moneyflow": 2_000,
    "limit-price": 2_000,
    "stock-st": 3_000,
    "top-list": 2_000,
    "limit-list": 5_000,
}
TUSHARE_EVENT_KEY_FIELDS = {
    "moneyflow": ("trade_date", "ts_code"),
    "limit-price": ("trade_date", "ts_code"),
    "stock-st": ("trade_date", "ts_code"),
    "top-list": ("trade_date", "ts_code", "reason"),
    "limit-list": ("trade_date", "ts_code"),
}
MINUTE_FEATURE_EXPECTED_BARS = 240
MINUTE_EXPECTED_BARS_BY_FREQUENCY = {"1m": 240, "5m": 48}
MINUTE_FEATURE_NAMES = (
    "late_return_30m",
    "late_amount_share_30m",
    "late_vwap_to_day_vwap_30m",
    "opening_gap_digestion",
    "intraday_realized_volatility",
)
MINUTE_FEATURE_DIRECTIONS = ("higher", "higher", "higher", "higher", "lower")
BAOSTOCK_5M_FEATURE_NAMES = (
    "late_return_30m_5m",
    "late_amount_share_30m_5m",
    "late_vwap_to_day_vwap_30m_5m",
    "opening_gap_digestion_5m",
    "intraday_realized_volatility_5m",
)
BAOSTOCK_5M_FEATURE_DIRECTIONS = ("higher", "higher", "higher", "higher", "lower")
REQUIRED_DAILY_PRICE_BASIS = "close_known_raw_pct_chg_chain_v1"
JQDATA_MONEYFLOW_CONTRACT_SHA256 = (
    "1a3c451ecc2d1b4f8c2ef38a8de1acf4aa474bbce4f98b99dc0369bb8d9d6004"
)
TUSHARE_MONEYFLOW_CONTRACT_SHA256 = (
    "a38f8113d948a179e6cc38eb388f13fcd691fe793209703009762db6cfa81b12"
)
TUSHARE_NORTHBOUND_TOP10_CONTRACT_SHA256 = (
    "9362211f3e35cbb24c779d49d138fb757d61f7a092b61f0304d0e147a739f63e"
)
TUSHARE_TOP_INST_CONTRACT_SHA256 = (
    "0520cd8bac454f14c2434cf7b8092aaaf3ff94cdc09b5404a6b55323bf0e7461"
)
TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT_SHA256 = (
    "cec766613b49292e724cfd78090bdbec9d7c52ae8b337bceaf0ebe208c729897"
)
TUSHARE_CASH_CONVERSION_CONTRACT_SHA256 = (
    "54584d758fc0846d90281fecedc7b90113823bb56b55d4782e749a9a5212ee01"
)
TUSHARE_CASH_CONVERSION_ACCEPTANCE_RECORD_SHA256 = (
    "615f0b794c165569b3d89444c594ee16fc60c628b36f0f834c759e09167fe962"
)
TUSHARE_CASH_CONVERSION_COMPANY_TYPE_REPAIR_SHA256 = (
    "0ac8c8caecafc92fd7af4626588b9f9830c1828ed40dd45b18bbc7522aa8bc80"
)
TUSHARE_CASH_CONVERSION_RESEARCH_RECORD_SHA256 = (
    "c1678755db519ae6645b7f1dd3ba61e768e36dc3976c8cef7d5b2e44ff45a819"
)
TUSHARE_EARNINGS_FORECAST_CONTRACT_SHA256 = (
    "4d2503381f3f7afcd02fcb80ed2a3a6ea06bddb0d1bb2831523ef0a7796c781b"
)
TUSHARE_EARNINGS_FORECAST_ACCEPTANCE_RECORD_SHA256 = (
    "38b966eea1728769ca977c1e26733527fc908846188e4727f2d76b716e97878b"
)
TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT_SHA256 = (
    "dece34e99134b1ba0f55f7970833d7b0835e756f99a81f335a9c6af4795fa47c"
)
TUSHARE_DISCLOSURE_PROMPTNESS_ACCEPTANCE_RECORD_SHA256 = (
    "2096e48a6126126e7fb4fd612e6f443a57e43df43bcfc45aa384d2574797e3ef"
)
TUSHARE_AUDIT_OPINION_CONTRACT_SHA256 = (
    "701240585505558cf34a3e9bc51ba17fb2c50ed1617fc13b332973b331c76d97"
)
TUSHARE_AUDIT_OPINION_ACCEPTANCE_RECORD_SHA256 = (
    "f5909c8114eb8505de1f86eab75ccf246938d9c537d7bbaf0f308d09e3dfce92"
)
TUSHARE_GROSS_MARGIN_CONTRACT_SHA256 = (
    "7d0bd69e72aa40a7426ea98444952caae35ce593647123684d376dd12a82d215"
)
TUSHARE_GROSS_MARGIN_ACCEPTANCE_RECORD_SHA256 = (
    "86d90ecf0c47e97489c358762abf1d2f7a9eb07260fa1aae62d6587eea4e2637"
)
TUSHARE_GROSS_MARGIN_RESEARCH_RECORD_SHA256 = (
    "83b9c930f1456ef748aa54765123d247dc330635f33c33ae8f675395c8cd3d18"
)
TUSHARE_MANAGEMENT_CONTINUITY_CONTRACT_SHA256 = (
    "86d7abc96da30c3e4825f1fcefa6722941b18f86ae3798ad6ad1db676c9323ec"
)
TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_RECORD_SHA256 = (
    "e42380d3bbf4509c25533fc8f0b9eec7113bdf219b14ab78a86e50ea6aa703a8"
)
TUSHARE_ST_RECOVERY_CONTRACT_SHA256 = (
    "cae22e7c7f8bf8c6e14587d5e7f260664c8080c579c52561ef0253d7c8a7ca9e"
)
TUSHARE_ST_RECOVERY_ACCEPTANCE_RECORD_SHA256 = (
    "e1798221e8758bd2d39ee0f7f611d9c3299b8fcbf824fa9df6e7627c61bd8d0f"
)
TUSHARE_ST_RECOVERY_NO_RETURN_SPEC_SHA256 = (
    "50c885bebe89c3e5e8b674afc86b3320639619431c17cad27f9fc4d00474a795"
)
TUSHARE_ST_RECOVERY_RESEARCH_RECORD_SHA256 = (
    "bbed853556c603a154501d59196ab353299b1ce4199a6bbd978197b01d37e067"
)
TUSHARE_DAILY_PB_CONTRACT_SHA256 = (
    "cd5c95636d9efa8eb975190072dfe94c4ee6da954dd4d9d6826d2c0b391ebdd2"
)
TUSHARE_DAILY_PB_CAPACITY_SPEC_SHA256 = (
    "14668ad3f97cef68cd2fae882507280ef835c0f5e7b4ddecb763c1907590c0a0"
)
TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT_SHA256 = (
    "a5897cf4bda28bb55e4a0f5c8db6fc328e916c68494e71931a313357d43bc1eb"
)
TUSHARE_FREE_FLOAT_SCARCITY_ACCEPTANCE_RECORD_SHA256 = (
    "7f3a929b08ca4da2a95284bca557e3ff3783bbc747cf31e821c5f48a8e2c125d"
)
TUSHARE_FREE_FLOAT_SCARCITY_NO_RETURN_SPEC_SHA256 = (
    "963e8c7d9f41da9c0ea7287399960ee5ecfdf02a1372cada25c6f7b7184f700f"
)
TUSHARE_FREE_FLOAT_SCARCITY_FULL_SOURCE_RECORD_SHA256 = (
    "2d9855e286e8fd8233e9bafe38301e2381fc4d2ca221a4a69626d580285adc13"
)
EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT_SHA256 = (
    "44c3fa5498cbc644f7b7de07c3c53d6d8f7af6a9a367922929d458706133e5a4"
)
EASTMONEY_BALANCE_SHEET_RESILIENCE_MECHANISM_AUDIT_SHA256 = (
    "ea3522891cee10446b01ba79ee875bdb9c16ac9ad63470b5894253a4ee0968ca"
)
EASTMONEY_BALANCE_SHEET_RESILIENCE_ACCEPTANCE_RECORD_SHA256 = (
    "9a014c7bfa25cfe40f1a5deca0168fe28f5c98f10c1da2bc782366cb15c94baf"
)
EASTMONEY_BALANCE_SHEET_RESILIENCE_NO_RETURN_SPEC_SHA256 = (
    "fac1c2aefb4c263704e7d93ff7affa6d7e1aa085e1f86dac04c18029ac632a6c"
)
EASTMONEY_BALANCE_SHEET_RESILIENCE_FULL_SOURCE_RECORD_SHA256 = (
    "8c523f2e5b2b14cb46b98a9becf114ef5efab582af2b84482524f6676caf6cc6"
)
EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT_SHA256 = (
    "2ae3be4b134e16681e702171157b48e8be5bc6c1f72aa9cecfc9a285518d7a45"
)
EASTMONEY_CORE_PROFIT_CONSISTENCY_MECHANISM_AUDIT_SHA256 = (
    "ca5ac438068dbf8d1911658ec4fcd72e20196d748ba1cfda4d610a105e96ed82"
)
EASTMONEY_CORE_PROFIT_CONSISTENCY_ACCEPTANCE_RECORD_SHA256 = (
    "1372ee0af59cf45e4f46659ba05730d0cbaac99232f49464b014e578cd89bf34"
)
EASTMONEY_CORE_PROFIT_CONSISTENCY_NO_RETURN_SPEC_SHA256 = (
    "47884d88736a19715bb3a615f9941611309322f9d6f1f1f4a0456ce924fb3943"
)
EASTMONEY_CORE_PROFIT_CONSISTENCY_FULL_SOURCE_RECORD_SHA256 = (
    "be6d43b7fb1e707898b88180c5d5a180bb4e28620fb8d9c646ef1c58cb7604fb"
)
TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256 = (
    "e8dc45f6302bb6a4f1173da3698064bf7133930616b2fcd3338061f2fc508e66"
)
TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC_SHA256 = (
    "dc5e0525df07e21d628ab09d46843511ddbeacb09ecbc3afb41d14b43bcfae59"
)
TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR_SHA256 = (
    "5001ae0b278d086f26ca35bf8a1fc43c8009aa99c13b03258e7b2fb7bc99b18f"
)
BAOSTOCK_5M_CONTRACT_SHA256 = (
    "3352497aa911f69ced631fac57db1369eaa12acabad8ca7857f6254205354a8f"
)
BAOSTOCK_5M_FACTOR_SPEC_SHA256 = (
    "a6b679c1476cacfc193aba5bf93988c92691025872150d3eaab723576c7164b8"
)
BAOSTOCK_5M_SUSPENSION_AUDIT_SHA256 = (
    "5c29bd194ef70ed0d30a1e72aa3adc7e287ec1f513e0d3ee29d7551cf1dff47d"
)
BAOSTOCK_5M_THROTTLE_AUDIT_SHA256 = (
    "4a881c707f41dc1a1043015ca004b65ff4607bc96bce21cd65c832cb20dc18aa"
)
BAOSTOCK_5M_MINIMUM_FREE_BYTES = 10 * 1024**3
BAOSTOCK_5M_MAX_WORKERS = 4
BAOSTOCK_5M_PARTITION_RETRIES = 3
BAOSTOCK_5M_RESTORATION_PROBE_MAX_AGE_MINUTES = 30
JQDATA_MONEYFLOW_RAW_FIELDS = (
    "inflow_xl",
    "inflow_l",
    "inflow_m",
    "inflow_s",
    "outflow_xl",
    "outflow_l",
    "outflow_m",
    "outflow_s",
)
JQDATA_MONEYFLOW_COLUMNS = (
    "trade_date",
    "instrument",
    "inflow_xl_amount",
    "inflow_l_amount",
    "inflow_m_amount",
    "inflow_s_amount",
    "outflow_xl_amount",
    "outflow_l_amount",
    "outflow_m_amount",
    "outflow_s_amount",
    "jqdata_large_order_net_inflow_share",
    "provider",
)
TUSHARE_MONEYFLOW_AMOUNT_FIELDS = (
    "buy_sm_amount",
    "sell_sm_amount",
    "buy_md_amount",
    "sell_md_amount",
    "buy_lg_amount",
    "sell_lg_amount",
    "buy_elg_amount",
    "sell_elg_amount",
)
TUSHARE_MONEYFLOW_RAW_FIELDS = (
    "ts_code",
    "trade_date",
    *TUSHARE_MONEYFLOW_AMOUNT_FIELDS,
)
TUSHARE_MONEYFLOW_COLUMNS = (
    "trade_date",
    "instrument",
    *TUSHARE_MONEYFLOW_AMOUNT_FIELDS,
    "tushare_large_order_net_inflow_share",
    "provider",
)
TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS = (
    "trade_date",
    "ts_code",
    "rank",
    "market_type",
    "amount",
    "buy",
    "sell",
)
TUSHARE_NORTHBOUND_TOP10_COLUMNS = (
    "trade_date",
    "instrument",
    "rank",
    "market_type",
    "amount",
    "buy",
    "sell",
    "tushare_northbound_top10_net_buy_share",
    "provider",
)
TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES = ("1", "3")
TUSHARE_TOP_INST_RAW_FIELDS = (
    "trade_date",
    "ts_code",
    "exalter",
    "buy",
    "sell",
    "net_buy",
)
TUSHARE_TOP_INST_COLUMNS = (
    "trade_date",
    "instrument",
    "institution_seat_count",
    "buy",
    "sell",
    "tushare_top_inst_net_buy_share",
    "provider",
)
TUSHARE_EARNINGS_FORECAST_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "end_date",
    "type",
    "p_change_min",
    "p_change_max",
    "first_ann_date",
)
TUSHARE_EARNINGS_FORECAST_COLUMNS = (
    "announcement_date",
    "first_announcement_date",
    "report_period",
    "instrument",
    "forecast_type",
    "p_change_min",
    "p_change_max",
    "tushare_earnings_forecast_growth_midpoint",
    "provider",
)
TUSHARE_EARNINGS_FORECAST_COMPARABLE_TYPES = frozenset(
    {"预增", "略增", "续盈", "预减", "略减"}
)
TUSHARE_EARNINGS_FORECAST_NONCOMPARABLE_TYPES = frozenset({"扭亏", "首亏", "续亏"})
TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "end_date",
    "pre_date",
    "modify_date",
)
TUSHARE_DISCLOSURE_PROMPTNESS_COLUMNS = (
    "announcement_date",
    "report_period",
    "planned_disclosure_date",
    "instrument",
    "tushare_disclosure_plan_lead_days",
    "provider",
)
TUSHARE_DISCLOSURE_PROMPTNESS_ACCEPTANCE_PERIODS = (
    "20191231",
    "20241231",
    "20251231",
)
TUSHARE_DISCLOSURE_PROMPTNESS_FULL_PERIODS = tuple(
    f"{year}{month_day}"
    for year in range(2019, 2026)
    for month_day in ("0331", "0630", "0930", "1231")
)
TUSHARE_AUDIT_OPINION_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "end_date",
    "audit_result",
)
TUSHARE_AUDIT_OPINION_COLUMNS = (
    "announcement_date",
    "instrument",
    "tushare_is_standard_unqualified_audit_opinion",
    "audit_report_count",
    "provider",
)
TUSHARE_AUDIT_OPINION_ACCEPTANCE_TS_CODES = (
    "600519.SH",
    "000001.SZ",
    "600518.SH",
)
TUSHARE_AUDIT_OPINION_ACCEPTANCE_START = "20190101"
TUSHARE_AUDIT_OPINION_ACCEPTANCE_END = "20251231"
TUSHARE_AUDIT_OPINION_CLEAN_TEXT = "标准无保留意见"
TUSHARE_GROSS_MARGIN_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "end_date",
    "q_gsprofit_margin",
    "update_flag",
)
TUSHARE_GROSS_MARGIN_COLUMNS = (
    "announcement_date",
    "report_period",
    "instrument",
    "tushare_q_gross_margin_yoy_change_pp",
    "provider",
)
TUSHARE_GROSS_MARGIN_ACCEPTANCE_TS_CODES = (
    "600519.SH",
    "000333.SZ",
    "300750.SZ",
)
TUSHARE_GROSS_MARGIN_ACCEPTANCE_START = "20180101"
TUSHARE_GROSS_MARGIN_ACCEPTANCE_END = "20251231"
TUSHARE_GROSS_MARGIN_FULL_SLICES = (
    ("20180101", "20211231"),
    ("20220101", "20251231"),
)
TUSHARE_MANAGEMENT_CONTINUITY_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "name",
    "end_date",
)
TUSHARE_MANAGEMENT_CONTINUITY_COLUMNS = (
    "announcement_date",
    "instrument",
    "manager_count",
    "departing_manager_count",
    "tushare_management_continuity_share",
    "provider",
)
TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_TS_CODES = (
    "000001.SZ",
    "600000.SH",
    "300750.SZ",
)
TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_START = "20190101"
TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_END = "20251231"
TUSHARE_ST_MEMBERSHIP_RAW_FIELDS = (
    "ts_code",
    "trade_date",
    "type",
)
TUSHARE_ST_MEMBERSHIP_COLUMNS = (
    "trade_date",
    "instrument",
    "provider",
)
TUSHARE_TOP10_FLOAT_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "end_date",
    "holder_name",
    "hold_float_ratio",
)
TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS = (
    "announcement_date",
    "report_period",
    "instrument",
    "holder_name_sha256",
    "hold_float_ratio",
    "provider",
)
TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS = (
    "announcement_date",
    "report_period",
    "previous_report_period",
    "instrument",
    "top10_float_holder_count",
    "top10_float_concentration_pct",
    "top10_float_concentration_change_pp",
    "provider",
)
TUSHARE_TOP10_FLOAT_ACCEPTANCE_SYMBOLS = (
    "600519.SH",
    "000001.SZ",
    "300750.SZ",
)
TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "report_type",
    "comp_type",
    "n_income_attr_p",
    "update_flag",
)
TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "report_type",
    "comp_type",
    "n_cashflow_act",
    "update_flag",
)
TUSHARE_CASH_CONVERSION_COLUMNS = (
    "announcement_date",
    "income_actual_announcement_date",
    "cashflow_actual_announcement_date",
    "report_period",
    "instrument",
    "n_income_attr_p",
    "n_cashflow_act",
    "tushare_operating_cash_conversion",
    "provider",
)
TUSHARE_CASH_CONVERSION_INCOME_COLUMNS = (
    "income_announcement_date",
    "income_actual_announcement_date",
    "report_period",
    "instrument",
    "n_income_attr_p",
    "provider",
)
TUSHARE_CASH_CONVERSION_CASHFLOW_COLUMNS = (
    "cashflow_announcement_date",
    "cashflow_actual_announcement_date",
    "report_period",
    "instrument",
    "n_cashflow_act",
    "provider",
)
TUSHARE_CASH_CONVERSION_ACCEPTANCE_SYMBOLS = (
    "600519.SH",
    "000333.SZ",
    "300750.SZ",
)
TUSHARE_CASH_CONVERSION_ADJUSTMENT_REPORT_TYPES = frozenset({3, 4, 5, 8, 9, 10, 11, 12})
TUSHARE_CASH_CONVERSION_CONTEXT_REPORT_TYPES = frozenset({2, 6, 7})
TUSHARE_CASH_CONVERSION_KNOWN_REPORT_TYPES = frozenset(range(1, 13))
TUSHARE_CASH_CONVERSION_KNOWN_COMPANY_TYPES = frozenset({1, 2, 3, 4})
TUSHARE_DAILY_PB_RAW_FIELDS = ("ts_code", "trade_date", "pb")
TUSHARE_DAILY_PB_COLUMNS = (
    "trade_date",
    "instrument",
    "pb",
    "tushare_positive_book_to_market",
    "provider",
)
TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS = (
    "ts_code",
    "trade_date",
    "total_share",
    "free_share",
)
TUSHARE_FREE_FLOAT_SCARCITY_COLUMNS = (
    "trade_date",
    "instrument",
    "total_share",
    "free_share",
    "tushare_free_float_scarcity",
    "provider",
)
EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS = (
    "instrument",
    "report_date",
    "announcement_date",
    "total_assets",
    "total_liabilities",
    "eastmoney_balance_sheet_resilience",
    "provider",
)
EASTMONEY_BALANCE_SHEET_RAW_POSITION_NAMES = (
    "stock_code",
    "announcement_date",
    "total_assets",
    "total_liabilities",
    "vendor_asset_liability_ratio_percent_for_formula_audit_only",
)
EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS = (
    "instrument",
    "report_date",
    "announcement_date",
    "operating_profit",
    "total_profit",
    "eastmoney_core_profit_consistency",
    "provider",
)
EASTMONEY_CORE_PROFIT_RAW_POSITION_NAMES = (
    "stock_code",
    "announcement_date",
    "operating_profit",
    "total_profit",
)
TUSHARE_SW_CLASSIFICATION_RAW_FIELDS = (
    "index_code",
    "industry_name",
    "level",
    "src",
)
TUSHARE_SW_MEMBERSHIP_RAW_FIELDS = (
    "l1_code",
    "l1_name",
    "l2_code",
    "l2_name",
    "l3_code",
    "l3_name",
    "ts_code",
    "in_date",
    "out_date",
    "is_new",
)
TUSHARE_SW_MEMBERSHIP_COLUMNS = (
    "l1_code",
    "l1_name",
    "l2_code",
    "l2_name",
    "l3_code",
    "l3_name",
    "instrument",
    "in_date",
    "out_date",
    "is_new",
    "provider",
)


class RichDataError(RuntimeError):
    """A recoverable provider, credential, or data-contract error."""


class RichDataProcessLock:
    """Hold one advisory lock for a long-running rich-data synchronization."""

    def __init__(self, path: Path):
        self.path = path
        self._handle: Any | None = None

    def __enter__(self) -> "RichDataProcessLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._handle.seek(0)
            owner = self._handle.read().strip() or "unknown"
            self._handle.close()
            self._handle = None
            raise RichDataError(
                f"another rich-data synchronization holds {self.path}; owner={owner}"
            ) from exc
        self._handle.seek(0)
        self._handle.truncate()
        self._handle.write(str(os.getpid()))
        self._handle.flush()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._handle is not None:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None


@dataclass(frozen=True)
class ProviderAvailability:
    """Safe provider readiness status; secrets are never represented here."""

    provider: str
    package: str
    package_installed: bool
    required_environment: tuple[str, ...]
    missing_environment: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.package_installed and not self.missing_environment


def parse_date(value: str) -> dt.date:
    """Parse a CLI ISO date."""

    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def latest_completed_session_date(now: dt.datetime | None = None) -> dt.date:
    """Conservatively avoid requesting a still-forming A-share session.

    The workspace time zone is China/Singapore.  The function intentionally
    only knows weekends; an exchange holiday will naturally return no rows and
    be recorded as such in the manifest rather than treated as a data error.
    """

    local_now = now or dt.datetime.now()
    cutoff = local_now.date()
    if local_now.weekday() < 5 and local_now.time() < dt.time(15, 30):
        cutoff -= dt.timedelta(days=1)
    while cutoff.weekday() >= 5:
        cutoff -= dt.timedelta(days=1)
    return cutoff


def qlib_symbol(code: str) -> str:
    """Convert a six-digit A-share code to the repository's symbol form."""

    code = str(code).strip().zfill(6)
    if code.startswith(("6", "9")):
        return f"SH{code}"
    if code.startswith(("0", "1", "2", "3")):
        return f"SZ{code}"
    raise RichDataError(f"unsupported A-share code: {code}")


def vendor_symbol(code: str, provider: str) -> str:
    """Return the selected provider's stock-code convention."""

    code = str(code).strip().zfill(6)
    symbol = qlib_symbol(code)
    if provider == "tushare":
        return f"{code}.{'SH' if symbol.startswith('SH') else 'SZ'}"
    if provider in {"jqdata", "rqdata"}:
        return f"{code}.{'XSHG' if symbol.startswith('SH') else 'XSHE'}"
    if provider == "baostock":
        return f"{'sh' if symbol.startswith('SH') else 'sz'}.{code}"
    raise RichDataError(f"unknown provider: {provider}")


def parse_symbols(value: str) -> list[str]:
    """Parse and de-duplicate a comma-separated A-share code list."""

    symbols = [item.strip() for item in value.split(",") if item.strip()]
    if not symbols:
        raise argparse.ArgumentTypeError("at least one symbol is required")
    normalized: list[str] = []
    for code in symbols:
        if not code.isdigit() or len(code) > 6:
            raise argparse.ArgumentTypeError(f"invalid A-share code: {code}")
        code = code.zfill(6)
        qlib_symbol(code)
        if code not in normalized:
            normalized.append(code)
    return normalized


def provider_availability(provider: str) -> ProviderAvailability:
    """Report credential/SDK readiness without disclosing a secret's value."""

    try:
        details = PROVIDER_REQUIREMENTS[provider]
    except KeyError as exc:
        raise RichDataError(f"unknown provider: {provider}") from exc
    required = tuple(details["environment"])
    return ProviderAvailability(
        provider=provider,
        package=str(details["package"]),
        package_installed=importlib.util.find_spec(str(details["package"])) is not None,
        required_environment=required,
        missing_environment=tuple(key for key in required if not os.environ.get(key)),
    )


def require_provider(provider: str) -> None:
    """Fail before a network call when the selected provider is not usable."""

    availability = provider_availability(provider)
    if not availability.package_installed:
        raise RichDataError(
            f"{provider} SDK is not installed; run "
            "python -m pip install -r scripts/data_collector/a_share_rich/requirements.txt"
        )
    if availability.missing_environment:
        keys = ", ".join(availability.missing_environment)
        raise RichDataError(
            f"{provider} credentials are missing from the environment: {keys}"
        )


def safe_exception_text(exc: BaseException) -> str:
    """Render an exception after removing any configured provider secret values."""

    message = str(exc)
    for details in PROVIDER_REQUIREMENTS.values():
        for key in details["environment"]:
            secret = os.environ.get(str(key))
            if secret:
                message = message.replace(secret, "<redacted>")
    return message


def _column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    lookup = {str(column).casefold(): str(column) for column in frame.columns}
    for candidate in candidates:
        found = lookup.get(candidate.casefold())
        if found is not None:
            return found
    return None


def canonicalize_minute_bars(
    frame: pd.DataFrame,
    provider: str,
    code: str,
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:
    """Normalize provider bars to a strict, unadjusted minute-bar contract.

    We retain raw, unadjusted prices.  Adjustment is deliberately deferred to
    downstream factor construction and must use a documented as-of adjustment
    series; a vendor's mutable present-day qfq series is not point-in-time.
    """

    if frame is None or frame.empty:
        return pd.DataFrame(
            columns=[
                "datetime",
                "symbol",
                "source_symbol",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "provider",
            ]
        )
    normalized = frame.copy()
    # JQData commonly returns a DatetimeIndex without a name, while RQData can
    # return a named MultiIndex.  Both carry the provider timestamp in the
    # index and therefore must be made explicit before column resolution.
    if not isinstance(normalized.index, pd.RangeIndex):
        normalized = normalized.reset_index()
    datetime_column = _column(normalized, ("datetime", "trade_time", "time", "date"))
    if datetime_column is None:
        raise RichDataError(f"{provider} minute response has no datetime column")
    field_map = {
        "open": ("open",),
        "high": ("high",),
        "low": ("low",),
        "close": ("close",),
        "volume": ("volume", "vol"),
        "amount": ("amount", "money", "total_turnover", "turnover"),
    }
    resolved = {
        field: _column(normalized, candidates)
        for field, candidates in field_map.items()
    }
    missing = [field for field, column in resolved.items() if column is None]
    if missing:
        raise RichDataError(
            f"{provider} minute response is missing required columns: {', '.join(missing)}"
        )
    result = pd.DataFrame(
        {
            "datetime": pd.to_datetime(normalized[datetime_column], errors="coerce"),
            "symbol": qlib_symbol(code),
            "source_symbol": vendor_symbol(code, provider),
            "provider": provider,
        }
    )
    for field, column in resolved.items():
        assert column is not None
        result[field] = pd.to_numeric(normalized[column], errors="coerce")
    start_timestamp = pd.Timestamp(start)
    end_timestamp = pd.Timestamp(end) + pd.Timedelta(days=1)
    result = result.loc[
        (result["datetime"] >= start_timestamp) & (result["datetime"] < end_timestamp)
    ].copy()
    result = result.dropna(
        subset=["datetime", "open", "high", "low", "close", "volume", "amount"]
    )
    if result.empty:
        return result.sort_values("datetime").reset_index(drop=True)
    invalid_price = (
        (result[["open", "high", "low", "close"]] <= 0).any(axis=1)
        | (result["high"] < result[["open", "low", "close"]].max(axis=1))
        | (result["low"] > result[["open", "high", "close"]].min(axis=1))
        | (result["volume"] < 0)
        | (result["amount"] < 0)
    )
    if invalid_price.any():
        raise RichDataError(
            f"{provider} returned {int(invalid_price.sum())} invalid minute bars for {code}"
        )
    result = result.drop_duplicates(subset=["datetime"], keep="last").sort_values(
        "datetime"
    )
    return result.reset_index(drop=True)


def canonicalize_baostock_5m_bars(
    frame: pd.DataFrame,
    code: str,
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:
    """Normalize BaoStock bars without silently resolving duplicate timestamps."""

    source_rows = 0 if frame is None else int(len(frame))
    source_rows_by_year: dict[int, int] = {}
    placeholder_rows = 0
    placeholder_rows_by_year: dict[int, int] = {}
    placeholder_dates: list[str] = []
    normalized = frame
    if frame is not None and not frame.empty:
        normalized = frame.copy()
        if not isinstance(normalized.index, pd.RangeIndex):
            normalized = normalized.reset_index()
        datetime_column = _column(
            normalized, ("datetime", "trade_time", "time", "date")
        )
        if datetime_column is None:
            raise RichDataError("baostock minute response has no datetime column")
        timestamps = pd.to_datetime(normalized[datetime_column], errors="coerce")
        source_rows_by_year = {
            int(year): int(count)
            for year, count in timestamps.loc[timestamps.notna()]
            .dt.year.value_counts()
            .items()
        }
        if (
            timestamps.notna().any()
            and timestamps[timestamps.notna()].duplicated().any()
        ):
            raise RichDataError(
                f"BaoStock returned duplicate five-minute timestamps for {code}; "
                "the frozen contract forbids silent deduplication"
            )
        resolved = {
            field: _column(normalized, candidates)
            for field, candidates in {
                "open": ("open",),
                "high": ("high",),
                "low": ("low",),
                "close": ("close",),
                "volume": ("volume", "vol"),
                "amount": ("amount", "money", "total_turnover", "turnover"),
            }.items()
        }
        if missing := [field for field, column in resolved.items() if column is None]:
            raise RichDataError(
                "baostock minute response is missing required columns: "
                + ", ".join(missing)
            )
        numeric = pd.DataFrame(
            {
                field: pd.to_numeric(normalized[column], errors="coerce")
                for field, column in resolved.items()
                if column is not None
            }
        )
        zero_price_placeholder = (
            numeric[["open", "high", "low", "close"]].eq(0.0).all(axis=1)
            & numeric["volume"].eq(0.0)
            & numeric["amount"].eq(0.0)
        )
        placeholder_rows = int(zero_price_placeholder.sum())
        placeholder_rows_by_year = {
            int(year): int(count)
            for year, count in timestamps.loc[
                zero_price_placeholder & timestamps.notna()
            ]
            .dt.year.value_counts()
            .items()
        }
        placeholder_dates = sorted(
            timestamps.loc[zero_price_placeholder & timestamps.notna()]
            .dt.date.astype(str)
            .unique()
            .tolist()
        )
        normalized = normalized.loc[~zero_price_placeholder].copy()
    result = canonicalize_minute_bars(normalized, "baostock", code, start, end)
    result.attrs["source_rows"] = source_rows
    result.attrs["source_rows_by_year"] = source_rows_by_year
    result.attrs["zero_price_placeholder_rows_excluded"] = placeholder_rows
    result.attrs["zero_price_placeholder_rows_by_year"] = placeholder_rows_by_year
    result.attrs["zero_price_placeholder_session_dates"] = placeholder_dates
    return result


def minute_daily_summary(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Return small reconciliation summaries without duplicating the raw data."""

    if frame.empty:
        return []
    work = frame.assign(trade_date=frame["datetime"].dt.date.astype(str))
    summaries: list[dict[str, Any]] = []
    for trade_date, group in work.groupby("trade_date", sort=True):
        summaries.append(
            {
                "trade_date": trade_date,
                "bars": int(len(group)),
                "first_bar": group["datetime"].iloc[0].isoformat(),
                "last_bar": group["datetime"].iloc[-1].isoformat(),
                "last_close": float(group["close"].iloc[-1]),
                "volume": float(group["volume"].sum()),
                "amount": float(group["amount"].sum()),
            }
        )
    return summaries


def _in_regular_session(timestamp: pd.Timestamp) -> bool:
    """Accept either provider's start- or end-labelled A-share minute bar."""

    time_of_day = timestamp.time()
    return dt.time(9, 30) <= time_of_day <= dt.time(11, 30) or dt.time(
        13, 0
    ) <= time_of_day <= dt.time(15, 0)


def minute_session_check(frame: pd.DataFrame) -> dict[str, Any]:
    """Check that minute bars are timestamped inside regular A-share sessions.

    A provider may label a bar by its start (09:30) or end (09:31) minute, so
    this deliberately accepts both conventions.  Trading halts can reduce the
    count, therefore row count is diagnostic information rather than a reason
    to silently fill or reject valid source data.
    """

    if frame.empty:
        return {"status": "failed", "reason": "no_bars", "days": []}
    work = frame.assign(trade_date=frame["datetime"].dt.date.astype(str))
    days: list[dict[str, Any]] = []
    for trade_date, group in work.groupby("trade_date", sort=True):
        in_session = group["datetime"].map(_in_regular_session)
        days.append(
            {
                "trade_date": trade_date,
                "bars": int(len(group)),
                "in_regular_session_bars": int(in_session.sum()),
                "out_of_session_bars": int((~in_session).sum()),
                "first_bar": group["datetime"].iloc[0].isoformat(),
                "last_bar": group["datetime"].iloc[-1].isoformat(),
            }
        )
    return {
        "status": (
            "passed"
            if all(day["out_of_session_bars"] == 0 for day in days)
            else "failed"
        ),
        "days": days,
    }


def _relative_error(actual: float, expected: float) -> float | None:
    if not pd.notna(actual) or not pd.notna(expected) or expected == 0:
        return None
    return abs(actual / expected - 1.0)


def minute_daily_reconciliation(frame: pd.DataFrame) -> dict[str, Any]:
    """Compare minute aggregates with local daily data without mixing prices.

    Incoming minute prices and volumes are explicitly raw.  The accepted daily
    pipeline preserves matching ``raw_*`` fields alongside factor-adjusted
    research columns, so reconciliation must use the raw fields directly.
    Comparing against adjusted ``volume`` would multiply the inferred source
    unit by the current adjustment factor and can reject otherwise exact data.
    """

    if frame.empty:
        return {"status": "failed", "reason": "no_bars", "days": []}
    symbol = str(frame["symbol"].iloc[0]).lower()
    path = DAILY_RAW_DIR / f"{symbol}.parquet"
    if not path.exists():
        return {
            "status": "unavailable",
            "reason": f"missing_local_daily:{path}",
            "days": [],
        }
    daily = pd.read_parquet(path)
    required_daily = {
        "date",
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "raw_volume",
        "amount",
        "price_basis",
    }
    if missing := sorted(required_daily - set(daily.columns)):
        return {
            "status": "unavailable",
            "reason": "local_daily_missing_raw_contract:" + ",".join(missing),
            "days": [],
        }
    bases = set(daily["price_basis"].dropna().astype(str))
    if bases != {REQUIRED_DAILY_PRICE_BASIS}:
        return {
            "status": "failed",
            "reason": f"unaccepted_local_daily_price_basis:{sorted(bases)}",
            "days": [],
        }
    daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
    daily = daily.set_index("date")
    work = frame.assign(trade_date=frame["datetime"].dt.normalize())
    days: list[dict[str, Any]] = []
    for trade_date, group in work.groupby("trade_date", sort=True):
        daily_row = daily.loc[daily.index == trade_date]
        if daily_row.empty:
            days.append(
                {
                    "trade_date": trade_date.date().isoformat(),
                    "status": "missing_local_daily",
                }
            )
            continue
        reference = daily_row.iloc[-1]
        minute_close = float(group["close"].iloc[-1])
        minute_ohlc = {
            "open": float(group["open"].iloc[0]),
            "high": float(group["high"].max()),
            "low": float(group["low"].min()),
            "close": minute_close,
        }
        price_relative_errors = {
            field: _relative_error(minute_ohlc[field], float(reference[f"raw_{field}"]))
            for field in ("open", "high", "low", "close")
        }
        volume_ratio = (
            float(group["volume"].sum() / float(reference["raw_volume"]))
            if float(reference["raw_volume"])
            else None
        )
        amount_ratio = (
            float(group["amount"].sum() / float(reference["amount"]))
            if float(reference["amount"])
            else None
        )
        price_ok = all(
            error is not None and error <= 0.002
            for error in price_relative_errors.values()
        )
        amount_ok = amount_ratio is not None and abs(amount_ratio - 1.0) <= 0.005
        # The public daily pipe reports volume in lots.  Sources can report
        # shares or lots, so accept either 1x or 100x here but record the
        # inferred ratio; never rescale a provider silently.
        volume_ok = (
            volume_ratio is not None
            and min(abs(volume_ratio - 1.0), abs(volume_ratio - 100.0)) <= 0.005
        )
        days.append(
            {
                "trade_date": trade_date.date().isoformat(),
                "status": (
                    "passed" if price_ok and amount_ok and volume_ok else "failed"
                ),
                "price_relative_errors": price_relative_errors,
                "amount_ratio_to_local_daily": amount_ratio,
                "volume_ratio_to_local_daily": volume_ratio,
                "inferred_volume_unit": (
                    "shares"
                    if volume_ratio is not None and abs(volume_ratio - 100.0) <= 0.005
                    else "lots"
                ),
            }
        )
    statuses = [day["status"] for day in days]
    if statuses and all(status == "passed" for status in statuses):
        status = "passed"
    elif "missing_local_daily" in statuses:
        status = "unavailable"
    else:
        status = "failed"
    return {
        "status": status,
        "daily_price_basis": "raw_unadjusted_to_raw_daily",
        "days": days,
    }


def minute_acceptance_report(frame: pd.DataFrame) -> dict[str, Any]:
    """Run the automatic checks required before minute data may become features."""

    session = minute_session_check(frame)
    reconciliation = minute_daily_reconciliation(frame)
    passed = session["status"] == "passed" and reconciliation["status"] == "passed"
    return {
        "status": (
            "automatic_checks_passed_pending_time_alignment"
            if passed
            else "automatic_checks_failed"
        ),
        "session": session,
        "daily_reconciliation": reconciliation,
    }


def _import_tushare() -> Any:
    import tushare as ts

    ts.set_token(os.environ["TUSHARE_TOKEN"])
    return ts


def _query_baostock_5m(
    client: Any, code: str, start: dt.date, end: dt.date
) -> pd.DataFrame:
    """Query one raw partition through an already authenticated BaoStock client."""

    fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
    response = client.query_history_k_data_plus(
        vendor_symbol(code, "baostock"),
        fields,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        frequency="5",
        adjustflag="3",
    )
    if str(response.error_code) != "0":
        raise RichDataError(
            f"BaoStock five-minute query failed for {code}: {response.error_msg}"
        )
    rows: list[list[str]] = []
    while response.next():
        rows.append(response.get_row_data())
    frame = pd.DataFrame(rows, columns=response.fields)
    if frame.empty:
        return frame
    expected_fields = fields.split(",")
    if list(frame.columns) != expected_fields:
        raise RichDataError(
            "BaoStock five-minute response changed its frozen field schema"
        )
    if set(frame["adjustflag"].astype(str)) != {"3"}:
        raise RichDataError(
            "BaoStock five-minute response is not entirely raw unadjusted data"
        )
    frame["datetime"] = pd.to_datetime(
        frame["time"], format="%Y%m%d%H%M%S%f", errors="coerce"
    )
    if frame["datetime"].isna().any():
        raise RichDataError(
            "BaoStock five-minute response contains an invalid timestamp"
        )
    return frame


def fetch_baostock_minutes(
    code: str, start: dt.date, end: dt.date, frequency: str
) -> pd.DataFrame:
    """Fetch only the frozen anonymous raw five-minute BaoStock fields."""

    if frequency != "5m":
        raise RichDataError(
            "the frozen BaoStock intraday contract supports only 5m bars"
        )
    import baostock as bs

    login = bs.login()
    if str(login.error_code) != "0":
        raise RichDataError(f"BaoStock anonymous login failed: {login.error_msg}")
    try:
        frame = _query_baostock_5m(bs, code, start, end)
    finally:
        bs.logout()
    return frame


_BAOSTOCK_WORKER_CLIENT: Any | None = None


def initialize_baostock_5m_worker() -> None:
    """Authenticate one anonymous BaoStock session per process."""

    import baostock as bs

    login = bs.login()
    if str(login.error_code) != "0":
        raise RichDataError(f"BaoStock worker login failed: {login.error_msg}")
    global _BAOSTOCK_WORKER_CLIENT
    _BAOSTOCK_WORKER_CLIENT = bs
    atexit.register(bs.logout)


def fetch_baostock_5m_request_worker(
    task: tuple[str, str, str],
) -> tuple[str, str, str, pd.DataFrame]:
    """Fetch one PIT instrument interval and canonicalize it with fixed retries."""

    code, start_value, end_value = task
    if _BAOSTOCK_WORKER_CLIENT is None:
        raise RichDataError("BaoStock five-minute worker is not initialized")
    start = dt.date.fromisoformat(start_value)
    end = dt.date.fromisoformat(end_value)
    error: Exception | None = None
    for attempt in range(1, BAOSTOCK_5M_PARTITION_RETRIES + 1):
        try:
            raw = _query_baostock_5m(_BAOSTOCK_WORKER_CLIENT, code, start, end)
            frame = canonicalize_baostock_5m_bars(raw, code, start, end)
            return code, start_value, end_value, frame
        except Exception as exc:  # noqa: BLE001 - worker must preserve the final provider error.
            error = exc
            if "黑名单用户" in str(exc):
                break
            if attempt < BAOSTOCK_5M_PARTITION_RETRIES:
                time.sleep(float(attempt))
    attempts = (
        1
        if error is not None and "黑名单用户" in str(error)
        else BAOSTOCK_5M_PARTITION_RETRIES
    )
    raise RichDataError(
        f"BaoStock five-minute PIT request failed after {attempts} attempt(s): "
        f"{code} {start_value} {end_value}: {error}"
    )


def download_baostock_5m_requests(
    tasks: Iterable[tuple[str, str, str]],
    workers: int,
) -> Iterable[tuple[str, str, str, pd.DataFrame]]:
    """Yield PIT interval responses while bounding submitted work and process count."""

    if not 1 <= workers <= BAOSTOCK_5M_MAX_WORKERS:
        raise RichDataError(
            f"BaoStock five-minute workers must be between 1 and {BAOSTOCK_5M_MAX_WORKERS}"
        )
    task_iterator = iter(tasks)
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers,
        initializer=initialize_baostock_5m_worker,
    ) as executor:
        pending: dict[
            concurrent.futures.Future[tuple[str, str, str, pd.DataFrame]], None
        ] = {}
        for _ in range(workers * 2):
            try:
                pending[
                    executor.submit(
                        fetch_baostock_5m_request_worker, next(task_iterator)
                    )
                ] = None
            except StopIteration:
                break
        while pending:
            completed, _ = concurrent.futures.wait(
                pending, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in completed:
                del pending[future]
                yield future.result()
                try:
                    task = next(task_iterator)
                except StopIteration:
                    continue
                pending[executor.submit(fetch_baostock_5m_request_worker, task)] = None


def fetch_tushare_minutes(
    code: str, start: dt.date, end: dt.date, frequency: str
) -> pd.DataFrame:
    """Fetch raw minute bars through Tushare's documented ``pro_bar`` wrapper."""

    ts = _import_tushare()
    return ts.pro_bar(
        ts_code=vendor_symbol(code, "tushare"),
        asset="E",
        adj=None,
        freq=frequency,
        # Tushare minute requests require time-of-day parameters and omit an
        # end date supplied without a time component.
        start_date=f"{start.isoformat()} 09:00:00",
        end_date=f"{end.isoformat()} 17:00:00",
    )


def fetch_jqdata_minutes(
    code: str, start: dt.date, end: dt.date, frequency: str
) -> pd.DataFrame:
    """Fetch raw minute bars with JQData, authenticating only in process memory."""

    from jqdatasdk import auth, get_price

    authenticated = auth(os.environ["JQDATA_USERNAME"], os.environ["JQDATA_PASSWORD"])
    if authenticated is False:
        raise RichDataError("JQData rejected the configured credentials")
    return get_price(
        vendor_symbol(code, "jqdata"),
        start_date=f"{start.isoformat()} 09:30:00",
        end_date=f"{end.isoformat()} 15:00:00",
        frequency=frequency,
        fields=["open", "high", "low", "close", "volume", "money"],
        skip_paused=False,
        fq=None,
        panel=False,
    )


def fetch_jqdata_moneyflow_pro(
    codes: list[str], start: dt.date, end: dt.date
) -> pd.DataFrame:
    """Fetch only the eight frozen daily classified-flow amount fields."""

    from jqdatasdk import auth, get_money_flow_pro

    authenticated = auth(os.environ["JQDATA_USERNAME"], os.environ["JQDATA_PASSWORD"])
    if authenticated is False:
        raise RichDataError("JQData rejected the configured credentials")
    result = get_money_flow_pro(
        [vendor_symbol(code, "jqdata") for code in codes],
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        frequency="daily",
        fields=list(JQDATA_MONEYFLOW_RAW_FIELDS),
        data_type="money",
    )
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_moneyflow(trade_date: dt.date) -> pd.DataFrame:
    """Fetch one complete session using only the frozen Tushare field whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.moneyflow(
            trade_date=trade_date.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_MONEYFLOW_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            f"Tushare moneyflow request failed for {trade_date.isoformat()}: {exc}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_northbound_top10(
    trade_date: dt.date, market_type: str
) -> pd.DataFrame:
    """Fetch one market/session using only the frozen Northbound whitelist."""

    if str(market_type) not in TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES:
        raise RichDataError(f"unsupported Northbound market_type: {market_type}")
    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.hsgt_top10(
            trade_date=trade_date.strftime("%Y%m%d"),
            market_type=str(market_type),
            fields=",".join(TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare hsgt_top10 request failed for "
            f"{trade_date.isoformat()} market_type={market_type}: {exc}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_top_inst(trade_date: dt.date) -> pd.DataFrame:
    """Fetch one institution-seat session using only the frozen whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.top_inst(
            trade_date=trade_date.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_TOP_INST_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare top_inst request failed for "
            f"{trade_date.isoformat()}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_earnings_forecast(
    ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
) -> pd.DataFrame:
    """Fetch one stock's forecast history using only the frozen whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.forecast(
            ts_code=ts_code,
            start_date=announcement_start.strftime("%Y%m%d"),
            end_date=announcement_end.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_EARNINGS_FORECAST_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            f"Tushare forecast request failed for {ts_code}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_disclosure_plan(report_period: dt.date) -> pd.DataFrame:
    """Fetch one frozen report period using only the five-field whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.disclosure_date(
            end_date=report_period.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare disclosure_date request failed for "
            f"{report_period.isoformat()}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_audit_opinions(
    ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
) -> pd.DataFrame:
    """Fetch one stock's audit opinions using only the frozen four fields."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.fina_audit(
            ts_code=ts_code,
            start_date=announcement_start.strftime("%Y%m%d"),
            end_date=announcement_end.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_AUDIT_OPINION_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare fina_audit request failed for "
            f"{ts_code}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_gross_margin_indicators(
    ts_code: str,
    report_period_start: dt.date,
    report_period_end: dt.date,
) -> pd.DataFrame:
    """Fetch one stock's frozen financial-indicator history and field whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.fina_indicator(
            ts_code=ts_code,
            start_date=report_period_start.strftime("%Y%m%d"),
            end_date=report_period_end.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_GROSS_MARGIN_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare fina_indicator request failed for "
            f"{ts_code}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_management_continuity_rows(
    ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
) -> pd.DataFrame:
    """Fetch one stock's management rows with the frozen privacy whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.stk_managers(
            ts_code=ts_code,
            start_date=announcement_start.strftime("%Y%m%d"),
            end_date=announcement_end.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_MANAGEMENT_CONTINUITY_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare stk_managers request failed for "
            f"{ts_code}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_stock_st_membership(trade_date: dt.date) -> pd.DataFrame:
    """Fetch one complete ST-membership session with the frozen field whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.stock_st(
            trade_date=trade_date.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_ST_MEMBERSHIP_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare stock_st request failed for "
            f"{trade_date.isoformat()}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_top10_float_holders(
    ts_code: str,
    report_period_start: dt.date,
    report_period_end: dt.date,
) -> pd.DataFrame:
    """Fetch one stock's frozen report-period range with the exact whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.top10_floatholders(
            ts_code=ts_code,
            start_date=report_period_start.strftime("%Y%m%d"),
            end_date=report_period_end.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_TOP10_FLOAT_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare top10_floatholders request failed for "
            f"{ts_code}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_cash_conversion_statement(
    endpoint: str,
    ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
) -> pd.DataFrame:
    """Fetch one frozen income or cashflow partition with its exact whitelist."""

    fields_by_endpoint = {
        "income": TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS,
        "cashflow": TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS,
    }
    if endpoint not in fields_by_endpoint:
        raise RichDataError(f"unsupported Tushare cash-conversion endpoint: {endpoint}")
    ts = _import_tushare()
    pro = ts.pro_api()
    request = getattr(pro, endpoint, None)
    if request is None or not callable(request):
        raise RichDataError(f"Tushare SDK lacks the required {endpoint} endpoint")
    try:
        result = request(
            ts_code=ts_code,
            start_date=announcement_start.strftime("%Y%m%d"),
            end_date=announcement_end.strftime("%Y%m%d"),
            fields=",".join(fields_by_endpoint[endpoint]),
        )
    except Exception as exc:
        raise RichDataError(
            f"Tushare {endpoint} request failed for {ts_code}: "
            f"{safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_daily_pb(trade_date: dt.date) -> pd.DataFrame:
    """Fetch one daily_basic session using only the frozen PB whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.daily_basic(
            trade_date=trade_date.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_DAILY_PB_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            f"Tushare daily_basic PB request failed for {trade_date.isoformat()}: {exc}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_free_float_scarcity(trade_date: dt.date) -> pd.DataFrame:
    """Fetch one daily_basic session using only the frozen share-count whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.daily_basic(
            trade_date=trade_date.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare daily_basic free-float-scarcity request failed for "
            f"{trade_date.isoformat()}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_sw_classification() -> pd.DataFrame:
    """Fetch only the frozen SW2021 level-one classification fields."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.index_classify(
            level="L1",
            src="SW2021",
            fields=",".join(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(f"Tushare index_classify request failed: {exc}") from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_sw_members(l1_code: str, is_new: str) -> pd.DataFrame:
    """Fetch one frozen SW2021 L1/current-state membership partition."""

    if is_new not in {"Y", "N"}:
        raise RichDataError(f"unsupported Tushare SW membership is_new: {is_new}")
    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.index_member_all(
            l1_code=l1_code,
            is_new=is_new,
            fields=",".join(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare index_member_all request failed for "
            f"l1_code={l1_code} is_new={is_new}: {exc}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_rqdata_minutes(
    code: str, start: dt.date, end: dt.date, frequency: str
) -> pd.DataFrame:
    """Fetch raw minute bars from RQData's licensed API."""

    import rqdatac

    rqdatac.init(os.environ["RQDATA_USERNAME"], os.environ["RQDATA_PASSWORD"])
    return rqdatac.get_price(
        vendor_symbol(code, "rqdata"),
        start_date=start,
        end_date=end,
        frequency=frequency,
        fields=["open", "high", "low", "close", "volume", "total_turnover"],
        adjust_type="none",
        skip_suspended=False,
        expect_df=True,
    )


MINUTE_FETCHERS: dict[str, Callable[[str, dt.date, dt.date, str], pd.DataFrame]] = {
    "baostock": fetch_baostock_minutes,
    "tushare": fetch_tushare_minutes,
    "jqdata": fetch_jqdata_minutes,
    "rqdata": fetch_rqdata_minutes,
}


def fetch_tushare_event(dataset: str, trade_date: dt.date) -> pd.DataFrame:
    """Fetch a single complete-session Tushare event table."""

    if dataset not in EVENT_DATASETS:
        raise RichDataError(f"unsupported Tushare event dataset: {dataset}")
    ts = _import_tushare()
    pro = ts.pro_api()
    method = {
        "moneyflow": pro.moneyflow,
        "limit-price": pro.stk_limit,
        "stock-st": pro.stock_st,
        "limit-list": pro.limit_list_d,
        "top-list": pro.top_list,
    }[dataset]
    try:
        result = method(trade_date=trade_date.strftime("%Y%m%d"))
    except Exception as exc:
        raise RichDataError(f"Tushare {dataset} request failed: {exc}") from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def tushare_event_quality(
    frame: pd.DataFrame,
    dataset: str,
    trade_date: dt.date,
) -> dict[str, Any]:
    """Audit one raw Tushare event response without changing source rows."""

    keys = TUSHARE_EVENT_KEY_FIELDS[dataset]
    if frame.empty:
        return {
            "status": "empty_source_response",
            "source_rows": 0,
            "missing_key_rows": 0,
            "outside_requested_date_rows": 0,
            "exact_duplicate_rows": 0,
            "duplicate_event_key_rows": 0,
            "raw_rows_preserved_without_deduplication": True,
        }
    missing_columns = [column for column in keys if column not in frame.columns]
    if missing_columns:
        raise RichDataError(
            f"Tushare {dataset} response lacks required columns: "
            + ", ".join(missing_columns)
        )
    missing_key_rows = int(frame[list(keys)].isna().any(axis=1).sum())
    if missing_key_rows:
        raise RichDataError(
            f"Tushare {dataset} response contains {missing_key_rows} rows with missing keys"
        )
    requested = trade_date.strftime("%Y%m%d")
    observed_dates = (
        frame["trade_date"].astype("string").str.replace("-", "", regex=False)
    )
    outside_requested_date_rows = int(observed_dates.ne(requested).sum())
    if outside_requested_date_rows:
        raise RichDataError(
            f"Tushare {dataset} response contains {outside_requested_date_rows} rows "
            "outside the requested date"
        )
    exact_duplicate_rows = int(frame.duplicated().sum())
    duplicate_event_key_rows = int(frame.duplicated(list(keys)).sum())
    return {
        "status": (
            "raw_duplicates_present_pending_canonicalization"
            if exact_duplicate_rows or duplicate_event_key_rows
            else "raw_keys_passed"
        ),
        "source_rows": int(len(frame)),
        "missing_key_rows": missing_key_rows,
        "outside_requested_date_rows": outside_requested_date_rows,
        "exact_duplicate_rows": exact_duplicate_rows,
        "duplicate_event_key_rows": duplicate_event_key_rows,
        "raw_rows_preserved_without_deduplication": True,
    }


def canonicalize_tushare_moneyflow(
    frame: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Normalize Tushare classified amounts and derive the frozen local ratio."""

    empty_stats = {
        "input_rows": 0,
        "missing_rows_excluded": 0,
        "zero_denominator_rows_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_MONEYFLOW_COLUMNS), empty_stats
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_MONEYFLOW_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare moneyflow response lacks requested fields: "
            + ", ".join(missing_columns)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        code = str(value).split(".", 1)[0].strip()
        if len(code) != 6 or not code.isdigit():
            return None
        try:
            return qlib_symbol(code)
        except RichDataError:
            return None

    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "instrument": raw["ts_code"].map(instrument),
            **{
                field: pd.to_numeric(raw[field], errors="coerce")
                for field in TUSHARE_MONEYFLOW_AMOUNT_FIELDS
            },
        }
    )
    required = ["trade_date", "instrument", *TUSHARE_MONEYFLOW_AMOUNT_FIELDS]
    complete = normalized[required].notna().all(axis=1)
    missing_rows = int((~complete).sum())
    valid = normalized.loc[complete].copy()
    amount_columns = list(TUSHARE_MONEYFLOW_AMOUNT_FIELDS)
    if valid[amount_columns].lt(0.0).any().any():
        raise RichDataError(
            "Tushare moneyflow response contains a negative raw flow amount"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not valid["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "Tushare moneyflow response contains a date outside the request"
        )
    if valid.duplicated(["instrument", "trade_date"]).any():
        raise RichDataError(
            "Tushare moneyflow response contains duplicate instrument/date keys"
        )
    valid[amount_columns] = valid[amount_columns].astype("float64")
    denominator = valid[amount_columns].sum(axis=1)
    positive = denominator.gt(0.0)
    zero_denominator_rows = int((~positive).sum())
    valid = valid.loc[positive].copy()
    denominator = denominator.loc[positive]
    valid["tushare_large_order_net_inflow_share"] = (
        valid["buy_elg_amount"]
        + valid["buy_lg_amount"]
        - valid["sell_elg_amount"]
        - valid["sell_lg_amount"]
    ) / denominator
    valid["provider"] = "tushare"
    result = (
        valid.loc[:, list(TUSHARE_MONEYFLOW_COLUMNS)]
        .sort_values(["trade_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    if not result["tushare_large_order_net_inflow_share"].between(-1.0, 1.0).all():
        raise RichDataError("derived Tushare large-order ratio falls outside [-1, 1]")
    return result, {
        "input_rows": int(len(raw)),
        "missing_rows_excluded": missing_rows,
        "zero_denominator_rows_excluded": zero_denominator_rows,
        "rows_written": int(len(result)),
    }


def canonicalize_tushare_northbound_top10(
    frame: pd.DataFrame,
    start: dt.date,
    end: dt.date,
    expected_market_type: str | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Normalize one frozen Northbound top-ten response and derive its ratio."""

    empty_stats = {
        "input_rows": 0,
        "missing_rows_excluded": 0,
        "zero_denominator_rows_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_NORTHBOUND_TOP10_COLUMNS), empty_stats
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare hsgt_top10 response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(
        set(raw.columns) - set(TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS)
    )
    if unexpected_columns:
        raise RichDataError(
            "Tushare hsgt_top10 response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected_columns)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        code = str(value).split(".", 1)[0].strip()
        if len(code) != 6 or not code.isdigit():
            return None
        try:
            return qlib_symbol(code)
        except RichDataError:
            return None

    numeric_market = pd.to_numeric(raw["market_type"], errors="coerce")
    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "instrument": raw["ts_code"].map(instrument),
            "rank": pd.to_numeric(raw["rank"], errors="coerce"),
            "market_type": numeric_market.map(
                lambda value: str(int(value)) if pd.notna(value) else pd.NA
            ).astype("string"),
            "amount": pd.to_numeric(raw["amount"], errors="coerce"),
            "buy": pd.to_numeric(raw["buy"], errors="coerce"),
            "sell": pd.to_numeric(raw["sell"], errors="coerce"),
        }
    )
    required = [
        "trade_date",
        "instrument",
        "rank",
        "market_type",
        "amount",
        "buy",
        "sell",
    ]
    complete = normalized[required].notna().all(axis=1)
    missing_rows = int((~complete).sum())
    valid = normalized.loc[complete].copy()
    if valid[["amount", "buy", "sell"]].lt(0.0).any().any():
        raise RichDataError(
            "Tushare hsgt_top10 response contains a negative raw amount"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not valid["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "Tushare hsgt_top10 response contains a date outside the request"
        )
    if not valid["market_type"].isin(TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES).all():
        raise RichDataError(
            "Tushare hsgt_top10 response contains an unsupported market_type"
        )
    if (
        expected_market_type is not None
        and not valid["market_type"].eq(str(expected_market_type)).all()
    ):
        raise RichDataError(
            "Tushare hsgt_top10 response market_type differs from the requested market"
        )
    integer_rank = valid["rank"].eq(np.floor(valid["rank"]))
    if not integer_rank.all() or not valid["rank"].between(1, 10).all():
        raise RichDataError(
            "Tushare hsgt_top10 ranks must be integers from 1 through 10"
        )
    valid["rank"] = valid["rank"].astype("int64")
    if valid.duplicated(["trade_date", "market_type", "rank"]).any():
        raise RichDataError(
            "Tushare hsgt_top10 response contains duplicate market ranks"
        )
    if valid.duplicated(["instrument", "trade_date"]).any():
        raise RichDataError(
            "Tushare hsgt_top10 response contains duplicate instrument/date keys"
        )
    market_counts = valid.groupby(["trade_date", "market_type"], observed=True).size()
    if market_counts.gt(10).any():
        raise RichDataError(
            "Tushare hsgt_top10 response contains more than ten rows per market"
        )
    valid[["amount", "buy", "sell"]] = valid[["amount", "buy", "sell"]].astype(
        "float64"
    )
    disclosed_total = valid["buy"] + valid["sell"]
    tolerance = np.maximum(1.0, np.maximum(valid["amount"], disclosed_total) * 0.000001)
    if (valid["amount"].sub(disclosed_total).abs() > tolerance).any():
        raise RichDataError(
            "Tushare hsgt_top10 amount does not reconcile to buy plus sell"
        )
    positive = disclosed_total.gt(0.0)
    zero_denominator_rows = int((~positive).sum())
    valid = valid.loc[positive].copy()
    disclosed_total = disclosed_total.loc[positive]
    valid["tushare_northbound_top10_net_buy_share"] = (
        valid["buy"] - valid["sell"]
    ) / disclosed_total
    valid["provider"] = "tushare"
    result = (
        valid.loc[:, list(TUSHARE_NORTHBOUND_TOP10_COLUMNS)]
        .sort_values(["trade_date", "market_type", "rank"], kind="stable")
        .reset_index(drop=True)
    )
    if not result["tushare_northbound_top10_net_buy_share"].between(-1.0, 1.0).all():
        raise RichDataError("derived Tushare Northbound ratio falls outside [-1, 1]")
    return result, {
        "input_rows": int(len(raw)),
        "missing_rows_excluded": missing_rows,
        "zero_denominator_rows_excluded": zero_denominator_rows,
        "rows_written": int(len(result)),
    }


def canonicalize_tushare_top_inst(
    frame: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Reconcile unique institution-seat rows and derive the frozen ratio."""

    empty_stats = {
        "input_rows": 0,
        "institution_seat_rows_reconciled": 0,
        "zero_denominator_stock_days_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_TOP_INST_COLUMNS), empty_stats
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_TOP_INST_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare top_inst response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(set(raw.columns) - set(TUSHARE_TOP_INST_RAW_FIELDS))
    if unexpected_columns:
        raise RichDataError(
            "Tushare top_inst response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected_columns)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        source_code = str(value).strip()
        parts = source_code.split(".", 1)
        if len(parts) != 2:
            return None
        code, suffix = parts[0].strip(), parts[1].strip().upper()
        if len(code) != 6 or not code.isdigit() or suffix not in {"SH", "SZ"}:
            return None
        try:
            symbol = qlib_symbol(code)
        except RichDataError:
            return None
        return symbol if symbol.startswith(suffix) else None

    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "instrument": raw["ts_code"].map(instrument),
            "exalter": raw["exalter"].astype("string").str.strip(),
            "buy": pd.to_numeric(raw["buy"], errors="coerce"),
            "sell": pd.to_numeric(raw["sell"], errors="coerce"),
            "net_buy": pd.to_numeric(raw["net_buy"], errors="coerce"),
        }
    )
    required = ["trade_date", "instrument", "exalter", "buy", "sell", "net_buy"]
    missing = normalized[required].isna().any(axis=1) | normalized["exalter"].eq("")
    finite_amounts = np.isfinite(normalized[["buy", "sell", "net_buy"]]).all(axis=1)
    if missing.any() or (~finite_amounts).any():
        invalid_rows = int((missing | ~finite_amounts).sum())
        raise RichDataError(
            f"Tushare top_inst response contains {invalid_rows} incomplete or non-finite rows"
        )
    if normalized[["buy", "sell"]].lt(0.0).any().any():
        raise RichDataError(
            "Tushare top_inst response contains a negative buy or sell amount"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not normalized["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "Tushare top_inst response contains a date outside the request"
        )
    seat_key = ["trade_date", "instrument", "exalter"]
    if normalized.duplicated(seat_key).any():
        raise RichDataError(
            "Tushare top_inst response contains duplicate institution-seat keys"
        )

    tolerance = np.maximum(
        0.01,
        0.000001
        * np.maximum(
            normalized["net_buy"].abs(),
            normalized["buy"] + normalized["sell"],
        ),
    )
    if (
        normalized["net_buy"].sub(normalized["buy"] - normalized["sell"]).abs()
        > tolerance
    ).any():
        raise RichDataError(
            "Tushare top_inst net_buy does not reconcile to buy minus sell"
        )

    aggregated = (
        normalized.groupby(["trade_date", "instrument"], as_index=False, observed=True)
        .agg(
            institution_seat_count=("exalter", "nunique"),
            buy=("buy", "sum"),
            sell=("sell", "sum"),
        )
        .sort_values(["trade_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    denominator = aggregated["buy"] + aggregated["sell"]
    positive = denominator.gt(0.0)
    zero_denominator_stock_days = int((~positive).sum())
    aggregated = aggregated.loc[positive].copy()
    denominator = denominator.loc[positive]
    aggregated["tushare_top_inst_net_buy_share"] = (
        aggregated["buy"] - aggregated["sell"]
    ) / denominator
    aggregated["provider"] = "tushare"
    result = aggregated.loc[:, list(TUSHARE_TOP_INST_COLUMNS)].reset_index(drop=True)
    factor = result["tushare_top_inst_net_buy_share"]
    if not np.isfinite(factor).all() or not factor.between(-1.0, 1.0).all():
        raise RichDataError(
            "derived Tushare institution-seat ratio falls outside [-1, 1]"
        )
    return result, {
        "input_rows": int(len(raw)),
        "institution_seat_rows_reconciled": int(len(normalized)),
        "zero_denominator_stock_days_excluded": zero_denominator_stock_days,
        "rows_written": int(len(result)),
    }


def canonicalize_tushare_earnings_forecast(
    frame: pd.DataFrame,
    expected_ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the frozen forecast type, bound, duplicate, and formula policy."""

    empty_quality: dict[str, Any] = {
        "input_rows": 0,
        "exact_semantic_duplicate_rows_collapsed": 0,
        "missing_first_announcement_dates": 0,
        "noncomparable_type_rows_excluded": 0,
        "noncomparable_type_counts": {},
        "missing_or_nonfinite_bound_rows_excluded": 0,
        "reversed_bound_rows_excluded": 0,
        "rows_written": 0,
        "forecast_type_counts": {},
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_EARNINGS_FORECAST_COLUMNS), empty_quality
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_EARNINGS_FORECAST_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare forecast response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(
        set(raw.columns) - set(TUSHARE_EARNINGS_FORECAST_RAW_FIELDS)
    )
    if unexpected_columns:
        raise RichDataError(
            "Tushare forecast response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected_columns)
        )

    expected_code = str(expected_ts_code).strip().upper()
    parts = expected_code.split(".", 1)
    if (
        len(parts) != 2
        or len(parts[0]) != 6
        or not parts[0].isdigit()
        or parts[1] not in {"SH", "SZ"}
    ):
        raise RichDataError(f"invalid frozen Tushare forecast code: {expected_ts_code}")
    expected_instrument = qlib_symbol(parts[0])
    if not expected_instrument.startswith(parts[1]):
        raise RichDataError(
            f"forecast stock code and exchange suffix disagree: {expected_ts_code}"
        )

    source_code = (
        raw["ts_code"].astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    announcement_date = pd.to_datetime(
        raw["ann_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    report_period = pd.to_datetime(
        raw["end_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    forecast_type = raw["type"].astype("string").str.strip().replace("", pd.NA)
    first_raw = raw["first_ann_date"].astype("string").str.strip().replace("", pd.NA)
    first_announcement_date = pd.to_datetime(
        first_raw, format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    invalid_key = (
        source_code.isna()
        | announcement_date.isna()
        | report_period.isna()
        | forecast_type.isna()
    )
    invalid_optional_first = first_raw.notna() & first_announcement_date.isna()
    if invalid_key.any() or invalid_optional_first.any():
        raise RichDataError(
            "Tushare forecast response contains "
            f"{int((invalid_key | invalid_optional_first).sum())} rows with invalid keys"
        )
    if not source_code.eq(expected_code).all():
        raise RichDataError(
            "Tushare forecast response contains a stock outside its request"
        )
    if first_announcement_date.gt(announcement_date).fillna(False).any():
        raise RichDataError(
            "Tushare forecast first announcement date is after ann_date"
        )
    if not announcement_date.between(
        pd.Timestamp(announcement_start), pd.Timestamp(announcement_end)
    ).all():
        raise RichDataError(
            "Tushare forecast response contains an announcement outside the request"
        )
    if (
        not report_period.dt.strftime("%m-%d")
        .isin({"03-31", "06-30", "09-30", "12-31"})
        .all()
    ):
        raise RichDataError(
            "Tushare forecast response contains a non-standard quarter end"
        )

    known_types = (
        TUSHARE_EARNINGS_FORECAST_COMPARABLE_TYPES
        | TUSHARE_EARNINGS_FORECAST_NONCOMPARABLE_TYPES
    )
    unknown_types = sorted(set(forecast_type.astype(str)) - known_types)
    if unknown_types:
        raise RichDataError(
            f"Tushare forecast response contains unknown types: {unknown_types}"
        )
    lower = pd.to_numeric(raw["p_change_min"], errors="coerce")
    upper = pd.to_numeric(raw["p_change_max"], errors="coerce")
    normalized = pd.DataFrame(
        {
            "announcement_date": announcement_date,
            "first_announcement_date": first_announcement_date,
            "report_period": report_period,
            "instrument": expected_instrument,
            "forecast_type": forecast_type.astype(str),
            "p_change_min": lower,
            "p_change_max": upper,
        }
    )
    type_counts = {
        str(key): int(value)
        for key, value in normalized["forecast_type"]
        .value_counts()
        .sort_index()
        .items()
    }
    before_dedup = len(normalized)
    normalized = normalized.drop_duplicates(ignore_index=True)
    duplicate_rows = int(before_dedup - len(normalized))
    event_key = ["instrument", "announcement_date", "report_period"]
    if normalized.duplicated(event_key, keep=False).any():
        raise RichDataError(
            "Tushare forecast response contains conflicting duplicate event keys"
        )

    comparable = normalized["forecast_type"].isin(
        TUSHARE_EARNINGS_FORECAST_COMPARABLE_TYPES
    )
    noncomparable_counts = {
        str(key): int(value)
        for key, value in normalized.loc[~comparable, "forecast_type"]
        .value_counts()
        .sort_index()
        .items()
    }
    finite_bounds = pd.Series(
        np.isfinite(normalized["p_change_min"])
        & np.isfinite(normalized["p_change_max"]),
        index=normalized.index,
    )
    reversed_bounds = finite_bounds & normalized["p_change_min"].gt(
        normalized["p_change_max"]
    )
    accepted = normalized.loc[comparable & finite_bounds & ~reversed_bounds].copy()
    accepted["tushare_earnings_forecast_growth_midpoint"] = (
        accepted["p_change_min"] + accepted["p_change_max"]
    ) / 2.0
    accepted["provider"] = "tushare"
    result = (
        accepted.loc[:, list(TUSHARE_EARNINGS_FORECAST_COLUMNS)]
        .sort_values(["announcement_date", "report_period"], kind="stable")
        .reset_index(drop=True)
    )
    if not np.isfinite(result["tushare_earnings_forecast_growth_midpoint"]).all():
        raise RichDataError("derived Tushare forecast midpoint is non-finite")
    return result, {
        "input_rows": int(len(raw)),
        "exact_semantic_duplicate_rows_collapsed": duplicate_rows,
        "missing_first_announcement_dates": int(first_raw.isna().sum()),
        "noncomparable_type_rows_excluded": int((~comparable).sum()),
        "noncomparable_type_counts": noncomparable_counts,
        "missing_or_nonfinite_bound_rows_excluded": int(
            (comparable & ~finite_bounds).sum()
        ),
        "reversed_bound_rows_excluded": int((comparable & reversed_bounds).sum()),
        "rows_written": int(len(result)),
        "forecast_type_counts": type_counts,
    }


def canonicalize_tushare_disclosure_plan(
    frame: pd.DataFrame,
    expected_report_period: dt.date,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the frozen disclosure-plan date, code, version, and formula policy."""

    empty_quality: dict[str, Any] = {
        "input_rows": 0,
        "outside_target_bj_rows_excluded": 0,
        "exact_semantic_duplicate_rows_collapsed": 0,
        "modify_date_context_rows": 0,
        "rows_written": 0,
        "distinct_lead_days": 0,
        "minimum_lead_days": None,
        "maximum_lead_days": None,
    }
    if frame is None or frame.empty:
        return (
            pd.DataFrame(columns=TUSHARE_DISCLOSURE_PROMPTNESS_COLUMNS),
            empty_quality,
        )
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare disclosure_date response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(
        set(raw.columns) - set(TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS)
    )
    if unexpected_columns:
        raise RichDataError(
            "Tushare disclosure_date response contains fields outside the frozen "
            "whitelist: " + ", ".join(unexpected_columns)
        )
    if expected_report_period.strftime("%m-%d") not in {
        "03-31",
        "06-30",
        "09-30",
        "12-31",
    }:
        raise RichDataError(
            "frozen Tushare disclosure_date request is not a standard quarter end"
        )

    source_code = (
        raw["ts_code"].astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    code_parts = source_code.str.extract(r"^(\d{6})\.(SH|SZ|BJ)$")
    announcement_date = pd.to_datetime(
        raw["ann_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    report_period = pd.to_datetime(
        raw["end_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    planned_date = pd.to_datetime(
        raw["pre_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    modify_context = raw["modify_date"].astype("string").str.strip().replace("", pd.NA)
    invalid_key = (
        source_code.isna()
        | code_parts[0].isna()
        | code_parts[1].isna()
        | announcement_date.isna()
        | report_period.isna()
        | planned_date.isna()
    )
    if invalid_key.any():
        raise RichDataError(
            "Tushare disclosure_date response contains "
            f"{int(invalid_key.sum())} rows with invalid keys or dates"
        )
    expected_ts = pd.Timestamp(expected_report_period)
    if not report_period.eq(expected_ts).all():
        raise RichDataError(
            "Tushare disclosure_date response contains a report period outside its request"
        )
    lead_days = (planned_date - announcement_date).dt.days
    if lead_days.lt(0).any():
        raise RichDataError(
            "Tushare disclosure_date response contains an announcement after its planned date"
        )

    outside_bj = code_parts[1].eq("BJ")
    normalized = (
        pd.DataFrame(
            {
                "source_code": source_code,
                "announcement_date": announcement_date,
                "report_period": report_period,
                "planned_disclosure_date": planned_date,
                "modify_date_context": modify_context,
                "lead_days": lead_days,
                "code": code_parts[0],
                "exchange": code_parts[1],
            }
        )
        .loc[~outside_bj]
        .copy()
    )
    before_dedup = len(normalized)
    normalized = normalized.drop_duplicates(ignore_index=True)
    duplicate_rows = int(before_dedup - len(normalized))
    event_key = ["source_code", "report_period"]
    if normalized.duplicated(event_key, keep=False).any():
        raise RichDataError(
            "Tushare disclosure_date response contains conflicting stock-period rows"
        )

    instruments: list[str] = []
    for code, exchange in zip(
        normalized["code"].astype(str), normalized["exchange"].astype(str)
    ):
        instrument = qlib_symbol(code)
        if not instrument.startswith(exchange):
            raise RichDataError(
                "Tushare disclosure_date stock code and exchange suffix disagree: "
                f"{code}.{exchange}"
            )
        instruments.append(instrument)
    result = pd.DataFrame(
        {
            "announcement_date": normalized["announcement_date"],
            "report_period": normalized["report_period"],
            "planned_disclosure_date": normalized["planned_disclosure_date"],
            "instrument": instruments,
            "tushare_disclosure_plan_lead_days": normalized["lead_days"].astype(
                "int64"
            ),
            "provider": "tushare",
        }
    )
    result = (
        result.loc[:, list(TUSHARE_DISCLOSURE_PROMPTNESS_COLUMNS)]
        .sort_values(["announcement_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    factor = result["tushare_disclosure_plan_lead_days"]
    if factor.lt(0).any() or not np.isfinite(factor).all():
        raise RichDataError(
            "derived Tushare disclosure-plan lead days are negative or non-finite"
        )
    return result, {
        "input_rows": int(len(raw)),
        "outside_target_bj_rows_excluded": int(outside_bj.sum()),
        "exact_semantic_duplicate_rows_collapsed": duplicate_rows,
        "modify_date_context_rows": int(modify_context.notna().sum()),
        "rows_written": int(len(result)),
        "distinct_lead_days": int(factor.nunique()),
        "minimum_lead_days": int(factor.min()) if len(factor) else None,
        "maximum_lead_days": int(factor.max()) if len(factor) else None,
    }


def canonicalize_tushare_audit_opinions(
    frame: pd.DataFrame,
    expected_ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the frozen audit-opinion identity, date, text, and binary policy."""

    empty_quality: dict[str, Any] = {
        "input_rows": 0,
        "exact_four_field_duplicate_rows_collapsed": 0,
        "hashed_opinion_category_counts": {},
        "annual_report_period_counts": {},
        "source_report_rows_retained": 0,
        "stock_announcement_events_written": 0,
        "distinct_factor_values": 0,
        "clean_report_rows": 0,
        "nonclean_report_rows": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_AUDIT_OPINION_COLUMNS), empty_quality
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_AUDIT_OPINION_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare fina_audit response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(
        set(raw.columns) - set(TUSHARE_AUDIT_OPINION_RAW_FIELDS)
    )
    if unexpected_columns:
        raise RichDataError(
            "Tushare fina_audit response contains fields outside the frozen "
            "whitelist: " + ", ".join(unexpected_columns)
        )
    expected_code = str(expected_ts_code).strip().upper()
    expected_parts = pd.Series([expected_code], dtype="string").str.extract(
        r"^(\d{6})\.(SH|SZ)$"
    )
    if expected_parts.isna().any(axis=None):
        raise RichDataError(f"invalid frozen Tushare fina_audit stock: {expected_code}")
    if announcement_start > announcement_end:
        raise RichDataError("Tushare fina_audit announcement range is reversed")

    source_code = (
        raw["ts_code"].astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    code_parts = source_code.str.extract(r"^(\d{6})\.(SH|SZ|BJ)$")
    announcement_date = pd.to_datetime(
        raw["ann_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    report_period = pd.to_datetime(
        raw["end_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    audit_text = (
        raw["audit_result"]
        .astype("string")
        .map(
            lambda value: (
                unicodedata.normalize("NFKC", str(value)).strip()
                if pd.notna(value)
                else pd.NA
            )
        )
    )
    audit_text = audit_text.astype("string").replace("", pd.NA)
    invalid_key = (
        source_code.isna()
        | code_parts[0].isna()
        | code_parts[1].isna()
        | announcement_date.isna()
        | report_period.isna()
        | audit_text.isna()
    )
    if invalid_key.any():
        raise RichDataError(
            "Tushare fina_audit response contains "
            f"{int(invalid_key.sum())} rows with invalid keys, dates, or opinions"
        )
    if not source_code.eq(expected_code).all():
        raise RichDataError(
            "Tushare fina_audit response contains a stock outside its frozen request"
        )
    if code_parts[1].eq("BJ").any():
        raise RichDataError(
            "Tushare fina_audit response contains BSE rows outside the frozen source universe"
        )
    start_ts = pd.Timestamp(announcement_start)
    end_ts = pd.Timestamp(announcement_end)
    if announcement_date.lt(start_ts).any() or announcement_date.gt(end_ts).any():
        raise RichDataError(
            "Tushare fina_audit response contains an announcement outside its request"
        )
    standard_quarter_end = report_period.dt.strftime("%m%d").isin(
        {"0331", "0630", "0930", "1231"}
    )
    if not standard_quarter_end.all():
        raise RichDataError(
            "Tushare fina_audit response contains a non-standard report period"
        )
    if report_period.gt(announcement_date).any():
        raise RichDataError(
            "Tushare fina_audit response contains a report period after its announcement"
        )

    normalized = pd.DataFrame(
        {
            "source_code": source_code,
            "announcement_date": announcement_date,
            "report_period": report_period,
            "audit_text": audit_text,
            "code": code_parts[0],
            "exchange": code_parts[1],
        }
    )
    before_dedup = len(normalized)
    normalized = normalized.drop_duplicates(ignore_index=True)
    duplicate_rows = int(before_dedup - len(normalized))
    report_key = ["source_code", "announcement_date", "report_period"]
    if normalized.duplicated(report_key, keep=False).any():
        raise RichDataError(
            "Tushare fina_audit response contains conflicting stock-announcement-report rows"
        )

    code = str(expected_parts.iloc[0, 0])
    exchange = str(expected_parts.iloc[0, 1])
    instrument = qlib_symbol(code)
    if not instrument.startswith(exchange):
        raise RichDataError(
            "Tushare fina_audit stock code and exchange suffix disagree: "
            f"{expected_code}"
        )
    normalized["factor"] = (
        normalized["audit_text"].eq(TUSHARE_AUDIT_OPINION_CLEAN_TEXT).astype("int8")
    )
    hashed_categories = normalized["audit_text"].map(
        lambda value: hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    )
    hashed_counts = {
        str(key): int(value)
        for key, value in hashed_categories.value_counts().sort_index().items()
    }
    annual_report_period_counts = {
        pd.Timestamp(key).date().isoformat(): int(value)
        for key, value in normalized.loc[
            normalized["report_period"].dt.strftime("%m%d").eq("1231"),
            "report_period",
        ]
        .value_counts()
        .sort_index()
        .items()
    }
    event_rows = (
        normalized.groupby("announcement_date", as_index=False, sort=True)
        .agg(
            tushare_is_standard_unqualified_audit_opinion=("factor", "min"),
            audit_report_count=("report_period", "size"),
        )
        .assign(instrument=instrument, provider="tushare")
    )
    result = (
        event_rows.loc[:, list(TUSHARE_AUDIT_OPINION_COLUMNS)]
        .sort_values(["announcement_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    factor = result["tushare_is_standard_unqualified_audit_opinion"]
    if not factor.isin({0, 1}).all():
        raise RichDataError("derived Tushare audit-opinion factor is not binary")
    return result, {
        "input_rows": int(len(raw)),
        "exact_four_field_duplicate_rows_collapsed": duplicate_rows,
        "hashed_opinion_category_counts": hashed_counts,
        "annual_report_period_counts": annual_report_period_counts,
        "source_report_rows_retained": int(len(normalized)),
        "stock_announcement_events_written": int(len(result)),
        "distinct_factor_values": int(factor.nunique()),
        "clean_report_rows": int(normalized["factor"].sum()),
        "nonclean_report_rows": int(normalized["factor"].eq(0).sum()),
    }


def canonicalize_tushare_gross_margin_indicators(
    frame: pd.DataFrame,
    expected_ts_code: str,
    report_period_start: dt.date,
    report_period_end: dt.date,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the frozen initial-only version and same-quarter YoY policy."""

    empty_quality: dict[str, Any] = {
        "input_rows": 0,
        "exact_five_field_duplicate_rows_collapsed": 0,
        "initial_rows_observed": 0,
        "revised_rows_observed": 0,
        "missing_margin_rows_excluded": 0,
        "ambiguous_initial_periods_excluded": 0,
        "initial_quarter_rows_retained": 0,
        "current_periods_without_prior_year_initial_excluded": 0,
        "prior_announcement_not_earlier_excluded": 0,
        "derived_yoy_events_written": 0,
        "distinct_derived_values": 0,
        "minimum_derived_value": None,
        "maximum_derived_value": None,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_GROSS_MARGIN_COLUMNS), empty_quality
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_GROSS_MARGIN_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare fina_indicator response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(set(raw.columns) - set(TUSHARE_GROSS_MARGIN_RAW_FIELDS))
    if unexpected_columns:
        raise RichDataError(
            "Tushare fina_indicator response contains fields outside the frozen "
            "whitelist: " + ", ".join(unexpected_columns)
        )
    expected_code = str(expected_ts_code).strip().upper()
    expected_parts = pd.Series([expected_code], dtype="string").str.extract(
        r"^(\d{6})\.(SH|SZ)$"
    )
    if expected_parts.isna().any(axis=None):
        raise RichDataError(
            f"invalid frozen Tushare fina_indicator stock: {expected_code}"
        )
    if report_period_start > report_period_end:
        raise RichDataError("Tushare fina_indicator report-period range is reversed")

    source_code = (
        raw["ts_code"].astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    code_parts = source_code.str.extract(r"^(\d{6})\.(SH|SZ|BJ)$")
    announcement_date = pd.to_datetime(
        raw["ann_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    report_period = pd.to_datetime(
        raw["end_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    update_flag = raw["update_flag"].astype("string").str.strip().replace("", pd.NA)
    margin = pd.to_numeric(raw["q_gsprofit_margin"], errors="coerce")
    invalid_key = (
        source_code.isna()
        | code_parts[0].isna()
        | code_parts[1].isna()
        | announcement_date.isna()
        | report_period.isna()
        | update_flag.isna()
    )
    if invalid_key.any():
        raise RichDataError(
            "Tushare fina_indicator response contains "
            f"{int(invalid_key.sum())} rows with invalid keys, dates, or update flags"
        )
    if not source_code.eq(expected_code).all():
        raise RichDataError(
            "Tushare fina_indicator response contains a stock outside its frozen request"
        )
    if code_parts[1].eq("BJ").any():
        raise RichDataError(
            "Tushare fina_indicator response contains BSE rows outside the frozen source universe"
        )
    if not update_flag.isin({"0", "1"}).all():
        unknown = sorted(
            str(value)
            for value in update_flag.loc[~update_flag.isin({"0", "1"})].unique()
        )
        raise RichDataError(
            "Tushare fina_indicator response contains unknown update_flag values: "
            + ", ".join(unknown)
        )
    start_ts = pd.Timestamp(report_period_start)
    end_ts = pd.Timestamp(report_period_end)
    if report_period.lt(start_ts).any() or report_period.gt(end_ts).any():
        raise RichDataError(
            "Tushare fina_indicator response contains a report period outside its request"
        )
    standard_quarter_end = report_period.dt.strftime("%m%d").isin(
        {"0331", "0630", "0930", "1231"}
    )
    if not standard_quarter_end.all():
        raise RichDataError(
            "Tushare fina_indicator response contains a non-standard report period"
        )
    if report_period.gt(announcement_date).any():
        raise RichDataError(
            "Tushare fina_indicator response contains a report period after its announcement"
        )

    normalized = pd.DataFrame(
        {
            "source_code": source_code,
            "announcement_date": announcement_date,
            "report_period": report_period,
            "q_gsprofit_margin": margin,
            "update_flag": update_flag,
        }
    )
    before_dedup = len(normalized)
    normalized = normalized.drop_duplicates(ignore_index=True)
    duplicate_rows = int(before_dedup - len(normalized))
    missing_margin = ~np.isfinite(
        normalized["q_gsprofit_margin"].to_numpy(dtype=float, copy=False)
    )
    initial_rows = normalized["update_flag"].eq("0")
    revised_rows = normalized["update_flag"].eq("1")
    complete_initial = normalized.loc[initial_rows & ~missing_margin].copy()
    initial_period_sizes = complete_initial.groupby("report_period", sort=True).size()
    ambiguous_periods = initial_period_sizes.loc[initial_period_sizes.gt(1)].index
    if len(ambiguous_periods):
        complete_initial = complete_initial.loc[
            ~complete_initial["report_period"].isin(ambiguous_periods)
        ].copy()
    complete_initial = complete_initial.sort_values(
        ["report_period", "announcement_date"], kind="stable"
    ).reset_index(drop=True)
    if complete_initial.duplicated("report_period").any():
        raise RichDataError(
            "Tushare fina_indicator initial-version collapse left duplicate report periods"
        )

    current = complete_initial.assign(
        prior_report_period=lambda values: (
            values["report_period"] - pd.DateOffset(years=1)
        )
    )
    prior = complete_initial.loc[
        :, ["report_period", "announcement_date", "q_gsprofit_margin"]
    ].rename(
        columns={
            "report_period": "prior_report_period",
            "announcement_date": "prior_announcement_date",
            "q_gsprofit_margin": "prior_q_gsprofit_margin",
        }
    )
    paired = current.merge(prior, on="prior_report_period", how="left", validate="m:1")
    has_prior = paired["prior_q_gsprofit_margin"].notna()
    prior_is_earlier = paired["prior_announcement_date"].lt(paired["announcement_date"])
    eligible = has_prior & prior_is_earlier
    paired = paired.loc[eligible].copy()
    paired["tushare_q_gross_margin_yoy_change_pp"] = (
        paired["q_gsprofit_margin"] - paired["prior_q_gsprofit_margin"]
    )
    finite_factor = np.isfinite(
        paired["tushare_q_gross_margin_yoy_change_pp"].to_numpy(dtype=float, copy=False)
    )
    if not finite_factor.all():
        raise RichDataError(
            "derived Tushare gross-margin year-over-year change is non-finite"
        )

    code = str(expected_parts.iloc[0, 0])
    exchange = str(expected_parts.iloc[0, 1])
    instrument = qlib_symbol(code)
    if not instrument.startswith(exchange):
        raise RichDataError(
            "Tushare fina_indicator stock code and exchange suffix disagree: "
            f"{expected_code}"
        )
    paired = paired.assign(instrument=instrument, provider="tushare")
    result = (
        paired.loc[:, list(TUSHARE_GROSS_MARGIN_COLUMNS)]
        .sort_values(
            ["announcement_date", "report_period", "instrument"], kind="stable"
        )
        .reset_index(drop=True)
    )
    factor = result["tushare_q_gross_margin_yoy_change_pp"]
    return result, {
        "input_rows": int(len(raw)),
        "exact_five_field_duplicate_rows_collapsed": duplicate_rows,
        "initial_rows_observed": int(initial_rows.sum()),
        "revised_rows_observed": int(revised_rows.sum()),
        "missing_margin_rows_excluded": int(missing_margin.sum()),
        "ambiguous_initial_periods_excluded": int(len(ambiguous_periods)),
        "initial_quarter_rows_retained": int(len(complete_initial)),
        "current_periods_without_prior_year_initial_excluded": int((~has_prior).sum()),
        "prior_announcement_not_earlier_excluded": int(
            (has_prior & ~prior_is_earlier).sum()
        ),
        "derived_yoy_events_written": int(len(result)),
        "distinct_derived_values": int(factor.nunique()),
        "minimum_derived_value": float(factor.min()) if len(factor) else None,
        "maximum_derived_value": float(factor.max()) if len(factor) else None,
    }


def canonicalize_tushare_management_continuity(
    frame: pd.DataFrame,
    expected_ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aggregate manager identities without persisting identity material."""

    empty_quality: dict[str, Any] = {
        "input_rows": 0,
        "exact_semantic_duplicate_rows_collapsed": 0,
        "multiple_role_rows_collapsed": 0,
        "unique_identity_rows_in_memory": 0,
        "departing_identity_rows": 0,
        "nondeparting_identity_rows": 0,
        "stock_announcement_events_written": 0,
        "distinct_factor_values": 0,
    }
    if frame is None or frame.empty:
        return (
            pd.DataFrame(columns=TUSHARE_MANAGEMENT_CONTINUITY_COLUMNS),
            empty_quality,
        )
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_MANAGEMENT_CONTINUITY_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare stk_managers response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(
        set(raw.columns) - set(TUSHARE_MANAGEMENT_CONTINUITY_RAW_FIELDS)
    )
    if unexpected_columns:
        raise RichDataError(
            "Tushare stk_managers response contains fields outside the frozen "
            "whitelist: " + ", ".join(unexpected_columns)
        )
    expected_code = str(expected_ts_code).strip().upper()
    expected_parts = pd.Series([expected_code], dtype="string").str.extract(
        r"^(\d{6})\.(SH|SZ)$"
    )
    if expected_parts.isna().any(axis=None):
        raise RichDataError(
            f"invalid frozen Tushare stk_managers stock: {expected_code}"
        )
    if announcement_start > announcement_end:
        raise RichDataError("Tushare stk_managers announcement range is reversed")

    def normalized_manager_name(value: Any) -> str | None:
        if pd.isna(value):
            return None
        normalized = unicodedata.normalize("NFKC", str(value))
        normalized = " ".join(normalized.strip().split())
        return normalized or None

    source_code = (
        raw["ts_code"].astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    code_parts = source_code.str.extract(r"^(\d{6})\.(SH|SZ|BJ)$")
    announcement_date = pd.to_datetime(
        raw["ann_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    manager_name = raw["name"].map(normalized_manager_name).astype("string")
    end_date_text = raw["end_date"].astype("string").str.strip().replace("", pd.NA)
    end_date = pd.to_datetime(
        end_date_text, format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    invalid_required = (
        source_code.isna()
        | code_parts[0].isna()
        | code_parts[1].isna()
        | announcement_date.isna()
        | manager_name.isna()
    )
    invalid_end_date = end_date_text.notna() & end_date.isna()
    if invalid_required.any() or invalid_end_date.any():
        invalid_rows = int((invalid_required | invalid_end_date).sum())
        raise RichDataError(
            "Tushare stk_managers response contains "
            f"{invalid_rows} rows with invalid stock, announcement date, "
            "identity, or departure date"
        )
    if not source_code.eq(expected_code).all():
        raise RichDataError(
            "Tushare stk_managers response contains a stock outside its frozen request"
        )
    if code_parts[1].eq("BJ").any():
        raise RichDataError(
            "Tushare stk_managers response unexpectedly contains a BSE stock"
        )
    request_start = pd.Timestamp(announcement_start)
    request_end = pd.Timestamp(announcement_end)
    if not announcement_date.between(request_start, request_end).all():
        raise RichDataError(
            "Tushare stk_managers response contains an announcement outside its request"
        )
    mismatched_departure = end_date.notna() & ~end_date.eq(announcement_date)
    if mismatched_departure.any():
        raise RichDataError(
            "Tushare stk_managers response contains "
            f"{int(mismatched_departure.sum())} departure dates unequal to ann_date"
        )

    identity_hash = manager_name.map(
        lambda value: hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    )
    normalized = pd.DataFrame(
        {
            "source_code": source_code,
            "announcement_date": announcement_date,
            "identity_hash_in_memory": identity_hash,
            "departing": end_date.notna(),
        }
    )
    exact_key = [
        "source_code",
        "announcement_date",
        "identity_hash_in_memory",
        "departing",
    ]
    before_exact = len(normalized)
    normalized = normalized.drop_duplicates(exact_key, ignore_index=True)
    exact_duplicates = int(before_exact - len(normalized))
    identity_key = [
        "source_code",
        "announcement_date",
        "identity_hash_in_memory",
    ]
    identity_state = (
        normalized.groupby(identity_key, as_index=False, observed=True)
        .agg(departing=("departing", "max"))
        .sort_values(identity_key, kind="stable")
        .reset_index(drop=True)
    )
    multiple_role_rows = int(len(normalized) - len(identity_state))
    event_key = ["source_code", "announcement_date"]
    events = (
        identity_state.groupby(event_key, as_index=False, observed=True)
        .agg(
            manager_count=("identity_hash_in_memory", "nunique"),
            departing_manager_count=("departing", "sum"),
        )
        .sort_values(event_key, kind="stable")
        .reset_index(drop=True)
    )
    manager_count = pd.to_numeric(events["manager_count"], errors="coerce")
    departing_count = pd.to_numeric(events["departing_manager_count"], errors="coerce")
    if (
        manager_count.isna().any()
        or manager_count.le(0).any()
        or departing_count.isna().any()
        or departing_count.lt(0).any()
        or departing_count.gt(manager_count).any()
    ):
        raise RichDataError("invalid Tushare management identity aggregation")
    continuity = 1.0 - departing_count.astype(float) / manager_count.astype(float)
    if (
        not np.isfinite(continuity.to_numpy(dtype=float, copy=False)).all()
        or not continuity.between(0.0, 1.0).all()
    ):
        raise RichDataError("derived Tushare management continuity is outside [0, 1]")
    code, exchange = expected_parts.iloc[0].astype(str).tolist()
    instrument = qlib_symbol(code)
    if not instrument.startswith(exchange):
        raise RichDataError(
            "Tushare stk_managers stock code and exchange suffix disagree: "
            f"{expected_code}"
        )
    result = pd.DataFrame(
        {
            "announcement_date": events["announcement_date"],
            "instrument": instrument,
            "manager_count": manager_count.astype("int64"),
            "departing_manager_count": departing_count.astype("int64"),
            "tushare_management_continuity_share": continuity.astype("float64"),
            "provider": "tushare",
        }
    )
    result = (
        result.loc[:, list(TUSHARE_MANAGEMENT_CONTINUITY_COLUMNS)]
        .sort_values(["announcement_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    if result.duplicated(["instrument", "announcement_date"]).any():
        raise RichDataError(
            "Tushare management continuity contains duplicate stock-announcement keys"
        )
    return result, {
        "input_rows": int(len(raw)),
        "exact_semantic_duplicate_rows_collapsed": exact_duplicates,
        "multiple_role_rows_collapsed": multiple_role_rows,
        "unique_identity_rows_in_memory": int(len(identity_state)),
        "departing_identity_rows": int(identity_state["departing"].sum()),
        "nondeparting_identity_rows": int((~identity_state["departing"]).sum()),
        "stock_announcement_events_written": int(len(result)),
        "distinct_factor_values": int(continuity.nunique()),
    }


def canonicalize_tushare_stock_st_membership(
    frame: pd.DataFrame,
    expected_trade_date: dt.date,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one complete ST list and retain only code/date membership."""

    if frame is None or frame.empty:
        raise RichDataError(
            "Tushare stock_st response is empty; absence cannot prove a complete list"
        )
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_ST_MEMBERSHIP_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare stock_st response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(
        set(raw.columns) - set(TUSHARE_ST_MEMBERSHIP_RAW_FIELDS)
    )
    if unexpected_columns:
        raise RichDataError(
            "Tushare stock_st response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected_columns)
        )

    source_code = (
        raw["ts_code"].astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    code_parts = source_code.str.extract(r"^(\d{6})\.(SH|SZ|BJ)$")
    trade_date = pd.to_datetime(
        raw["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    source_type = (
        raw["type"].astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    invalid = (
        source_code.isna()
        | code_parts[0].isna()
        | code_parts[1].isna()
        | trade_date.isna()
        | source_type.isna()
    )
    if invalid.any():
        raise RichDataError(
            "Tushare stock_st response contains "
            f"{int(invalid.sum())} incomplete or malformed key/type rows"
        )
    expected_ts = pd.Timestamp(expected_trade_date)
    if not trade_date.eq(expected_ts).all():
        raise RichDataError(
            "Tushare stock_st response contains a date outside the exact request"
        )
    if not source_type.eq("ST").all():
        unsupported = sorted(set(source_type.loc[~source_type.eq("ST")].astype(str)))
        raise RichDataError(
            "Tushare stock_st response contains a type outside the frozen literal ST: "
            + ", ".join(unsupported)
        )
    source_keys = pd.DataFrame({"ts_code": source_code, "trade_date": trade_date})
    if source_keys.duplicated(["ts_code", "trade_date"]).any():
        raise RichDataError(
            "Tushare stock_st response contains duplicate stock-date keys"
        )

    outside_bj = code_parts[1].eq("BJ")
    retained_parts = code_parts.loc[~outside_bj].copy()
    retained_dates = trade_date.loc[~outside_bj]
    instruments: list[str] = []
    for code, exchange in retained_parts.itertuples(index=False, name=None):
        instrument = qlib_symbol(str(code))
        if not instrument.startswith(str(exchange)):
            raise RichDataError(
                "Tushare stock_st stock code and exchange suffix disagree: "
                f"{code}.{exchange}"
            )
        instruments.append(instrument)
    result = pd.DataFrame(
        {
            "trade_date": retained_dates.to_numpy(),
            "instrument": instruments,
            "provider": "tushare",
        }
    )
    result = (
        result.loc[:, list(TUSHARE_ST_MEMBERSHIP_COLUMNS)]
        .sort_values(["trade_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    if result.empty:
        raise RichDataError(
            "Tushare stock_st response has no supported SH/SZ membership rows"
        )
    if result.duplicated(["trade_date", "instrument"]).any():
        raise RichDataError(
            "canonical Tushare stock_st membership has duplicate stock-date keys"
        )
    return result, {
        "input_rows": int(len(raw)),
        "outside_target_bj_rows_excluded": int(outside_bj.sum()),
        "rows_written": int(len(result)),
    }


def canonicalize_tushare_top10_float_holders(
    frame: pd.DataFrame,
    expected_ts_code: str,
    report_period_start: dt.date,
    report_period_end: dt.date,
    latest_announcement_date: dt.date,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Hash identities, select first complete reports, and derive quarter changes."""

    empty_quality = {
        "input_rows": 0,
        "source_rows_written": 0,
        "report_groups_observed": 0,
        "complete_report_groups": 0,
        "incomplete_report_groups_excluded": 0,
        "first_complete_report_periods": 0,
        "later_complete_revision_groups_not_used": 0,
        "factor_ready_consecutive_pairs": 0,
    }
    if frame is None or frame.empty:
        return (
            pd.DataFrame(columns=TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS),
            pd.DataFrame(columns=TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS),
            empty_quality,
        )
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_TOP10_FLOAT_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare top10_floatholders response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(set(raw.columns) - set(TUSHARE_TOP10_FLOAT_RAW_FIELDS))
    if unexpected_columns:
        raise RichDataError(
            "Tushare top10_floatholders response contains fields outside the "
            "frozen whitelist: " + ", ".join(unexpected_columns)
        )

    expected_parts = expected_ts_code.strip().upper().split(".", 1)
    if (
        len(expected_parts) != 2
        or len(expected_parts[0]) != 6
        or not expected_parts[0].isdigit()
        or expected_parts[1] not in {"SH", "SZ"}
    ):
        raise RichDataError(
            f"invalid frozen top10_floatholders stock code: {expected_ts_code}"
        )
    expected_instrument = qlib_symbol(expected_parts[0])
    if not expected_instrument.startswith(expected_parts[1]):
        raise RichDataError(
            f"stock code and exchange suffix disagree: {expected_ts_code}"
        )

    def normalized_holder_name(value: Any) -> str | None:
        if pd.isna(value):
            return None
        normalized = unicodedata.normalize("NFKC", str(value))
        normalized = " ".join(normalized.strip().split())
        return normalized or None

    holder_names = raw["holder_name"].map(normalized_holder_name)
    normalized = pd.DataFrame(
        {
            "announcement_date": pd.to_datetime(
                raw["ann_date"].astype("string"),
                format="%Y%m%d",
                errors="coerce",
            ).dt.normalize(),
            "report_period": pd.to_datetime(
                raw["end_date"].astype("string"),
                format="%Y%m%d",
                errors="coerce",
            ).dt.normalize(),
            "instrument": expected_instrument,
            "holder_name": holder_names,
            "hold_float_ratio": pd.to_numeric(raw["hold_float_ratio"], errors="coerce"),
            "source_ts_code": raw["ts_code"].astype("string").str.strip().str.upper(),
        }
    )
    required = [
        "announcement_date",
        "report_period",
        "holder_name",
        "hold_float_ratio",
        "source_ts_code",
    ]
    missing = normalized[required].isna().any(axis=1)
    finite_ratio = np.isfinite(normalized["hold_float_ratio"])
    if missing.any() or (~finite_ratio).any():
        invalid_rows = int((missing | ~finite_ratio).sum())
        raise RichDataError(
            "Tushare top10_floatholders response contains "
            f"{invalid_rows} incomplete or non-finite rows"
        )
    if not normalized["source_ts_code"].eq(expected_ts_code.upper()).all():
        observed = sorted(set(normalized["source_ts_code"].astype(str)))
        raise RichDataError(
            "Tushare top10_floatholders response contains a stock outside its "
            f"request: expected {expected_ts_code.upper()}, observed {observed}"
        )
    ratio = normalized["hold_float_ratio"]
    if not ratio.between(0.0, 100.0).all():
        raise RichDataError(
            "Tushare top10_floatholders response contains a ratio outside [0, 100]"
        )
    report_start = pd.Timestamp(report_period_start)
    report_end = pd.Timestamp(report_period_end)
    if not normalized["report_period"].between(report_start, report_end).all():
        raise RichDataError(
            "Tushare top10_floatholders response contains a report period outside "
            "the request"
        )
    standard_quarter_end = (
        normalized["report_period"]
        .dt.strftime("%m%d")
        .isin({"0331", "0630", "0930", "1231"})
    )
    if not standard_quarter_end.all():
        raise RichDataError(
            "Tushare top10_floatholders response contains a non-quarter-end period"
        )
    if normalized["announcement_date"].gt(pd.Timestamp(latest_announcement_date)).any():
        raise RichDataError(
            "Tushare top10_floatholders response contains a future announcement"
        )
    if normalized["announcement_date"].lt(normalized["report_period"]).any():
        raise RichDataError(
            "Tushare top10_floatholders response contains an announcement before "
            "its report period"
        )

    normalized["holder_name_sha256"] = normalized["holder_name"].map(
        lambda value: hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    )
    raw_event_key = [
        "announcement_date",
        "report_period",
        "instrument",
        "holder_name_sha256",
    ]
    if normalized.duplicated(raw_event_key).any():
        raise RichDataError(
            "Tushare top10_floatholders response contains duplicate holder event keys"
        )

    persisted = normalized.assign(provider="tushare").loc[
        :, list(TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS)
    ]
    persisted = persisted.sort_values(
        ["instrument", "report_period", "announcement_date", "holder_name_sha256"],
        kind="stable",
    ).reset_index(drop=True)

    group_key = ["instrument", "report_period", "announcement_date"]
    groups = (
        persisted.groupby(group_key, as_index=False, observed=True)
        .agg(
            top10_float_holder_count=("holder_name_sha256", "nunique"),
            top10_float_concentration_pct=("hold_float_ratio", "sum"),
        )
        .sort_values(group_key, kind="stable")
        .reset_index(drop=True)
    )
    if groups["top10_float_holder_count"].gt(10).any():
        raise RichDataError(
            "Tushare top10_floatholders response contains more than ten unique "
            "holders in one report group"
        )
    complete = groups["top10_float_holder_count"].eq(10)
    complete_groups = groups.loc[complete].copy()
    concentration = complete_groups["top10_float_concentration_pct"]
    if (
        not np.isfinite(concentration).all()
        or concentration.lt(0.0).any()
        or concentration.gt(100.000001).any()
    ):
        raise RichDataError(
            "Tushare top10_floatholders complete-group concentration falls "
            "outside [0, 100.000001]"
        )
    first_complete = (
        complete_groups.sort_values(
            ["instrument", "report_period", "announcement_date"], kind="stable"
        )
        .drop_duplicates(["instrument", "report_period"], keep="first")
        .reset_index(drop=True)
    )

    def previous_quarter(period: pd.Timestamp) -> pd.Timestamp:
        if period.month == 3:
            return pd.Timestamp(year=period.year - 1, month=12, day=31)
        if period.month == 6:
            return pd.Timestamp(year=period.year, month=3, day=31)
        if period.month == 9:
            return pd.Timestamp(year=period.year, month=6, day=30)
        return pd.Timestamp(year=period.year, month=9, day=30)

    lookup = {
        (str(row.instrument), pd.Timestamp(row.report_period)): row
        for row in first_complete.itertuples(index=False)
    }
    factor_rows: list[dict[str, Any]] = []
    for row in first_complete.itertuples(index=False):
        report_period = pd.Timestamp(row.report_period)
        prior_period = previous_quarter(report_period)
        prior = lookup.get((str(row.instrument), prior_period))
        if prior is None or pd.Timestamp(prior.announcement_date) > pd.Timestamp(
            row.announcement_date
        ):
            continue
        change = float(row.top10_float_concentration_pct) - float(
            prior.top10_float_concentration_pct
        )
        factor_rows.append(
            {
                "announcement_date": pd.Timestamp(row.announcement_date),
                "report_period": report_period,
                "previous_report_period": prior_period,
                "instrument": str(row.instrument),
                "top10_float_holder_count": int(row.top10_float_holder_count),
                "top10_float_concentration_pct": float(
                    row.top10_float_concentration_pct
                ),
                "top10_float_concentration_change_pp": change,
                "provider": "tushare",
            }
        )
    factors = (
        pd.DataFrame(factor_rows, columns=TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS)
        .sort_values(
            ["instrument", "report_period", "announcement_date"], kind="stable"
        )
        .reset_index(drop=True)
    )
    if not factors.empty:
        changes = factors["top10_float_concentration_change_pp"]
        if (
            not np.isfinite(changes).all()
            or changes.lt(-100.000001).any()
            or changes.gt(100.000001).any()
        ):
            raise RichDataError(
                "derived top-ten float concentration change falls outside its "
                "frozen bounds"
            )
        if factors.duplicated(
            ["instrument", "announcement_date", "report_period"]
        ).any():
            raise RichDataError(
                "derived top-ten float concentration contains duplicate factor keys"
            )
    return (
        persisted,
        factors,
        {
            "input_rows": int(len(raw)),
            "source_rows_written": int(len(persisted)),
            "report_groups_observed": int(len(groups)),
            "complete_report_groups": int(complete.sum()),
            "incomplete_report_groups_excluded": int((~complete).sum()),
            "first_complete_report_periods": int(len(first_complete)),
            "later_complete_revision_groups_not_used": int(
                len(complete_groups) - len(first_complete)
            ),
            "factor_ready_consecutive_pairs": int(len(factors)),
        },
    )


def canonicalize_tushare_cash_conversion_endpoint(
    frame: pd.DataFrame,
    endpoint: str,
    expected_ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
    latest_actual_announcement_date: dt.date,
    *,
    allow_complete_integer_non_target_company_type_codes: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the frozen statement-version policy before cross-endpoint joining."""

    endpoint_specs = {
        "income": {
            "raw_fields": TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS,
            "metric": "n_income_attr_p",
            "columns": TUSHARE_CASH_CONVERSION_INCOME_COLUMNS,
            "announcement_column": "income_announcement_date",
            "actual_column": "income_actual_announcement_date",
        },
        "cashflow": {
            "raw_fields": TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS,
            "metric": "n_cashflow_act",
            "columns": TUSHARE_CASH_CONVERSION_CASHFLOW_COLUMNS,
            "announcement_column": "cashflow_announcement_date",
            "actual_column": "cashflow_actual_announcement_date",
        },
    }
    if endpoint not in endpoint_specs:
        raise RichDataError(f"unsupported cash-conversion endpoint: {endpoint}")
    spec = endpoint_specs[endpoint]
    empty_quality: dict[str, Any] = {
        "input_rows": 0,
        "non_target_company_rows_excluded": 0,
        "non_target_company_type_counts": {},
        "target_company_periods_observed": 0,
        "adjustment_periods_excluded": 0,
        "no_type_one_periods_excluded": 0,
        "missing_metric_periods_excluded": 0,
        "ambiguous_type_one_periods_excluded": 0,
        "semantic_duplicate_rows_collapsed": 0,
        "accepted_periods": 0,
        "update_flag_counts": {},
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=spec["columns"]), empty_quality

    raw = frame.copy()
    raw_fields = tuple(spec["raw_fields"])
    missing_columns = [field for field in raw_fields if field not in raw]
    if missing_columns:
        raise RichDataError(
            f"Tushare {endpoint} response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(set(raw.columns) - set(raw_fields))
    if unexpected_columns:
        raise RichDataError(
            f"Tushare {endpoint} response contains fields outside the frozen "
            "whitelist: " + ", ".join(unexpected_columns)
        )

    expected_code = expected_ts_code.strip().upper()
    expected_parts = expected_code.split(".", 1)
    if (
        len(expected_parts) != 2
        or len(expected_parts[0]) != 6
        or not expected_parts[0].isdigit()
        or expected_parts[1] not in {"SH", "SZ"}
    ):
        raise RichDataError(
            f"invalid frozen cash-conversion stock code: {expected_ts_code}"
        )
    expected_instrument = qlib_symbol(expected_parts[0])
    if not expected_instrument.startswith(expected_parts[1]):
        raise RichDataError(
            f"stock code and exchange suffix disagree: {expected_ts_code}"
        )

    source_code = (
        raw["ts_code"].astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    announcement_date = pd.to_datetime(
        raw["ann_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    actual_announcement_date = pd.to_datetime(
        raw["f_ann_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    report_period = pd.to_datetime(
        raw["end_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    report_type_number = pd.to_numeric(raw["report_type"], errors="coerce")
    company_type_number = pd.to_numeric(raw["comp_type"], errors="coerce")
    update_flag = raw["update_flag"].astype("string").str.strip().replace("", pd.NA)
    report_type_integer = (
        report_type_number.notna()
        & pd.Series(np.isfinite(report_type_number), index=raw.index)
        & report_type_number.mod(1).eq(0)
    )
    company_type_integer = (
        company_type_number.notna()
        & pd.Series(np.isfinite(company_type_number), index=raw.index)
        & company_type_number.mod(1).eq(0)
    )
    invalid_key = (
        source_code.isna()
        | announcement_date.isna()
        | actual_announcement_date.isna()
        | report_period.isna()
        | ~report_type_integer
        | ~company_type_integer
        | update_flag.isna()
    )
    if invalid_key.any():
        raise RichDataError(
            f"Tushare {endpoint} response contains "
            f"{int(invalid_key.sum())} rows with incomplete or invalid statement keys"
        )

    report_type = report_type_number.astype(int)
    company_type = company_type_number.astype(int)
    unknown_report_types = sorted(
        set(report_type.astype(int)) - TUSHARE_CASH_CONVERSION_KNOWN_REPORT_TYPES
    )
    if unknown_report_types:
        raise RichDataError(
            f"Tushare {endpoint} response contains unknown report types: "
            f"{unknown_report_types}"
        )
    unknown_company_types = sorted(
        set(company_type.astype(int)) - TUSHARE_CASH_CONVERSION_KNOWN_COMPANY_TYPES
    )
    if (
        unknown_company_types
        and not allow_complete_integer_non_target_company_type_codes
    ):
        raise RichDataError(
            f"Tushare {endpoint} response contains unknown company types: "
            f"{unknown_company_types}"
        )
    if not source_code.eq(expected_code).all():
        observed = sorted(set(source_code.astype(str)))
        raise RichDataError(
            f"Tushare {endpoint} response contains a stock outside its request: "
            f"expected {expected_code}, observed {observed}"
        )

    start_stamp = pd.Timestamp(announcement_start)
    end_stamp = pd.Timestamp(announcement_end)
    latest_stamp = pd.Timestamp(latest_actual_announcement_date)
    if announcement_date.lt(start_stamp).any() or announcement_date.gt(end_stamp).any():
        raise RichDataError(
            f"Tushare {endpoint} response contains an announcement outside the "
            "frozen request range"
        )
    if actual_announcement_date.lt(announcement_date).any():
        raise RichDataError(
            f"Tushare {endpoint} response contains an actual announcement before ann_date"
        )
    if actual_announcement_date.gt(latest_stamp).any():
        raise RichDataError(
            f"Tushare {endpoint} response contains an actual announcement after "
            "the frozen observation date"
        )
    if report_period.gt(announcement_date).any():
        raise RichDataError(
            f"Tushare {endpoint} response contains a report period after ann_date"
        )
    standard_quarter_ends = {"03-31", "06-30", "09-30", "12-31"}
    if not report_period.dt.strftime("%m-%d").isin(standard_quarter_ends).all():
        raise RichDataError(
            f"Tushare {endpoint} response contains a non-standard quarter end"
        )

    metric_name = str(spec["metric"])
    metric = pd.to_numeric(raw[metric_name], errors="coerce")
    normalized = pd.DataFrame(
        {
            "announcement_date": announcement_date,
            "actual_announcement_date": actual_announcement_date,
            "report_period": report_period,
            "instrument": expected_instrument,
            "report_type": report_type,
            "company_type": company_type,
            "metric": metric,
            "update_flag": update_flag,
        }
    )
    update_flag_counts = {
        str(key): int(value)
        for key, value in normalized["update_flag"]
        .value_counts(dropna=False)
        .sort_index()
        .items()
    }
    non_target_company_type_counts = {
        str(int(key)): int(value)
        for key, value in normalized.loc[
            normalized["company_type"].ne(1), "company_type"
        ]
        .value_counts()
        .sort_index()
        .items()
    }
    target = normalized.loc[normalized["company_type"].eq(1)].copy()
    quality: dict[str, Any] = {
        "input_rows": int(len(normalized)),
        "non_target_company_rows_excluded": int(normalized["company_type"].ne(1).sum()),
        "non_target_company_type_counts": non_target_company_type_counts,
        "target_company_periods_observed": int(target["report_period"].nunique()),
        "adjustment_periods_excluded": 0,
        "no_type_one_periods_excluded": 0,
        "missing_metric_periods_excluded": 0,
        "ambiguous_type_one_periods_excluded": 0,
        "semantic_duplicate_rows_collapsed": 0,
        "accepted_periods": 0,
        "update_flag_counts": update_flag_counts,
    }
    accepted_rows: list[dict[str, Any]] = []
    for period, group in target.groupby("report_period", sort=True, observed=True):
        observed_types = set(group["report_type"].astype(int))
        if observed_types & TUSHARE_CASH_CONVERSION_ADJUSTMENT_REPORT_TYPES:
            quality["adjustment_periods_excluded"] += 1
            continue
        type_one = group.loc[group["report_type"].eq(1)].copy()
        if type_one.empty:
            quality["no_type_one_periods_excluded"] += 1
            continue
        finite_metric = pd.Series(np.isfinite(type_one["metric"]), index=type_one.index)
        if type_one["metric"].isna().any() or (~finite_metric).any():
            quality["missing_metric_periods_excluded"] += 1
            continue
        semantic = type_one.drop_duplicates(
            ["announcement_date", "actual_announcement_date", "metric"]
        )
        if len(semantic) != 1:
            quality["ambiguous_type_one_periods_excluded"] += 1
            continue
        quality["semantic_duplicate_rows_collapsed"] += int(len(type_one) - 1)
        row = semantic.iloc[0]
        accepted_rows.append(
            {
                str(spec["announcement_column"]): pd.Timestamp(
                    row["announcement_date"]
                ),
                str(spec["actual_column"]): pd.Timestamp(
                    row["actual_announcement_date"]
                ),
                "report_period": pd.Timestamp(period),
                "instrument": expected_instrument,
                metric_name: float(row["metric"]),
                "provider": "tushare",
            }
        )

    accepted = pd.DataFrame(accepted_rows, columns=spec["columns"])
    if not accepted.empty:
        accepted = accepted.sort_values(
            ["instrument", "report_period"], kind="stable"
        ).reset_index(drop=True)
        if accepted.duplicated(["instrument", "report_period"]).any():
            raise RichDataError(
                f"canonical Tushare {endpoint} rows contain a duplicate period key"
            )
    quality["accepted_periods"] = int(len(accepted))
    return accepted, quality


def derive_tushare_cash_conversion(
    income: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Join accepted statement periods and derive the sole frozen ratio."""

    if income.columns.tolist() != list(TUSHARE_CASH_CONVERSION_INCOME_COLUMNS):
        raise RichDataError(
            "cash-conversion income columns do not match the frozen schema"
        )
    if cashflow.columns.tolist() != list(TUSHARE_CASH_CONVERSION_CASHFLOW_COLUMNS):
        raise RichDataError(
            "cash-conversion cashflow columns do not match the frozen schema"
        )
    key = ["instrument", "report_period"]
    if income.duplicated(key).any() or cashflow.duplicated(key).any():
        raise RichDataError(
            "cash-conversion endpoint rows contain duplicate period keys"
        )
    income_keys = set(income.loc[:, key].itertuples(index=False, name=None))
    cashflow_keys = set(cashflow.loc[:, key].itertuples(index=False, name=None))
    joined = income.merge(
        cashflow,
        on=key,
        how="inner",
        suffixes=("_income", "_cashflow"),
        validate="one_to_one",
    )
    quality: dict[str, Any] = {
        "income_accepted_periods": int(len(income)),
        "cashflow_accepted_periods": int(len(cashflow)),
        "income_only_periods_excluded": int(len(income_keys - cashflow_keys)),
        "cashflow_only_periods_excluded": int(len(cashflow_keys - income_keys)),
        "joined_periods_before_metric_policy": int(len(joined)),
        "nonpositive_income_periods_excluded": 0,
        "nonfinite_cashflow_periods_excluded": 0,
        "nonfinite_derived_periods_excluded": 0,
        "usable_joined_periods": 0,
    }
    if joined.empty:
        return pd.DataFrame(columns=TUSHARE_CASH_CONVERSION_COLUMNS), quality
    if (
        not joined["provider_income"].eq("tushare").all()
        or not joined["provider_cashflow"].eq("tushare").all()
    ):
        raise RichDataError("cash-conversion endpoint provider identity mismatch")

    denominator = pd.to_numeric(joined["n_income_attr_p"], errors="coerce")
    numerator = pd.to_numeric(joined["n_cashflow_act"], errors="coerce")
    denominator_finite = pd.Series(np.isfinite(denominator), index=joined.index)
    numerator_finite = pd.Series(np.isfinite(numerator), index=joined.index)
    positive_denominator = denominator_finite & denominator.gt(0.0)
    quality["nonpositive_income_periods_excluded"] = int((~positive_denominator).sum())
    quality["nonfinite_cashflow_periods_excluded"] = int((~numerator_finite).sum())
    base_eligible = positive_denominator & numerator_finite
    derived = pd.Series(np.nan, index=joined.index, dtype="float64")
    derived.loc[base_eligible] = (
        numerator.loc[base_eligible] / denominator.loc[base_eligible]
    )
    derived_finite = pd.Series(np.isfinite(derived), index=joined.index)
    quality["nonfinite_derived_periods_excluded"] = int(
        (base_eligible & ~derived_finite).sum()
    )
    eligible = base_eligible & derived_finite
    accepted = joined.loc[eligible].copy()
    accepted["announcement_date"] = accepted[
        ["income_actual_announcement_date", "cashflow_actual_announcement_date"]
    ].max(axis=1)
    accepted["tushare_operating_cash_conversion"] = derived.loc[eligible]
    accepted["provider"] = "tushare"
    accepted = (
        accepted.loc[:, list(TUSHARE_CASH_CONVERSION_COLUMNS)]
        .sort_values(
            ["instrument", "report_period", "announcement_date"], kind="stable"
        )
        .reset_index(drop=True)
    )
    if accepted.duplicated(["instrument", "announcement_date", "report_period"]).any():
        raise RichDataError("cash-conversion factor rows contain duplicate event keys")
    quality["usable_joined_periods"] = int(len(accepted))
    return accepted, quality


def canonicalize_tushare_daily_pb(
    frame: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Normalize a daily_basic PB response and derive positive book-to-market."""

    empty_stats = {
        "input_rows": 0,
        "missing_pb_rows_excluded": 0,
        "nonpositive_pb_rows_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_DAILY_PB_COLUMNS), empty_stats
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_DAILY_PB_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare daily_basic PB response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(set(raw.columns) - set(TUSHARE_DAILY_PB_RAW_FIELDS))
    if unexpected_columns:
        raise RichDataError(
            "Tushare daily_basic PB response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected_columns)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        source_code = str(value).strip()
        parts = source_code.split(".", 1)
        code = parts[0].strip()
        if len(code) != 6 or not code.isdigit():
            return None
        suffix = parts[1].upper() if len(parts) == 2 else ""
        # Tushare back-labels some historical NEEQ rows with a ``.BJ``
        # suffix.  The frozen PB contract explicitly excludes and counts BSE
        # names at the point-in-time holding-universe gate.  Preserve their
        # source identity long enough to reach that gate instead of
        # misclassifying a valid six-digit source key as missing.
        if suffix == "BJ" and code.startswith(("4", "8")):
            return f"BJ{code}"
        try:
            symbol = qlib_symbol(code)
        except RichDataError:
            return None
        if suffix in {"SH", "SZ"} and not symbol.startswith(suffix):
            return None
        return symbol

    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "instrument": raw["ts_code"].map(instrument),
            "pb": pd.to_numeric(raw["pb"], errors="coerce"),
        }
    )
    missing_key = normalized[["trade_date", "instrument"]].isna().any(axis=1)
    if missing_key.any():
        raise RichDataError(
            f"Tushare daily_basic PB response contains {int(missing_key.sum())} missing keys"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not normalized["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "Tushare daily_basic PB response contains a date outside the request"
        )
    if normalized.duplicated(["instrument", "trade_date"]).any():
        raise RichDataError(
            "Tushare daily_basic PB response contains duplicate instrument/date keys"
        )
    finite_or_missing = normalized["pb"].isna() | np.isfinite(normalized["pb"])
    if not finite_or_missing.all():
        raise RichDataError(
            "Tushare daily_basic PB response contains an infinite PB value"
        )
    missing_pb = normalized["pb"].isna()
    nonpositive_pb = normalized["pb"].notna() & normalized["pb"].le(0.0)
    valid = normalized.loc[~missing_pb & ~nonpositive_pb].copy()
    valid["pb"] = valid["pb"].astype("float64")
    valid["tushare_positive_book_to_market"] = 1.0 / valid["pb"]
    if (
        not np.isfinite(valid["tushare_positive_book_to_market"]).all()
        or not valid["tushare_positive_book_to_market"].gt(0.0).all()
    ):
        raise RichDataError("derived Tushare book-to-market is not finite and positive")
    valid["provider"] = "tushare"
    result = (
        valid.loc[:, list(TUSHARE_DAILY_PB_COLUMNS)]
        .sort_values(["trade_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    return result, {
        "input_rows": int(len(raw)),
        "missing_pb_rows_excluded": int(missing_pb.sum()),
        "nonpositive_pb_rows_excluded": int(nonpositive_pb.sum()),
        "rows_written": int(len(result)),
    }


def canonicalize_tushare_free_float_scarcity(
    frame: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Normalize daily_basic share counts and derive structural scarcity."""

    empty_stats = {
        "input_rows": 0,
        "missing_or_nonfinite_share_rows_excluded": 0,
        "nonpositive_share_rows_excluded": 0,
        "free_share_above_total_share_rows_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return (
            pd.DataFrame(columns=TUSHARE_FREE_FLOAT_SCARCITY_COLUMNS),
            empty_stats,
        )
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare daily_basic free-float response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(
        set(raw.columns) - set(TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS)
    )
    if unexpected_columns:
        raise RichDataError(
            "Tushare daily_basic free-float response contains fields outside the "
            "frozen whitelist: " + ", ".join(unexpected_columns)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        source_code = str(value).strip()
        parts = source_code.split(".", 1)
        code = parts[0].strip()
        if len(code) != 6 or not code.isdigit():
            return None
        suffix = parts[1].upper() if len(parts) == 2 else ""
        if suffix == "BJ" and code.startswith(("4", "8", "9")):
            return f"BJ{code}"
        try:
            symbol = qlib_symbol(code)
        except RichDataError:
            return None
        if suffix in {"SH", "SZ"} and not symbol.startswith(suffix):
            return None
        return symbol

    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw["trade_date"].astype("string"),
                format="%Y%m%d",
                errors="coerce",
            ).dt.normalize(),
            "instrument": raw["ts_code"].map(instrument),
            "total_share": pd.to_numeric(raw["total_share"], errors="coerce"),
            "free_share": pd.to_numeric(raw["free_share"], errors="coerce"),
        }
    )
    missing_key = normalized[["trade_date", "instrument"]].isna().any(axis=1)
    if missing_key.any():
        raise RichDataError(
            "Tushare daily_basic free-float response contains "
            f"{int(missing_key.sum())} missing keys"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not normalized["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "Tushare daily_basic free-float response contains a date outside the request"
        )
    if normalized.duplicated(["instrument", "trade_date"]).any():
        raise RichDataError(
            "Tushare daily_basic free-float response contains duplicate "
            "instrument/date keys"
        )

    finite = pd.Series(
        np.isfinite(normalized["total_share"]) & np.isfinite(normalized["free_share"]),
        index=normalized.index,
    )
    missing_or_nonfinite = ~finite
    nonpositive = finite & (
        normalized["total_share"].le(0.0) | normalized["free_share"].le(0.0)
    )
    above_total = (
        finite & ~nonpositive & normalized["free_share"].gt(normalized["total_share"])
    )
    eligible = finite & ~nonpositive & ~above_total
    accepted = normalized.loc[eligible].copy()
    accepted["total_share"] = accepted["total_share"].astype("float64")
    accepted["free_share"] = accepted["free_share"].astype("float64")
    accepted["tushare_free_float_scarcity"] = (
        1.0 - accepted["free_share"] / accepted["total_share"]
    )
    factor = accepted["tushare_free_float_scarcity"]
    if (
        not np.isfinite(factor).all()
        or not factor.ge(0.0).all()
        or not factor.lt(1.0).all()
    ):
        raise RichDataError(
            "derived Tushare free-float scarcity is outside the frozen [0, 1) range"
        )
    accepted["provider"] = "tushare"
    result = (
        accepted.loc[:, list(TUSHARE_FREE_FLOAT_SCARCITY_COLUMNS)]
        .sort_values(["trade_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    return result, {
        "input_rows": int(len(raw)),
        "missing_or_nonfinite_share_rows_excluded": int(missing_or_nonfinite.sum()),
        "nonpositive_share_rows_excluded": int(nonpositive.sum()),
        "free_share_above_total_share_rows_excluded": int(above_total.sum()),
        "rows_written": int(len(result)),
    }


def canonicalize_tushare_sw_classification(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the frozen SW2021 level-one classification response."""

    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_SW_CLASSIFICATION_RAW_FIELDS)
    raw = frame.copy()
    missing = [
        field for field in TUSHARE_SW_CLASSIFICATION_RAW_FIELDS if field not in raw
    ]
    if missing:
        raise RichDataError(
            "Tushare SW classification response lacks requested fields: "
            + ", ".join(missing)
        )
    unexpected = sorted(set(raw.columns) - set(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS))
    if unexpected:
        raise RichDataError(
            "Tushare SW classification response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected)
        )
    result = raw.loc[:, list(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS)].copy()
    for column in TUSHARE_SW_CLASSIFICATION_RAW_FIELDS:
        result[column] = result[column].astype("string").str.strip()
    if result[list(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS)].isna().any(axis=None):
        raise RichDataError(
            "Tushare SW classification response contains a missing value"
        )
    if not result["level"].eq("L1").all() or not result["src"].eq("SW2021").all():
        raise RichDataError("Tushare SW classification response is not SW2021 L1")
    if not result["index_code"].str.fullmatch(r"\d{6}\.SI").all():
        raise RichDataError("Tushare SW classification contains an invalid index code")
    if result["index_code"].duplicated().any():
        raise RichDataError("Tushare SW classification contains duplicate L1 codes")
    return result.sort_values("index_code", kind="stable").reset_index(drop=True)


def canonicalize_tushare_sw_members(
    frame: pd.DataFrame,
    *,
    expected_l1_code: str,
    expected_is_new: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one frozen SW2021 membership partition without price data."""

    if expected_is_new not in {"Y", "N"}:
        raise RichDataError(
            f"unsupported expected SW membership is_new: {expected_is_new}"
        )
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_SW_MEMBERSHIP_COLUMNS), {
            "input_rows": 0,
            "rows_written": 0,
            "missing_out_date_rows": 0,
            "unsupported_provider_symbol_rows_excluded": 0,
        }
    raw = frame.copy()
    missing = [field for field in TUSHARE_SW_MEMBERSHIP_RAW_FIELDS if field not in raw]
    if missing:
        raise RichDataError(
            "Tushare SW membership response lacks requested fields: "
            + ", ".join(missing)
        )
    unexpected = sorted(set(raw.columns) - set(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS))
    if unexpected:
        raise RichDataError(
            "Tushare SW membership response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        source_code = str(value).strip()
        parts = source_code.split(".", 1)
        code = parts[0].strip()
        suffix = parts[1].upper() if len(parts) == 2 else ""
        if len(code) != 6 or not code.isdigit():
            return None
        if suffix not in {"SH", "SZ", "BJ"}:
            return None
        return f"{suffix}{code}"

    source_ts_code = raw["ts_code"].astype("string").str.strip()
    if source_ts_code.isna().any() or source_ts_code.eq("").any():
        raise RichDataError("Tushare SW membership response contains a missing ts_code")
    normalized = pd.DataFrame(
        {
            "l1_code": raw["l1_code"].astype("string").str.strip(),
            "l1_name": raw["l1_name"].astype("string").str.strip(),
            "l2_code": raw["l2_code"].astype("string").str.strip(),
            "l2_name": raw["l2_name"].astype("string").str.strip(),
            "l3_code": raw["l3_code"].astype("string").str.strip(),
            "l3_name": raw["l3_name"].astype("string").str.strip(),
            "instrument": source_ts_code.map(instrument),
            "in_date": pd.to_datetime(
                raw["in_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "out_date": pd.to_datetime(
                raw["out_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "is_new": raw["is_new"].astype("string").str.strip().str.upper(),
        }
    )
    required = [
        "l1_code",
        "l1_name",
        "l2_code",
        "l2_name",
        "l3_code",
        "l3_name",
        "in_date",
        "is_new",
    ]
    if normalized[required].isna().any(axis=None):
        raise RichDataError("Tushare SW membership response contains a missing key")
    if not normalized["l1_code"].eq(expected_l1_code).all():
        raise RichDataError("Tushare SW membership response contains another L1 code")
    if not normalized["is_new"].eq(expected_is_new).all():
        raise RichDataError(
            "Tushare SW membership response contains another is_new value"
        )
    if (
        not normalized["l2_code"].str.fullmatch(r"\d{6}\.SI").all()
        or not normalized["l3_code"].str.fullmatch(r"\d{6}\.SI").all()
    ):
        raise RichDataError(
            "Tushare SW membership response contains an invalid industry code"
        )
    missing_out = normalized["out_date"].isna()
    if expected_is_new == "Y" and not missing_out.all():
        raise RichDataError(
            "current Tushare SW membership row unexpectedly has out_date"
        )
    if expected_is_new == "N" and missing_out.any():
        raise RichDataError("historical Tushare SW membership row lacks out_date")
    dated = normalized["out_date"].notna()
    if (normalized.loc[dated, "in_date"] > normalized.loc[dated, "out_date"]).any():
        raise RichDataError("Tushare SW membership interval starts after it ends")
    unsupported_symbols = normalized["instrument"].isna()
    unsupported_symbol_rows = int(unsupported_symbols.sum())
    normalized = normalized.loc[~unsupported_symbols].copy()
    duplicate_key = [
        "l1_code",
        "l2_code",
        "l3_code",
        "instrument",
        "in_date",
        "out_date",
        "is_new",
    ]
    if normalized.duplicated(duplicate_key).any():
        raise RichDataError(
            "Tushare SW membership response contains duplicate intervals"
        )
    normalized["provider"] = "tushare"
    result = (
        normalized.loc[:, list(TUSHARE_SW_MEMBERSHIP_COLUMNS)]
        .sort_values(
            ["l1_code", "l2_code", "l3_code", "instrument", "in_date", "is_new"],
            kind="stable",
        )
        .reset_index(drop=True)
    )
    return result, {
        "input_rows": int(len(raw)),
        "rows_written": int(len(result)),
        "missing_out_date_rows": int(missing_out.sum()),
        "unsupported_provider_symbol_rows_excluded": unsupported_symbol_rows,
    }


def canonicalize_jqdata_moneyflow(
    frame: pd.DataFrame,
    codes: list[str],
    start: dt.date,
    end: dt.date,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Normalize licensed classified flows and derive the frozen ratio locally."""

    empty_stats = {
        "input_rows": 0,
        "missing_rows_excluded": 0,
        "zero_denominator_rows_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=JQDATA_MONEYFLOW_COLUMNS), empty_stats
    raw = frame.copy()
    if not isinstance(raw.index, pd.RangeIndex):
        raw = raw.reset_index()
    date_column = _column(raw, ("time", "date", "trade_date"))
    code_column = _column(raw, ("code", "sec_code", "security"))
    if date_column is None or code_column is None:
        raise RichDataError("JQData moneyflow response lacks a time or code key")
    raw_columns: dict[str, str] = {}
    for field in JQDATA_MONEYFLOW_RAW_FIELDS:
        column = _column(raw, (field,))
        if column is None:
            raise RichDataError(
                f"JQData moneyflow response lacks requested field: {field}"
            )
        raw_columns[field] = column

    def instrument(value: Any) -> str | None:
        code = str(value).split(".", 1)[0].strip()
        try:
            return qlib_symbol(code)
        except RichDataError:
            return None

    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw[date_column], errors="coerce"
            ).dt.normalize(),
            "instrument": raw[code_column].map(instrument),
            **{
                f"{field}_amount": pd.to_numeric(raw[column], errors="coerce")
                for field, column in raw_columns.items()
            },
        }
    )
    amount_columns = [f"{field}_amount" for field in JQDATA_MONEYFLOW_RAW_FIELDS]
    complete = (
        normalized[["trade_date", "instrument", *amount_columns]].notna().all(axis=1)
    )
    missing_rows = int((~complete).sum())
    valid = normalized.loc[complete].copy()
    if valid[amount_columns].lt(0.0).any().any():
        raise RichDataError(
            "JQData moneyflow response contains a negative raw flow amount"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not valid["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "JQData moneyflow response contains a date outside the request"
        )
    requested_instruments = {qlib_symbol(code) for code in codes}
    if not set(valid["instrument"]).issubset(requested_instruments):
        raise RichDataError(
            "JQData moneyflow response contains an unrequested instrument"
        )
    if valid.duplicated(["instrument", "trade_date"]).any():
        raise RichDataError(
            "JQData moneyflow response contains duplicate instrument/date keys"
        )
    valid[amount_columns] = valid[amount_columns].astype("float64")
    denominator = valid[amount_columns].sum(axis=1)
    positive = denominator.gt(0.0)
    zero_denominator_rows = int((~positive).sum())
    valid = valid.loc[positive].copy()
    denominator = denominator.loc[positive]
    valid["jqdata_large_order_net_inflow_share"] = (
        valid["inflow_xl_amount"]
        + valid["inflow_l_amount"]
        - valid["outflow_xl_amount"]
        - valid["outflow_l_amount"]
    ) / denominator
    valid["provider"] = "jqdata"
    result = (
        valid.loc[:, list(JQDATA_MONEYFLOW_COLUMNS)]
        .sort_values(["trade_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    if not result["jqdata_large_order_net_inflow_share"].between(-1.0, 1.0).all():
        raise RichDataError("derived JQData large-order ratio falls outside [-1, 1]")
    return result, {
        "input_rows": int(len(raw)),
        "missing_rows_excluded": missing_rows,
        "zero_denominator_rows_excluded": zero_denominator_rows,
        "rows_written": int(len(result)),
    }


def validate_range(
    start: dt.date, end: dt.date, allow_large: bool, unit_count: int = 1
) -> None:
    """Guard against an accidental multi-year paid-data request."""

    if end < start:
        raise RichDataError("end date precedes start date")
    completed = latest_completed_session_date()
    if end > completed:
        raise RichDataError(
            f"end date {end.isoformat()} is not a completed A-share session; use {completed.isoformat()} or earlier"
        )
    work_units = len(pd.bdate_range(start, end)) * unit_count
    if work_units > 100 and not allow_large:
        raise RichDataError(
            f"request covers {work_units} symbol-sessions; pass --allow-large only after a small acceptance run succeeds"
        )


def frame_digest(frame: pd.DataFrame) -> str:
    """Return a stable digest for a stored data frame."""

    content = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def file_digest(path: Path) -> str:
    """Return a SHA-256 digest for an immutable manifest or specification."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_record_path(value: str | Path) -> Path:
    """Resolve a manifest-stored repository-relative path safely."""

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def load_json_record(path: Path, *, kind: str | None = None) -> dict[str, Any]:
    """Load one JSON record and optionally enforce its immutable kind."""

    path = path.expanduser().resolve()
    if not path.exists():
        raise RichDataError(f"JSON record does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RichDataError(f"JSON record is invalid: {path}") from exc
    if not isinstance(payload, dict):
        raise RichDataError(f"JSON record must contain an object: {path}")
    if kind is not None and payload.get("kind") != kind:
        raise RichDataError(f"expected {kind!r}, got {payload.get('kind')!r}: {path}")
    return payload


def load_jqdata_moneyflow_contract(
    path: Path = DEFAULT_JQDATA_MONEYFLOW_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-entitlement daily moneyflow contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != JQDATA_MONEYFLOW_CONTRACT_SHA256:
        raise RichDataError("JQData moneyflow contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_jqdata_moneyflow_data_contract")
    source = contract.get("source") or {}
    factor = contract.get("factor") or {}
    snapshot = contract.get("snapshot_contract") or {}
    partition = snapshot.get("partition_policy") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    coverage = contract.get("coverage_and_capacity_policy") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_jqdata_moneyflow_entitlement_or_rows_observed"
        or contract.get("preregistered_at") != "2026-07-14T20:20:32Z"
        or source.get("provider") != "jqdata"
        or source.get("api") != "get_money_flow_pro"
        or source.get("frequency") != "daily"
        or source.get("data_type") != "money"
        or tuple(source.get("requested_fields") or ()) != JQDATA_MONEYFLOW_RAW_FIELDS
        or tuple(snapshot.get("columns") or ()) != JQDATA_MONEYFLOW_COLUMNS
        or partition.get("partition") != "one calendar year"
        or partition.get("provider_documented_maximum_rows_per_call") != 2000000
        or factor.get("name") != "jqdata_large_order_net_inflow_share"
        or factor.get("direction") != "higher_is_better"
        or acceptance.get("symbols") != ["600519", "000001", "300750", "688981"]
        or coverage.get("minimum_required_cohorts") != 200
        or coverage.get("minimum_observed_years") != 5
        or coverage.get("holding_period_trading_days") != 3
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "JQData moneyflow contract does not match the frozen protocol"
        )
    return contract


def load_tushare_moneyflow_contract(
    path: Path = DEFAULT_TUSHARE_MONEYFLOW_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable post-acceptance, pre-history Tushare contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_MONEYFLOW_CONTRACT_SHA256:
        raise RichDataError("Tushare moneyflow contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_tushare_moneyflow_data_contract")
    source = contract.get("source") or {}
    factor = contract.get("factor") or {}
    snapshot = contract.get("snapshot_contract") or {}
    partition = snapshot.get("partition_policy") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    coverage = contract.get("coverage_and_capacity_policy") or {}
    mechanism = contract.get("mechanism_identity") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_after_entitlement_acceptance_before_full_history_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T08:38:42Z"
        or source.get("provider") != "tushare"
        or source.get("api") != "moneyflow"
        or source.get("frequency") != "daily"
        or tuple(source.get("requested_fields") or ()) != TUSHARE_MONEYFLOW_RAW_FIELDS
        or tuple(snapshot.get("columns") or ()) != TUSHARE_MONEYFLOW_COLUMNS
        or partition.get("partition") != "one calendar year"
        or partition.get("provider_call_partition") != "one local trading session"
        or partition.get("provider_documented_maximum_rows_per_call") != 6000
        or partition.get("minimum_seconds_between_calls") != 0.32
        or partition.get("maximum_attempts_per_session") != 3
        or factor.get("name") != "tushare_large_order_net_inflow_share"
        or factor.get("direction") != "higher_is_better"
        or acceptance.get("status") != "completed_schema_and_entitlement_probe"
        or acceptance.get("bound_manifest_sha256")
        != "83c141749256a01852cf2cb0534da653e947e264a1b5ba3eb0efa2fd4b87a849"
        or mechanism.get("independent_factor_count") != 1
        or mechanism.get("jqdata_and_tushare_may_be_combined_as_independent_factors")
        is not False
        or coverage.get("minimum_required_cohorts") != 200
        or coverage.get("minimum_observed_years") != 5
        or coverage.get("holding_period_trading_days") != 3
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare moneyflow contract does not match the frozen protocol"
        )
    return contract


def load_tushare_northbound_top10_contract(
    path: Path = DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-entitlement Northbound top-ten contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_NORTHBOUND_TOP10_CONTRACT_SHA256:
        raise RichDataError("Tushare Northbound top-ten contract fingerprint mismatch")
    contract = load_json_record(
        path, kind="a_share_tushare_northbound_top10_data_contract"
    )
    source = contract.get("source") or {}
    factor = contract.get("factor") or {}
    snapshot = contract.get("snapshot_contract") or {}
    partition = snapshot.get("partition_policy") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    completeness = contract.get("source_completeness_policy") or {}
    capacity = contract.get("coverage_and_capacity_policy") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_entitlement_rows_full_history_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T09:37:55Z"
        or source.get("provider") != "tushare"
        or source.get("api") != "hsgt_top10"
        or tuple(source.get("market_types") or ())
        != TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES
        or tuple(source.get("requested_fields") or ())
        != TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS
        or tuple(snapshot.get("columns") or ()) != TUSHARE_NORTHBOUND_TOP10_COLUMNS
        or partition.get("partition") != "one calendar year"
        or partition.get("provider_call_partition")
        != "one local trading session and one market_type"
        or partition.get("minimum_seconds_between_calls") != 0.32
        or partition.get("maximum_attempts_per_market_session") != 3
        or factor.get("name") != "tushare_northbound_top10_net_buy_share"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula") != "(buy - sell) / (buy + sell)"
        or acceptance.get("fixed_completed_session") != "2026-07-13"
        or tuple(acceptance.get("markets_requested") or ())
        != TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES
        or completeness.get("minimum_nonempty_source_sessions") != 1000
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare Northbound top-ten contract does not match the frozen protocol"
        )
    return contract


def load_tushare_top_inst_contract(
    path: Path = DEFAULT_TUSHARE_TOP_INST_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-entitlement institution-seat contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_TOP_INST_CONTRACT_SHA256:
        raise RichDataError("Tushare top_inst contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_tushare_top_inst_data_contract")
    source_selection = contract.get("source_selection") or {}
    source = contract.get("source") or {}
    timing = contract.get("point_in_time_policy") or {}
    factor = contract.get("factor") or {}
    context = contract.get("local_context") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    gates = contract.get("no_return_gates") or {}
    completeness = gates.get("source_completeness") or {}
    capacity = gates.get("capacity") or {}
    uniqueness = gates.get("uniqueness") or {}
    diagnostic = contract.get("diagnostic_policy_if_all_no_return_gates_pass") or {}
    top_list_manifest = context.get("accepted_top_list_manifest") or {}
    top_list_frame = context.get("accepted_top_list_frame") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_top_inst_entitlement_rows_full_history_factor_values_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T12:50:27Z"
        or source_selection.get("minimum_permission_points") != 2000
        or source_selection.get("provider_documented_maximum_rows_per_call") != 10000
        or source.get("provider") != "tushare"
        or source.get("api") != "top_inst"
        or source.get("frequency") != "daily_after_close_event"
        or source.get("request_mode") != "one completed local trading session per call"
        or tuple(source.get("requested_fields") or ()) != TUSHARE_TOP_INST_RAW_FIELDS
        or timing.get("same_session_trade_allowed") is not False
        or timing.get("maximum_event_age_days") != 0
        or timing.get("forward_fill_allowed") is not False
        or factor.get("name") != "tushare_top_inst_net_buy_share"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula") != "(sum(buy) - sum(sell)) / (sum(buy) + sum(sell))"
        or factor.get("provider_net_buy_use")
        != "integrity reconciliation only; never use provider net_buy as the factor numerator"
        or top_list_manifest.get("sha256")
        != "83c141749256a01852cf2cb0534da653e947e264a1b5ba3eb0efa2fd4b87a849"
        or top_list_frame.get("sha256")
        != "658592ebdcc44685e15184a2f01bc77f3c9ebdac7f0147b537564b7290ae24e6"
        or top_list_frame.get("raw_rows") != 91
        or top_list_frame.get("exact_duplicate_rows_preserved") != 2
        or acceptance.get("fixed_completed_session") != "2026-07-13"
        or acceptance.get("provider_calls") != 1
        or acceptance.get("minimum_raw_institution_rows") != 1
        or acceptance.get("minimum_aggregated_stock_rows") != 1
        or snapshot.get("development_start") != "2019-01-01"
        or snapshot.get("development_end") != "2025-12-31"
        or snapshot.get("request_every_local_session") is not True
        or snapshot.get("provider_call_partition") != "one local trading session"
        or snapshot.get("minimum_seconds_between_calls") != 0.32
        or snapshot.get("maximum_attempts_per_session") != 3
        or tuple(snapshot.get("canonical_columns") or ()) != TUSHARE_TOP_INST_COLUMNS
        or completeness.get("minimum_nonempty_source_sessions") != 200
        or completeness.get("minimum_observed_source_years") != 5
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("comparison_factor_count") != 51
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or diagnostic.get(
            "separate_immutable_preregistration_required_before_price_access"
        )
        is not True
        or diagnostic.get("holding_period_trading_days") != 3
        or diagnostic.get("topk") != 3
        or diagnostic.get("selection_or_promotion_allowed") is not False
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare top_inst contract does not match the frozen protocol"
        )
    return contract


def load_tushare_top_inst_top_list_context(
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Revalidate the accepted same-date raw top-list evidence without prices."""

    context = contract["local_context"]
    manifest_link = context["accepted_top_list_manifest"]
    frame_link = context["accepted_top_list_frame"]
    manifest_file = resolve_record_path(manifest_link["path"])
    frame_file = resolve_record_path(frame_link["path"])
    if (
        not manifest_file.exists()
        or file_digest(manifest_file) != manifest_link["sha256"]
    ):
        raise RichDataError("accepted Tushare top-list manifest fingerprint mismatch")
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    trade_date = contract["acceptance_protocol"]["fixed_completed_session"]
    if (
        manifest.get("dataset") != "tushare_events"
        or manifest.get("provider") != "tushare"
        or manifest.get("requested_start") != trade_date
        or manifest.get("requested_end") != trade_date
        or manifest.get("acceptance_status")
        != "pending_event_time_alignment_and_canonicalization"
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("accepted Tushare top-list manifest is incompatible")
    records = [
        item
        for item in manifest.get("files") or []
        if item.get("dataset") == "top-list"
    ]
    if len(records) != 1:
        raise RichDataError(
            "accepted Tushare event manifest must contain one top-list frame"
        )
    record = records[0]
    quality = record.get("quality") or {}
    if (
        resolve_record_path(record.get("path", "")) != frame_file
        or record.get("sha256") != frame_link["sha256"]
        or record.get("rows") != frame_link["raw_rows"]
        or quality.get("exact_duplicate_rows")
        != frame_link["exact_duplicate_rows_preserved"]
        or quality.get("missing_key_rows") != 0
        or quality.get("outside_requested_date_rows") != 0
        or quality.get("raw_rows_preserved_without_deduplication") is not True
    ):
        raise RichDataError("accepted Tushare top-list frame metadata mismatch")
    if not frame_file.exists():
        raise RichDataError("accepted Tushare top-list frame is missing")
    frame = pd.read_parquet(frame_file)
    if (
        frame_digest(frame) != frame_link["sha256"]
        or len(frame) != frame_link["raw_rows"]
    ):
        raise RichDataError(
            "accepted Tushare top-list frame content fingerprint mismatch"
        )
    required = {"trade_date", "ts_code"}
    if not required.issubset(frame.columns):
        raise RichDataError("accepted Tushare top-list frame lacks stock/date keys")
    dates = pd.to_datetime(
        frame["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    if dates.isna().any() or not dates.eq(trade_date).all():
        raise RichDataError("accepted Tushare top-list frame has an incompatible date")

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        parts = str(value).strip().split(".", 1)
        if len(parts) != 2:
            return None
        code, suffix = parts[0].strip(), parts[1].strip().upper()
        if len(code) != 6 or not code.isdigit() or suffix not in {"SH", "SZ"}:
            return None
        try:
            symbol = qlib_symbol(code)
        except RichDataError:
            return None
        return symbol if symbol.startswith(suffix) else None

    instruments = frame["ts_code"].map(instrument)
    supported = instruments.dropna().astype(str)
    if supported.empty:
        raise RichDataError(
            "accepted Tushare top-list frame has no supported A-share stock keys"
        )
    return {
        "manifest_path": manifest_file,
        "manifest_sha256": manifest_link["sha256"],
        "frame_path": frame_file,
        "frame_sha256": frame_link["sha256"],
        "frame_rows": int(len(frame)),
        "exact_duplicate_rows_preserved": int(quality["exact_duplicate_rows"]),
        "unsupported_security_rows_excluded": int(instruments.isna().sum()),
        "instruments": frozenset(supported),
    }


def tushare_top_inst_acceptance_records() -> list[Path]:
    """Return prior success or rejection records that consumed the one-shot gate."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_top_inst_acceptance*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_top_inst_acceptance":
            records.append(path)
    return records


def load_tushare_top10_float_concentration_contract(
    path: Path = DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-row top-ten float concentration contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT_SHA256:
        raise RichDataError(
            "Tushare top-ten float concentration contract fingerprint mismatch"
        )
    contract = load_json_record(
        path, kind="a_share_tushare_top10_float_concentration_data_contract"
    )
    source_selection = contract.get("source_selection") or {}
    source = contract.get("source") or {}
    timing = contract.get("point_in_time_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    gates = contract.get("no_return_gates") or {}
    completeness = gates.get("source_completeness") or {}
    capacity = gates.get("capacity") or {}
    uniqueness = gates.get("uniqueness") or {}
    diagnostic = contract.get("diagnostic_policy_if_all_no_return_gates_pass") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_top10_floatholders_entitlement_rows_full_history_factor_values_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T13:26:35Z"
        or source_selection.get("minimum_permission_points") != 2000
        or source_selection.get("current_account_points") != 3000
        or source.get("provider") != "tushare"
        or source.get("api") != "top10_floatholders"
        or source.get("request_mode")
        != "one stock and one frozen report-period range per call"
        or tuple(source.get("requested_fields") or ()) != TUSHARE_TOP10_FLOAT_RAW_FIELDS
        or source.get("plaintext_holder_name_may_be_logged_stored_or_committed")
        is not False
        or timing.get("conservative_availability")
        != "first local trading session strictly after ann_date"
        or timing.get("same_announcement_session_trade_allowed") is not False
        or timing.get("maximum_event_age_calendar_days") != 3
        or timing.get("forward_fill_beyond_event_age_allowed") is not False
        or factor.get("name") != "top10_float_concentration_change_pp"
        or factor.get("direction") != "higher_is_better"
        or factor.get("concentration_formula")
        != "sum(hold_float_ratio) across the exact ten-holder group"
        or factor.get("factor_formula")
        != "current first-complete top10_float_concentration_pct minus the immediately previous quarter's first-complete top10_float_concentration_pct"
        or tuple(acceptance.get("fixed_symbols") or ())
        != TUSHARE_TOP10_FLOAT_ACCEPTANCE_SYMBOLS
        or acceptance.get("fixed_report_period_start") != "20241231"
        or acceptance.get("fixed_report_period_end") != "20251231"
        or acceptance.get("latest_allowed_announcement_date") != "20260716"
        or acceptance.get("provider_calls") != 3
        or acceptance.get("minimum_complete_report_groups_per_symbol") != 2
        or acceptance.get("minimum_factor_ready_consecutive_pairs_per_symbol") != 1
        or acceptance.get("success_status")
        != "accepted_entitlement_schema_and_concentration_formula_pending_full_history"
        or snapshot.get("source_report_period_start") != "20181231"
        or snapshot.get("source_report_period_end") != "20251231"
        or snapshot.get("development_signal_start") != "2019-01-01"
        or snapshot.get("development_signal_end") != "2025-12-31"
        or snapshot.get("request_each_point_in_time_buyable_instrument_once")
        is not True
        or snapshot.get("provider_call_partition")
        != "one ts_code over the full frozen report-period range"
        or snapshot.get("minimum_seconds_between_calls") != 0.65
        or snapshot.get("maximum_attempts_per_symbol") != 3
        or tuple(snapshot.get("persisted_normalized_source_columns") or ())
        != TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS
        or tuple(snapshot.get("canonical_factor_columns") or ())
        != TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS
        or completeness.get("minimum_complete_factor_events") != 2000
        or completeness.get("minimum_observed_announcement_years") != 5
        or completeness.get("plaintext_holder_identity_persisted") is not False
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("comparison_factor_count") != 54
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or diagnostic.get(
            "separate_immutable_preregistration_required_before_price_access"
        )
        is not True
        or diagnostic.get("holding_period_trading_days") != 3
        or diagnostic.get("topk") != 3
        or diagnostic.get("selection_or_promotion_allowed") is not False
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare top-ten float concentration contract does not match the "
            "frozen protocol"
        )
    return contract


def validate_tushare_top10_float_local_context(
    contract: dict[str, Any],
) -> dict[str, dict[str, str]]:
    """Fingerprint-bind every local no-return prerequisite before a provider call."""

    context = contract.get("local_context") or {}
    validated: dict[str, dict[str, str]] = {}
    for label, evidence in context.items():
        if (
            not isinstance(evidence, dict)
            or not evidence.get("path")
            or not evidence.get("sha256")
        ):
            raise RichDataError(
                f"top-ten float concentration context is incomplete: {label}"
            )
        path = resolve_record_path(str(evidence["path"]))
        expected = str(evidence["sha256"])
        if not path.exists() or file_digest(path) != expected:
            raise RichDataError(
                f"top-ten float concentration context fingerprint mismatch: {label}"
            )
        validated[label] = {
            "path": manifest_path(path),
            "sha256": expected,
        }
        manifest_value = evidence.get("manifest_path")
        manifest_sha = evidence.get("manifest_sha256")
        if manifest_value is not None or manifest_sha is not None:
            if not manifest_value or not manifest_sha:
                raise RichDataError(
                    f"top-ten float concentration manifest context is incomplete: {label}"
                )
            manifest_file = resolve_record_path(str(manifest_value))
            if not manifest_file.exists() or file_digest(manifest_file) != str(
                manifest_sha
            ):
                raise RichDataError(
                    "top-ten float concentration manifest fingerprint mismatch: "
                    f"{label}"
                )
            validated[f"{label}_manifest"] = {
                "path": manifest_path(manifest_file),
                "sha256": str(manifest_sha),
            }
    return validated


def tushare_top10_float_concentration_acceptance_records() -> list[Path]:
    """Return terminal records that have consumed this exact one-shot gate."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(
        RUNS_ROOT.glob("*tushare_top10_float_concentration_acceptance*.json")
    ):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_top10_float_concentration_acceptance":
            records.append(path)
    return records


def load_tushare_earnings_forecast_contract(
    path: Path = DEFAULT_TUSHARE_EARNINGS_FORECAST_CONTRACT,
) -> dict[str, Any]:
    """Load and structurally validate the immutable pre-row forecast contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_EARNINGS_FORECAST_CONTRACT_SHA256:
        raise RichDataError("Tushare earnings-forecast contract fingerprint mismatch")
    contract = load_json_record(
        path, kind="a_share_tushare_earnings_forecast_data_contract"
    )
    selection = contract.get("source_selection") or {}
    source = contract.get("source") or {}
    timing = contract.get("point_in_time_and_version_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    gates = contract.get("no_return_gates") or {}
    completeness = gates.get("source_completeness") or {}
    capacity = gates.get("capacity") or {}
    uniqueness = gates.get("uniqueness") or {}
    diagnostic = contract.get("diagnostic_policy_if_all_no_return_gates_pass") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_forecast_entitlement_rows_full_history_factor_values_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T17:26:26Z"
        or selection.get("minimum_permission_points") != 2000
        or selection.get("current_account_points") != 3000
        or source.get("provider") != "tushare"
        or source.get("api") != "forecast"
        or source.get("request_mode")
        != "one stock and one frozen announcement-date range per call"
        or tuple(source.get("requested_fields") or ())
        != TUSHARE_EARNINGS_FORECAST_RAW_FIELDS
        or tuple(timing.get("comparable_forecast_types") or ())
        != ("预增", "略增", "续盈", "预减", "略减")
        or tuple(timing.get("non_comparable_types_excluded_and_counted") or ())
        != ("扭亏", "首亏", "续亏")
        or timing.get("conservative_availability")
        != "first local trading session strictly after ann_date"
        or timing.get("same_announcement_session_trade_allowed") is not False
        or timing.get("maximum_event_age_calendar_days") != 3
        or timing.get("forward_fill_beyond_event_age_allowed") is not False
        or factor.get("name") != "tushare_earnings_forecast_growth_midpoint"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula") != "(p_change_min + p_change_max) / 2"
        or tuple(factor.get("applicable_types") or ())
        != ("预增", "略增", "续盈", "预减", "略减")
        or tuple(acceptance.get("fixed_symbols") or ())
        != ("002466.SZ", "002594.SZ", "300750.SZ")
        or acceptance.get("fixed_announcement_start") != "20190101"
        or acceptance.get("fixed_announcement_end") != "20251231"
        or acceptance.get("provider_calls") != 3
        or acceptance.get("minimum_total_source_rows") != 6
        or acceptance.get("minimum_symbols_with_one_comparable_event") != 2
        or acceptance.get("success_status")
        != "accepted_entitlement_schema_type_policy_and_formula_pending_full_history"
        or snapshot.get("announcement_start") != "20190101"
        or snapshot.get("announcement_end") != "20251231"
        or snapshot.get("request_each_point_in_time_buyable_instrument_once")
        is not True
        or snapshot.get("local_truncation_suspicion_row_ceiling_per_stock") != 100
        or snapshot.get("minimum_seconds_between_calls") != 0.32
        or snapshot.get("maximum_attempts_per_stock") != 3
        or tuple(snapshot.get("canonical_columns") or ())
        != TUSHARE_EARNINGS_FORECAST_COLUMNS
        or completeness.get("minimum_comparable_forecast_events") != 3000
        or completeness.get("minimum_observed_signal_years") != 5
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("minimum_pairwise_event_sessions") != 20
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or diagnostic.get(
            "separate_immutable_preregistration_required_before_price_access"
        )
        is not True
        or diagnostic.get("holding_period_trading_days") != 3
        or diagnostic.get("topk") != 3
        or diagnostic.get("selection_or_promotion_allowed") is not False
        or contract.get("price_fields_loaded") != []
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare earnings-forecast contract does not match the frozen protocol"
        )
    for label, evidence in (contract.get("local_context") or {}).items():
        linked_path = resolve_record_path(str(evidence.get("path") or ""))
        linked_sha = str(evidence.get("sha256") or "")
        if not linked_path.exists() or file_digest(linked_path) != linked_sha:
            raise RichDataError(
                f"Tushare earnings-forecast local context changed: {label}"
            )
        manifest_value = evidence.get("manifest_path")
        manifest_sha = evidence.get("manifest_sha256")
        if manifest_value is not None or manifest_sha is not None:
            manifest_file = resolve_record_path(str(manifest_value or ""))
            if (
                not manifest_value
                or not manifest_sha
                or not manifest_file.exists()
                or file_digest(manifest_file) != str(manifest_sha)
            ):
                raise RichDataError(
                    f"Tushare earnings-forecast manifest context changed: {label}"
                )
    return contract


def tushare_earnings_forecast_acceptance_records() -> list[Path]:
    """Return terminal records that consumed the frozen forecast acceptance."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_earnings_forecast_acceptance*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_earnings_forecast_acceptance":
            records.append(path)
    return records


def load_tushare_earnings_forecast_acceptance_record(
    path: Path = DEFAULT_TUSHARE_EARNINGS_FORECAST_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Validate the terminal one-call forecast record and prior-branch overlap."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_EARNINGS_FORECAST_ACCEPTANCE_RECORD_SHA256:
        raise RichDataError(
            "Tushare earnings-forecast acceptance-record fingerprint mismatch"
        )
    record = load_json_record(
        path, kind="a_share_tushare_earnings_forecast_source_acceptance_record"
    )
    failure = record.get("acceptance_failure") or {}
    implementation = record.get("implementation_audit") or {}
    overlap = record.get("prior_mechanism_overlap") or {}
    rebuild = overlap.get("accepted_price_rebuild") or {}
    decision = record.get("decision") or {}
    if (
        record.get("status")
        != "terminal_rejected_after_one_call_before_factor_values_with_prior_mechanism_overlap"
        or (record.get("data_contract") or {}).get("sha256")
        != TUSHARE_EARNINGS_FORECAST_CONTRACT_SHA256
        or failure.get("sha256")
        != "56125255b582c05c4e3889b75aefa4e29f77bb0b372fbc2c1456df5ff3883fe7"
        or failure.get("failed_symbol") != "002466.SZ"
        or failure.get("provider_calls_issued") != 1
        or failure.get("factor_frame_published") is not False
        or failure.get("partial_snapshot_deleted") is not True
        or failure.get("final_snapshot_published") is not False
        or implementation.get("failure_was_uncontracted_implementation_check")
        is not True
        or implementation.get("factor_value_constructed_before_failure") is not False
        or implementation.get("retry_authorized") is not False
        or overlap.get("new_contract_incorrectly_described_as_independent") is not True
        or rebuild.get("qualified_factor_count") != 0
        or decision.get("acceptance_retry_allowed") is not False
        or decision.get(
            "run_full_history_capacity_uniqueness_or_return_diagnostic_allowed"
        )
        is not False
        or record.get("price_fields_loaded") != []
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare earnings-forecast acceptance record changed")
    linked_records = [
        record.get("data_contract") or {},
        failure,
        overlap.get("existing_rebuild_preregistration") or {},
        overlap.get("existing_performance_forecast_snapshot") or {},
    ]
    for link in linked_records:
        linked_path = resolve_record_path(str(link.get("path") or ""))
        linked_sha = str(link.get("sha256") or "")
        if linked_path.exists() and file_digest(linked_path) != linked_sha:
            raise RichDataError(
                f"Tushare earnings-forecast terminal evidence changed: {linked_path}"
            )
        manifest_value = link.get("manifest_path")
        manifest_sha = link.get("manifest_sha256")
        if manifest_value and manifest_sha:
            manifest_file = resolve_record_path(str(manifest_value))
            if manifest_file.exists() and file_digest(manifest_file) != str(
                manifest_sha
            ):
                raise RichDataError(
                    "Tushare earnings-forecast terminal manifest evidence changed: "
                    f"{manifest_file}"
                )
    return record


def load_tushare_disclosure_promptness_contract(
    path: Path = DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT,
) -> dict[str, Any]:
    """Load and revalidate the immutable pre-row disclosure-plan contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT_SHA256:
        raise RichDataError(
            "Tushare disclosure-promptness contract fingerprint mismatch"
        )
    contract = load_json_record(
        path, kind="a_share_tushare_disclosure_promptness_data_contract"
    )
    selection = contract.get("source_selection") or {}
    mechanism = contract.get("mechanism_identity") or {}
    overlap = mechanism.get("mechanism_overlap_audit") or {}
    source = contract.get("source") or {}
    timing = contract.get("point_in_time_and_version_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    completeness = contract.get("source_completeness_policy") or {}
    capacity = contract.get("no_return_capacity_policy") or {}
    uniqueness = contract.get("no_return_uniqueness_policy") or {}
    diagnostic = (
        contract.get("diagnostic_policy_if_source_capacity_and_uniqueness_pass") or {}
    )
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_after_mechanism_overlap_audit_before_entitlement_rows_factor_values_or_returns"
        or contract.get("preregistered_at") != "2026-07-16T17:48:19Z"
        or selection.get("minimum_permission_points") != 2000
        or selection.get("current_account_points") != 3000
        or selection.get("provider_documented_maximum_rows_per_call") != 6000
        or overlap.get("path")
        != "docs/a_share_three_day_mechanism_overlap_reaudit_20260717.json"
        or overlap.get("sha256")
        != "f21194cf93b5ac126d6cb39d93cab529d77a2e28ab153b90e0cc2326c860370e"
        or source.get("provider") != "tushare"
        or source.get("api") != "disclosure_date"
        or source.get("request_mode") != "one frozen report period per call"
        or tuple(source.get("requested_fields") or ())
        != TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS
        or timing.get("conservative_availability")
        != "first local trading session strictly after ann_date"
        or timing.get("same_announcement_session_trade_allowed") is not False
        or timing.get("maximum_event_age_calendar_days") != 3
        or timing.get("forward_fill_beyond_event_age_allowed") is not False
        or factor.get("name") != "tushare_disclosure_plan_promptness"
        or factor.get("raw_column") != "tushare_disclosure_plan_lead_days"
        or factor.get("direction") != "lower_is_better"
        or factor.get("formula") != "calendar_days(pre_date - ann_date)"
        or tuple(acceptance.get("fixed_report_periods") or ())
        != TUSHARE_DISCLOSURE_PROMPTNESS_ACCEPTANCE_PERIODS
        or acceptance.get("provider_calls") != 3
        or acceptance.get("minimum_source_rows_per_period") != 2000
        or acceptance.get("minimum_retained_rows_per_period") != 1000
        or acceptance.get("minimum_distinct_lead_days_per_period") != 10
        or acceptance.get("provider_row_ceiling_is_strict") is not True
        or acceptance.get("success_status")
        != "accepted_entitlement_schema_point_in_time_policy_and_formula_pending_full_history"
        or tuple(snapshot.get("fixed_report_periods") or ())
        != TUSHARE_DISCLOSURE_PROMPTNESS_FULL_PERIODS
        or snapshot.get("provider_calls") != 28
        or snapshot.get("provider_documented_maximum_rows_per_call") != 6000
        or tuple(snapshot.get("output_columns") or ())
        != TUSHARE_DISCLOSURE_PROMPTNESS_COLUMNS
        or snapshot.get("raw_provider_frames_persisted") is not False
        or snapshot.get("actual_date_requested_or_persisted") is not False
        or completeness.get("minimum_median_valid_plan_coverage") != 0.9
        or completeness.get("minimum_p05_valid_plan_coverage") != 0.85
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_local_sessions") != 3
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or diagnostic.get(
            "separate_immutable_preregistration_required_before_price_access"
        )
        is not True
        or diagnostic.get("holding_period_local_sessions") != 3
        or diagnostic.get("topk") != 3
        or contract.get("price_fields_loaded") != []
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare disclosure-promptness contract does not match the frozen protocol"
        )
    overlap_path = resolve_record_path(str(overlap["path"]))
    if not overlap_path.exists() or file_digest(overlap_path) != str(overlap["sha256"]):
        raise RichDataError(
            "Tushare disclosure-promptness mechanism-overlap evidence changed"
        )
    for label, evidence in (contract.get("local_context") or {}).items():
        linked_path = resolve_record_path(str(evidence.get("path") or ""))
        linked_sha = str(evidence.get("sha256") or "")
        if not linked_path.exists() or file_digest(linked_path) != linked_sha:
            raise RichDataError(
                f"Tushare disclosure-promptness local context changed: {label}"
            )
        manifest_value = evidence.get("manifest_path")
        manifest_sha = evidence.get("manifest_sha256")
        if manifest_value is not None or manifest_sha is not None:
            manifest_file = resolve_record_path(str(manifest_value or ""))
            if (
                not manifest_value
                or not manifest_sha
                or not manifest_file.exists()
                or file_digest(manifest_file) != str(manifest_sha)
            ):
                raise RichDataError(
                    f"Tushare disclosure-promptness manifest context changed: {label}"
                )
    return contract


def tushare_disclosure_promptness_acceptance_records() -> list[Path]:
    """Return records that consumed the frozen disclosure-plan acceptance."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(
        RUNS_ROOT.glob("*tushare_disclosure_promptness_acceptance*.json")
    ):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_disclosure_promptness_acceptance":
            records.append(path)
    return records


def load_tushare_audit_opinion_contract(
    path: Path = DEFAULT_TUSHARE_AUDIT_OPINION_CONTRACT,
) -> dict[str, Any]:
    """Load and revalidate the immutable pre-row audit-opinion contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_AUDIT_OPINION_CONTRACT_SHA256:
        raise RichDataError("Tushare audit-opinion contract fingerprint mismatch")
    contract = load_json_record(
        path, kind="a_share_tushare_audit_opinion_data_contract"
    )
    selection = contract.get("source_selection") or {}
    mechanism = contract.get("mechanism_identity") or {}
    overlap = mechanism.get("mechanism_overlap_audit") or {}
    source = contract.get("source") or {}
    timing = contract.get("point_in_time_and_version_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    capacity = contract.get("no_return_capacity_policy") or {}
    uniqueness = contract.get("no_return_uniqueness_policy") or {}
    diagnostic = (
        contract.get("diagnostic_policy_if_source_capacity_and_uniqueness_pass") or {}
    )
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_after_mechanism_overlap_audit_before_entitlement_rows_factor_values_or_returns"
        or contract.get("preregistered_at") != "2026-07-16T18:13:26Z"
        or selection.get("minimum_permission_points") != 2000
        or selection.get("current_account_points") != 3000
        or selection.get("defensive_maximum_rows_per_single_stock_call") != 1000
        or overlap.get("path")
        != "docs/a_share_three_day_audit_opinion_mechanism_overlap_reaudit_20260717.json"
        or overlap.get("sha256")
        != "a13470c5dafa4c278035e7b17e56f896ae03932b4131b6d90830a2168282acdb"
        or source.get("provider") != "tushare"
        or source.get("api") != "fina_audit"
        or source.get("request_mode")
        != "one frozen stock and announcement-date range per call"
        or tuple(source.get("requested_fields") or ())
        != TUSHARE_AUDIT_OPINION_RAW_FIELDS
        or timing.get("audit_result_normalization")
        != "Apply Unicode NFKC, strip surrounding whitespace, and remove no internal wording or punctuation."
        or timing.get("conservative_availability")
        != "first local trading session strictly after ann_date"
        or timing.get("same_announcement_session_trade_allowed") is not False
        or timing.get("maximum_event_age_calendar_days") != 3
        or timing.get("forward_fill_beyond_event_age_allowed") is not False
        or factor.get("name") != "tushare_standard_unqualified_audit_opinion"
        or factor.get("raw_column") != "tushare_is_standard_unqualified_audit_opinion"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula")
        != "1 if NFKC_trim(audit_result) == '标准无保留意见' else 0 for any other complete nonempty opinion"
        or factor.get("text_synonym_mapping_allowed") is not False
        or tuple(acceptance.get("fixed_ts_codes") or ())
        != TUSHARE_AUDIT_OPINION_ACCEPTANCE_TS_CODES
        or acceptance.get("announcement_start")
        != TUSHARE_AUDIT_OPINION_ACCEPTANCE_START
        or acceptance.get("announcement_end") != TUSHARE_AUDIT_OPINION_ACCEPTANCE_END
        or acceptance.get("provider_calls") != 3
        or acceptance.get("minimum_source_rows_per_stock") != 5
        or acceptance.get("minimum_retained_rows_per_stock") != 5
        or acceptance.get(
            "minimum_distinct_hashed_opinion_categories_across_acceptance"
        )
        != 2
        or acceptance.get("minimum_distinct_factor_values_across_acceptance") != 2
        or acceptance.get("defensive_row_ceiling_is_strict") is not True
        or acceptance.get("success_status")
        != "accepted_entitlement_schema_point_in_time_policy_and_binary_formula_pending_full_history"
        or snapshot.get("provider_calls") != 5451
        or tuple(snapshot.get("output_columns") or ()) != TUSHARE_AUDIT_OPINION_COLUMNS
        or snapshot.get("raw_provider_frames_persisted") is not False
        or snapshot.get("raw_or_normalized_audit_result_text_persisted") is not False
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_local_sessions") != 3
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or diagnostic.get(
            "separate_immutable_preregistration_required_before_price_access"
        )
        is not True
        or diagnostic.get("holding_period_local_sessions") != 3
        or diagnostic.get("topk") != 3
        or contract.get("price_fields_loaded") != []
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare audit-opinion contract does not match the frozen protocol"
        )
    overlap_path = resolve_record_path(str(overlap["path"]))
    if not overlap_path.exists() or file_digest(overlap_path) != str(overlap["sha256"]):
        raise RichDataError("Tushare audit-opinion mechanism-overlap evidence changed")
    for label, evidence in (contract.get("local_context") or {}).items():
        linked_path = resolve_record_path(str(evidence.get("path") or ""))
        linked_sha = str(evidence.get("sha256") or "")
        if not linked_path.exists() or file_digest(linked_path) != linked_sha:
            raise RichDataError(f"Tushare audit-opinion local context changed: {label}")
        manifest_value = evidence.get("manifest_path")
        manifest_sha = evidence.get("manifest_sha256")
        if manifest_value is not None or manifest_sha is not None:
            manifest_file = resolve_record_path(str(manifest_value or ""))
            if (
                not manifest_value
                or not manifest_sha
                or not manifest_file.exists()
                or file_digest(manifest_file) != str(manifest_sha)
            ):
                raise RichDataError(
                    f"Tushare audit-opinion manifest context changed: {label}"
                )
    return contract


def tushare_audit_opinion_acceptance_records() -> list[Path]:
    """Return records that consumed the frozen audit-opinion acceptance."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_audit_opinion_acceptance*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_audit_opinion_acceptance":
            records.append(path)
    return records


def load_tushare_gross_margin_contract(
    path: Path = DEFAULT_TUSHARE_GROSS_MARGIN_CONTRACT,
) -> dict[str, Any]:
    """Load and revalidate the immutable pre-row gross-margin contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_GROSS_MARGIN_CONTRACT_SHA256:
        raise RichDataError("Tushare gross-margin contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_tushare_gross_margin_data_contract")
    selection = contract.get("source_selection") or {}
    mechanism = contract.get("mechanism_identity") or {}
    overlap = mechanism.get("mechanism_overlap_audit") or {}
    source = contract.get("source") or {}
    timing = contract.get("point_in_time_and_version_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    completeness = contract.get("source_completeness_policy") or {}
    capacity = contract.get("no_return_capacity_policy") or {}
    uniqueness = contract.get("no_return_uniqueness_policy") or {}
    return_policy = contract.get("return_research_policy") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_after_mechanism_overlap_audit_before_entitlement_rows_factor_values_or_returns"
        or contract.get("preregistered_at") != "2026-07-16T19:34:37Z"
        or selection.get("minimum_permission_points") != 2000
        or selection.get("current_account_points") != 3000
        or selection.get("provider_documented_maximum_rows_per_call") != 100
        or selection.get("vip_variant_requested") is not False
        or overlap.get("path")
        != "docs/a_share_three_day_gross_margin_mechanism_overlap_reaudit_20260717.json"
        or overlap.get("sha256")
        != "df2e40d788c91e66de278437379180a7082d7940da8ce46a37ba2b8791164427"
        or source.get("provider") != "tushare"
        or source.get("api") != "fina_indicator"
        or source.get("request_mode")
        != "one frozen stock and report-period range per call"
        or tuple(source.get("requested_fields") or ())
        != TUSHARE_GROSS_MARGIN_RAW_FIELDS
        or timing.get("factor_version") != "initial_only"
        or timing.get("conservative_availability")
        != "first local trading session strictly after the current initial ann_date"
        or timing.get("same_announcement_session_trade_allowed") is not False
        or timing.get("maximum_event_age_calendar_days") != 3
        or timing.get("forward_fill_beyond_event_age_allowed") is not False
        or factor.get("name") != "tushare_single_quarter_gross_margin_yoy_change"
        or factor.get("raw_column") != "tushare_q_gross_margin_yoy_change_pp"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula")
        != "current_initial_q_gsprofit_margin - same_fiscal_quarter_previous_year_initial_q_gsprofit_margin"
        or tuple(acceptance.get("fixed_ts_codes") or ())
        != TUSHARE_GROSS_MARGIN_ACCEPTANCE_TS_CODES
        or acceptance.get("report_period_start")
        != TUSHARE_GROSS_MARGIN_ACCEPTANCE_START
        or acceptance.get("report_period_end") != TUSHARE_GROSS_MARGIN_ACCEPTANCE_END
        or acceptance.get("provider_calls") != 3
        or acceptance.get("minimum_source_rows_per_stock") != 20
        or acceptance.get("minimum_initial_quarter_rows_per_stock") != 18
        or acceptance.get("minimum_derived_yoy_events_per_stock") != 12
        or acceptance.get("minimum_distinct_derived_values_across_acceptance") != 6
        or acceptance.get("documented_row_ceiling_is_strict") is not True
        or acceptance.get("success_status")
        != "accepted_entitlement_schema_initial_version_policy_and_formula_pending_full_history"
        or snapshot.get("provider_calls") != 10902
        or snapshot.get("source_report_period_start") != "2018-01-01"
        or snapshot.get("source_report_period_end") != "2025-12-31"
        or snapshot.get("provider_call_partition")
        != "two frozen report-period slices per source-universe stock: 20180101-20211231 and 20220101-20251231"
        or tuple(snapshot.get("output_columns") or ()) != TUSHARE_GROSS_MARGIN_COLUMNS
        or snapshot.get("raw_provider_frames_persisted") is not False
        or snapshot.get("revised_values_persisted") is not False
        or completeness.get("minimum_complete_derived_factor_events") != 20000
        or completeness.get("minimum_median_report_period_coverage") != 0.75
        or completeness.get("minimum_p05_report_period_coverage") != 0.65
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_local_sessions") != 3
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("minimum_comparison_sessions_per_field") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or return_policy.get("separate_immutable_return_preregistration_required")
        is not True
        or return_policy.get(
            "allowed_only_after_source_acceptance_full_source_capacity_and_uniqueness_gates_pass"
        )
        is not True
        or contract.get("price_fields_loaded") != []
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare gross-margin contract does not match the frozen protocol"
        )
    overlap_path = resolve_record_path(str(overlap["path"]))
    if not overlap_path.exists() or file_digest(overlap_path) != str(overlap["sha256"]):
        raise RichDataError("Tushare gross-margin mechanism-overlap evidence changed")
    for label, evidence in (contract.get("local_context") or {}).items():
        linked_path = resolve_record_path(str(evidence.get("path") or ""))
        linked_sha = str(evidence.get("sha256") or "")
        if not linked_path.exists() or file_digest(linked_path) != linked_sha:
            raise RichDataError(f"Tushare gross-margin local context changed: {label}")
        manifest_value = evidence.get("manifest_path")
        manifest_sha = evidence.get("manifest_sha256")
        if manifest_value is not None or manifest_sha is not None:
            manifest_file = resolve_record_path(str(manifest_value or ""))
            if (
                not manifest_value
                or not manifest_sha
                or not manifest_file.exists()
                or file_digest(manifest_file) != str(manifest_sha)
            ):
                raise RichDataError(
                    f"Tushare gross-margin manifest context changed: {label}"
                )
    return contract


def load_tushare_management_continuity_contract(
    path: Path = DEFAULT_TUSHARE_MANAGEMENT_CONTINUITY_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-row management-continuity contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_MANAGEMENT_CONTINUITY_CONTRACT_SHA256:
        raise RichDataError(
            "Tushare management-continuity contract fingerprint mismatch"
        )
    contract = load_json_record(
        path, kind="a_share_tushare_management_continuity_data_contract"
    )
    selection = contract.get("source_selection") or {}
    mechanism = contract.get("mechanism_identity") or {}
    overlap = mechanism.get("mechanism_overlap_audit") or {}
    source = contract.get("source") or {}
    identity = contract.get("identity_privacy_and_date_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    completeness = contract.get("source_completeness_policy") or {}
    capacity = contract.get("no_return_capacity_policy") or {}
    uniqueness = contract.get("no_return_uniqueness_policy") or {}
    return_policy = contract.get("return_research_policy") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_after_mechanism_overlap_audit_before_entitlement_rows_factor_values_or_returns"
        or contract.get("preregistered_at") != "2026-07-16T20:11:36Z"
        or selection.get("minimum_permission_points") != 2000
        or selection.get("current_account_points") != 3000
        or selection.get("provider_documented_maximum_rows_per_call") is not None
        or selection.get("defensive_response_row_ceiling") != 6000
        or overlap.get("path")
        != "docs/a_share_three_day_management_continuity_mechanism_overlap_reaudit_20260717.json"
        or overlap.get("sha256")
        != "e6b64475b17839cac9e2c8f2177c60509d1d58950127eddb625b9bf128d11946"
        or source.get("provider") != "tushare"
        or source.get("api") != "stk_managers"
        or source.get("request_mode")
        != "one frozen stock and announcement-date range per call"
        or tuple(source.get("requested_fields") or ())
        != TUSHARE_MANAGEMENT_CONTINUITY_RAW_FIELDS
        or identity.get("plaintext_name_persisted") is not False
        or identity.get("hashed_identity_persisted") is not False
        or identity.get("hash_or_plaintext_identity_logged") is not False
        or identity.get("end_date_departure_policy")
        != "A complete end_date exactly equal to ann_date means that identity is departing in this announcement."
        or identity.get("conservative_availability")
        != "first local trading session strictly after ann_date"
        or identity.get("same_announcement_session_trade_allowed") is not False
        or identity.get("maximum_event_age_calendar_days") != 3
        or identity.get("forward_fill_beyond_event_age_allowed") is not False
        or factor.get("name") != "tushare_management_continuity"
        or factor.get("raw_column") != "tushare_management_continuity_share"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula") != "1 - departing_manager_count / manager_count"
        or tuple(acceptance.get("fixed_ts_codes") or ())
        != TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_TS_CODES
        or acceptance.get("announcement_start")
        != TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_START
        or acceptance.get("announcement_end")
        != TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_END
        or acceptance.get("provider_calls") != 3
        or acceptance.get("minimum_source_rows_per_stock") != 5
        or acceptance.get("minimum_events_per_stock") != 3
        or acceptance.get("minimum_events_across_acceptance") != 15
        or acceptance.get("minimum_distinct_factor_values_across_acceptance") != 2
        or acceptance.get("must_observe_at_least_one_departing_identity") is not True
        or acceptance.get("must_observe_at_least_one_nondeparting_identity") is not True
        or acceptance.get("defensive_response_row_ceiling_is_strict") is not True
        or acceptance.get("success_status")
        != "accepted_entitlement_schema_identity_privacy_date_policy_and_formula_pending_full_history"
        or snapshot.get("provider_calls") != 5451
        or snapshot.get("source_universe_instrument_count") != 5451
        or snapshot.get("provider_call_partition")
        != "one complete 20190101-20251231 announcement range per source-universe stock"
        or tuple(snapshot.get("output_columns") or ())
        != TUSHARE_MANAGEMENT_CONTINUITY_COLUMNS
        or snapshot.get("raw_provider_frames_persisted") is not False
        or snapshot.get("plaintext_names_or_hashes_persisted") is not False
        or completeness.get("provider_call_coverage_required") != 1.0
        or completeness.get("minimum_complete_factor_events") != 10000
        or completeness.get("minimum_instruments_with_any_event") != 1500
        or completeness.get("minimum_distinct_factor_values") != 5
        or completeness.get("minimum_observed_signal_years") != 7
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_local_sessions") != 3
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("minimum_comparison_sessions_per_field") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or return_policy.get("separate_immutable_return_preregistration_required")
        is not True
        or return_policy.get(
            "allowed_only_after_source_acceptance_full_source_capacity_and_uniqueness_gates_pass"
        )
        is not True
        or contract.get("price_fields_loaded") != []
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare management-continuity contract does not match the frozen protocol"
        )
    overlap_path = resolve_record_path(str(overlap["path"]))
    if not overlap_path.exists() or file_digest(overlap_path) != str(overlap["sha256"]):
        raise RichDataError(
            "Tushare management-continuity mechanism-overlap evidence changed"
        )
    for label, evidence in (contract.get("local_context") or {}).items():
        linked_path = resolve_record_path(str(evidence.get("path") or ""))
        linked_sha = str(evidence.get("sha256") or "")
        if not linked_path.exists() or file_digest(linked_path) != linked_sha:
            raise RichDataError(
                f"Tushare management-continuity local context changed: {label}"
            )
        manifest_value = evidence.get("manifest_path")
        manifest_sha = evidence.get("manifest_sha256")
        if manifest_value is not None or manifest_sha is not None:
            manifest_file = resolve_record_path(str(manifest_value or ""))
            if (
                not manifest_value
                or not manifest_sha
                or not manifest_file.exists()
                or file_digest(manifest_file) != str(manifest_sha)
            ):
                raise RichDataError(
                    f"Tushare management-continuity manifest context changed: {label}"
                )
    return contract


def load_tushare_management_continuity_acceptance_record(
    path: Path = DEFAULT_TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Validate the terminal one-shot management source rejection."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_RECORD_SHA256:
        raise RichDataError(
            "Tushare management-continuity acceptance-record fingerprint mismatch"
        )
    record = load_json_record(
        path, kind="a_share_tushare_management_continuity_source_acceptance_record"
    )
    contract = record.get("data_contract") or {}
    acceptance = record.get("acceptance") or {}
    privacy = record.get("privacy_and_scope") or {}
    decision = record.get("terminal_decision") or {}
    if (
        record.get("status")
        != "terminal_source_rejected_before_identity_aggregation_factor_values_full_history_or_returns"
        or contract.get("sha256") != TUSHARE_MANAGEMENT_CONTINUITY_CONTRACT_SHA256
        or acceptance.get("manifest_sha256")
        != "1de603f276d14e77fafc993ed552f709d9c2d35456607c336875e3a70a06d45b"
        or acceptance.get("acceptance_status")
        != "rejected_stop_before_full_history_capacity_uniqueness_or_returns"
        or acceptance.get("provider_calls_planned") != 3
        or acceptance.get("provider_calls_issued") != 1
        or acceptance.get("first_and_only_requested_stock") != "000001.SZ"
        or acceptance.get("source_rows_observed") != 184
        or acceptance.get("departure_dates_unequal_to_announcement_date") != 53
        or acceptance.get("failure_code")
        != "source_departure_date_point_in_time_incompatibility"
        or acceptance.get("field_level_values_persisted") is not False
        or acceptance.get("factor_frame_published") is not False
        or acceptance.get("published_file_count") != 0
        or acceptance.get("partial_snapshot_deleted") is not True
        or acceptance.get("final_snapshot_published") is not False
        or privacy.get("raw_provider_frame_persisted") is not False
        or privacy.get("plaintext_manager_name_persisted_or_logged") is not False
        or privacy.get("manager_identity_hash_persisted_or_logged") is not False
        or privacy.get("identity_aggregation_completed") is not False
        or privacy.get("factor_value_observed_or_persisted") is not False
        or privacy.get("price_fields_loaded") != []
        or privacy.get("forward_return_fields_read") is not False
        or decision.get("acceptance_consumed") is not True
        or decision.get("acceptance_retry_allowed") is not False
        or decision.get("remaining_acceptance_stocks_may_be_requested") is not False
        or decision.get("full_source_sync_allowed") is not False
        or decision.get("capacity_uniqueness_or_return_work_allowed") is not False
    ):
        raise RichDataError("Tushare management-continuity acceptance record changed")
    for link in (
        record.get("mechanism_overlap_audit") or {},
        contract,
        {
            "path": acceptance.get("manifest_path"),
            "sha256": acceptance.get("manifest_sha256"),
        },
    ):
        linked_path = resolve_record_path(str(link.get("path") or ""))
        linked_sha = str(link.get("sha256") or "")
        if not linked_path.exists() or file_digest(linked_path) != linked_sha:
            raise RichDataError(
                "Tushare management-continuity terminal evidence changed: "
                f"{linked_path}"
            )
    return record


def tushare_management_continuity_acceptance_records() -> list[Path]:
    """Return records that consumed the management-continuity acceptance."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(
        RUNS_ROOT.glob("*tushare_management_continuity_acceptance*.json")
    ):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_management_continuity_acceptance":
            records.append(path)
    return records


def load_tushare_st_recovery_contract(
    path: Path = DEFAULT_TUSHARE_ST_RECOVERY_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable post-entitlement, pre-history ST recovery contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_ST_RECOVERY_CONTRACT_SHA256:
        raise RichDataError("Tushare ST-recovery contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_tushare_st_recovery_data_contract")
    mechanism = contract.get("mechanism_identity") or {}
    overlap = mechanism.get("mechanism_overlap_audit") or {}
    selection = contract.get("source_selection") or {}
    source = contract.get("source") or {}
    accepted = contract.get("already_accepted_source_evidence") or {}
    accepted_frame = accepted.get("stock_st_frame") or {}
    canonical = contract.get("canonical_membership_policy") or {}
    transition = contract.get("transition_and_factor_policy") or {}
    offline = contract.get("offline_source_acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    downstream = contract.get("downstream_no_return_gate") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_after_single_session_entitlement_schema_evidence_before_historical_membership_rows_transition_values_or_returns"
        or contract.get("preregistered_at") != "2026-07-16T20:35:22Z"
        or overlap.get("path")
        != "docs/a_share_three_day_st_recovery_mechanism_overlap_reaudit_20260717.json"
        or overlap.get("sha256")
        != "a916021e4fa6fca094d03cdb6a3360b12c4c4fc09f7e7250dd6f2fde7dc5bc55"
        or selection.get("minimum_permission_points") != 3000
        or selection.get("current_account_points") != 3000
        or selection.get("documented_history_start") != "2016-01-01"
        or selection.get("documented_update_time_asia_shanghai") != "09:20"
        or selection.get("documented_maximum_rows_per_call") != 1000
        or source.get("provider") != "tushare"
        or source.get("api") != "stock_st"
        or source.get("request_mode") != "one frozen local trading session per call"
        or tuple(source.get("requested_fields") or ())
        != TUSHARE_ST_MEMBERSHIP_RAW_FIELDS
        or accepted.get("new_provider_acceptance_call_allowed") is not False
        or accepted.get("offline_revalidation_required_before_full_sync") is not True
        or accepted_frame.get("content_sha256")
        != "2480f243cd46c2a71d6337c6e1f11f64a959788b16f077cfc8936c6fd6bc650c"
        or accepted_frame.get("rows") != 211
        or accepted_frame.get("trade_date") != "2026-07-13"
        or tuple(accepted_frame.get("relevant_columns_to_revalidate") or ())
        != ("ts_code", "trade_date", "type", "provider", "dataset")
        or accepted_frame.get(
            "name_or_type_name_values_may_be_read_by_dedicated_revalidation"
        )
        is not False
        or tuple(canonical.get("output_columns") or ()) != TUSHARE_ST_MEMBERSHIP_COLUMNS
        or canonical.get("raw_provider_frame_persisted") is not False
        or canonical.get("name_or_type_name_persisted") is not False
        or canonical.get("factor_value_persisted_by_full_sync") is not False
        or transition.get("factor_name") != "tushare_st_recovery_speed"
        or transition.get("raw_column") != "prior_consecutive_st_sessions"
        or transition.get("formula") != "1 / prior_consecutive_st_sessions"
        or transition.get("direction") != "higher_is_better"
        or transition.get("confirmation_session") != "t+1"
        or transition.get("same_first_absence_session_trade_allowed") is not False
        or transition.get("maximum_event_age_calendar_days") != 3
        or offline.get("provider_calls") != 0
        or offline.get("fixed_trade_date") != "2026-07-13"
        or offline.get("required_rows") != 211
        or offline.get("success_status")
        != "accepted_existing_entitlement_schema_and_type_pending_full_history"
        or snapshot.get("dataset") != "tushare_stock_st_membership"
        or snapshot.get("requested_start") != "2019-01-01"
        or snapshot.get("requested_end") != "2025-12-31"
        or snapshot.get("requested_local_sessions") != 1699
        or snapshot.get("provider_calls") != 1699
        or snapshot.get("provider_call_partition")
        != "one complete local trading session per call"
        or snapshot.get("minimum_seconds_between_calls") != 0.32
        or snapshot.get("maximum_attempts_per_session") != 3
        or snapshot.get("response_row_ceiling_is_strict") is not True
        or tuple(snapshot.get("required_partition_years") or ())
        != tuple(range(2019, 2026))
        or tuple(snapshot.get("required_output_columns") or ())
        != TUSHARE_ST_MEMBERSHIP_COLUMNS
        or snapshot.get("success_status")
        != "full_source_continuity_passed_pending_no_return_capacity_and_uniqueness"
        or downstream.get("capacity_before_comparison_fields") is not True
        or downstream.get("holding_period_trading_days") != 3
        or downstream.get("minimum_eligible_names_per_cross_section") != 6
        or downstream.get("minimum_distinct_factor_values") != 2
        or downstream.get("minimum_required_cohorts") != 200
        or downstream.get("minimum_observed_years") != 5
        or downstream.get("maximum_quality_age_days") != 550
        or downstream.get("minimum_listing_sessions") != 20
        or downstream.get("uniqueness_comparison_factor_count") != 54
        or downstream.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or contract.get("price_fields_loaded") != []
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare ST-recovery contract changed")
    overlap_path = resolve_record_path(str(overlap.get("path") or ""))
    if not overlap_path.exists() or file_digest(overlap_path) != overlap.get("sha256"):
        raise RichDataError("Tushare ST-recovery overlap audit changed")

    context = contract.get("local_context") or {}
    context_files = {
        "holding_universe": ("file_sha256", None),
        "source_universe": ("file_sha256", None),
        "calendar": ("file_sha256", None),
        "accepted_price_basis_for_later_return_stage_only": ("sha256", None),
        "quarterly_quality": ("sha256", "manifest_sha256"),
        "accepted_price_frontier": ("sha256", None),
    }
    for label, (sha_key, manifest_sha_key) in context_files.items():
        evidence = context.get(label) or {}
        linked_path = resolve_record_path(str(evidence.get("path") or ""))
        if not linked_path.exists() or file_digest(linked_path) != str(
            evidence.get(sha_key) or ""
        ):
            raise RichDataError(f"Tushare ST-recovery local context changed: {label}")
        if manifest_sha_key is not None:
            manifest_file = resolve_record_path(
                str(evidence.get("manifest_path") or "")
            )
            if not manifest_file.exists() or file_digest(manifest_file) != str(
                evidence.get(manifest_sha_key) or ""
            ):
                raise RichDataError(
                    f"Tushare ST-recovery manifest context changed: {label}"
                )
    return contract


def load_tushare_stock_st_acceptance_record(
    path: Path = DEFAULT_TUSHARE_ST_RECOVERY_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Validate the zero-network stock_st entitlement/schema acceptance record."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_ST_RECOVERY_ACCEPTANCE_RECORD_SHA256:
        raise RichDataError("Tushare stock_st acceptance-record fingerprint mismatch")
    record = load_json_record(
        path, kind="a_share_tushare_stock_st_source_acceptance_record"
    )
    protocol = record.get("protocol") or {}
    contract_link = protocol.get("data_contract") or {}
    overlap_link = protocol.get("mechanism_overlap_audit") or {}
    evidence = record.get("bound_existing_evidence") or {}
    manifest_link = evidence.get("combined_manifest") or {}
    frame_link = evidence.get("stock_st_frame") or {}
    audit = record.get("offline_revalidation") or {}
    boundary = record.get("observation_boundary") or {}
    decision = record.get("decision") or {}
    if (
        record.get("version") != 1
        or record.get("status")
        != "accepted_existing_entitlement_schema_and_type_pending_full_history"
        or contract_link.get("sha256") != TUSHARE_ST_RECOVERY_CONTRACT_SHA256
        or overlap_link.get("sha256")
        != "a916021e4fa6fca094d03cdb6a3360b12c4c4fc09f7e7250dd6f2fde7dc5bc55"
        or manifest_link.get("sha256")
        != "83c141749256a01852cf2cb0534da653e947e264a1b5ba3eb0efa2fd4b87a849"
        or frame_link.get("file_sha256")
        != "6689ceeeecd1d13a5f5475a8c9993335e145052d146eb61014c86665d18010c3"
        or frame_link.get("content_sha256")
        != "2480f243cd46c2a71d6337c6e1f11f64a959788b16f077cfc8936c6fd6bc650c"
        or frame_link.get("manifest_rows") != 211
        or audit.get("provider_calls_issued") != 0
        or tuple(audit.get("columns_read") or ())
        != ("ts_code", "trade_date", "type", "provider", "dataset")
        or audit.get("name_values_read") is not False
        or audit.get("type_name_values_read") is not False
        or audit.get("rows_revalidated") != 211
        or audit.get("missing_required_rows") != 0
        or audit.get("duplicate_stock_date_keys") != 0
        or tuple(audit.get("observed_type_values") or ()) != ("ST",)
        or boundary.get("historical_membership_rows_observed_for_dedicated_mechanism")
        is not False
        or boundary.get("membership_transition_derived") is not False
        or boundary.get("consecutive_st_duration_derived") is not False
        or boundary.get("factor_value_derived") is not False
        or boundary.get("price_fields_loaded") != []
        or boundary.get("forward_return_fields_read") is not False
        or decision.get("source_entitlement_schema_and_literal_type_accepted")
        is not True
        or decision.get("full_history_authorized_only_under_exact_contract") is not True
        or decision.get("acceptance_call_may_be_repeated") is not False
        or decision.get("static_st_membership_may_be_ranked") is not False
        or decision.get("factor_or_return_stage_authorized") is not False
        or record.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare stock_st acceptance record changed")
    load_tushare_st_recovery_contract(
        resolve_record_path(str(contract_link.get("path") or ""))
    )
    overlap_path = resolve_record_path(str(overlap_link.get("path") or ""))
    manifest_file = resolve_record_path(str(manifest_link.get("path") or ""))
    frame_file = resolve_record_path(str(frame_link.get("path") or ""))
    if (
        not overlap_path.exists()
        or file_digest(overlap_path) != overlap_link.get("sha256")
        or not manifest_file.exists()
        or file_digest(manifest_file) != manifest_link.get("sha256")
        or not frame_file.exists()
        or file_digest(frame_file) != frame_link.get("file_sha256")
    ):
        raise RichDataError("Tushare stock_st accepted evidence fingerprint changed")
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    files = [
        item
        for item in manifest.get("files") or []
        if item.get("dataset") == "stock-st"
    ]
    if (
        manifest.get("dataset") != "tushare_events"
        or manifest.get("provider") != "tushare"
        or manifest.get("acceptance_status")
        != "pending_event_time_alignment_and_canonicalization"
        or len(files) != 1
        or files[0].get("path") != frame_link.get("path")
        or files[0].get("sha256") != frame_link.get("content_sha256")
        or int(files[0].get("rows") or -1) != 211
    ):
        raise RichDataError("Tushare stock_st accepted manifest identity changed")
    frame = pd.read_parquet(
        frame_file,
        columns=["ts_code", "trade_date", "type", "provider", "dataset"],
    )
    if (
        len(frame) != 211
        or frame.isna().any().any()
        or frame.duplicated(["ts_code", "trade_date"]).any()
        or set(frame["trade_date"].astype(str)) != {"20260713"}
        or set(frame["type"].astype(str)) != {"ST"}
        or set(frame["provider"].astype(str)) != {"tushare"}
        or set(frame["dataset"].astype(str)) != {"stock-st"}
    ):
        raise RichDataError("Tushare stock_st accepted frame integrity changed")
    return record


def load_tushare_st_recovery_no_return_spec(
    path: Path = DEFAULT_TUSHARE_ST_RECOVERY_NO_RETURN_SPEC,
) -> dict[str, Any]:
    """Validate the pre-history no-return ST-recovery capacity protocol."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_ST_RECOVERY_NO_RETURN_SPEC_SHA256:
        raise RichDataError("Tushare ST-recovery no-return spec fingerprint mismatch")
    spec = load_json_record(
        path, kind="a_share_tushare_st_recovery_no_return_preregistration"
    )
    source = spec.get("source_protocol") or {}
    capacity = spec.get("capacity_contract") or {}
    uniqueness = spec.get("uniqueness_contract") or {}
    policy = spec.get("no_return_gate_policy") or {}
    comparisons = tuple(uniqueness.get("comparison_factors") or ())
    if (
        spec.get("version") != 1
        or spec.get("status")
        != "frozen_after_single_session_source_acceptance_before_full_history_transitions_factor_values_comparison_fields_or_returns"
        or (source.get("data_contract") or {}).get("sha256")
        != TUSHARE_ST_RECOVERY_CONTRACT_SHA256
        or (source.get("source_acceptance_record") or {}).get("sha256")
        != TUSHARE_ST_RECOVERY_ACCEPTANCE_RECORD_SHA256
        or source.get("required_full_snapshot_dataset") != "tushare_stock_st_membership"
        or source.get("required_full_snapshot_status")
        != "full_source_continuity_passed_pending_no_return_capacity_and_uniqueness"
        or source.get("required_local_sessions") != 1699
        or tuple(source.get("required_partition_years") or ())
        != tuple(range(2019, 2026))
        or tuple(source.get("required_canonical_columns") or ())
        != TUSHARE_ST_MEMBERSHIP_COLUMNS
        or source.get("factor") != "tushare_st_recovery_speed"
        or source.get("formula") != "1 / prior_consecutive_st_sessions"
        or source.get("direction") != "higher_is_better"
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("comparison_factor_count") != 54
        or len(comparisons) != 54
        or len(set(comparisons)) != 54
        or uniqueness.get("minimum_pairwise_names_per_session") != 6
        or uniqueness.get("minimum_pairwise_sessions_per_comparison") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or policy.get("capacity_must_run_before_comparison_fields") is not True
        or policy.get("both_capacity_and_uniqueness_must_pass") is not True
        or policy.get("one_completed_combined_audit_per_full_snapshot") is not True
        or spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare ST-recovery no-return spec changed")
    for label in (
        "mechanism_overlap_audit",
        "data_contract",
        "source_acceptance_record",
    ):
        link = source.get(label) or {}
        linked_path = resolve_record_path(str(link.get("path") or ""))
        if not linked_path.exists() or file_digest(linked_path) != link.get("sha256"):
            raise RichDataError(f"Tushare ST-recovery source protocol changed: {label}")
    return spec


def load_tushare_st_recovery_research_record(
    path: Path = DEFAULT_TUSHARE_ST_RECOVERY_RESEARCH_RECORD,
) -> dict[str, Any]:
    """Validate the tracked terminal stock_st source-continuity record."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_ST_RECOVERY_RESEARCH_RECORD_SHA256:
        raise RichDataError("Tushare ST-recovery terminal-record fingerprint mismatch")
    record = load_json_record(path, kind="a_share_tushare_st_recovery_research_record")
    mechanism = record.get("mechanism") or {}
    evidence = record.get("frozen_evidence") or {}
    attempt = record.get("full_source_attempt") or {}
    scope = record.get("scope_and_safety") or {}
    interpretation = record.get("interpretation") or {}
    decision = record.get("terminal_decision") or {}
    overlap = evidence.get("mechanism_overlap_audit") or {}
    contract = evidence.get("data_contract") or {}
    acceptance = evidence.get("source_acceptance_record") or {}
    no_return = evidence.get("no_return_preregistration") or {}
    failure = evidence.get("terminal_full_source_failure") or {}
    if (
        record.get("version") != 1
        or record.get("status")
        != "terminal_source_continuity_failed_on_empty_historical_session_before_transitions_factor_values_capacity_uniqueness_or_returns"
        or record.get("recorded_at") != "2026-07-16T20:55:52Z"
        or mechanism.get("name") != "tushare_st_recovery_speed"
        or mechanism.get("formula") != "1 / prior_consecutive_st_sessions"
        or mechanism.get("direction") != "higher_is_better"
        or mechanism.get("exit_definition")
        != "present at t-1 and absent on both consecutive local sessions t and t+1"
        or mechanism.get("availability")
        != "confirmed at t+1 close and first tradable at the following local session open"
        or mechanism.get("maximum_event_age_calendar_days") != 3
        or overlap.get("sha256")
        != "a916021e4fa6fca094d03cdb6a3360b12c4c4fc09f7e7250dd6f2fde7dc5bc55"
        or contract.get("sha256") != TUSHARE_ST_RECOVERY_CONTRACT_SHA256
        or acceptance.get("sha256") != TUSHARE_ST_RECOVERY_ACCEPTANCE_RECORD_SHA256
        or no_return.get("sha256") != TUSHARE_ST_RECOVERY_NO_RETURN_SPEC_SHA256
        or failure.get("sha256")
        != "58e12ab4b03dafd8f99725c03a8b8988d5df797f98163164cb3e221075640a75"
        or attempt.get("run_id")
        != "20260716T205448Z_tushare_stock_st_membership_4fa3ee9c"
        or attempt.get("requested_start") != "2019-01-01"
        or attempt.get("requested_end") != "2025-12-31"
        or attempt.get("planned_local_sessions") != 1699
        or attempt.get("logical_sessions_issued") != 59
        or attempt.get("logical_sessions_completed") != 58
        or attempt.get("first_completed_session") != "2019-01-02"
        or attempt.get("last_completed_session") != "2019-03-29"
        or attempt.get("failed_session") != "2019-04-01"
        or attempt.get("provider_request_attempts") != 59
        or attempt.get("source_rows_observed_before_failure") != 5066
        or tuple(attempt.get("requested_fields") or ())
        != TUSHARE_ST_MEMBERSHIP_RAW_FIELDS
        or attempt.get("failure_code")
        != "empty_historical_membership_response_cannot_prove_complete_daily_list"
        or attempt.get("empty_response_treated_as_zero_membership") is not False
        or attempt.get("failed_session_retried_or_rerequested") is not False
        or attempt.get("later_sessions_requested") is not False
        or attempt.get("partial_completed_history_usable") is not False
        or attempt.get("partial_snapshot_deleted") is not True
        or attempt.get("final_snapshot_published") is not False
        or attempt.get("published_partition_count") != 0
        or attempt.get("published_files") != []
        or scope.get("raw_provider_frames_persisted") is not False
        or scope.get("name_or_type_name_requested_or_persisted") is not False
        or scope.get("credentials_logged_or_stored") is not False
        or scope.get("membership_transitions_derived") is not False
        or scope.get("prior_consecutive_st_sessions_derived") is not False
        or scope.get("factor_values_derived_or_persisted") is not False
        or scope.get("capacity_run") is not False
        or scope.get("comparison_fields_loaded") is not False
        or scope.get("uniqueness_run") is not False
        or scope.get("price_fields_loaded") != []
        or scope.get("open_close_or_forward_return_fields_read") is not False
        or scope.get("forward_return_fields_read") is not False
        or scope.get("aggregation_scoring_selection_sizing_or_ordering_performed")
        is not False
        or interpretation.get("economic_classification")
        != "The recovery-speed idea remains economically distinct from static ST exclusion, but this exact Tushare historical route failed its predeclared reproducibility gate and contributes no admitted factor."
        or decision.get("full_source_contract_consumed") is not True
        or decision.get("full_source_retry_allowed") is not False
        or decision.get("failed_session_detail_or_probe_request_allowed") is not False
        or decision.get("empty_response_as_zero_or_complete_absence_allowed")
        is not False
        or decision.get("skip_fill_interpolate_or_mix_provider_allowed") is not False
        or decision.get("partial_58_session_history_use_allowed") is not False
        or decision.get("capacity_comparison_uniqueness_or_return_work_allowed")
        is not False
        or decision.get(
            "combine_aggregate_score_select_size_order_or_level2_justification_allowed"
        )
        is not False
    ):
        raise RichDataError("Tushare ST-recovery terminal record changed")

    for label, link in (
        ("mechanism overlap audit", overlap),
        ("data contract", contract),
        ("source acceptance record", acceptance),
        ("no-return preregistration", no_return),
    ):
        linked_path = resolve_record_path(str(link.get("path") or ""))
        if not linked_path.exists() or file_digest(linked_path) != link.get("sha256"):
            raise RichDataError(f"Tushare ST-recovery terminal {label} changed")

    failure_path = resolve_record_path(str(failure.get("path") or ""))
    if failure_path.exists():
        if file_digest(failure_path) != failure.get("sha256"):
            raise RichDataError("Tushare ST-recovery terminal failure changed")
        failure_record = load_json_record(
            failure_path, kind="a_share_rich_data_snapshot"
        )
        source_request = failure_record.get("source_request") or {}
        if (
            failure_record.get("dataset") != "tushare_stock_st_membership"
            or failure_record.get("run_id") != attempt.get("run_id")
            or failure_record.get("failed_trade_date") != attempt.get("failed_session")
            or source_request.get("logical_sessions_planned") != 1699
            or source_request.get("logical_sessions_issued") != 59
            or source_request.get("logical_sessions_completed") != 58
            or source_request.get("provider_request_attempts") != 59
            or source_request.get("source_rows_observed") != 5066
            or tuple(source_request.get("fields") or ())
            != TUSHARE_ST_MEMBERSHIP_RAW_FIELDS
            or failure_record.get("files") != []
            or failure_record.get("partial_snapshot_deleted") is not True
            or failure_record.get("final_snapshot_published") is not False
            or failure_record.get("membership_transitions_derived") is not False
            or failure_record.get("prior_spell_durations_derived") is not False
            or failure_record.get("factor_values_derived_or_persisted") is not False
            or failure_record.get("price_fields_loaded") != []
            or failure_record.get("forward_return_fields_read") is not False
            or failure_record.get("selection_or_promotion_allowed") is not False
        ):
            raise RichDataError("Tushare ST-recovery terminal failure changed")
    return record


def load_tushare_st_recovery_source_chain() -> dict[str, Any]:
    """Validate contract, offline acceptance, and no-return protocol before Token use."""

    contract = load_tushare_st_recovery_contract()
    record = load_tushare_stock_st_acceptance_record()
    spec = load_tushare_st_recovery_no_return_spec()
    return {"contract": contract, "acceptance_record": record, "spec": spec}


def tushare_stock_st_full_snapshot_records() -> list[Path]:
    """Return any local manifest that consumed the one-shot full source contract."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_stock_st_membership*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_stock_st_membership":
            records.append(path)
    return records


def tushare_gross_margin_acceptance_records() -> list[Path]:
    """Return records that consumed the frozen gross-margin acceptance."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_gross_margin_acceptance*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_gross_margin_acceptance":
            records.append(path)
    return records


def load_tushare_gross_margin_acceptance_record(
    path: Path = DEFAULT_TUSHARE_GROSS_MARGIN_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Validate the successful one-shot gross-margin source acceptance."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_GROSS_MARGIN_ACCEPTANCE_RECORD_SHA256:
        raise RichDataError(
            "Tushare gross-margin acceptance-record fingerprint mismatch"
        )
    record = load_json_record(
        path, kind="a_share_tushare_gross_margin_source_acceptance_record"
    )
    contract = record.get("data_contract") or {}
    acceptance = record.get("acceptance") or {}
    factor_frame = acceptance.get("published_factor_frame") or {}
    quality = acceptance.get("quality") or {}
    privacy = record.get("privacy_and_scope") or {}
    decision = record.get("one_shot_and_next_action") or {}
    if (
        record.get("status")
        != "accepted_source_pending_frozen_full_history_and_no_return_gates"
        or contract.get("sha256") != TUSHARE_GROSS_MARGIN_CONTRACT_SHA256
        or acceptance.get("manifest_sha256")
        != "21aafe677009f09ef78ba1fb6b1a5eed52c6c147dac29b2861cdbd05c8324c02"
        or acceptance.get("provider_calls_issued") != 3
        or acceptance.get("source_rows") != 163
        or factor_frame.get("content_sha256")
        != "0147228cc123dd4ac4a538f9aa6708c10a449d8cd3d13d3b86d8c437030d5720"
        or factor_frame.get("rows") != 51
        or factor_frame.get("factor_distinct_values") != 51
        or quality.get("initial_rows_retained") != 67
        or quality.get("revised_rows_observed_but_not_used") != 96
        or quality.get("ambiguous_initial_periods_excluded") != 0
        or quality.get("duplicate_factor_event_keys") != 0
        or quality.get("source_margin_levels_persisted") is not False
        or quality.get("revised_values_persisted_or_used") is not False
        or privacy.get("raw_provider_frames_persisted") is not False
        or privacy.get("initial_or_revised_source_margin_levels_persisted") is not False
        or privacy.get("credentials_logged_or_stored") is not False
        or privacy.get("price_fields_loaded") != []
        or privacy.get("forward_return_fields_read") is not False
        or decision.get("acceptance_consumed") is not True
        or decision.get("price_access_authorized_now") is not False
        or decision.get("aggregation_scoring_selection_or_trading_authorized_now")
        is not False
    ):
        raise RichDataError("Tushare gross-margin acceptance record changed")
    for link in (
        record.get("mechanism_overlap_audit") or {},
        contract,
        {
            "path": acceptance.get("manifest_path"),
            "sha256": acceptance.get("manifest_sha256"),
        },
    ):
        linked_path = resolve_record_path(str(link.get("path") or ""))
        linked_sha = str(link.get("sha256") or "")
        if linked_path.exists() and file_digest(linked_path) != linked_sha:
            raise RichDataError(
                "Tushare gross-margin source-acceptance evidence changed: "
                f"{linked_path}"
            )
    return record


def load_tushare_gross_margin_source_chain(
    record_path: Path = DEFAULT_TUSHARE_GROSS_MARGIN_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Revalidate the frozen contract and accepted no-margin-level factor sample."""

    contract = load_tushare_gross_margin_contract()
    record_path = record_path.expanduser().resolve()
    record = load_tushare_gross_margin_acceptance_record(record_path)
    acceptance = record["acceptance"]
    manifest_file = resolve_record_path(str(acceptance["manifest_path"]))
    if (
        not manifest_file.exists()
        or file_digest(manifest_file) != acceptance["manifest_sha256"]
    ):
        raise RichDataError(
            "Tushare gross-margin acceptance manifest fingerprint mismatch"
        )
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    files = list(manifest.get("files") or [])
    published = acceptance["published_factor_frame"]
    if (
        manifest.get("dataset") != "tushare_gross_margin_acceptance"
        or manifest.get("provider") != "tushare"
        or manifest.get("acceptance_status") != acceptance["acceptance_status"]
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
        or len(files) != 1
        or files[0].get("path") != published["path"]
        or files[0].get("sha256") != published["content_sha256"]
        or files[0].get("rows") != published["rows"]
    ):
        raise RichDataError(
            "Tushare gross-margin acceptance manifest identity mismatch"
        )
    frame_path = resolve_record_path(str(published["path"]))
    if not frame_path.exists():
        raise RichDataError("Tushare gross-margin accepted factor frame is missing")
    frame = pd.read_parquet(frame_path)
    factor_name = "tushare_q_gross_margin_yoy_change_pp"
    expected_instruments = {
        qlib_symbol(ts_code.split(".", 1)[0])
        for ts_code in TUSHARE_GROSS_MARGIN_ACCEPTANCE_TS_CODES
    }
    factor = (
        pd.to_numeric(frame[factor_name], errors="coerce")
        if factor_name in frame
        else pd.Series(dtype="float64")
    )
    if (
        tuple(frame.columns) != TUSHARE_GROSS_MARGIN_COLUMNS
        or len(frame) != int(published["rows"])
        or frame_digest(frame) != published["content_sha256"]
        or set(frame["instrument"].astype(str)) != expected_instruments
        or frame.duplicated(["instrument", "announcement_date", "report_period"]).any()
        or frame[["announcement_date", "report_period"]].isna().any().any()
        or factor.isna().any()
        or not np.isfinite(factor.to_numpy(dtype=float, copy=False)).all()
        or int(factor.nunique()) != int(published["factor_distinct_values"])
        or not frame["provider"].eq("tushare").all()
        or any(
            str(column) in {"q_gsprofit_margin", "prior_q_gsprofit_margin"}
            for column in frame.columns
        )
    ):
        raise RichDataError(
            "Tushare gross-margin accepted factor integrity audit failed"
        )
    return {
        "contract": contract,
        "record_path": record_path,
        "record": record,
        "manifest_path": manifest_file,
        "manifest": manifest,
        "frame_path": frame_path,
        "frame": frame,
    }


def tushare_gross_margin_full_snapshot_records() -> list[Path]:
    """Return terminal full-source manifests or failures for this contract."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_gross_margin_full*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == (
            "tushare_single_quarter_gross_margin_yoy_change_events"
        ):
            records.append(path)
    return records


def load_tushare_gross_margin_research_record(
    path: Path = DEFAULT_TUSHARE_GROSS_MARGIN_RESEARCH_RECORD,
) -> dict[str, Any]:
    """Validate the terminal full-source gross-margin rejection."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_GROSS_MARGIN_RESEARCH_RECORD_SHA256:
        raise RichDataError("Tushare gross-margin research-record fingerprint mismatch")
    record = load_json_record(path, kind="a_share_tushare_gross_margin_research_record")
    attempt = record.get("full_source_attempt") or {}
    scope = record.get("scope_and_safety") or {}
    decision = record.get("terminal_decision") or {}
    evidence = record.get("frozen_evidence") or {}
    failure = evidence.get("terminal_full_source_failure") or {}
    if (
        record.get("status")
        != "terminal_rejected_at_full_source_identity_date_or_version_gate_before_partitions_capacity_uniqueness_or_returns"
        or failure.get("sha256")
        != "0089f7e37e08ad802c89f3dffffa7595d689d6b742a0d3d2ed97252295081607"
        or attempt.get("planned_provider_calls") != 10902
        or attempt.get("completed_instruments_before_failure") != 528
        or attempt.get("completed_provider_calls_before_failure") != 1058
        or attempt.get("source_rows_observed_before_failure") != 28566
        or attempt.get("failed_instrument") != "SH600638"
        or attempt.get("failed_slice") != "20220101-20251231"
        or attempt.get("failure_code") != "source_identity_date_or_version_failure"
        or attempt.get("field_level_failure_identity_known") is not False
        or attempt.get("partial_snapshot_deleted") is not True
        or attempt.get("final_snapshot_published") is not False
        or attempt.get("published_partition_count") != 0
        or scope.get("price_fields_loaded") != []
        or scope.get("forward_return_fields_read") is not False
        or scope.get("capacity_run") is not False
        or scope.get("uniqueness_run") is not False
        or decision.get("acceptance_retry_allowed") is not False
        or decision.get("full_source_retry_allowed") is not False
        or decision.get("capacity_uniqueness_or_return_work_allowed") is not False
    ):
        raise RichDataError("Tushare gross-margin terminal research record changed")
    for link in evidence.values():
        linked_path = resolve_record_path(str(link.get("path") or ""))
        linked_sha = str(link.get("sha256") or "")
        if linked_path.exists() and file_digest(linked_path) != linked_sha:
            raise RichDataError(
                f"Tushare gross-margin terminal evidence changed: {linked_path}"
            )
    return record


def load_tushare_audit_opinion_acceptance_record(
    path: Path = DEFAULT_TUSHARE_AUDIT_OPINION_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Validate the successful one-shot audit-opinion source acceptance."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_AUDIT_OPINION_ACCEPTANCE_RECORD_SHA256:
        raise RichDataError(
            "Tushare audit-opinion acceptance-record fingerprint mismatch"
        )
    record = load_json_record(
        path, kind="a_share_tushare_audit_opinion_source_acceptance_record"
    )
    contract = record.get("data_contract") or {}
    acceptance = record.get("acceptance") or {}
    factor_frame = acceptance.get("published_factor_frame") or {}
    quality = acceptance.get("quality") or {}
    privacy = record.get("privacy_and_scope") or {}
    decision = record.get("one_shot_and_next_action") or {}
    if (
        record.get("status")
        != "accepted_source_pending_frozen_full_history_and_no_return_gates"
        or contract.get("sha256") != TUSHARE_AUDIT_OPINION_CONTRACT_SHA256
        or acceptance.get("manifest_sha256")
        != "f23e7cc7571dc08f72d8ca1cbf465e2556934f22043a34aff50a87af8aab9b51"
        or acceptance.get("provider_calls_issued") != 3
        or acceptance.get("source_rows") != 21
        or factor_frame.get("content_sha256")
        != "a0b6c96d447f05e5f4c08cfc67098ea8665b2bc5b88d1e05a2b060df8722f7b5"
        or factor_frame.get("rows") != 21
        or quality.get("duplicate_stock_announcement_keys") != 0
        or quality.get("distinct_hashed_opinion_categories") != 4
        or quality.get("factor_distinct_values") != 2
        or quality.get("factor_value_counts") != {"0": 4, "1": 17}
        or privacy.get("raw_provider_frames_persisted") is not False
        or privacy.get("raw_or_normalized_audit_result_text_persisted") is not False
        or privacy.get("credentials_logged_or_stored") is not False
        or privacy.get("price_fields_loaded") != []
        or privacy.get("forward_return_fields_read") is not False
        or decision.get("acceptance_consumed") is not True
        or decision.get("price_access_authorized_now") is not False
        or decision.get("aggregation_scoring_selection_or_trading_authorized_now")
        is not False
    ):
        raise RichDataError("Tushare audit-opinion acceptance record changed")
    for link in (
        record.get("mechanism_overlap_audit") or {},
        contract,
        {
            "path": acceptance.get("manifest_path"),
            "sha256": acceptance.get("manifest_sha256"),
        },
    ):
        linked_path = resolve_record_path(str(link.get("path") or ""))
        linked_sha = str(link.get("sha256") or "")
        if linked_path.exists() and file_digest(linked_path) != linked_sha:
            raise RichDataError(
                "Tushare audit-opinion source-acceptance evidence changed: "
                f"{linked_path}"
            )
    return record


def load_tushare_audit_opinion_source_chain(
    record_path: Path = DEFAULT_TUSHARE_AUDIT_OPINION_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Revalidate the frozen contract and accepted no-text factor sample."""

    contract = load_tushare_audit_opinion_contract()
    record_path = record_path.expanduser().resolve()
    record = load_tushare_audit_opinion_acceptance_record(record_path)
    acceptance = record["acceptance"]
    manifest_file = resolve_record_path(str(acceptance["manifest_path"]))
    if (
        not manifest_file.exists()
        or file_digest(manifest_file) != acceptance["manifest_sha256"]
    ):
        raise RichDataError(
            "Tushare audit-opinion acceptance manifest fingerprint mismatch"
        )
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    files = list(manifest.get("files") or [])
    published = acceptance["published_factor_frame"]
    if (
        manifest.get("dataset") != "tushare_audit_opinion_acceptance"
        or manifest.get("provider") != "tushare"
        or manifest.get("acceptance_status") != acceptance["acceptance_status"]
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
        or len(files) != 1
        or files[0].get("path") != published["path"]
        or files[0].get("sha256") != published["content_sha256"]
        or files[0].get("rows") != published["rows"]
    ):
        raise RichDataError(
            "Tushare audit-opinion acceptance manifest identity mismatch"
        )
    frame_path = resolve_record_path(str(published["path"]))
    if not frame_path.exists():
        raise RichDataError("Tushare audit-opinion accepted factor frame is missing")
    frame = pd.read_parquet(frame_path)
    factor_name = "tushare_is_standard_unqualified_audit_opinion"
    expected_instruments = {
        qlib_symbol(ts_code.split(".", 1)[0])
        for ts_code in TUSHARE_AUDIT_OPINION_ACCEPTANCE_TS_CODES
    }
    if (
        tuple(frame.columns) != TUSHARE_AUDIT_OPINION_COLUMNS
        or len(frame) != int(published["rows"])
        or frame_digest(frame) != published["content_sha256"]
        or set(frame["instrument"].astype(str)) != expected_instruments
        or frame.duplicated(["instrument", "announcement_date"]).any()
        or frame["announcement_date"].isna().any()
        or not frame[factor_name].isin({0, 1}).all()
        or frame[factor_name].value_counts().sort_index().to_dict() != {0: 4, 1: 17}
        or not pd.to_numeric(frame["audit_report_count"], errors="coerce").ge(1).all()
        or not frame["provider"].eq("tushare").all()
        or any("audit_result" in str(column).casefold() for column in frame.columns)
    ):
        raise RichDataError(
            "Tushare audit-opinion accepted factor integrity audit failed"
        )
    return {
        "contract": contract,
        "record_path": record_path,
        "record": record,
        "manifest_path": manifest_file,
        "manifest": manifest,
        "frame_path": frame_path,
        "frame": frame,
    }


def tushare_audit_opinion_full_snapshot_records() -> list[Path]:
    """Return terminal full-source manifests or failure records for this contract."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_audit_opinion_full*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_audit_opinion_events":
            records.append(path)
    return records


def load_tushare_disclosure_promptness_acceptance_record(
    path: Path = DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Validate the terminal first-period disclosure-plan rejection record."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_DISCLOSURE_PROMPTNESS_ACCEPTANCE_RECORD_SHA256:
        raise RichDataError(
            "Tushare disclosure-promptness acceptance-record fingerprint mismatch"
        )
    record = load_json_record(
        path, kind="a_share_tushare_disclosure_promptness_source_acceptance_record"
    )
    contract = record.get("data_contract") or {}
    failure = record.get("acceptance_failure") or {}
    interpretation = record.get("failure_interpretation") or {}
    decision = record.get("decision") or {}
    if (
        record.get("status")
        != "terminal_rejected_on_first_report_period_before_factor_values_or_returns"
        or contract.get("sha256") != TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT_SHA256
        or contract.get("factor") != "tushare_disclosure_plan_promptness"
        or failure.get("sha256")
        != "5929ce2a1520a9b93b170868be89e8dee7ef3842feb9a7de37625f2170ce9ef4"
        or failure.get("failed_report_period") != "20191231"
        or failure.get("source_rows_returned") != 4432
        or failure.get("invalid_key_or_date_rows") != 25
        or failure.get("provider_calls_issued") != 1
        or failure.get("factor_frame_published") is not False
        or failure.get("factor_value_constructed") is not False
        or failure.get("partial_snapshot_deleted") is not True
        or failure.get("final_snapshot_published") is not False
        or interpretation.get("factor_failure_claimed") is not False
        or decision.get("acceptance_retry_allowed") is not False
        or decision.get("request_remaining_periods_allowed") is not False
        or decision.get("run_full_history_allowed") is not False
        or decision.get("run_capacity_or_uniqueness_allowed") is not False
        or decision.get("run_return_diagnostic_allowed") is not False
        or record.get("price_fields_loaded") != []
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare disclosure-promptness acceptance record changed")
    for link in (
        record.get("mechanism_overlap_audit") or {},
        contract,
        failure,
    ):
        linked_path = resolve_record_path(str(link.get("path") or ""))
        linked_sha = str(link.get("sha256") or "")
        if linked_path.exists() and file_digest(linked_path) != linked_sha:
            raise RichDataError(
                "Tushare disclosure-promptness terminal evidence changed: "
                f"{linked_path}"
            )
    return record


def load_tushare_cash_conversion_contract(
    path: Path = DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT,
) -> dict[str, Any]:
    """Load and structurally revalidate the immutable pre-row accounting contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_CASH_CONVERSION_CONTRACT_SHA256:
        raise RichDataError("Tushare cash-conversion contract fingerprint mismatch")
    contract = load_json_record(
        path, kind="a_share_tushare_cash_conversion_data_contract"
    )
    selection = contract.get("source_selection") or {}
    source = contract.get("source") or {}
    version = contract.get("point_in_time_and_version_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    gates = contract.get("no_return_gates") or {}
    completeness = gates.get("source_completeness") or {}
    capacity = gates.get("capacity") or {}
    uniqueness = gates.get("uniqueness") or {}
    diagnostic = contract.get("diagnostic_policy_if_all_no_return_gates_pass") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_income_or_cashflow_entitlement_rows_full_history_factor_values_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T13:43:50Z"
        or selection.get("minimum_permission_points_each") != 2000
        or selection.get("current_account_points") != 3000
        or selection.get("provider_documented_maximum_rows_per_call") != 100
        or source.get("provider") != "tushare"
        or tuple(source.get("apis") or ()) != ("income", "cashflow")
        or source.get("request_mode")
        != "one stock and one frozen announcement-date range per endpoint call"
        or tuple(source.get("income_requested_fields") or ())
        != TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS
        or tuple(source.get("cashflow_requested_fields") or ())
        != TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS
        or version.get("candidate_company_type") != "1"
        or version.get("candidate_report_type") != "1 consolidated cumulative report"
        or tuple(version.get("non_candidate_context_report_types") or ())
        != tuple(
            str(value) for value in sorted(TUSHARE_CASH_CONVERSION_CONTEXT_REPORT_TYPES)
        )
        or tuple(
            version.get(
                "adjustment_report_types_that_exclude_the_whole_endpoint_period"
            )
            or ()
        )
        != tuple(
            str(value)
            for value in sorted(TUSHARE_CASH_CONVERSION_ADJUSTMENT_REPORT_TYPES)
        )
        or version.get("conservative_availability")
        != "first local trading session strictly after the later actual announcement date"
        or version.get("same_announcement_session_trade_allowed") is not False
        or version.get("maximum_event_age_calendar_days") != 3
        or version.get("forward_fill_beyond_event_age_allowed") is not False
        or factor.get("name") != "tushare_operating_cash_conversion"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula") != "n_cashflow_act / n_income_attr_p"
        or factor.get("clipping_winsorization_log_absolute_value_or_imputation")
        is not None
        or tuple(acceptance.get("fixed_symbols") or ())
        != TUSHARE_CASH_CONVERSION_ACCEPTANCE_SYMBOLS
        or acceptance.get("fixed_announcement_start") != "20240101"
        or acceptance.get("fixed_announcement_end") != "20260630"
        or acceptance.get("latest_allowed_actual_announcement_date") != "20260716"
        or tuple(acceptance.get("endpoints_per_symbol") or ()) != ("income", "cashflow")
        or acceptance.get("provider_calls") != 6
        or acceptance.get("minimum_usable_joined_periods_per_symbol") != 4
        or acceptance.get("success_status")
        != "accepted_entitlement_schema_version_policy_and_formula_pending_full_history"
        or snapshot.get("announcement_start") != "20190101"
        or snapshot.get("announcement_end") != "20251231"
        or snapshot.get("development_signal_start") != "2019-01-01"
        or snapshot.get("development_signal_end") != "2025-12-31"
        or snapshot.get(
            "request_each_point_in_time_buyable_instrument_once_per_endpoint"
        )
        is not True
        or snapshot.get("provider_call_partition")
        != "one ts_code over the full frozen announcement-date range for each endpoint"
        or snapshot.get("provider_documented_maximum_rows_per_call") != 100
        or snapshot.get("minimum_seconds_between_calls") != 0.65
        or snapshot.get("maximum_attempts_per_symbol_endpoint") != 3
        or tuple(snapshot.get("canonical_columns") or ())
        != TUSHARE_CASH_CONVERSION_COLUMNS
        or completeness.get("minimum_complete_joined_factor_events") != 5000
        or completeness.get("minimum_observed_signal_years") != 5
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("non_overlapping_cohorts") is not True
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("comparison_factor_count") != 54
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or diagnostic.get(
            "separate_immutable_preregistration_required_before_price_access"
        )
        is not True
        or diagnostic.get("holding_period_trading_days") != 3
        or diagnostic.get("topk") != 3
        or diagnostic.get("selection_or_promotion_allowed") is not False
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare cash-conversion contract does not match the frozen protocol"
        )
    return contract


def validate_tushare_cash_conversion_local_context(
    contract: dict[str, Any],
) -> dict[str, dict[str, str]]:
    """Fingerprint-bind every local no-return prerequisite before provider calls."""

    context = contract.get("local_context") or {}
    validated: dict[str, dict[str, str]] = {}
    for label, evidence in context.items():
        if (
            not isinstance(evidence, dict)
            or not evidence.get("path")
            or not evidence.get("sha256")
        ):
            raise RichDataError(f"cash-conversion context is incomplete: {label}")
        path = resolve_record_path(str(evidence["path"]))
        expected = str(evidence["sha256"])
        if not path.exists() or file_digest(path) != expected:
            raise RichDataError(
                f"cash-conversion context fingerprint mismatch: {label}"
            )
        validated[label] = {"path": manifest_path(path), "sha256": expected}
        manifest_value = evidence.get("manifest_path")
        manifest_sha = evidence.get("manifest_sha256")
        if manifest_value is not None or manifest_sha is not None:
            if not manifest_value or not manifest_sha:
                raise RichDataError(
                    f"cash-conversion manifest context is incomplete: {label}"
                )
            manifest_file = resolve_record_path(str(manifest_value))
            if not manifest_file.exists() or file_digest(manifest_file) != str(
                manifest_sha
            ):
                raise RichDataError(
                    f"cash-conversion manifest fingerprint mismatch: {label}"
                )
            validated[f"{label}_manifest"] = {
                "path": manifest_path(manifest_file),
                "sha256": str(manifest_sha),
            }
    return validated


def load_tushare_cash_conversion_company_type_repair(
    path: Path = DEFAULT_TUSHARE_CASH_CONVERSION_COMPANY_TYPE_REPAIR,
) -> dict[str, Any]:
    """Validate the exact no-price repair and its deleted first-attempt evidence."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_CASH_CONVERSION_COMPANY_TYPE_REPAIR_SHA256:
        raise RichDataError(
            "Tushare cash-conversion company-type repair fingerprint mismatch"
        )
    repair = load_json_record(
        path,
        kind="a_share_tushare_cash_conversion_company_type_source_repair",
    )
    protocol = repair.get("unchanged_source_protocol") or {}
    failed = repair.get("first_failed_full_source_run") or {}
    documentation = repair.get("official_documentation_recheck") or {}
    rule = repair.get("repair_policy") or {}
    retry = repair.get("single_retry_authorization") or {}
    downstream = repair.get("downstream_policy") or {}
    failure_path = resolve_record_path(str(failed.get("failure_record_path") or ""))
    expected_failure_sha = str(failed.get("failure_record_sha256") or "")
    if not failure_path.exists() or file_digest(failure_path) != expected_failure_sha:
        raise RichDataError(
            "Tushare cash-conversion company-type repair failure evidence mismatch"
        )
    failure = load_json_record(failure_path, kind="a_share_rich_data_source_failure")
    if (
        repair.get("version") != 1
        or repair.get("status")
        != "frozen_after_first_full_source_schema_failure_before_any_complete_full_snapshot_factor_values_prices_or_returns"
        or repair.get("frozen_at") != "2026-07-16T15:31:33Z"
        or protocol.get("data_contract_sha256")
        != TUSHARE_CASH_CONVERSION_CONTRACT_SHA256
        or protocol.get("source_acceptance_record_sha256")
        != TUSHARE_CASH_CONVERSION_ACCEPTANCE_RECORD_SHA256
        or protocol.get("candidate_company_type") != 1
        or protocol.get("candidate_report_type") != 1
        or protocol.get("factor") != "tushare_operating_cash_conversion"
        or protocol.get("formula") != "n_cashflow_act / n_income_attr_p"
        or protocol.get("direction") != "higher_is_better"
        or protocol.get("announcement_start") != "2019-01-01"
        or protocol.get("announcement_end") != "2025-12-31"
        or protocol.get("point_in_time_instrument_count") != 4794
        or protocol.get("provider_calls") != 9588
        or protocol.get("minimum_seconds_between_calls") != 0.65
        or protocol.get("maximum_attempts_per_symbol_endpoint") != 3
        or failed.get("run_id")
        != "20260716T141556Z_tushare_cash_conversion_full_b2e31205"
        or failed.get("failure_code") != "source_statement_type_failure"
        or failed.get("failed_instrument") != "SZ002961"
        or failed.get("failed_endpoint") != "income"
        or failed.get("observed_complete_integer_non_candidate_company_type_codes")
        != [7]
        or failed.get("completed_instruments_before_failure") != 3289
        or failed.get("completed_provider_calls_before_failure") != 6579
        or failed.get("partial_snapshot_deleted") is not True
        or failed.get("final_snapshot_published") is not False
        or failed.get("price_fields_loaded") != []
        or failed.get("forward_return_fields_read") is not False
        or documentation.get("documented_company_type_codes")
        != {
            "1": "general_industry",
            "2": "bank",
            "3": "insurance",
            "4": "securities",
        }
        or documentation.get("code_7_documented") is not False
        or documentation.get("inference_about_code_7_business_meaning_allowed")
        is not False
        or rule.get("target_row_rule")
        != "company_type must be a complete finite integer exactly equal to 1"
        or rule.get("invalid_company_type_rule")
        != "A missing, non-finite, or non-integer company_type remains a fatal source key error."
        or rule.get("source_completeness_thresholds_changed") is not False
        or rule.get("capacity_thresholds_changed") is not False
        or rule.get("uniqueness_thresholds_changed") is not False
        or rule.get("factor_values_from_failed_partial_run_observed_or_reused")
        is not False
        or rule.get("prices_or_returns_observed") is not False
        or retry.get("requires_exact_prior_failure_record_sha256")
        != expected_failure_sha
        or retry.get("maximum_repair_retries") != 1
        or retry.get("resume_partial_snapshot_allowed") is not False
        or retry.get("full_from_scratch_restart_required") is not True
        or retry.get("symbol_date_field_or_endpoint_subset_allowed") is not False
        or retry.get("request_count_change_allowed") is not False
        or retry.get("retry_is_consumed_by_success_or_failure") is not True
        or downstream.get("successful_retry_must_bind_this_repair_path_and_sha256")
        is not True
        or downstream.get(
            "successful_retry_still_requires_original_source_completeness_gate"
        )
        is not True
        or downstream.get(
            "successful_retry_still_requires_frozen_no_return_capacity_and_uniqueness_audit"
        )
        is not True
        or downstream.get("generic_factor_diagnostic_allowed") is not False
        or repair.get("price_fields_loaded") != []
        or repair.get("forward_return_fields_read") is not False
        or repair.get("selection_or_promotion_allowed") is not False
        or failure.get("run_id") != failed.get("run_id")
        or failure.get("failure_code") != failed.get("failure_code")
        or failure.get("failed_instrument") != failed.get("failed_instrument")
        or failure.get("failed_endpoint") != failed.get("failed_endpoint")
        or failure.get("completed_instruments_before_failure")
        != failed.get("completed_instruments_before_failure")
        or failure.get("completed_provider_calls_before_failure")
        != failed.get("completed_provider_calls_before_failure")
        or failure.get("partial_snapshot_deleted") is not True
        or failure.get("final_snapshot_published") is not False
        or failure.get("price_fields_loaded") != []
        or failure.get("forward_return_fields_read") is not False
        or failure.get("error")
        != "Tushare income response contains unknown company types: [7]"
    ):
        raise RichDataError(
            "Tushare cash-conversion company-type repair does not match the frozen retry"
        )
    return {
        "repair_path": path,
        "repair": repair,
        "failure_path": failure_path,
        "failure": failure,
    }


def load_tushare_cash_conversion_research_record(
    path: Path = DEFAULT_TUSHARE_CASH_CONVERSION_RESEARCH_RECORD,
) -> dict[str, Any]:
    """Validate the tracked terminal source decision that forbids another run."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_CASH_CONVERSION_RESEARCH_RECORD_SHA256:
        raise RichDataError(
            "Tushare cash-conversion terminal research-record fingerprint mismatch"
        )
    record = load_json_record(
        path, kind="a_share_tushare_cash_conversion_research_record"
    )
    evidence = record.get("evidence_chain") or {}
    first = evidence.get("first_full_source_failure") or {}
    repair = evidence.get("company_type_source_repair") or {}
    second = evidence.get("second_full_source_failure") or {}
    source_gate = record.get("source_gate") or {}
    downstream = record.get("downstream_gates") or {}
    decision = record.get("decision") or {}
    if (
        record.get("version") != 1
        or record.get("status")
        != "terminal_rejected_at_full_source_after_single_repair_retry"
        or (record.get("factor") or {}).get("name")
        != "tushare_operating_cash_conversion"
        or first.get("sha256")
        != "59693d4e34f63425670eaf6bf41adf9aacca888379c36ba315535c82b4ab3f3a"
        or first.get("completed_provider_calls_before_failure") != 6579
        or first.get("partial_snapshot_deleted") is not True
        or first.get("final_snapshot_published") is not False
        or repair.get("sha256") != TUSHARE_CASH_CONVERSION_COMPANY_TYPE_REPAIR_SHA256
        or repair.get("authorized_full_from_scratch_retries") != 1
        or repair.get("retry_consumed") is not True
        or second.get("sha256")
        != "0f4d6d40081eda418a7a94c999ec83f1a5be33a29f6af5af0470390de10c7344"
        or second.get("failed_instrument") != "SZ301200"
        or second.get("failed_endpoint") != "income"
        or second.get("completed_instruments_before_failure") != 4518
        or second.get("completed_provider_calls_before_failure") != 9037
        or second.get("total_planned_provider_calls") != 9588
        or second.get("failure")
        != "Tushare income response contains a non-standard quarter end"
        or second.get("partial_snapshot_deleted") is not True
        or second.get("final_snapshot_published") is not False
        or second.get("repair_retry_consumed_by_this_failure") is not True
        or source_gate.get("complete_full_snapshot_published") is not False
        or source_gate.get("annual_partition_count") != 0
        or source_gate.get("source_completeness_gate_passed") is not False
        or downstream.get("capacity_audit_run") is not False
        or downstream.get("uniqueness_audit_run") is not False
        or downstream.get("forward_return_diagnostic_run") is not False
        or decision.get("same_source_version_rerun_allowed") is not False
        or decision.get("run_capacity_uniqueness_or_return_diagnostic_allowed")
        is not False
        or record.get("price_fields_loaded") != []
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare cash-conversion terminal research record changed")
    for link in (
        evidence.get("data_contract") or {},
        evidence.get("source_acceptance_record") or {},
        evidence.get("no_return_preregistration") or {},
        repair,
        first,
        second,
    ):
        linked_path = resolve_record_path(str(link.get("path") or ""))
        linked_sha = str(link.get("sha256") or "")
        if linked_path.exists() and file_digest(linked_path) != linked_sha:
            raise RichDataError(
                "Tushare cash-conversion terminal evidence fingerprint mismatch: "
                f"{linked_path}"
            )
    return record


def tushare_cash_conversion_acceptance_records() -> list[Path]:
    """Return terminal records that consumed the cash-conversion one-shot gate."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_cash_conversion_acceptance*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_cash_conversion_acceptance":
            records.append(path)
    return records


def load_tushare_cash_conversion_source_chain(
    record_path: Path = DEFAULT_TUSHARE_CASH_CONVERSION_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Revalidate the frozen contract and accepted no-return factor sample."""

    contract = load_tushare_cash_conversion_contract()
    record_path = record_path.expanduser().resolve()
    if (
        not record_path.exists()
        or file_digest(record_path) != TUSHARE_CASH_CONVERSION_ACCEPTANCE_RECORD_SHA256
    ):
        raise RichDataError(
            "Tushare cash-conversion acceptance record fingerprint mismatch"
        )
    record = load_json_record(
        record_path,
        kind="a_share_tushare_cash_conversion_source_acceptance_record",
    )
    contract_link = record.get("data_contract") or {}
    acceptance = record.get("acceptance") or {}
    next_action = record.get("one_shot_and_next_action") or {}
    manifest_file = resolve_record_path(str(acceptance.get("manifest_path") or ""))
    expected_manifest_sha = str(acceptance.get("manifest_sha256") or "")
    if (
        record.get("version") != 1
        or record.get("status")
        != "accepted_source_pending_frozen_full_history_and_no_return_gates"
        or contract_link.get("sha256") != TUSHARE_CASH_CONVERSION_CONTRACT_SHA256
        or contract_link.get("preregistered_at") != contract.get("preregistered_at")
        or acceptance.get("acceptance_status")
        != "accepted_entitlement_schema_version_policy_and_formula_pending_full_history"
        or tuple(acceptance.get("fixed_symbols") or ())
        != TUSHARE_CASH_CONVERSION_ACCEPTANCE_SYMBOLS
        or tuple(acceptance.get("endpoints_per_symbol") or ()) != ("income", "cashflow")
        or acceptance.get("provider_calls_issued") != 6
        or acceptance.get("provider_calls_expected") != 6
        or acceptance.get("total_source_rows") != 76
        or acceptance.get("formula") != "n_cashflow_act / n_income_attr_p"
        or acceptance.get("direction") != "higher_is_better"
        or acceptance.get("price_fields_loaded") != []
        or acceptance.get("forward_return_fields_read") is not False
        or acceptance.get("selection_or_promotion_performed") is not False
        or next_action.get("acceptance_consumed") is not True
        or next_action.get("price_access_authorized_now") is not False
        or next_action.get("aggregation_scoring_selection_or_trading_authorized_now")
        is not False
        or not manifest_file.exists()
        or file_digest(manifest_file) != expected_manifest_sha
    ):
        raise RichDataError("Tushare cash-conversion acceptance record is incompatible")
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    files = list(manifest.get("files") or [])
    published = acceptance.get("published_factor_frame") or {}
    if (
        manifest.get("dataset") != "tushare_cash_conversion_acceptance"
        or manifest.get("provider") != "tushare"
        or manifest.get("acceptance_status") != acceptance.get("acceptance_status")
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
        or len(files) != 1
        or files[0].get("path") != published.get("path")
        or files[0].get("sha256") != published.get("sha256")
        or files[0].get("rows") != published.get("rows")
    ):
        raise RichDataError(
            "Tushare cash-conversion acceptance manifest identity mismatch"
        )
    frame_path = resolve_record_path(str(published.get("path") or ""))
    if not frame_path.exists():
        raise RichDataError("Tushare cash-conversion accepted factor frame is missing")
    frame = pd.read_parquet(frame_path)
    denominator = pd.to_numeric(frame["n_income_attr_p"], errors="coerce")
    numerator = pd.to_numeric(frame["n_cashflow_act"], errors="coerce")
    factor = pd.to_numeric(frame["tushare_operating_cash_conversion"], errors="coerce")
    later_actual = frame[
        ["income_actual_announcement_date", "cashflow_actual_announcement_date"]
    ].max(axis=1)
    expected_instruments = {
        qlib_symbol(symbol.split(".", 1)[0])
        for symbol in TUSHARE_CASH_CONVERSION_ACCEPTANCE_SYMBOLS
    }
    if (
        tuple(frame.columns) != TUSHARE_CASH_CONVERSION_COLUMNS
        or len(frame) != int(published.get("rows") or -1)
        or frame_digest(frame) != published.get("sha256")
        or set(frame["instrument"].astype(str)) != expected_instruments
        or frame.duplicated(["instrument", "announcement_date", "report_period"]).any()
        or frame["announcement_date"].isna().any()
        or not pd.to_datetime(frame["announcement_date"]).eq(later_actual).all()
        or not np.isfinite(denominator).all()
        or not denominator.gt(0.0).all()
        or not np.isfinite(numerator).all()
        or not np.isfinite(factor).all()
        or not np.allclose(
            factor.to_numpy(dtype="float64"),
            numerator.to_numpy(dtype="float64") / denominator.to_numpy(dtype="float64"),
            rtol=0.0,
            atol=1e-12,
        )
        or not frame["provider"].eq("tushare").all()
    ):
        raise RichDataError(
            "Tushare cash-conversion accepted factor integrity audit failed"
        )
    return {
        "contract": contract,
        "record_path": record_path,
        "record": record,
        "manifest_path": manifest_file,
        "manifest": manifest,
        "frame_path": frame_path,
        "frame": frame,
    }


def tushare_cash_conversion_full_snapshot_records() -> list[Path]:
    """Return completed full-snapshot manifests for this exact mechanism."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_cash_conversion_full*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_operating_cash_conversion":
            records.append(path)
    return records


def load_tushare_daily_pb_contract(
    path: Path = DEFAULT_TUSHARE_DAILY_PB_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-entitlement daily PB contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_DAILY_PB_CONTRACT_SHA256:
        raise RichDataError("Tushare daily PB contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_tushare_daily_pb_data_contract")
    source = contract.get("source") or {}
    factor = contract.get("factor") or {}
    snapshot = contract.get("snapshot_contract") or {}
    partition = snapshot.get("partition_policy") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    completeness = contract.get("source_completeness_policy") or {}
    uniqueness = contract.get("no_return_uniqueness_policy") or {}
    capacity = contract.get("coverage_and_capacity_policy") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_entitlement_rows_full_history_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T09:48:42Z"
        or source.get("provider") != "tushare"
        or source.get("api") != "daily_basic"
        or tuple(source.get("requested_fields") or ()) != TUSHARE_DAILY_PB_RAW_FIELDS
        or tuple(snapshot.get("columns") or ()) != TUSHARE_DAILY_PB_COLUMNS
        or partition.get("partition") != "one calendar year"
        or partition.get("provider_call_partition") != "one local trading session"
        or partition.get("provider_documented_maximum_rows_per_call") != 6000
        or partition.get("minimum_seconds_between_calls") != 0.32
        or partition.get("maximum_attempts_per_session") != 3
        or factor.get("name") != "tushare_positive_book_to_market"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula") != "1 / pb"
        or acceptance.get("fixed_completed_session") != "2026-07-13"
        or acceptance.get("minimum_all_market_source_rows") != 4000
        or completeness.get("minimum_sessions_with_fifty_positive_pb_names") != 200
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_eligible_names_per_cross_section") != 50
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare daily PB contract does not match the frozen protocol"
        )
    return contract


def load_tushare_free_float_scarcity_contract(
    path: Path = DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT,
) -> dict[str, Any]:
    """Load and verify the frozen pre-row free-float-scarcity contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT_SHA256:
        raise RichDataError("Tushare free-float-scarcity contract fingerprint mismatch")
    contract = load_json_record(
        path, kind="a_share_tushare_free_float_scarcity_data_contract"
    )
    source = contract.get("source") or {}
    factor = contract.get("factor") or {}
    point_in_time = contract.get("point_in_time_policy") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("snapshot_contract") or {}
    partition = snapshot.get("partition_policy") or {}
    completeness = contract.get("source_completeness_policy") or {}
    capacity = contract.get("no_return_capacity_policy") or {}
    uniqueness = contract.get("no_return_uniqueness_policy") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_after_mechanism_overlap_and_suspend_capacity_rejection_before_free_float_provider_rows_factor_values_prices_or_returns"
        or contract.get("preregistered_at") != "2026-07-16T21:21:37Z"
        or source.get("provider") != "tushare"
        or source.get("api") != "daily_basic"
        or source.get("minimum_permission_points") != 2000
        or source.get("authorized_account_points") != 3000
        or tuple(source.get("requested_fields") or ())
        != TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS
        or tuple(snapshot.get("columns") or ()) != TUSHARE_FREE_FLOAT_SCARCITY_COLUMNS
        or factor.get("name") != "tushare_free_float_scarcity"
        or factor.get("formula") != "1 - free_share / total_share"
        or factor.get("direction") != "higher_is_better"
        or point_in_time.get(
            "availability", point_in_time.get("source_row_availability")
        )
        != "after the documented 15:00-17:00 update on trade_date"
        or point_in_time.get("maximum_event_age_calendar_days") != 0
        or acceptance.get("fixed_completed_session") != "2026-07-13"
        or acceptance.get("minimum_all_market_source_rows") != 4000
        or acceptance.get("provider_documented_maximum_rows_per_call") != 6000
        or acceptance.get("minimum_valid_holding_universe_coverage") != 0.95
        or acceptance.get("minimum_valid_holding_names") != 50
        or acceptance.get("minimum_distinct_factor_values") != 2
        or partition.get("storage_partition") != "one calendar year"
        or partition.get("provider_call_partition") != "one local trading session"
        or partition.get("provider_documented_maximum_rows_per_call") != 6000
        or partition.get("minimum_seconds_between_calls") != 0.32
        or partition.get("maximum_attempts_per_session") != 3
        or completeness.get("minimum_median_valid_holding_universe_coverage") != 0.95
        or completeness.get("minimum_p05_valid_holding_universe_coverage") != 0.9
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or uniqueness.get("comparison_factor_count") != 54
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("required_named_near_neighbor") != "free_float_cap_proxy"
        or contract.get("provider_rows_observed_before_freeze") is not False
        or contract.get("factor_values_observed_before_freeze") is not False
        or contract.get("price_fields_loaded") != []
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare free-float-scarcity contract does not match the frozen protocol"
        )

    for label, link in (contract.get("freeze_evidence") or {}).items():
        linked_path = resolve_record_path(str((link or {}).get("path") or ""))
        if not linked_path.exists() or file_digest(linked_path) != link.get("sha256"):
            raise RichDataError(
                f"Tushare free-float-scarcity freeze evidence changed: {label}"
            )
    for label, link in (contract.get("local_context") or {}).items():
        linked_path = resolve_record_path(str((link or {}).get("path") or ""))
        if not linked_path.exists() or file_digest(linked_path) != link.get("sha256"):
            raise RichDataError(
                f"Tushare free-float-scarcity local context changed: {label}"
            )
    return contract


def load_tushare_free_float_scarcity_acceptance_record(
    path: Path = DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Verify the tracked cross-clone record for the consumed source probe."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_FREE_FLOAT_SCARCITY_ACCEPTANCE_RECORD_SHA256:
        raise RichDataError(
            "Tushare free-float-scarcity acceptance-record fingerprint mismatch"
        )
    record = load_json_record(
        path,
        kind="a_share_tushare_free_float_scarcity_source_acceptance_record",
    )
    contract = record.get("data_contract") or {}
    audit = record.get("mechanism_and_capacity_audit") or {}
    manifest = record.get("acceptance_manifest") or {}
    frame = record.get("accepted_frame") or {}
    request = record.get("source_request") or {}
    observed = record.get("observed_result") or {}
    if (
        record.get("version") != 1
        or record.get("status")
        != "accepted_pending_frozen_full_history_capacity_and_uniqueness"
        or record.get("created_at") != "2026-07-16T21:33:33Z"
        or contract.get("path")
        != "docs/a_share_tushare_free_float_scarcity_data_contract.json"
        or contract.get("sha256") != TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT_SHA256
        or contract.get("preregistered_at") != "2026-07-16T21:21:37Z"
        or contract.get("provider_rows_observed_before_freeze") is not False
        or contract.get("factor_values_observed_before_freeze") is not False
        or audit.get("path")
        != "docs/a_share_three_day_free_float_scarcity_mechanism_overlap_reaudit_20260717.json"
        or audit.get("sha256")
        != "62c6affbf4ea77a8d85a162f6a641a92bca17dc2d0a661744ed68b8e49b5c3d7"
        or manifest.get("path")
        != "data/metadata/rich_data/runs/20260716T213248Z_tushare_free_float_scarcity_acceptance_76551e6b.json"
        or manifest.get("sha256")
        != "459fe609a218c1ed336740796dce04e967d015b328391cfe3b67651cd2b1569a"
        or manifest.get("run_id")
        != "20260716T213248Z_tushare_free_float_scarcity_acceptance_76551e6b"
        or manifest.get("requested_session") != "2026-07-13"
        or manifest.get("acceptance_status")
        != "accepted_entitlement_formula_and_current_coverage_pending_full_history_and_frozen_no_return_protocol"
        or frame.get("path")
        != "data/raw/a_share/rich/tushare/free_float_scarcity/acceptance/20260716T213248Z_tushare_free_float_scarcity_acceptance_76551e6b/free_float_scarcity.parquet"
        or frame.get("content_sha256")
        != "e9bb5984673c0fa903bb6cf6c15e24509ddd971db918f08f7ea75302bc62cc0c"
        or frame.get("file_sha256")
        != "7f12d2db8de0c0bb97478dab53926256a92ec91617b446a1c20ad723cd3327d7"
        or int(frame.get("rows") or -1) != 4586
        or tuple(frame.get("columns") or ()) != TUSHARE_FREE_FLOAT_SCARCITY_COLUMNS
        or request.get("provider") != "tushare"
        or request.get("api") != "daily_basic"
        or tuple(request.get("fields") or ()) != TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS
        or request.get("provider_calls") != 1
        or request.get("all_market_source_rows") != 5524
        or request.get("forbidden_fields_requested_or_stored") != []
        or request.get("credentials_logged_or_stored") is not False
        or observed.get("expected_point_in_time_holding_names") != 4592
        or observed.get("valid_free_float_holding_names") != 4586
        or observed.get("valid_free_float_holding_coverage") != 0.9986933797909407
        or observed.get("distinct_factor_values") != 4568
        or observed.get("formula_max_absolute_error") != 0.0
        or observed.get("schema_formula_and_current_coverage_gate_passed") is not True
        or record.get("price_fields_loaded") != []
        or record.get("open_close_or_forward_return_fields_read") is not False
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare free-float-scarcity acceptance record is inconsistent"
        )
    return record


def load_eastmoney_balance_sheet_resilience_contract(
    path: Path = DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT,
) -> dict[str, Any]:
    """Load and verify the frozen pre-row balance-sheet resilience contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT_SHA256:
        raise RichDataError(
            "Eastmoney balance-sheet-resilience contract fingerprint mismatch"
        )
    contract = load_json_record(
        path, kind="a_share_eastmoney_balance_sheet_resilience_data_contract"
    )
    source = contract.get("source") or {}
    request = source.get("request_parameters") or {}
    schema = source.get("source_schema_policy") or {}
    positions = schema.get("raw_json_data_object_zero_based_positions") or {}
    adapter = contract.get("pinned_public_adapter") or {}
    factor = contract.get("factor") or {}
    point_in_time = contract.get("point_in_time_policy") or {}
    normalized = contract.get("normalized_snapshot") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    full = contract.get("full_snapshot_contract") or {}
    capacity = contract.get("capacity_contract") or {}
    uniqueness = contract.get("uniqueness_contract") or {}
    mechanism = contract.get("mechanism_selection") or {}
    expected_positions = {
        "stock_code": 1,
        "announcement_date": 12,
        "total_assets": 14,
        "total_liabilities": 22,
        "vendor_asset_liability_ratio_percent_for_formula_audit_only": 32,
    }
    report_dates = list(full.get("report_dates") or [])
    expected_report_dates = [
        f"{year}-{month_day}"
        for year in range(2019, 2026)
        for month_day in ("03-31", "06-30", "09-30", "12-31")
    ]
    dense = list(uniqueness.get("dense_comparison_factors") or [])
    sparse = list(
        uniqueness.get("sparse_event_factors_excluded_from_statistical_pass_fail") or []
    )
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_new_balance_sheet_provider_rows_factor_values_capacity_uniqueness_prices_or_returns"
        or contract.get("preregistered_at") != "2026-07-16T22:33:14Z"
        or mechanism.get("path")
        != "docs/a_share_three_day_balance_sheet_resilience_mechanism_overlap_reaudit_20260717.json"
        or mechanism.get("sha256_at_contract_freeze")
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_MECHANISM_AUDIT_SHA256
        or source.get("provider") != "Eastmoney public datacenter"
        or source.get("endpoint")
        != "https://datacenter-web.eastmoney.com/api/data/v1/get"
        or source.get("report_name") != "RPT_DMSK_FN_BALANCE"
        or request.get("sortColumns") != "NOTICE_DATE,SECURITY_CODE"
        or request.get("sortTypes") != "-1,-1"
        or request.get("pageSize") != 500
        or request.get("columns") != "ALL"
        or request.get("filter_template")
        != '(SECURITY_TYPE_CODE in ("058001001","058001008"))(TRADE_MARKET_CODE!="069001017")(REPORT_DATE=\'YYYY-MM-DD\')'
        or source.get("maximum_pages_per_partition") != 20
        or source.get("maximum_attempts_per_page") != 4
        or source.get("retry_backoff_seconds") != [0.5, 1.0, 2.0, 4.0]
        or source.get("credentials_required") != []
        or source.get("authentication_cookie_proxy_or_retail_session_allowed")
        is not False
        or positions != expected_positions
        or schema.get("minimum_raw_columns") != 33
        or schema.get("schema_position_change_allowed") is not False
        or adapter.get("commit") != "fcdbf25aa864a218c54864c3f6ab6a2ed19cce28"
        or adapter.get("source_path") != "akshare/stock_feature/stock_report_em.py"
        or adapter.get("source_file_sha256")
        != "2012492017222a405d5cd396d3a29a384bc79dd8c1dc4d3e8737f1d2361bd783"
        or adapter.get("function") != "stock_zcfz_em"
        or adapter.get("function_lines") != "20-158"
        or adapter.get("function_block_sha256")
        != "2b56023d50c0c1f7c9c73e8cc27cc0d7d03b6573a90174f2698a63094b3ba903"
        or factor.get("name") != "eastmoney_balance_sheet_resilience"
        or factor.get("formula") != "1 - total_liabilities / total_assets"
        or factor.get("direction") != "higher_is_better"
        or factor.get("valid_range") != [0.0, 1.0]
        or point_in_time.get("conservative_availability")
        != "first local trading session strictly after announcement_date"
        or point_in_time.get("same_announcement_session_trade_allowed") is not False
        or point_in_time.get("maximum_age_calendar_days") != 550
        or tuple(normalized.get("columns") or ())
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS
        or tuple(normalized.get("event_key") or ()) != ("instrument", "report_date")
        or normalized.get("provider_value") != "eastmoney"
        or normalized.get("duplicate_event_keys_allowed") is not False
        or acceptance.get("fixed_report_date") != "2025-12-31"
        or acceptance.get("one_count_complete_partition_only") is not True
        or acceptance.get("minimum_valid_holding_names") != 4000
        or acceptance.get("minimum_valid_point_in_time_holding_coverage") != 0.9
        or acceptance.get("minimum_distinct_factor_values") != 100
        or acceptance.get("maximum_formula_absolute_error") != 1e-8
        or report_dates != expected_report_dates
        or full.get("required_report_date_count") != 28
        or full.get("minimum_valid_active_holding_coverage_per_report_date") != 0.85
        or full.get("minimum_median_valid_active_holding_coverage") != 0.95
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("minimum_eligible_names_per_cross_section") != 50
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("maximum_factor_age_calendar_days") != 550
        or uniqueness.get("dense_comparison_factor_count") != 46
        or len(dense) != 46
        or len(set(dense)) != 46
        or len(sparse) != 8
        or len(set(sparse)) != 8
        or uniqueness.get("minimum_pairwise_sessions_per_dense_comparison") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or contract.get("price_fields_loaded") != []
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience contract does not match the frozen protocol"
        )

    mechanism_path = resolve_record_path(str(mechanism.get("path") or ""))
    if (
        not mechanism_path.exists()
        or file_digest(mechanism_path)
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_MECHANISM_AUDIT_SHA256
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience mechanism audit changed"
        )
    for label, link in (contract.get("local_context") or {}).items():
        if not isinstance(link, dict) or "path" not in link or "sha256" not in link:
            continue
        linked_path = resolve_record_path(str(link.get("path") or ""))
        if not linked_path.exists() or file_digest(linked_path) != link.get("sha256"):
            raise RichDataError(
                f"Eastmoney balance-sheet-resilience local context changed: {label}"
            )
    return contract


def load_eastmoney_core_profit_consistency_contract(
    path: Path = DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT,
) -> dict[str, Any]:
    """Load and verify the frozen pre-row core-profit contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT_SHA256:
        raise RichDataError(
            "Eastmoney core-profit-consistency contract fingerprint mismatch"
        )
    contract = load_json_record(
        path, kind="a_share_eastmoney_core_profit_consistency_data_contract"
    )
    mechanism = contract.get("mechanism_selection") or {}
    adapter = contract.get("pinned_public_adapter") or {}
    source = contract.get("source") or {}
    request = source.get("request_parameters") or {}
    schema = source.get("source_schema_policy") or {}
    positions = schema.get("raw_json_data_object_zero_based_positions") or {}
    factor = contract.get("factor") or {}
    point_in_time = contract.get("point_in_time_policy") or {}
    normalized = contract.get("normalized_snapshot") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    full = contract.get("full_snapshot_framework") or {}
    capacity = contract.get("capacity_contract") or {}
    uniqueness = contract.get("uniqueness_contract") or {}
    expected_dates = [
        f"{year}-{month_day}"
        for year in range(2019, 2026)
        for month_day in ("03-31", "06-30", "09-30", "12-31")
    ]
    expected_positions = {
        "stock_code": 1,
        "announcement_date": 12,
        "operating_profit": 24,
        "total_profit": 25,
    }
    dense = list(uniqueness.get("dense_comparison_factors") or [])
    sparse = list(
        uniqueness.get("sparse_event_factors_excluded_from_statistical_pass_fail")
        or []
    )
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_new_income_statement_provider_rows_factor_values_capacity_uniqueness_prices_or_returns"
        or contract.get("preregistered_at") != "2026-07-16T23:37:00Z"
        or mechanism.get("path")
        != "docs/a_share_three_day_core_profit_consistency_mechanism_overlap_reaudit_20260717.json"
        or mechanism.get("sha256_at_contract_freeze")
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_MECHANISM_AUDIT_SHA256
        or adapter.get("commit") != "fcdbf25aa864a218c54864c3f6ab6a2ed19cce28"
        or adapter.get("source_path")
        != "akshare/stock_feature/stock_report_em.py"
        or adapter.get("source_file_sha256")
        != "2012492017222a405d5cd396d3a29a384bc79dd8c1dc4d3e8737f1d2361bd783"
        or adapter.get("function") != "stock_lrb_em"
        or adapter.get("function_lines") != "302-435"
        or adapter.get("function_block_sha256")
        != "9702cd6ff8cbf49e32f9b7ca97170a4ecf954393c6972f06d5985610f44bb97c"
        or source.get("provider") != "Eastmoney public datacenter"
        or source.get("endpoint")
        != "https://datacenter-web.eastmoney.com/api/data/v1/get"
        or source.get("report_name") != "RPT_DMSK_FN_INCOME"
        or request.get("sortColumns") != "NOTICE_DATE,SECURITY_CODE"
        or request.get("sortTypes") != "-1,-1"
        or request.get("pageSize") != 500
        or request.get("columns") != "ALL"
        or request.get("filter_template")
        != '(SECURITY_TYPE_CODE in ("058001001","058001008"))(TRADE_MARKET_CODE!="069001017")(REPORT_DATE=\'YYYY-MM-DD\')'
        or source.get("maximum_pages_per_partition") != 20
        or source.get("maximum_attempts_per_page") != 4
        or source.get("retry_backoff_seconds") != [0.5, 1.0, 2.0, 4.0]
        or source.get("credentials_required") != []
        or source.get("tushare_token_read") is not False
        or source.get("authentication_cookie_proxy_or_retail_session_allowed")
        is not False
        or positions != expected_positions
        or schema.get("minimum_raw_columns") != 26
        or schema.get("schema_position_change_allowed") is not False
        or factor.get("name") != "eastmoney_core_profit_consistency"
        or factor.get("formula")
        != "min(operating_profit, total_profit) / max(operating_profit, total_profit)"
        or factor.get("direction") != "higher_is_better"
        or factor.get("valid_range") != [0.0, 1.0]
        or point_in_time.get("same_announcement_session_trade_allowed") is not False
        or point_in_time.get("older_report_carry_after_new_partition_activation_allowed")
        is not False
        or point_in_time.get("late_older_correction_can_supersede_newer_report")
        is not False
        or point_in_time.get("maximum_age_calendar_days") != 550
        or tuple(normalized.get("columns") or ())
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS
        or tuple(normalized.get("event_key") or ())
        != ("instrument", "report_date")
        or normalized.get("provider_value") != "eastmoney"
        or normalized.get("duplicate_event_keys_allowed") is not False
        or acceptance.get("fixed_report_date") != "2025-12-31"
        or acceptance.get("one_count_complete_partition_only") is not True
        or acceptance.get("minimum_complete_identity_holding_names") != 4000
        or acceptance.get("minimum_complete_identity_holding_coverage") != 0.9
        or acceptance.get("minimum_valid_factor_holding_names") != 2500
        or acceptance.get("minimum_valid_factor_holding_coverage") != 0.55
        or acceptance.get("minimum_distinct_factor_values") != 100
        or acceptance.get("maximum_equivalent_formula_absolute_error") != 1e-12
        or full.get("report_dates") != expected_dates
        or full.get("required_report_date_count") != 28
        or full.get("new_network_partition_count_if_acceptance_passes") != 27
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("minimum_eligible_names_per_cross_section") != 50
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("maximum_factor_age_calendar_days") != 550
        or uniqueness.get("dense_comparison_factor_count") != 47
        or len(dense) != 47
        or len(set(dense)) != 47
        or dense[-1:] != ["eastmoney_balance_sheet_resilience"]
        or len(sparse) != 8
        or len(set(sparse)) != 8
        or uniqueness.get("minimum_pairwise_sessions_per_dense_comparison") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or contract.get("price_fields_loaded") != []
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency contract does not match the frozen protocol"
        )
    mechanism_path = resolve_record_path(str(mechanism.get("path") or ""))
    if (
        not mechanism_path.exists()
        or file_digest(mechanism_path)
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_MECHANISM_AUDIT_SHA256
    ):
        raise RichDataError("Eastmoney core-profit-consistency mechanism audit changed")
    for label, link in (contract.get("local_context") or {}).items():
        if not isinstance(link, dict) or "path" not in link or "sha256" not in link:
            continue
        linked_path = resolve_record_path(str(link.get("path") or ""))
        if not linked_path.exists() or file_digest(linked_path) != link.get("sha256"):
            raise RichDataError(
                f"Eastmoney core-profit-consistency local context changed: {label}"
            )
    return contract


def load_tushare_free_float_scarcity_source_chain(
    path: Path = DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_NO_RETURN_SPEC,
) -> dict[str, Any]:
    """Verify the post-acceptance, pre-history structural-scarcity chain."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_FREE_FLOAT_SCARCITY_NO_RETURN_SPEC_SHA256:
        raise RichDataError(
            "Tushare free-float-scarcity no-return preregistration fingerprint mismatch"
        )
    spec = load_json_record(
        path,
        kind="a_share_tushare_free_float_scarcity_no_return_preregistration",
    )
    source = spec.get("source_protocol") or {}
    snapshot = spec.get("full_source_snapshot_contract") or {}
    capacity = spec.get("capacity_contract") or {}
    uniqueness = spec.get("uniqueness_contract") or {}
    policy = spec.get("no_return_gate_policy") or {}
    contract_link = source.get("data_contract") or {}
    record_link = source.get("source_acceptance_record") or {}
    manifest_link = source.get("source_acceptance_manifest") or {}
    frame_link = source.get("source_acceptance_frame") or {}
    contract = load_tushare_free_float_scarcity_contract(
        resolve_record_path(str(contract_link.get("path") or ""))
    )
    record = load_tushare_free_float_scarcity_acceptance_record(
        resolve_record_path(str(record_link.get("path") or ""))
    )
    if (
        spec.get("version") != 1
        or spec.get("status")
        != "frozen_after_single_session_acceptance_before_full_history_capacity_uniqueness_or_factor_returns_observed"
        or spec.get("preregistered_at") != "2026-07-16T21:37:09Z"
        or contract_link.get("sha256") != TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT_SHA256
        or contract_link.get("preregistered_at") != contract.get("preregistered_at")
        or record_link.get("sha256")
        != TUSHARE_FREE_FLOAT_SCARCITY_ACCEPTANCE_RECORD_SHA256
        or source.get("provider") != "tushare"
        or source.get("api") != "daily_basic"
        or tuple(source.get("requested_fields") or ())
        != TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS
        or source.get("factor") != "tushare_free_float_scarcity"
        or source.get("formula") != "1 - free_share / total_share"
        or source.get("direction") != "higher_is_better"
        or snapshot.get("dataset") != "tushare_free_float_scarcity"
        or snapshot.get("provider") != "tushare"
        or snapshot.get("required_success_status")
        != "full_source_coverage_passed_pending_no_return_capacity_and_uniqueness"
        or snapshot.get("requested_start") != "2019-01-01"
        or snapshot.get("requested_end") != "2025-12-31"
        or snapshot.get("required_local_trading_sessions") != 1699
        or snapshot.get("expected_provider_calls") != 1699
        or snapshot.get("provider_documented_maximum_rows_per_call") != 6000
        or snapshot.get("minimum_seconds_between_calls") != 0.32
        or snapshot.get("maximum_attempts_per_session") != 3
        or tuple(snapshot.get("retry_backoff_seconds") or ()) != (2, 5)
        or snapshot.get("requests_are_sequential") is not True
        or snapshot.get("one_full_snapshot_attempt_after_acceptance") is not True
        or tuple(snapshot.get("required_partition_years") or ())
        != tuple(range(2019, 2026))
        or tuple(snapshot.get("required_columns") or ())
        != TUSHARE_FREE_FLOAT_SCARCITY_COLUMNS
        or tuple(snapshot.get("event_key") or ()) != ("instrument", "trade_date")
        or snapshot.get("minimum_median_valid_holding_universe_coverage") != 0.95
        or snapshot.get("minimum_p05_valid_holding_universe_coverage") != 0.9
        or snapshot.get("minimum_sessions_with_fifty_valid_names") != 200
        or snapshot.get("minimum_observed_source_years") != 5
        or snapshot.get("all_years_share_one_hidden_temporary_root") is not True
        or snapshot.get("partial_snapshot_accepted") is not False
        or capacity.get("development_start") != "2019-01-01"
        or capacity.get("development_end") != "2025-12-31"
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("non_overlapping_cohorts") is not True
        or capacity.get("minimum_eligible_names_per_cross_section") != 50
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("screen_start") != "2025-01-01"
        or uniqueness.get("screen_end") != "2025-12-31"
        or uniqueness.get("minimum_pairwise_names_per_session") != 50
        or uniqueness.get("minimum_pairwise_sessions_per_comparison") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or uniqueness.get("required_named_near_neighbor") != "free_float_cap_proxy"
        or uniqueness.get("comparison_factor_count") != 54
        or len(uniqueness.get("comparison_factors") or []) != 54
        or "free_float_cap_proxy" not in set(uniqueness.get("comparison_factors") or [])
        or policy.get("capacity_must_run_before_close_known_comparison_fields")
        is not True
        or policy.get("both_capacity_and_uniqueness_must_pass") is not True
        or policy.get("one_completed_combined_audit_per_full_snapshot") is not True
        or spec.get("price_fields_loaded") != []
        or spec.get("open_close_or_forward_return_fields_read") is not False
        or spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare free-float-scarcity no-return preregistration is inconsistent"
        )

    manifest_path_value = resolve_record_path(str(manifest_link.get("path") or ""))
    frame_path = resolve_record_path(str(frame_link.get("path") or ""))
    if (
        not manifest_path_value.exists()
        or file_digest(manifest_path_value) != manifest_link.get("sha256")
        or not frame_path.exists()
        or file_digest(frame_path) != frame_link.get("file_sha256")
    ):
        raise RichDataError(
            "Tushare free-float-scarcity acceptance evidence fingerprint mismatch"
        )
    manifest = load_json_record(manifest_path_value, kind="a_share_rich_data_snapshot")
    files = list(manifest.get("files") or [])
    request = manifest.get("source_request") or {}
    quality = manifest.get("source_quality") or {}
    record_manifest = record.get("acceptance_manifest") or {}
    record_frame = record.get("accepted_frame") or {}
    if (
        record_manifest.get("sha256") != manifest_link.get("sha256")
        or record_frame.get("content_sha256") != frame_link.get("content_sha256")
        or record_frame.get("file_sha256") != frame_link.get("file_sha256")
        or manifest.get("dataset") != "tushare_free_float_scarcity_acceptance"
        or manifest.get("provider") != "tushare"
        or manifest.get("requested_start") != "2026-07-13"
        or manifest.get("requested_end") != "2026-07-13"
        or manifest.get("acceptance_status")
        != "accepted_entitlement_formula_and_current_coverage_pending_full_history_and_frozen_no_return_protocol"
        or request.get("api") != "daily_basic"
        or tuple(request.get("fields") or ()) != TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS
        or request.get("forbidden_fields_requested_or_stored") != []
        or request.get("credentials_logged_or_stored") is not False
        or quality.get("valid_free_float_holding_names") != 4586
        or quality.get("valid_free_float_holding_coverage") != 0.9986933797909407
        or quality.get("distinct_factor_values") != 4568
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
        or len(files) != 1
        or files[0].get("path") != frame_link.get("path")
        or files[0].get("sha256") != frame_link.get("content_sha256")
        or int(files[0].get("rows") or -1) != int(frame_link.get("rows") or -2)
    ):
        raise RichDataError(
            "Tushare free-float-scarcity acceptance evidence identity mismatch"
        )
    frame = load_snapshot_frame(files[0])
    dates = pd.to_datetime(frame["trade_date"], errors="coerce").dt.normalize()
    total_share = pd.to_numeric(frame["total_share"], errors="coerce")
    free_share = pd.to_numeric(frame["free_share"], errors="coerce")
    factor = pd.to_numeric(frame["tushare_free_float_scarcity"], errors="coerce")
    if (
        tuple(frame.columns) != TUSHARE_FREE_FLOAT_SCARCITY_COLUMNS
        or len(frame) != int(frame_link["rows"])
        or dates.isna().any()
        or not dates.eq(pd.Timestamp("2026-07-13")).all()
        or frame["instrument"].astype("string").isna().any()
        or frame["instrument"].nunique() != len(frame)
        or not np.isfinite(total_share).all()
        or not np.isfinite(free_share).all()
        or not total_share.gt(0.0).all()
        or not free_share.gt(0.0).all()
        or not free_share.le(total_share).all()
        or not np.isfinite(factor).all()
        or not np.allclose(
            factor.to_numpy(dtype="float64"),
            1.0
            - free_share.to_numpy(dtype="float64")
            / total_share.to_numpy(dtype="float64"),
            rtol=0.0,
            atol=1e-12,
        )
        or not frame["provider"].eq("tushare").all()
    ):
        raise RichDataError(
            "Tushare free-float-scarcity acceptance formula audit failed"
        )

    context_paths: dict[str, Path] = {}
    context = spec.get("point_in_time_context") or {}
    for label, link, digest_key in (
        ("holding_universe", context.get("holding_universe") or {}, "file_sha256"),
        ("local_calendar", context.get("local_calendar") or {}, "file_sha256"),
        ("quarterly_quality", context.get("quarterly_quality") or {}, "sha256"),
        (
            "accepted_price_basis",
            context.get("accepted_price_basis_for_later_comparison_or_return_work")
            or {},
            "sha256",
        ),
        (
            "accepted_price_frontier",
            context.get("accepted_price_frontier") or {},
            "sha256",
        ),
    ):
        linked = resolve_record_path(str(link.get("path") or ""))
        if not linked.exists() or file_digest(linked) != link.get(digest_key):
            raise RichDataError(
                f"Tushare free-float-scarcity {label} fingerprint mismatch"
            )
        context_paths[label] = linked
    quality_link = context.get("quarterly_quality") or {}
    quality_manifest = resolve_record_path(str(quality_link.get("manifest_path") or ""))
    if not quality_manifest.exists() or file_digest(
        quality_manifest
    ) != quality_link.get("manifest_sha256"):
        raise RichDataError(
            "Tushare free-float-scarcity quarterly-quality manifest changed"
        )
    return {
        "spec_path": path,
        "spec": spec,
        "contract": contract,
        "record_path": resolve_record_path(str(record_link["path"])),
        "record": record,
        "manifest_path": manifest_path_value,
        "manifest": manifest,
        "frame_path": frame_path,
        "context_paths": context_paths,
    }


def load_tushare_free_float_scarcity_full_source_record(
    path: Path = DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_FULL_SOURCE_RECORD,
) -> dict[str, Any]:
    """Verify the tracked cross-clone full-source completion record."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_FREE_FLOAT_SCARCITY_FULL_SOURCE_RECORD_SHA256:
        raise RichDataError(
            "Tushare free-float-scarcity full-source record fingerprint mismatch"
        )
    record = load_json_record(
        path, kind="a_share_tushare_free_float_scarcity_full_source_record"
    )
    chain = record.get("source_chain") or {}
    manifest = record.get("full_manifest") or {}
    request = record.get("source_request") or {}
    quality = record.get("normalization_quality") or {}
    coverage = record.get("coverage") or {}
    partitions = list(record.get("partitions") or [])
    years = tuple(int(item.get("year") or 0) for item in partitions)
    rows = tuple(int(item.get("rows") or 0) for item in partitions)
    expected_rows = (880012, 912940, 986192, 1040146, 1079358, 1094386, 1105230)
    if (
        record.get("version") != 1
        or record.get("status")
        != "accepted_full_source_pending_no_return_capacity_and_uniqueness"
        or record.get("created_at") != "2026-07-16T21:56:44Z"
        or ((chain.get("data_contract") or {}).get("sha256"))
        != TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT_SHA256
        or ((chain.get("source_acceptance_record") or {}).get("sha256"))
        != TUSHARE_FREE_FLOAT_SCARCITY_ACCEPTANCE_RECORD_SHA256
        or ((chain.get("no_return_preregistration") or {}).get("sha256"))
        != TUSHARE_FREE_FLOAT_SCARCITY_NO_RETURN_SPEC_SHA256
        or manifest.get("path")
        != "data/metadata/rich_data/runs/20260716T214522Z_tushare_free_float_scarcity_c647ce28.json"
        or manifest.get("sha256")
        != "b5653c447c59588e169ed24dd1915adc5b1b2d37b8769dbd682bdc2505797965"
        or manifest.get("run_id")
        != "20260716T214522Z_tushare_free_float_scarcity_c647ce28"
        or manifest.get("requested_start") != "2019-01-01"
        or manifest.get("requested_end") != "2025-12-31"
        or manifest.get("acceptance_status")
        != "full_source_coverage_passed_pending_no_return_capacity_and_uniqueness"
        or years != tuple(range(2019, 2026))
        or rows != expected_rows
        or len(partitions) != 7
        or any(not item.get("content_sha256") for item in partitions)
        or any(not item.get("file_sha256") for item in partitions)
        or request.get("provider") != "tushare"
        or request.get("api") != "daily_basic"
        or tuple(request.get("fields") or ()) != TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS
        or request.get("completed_provider_calls") != 1699
        or request.get("forbidden_fields_requested_or_stored") != []
        or request.get("credentials_logged_or_stored") is not False
        or quality.get("all_market_source_rows") != 7931826
        or quality.get("valid_holding_rows_written") != 7098264
        or quality.get("duplicate_stock_date_rows") != 0
        or quality.get("invalid_retained_share_or_factor_rows") != 0
        or quality.get("formula_max_absolute_error") != 0.0
        or coverage.get("calendar_sessions") != 1699
        or coverage.get("observed_source_years") != 7
        or coverage.get("median_valid_holding_universe_coverage") != 0.9968066814050602
        or coverage.get("p05_valid_holding_universe_coverage") != 0.9917082362759253
        or coverage.get("sessions_with_at_least_fifty_valid_names") != 1699
        or coverage.get("source_coverage_gate_passed") is not True
        or record.get("price_fields_loaded") != []
        or record.get("open_close_or_forward_return_fields_read") is not False
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare free-float-scarcity full-source record is inconsistent"
        )
    return record


def load_tushare_sw_industry_breadth_contract(
    path: Path = DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-row SW2021 industry-breadth contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256:
        raise RichDataError("Tushare SW industry-breadth contract fingerprint mismatch")
    contract = load_json_record(
        path, kind="a_share_tushare_sw_industry_breadth_data_contract"
    )
    source = contract.get("source") or {}
    membership = contract.get("point_in_time_membership_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    gates = contract.get("no_return_gates") or {}
    diagnostic = contract.get("diagnostic_policy_if_all_no_return_gates_pass") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_index_member_rows_factor_values_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T11:22:05Z"
        or source.get("provider") != "tushare"
        or source.get("classification_api") != "index_classify"
        or source.get("classification_parameters") != {"level": "L1", "src": "SW2021"}
        or tuple(source.get("classification_requested_fields") or ())
        != TUSHARE_SW_CLASSIFICATION_RAW_FIELDS
        or source.get("membership_api") != "index_member_all"
        or tuple(source.get("membership_requested_fields") or ())
        != TUSHARE_SW_MEMBERSHIP_RAW_FIELDS
        or tuple(source.get("membership_is_new_values") or ()) != ("Y", "N")
        or membership.get("classification_version") != "SW2021"
        or membership.get("industry_level") != "L1 only"
        or membership.get("maximum_active_level_one_memberships_per_stock_session") != 1
        or factor.get("name") != "sw1_three_session_leave_one_out_breadth"
        or factor.get("direction") != "higher_is_better"
        or factor.get("minimum_other_valid_peers_each_session") != 10
        or factor.get("peer_minimum_listing_sessions") != 20
        or factor.get("stock_self_direction_included") is not False
        or acceptance.get("representative_l1_code") != "801010.SI"
        or acceptance.get("minimum_classification_rows") != 25
        or acceptance.get("maximum_classification_rows") != 40
        or acceptance.get("minimum_current_representative_members") != 20
        or acceptance.get("minimum_historical_representative_members") != 1
        or tuple(snapshot.get("canonical_columns") or ())
        != TUSHARE_SW_MEMBERSHIP_COLUMNS
        or ((gates.get("capacity") or {}).get("minimum_required_cohorts")) != 200
        or ((gates.get("capacity") or {}).get("holding_period_trading_days")) != 3
        or ((gates.get("uniqueness") or {}).get("comparison_factor_count")) != 45
        or (
            (gates.get("uniqueness") or {}).get(
                "maximum_allowed_absolute_median_daily_rank_correlation"
            )
        )
        != 0.8
        or diagnostic.get("holding_period_trading_days") != 3
        or diagnostic.get("topk") != 3
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare SW industry-breadth contract does not match the frozen protocol"
        )
    return contract


def load_tushare_sw_industry_breadth_symbol_repair(
    path: Path = DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR,
) -> dict[str, Any]:
    """Verify the no-price symbol-normalization repair for the exact retry."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR_SHA256:
        raise RichDataError("Tushare SW symbol-repair fingerprint mismatch")
    repair = load_json_record(
        path,
        kind="a_share_tushare_sw_industry_breadth_symbol_normalization_repair",
    )
    contract = repair.get("bound_contract") or {}
    preregistration = repair.get("bound_preregistration") or {}
    failed = repair.get("failed_attempt") or {}
    diagnosis = repair.get("targeted_no_price_diagnosis") or {}
    rule = repair.get("repair") or {}
    retry = repair.get("retry_authorization") or {}
    failure_path = resolve_record_path(str(failed.get("record_path") or ""))
    if not failure_path.exists() or file_digest(failure_path) != failed.get(
        "record_sha256"
    ):
        raise RichDataError("Tushare SW symbol-repair failure evidence mismatch")
    failure = load_json_record(failure_path, kind="a_share_rich_data_source_failure")
    if (
        repair.get("version") != 1
        or repair.get("status")
        != "frozen_after_first_full_snapshot_infrastructure_failure_before_exact_retry_factor_values_or_factor_returns"
        or repair.get("recorded_at") != "2026-07-16T11:44:07Z"
        or contract.get("sha256") != TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256
        or preregistration.get("sha256")
        != TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC_SHA256
        or failure.get("dataset") != "tushare_sw2021_l1_membership"
        or failure.get("failed_l1_code") != failed.get("failed_l1_code")
        or failure.get("failed_is_new") != failed.get("failed_is_new")
        or failure.get("completed_provider_calls_before_failure")
        != failed.get("completed_provider_calls_before_failure")
        or failure.get("partial_snapshot_deleted") is not True
        or failure.get("final_snapshot_published") is not False
        or failure.get("forward_return_fields_read") is not False
        or diagnosis.get("provider_calls_after_failure") != 2
        or diagnosis.get("request_identity_unchanged") is not True
        or diagnosis.get("l1_code") != "801170.SI"
        or diagnosis.get("is_new") != "Y"
        or diagnosis.get("rows_each_call") != 144
        or diagnosis.get("unsupported_provider_symbol_rows") != 1
        or diagnosis.get("unsupported_provider_symbol_examples") != ["T00018.SH"]
        or diagnosis.get("price_fields_loaded") != []
        or diagnosis.get("factor_values_constructed") is not False
        or diagnosis.get("forward_return_fields_read") is not False
        or rule.get("unsupported_non_six_digit_provider_symbol_policy")
        != "exclude the row from the canonical membership frame and count it explicitly"
        or rule.get("interval_dates_changed") is not False
        or rule.get("classification_codes_changed") is not False
        or rule.get("is_new_states_changed") is not False
        or rule.get("provider_fields_changed") is not False
        or rule.get("provider_call_count_changed") is not False
        or rule.get("factor_formula_direction_window_or_peer_threshold_changed")
        is not False
        or retry.get("exact_full_snapshot_retry_allowed") is not True
        or retry.get("retry_must_restart_all_62_calls") is not True
        or retry.get("partial_resume_allowed") is not False
        or retry.get("maximum_accepted_full_snapshot_retries_under_this_repair") != 1
        or retry.get("factor_or_return_access_allowed_by_this_record") is not False
        or repair.get("forward_return_fields_read") is not False
        or repair.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare SW symbol-repair record is inconsistent")
    return repair


def load_tushare_sw_industry_breadth_source_chain(
    path: Path = DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC,
) -> dict[str, Any]:
    """Verify the accepted SW2021 source before the 62-call full snapshot."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC_SHA256:
        raise RichDataError(
            "Tushare SW industry-breadth capacity preregistration fingerprint mismatch"
        )
    spec = load_json_record(
        path, kind="a_share_tushare_sw_industry_breadth_capacity_preregistration"
    )
    contract_link = spec.get("data_contract") or {}
    acceptance = spec.get("source_acceptance") or {}
    snapshot = spec.get("full_membership_snapshot") or {}
    context = spec.get("point_in_time_context") or {}
    factor = spec.get("factor_contract") or {}
    audit = spec.get("combined_no_return_audit") or {}
    capacity = audit.get("capacity") or {}
    uniqueness = audit.get("uniqueness") or {}
    evidence = spec.get("freeze_evidence") or {}
    contract = load_tushare_sw_industry_breadth_contract(
        resolve_record_path(str(contract_link.get("path") or ""))
    )
    classification_codes = tuple(snapshot.get("classification_codes") or ())
    if (
        spec.get("version") != 1
        or spec.get("status")
        != "frozen_after_source_acceptance_before_full_membership_factor_values_or_factor_returns_observed"
        or spec.get("preregistered_at") != "2026-07-16T11:29:22Z"
        or evidence
        != {
            "source_acceptance_observed": True,
            "full_membership_snapshot_observed": False,
            "factor_values_observed": False,
            "close_known_comparison_values_observed_for_this_factor": False,
            "factor_returns_observed": False,
            "selection_or_promotion_performed": False,
        }
        or contract_link.get("sha256") != TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256
        or contract_link.get("preregistered_at") != contract.get("preregistered_at")
        or snapshot.get("dataset") != "tushare_sw2021_l1_membership"
        or snapshot.get("provider") != "tushare"
        or snapshot.get("membership_api") != "index_member_all"
        or tuple(snapshot.get("requested_fields") or ())
        != TUSHARE_SW_MEMBERSHIP_RAW_FIELDS
        or len(classification_codes) != 31
        or len(set(classification_codes)) != 31
        or tuple(sorted(classification_codes)) != classification_codes
        or tuple(snapshot.get("is_new_values") or ()) != ("Y", "N")
        or snapshot.get("expected_provider_calls") != 62
        or snapshot.get("provider_documented_maximum_rows_per_call") != 2000
        or snapshot.get("minimum_seconds_between_calls") != 0.32
        or snapshot.get("maximum_attempts_per_call") != 3
        or tuple(snapshot.get("retry_backoff_seconds") or ()) != (2, 5)
        or snapshot.get("requests_are_sequential") is not True
        or snapshot.get("partial_snapshot_accepted") is not False
        or snapshot.get("hidden_temporary_root_required") is not True
        or tuple(snapshot.get("canonical_columns") or ())
        != TUSHARE_SW_MEMBERSHIP_COLUMNS
        or snapshot.get("required_success_status")
        != "full_membership_snapshot_passed_pending_no_return_factor_capacity_and_uniqueness"
        or factor.get("factor_catalog") != ["sw1_three_session_leave_one_out_breadth"]
        or factor.get("direction") != "higher_is_better"
        or factor.get("minimum_other_valid_peers_each_session") != 10
        or factor.get("peer_minimum_listing_sessions") != 20
        or factor.get("stock_self_direction_included") is not False
        or factor.get("holding_universe") != "buyable_main_chinext"
        or factor.get("maximum_quality_age_days") != 550
        or factor.get("candidate_minimum_listing_sessions") != 20
        or capacity.get("development_start") != "2019-01-01"
        or capacity.get("development_end") != "2025-12-31"
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_eligible_names_per_cross_section") != 50
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or uniqueness.get("screen_start") != "2025-01-01"
        or uniqueness.get("screen_end") != "2025-12-31"
        or len(uniqueness.get("comparison_factors") or []) != 45
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or audit.get("forward_return_fields_read") is not False
        or audit.get("selection_or_promotion_allowed") is not False
        or spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare SW industry-breadth capacity preregistration is inconsistent"
        )

    context_paths: dict[str, Path] = {}
    for key in ("source_universe", "holding_universe", "local_calendar"):
        link = context.get(key) or {}
        source_path = resolve_record_path(str(link.get("path") or ""))
        if (
            not source_path.exists()
            or not link.get("file_sha256")
            or file_digest(source_path) != link.get("file_sha256")
        ):
            raise RichDataError(f"Tushare SW point-in-time {key} fingerprint mismatch")
        context_paths[key] = source_path
    quality = context.get("quarterly_quality") or {}
    for key, path_key, sha_key in (
        ("quarterly_quality", "path", "sha256"),
        ("quarterly_quality_manifest", "manifest_path", "manifest_sha256"),
    ):
        source_path = resolve_record_path(str(quality.get(path_key) or ""))
        if (
            not source_path.exists()
            or not quality.get(sha_key)
            or file_digest(source_path) != quality.get(sha_key)
        ):
            raise RichDataError(f"Tushare SW {key} fingerprint mismatch")
        context_paths[key] = source_path
    price_link = context.get("accepted_price_basis") or {}
    price_path = resolve_record_path(str(price_link.get("path") or ""))
    if not price_path.exists() or file_digest(price_path) != price_link.get("sha256"):
        raise RichDataError("Tushare SW accepted price-basis fingerprint mismatch")
    price_basis = load_json_record(price_path)
    if (
        price_basis.get("status") != price_link.get("status")
        or price_basis.get("price_basis") != price_link.get("price_basis")
        or price_basis.get("daily_sources") != price_link.get("daily_sources")
        or price_basis.get("future_corporate_actions_used")
        is not price_link.get("future_corporate_actions_used")
    ):
        raise RichDataError("Tushare SW accepted price-basis identity mismatch")
    context_paths["accepted_price_basis"] = price_path

    record_path = resolve_record_path(str(acceptance.get("record_path") or ""))
    manifest_path_value = resolve_record_path(
        str(acceptance.get("manifest_path") or "")
    )
    if (
        not record_path.exists()
        or file_digest(record_path) != acceptance.get("record_sha256")
        or not manifest_path_value.exists()
        or file_digest(manifest_path_value) != acceptance.get("manifest_sha256")
    ):
        raise RichDataError("Tushare SW source-acceptance fingerprint mismatch")
    record = load_json_record(
        record_path,
        kind="a_share_tushare_sw_industry_breadth_source_acceptance_record",
    )
    manifest = load_json_record(manifest_path_value, kind="a_share_rich_data_snapshot")
    files = {str(item.get("dataset")): item for item in manifest.get("files") or []}
    stored_frames = record.get("stored_frames") or {}
    source_quality = manifest.get("source_quality") or {}
    if (
        record.get("status")
        != "accepted_entitlement_schema_and_point_in_time_intervals_pending_full_membership_snapshot"
        or (record.get("data_contract") or {}).get("sha256")
        != TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256
        or (record.get("acceptance_manifest") or {}).get("sha256")
        != acceptance.get("manifest_sha256")
        or (
            (record.get("decision") or {}).get(
                "source_accepted_for_frozen_full_membership_snapshot"
            )
        )
        is not True
        or (
            (record.get("decision") or {}).get(
                "source_accepted_for_factor_construction_or_returns"
            )
        )
        is not False
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
        or manifest.get("dataset") != "tushare_sw2021_l1_acceptance"
        or manifest.get("provider") != "tushare"
        or manifest.get("run_id") != acceptance.get("run_id")
        or manifest.get("acceptance_status")
        != "accepted_entitlement_schema_and_point_in_time_intervals_pending_full_membership_snapshot"
        or (manifest.get("data_contract") or {}).get("sha256")
        != TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256
        or (manifest.get("source_request") or {}).get("classification_fields")
        != list(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS)
        or (manifest.get("source_request") or {}).get("membership_fields")
        != list(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS)
        or (manifest.get("source_request") or {}).get(
            "forbidden_fields_requested_or_stored"
        )
        != []
        or (manifest.get("source_request") or {}).get("credentials_logged_or_stored")
        is not False
        or manifest.get("price_fields_loaded") != []
        or manifest.get("factor_values_constructed") is not False
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
        or set(files) != {"classification", "membership"}
    ):
        raise RichDataError("Tushare SW source-acceptance identity mismatch")
    for key in ("classification", "membership"):
        record_frame = stored_frames.get(key) or {}
        manifest_frame = files[key]
        if (
            record_frame.get("path") != manifest_frame.get("path")
            or record_frame.get("sha256") != manifest_frame.get("sha256")
            or int(record_frame.get("rows") or -1)
            != int(manifest_frame.get("rows") or -2)
        ):
            raise RichDataError(f"Tushare SW accepted {key} frame identity mismatch")
    classification = load_snapshot_frame(files["classification"])
    membership = load_snapshot_frame(files["membership"])
    representative_l1 = str(contract["acceptance_protocol"]["representative_l1_code"])
    duplicate_key = list(contract["full_snapshot_contract"]["duplicate_event_key"])
    if (
        tuple(classification.columns) != TUSHARE_SW_CLASSIFICATION_RAW_FIELDS
        or len(classification) != int(acceptance.get("classification_rows") or -1)
        or tuple(classification["index_code"].astype(str)) != classification_codes
        or not classification["level"].eq("L1").all()
        or not classification["src"].eq("SW2021").all()
        or tuple(membership.columns) != TUSHARE_SW_MEMBERSHIP_COLUMNS
        or len(membership) != int(acceptance.get("membership_rows") or -1)
        or int(membership["is_new"].eq("Y").sum())
        != int(acceptance.get("current_membership_rows") or -1)
        or int(membership["is_new"].eq("N").sum())
        != int(acceptance.get("historical_membership_rows") or -1)
        or not membership["l1_code"].eq(representative_l1).all()
        or not membership["provider"].eq("tushare").all()
        or membership.duplicated(duplicate_key).any()
        or membership.loc[membership["is_new"].eq("Y"), "out_date"].notna().any()
        or membership.loc[membership["is_new"].eq("N"), "out_date"].isna().any()
        or source_quality.get("classification_codes") != list(classification_codes)
    ):
        raise RichDataError("Tushare SW accepted frame integrity audit failed")
    symbol_repair_path = DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR.resolve()
    symbol_repair = load_tushare_sw_industry_breadth_symbol_repair(symbol_repair_path)
    return {
        "spec_path": path,
        "spec": spec,
        "contract": contract,
        "record_path": record_path,
        "record": record,
        "manifest_path": manifest_path_value,
        "manifest": manifest,
        "classification": classification,
        "membership": membership,
        "context_paths": context_paths,
        "symbol_repair_path": symbol_repair_path,
        "symbol_repair": symbol_repair,
    }


def load_tushare_daily_pb_source_chain(
    path: Path = DEFAULT_TUSHARE_DAILY_PB_CAPACITY_SPEC,
) -> dict[str, Any]:
    """Verify the post-acceptance, pre-history PB evidence chain."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_DAILY_PB_CAPACITY_SPEC_SHA256:
        raise RichDataError(
            "Tushare daily PB capacity preregistration fingerprint mismatch"
        )
    spec = load_json_record(
        path, kind="a_share_tushare_daily_pb_capacity_preregistration"
    )
    contract_link = spec.get("data_contract") or {}
    acceptance = spec.get("source_acceptance") or {}
    required = spec.get("required_full_snapshot") or {}
    capacity = spec.get("capacity_contract") or {}
    uniqueness = spec.get("uniqueness_contract") or {}
    policy = spec.get("no_return_gate_policy") or {}
    contract = load_tushare_daily_pb_contract(
        resolve_record_path(str(contract_link.get("path") or ""))
    )
    if (
        spec.get("version") != 1
        or spec.get("status")
        != "frozen_after_single_session_acceptance_before_full_history_uniqueness_capacity_or_factor_returns_observed"
        or spec.get("preregistered_at") != "2026-07-16T10:05:41Z"
        or contract_link.get("sha256") != TUSHARE_DAILY_PB_CONTRACT_SHA256
        or contract_link.get("preregistered_at") != contract.get("preregistered_at")
        or tuple(spec.get("factor_catalog") or ())
        != ("tushare_positive_book_to_market",)
        or spec.get("factor_raw_columns")
        != {"tushare_positive_book_to_market": "tushare_positive_book_to_market"}
        or required.get("dataset") != "tushare_daily_pb"
        or required.get("provider") != "tushare"
        or required.get("acceptance_status")
        != "full_source_coverage_passed_pending_no_return_uniqueness_and_capacity"
        or tuple(required.get("required_partition_years") or ())
        != tuple(range(2019, 2026))
        or tuple(required.get("required_columns") or ()) != TUSHARE_DAILY_PB_COLUMNS
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_valid_names_per_factor_cohort") != 50
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("start") != "2025-01-01"
        or uniqueness.get("end") != "2025-12-31"
        or uniqueness.get("comparison_field_count") != 43
        or len(uniqueness.get("comparison_fields") or []) != 43
        or uniqueness.get("minimum_pairwise_names_per_session") != 50
        or uniqueness.get("minimum_pairwise_sessions_per_comparison") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or policy.get("capacity_must_run_before_close_known_comparison_fields")
        is not True
        or policy.get("both_capacity_and_uniqueness_must_pass") is not True
        or policy.get("one_completed_combined_audit_per_full_snapshot") is not True
        or spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare daily PB capacity preregistration is inconsistent")

    record_path = resolve_record_path(str(acceptance.get("record_path") or ""))
    manifest_path = resolve_record_path(str(acceptance.get("manifest_path") or ""))
    frame_path = resolve_record_path(str(acceptance.get("frame_path") or ""))
    if (
        not record_path.exists()
        or file_digest(record_path) != acceptance.get("record_sha256")
        or not manifest_path.exists()
        or file_digest(manifest_path) != acceptance.get("manifest_sha256")
        or not frame_path.exists()
        or file_digest(frame_path) != acceptance.get("frame_file_sha256")
    ):
        raise RichDataError("Tushare daily PB acceptance evidence fingerprint mismatch")
    record = load_json_record(
        record_path, kind="a_share_tushare_daily_pb_source_acceptance_record"
    )
    manifest = load_json_record(manifest_path, kind="a_share_rich_data_snapshot")
    files = list(manifest.get("files") or [])
    if (
        record.get("status") != "accepted_pending_full_history_uniqueness_and_capacity"
        or (record.get("acceptance_manifest") or {}).get("sha256")
        != acceptance.get("manifest_sha256")
        or manifest.get("dataset") != "tushare_daily_pb_acceptance"
        or manifest.get("provider") != "tushare"
        or manifest.get("requested_start") != acceptance.get("trade_date")
        or manifest.get("requested_end") != acceptance.get("trade_date")
        or manifest.get("acceptance_status")
        != "accepted_entitlement_formula_and_current_coverage_pending_full_history"
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
        or len(files) != 1
        or files[0].get("path") != str(acceptance.get("frame_path"))
        or files[0].get("sha256") != acceptance.get("frame_content_sha256")
        or int(files[0].get("rows") or -1) != int(acceptance.get("rows") or -2)
    ):
        raise RichDataError("Tushare daily PB acceptance evidence identity mismatch")
    frame = load_snapshot_frame(files[0])
    trade_date = pd.Timestamp(str(acceptance["trade_date"]))
    stored_dates = pd.to_datetime(frame["trade_date"], errors="coerce").dt.normalize()
    stored_pb = pd.to_numeric(frame["pb"], errors="coerce")
    stored_factor = pd.to_numeric(
        frame["tushare_positive_book_to_market"], errors="coerce"
    )
    if (
        tuple(frame.columns) != TUSHARE_DAILY_PB_COLUMNS
        or len(frame) != int(acceptance["rows"])
        or stored_dates.isna().any()
        or not stored_dates.eq(trade_date).all()
        or frame["instrument"].astype("string").isna().any()
        or frame["instrument"].nunique() != len(frame)
        or not stored_pb.gt(0.0).all()
        or not np.isfinite(stored_factor).all()
        or not np.allclose(
            stored_factor.to_numpy(dtype="float64"),
            1.0 / stored_pb.to_numpy(dtype="float64"),
            rtol=0.0,
            atol=1e-12,
        )
        or not frame["provider"].eq("tushare").all()
    ):
        raise RichDataError("Tushare daily PB acceptance formula audit failed")
    return {
        "spec_path": path,
        "spec": spec,
        "record_path": record_path,
        "record": record,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "frame_path": frame_path,
    }


def load_baostock_5m_contract(
    path: Path = DEFAULT_BAOSTOCK_5M_CONTRACT,
) -> dict[str, Any]:
    """Load the frozen post-probe, pre-acceptance BaoStock contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != BAOSTOCK_5M_CONTRACT_SHA256:
        raise RichDataError("BaoStock five-minute contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_baostock_5m_data_contract")
    source = contract.get("source") or {}
    timestamp = contract.get("timestamp_contract") or {}
    acceptance = contract.get("formal_acceptance") or {}
    bulk = contract.get("bulk_snapshot_contract") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_after_no_return_feasibility_probe_before_formal_acceptance_bulk_snapshot_or_factor_values"
        or contract.get("frozen_at") != "2026-07-14T20:57:08Z"
        or source.get("provider") != "baostock"
        or source.get("sdk_version") != "0.9.3"
        or source.get("source_frequency") != "5"
        or source.get("canonical_frequency") != "5m"
        or source.get("adjustflag") != "3"
        or source.get("requested_fields")
        != [
            "date",
            "time",
            "code",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "adjustflag",
        ]
        or timestamp.get("source_label") != "bar_end"
        or timestamp.get("expected_bars_per_complete_regular_session") != 48
        or acceptance.get("trade_date") != "2026-07-10"
        or acceptance.get("symbols") != ["600519", "000001", "300750", "688981"]
        or acceptance.get("required_rows_per_symbol") != 48
        or acceptance.get("raw_ohlc_max_relative_error_to_local_raw_daily") != 0.002
        or bulk.get("development_start") != "2020-01-01"
        or bulk.get("development_end") != "2025-12-31"
        or bulk.get("minimum_potential_non_overlapping_three_session_cohorts") != 200
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "BaoStock five-minute contract does not match the frozen protocol"
        )
    return contract


def load_factor_universe_intervals(
    path: Path = DEFAULT_FACTOR_UNIVERSE,
) -> pd.DataFrame:
    """Read point-in-time instrument intervals without loading any price field."""

    path = path.expanduser().resolve()
    if not path.exists():
        raise RichDataError(f"factor universe does not exist: {path}")
    frame = pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=["instrument", "start_date", "end_date"],
        dtype={"instrument": "string"},
    )
    frame["start_date"] = pd.to_datetime(
        frame["start_date"], errors="coerce"
    ).dt.normalize()
    frame["end_date"] = pd.to_datetime(
        frame["end_date"], errors="coerce"
    ).dt.normalize()
    valid_symbols = frame["instrument"].str.fullmatch(r"(?:SH6|SZ[03])\d{5}", na=False)
    if (
        frame.empty
        or frame[["start_date", "end_date"]].isna().any().any()
        or (~valid_symbols).any()
        or frame["instrument"].duplicated().any()
        or frame["start_date"].gt(frame["end_date"]).any()
    ):
        raise RichDataError("factor universe contains invalid or duplicate intervals")
    return frame.sort_values("instrument", kind="stable").reset_index(drop=True)


def local_calendar_dates(
    start: dt.date,
    end: dt.date,
    path: Path = DEFAULT_LOCAL_CALENDAR,
) -> pd.DatetimeIndex:
    """Read the local calendar without touching daily prices."""

    path = path.expanduser().resolve()
    if not path.exists():
        raise RichDataError(f"local calendar does not exist: {path}")
    values = pd.to_datetime(
        path.read_text(encoding="utf-8").splitlines(), errors="coerce"
    )
    if pd.isna(values).any():
        raise RichDataError("local calendar contains an invalid date")
    calendar = pd.DatetimeIndex(values).normalize().unique().sort_values()
    return calendar[(calendar >= pd.Timestamp(start)) & (calendar <= pd.Timestamp(end))]


def atomic_write_frame(frame: pd.DataFrame, destination: Path) -> None:
    """Write one Parquet snapshot atomically."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, suffix=".parquet", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        frame.to_parquet(temporary, index=False)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(payload: dict[str, Any], destination: Path) -> None:
    """Write a manifest atomically."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, suffix=".json", mode="w", encoding="utf-8", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def new_run_id(prefix: str) -> str:
    """Create a chronological, collision-resistant snapshot identifier."""

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{now}_{prefix}_{uuid.uuid4().hex[:8]}"


def manifest_path(path: Path) -> str:
    """Use repository-relative paths in production and absolute paths in tests."""

    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def write_minute_snapshot(
    provider: str,
    frequency: str,
    start: dt.date,
    end: dt.date,
    rows_by_code: dict[str, pd.DataFrame],
    acceptance_by_code: dict[str, dict[str, Any]] | None = None,
    data_contract: dict[str, Any] | None = None,
) -> Path:
    """Persist one immutable minute-data snapshot and its complete manifest."""

    run_id = new_run_id(f"{provider}_{frequency}")
    run_root = RAW_ROOT / provider / "minutes" / frequency / "snapshots" / run_id
    files: list[dict[str, Any]] = []
    for code, frame in rows_by_code.items():
        destination = run_root / f"{qlib_symbol(code).lower()}.parquet"
        atomic_write_frame(frame, destination)
        files.append(
            {
                "code": code,
                "symbol": qlib_symbol(code),
                "path": manifest_path(destination),
                "rows": int(len(frame)),
                "sha256": frame_digest(frame),
                "daily_summary": minute_daily_summary(frame),
                "acceptance": (acceptance_by_code or {}).get(code),
            }
        )
    manifest = {
        "kind": "a_share_rich_data_snapshot",
        "dataset": "minutes",
        "provider": provider,
        "frequency": frequency,
        "prices": "raw_unadjusted",
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_id": run_id,
        "files": files,
        "acceptance_status": (
            "automatic_checks_passed_pending_time_alignment"
            if acceptance_by_code
            and all(
                report["status"].startswith("automatic_checks_passed")
                for report in acceptance_by_code.values()
            )
            else "not_run"
            if acceptance_by_code is None
            else "automatic_checks_failed"
        ),
    }
    if data_contract is not None:
        manifest["data_contract"] = data_contract
    run_manifest_path = RUNS_ROOT / f"{run_id}.json"
    atomic_write_json(manifest, run_manifest_path)
    return run_manifest_path


def expected_minute_times(bar_label: str, frequency: str = "1m") -> tuple[dt.time, ...]:
    """Return exact regular-session timestamps for one supported bar contract."""

    if bar_label not in {"start", "end"}:
        raise RichDataError("bar label must be 'start' or 'end'")
    if frequency not in MINUTE_EXPECTED_BARS_BY_FREQUENCY:
        raise RichDataError(f"unsupported alignment frequency: {frequency}")
    minutes = int(frequency.removesuffix("m"))
    bars_per_half = 120 // minutes
    anchor = pd.Timestamp("2000-01-03")
    bar_ends = pd.DatetimeIndex(
        [
            *pd.date_range(
                anchor + pd.Timedelta(hours=9, minutes=30 + minutes),
                periods=bars_per_half,
                freq=f"{minutes}min",
            ),
            *pd.date_range(
                anchor + pd.Timedelta(hours=13, minutes=minutes),
                periods=bars_per_half,
                freq=f"{minutes}min",
            ),
        ]
    )
    timestamps = bar_ends - (
        pd.Timedelta(minutes=minutes) if bar_label == "start" else pd.Timedelta(0)
    )
    return tuple(value.time() for value in timestamps)


def load_snapshot_frame(file_record: dict[str, Any]) -> pd.DataFrame:
    """Read and fingerprint one immutable snapshot file."""

    path_value = file_record.get("path")
    if not path_value:
        raise RichDataError("snapshot file record has no path")
    path = resolve_record_path(str(path_value))
    if not path.exists():
        raise RichDataError(f"snapshot data file does not exist: {path}")
    frame = pd.read_parquet(path)
    expected = str(file_record.get("sha256") or "")
    observed = frame_digest(frame)
    if not expected or observed != expected:
        raise RichDataError(f"snapshot data fingerprint mismatch: {path}")
    return frame


def confirmation_volume_units(snapshot: dict[str, Any]) -> set[str]:
    """Collect only volume units inferred by passed daily reconciliation rows."""

    units: set[str] = set()
    for file_record in snapshot.get("files") or []:
        acceptance = file_record.get("acceptance") or {}
        reconciliation = acceptance.get("daily_reconciliation") or {}
        for day in reconciliation.get("days") or []:
            if day.get("status") == "passed" and day.get("inferred_volume_unit") in {
                "shares",
                "lots",
            }:
                units.add(str(day["inferred_volume_unit"]))
    return units


def confirm_minute_alignment(
    snapshot_path: Path,
    *,
    bar_label: str,
    volume_unit: str,
    reviewed_boundaries: bool,
    output: Path | None = None,
) -> Path:
    """Write an append-only provider alignment confirmation.

    The source snapshot remains immutable.  This record binds the explicit
    operator review to its manifest fingerprint and can later authorize bulk
    snapshots from only the same provider/frequency contract.
    """

    if not reviewed_boundaries:
        raise RichDataError(
            "pass --reviewed-boundaries only after checking the first and last minute labels"
        )
    if bar_label not in {"start", "end"}:
        raise RichDataError("bar label must be 'start' or 'end'")
    if volume_unit not in {"shares", "lots"}:
        raise RichDataError("volume unit must be 'shares' or 'lots'")
    snapshot_path = snapshot_path.expanduser().resolve()
    snapshot = load_json_record(snapshot_path, kind="a_share_rich_data_snapshot")
    frequency = str(snapshot.get("frequency") or "")
    if (
        snapshot.get("dataset") != "minutes"
        or frequency not in MINUTE_EXPECTED_BARS_BY_FREQUENCY
    ):
        raise RichDataError(
            "minute alignment confirmation requires a supported minute snapshot"
        )
    if (
        snapshot.get("acceptance_status")
        != "automatic_checks_passed_pending_time_alignment"
    ):
        raise RichDataError(
            "minute snapshot has not passed automatic acceptance checks"
        )
    files = list(snapshot.get("files") or [])
    if not files:
        raise RichDataError("minute snapshot contains no files")

    expected_times = expected_minute_times(bar_label, frequency)
    expected_bars = MINUTE_EXPECTED_BARS_BY_FREQUENCY[frequency]
    complete_session_evidence: list[dict[str, Any]] = []
    for file_record in files:
        frame = load_snapshot_frame(file_record)
        if frame.empty:
            continue
        required = {
            "datetime",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "provider",
        }
        if missing := sorted(required - set(frame.columns)):
            raise RichDataError(
                "minute snapshot file is missing canonical columns: "
                + ", ".join(missing)
            )
        timestamps = pd.to_datetime(frame["datetime"], errors="coerce")
        if timestamps.isna().any():
            raise RichDataError("minute snapshot contains an invalid timestamp")
        providers = set(frame["provider"].dropna().astype(str))
        if providers != {str(snapshot["provider"])}:
            raise RichDataError(
                f"minute snapshot contains an unexpected provider: {sorted(providers)}"
            )
        work = frame.assign(_datetime=timestamps, _trade_date=timestamps.dt.normalize())
        for trade_date, group in work.groupby("_trade_date", sort=True):
            observed_times = tuple(group.sort_values("_datetime")["_datetime"].dt.time)
            if len(observed_times) == expected_bars:
                if observed_times != expected_times:
                    raise RichDataError(
                        f"declared {bar_label}-label convention conflicts with a {expected_bars}-bar session on "
                        f"{pd.Timestamp(trade_date).date().isoformat()}"
                    )
                complete_session_evidence.append(
                    {
                        "symbol": str(group["symbol"].iloc[0]),
                        "trade_date": pd.Timestamp(trade_date).date().isoformat(),
                        "first_bar": group.sort_values("_datetime")["_datetime"]
                        .iloc[0]
                        .isoformat(),
                        "last_bar": group.sort_values("_datetime")["_datetime"]
                        .iloc[-1]
                        .isoformat(),
                    }
                )
    if not complete_session_evidence:
        raise RichDataError(
            f"alignment confirmation needs at least one exact {expected_bars}-bar session as boundary evidence"
        )
    inferred_units = confirmation_volume_units(snapshot)
    if inferred_units != {volume_unit}:
        raise RichDataError(
            "declared volume unit conflicts with automatic reconciliation: "
            f"declared={volume_unit}, inferred={sorted(inferred_units)}"
        )

    interval_minutes = int(frequency.removesuffix("m"))
    run_id = new_run_id(f"{snapshot['provider']}_{frequency}_alignment")
    record = {
        "schema_version": 1,
        "kind": "a_share_minute_alignment_confirmation",
        "status": "passed_for_feature_research",
        "run_id": run_id,
        "confirmed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": snapshot["provider"],
        "frequency": frequency,
        "bar_timestamp_label": bar_label,
        "normalization_to_bar_end": (
            f"add_{interval_minutes}_minutes" if bar_label == "start" else "identity"
        ),
        "volume_unit": volume_unit,
        "reviewed_boundaries": True,
        "complete_session_evidence": complete_session_evidence,
        "source_acceptance_snapshot": {
            "path": manifest_path(snapshot_path),
            "sha256": file_digest(snapshot_path),
            "run_id": snapshot.get("run_id"),
        },
        "forward_return_fields_read": False,
        "limitations": [
            "This confirms timestamp and volume-unit semantics only; it does not validate a factor or strategy.",
            "Missing or halted minute bars remain missing and must never be zero-filled.",
        ],
    }
    destination = (
        output.expanduser().resolve()
        if output is not None
        else ALIGNMENTS_ROOT / f"{run_id}.json"
    )
    if destination.exists():
        raise RichDataError(f"alignment confirmation already exists: {destination}")
    atomic_write_json(record, destination)
    return destination


def load_minute_factor_spec(path: Path = DEFAULT_MINUTE_FACTOR_SPEC) -> dict[str, Any]:
    """Load the frozen minute-factor preregistration and enforce its catalog."""

    path = path.expanduser().resolve()
    spec = load_json_record(path, kind="a_share_minute_factor_preregistration")
    features = list(spec.get("features") or [])
    names = tuple(str(item.get("name")) for item in features if isinstance(item, dict))
    directions = tuple(
        str(item.get("diagnostic_direction"))
        for item in features
        if isinstance(item, dict)
    )
    minute_contract = spec.get("minute_contract") or {}
    holding_protocol = spec.get("holding_protocol") or {}
    contract_ok = (
        spec.get("version") == 1
        and spec.get("status") == "frozen_before_minute_data_observed"
        and names == MINUTE_FEATURE_NAMES
        and directions == MINUTE_FEATURE_DIRECTIONS
        and minute_contract.get("frequency") == "1m"
        and minute_contract.get("prices") == "raw_unadjusted"
        and minute_contract.get("timestamp_normalized_to") == "bar_end"
        and minute_contract.get("complete_regular_session_required") is True
        and minute_contract.get("expected_regular_session_bars")
        == MINUTE_FEATURE_EXPECTED_BARS
        and holding_protocol.get("holding_period_trading_days") == 3
        and holding_protocol.get("non_overlapping_cohorts") is True
        and holding_protocol.get("topk") == 3
        and holding_protocol.get("open_cost") == 0.00012
        and holding_protocol.get("close_cost") == 0.00062
    )
    if not contract_ok:
        raise RichDataError(
            "minute factor preregistration does not match the frozen v1 feature catalog"
        )
    if (
        spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "minute factor preregistration must exclude forward returns and promotion"
        )
    return spec


def load_baostock_5m_factor_spec(
    path: Path = DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
) -> dict[str, Any]:
    """Load the immutable post-acceptance, pre-factor-value five-minute spec."""

    path = path.expanduser().resolve()
    if file_digest(path) != BAOSTOCK_5M_FACTOR_SPEC_SHA256:
        raise RichDataError(
            "BaoStock five-minute factor preregistration fingerprint mismatch"
        )
    spec = load_json_record(path, kind="a_share_baostock_5m_factor_preregistration")
    source_chain = spec.get("source_chain") or {}
    contract_link = source_chain.get("data_contract") or {}
    acceptance_link = source_chain.get("acceptance_snapshot") or {}
    alignment_link = source_chain.get("alignment_confirmation") or {}
    minute_contract = spec.get("minute_contract") or {}
    features = list(spec.get("features") or [])
    names = tuple(str(item.get("name")) for item in features if isinstance(item, dict))
    directions = tuple(
        str(item.get("diagnostic_direction"))
        for item in features
        if isinstance(item, dict)
    )
    development = spec.get("development_protocol") or {}
    coverage = spec.get("coverage_gate_before_forward_returns") or {}
    if (
        spec.get("version") != 1
        or spec.get("status")
        != "frozen_after_source_acceptance_before_five_minute_factor_values_or_forward_returns"
        or spec.get("preregistered_at") != "2026-07-14T21:02:19Z"
        or contract_link.get("sha256") != BAOSTOCK_5M_CONTRACT_SHA256
        or acceptance_link.get("sha256")
        != "e3d2160fab34c3a51b1524623a7c14f800abdc75164a66f0371386cf29ac68cd"
        or alignment_link.get("sha256")
        != "cf50051d254a3fcc2727d649b167ed053bbba2e2b3dfa2c939fae04166b54c6c"
        or names != BAOSTOCK_5M_FEATURE_NAMES
        or directions != BAOSTOCK_5M_FEATURE_DIRECTIONS
        or minute_contract.get("provider") != "baostock"
        or minute_contract.get("frequency") != "5m"
        or minute_contract.get("prices") != "raw_unadjusted"
        or minute_contract.get("timestamp_normalized_to") != "bar_end"
        or minute_contract.get("complete_regular_session_required") is not True
        or minute_contract.get("expected_regular_session_bars") != 48
        or development.get("start") != "2020-01-01"
        or development.get("end") != "2025-12-31"
        or development.get("holding_period_trading_days") != 3
        or development.get("non_overlapping_cohorts") is not True
        or development.get("topk") != 3
        or development.get("open_cost") != 0.00012
        or development.get("close_cost") != 0.00062
        or coverage.get("minimum_potential_non_overlapping_three_session_cohorts")
        != 200
        or spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "BaoStock five-minute factor preregistration does not match the frozen protocol"
        )
    return spec


def load_baostock_5m_source_chain(
    factor_spec_path: Path = DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
) -> dict[str, Any]:
    """Fingerprint-validate the contract, acceptance and alignment records."""

    spec = load_baostock_5m_factor_spec(factor_spec_path)
    contract = load_baostock_5m_contract()
    chain = spec["source_chain"]
    acceptance_link = chain["acceptance_snapshot"]
    alignment_link = chain["alignment_confirmation"]
    acceptance_path = resolve_record_path(acceptance_link["path"])
    alignment_path = resolve_record_path(alignment_link["path"])
    if (
        not acceptance_path.exists()
        or file_digest(acceptance_path) != acceptance_link["sha256"]
    ):
        raise RichDataError("BaoStock five-minute acceptance fingerprint mismatch")
    if (
        not alignment_path.exists()
        or file_digest(alignment_path) != alignment_link["sha256"]
    ):
        raise RichDataError("BaoStock five-minute alignment fingerprint mismatch")
    acceptance = load_json_record(acceptance_path, kind="a_share_rich_data_snapshot")
    alignment = load_json_record(
        alignment_path, kind="a_share_minute_alignment_confirmation"
    )
    expected_symbols = {
        qlib_symbol(code) for code in contract["formal_acceptance"]["symbols"]
    }
    observed_symbols = {
        str(item.get("symbol")) for item in (acceptance.get("files") or [])
    }
    if (
        acceptance.get("provider") != "baostock"
        or acceptance.get("frequency") != "5m"
        or acceptance.get("prices") != "raw_unadjusted"
        or acceptance.get("acceptance_status")
        != "automatic_checks_passed_pending_time_alignment"
        or (acceptance.get("data_contract") or {}).get("sha256")
        != BAOSTOCK_5M_CONTRACT_SHA256
        or observed_symbols != expected_symbols
        or any(
            int(item.get("rows") or 0) != 48 for item in (acceptance.get("files") or [])
        )
        or alignment.get("status") != "passed_for_feature_research"
        or alignment.get("provider") != "baostock"
        or alignment.get("frequency") != "5m"
        or alignment.get("bar_timestamp_label") != "end"
        or alignment.get("volume_unit") != "shares"
        or resolve_record_path(
            (alignment.get("source_acceptance_snapshot") or {}).get("path") or ""
        )
        != acceptance_path
        or (alignment.get("source_acceptance_snapshot") or {}).get("sha256")
        != acceptance_link["sha256"]
    ):
        raise RichDataError(
            "BaoStock five-minute source chain violates the frozen protocol"
        )
    for file_record in acceptance.get("files") or []:
        frame = load_snapshot_frame(file_record)
        report = file_record.get("acceptance") or {}
        exact = report.get("baostock_5m_contract") or {}
        if (
            report.get("status") != "automatic_checks_passed_pending_time_alignment"
            or exact.get("exact_timestamp_grid_passed") is not True
            or (report.get("daily_reconciliation") or {}).get("status") != "passed"
        ):
            raise RichDataError(
                "BaoStock five-minute acceptance file failed its frozen checks"
            )
        if len(frame) != 48:
            raise RichDataError(
                "BaoStock five-minute acceptance data no longer has 48 rows"
            )
    return {
        "contract": contract,
        "factor_spec": spec,
        "acceptance_path": acceptance_path,
        "acceptance": acceptance,
        "alignment_path": alignment_path,
        "alignment": alignment,
    }


def load_baostock_5m_suspension_audit(
    path: Path = DEFAULT_BAOSTOCK_5M_SUSPENSION_AUDIT,
) -> dict[str, Any]:
    """Validate the frozen treatment of BaoStock zero-price suspension rows."""

    path = path.expanduser().resolve()
    if file_digest(path) != BAOSTOCK_5M_SUSPENSION_AUDIT_SHA256:
        raise RichDataError(
            "BaoStock five-minute suspension audit fingerprint mismatch"
        )
    audit = load_json_record(
        path, kind="a_share_baostock_5m_suspension_placeholder_audit"
    )
    failure = audit.get("failed_full_attempt") or {}
    raw = audit.get("isolated_raw_partition_audit") or {}
    policy = audit.get("frozen_normalization_and_eligibility_treatment") or {}
    verification = audit.get("post_change_partition_verification") or {}
    if (
        audit.get("status")
        != "resolved_within_frozen_missing_or_halted_session_policy_before_full_retry"
        or (failure.get("failed_partition") or {}).get("code") != "600027"
        or (failure.get("failed_partition") or {}).get("year") != 2024
        or failure.get("temporary_snapshot_deleted") is not True
        or failure.get("final_snapshot_written") is not False
        or raw.get("source_rows") != 11616
        or raw.get("zero_price_zero_volume_zero_amount_placeholder_rows") != 478
        or raw.get("placeholder_stock_sessions") != 10
        or policy.get("silent_deduplication") is not False
        or policy.get("fill_interpolate_or_borrow_another_source") is not False
        or verification.get("canonical_rows_written") != 11138
        or verification.get("complete_regular_positive_activity_sessions") != 232
        or audit.get("forward_return_fields_read") is not False
        or audit.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "BaoStock five-minute suspension audit violates its frozen protocol"
        )
    return audit


def load_baostock_5m_throttle_audit(
    path: Path = DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT,
) -> dict[str, Any]:
    """Validate the frozen low-call-count plan after anonymous throttling."""

    path = path.expanduser().resolve()
    if file_digest(path) != BAOSTOCK_5M_THROTTLE_AUDIT_SHA256:
        raise RichDataError("BaoStock five-minute throttle audit fingerprint mismatch")
    audit = load_json_record(path, kind="a_share_baostock_5m_request_throttle_audit")
    failure = audit.get("failed_attempt") or {}
    probe = audit.get("single_post_failure_probe") or {}
    plan = audit.get("frozen_reduced_request_plan") or {}
    if (
        audit.get("status") != "request_plan_reduced_before_any_post_blacklist_retry"
        or failure.get("planned_provider_requests") != 29246
        or failure.get("reported_partitions_completed_before_failure") != 9000
        or (failure.get("failed_request") or {}).get("provider_error")
        != "黑名单用户，请与管理员联系"
        or failure.get("temporary_snapshot_deleted") is not True
        or failure.get("final_snapshot_written") is not False
        or probe.get("login_status") != "rejected"
        or probe.get("history_query_issued") is not False
        or plan.get("provider_requests") != 5386
        or plan.get("yearly_parquet_storage_partitions") != 29246
        or plan.get("blacklist_error_is_immediately_fatal_without_retry") is not True
        or plan.get("partial_resume_allowed") is not False
        or audit.get("forward_return_fields_read") is not False
        or audit.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "BaoStock five-minute throttle audit violates its frozen protocol"
        )
    return audit


def require_baostock_5m_runtime() -> None:
    """Require the exact anonymous SDK version frozen by the source contract."""

    require_provider("baostock")
    try:
        version = importlib.metadata.version("baostock")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RichDataError("BaoStock SDK metadata is unavailable") from exc
    if version != "0.9.3":
        raise RichDataError(
            f"BaoStock five-minute sync requires baostock==0.9.3, found {version}"
        )


def baostock_5m_partition_tasks(
    intervals: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> list[tuple[str, str, str, int]]:
    """Split point-in-time instrument intervals into calendar-year storage partitions."""

    tasks: list[tuple[str, str, str, int]] = []
    range_start = pd.Timestamp(start)
    range_end = pd.Timestamp(end)
    for row in intervals.itertuples(index=False):
        interval_start = max(pd.Timestamp(row.start_date), range_start)
        interval_end = min(pd.Timestamp(row.end_date), range_end)
        if interval_start > interval_end:
            continue
        code = str(row.instrument)[2:]
        for year in range(interval_start.year, interval_end.year + 1):
            partition_start = max(
                interval_start, pd.Timestamp(year=year, month=1, day=1)
            )
            partition_end = min(interval_end, pd.Timestamp(year=year, month=12, day=31))
            tasks.append(
                (
                    code,
                    partition_start.date().isoformat(),
                    partition_end.date().isoformat(),
                    year,
                )
            )
    keys = [(code, year) for code, _, _, year in tasks]
    if len(keys) != len(set(keys)):
        raise RichDataError(
            "BaoStock five-minute point-in-time tasks contain duplicate symbol-years"
        )
    return tasks


def baostock_5m_request_tasks(
    intervals: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> list[tuple[str, str, str]]:
    """Create one low-rate provider request for each clipped PIT instrument interval."""

    tasks: list[tuple[str, str, str]] = []
    range_start = pd.Timestamp(start)
    range_end = pd.Timestamp(end)
    for row in intervals.itertuples(index=False):
        interval_start = max(pd.Timestamp(row.start_date), range_start)
        interval_end = min(pd.Timestamp(row.end_date), range_end)
        if interval_start > interval_end:
            continue
        tasks.append(
            (
                str(row.instrument)[2:],
                interval_start.date().isoformat(),
                interval_end.date().isoformat(),
            )
        )
    codes = [code for code, _, _ in tasks]
    if len(codes) != len(set(codes)):
        raise RichDataError(
            "BaoStock five-minute provider requests contain duplicate symbols"
        )
    return tasks


def split_baostock_5m_request_frame(
    frame: pd.DataFrame,
    storage_tasks: list[tuple[str, str, str, int]],
) -> Iterable[tuple[tuple[str, str, str, int], pd.DataFrame]]:
    """Split one instrument response into the frozen yearly Parquet partitions."""

    source_by_year = {
        int(year): int(count)
        for year, count in frame.attrs.get("source_rows_by_year", {}).items()
    }
    placeholders_by_year = {
        int(year): int(count)
        for year, count in frame.attrs.get(
            "zero_price_placeholder_rows_by_year", {}
        ).items()
    }
    placeholder_dates = [
        str(value)
        for value in frame.attrs.get("zero_price_placeholder_session_dates", [])
    ]
    timestamps = (
        pd.to_datetime(frame["datetime"], errors="coerce")
        if not frame.empty
        else pd.Series([], dtype="datetime64[ns]")
    )
    if not source_by_year and not frame.empty:
        source_by_year = {
            int(year): int(count)
            for year, count in timestamps.dt.year.value_counts().items()
        }
    for task in storage_tasks:
        _, start_value, end_value, year = task
        if frame.empty:
            partition = frame.copy()
        else:
            in_partition = timestamps.ge(pd.Timestamp(start_value)) & timestamps.lt(
                pd.Timestamp(end_value) + pd.Timedelta(days=1)
            )
            partition = frame.loc[in_partition].copy().reset_index(drop=True)
        year_placeholder_dates = [
            value for value in placeholder_dates if pd.Timestamp(value).year == year
        ]
        partition.attrs["source_rows"] = source_by_year.get(year, 0)
        partition.attrs["source_rows_by_year"] = {year: source_by_year.get(year, 0)}
        partition.attrs["zero_price_placeholder_rows_excluded"] = (
            placeholders_by_year.get(year, 0)
        )
        partition.attrs["zero_price_placeholder_rows_by_year"] = {
            year: placeholders_by_year.get(year, 0)
        }
        partition.attrs["zero_price_placeholder_session_dates"] = year_placeholder_dates
        yield task, partition


def validate_baostock_5m_partition(
    frame: pd.DataFrame,
    task: tuple[str, str, str, int],
    calendar: pd.DatetimeIndex,
) -> list[str]:
    """Validate one raw partition and return its exact complete-session dates."""

    code, start_value, end_value, year = task
    required = {
        "datetime",
        "symbol",
        "source_symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "provider",
    }
    if missing := sorted(required - set(frame.columns)):
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition is missing columns: "
            + ", ".join(missing)
        )
    if frame.empty:
        return []
    timestamps = pd.to_datetime(frame["datetime"], errors="coerce")
    if timestamps.isna().any() or timestamps.duplicated().any():
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition has invalid or duplicate timestamps"
        )
    if not timestamps.is_monotonic_increasing:
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition is not sorted"
        )
    start_timestamp = pd.Timestamp(start_value)
    end_timestamp = pd.Timestamp(end_value) + pd.Timedelta(days=1)
    if timestamps.lt(start_timestamp).any() or timestamps.ge(end_timestamp).any():
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition escaped its task range"
        )
    expected_symbol = qlib_symbol(code)
    if (
        set(frame["symbol"].astype(str)) != {expected_symbol}
        or set(frame["source_symbol"].astype(str)) != {vendor_symbol(code, "baostock")}
        or set(frame["provider"].astype(str)) != {"baostock"}
    ):
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition identity mismatch"
        )
    calendar_dates = set(pd.DatetimeIndex(calendar).normalize())
    observed_dates = set(timestamps.dt.normalize())
    if not observed_dates.issubset(calendar_dates):
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition contains non-local-calendar dates"
        )
    expected_times = expected_minute_times("end", "5m")
    expected_time_set = set(expected_times)
    if not set(timestamps.dt.time).issubset(expected_time_set):
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition violates the frozen end-label grid"
        )
    complete_dates: list[str] = []
    work = frame.assign(_trade_date=timestamps.dt.normalize())
    for trade_date, group in work.groupby("_trade_date", sort=True):
        observed_times = tuple(pd.to_datetime(group["datetime"]).dt.time)
        if len(group) > len(expected_times):
            raise RichDataError(
                f"BaoStock five-minute {code} {trade_date.date()} has too many bars"
            )
        positive_activity = (
            pd.to_numeric(group["volume"], errors="coerce").sum() > 0.0
            and pd.to_numeric(group["amount"], errors="coerce").sum() > 0.0
        )
        if observed_times == expected_times and positive_activity:
            complete_dates.append(trade_date.date().isoformat())
    return complete_dates


def baostock_5m_coverage_report(
    intervals: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    complete_counts: dict[str, int],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Compute the frozen no-return point-in-time coverage and capacity gates."""

    active_counts = np.zeros(len(calendar), dtype=np.int64)
    for row in intervals.itertuples(index=False):
        left = int(calendar.searchsorted(pd.Timestamp(row.start_date), side="left"))
        right = int(calendar.searchsorted(pd.Timestamp(row.end_date), side="right"))
        if right > left:
            active_counts[left:right] += 1
    completed = np.asarray(
        [int(complete_counts.get(value.date().isoformat(), 0)) for value in calendar],
        dtype=np.int64,
    )
    if (completed > active_counts).any():
        raise RichDataError(
            "BaoStock five-minute complete-session count exceeds the PIT universe"
        )
    ratios = np.divide(
        completed,
        active_counts,
        out=np.full(len(calendar), np.nan, dtype=float),
        where=active_counts > 0,
    )
    valid_ratios = ratios[np.isfinite(ratios)]
    if valid_ratios.size == 0:
        raise RichDataError(
            "BaoStock five-minute coverage has no active PIT-universe sessions"
        )
    bulk = contract["bulk_snapshot_contract"]
    potential_indices = np.arange(0, max(len(calendar) - 3, 0), 3, dtype=int)
    potential_cohorts = int(
        (
            completed[potential_indices]
            >= int(bulk["minimum_names_per_factor_cross_section"])
        ).sum()
    )
    median_coverage = float(np.median(valid_ratios))
    p05_coverage = float(np.quantile(valid_ratios, 0.05))
    gate_passed = (
        median_coverage >= float(bulk["median_eligible_universe_coverage_min"])
        and p05_coverage >= float(bulk["p05_eligible_universe_coverage_min"])
        and potential_cohorts
        >= int(bulk["minimum_potential_non_overlapping_three_session_cohorts"])
    )
    return {
        "calendar_sessions": int(len(calendar)),
        "median_eligible_universe_coverage": median_coverage,
        "p05_eligible_universe_coverage": p05_coverage,
        "dates_with_at_least_fifty_complete_names": int(
            (completed >= int(bulk["minimum_names_per_factor_cross_section"])).sum()
        ),
        "potential_non_overlapping_three_session_cohorts": potential_cohorts,
        "gate_passed_before_prices": gate_passed,
        "daily": [
            {
                "trade_date": value.date().isoformat(),
                "active_pit_names": int(active),
                "complete_five_minute_names": int(complete),
                "eligible_universe_coverage": (
                    float(ratio) if np.isfinite(ratio) else None
                ),
            }
            for value, active, complete, ratio in zip(
                calendar, active_counts, completed, ratios, strict=True
            )
        ],
    }


def write_baostock_5m_preflight(
    *,
    data_root: Path = DATA_ROOT,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
    factor_spec_path: Path = DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
) -> Path:
    """Record a source-chain and storage audit without issuing a network request."""

    source_chain = load_baostock_5m_source_chain(factor_spec_path)
    load_baostock_5m_suspension_audit()
    load_baostock_5m_throttle_audit()
    require_baostock_5m_runtime()
    contract = source_chain["contract"]
    bulk = contract["bulk_snapshot_contract"]
    start = dt.date.fromisoformat(str(bulk["development_start"]))
    end = dt.date.fromisoformat(str(bulk["development_end"]))
    intervals = load_factor_universe_intervals(universe_path)
    calendar = local_calendar_dates(start, end, calendar_path)
    if calendar.empty:
        raise RichDataError(
            "local calendar has no sessions in the BaoStock five-minute range"
        )
    storage_tasks = baostock_5m_partition_tasks(intervals, start, end)
    request_tasks = baostock_5m_request_tasks(intervals, start, end)
    if not storage_tasks or not request_tasks:
        raise RichDataError("factor universe has no BaoStock five-minute partitions")
    resolved_data_root = data_root.expanduser().resolve()
    resolved_data_root.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(resolved_data_root)
    passed = usage.free >= BAOSTOCK_5M_MINIMUM_FREE_BYTES
    run_id = new_run_id("baostock_5m_preflight")
    payload = {
        "schema_version": 1,
        "kind": "a_share_baostock_5m_preflight",
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": (
            "passed_before_network"
            if passed
            else "blocked_insufficient_disk_before_network"
        ),
        "data_root": str(resolved_data_root),
        "sdk_version": importlib.metadata.version("baostock"),
        "source_chain": {
            "data_contract_sha256": BAOSTOCK_5M_CONTRACT_SHA256,
            "factor_spec_sha256": BAOSTOCK_5M_FACTOR_SPEC_SHA256,
            "acceptance_snapshot": {
                "path": manifest_path(source_chain["acceptance_path"]),
                "sha256": file_digest(source_chain["acceptance_path"]),
            },
            "alignment_confirmation": {
                "path": manifest_path(source_chain["alignment_path"]),
                "sha256": file_digest(source_chain["alignment_path"]),
            },
            "suspension_placeholder_audit": {
                "path": manifest_path(DEFAULT_BAOSTOCK_5M_SUSPENSION_AUDIT.resolve()),
                "sha256": BAOSTOCK_5M_SUSPENSION_AUDIT_SHA256,
            },
            "request_throttle_audit": {
                "path": manifest_path(DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT.resolve()),
                "sha256": BAOSTOCK_5M_THROTTLE_AUDIT_SHA256,
            },
        },
        "development_start": start.isoformat(),
        "development_end": end.isoformat(),
        "point_in_time_instruments": int(len(intervals)),
        "provider_pit_interval_requests": int(len(request_tasks)),
        "yearly_storage_partitions": int(len(storage_tasks)),
        "calendar_sessions": int(len(calendar)),
        "universe": {
            "path": manifest_path(universe_path.expanduser().resolve()),
            "sha256": file_digest(universe_path.expanduser().resolve()),
        },
        "calendar": {
            "path": manifest_path(calendar_path.expanduser().resolve()),
            "sha256": file_digest(calendar_path.expanduser().resolve()),
        },
        "minimum_free_bytes": BAOSTOCK_5M_MINIMUM_FREE_BYTES,
        "observed_free_bytes": int(usage.free),
        "observed_free_gib": float(usage.free / 1024**3),
        "filesystem_device": int(resolved_data_root.stat().st_dev),
        "network_request_issued": False,
        "raw_or_derived_factor_values_read": False,
        "forward_return_fields_read": False,
        "selection_or_promotion_allowed": False,
    }
    destination = (
        resolved_data_root / "metadata" / "rich_data" / "preflights" / f"{run_id}.json"
    )
    atomic_write_json(payload, destination)
    return destination


def probe_baostock_5m_restoration(
    *,
    data_root: Path = DATA_ROOT,
) -> Path:
    """Issue one accepted-date request and record whether anonymous access recovered."""

    source_chain = load_baostock_5m_source_chain()
    load_baostock_5m_suspension_audit()
    load_baostock_5m_throttle_audit()
    require_baostock_5m_runtime()
    contract = source_chain["contract"]
    acceptance = contract["formal_acceptance"]
    code = str(acceptance["symbols"][0])
    trade_date = dt.date.fromisoformat(str(acceptance["trade_date"]))
    run_id = new_run_id("baostock_5m_restoration_probe")
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": "a_share_baostock_5m_restoration_probe",
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": "baostock",
        "sdk_version": importlib.metadata.version("baostock"),
        "code": code,
        "trade_date": trade_date.isoformat(),
        "frequency": "5m",
        "source_chain": {
            "data_contract_sha256": BAOSTOCK_5M_CONTRACT_SHA256,
            "factor_spec_sha256": BAOSTOCK_5M_FACTOR_SPEC_SHA256,
            "suspension_placeholder_audit_sha256": BAOSTOCK_5M_SUSPENSION_AUDIT_SHA256,
            "request_throttle_audit_sha256": BAOSTOCK_5M_THROTTLE_AUDIT_SHA256,
        },
        "anonymous_login_attempted": True,
        "history_query_succeeded": False,
        "network_request_issued": True,
        "raw_or_derived_factor_values_read": False,
        "daily_open_close_fields_read": False,
        "forward_return_fields_read": False,
        "selection_or_promotion_allowed": False,
    }
    try:
        raw = fetch_baostock_minutes(code, trade_date, trade_date, "5m")
        frame = canonicalize_baostock_5m_bars(raw, code, trade_date, trade_date)
        report = baostock_5m_acceptance_report(frame, contract)
        passed = (
            report.get("status") == "automatic_checks_passed_pending_time_alignment"
            and (report.get("baostock_5m_contract") or {}).get(
                "exact_timestamp_grid_passed"
            )
            is True
            and len(frame) == 48
        )
        payload.update(
            {
                "status": (
                    "passed_for_bulk_retry"
                    if passed
                    else "failed_acceptance_stop_before_bulk_retry"
                ),
                "history_query_succeeded": True,
                "rows": int(len(frame)),
                "frame_sha256": frame_digest(frame),
                "acceptance": report,
            }
        )
    except Exception as exc:  # noqa: BLE001 - rejection must be recorded without retry.
        payload.update(
            {
                "status": "provider_rejected_stop_before_bulk_retry",
                "rows": 0,
                "provider_error": str(exc),
            }
        )
    resolved_data_root = data_root.expanduser().resolve()
    destination = (
        resolved_data_root
        / "metadata"
        / "rich_data"
        / "availability"
        / f"{run_id}.json"
    )
    atomic_write_json(payload, destination)
    return destination


def load_baostock_5m_restoration_probe(
    data_root: Path,
    *,
    now: dt.datetime | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Require a recent passing isolated probe before any post-blacklist bulk retry."""

    root = data_root.expanduser().resolve() / "metadata" / "rich_data" / "availability"
    paths = sorted(root.glob("*.json")) if root.exists() else []
    if not paths:
        raise RichDataError(
            "BaoStock bulk retry requires one restoration probe after the provider blacklist; "
            "run probe-baostock-5m-restoration once after a cooldown"
        )
    path = paths[-1]
    record = load_json_record(path, kind="a_share_baostock_5m_restoration_probe")
    chain = record.get("source_chain") or {}
    created = pd.Timestamp(record.get("created_at"))
    current = pd.Timestamp(now or dt.datetime.now(dt.timezone.utc))
    age_minutes = float((current - created).total_seconds() / 60.0)
    if (
        record.get("status") != "passed_for_bulk_retry"
        or record.get("provider") != "baostock"
        or record.get("code") != "600519"
        or record.get("trade_date") != "2026-07-10"
        or record.get("rows") != 48
        or record.get("history_query_succeeded") is not True
        or chain.get("request_throttle_audit_sha256")
        != BAOSTOCK_5M_THROTTLE_AUDIT_SHA256
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
        or not 0.0 <= age_minutes <= BAOSTOCK_5M_RESTORATION_PROBE_MAX_AGE_MINUTES
    ):
        raise RichDataError(
            "latest BaoStock restoration probe is rejected, invalid, or older than "
            f"{BAOSTOCK_5M_RESTORATION_PROBE_MAX_AGE_MINUTES} minutes: {path}"
        )
    return path.resolve(), record


def previous_comparable_close_map(symbol: str) -> dict[pd.Timestamp, float]:
    """Express the prior close on each current session's raw-price scale.

    ``raw_close[t-1]`` alone creates a false gap on an ex-rights date.  The
    accepted daily factor lets us carry yesterday's adjusted close onto
    today's raw scale as ``raw_close[t-1] * factor[t-1] / factor[t]``.
    """

    path = DAILY_RAW_DIR / f"{str(symbol).lower()}.parquet"
    if not path.exists():
        raise RichDataError(
            f"local daily raw history is missing for minute feature construction: {path}"
        )
    daily = pd.read_parquet(path)
    required = {"date", "raw_close", "factor", "price_basis"}
    if missing := sorted(required - set(daily.columns)):
        raise RichDataError(
            "local daily history is missing raw-price columns: " + ", ".join(missing)
        )
    bases = set(daily["price_basis"].dropna().astype(str))
    if bases != {REQUIRED_DAILY_PRICE_BASIS}:
        raise RichDataError(
            f"local daily history has an unaccepted price basis for {symbol}: {sorted(bases)}"
        )
    work = daily[["date", "raw_close", "factor"]].copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.normalize()
    work["raw_close"] = pd.to_numeric(work["raw_close"], errors="coerce")
    work["factor"] = pd.to_numeric(work["factor"], errors="coerce")
    work = (
        work.dropna()
        .sort_values("date", kind="stable")
        .drop_duplicates("date", keep="last")
    )
    work["previous_comparable_close"] = (
        work["raw_close"].shift(1) * work["factor"].shift(1) / work["factor"]
    )
    return {
        pd.Timestamp(row.date): float(row.previous_comparable_close)
        for row in work.itertuples(index=False)
        if pd.notna(row.previous_comparable_close)
        and float(row.previous_comparable_close) > 0.0
    }


def minute_feature_frame(
    frame: pd.DataFrame,
    *,
    bar_label: str,
    previous_closes: dict[str, dict[pd.Timestamp, float]],
    frequency: str = "1m",
    feature_names: tuple[str, ...] = MINUTE_FEATURE_NAMES,
) -> pd.DataFrame:
    """Construct one frozen close-known intraday feature catalog without returns."""

    required = {
        "datetime",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "provider",
    }
    if missing := sorted(required - set(frame.columns)):
        raise RichDataError(
            "minute feature input is missing columns: " + ", ".join(missing)
        )
    if bar_label not in {"start", "end"}:
        raise RichDataError("bar label must be 'start' or 'end'")
    if frequency not in MINUTE_EXPECTED_BARS_BY_FREQUENCY:
        raise RichDataError(f"unsupported minute feature frequency: {frequency}")
    if len(feature_names) != 5:
        raise RichDataError(
            "minute feature catalog must contain exactly five ordered names"
        )
    interval_minutes = int(frequency.removesuffix("m"))
    if 30 % interval_minutes:
        raise RichDataError(
            "minute feature frequency must divide the frozen 30-minute late window"
        )
    expected_bars = MINUTE_EXPECTED_BARS_BY_FREQUENCY[frequency]
    late_bar_count = 30 // interval_minutes
    late_return_name, late_amount_name, late_vwap_name, gap_name, volatility_name = (
        feature_names
    )
    work = frame.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    if work["datetime"].isna().any():
        raise RichDataError("minute feature input contains invalid timestamps")
    work["bar_end"] = work["datetime"] + (
        pd.Timedelta(minutes=interval_minutes)
        if bar_label == "start"
        else pd.Timedelta(0)
    )
    numeric_columns = ["open", "high", "low", "close", "volume", "amount"]
    for column in numeric_columns:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if not np.isfinite(work[numeric_columns].to_numpy(dtype=float)).all():
        raise RichDataError(
            "minute feature input contains non-finite OHLCV/amount values"
        )
    if (work[["open", "high", "low", "close"]] <= 0.0).any().any():
        raise RichDataError("minute feature input contains non-positive prices")
    if (work[["volume", "amount"]] < 0.0).any().any():
        raise RichDataError("minute feature input contains negative volume or amount")
    work["trade_date"] = work["bar_end"].dt.normalize()
    expected_bar_ends = expected_minute_times("end", frequency)
    rows: list[dict[str, Any]] = []
    for (symbol, trade_date), group in work.groupby(
        ["symbol", "trade_date"], sort=True
    ):
        group = group.sort_values("bar_end", kind="stable")
        observed_bar_ends = tuple(group["bar_end"].dt.time)
        complete = (
            len(group) == expected_bars and observed_bar_ends == expected_bar_ends
        )
        values = {name: float("nan") for name in feature_names}
        opening_gap_return = float("nan")
        if complete:
            day_open = float(group["open"].iloc[0])
            day_close = float(group["close"].iloc[-1])
            anchor = group.loc[group["bar_end"].dt.time == dt.time(14, 30)]
            late = group.loc[group["bar_end"].dt.time > dt.time(14, 30)]
            total_amount = float(group["amount"].sum())
            total_volume = float(group["volume"].sum())
            late_amount = float(late["amount"].sum())
            late_volume = float(late["volume"].sum())
            if (
                len(anchor) == 1
                and len(late) == late_bar_count
                and float(anchor["close"].iloc[0]) > 0.0
            ):
                values[late_return_name] = (
                    day_close / float(anchor["close"].iloc[0]) - 1.0
                )
            if total_amount > 0.0:
                values[late_amount_name] = late_amount / total_amount
            if (
                total_amount > 0.0
                and total_volume > 0.0
                and late_amount > 0.0
                and late_volume > 0.0
            ):
                values[late_vwap_name] = (late_amount / late_volume) / (
                    total_amount / total_volume
                ) - 1.0
            previous_close = previous_closes.get(str(symbol), {}).get(
                pd.Timestamp(trade_date)
            )
            if previous_close is not None and previous_close > 0.0 and day_open > 0.0:
                opening_gap_return = day_open / previous_close - 1.0
                values[gap_name] = -float(np.sign(opening_gap_return)) * (
                    day_close / day_open - 1.0
                )
            log_returns = (
                np.log(pd.to_numeric(group["close"], errors="coerce")).diff().dropna()
            )
            if len(log_returns) == expected_bars - 1 and np.isfinite(log_returns).all():
                values[volatility_name] = float(np.sqrt(np.square(log_returns).sum()))
        eligible = complete and all(np.isfinite(values[name]) for name in feature_names)
        rows.append(
            {
                "symbol": str(symbol),
                "trade_date": pd.Timestamp(trade_date),
                "provider": str(group["provider"].iloc[0]),
                "bar_timestamp_label": bar_label,
                "minute_bars": int(len(group)),
                "complete_regular_session": bool(complete),
                "minute_feature_eligible": bool(eligible),
                "opening_gap_return": opening_gap_return,
                **values,
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values(["trade_date", "symbol"], kind="stable")
        .reset_index(drop=True)
    )


def build_minute_features(
    snapshot_path: Path,
    alignment_path: Path,
    *,
    factor_spec_path: Path = DEFAULT_MINUTE_FACTOR_SPEC,
    output: Path | None = None,
) -> Path:
    """Build frozen minute features only after provider semantics are confirmed."""

    snapshot_path = snapshot_path.expanduser().resolve()
    alignment_path = alignment_path.expanduser().resolve()
    factor_spec_path = factor_spec_path.expanduser().resolve()
    snapshot = load_json_record(snapshot_path, kind="a_share_rich_data_snapshot")
    alignment = load_json_record(
        alignment_path, kind="a_share_minute_alignment_confirmation"
    )
    spec_kind = load_json_record(factor_spec_path).get("kind")
    if spec_kind == "a_share_minute_factor_preregistration":
        spec = load_minute_factor_spec(factor_spec_path)
    elif spec_kind == "a_share_baostock_5m_factor_preregistration":
        spec = load_baostock_5m_factor_spec(factor_spec_path)
    else:
        raise RichDataError(
            f"unsupported minute factor preregistration kind: {spec_kind}"
        )
    minute_contract = spec["minute_contract"]
    frequency = str(minute_contract["frequency"])
    feature_names = tuple(str(item["name"]) for item in spec["features"])
    allowed_datasets = (
        {"minutes", "baostock_five_minute_history"}
        if spec_kind == "a_share_baostock_5m_factor_preregistration"
        else {"minutes"}
    )
    if (
        snapshot.get("dataset") not in allowed_datasets
        or snapshot.get("frequency") != frequency
    ):
        raise RichDataError(
            f"minute feature construction requires a {frequency} minute snapshot"
        )
    if snapshot.get("dataset") == "baostock_five_minute_history" and (
        snapshot.get("status")
        != "full_source_coverage_passed_pending_no_return_feature_materialization"
        or (snapshot.get("coverage") or {}).get("gate_passed_before_prices") is not True
        or snapshot.get("forward_return_fields_read") is not False
        or snapshot.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "BaoStock five-minute history must pass its no-return full-source coverage gate "
            "before feature materialization"
        )
    if snapshot.get("prices") != "raw_unadjusted":
        raise RichDataError(
            "minute feature construction requires raw unadjusted prices"
        )
    expected_provider = minute_contract.get("provider")
    if expected_provider is not None and snapshot.get("provider") != expected_provider:
        raise RichDataError(
            "minute snapshot provider does not match the frozen factor specification"
        )
    if alignment.get("status") != "passed_for_feature_research":
        raise RichDataError("minute alignment has not passed for feature research")
    if snapshot.get("provider") != alignment.get("provider") or snapshot.get(
        "frequency"
    ) != alignment.get("frequency"):
        raise RichDataError(
            "minute snapshot provider/frequency does not match the alignment confirmation"
        )
    source_acceptance = alignment.get("source_acceptance_snapshot") or {}
    source_acceptance_path = resolve_record_path(
        str(source_acceptance.get("path") or "")
    )
    if not source_acceptance.get("path") or not source_acceptance_path.exists():
        raise RichDataError(
            "alignment confirmation has no readable source acceptance snapshot"
        )
    if file_digest(source_acceptance_path) != source_acceptance.get("sha256"):
        raise RichDataError(
            "alignment confirmation source acceptance fingerprint mismatch"
        )
    acceptance_snapshot = load_json_record(
        source_acceptance_path, kind="a_share_rich_data_snapshot"
    )
    if (
        acceptance_snapshot.get("acceptance_status")
        != "automatic_checks_passed_pending_time_alignment"
        or acceptance_snapshot.get("provider") != alignment.get("provider")
        or acceptance_snapshot.get("frequency") != alignment.get("frequency")
    ):
        raise RichDataError(
            "alignment confirmation is not bound to a compatible accepted snapshot"
        )
    if spec_kind == "a_share_baostock_5m_factor_preregistration":
        chain = spec["source_chain"]
        expected_acceptance = chain["acceptance_snapshot"]
        expected_alignment = chain["alignment_confirmation"]
        if (
            resolve_record_path(expected_acceptance["path"]) != source_acceptance_path
            or expected_acceptance["sha256"] != file_digest(source_acceptance_path)
            or resolve_record_path(expected_alignment["path"]) != alignment_path
            or expected_alignment["sha256"] != file_digest(alignment_path)
        ):
            raise RichDataError(
                "BaoStock five-minute feature build is not bound to its frozen source chain"
            )
        if snapshot.get("dataset") == "baostock_five_minute_history":
            history_chain = snapshot.get("source_chain") or {}
            history_spec = history_chain.get("factor_spec") or {}
            history_acceptance = history_chain.get("acceptance_snapshot") or {}
            history_alignment = history_chain.get("alignment_confirmation") or {}
            if (
                history_spec.get("sha256") != file_digest(factor_spec_path)
                or history_acceptance.get("sha256") != expected_acceptance["sha256"]
                or history_alignment.get("sha256") != expected_alignment["sha256"]
            ):
                raise RichDataError(
                    "BaoStock five-minute history is not fingerprint-bound to the frozen "
                    "factor, acceptance, and alignment chain"
                )
    files = list(snapshot.get("files") or [])
    if not files:
        raise RichDataError("minute snapshot contains no files")

    previous_closes: dict[str, dict[pd.Timestamp, float]] = {}
    feature_frames: list[pd.DataFrame] = []
    for file_record in files:
        frame = load_snapshot_frame(file_record)
        if frame.empty:
            continue
        providers = frame["provider"].dropna().astype(str).unique().tolist()
        if providers != [str(snapshot["provider"])]:
            raise RichDataError(
                "minute snapshot file contains a mixed or unexpected provider"
            )
        symbols = frame["symbol"].dropna().astype(str).unique().tolist()
        if len(symbols) != 1:
            raise RichDataError(
                "each minute snapshot file must contain exactly one canonical symbol"
            )
        symbol = symbols[0]
        previous_closes.setdefault(symbol, previous_comparable_close_map(symbol))
        feature_frames.append(
            minute_feature_frame(
                frame,
                bar_label=str(alignment["bar_timestamp_label"]),
                previous_closes=previous_closes,
                frequency=frequency,
                feature_names=feature_names,
            )
        )
    if not feature_frames:
        raise RichDataError("minute snapshot contains no bars for feature construction")
    features = pd.concat(feature_frames, ignore_index=True).sort_values(
        ["trade_date", "symbol"], kind="stable"
    )
    eligible_rows = int(features["minute_feature_eligible"].sum())
    if eligible_rows == 0:
        raise RichDataError(
            "minute snapshot has no complete feature-eligible sessions; missing bars are not filled"
        )

    feature_version = "v1" if frequency == "1m" else "baostock_5m_v1"
    run_id = new_run_id(f"{snapshot['provider']}_{frequency}_features_v1")
    feature_path = (
        output.expanduser().resolve()
        if output is not None
        else DERIVED_ROOT
        / "minute_features"
        / feature_version
        / run_id
        / "features.parquet"
    )
    if feature_path.exists():
        raise RichDataError(f"minute feature output already exists: {feature_path}")
    atomic_write_frame(features, feature_path)
    manifest = {
        "schema_version": 1,
        "kind": "a_share_minute_feature_run",
        "status": "features_built_research_only",
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": snapshot["provider"],
        "frequency": frequency,
        "feature_spec": {
            "path": manifest_path(factor_spec_path),
            "sha256": file_digest(factor_spec_path),
            "version": spec.get("version"),
            "features": spec["features"],
        },
        "source_snapshot": {
            "path": manifest_path(snapshot_path),
            "sha256": file_digest(snapshot_path),
            "run_id": snapshot.get("run_id"),
            "prices": snapshot.get("prices"),
        },
        "alignment_confirmation": {
            "path": manifest_path(alignment_path),
            "sha256": file_digest(alignment_path),
            "run_id": alignment.get("run_id"),
            "bar_timestamp_label": alignment.get("bar_timestamp_label"),
            "volume_unit": alignment.get("volume_unit"),
        },
        "output": {
            "path": manifest_path(feature_path),
            "sha256": frame_digest(features),
            "rows": int(len(features)),
            "eligible_rows": eligible_rows,
            "incomplete_session_rows": int(
                (~features["complete_regular_session"]).sum()
            ),
            "calendar_start": pd.Timestamp(features["trade_date"].min())
            .date()
            .isoformat(),
            "calendar_end": pd.Timestamp(features["trade_date"].max())
            .date()
            .isoformat(),
        },
        "forward_return_fields_read": False,
        "future_price_fields_read": False,
        "selection_or_promotion_allowed": False,
    }
    destination = FEATURE_RUNS_ROOT / f"{run_id}.json"
    atomic_write_json(manifest, destination)
    return destination


def sync_minutes(
    provider: str,
    codes: list[str],
    start: dt.date,
    end: dt.date,
    frequency: str,
    allow_large: bool,
    acceptance: bool = False,
) -> Path:
    """Download and validate explicit-symbol minute bars into one snapshot."""

    if frequency not in {"1m", "5m", "15m", "30m", "60m"}:
        raise RichDataError("frequency must be one of 1m, 5m, 15m, 30m, 60m")
    if provider == "baostock" and frequency != "5m":
        raise RichDataError(
            "the frozen BaoStock intraday contract supports only 5m bars"
        )
    require_provider(provider)
    validate_range(start, end, allow_large=allow_large, unit_count=len(codes))
    fetcher = MINUTE_FETCHERS[provider]
    rows_by_code: dict[str, pd.DataFrame] = {}
    acceptance_by_code: dict[str, dict[str, Any]] = {}
    for code in codes:
        raw = fetcher(code, start, end, frequency)
        rows_by_code[code] = (
            canonicalize_baostock_5m_bars(raw, code, start, end)
            if provider == "baostock"
            else canonicalize_minute_bars(raw, provider, code, start, end)
        )
        if acceptance:
            acceptance_by_code[code] = minute_acceptance_report(rows_by_code[code])
    return write_minute_snapshot(
        provider,
        frequency,
        start,
        end,
        rows_by_code,
        acceptance_by_code if acceptance else None,
    )


def baostock_5m_acceptance_report(
    frame: pd.DataFrame, contract: dict[str, Any]
) -> dict[str, Any]:
    """Apply exact 48-bar end-label checks on top of raw daily reconciliation."""

    report = minute_acceptance_report(frame)
    acceptance = contract["formal_acceptance"]
    expected_times = expected_minute_times("end", "5m")
    observed_times = (
        tuple(pd.to_datetime(frame["datetime"]).dt.time) if not frame.empty else ()
    )
    exact = (
        len(frame) == int(acceptance["required_rows_per_symbol"])
        and observed_times == expected_times
    )
    report["baostock_5m_contract"] = {
        "required_rows": int(acceptance["required_rows_per_symbol"]),
        "observed_rows": int(len(frame)),
        "expected_bar_label": "end",
        "exact_timestamp_grid_passed": exact,
        "forward_return_fields_read": False,
    }
    if not exact:
        report["status"] = "automatic_checks_failed"
    return report


def sync_baostock_5m_acceptance() -> Path:
    """Persist the one fixed no-return BaoStock five-minute acceptance snapshot."""

    contract = load_baostock_5m_contract()
    acceptance = contract["formal_acceptance"]
    trade_date = dt.date.fromisoformat(str(acceptance["trade_date"]))
    codes = [str(code) for code in acceptance["symbols"]]
    require_provider("baostock")
    validate_range(trade_date, trade_date, allow_large=False, unit_count=len(codes))
    rows_by_code: dict[str, pd.DataFrame] = {}
    acceptance_by_code: dict[str, dict[str, Any]] = {}
    for code in codes:
        raw = fetch_baostock_minutes(code, trade_date, trade_date, "5m")
        frame = canonicalize_baostock_5m_bars(raw, code, trade_date, trade_date)
        rows_by_code[code] = frame
        acceptance_by_code[code] = baostock_5m_acceptance_report(frame, contract)
    return write_minute_snapshot(
        "baostock",
        "5m",
        trade_date,
        trade_date,
        rows_by_code,
        acceptance_by_code,
        data_contract={
            "path": manifest_path(DEFAULT_BAOSTOCK_5M_CONTRACT.resolve()),
            "sha256": file_digest(DEFAULT_BAOSTOCK_5M_CONTRACT),
            "kind": contract["kind"],
            "forward_return_fields_read": False,
        },
    )


def sync_baostock_5m_history(
    *,
    allow_large: bool = False,
    data_root: Path = DATA_ROOT,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
    factor_spec_path: Path = DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
    workers: int = BAOSTOCK_5M_MAX_WORKERS,
) -> Path:
    """Run one locked full-history synchronization on the selected data root."""

    if not allow_large:
        raise RichDataError(
            "BaoStock full five-minute history requires explicit --allow-large"
        )
    resolved_data_root = data_root.expanduser().resolve()
    resolved_data_root.mkdir(parents=True, exist_ok=True)
    with RichDataProcessLock(resolved_data_root / ".a_share_baostock_5m.lock"):
        return _sync_baostock_5m_history_unlocked(
            allow_large=allow_large,
            data_root=resolved_data_root,
            universe_path=universe_path,
            calendar_path=calendar_path,
            factor_spec_path=factor_spec_path,
            workers=workers,
        )


def _sync_baostock_5m_history_unlocked(
    *,
    allow_large: bool = False,
    data_root: Path = DATA_ROOT,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
    factor_spec_path: Path = DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
    workers: int = BAOSTOCK_5M_MAX_WORKERS,
) -> Path:
    """Store the frozen 2020--2025 PIT-universe BaoStock five-minute history."""

    if not allow_large:
        raise RichDataError(
            "BaoStock full five-minute history requires explicit --allow-large"
        )
    if not 1 <= workers <= BAOSTOCK_5M_MAX_WORKERS:
        raise RichDataError(
            f"BaoStock five-minute workers must be between 1 and {BAOSTOCK_5M_MAX_WORKERS}"
        )
    restoration_path, restoration = load_baostock_5m_restoration_probe(data_root)
    preflight_path = write_baostock_5m_preflight(
        data_root=data_root,
        universe_path=universe_path,
        calendar_path=calendar_path,
        factor_spec_path=factor_spec_path,
    )
    preflight = load_json_record(preflight_path, kind="a_share_baostock_5m_preflight")
    if preflight.get("status") != "passed_before_network":
        raise RichDataError(
            "BaoStock full five-minute history stopped before any network request: "
            f"{preflight['data_root']} has {float(preflight['observed_free_gib']):.2f} GiB free; "
            "pass --data-root pointing to a volume with at least 10 GiB. "
            f"Audit: {preflight_path}"
        )
    source_chain = load_baostock_5m_source_chain(factor_spec_path)
    contract = source_chain["contract"]
    require_baostock_5m_runtime()
    bulk = contract["bulk_snapshot_contract"]
    start = dt.date.fromisoformat(str(bulk["development_start"]))
    end = dt.date.fromisoformat(str(bulk["development_end"]))
    intervals = load_factor_universe_intervals(universe_path)
    calendar = local_calendar_dates(start, end, calendar_path)
    if calendar.empty:
        raise RichDataError(
            "local calendar has no sessions in the BaoStock five-minute range"
        )
    storage_tasks = baostock_5m_partition_tasks(intervals, start, end)
    request_tasks = baostock_5m_request_tasks(intervals, start, end)
    if not storage_tasks or not request_tasks:
        raise RichDataError("factor universe has no BaoStock five-minute partitions")

    resolved_data_root = data_root.expanduser().resolve()
    resolved_data_root.mkdir(parents=True, exist_ok=True)
    storage_device = int(resolved_data_root.stat().st_dev)
    if storage_device != int(preflight["filesystem_device"]):
        raise RichDataError(
            "BaoStock five-minute target filesystem changed after preflight"
        )
    disk_before = shutil.disk_usage(resolved_data_root)
    if disk_before.free < BAOSTOCK_5M_MINIMUM_FREE_BYTES:
        raise RichDataError(
            "BaoStock full five-minute history requires at least 10 GiB free before any "
            f"network request; {resolved_data_root} has {disk_before.free / 1024**3:.2f} GiB. "
            "Pass --data-root pointing to a larger volume."
        )

    run_id = new_run_id("baostock_5m_history")
    parent = (
        resolved_data_root
        / "raw"
        / "a_share"
        / "rich"
        / "baostock"
        / "minutes"
        / "5m"
        / "snapshots"
    )
    run_root = parent / run_id
    temporary_root = parent / f".{run_id}.partial"
    runs_root = resolved_data_root / "metadata" / "rich_data" / "runs"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"BaoStock five-minute snapshot already exists: {run_id}")
    temporary_root.mkdir(parents=True)

    task_by_key = {(task[0], task[3]): task for task in storage_tasks}
    tasks_by_code: dict[str, list[tuple[str, str, str, int]]] = {}
    for task in storage_tasks:
        tasks_by_code.setdefault(task[0], []).append(task)
    expected_requests = set(request_tasks)
    received_requests: set[tuple[str, str, str]] = set()
    received_partitions: set[tuple[str, int]] = set()
    complete_counts: dict[str, int] = {}
    files: list[dict[str, Any]] = []
    total_rows = 0
    source_rows = 0
    zero_price_placeholder_rows = 0
    zero_price_placeholder_sessions = 0
    complete_sessions = 0
    incomplete_sessions = 0
    download_started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    download_started_monotonic = time.monotonic()
    try:
        for (
            code,
            request_start,
            request_end,
            request_frame,
        ) in download_baostock_5m_requests(request_tasks, workers):
            request_key = (str(code), str(request_start), str(request_end))
            if request_key not in expected_requests:
                raise RichDataError(
                    "BaoStock five-minute downloader returned an unexpected PIT request: "
                    f"{request_key}"
                )
            if request_key in received_requests:
                raise RichDataError(
                    "BaoStock five-minute downloader returned a duplicate PIT request: "
                    f"{request_key}"
                )
            request_partition_rows = 0
            for task, frame in split_baostock_5m_request_frame(
                request_frame, tasks_by_code[str(code)]
            ):
                year = task[3]
                key = (str(code), int(year))
                if key not in task_by_key:
                    raise RichDataError(
                        "BaoStock five-minute downloader produced an unexpected storage "
                        f"partition: {key}"
                    )
                if key in received_partitions:
                    raise RichDataError(
                        "BaoStock five-minute downloader produced a duplicate storage "
                        f"partition: {key}"
                    )
                complete_dates = validate_baostock_5m_partition(frame, task, calendar)
                frame_dates = (
                    set(pd.to_datetime(frame["datetime"]).dt.date.astype(str))
                    if not frame.empty
                    else set()
                )
                placeholder_dates = set(
                    str(value)
                    for value in frame.attrs.get(
                        "zero_price_placeholder_session_dates", []
                    )
                )
                observed_dates = len(frame_dates | placeholder_dates)
                partition_source_rows = int(frame.attrs.get("source_rows", len(frame)))
                partition_placeholder_rows = int(
                    frame.attrs.get("zero_price_placeholder_rows_excluded", 0)
                )
                for trade_date in complete_dates:
                    complete_counts[trade_date] = complete_counts.get(trade_date, 0) + 1
                complete_sessions += len(complete_dates)
                incomplete_sessions += observed_dates - len(complete_dates)
                relative = Path(qlib_symbol(code).lower()) / f"{year}.parquet"
                temporary_destination = temporary_root / relative
                final_destination = run_root / relative
                try:
                    current_device = int(resolved_data_root.stat().st_dev)
                except FileNotFoundError as exc:
                    raise RichDataError(
                        "BaoStock five-minute target volume disappeared during download"
                    ) from exc
                if current_device != storage_device:
                    raise RichDataError(
                        "BaoStock five-minute target filesystem changed during download"
                    )
                atomic_write_frame(frame, temporary_destination)
                request_partition_rows += int(len(frame))
                total_rows += int(len(frame))
                source_rows += partition_source_rows
                zero_price_placeholder_rows += partition_placeholder_rows
                zero_price_placeholder_sessions += len(placeholder_dates)
                files.append(
                    {
                        "code": str(code),
                        "symbol": qlib_symbol(code),
                        "year": int(year),
                        "requested_start": task[1],
                        "requested_end": task[2],
                        "path": manifest_path(final_destination),
                        "rows": int(len(frame)),
                        "source_rows": partition_source_rows,
                        "zero_price_placeholder_rows_excluded": partition_placeholder_rows,
                        "zero_price_placeholder_sessions": len(placeholder_dates),
                        "observed_sessions": observed_dates,
                        "complete_regular_sessions": int(len(complete_dates)),
                        "sha256": frame_digest(frame),
                    }
                )
                received_partitions.add(key)
            if request_partition_rows != len(request_frame):
                raise RichDataError(
                    f"BaoStock five-minute yearly split lost rows for {code}: "
                    f"{request_partition_rows} != {len(request_frame)}"
                )
            received_requests.add(request_key)
            if len(received_requests) == 1 or len(received_requests) % 5 == 0:
                elapsed = max(time.monotonic() - download_started_monotonic, 0.001)
                print(
                    json.dumps(
                        {
                            "status": "downloading_baostock_5m",
                            "provider_requests_completed": len(received_requests),
                            "provider_requests_total": len(request_tasks),
                            "storage_partitions_completed": len(received_partitions),
                            "storage_partitions_total": len(storage_tasks),
                            "rows_written": total_rows,
                            "elapsed_minutes": round(elapsed / 60.0, 2),
                            "provider_requests_per_minute": round(
                                len(received_requests) / elapsed * 60.0, 2
                            ),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
        missing_requests = sorted(expected_requests - received_requests)
        if missing_requests:
            raise RichDataError(
                f"BaoStock five-minute downloader omitted {len(missing_requests)} requests; "
                f"first missing request: {missing_requests[0]}"
            )
        missing_partitions = sorted(set(task_by_key) - received_partitions)
        if missing_partitions:
            raise RichDataError(
                f"BaoStock five-minute downloader omitted {len(missing_partitions)} storage "
                f"partitions; first missing partition: {missing_partitions[0]}"
            )
        coverage = baostock_5m_coverage_report(
            intervals, calendar, complete_counts, contract
        )
        disk_after_download = shutil.disk_usage(resolved_data_root)
        files.sort(key=lambda item: (item["symbol"], item["year"]))
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "baostock_five_minute_history",
            "provider": "baostock",
            "frequency": "5m",
            "prices": "raw_unadjusted",
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "download_started_at": download_started_at,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": run_id,
            "status": (
                "full_source_coverage_passed_pending_no_return_feature_materialization"
                if coverage["gate_passed_before_prices"]
                else "full_source_coverage_failed_stop_before_forward_returns"
            ),
            "data_root": str(resolved_data_root),
            "source_chain": {
                "data_contract": {
                    "path": manifest_path(DEFAULT_BAOSTOCK_5M_CONTRACT.resolve()),
                    "sha256": BAOSTOCK_5M_CONTRACT_SHA256,
                },
                "factor_spec": {
                    "path": manifest_path(factor_spec_path.expanduser().resolve()),
                    "sha256": BAOSTOCK_5M_FACTOR_SPEC_SHA256,
                },
                "acceptance_snapshot": {
                    "path": manifest_path(source_chain["acceptance_path"]),
                    "sha256": file_digest(source_chain["acceptance_path"]),
                    "run_id": source_chain["acceptance"].get("run_id"),
                },
                "alignment_confirmation": {
                    "path": manifest_path(source_chain["alignment_path"]),
                    "sha256": file_digest(source_chain["alignment_path"]),
                    "run_id": source_chain["alignment"].get("run_id"),
                },
                "suspension_placeholder_audit": {
                    "path": manifest_path(
                        DEFAULT_BAOSTOCK_5M_SUSPENSION_AUDIT.resolve()
                    ),
                    "sha256": BAOSTOCK_5M_SUSPENSION_AUDIT_SHA256,
                },
                "request_throttle_audit": {
                    "path": manifest_path(DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT.resolve()),
                    "sha256": BAOSTOCK_5M_THROTTLE_AUDIT_SHA256,
                },
            },
            "storage_preflight_record": {
                "path": manifest_path(preflight_path),
                "sha256": file_digest(preflight_path),
                "status": preflight["status"],
                "network_request_issued": preflight["network_request_issued"],
            },
            "restoration_probe": {
                "path": manifest_path(restoration_path),
                "sha256": file_digest(restoration_path),
                "status": restoration["status"],
                "created_at": restoration["created_at"],
            },
            "request_protocol": {
                "sdk_version": importlib.metadata.version("baostock"),
                "frequency": "5",
                "adjustflag": "3",
                "fields": contract["source"]["requested_fields"],
                "provider_request_unit": "one_clipped_pit_interval_per_instrument",
                "yearly_parquet_storage_partitions": True,
                "partition_retries": BAOSTOCK_5M_PARTITION_RETRIES,
                "blacklist_error_retried": False,
                "workers": workers,
                "provider_request_count": len(request_tasks),
                "storage_partition_count": len(storage_tasks),
                "credentials_required_or_stored": False,
            },
            "storage_preflight": {
                "minimum_free_bytes": BAOSTOCK_5M_MINIMUM_FREE_BYTES,
                "free_bytes_before_network": int(disk_before.free),
                "free_bytes_after_download": int(disk_after_download.free),
                "passed_before_network": True,
                "temporary_snapshot_deleted_on_failure": True,
            },
            "universe": {
                "path": manifest_path(universe_path.expanduser().resolve()),
                "sha256": file_digest(universe_path.expanduser().resolve()),
                "point_in_time_intervals": int(len(intervals)),
            },
            "calendar": {
                "path": manifest_path(calendar_path.expanduser().resolve()),
                "sha256": file_digest(calendar_path.expanduser().resolve()),
                "sessions": int(len(calendar)),
            },
            "rows": total_rows,
            "normalization_quality": {
                "source_rows": source_rows,
                "rows_written": total_rows,
                "zero_price_placeholder_rows_excluded": zero_price_placeholder_rows,
                "zero_price_placeholder_sessions": zero_price_placeholder_sessions,
            },
            "complete_regular_sessions": complete_sessions,
            "incomplete_observed_sessions": incomplete_sessions,
            "files": files,
            "coverage": coverage,
            "raw_minute_price_fields_stored": ["open", "high", "low", "close"],
            "daily_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = runs_root / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def sync_tushare_events(
    datasets: list[str], start: dt.date, end: dt.date, allow_large: bool
) -> Path:
    """Download one or more Tushare end-of-day event tables into a snapshot."""

    require_provider("tushare")
    unknown = sorted(set(datasets) - set(EVENT_DATASETS))
    if unknown:
        raise RichDataError(f"unsupported event dataset(s): {', '.join(unknown)}")
    validate_range(start, end, allow_large=allow_large, unit_count=len(datasets))
    run_id = new_run_id("tushare_events")
    run_root = RAW_ROOT / "tushare" / "events" / "snapshots" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare event snapshot already exists: {run_id}")
    files: list[dict[str, Any]] = []
    quality_totals = {
        "source_rows": 0,
        "exact_duplicate_rows": 0,
        "duplicate_event_key_rows": 0,
    }
    try:
        for trade_date in pd.bdate_range(start, end):
            date = trade_date.date()
            for dataset in datasets:
                source_frame = fetch_tushare_event(dataset, date)
                quality = tushare_event_quality(source_frame, dataset, date)
                for field in quality_totals:
                    quality_totals[field] += int(quality[field])
                frame = source_frame.copy()
                frame["provider"] = "tushare"
                frame["dataset"] = dataset
                frame["retrieved_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
                temporary_destination = (
                    temporary_root / dataset / f"{date.isoformat()}.parquet"
                )
                final_destination = run_root / dataset / f"{date.isoformat()}.parquet"
                atomic_write_frame(frame, temporary_destination)
                files.append(
                    {
                        "dataset": dataset,
                        "trade_date": date.isoformat(),
                        "path": manifest_path(final_destination),
                        "rows": int(len(frame)),
                        "sha256": frame_digest(frame),
                        "minimum_permission_points": TUSHARE_EVENT_PERMISSION_POINTS[
                            dataset
                        ],
                        "quality": quality,
                    }
                )
        manifest = {
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_events",
            "provider": "tushare",
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": run_id,
            "requested_datasets": datasets,
            "files": files,
            "source_quality": {
                **quality_totals,
                "raw_rows_preserved_without_deduplication": True,
            },
            "acceptance_status": "pending_event_time_alignment_and_canonicalization",
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        run_manifest_path = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, run_manifest_path)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return run_manifest_path
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def sync_tushare_northbound_top10_acceptance() -> Path:
    """Run the frozen one-session, two-market no-return entitlement check."""

    require_provider("tushare")
    contract = load_tushare_northbound_top10_contract()
    acceptance = contract["acceptance_protocol"]
    trade_date = dt.date.fromisoformat(acceptance["fixed_completed_session"])
    run_id = new_run_id("tushare_northbound_top10_acceptance")
    run_root = RAW_ROOT / "tushare" / "northbound_top10" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare Northbound acceptance already exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        frames: list[pd.DataFrame] = []
        market_quality: list[dict[str, Any]] = []
        for market_type in TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES:
            raw = fetch_tushare_northbound_top10(trade_date, market_type)
            normalized, quality = canonicalize_tushare_northbound_top10(
                raw,
                trade_date,
                trade_date,
                expected_market_type=market_type,
            )
            observed_ranks = sorted(normalized["rank"].astype(int).tolist())
            if observed_ranks != list(range(1, 11)):
                raise RichDataError(
                    "Tushare hsgt_top10 acceptance must contain ranks 1 through 10 for "
                    f"market_type={market_type}; observed={observed_ranks}"
                )
            frames.append(normalized)
            market_quality.append(
                {
                    "market_type": market_type,
                    **quality,
                    "observed_ranks": observed_ranks,
                }
            )
        combined = (
            pd.concat(frames, ignore_index=True)
            .sort_values(["trade_date", "market_type", "rank"], kind="stable")
            .reset_index(drop=True)
        )
        if combined.duplicated(["instrument", "trade_date"]).any():
            raise RichDataError(
                "Tushare hsgt_top10 acceptance contains duplicate instrument/date keys"
            )
        temporary_destination = temporary_root / "northbound_top10.parquet"
        final_destination = run_root / "northbound_top10.parquet"
        atomic_write_frame(combined, temporary_destination)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_northbound_top10_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "hsgt_top10",
                "request_mode": "one completed local trading session and one market_type per call",
                "market_types": list(TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES),
                "fields": list(TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS),
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(combined)),
                    "sha256": frame_digest(combined),
                }
            ],
            "source_quality": {
                "market_requests": market_quality,
                "rows_written": int(len(combined)),
                "unique_instruments": int(combined["instrument"].nunique()),
                "duplicate_event_key_rows": int(
                    combined.duplicated(["instrument", "trade_date"]).sum()
                ),
                "factor_min": float(
                    combined["tushare_northbound_top10_net_buy_share"].min()
                ),
                "factor_max": float(
                    combined["tushare_northbound_top10_net_buy_share"].max()
                ),
            },
            "acceptance_status": "accepted_entitlement_and_formula_pending_full_history",
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_northbound_top10_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT),
            },
            "source_request": {
                "api": "hsgt_top10",
                "market_types": list(TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES),
                "fields": list(TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS),
                "credentials_logged_or_stored": False,
            },
            "files": [],
            "acceptance_status": "entitlement_or_schema_rejected_stop_before_full_history",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def sync_tushare_top_inst_acceptance() -> Path:
    """Run the single frozen no-return institution-seat acceptance request."""

    contract = load_tushare_top_inst_contract()
    prior_records = tushare_top_inst_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare top_inst acceptance is one-shot and was already consumed: "
            + ", ".join(str(path) for path in prior_records)
        )
    top_list = load_tushare_top_inst_top_list_context(contract)
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    trade_date = dt.date.fromisoformat(acceptance["fixed_completed_session"])
    validate_range(trade_date, trade_date, allow_large=False)
    run_id = new_run_id("tushare_top_inst_acceptance")
    run_root = RAW_ROOT / "tushare" / "top_inst" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare top_inst acceptance already exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    provider_call_issued = False
    try:
        provider_call_issued = True
        raw = fetch_tushare_top_inst(trade_date)
        minimum_raw = int(acceptance["minimum_raw_institution_rows"])
        if len(raw) < minimum_raw:
            raise RichDataError(
                "Tushare top_inst acceptance returned too few institution-seat rows: "
                f"{len(raw)} < {minimum_raw}"
            )
        maximum_rows = int(
            contract["source_selection"]["provider_documented_maximum_rows_per_call"]
        )
        if len(raw) >= maximum_rows:
            raise RichDataError(
                "Tushare top_inst acceptance reached the possible truncation ceiling: "
                f"{len(raw)} >= {maximum_rows}"
            )
        normalized, quality = canonicalize_tushare_top_inst(raw, trade_date, trade_date)
        minimum_aggregated = int(acceptance["minimum_aggregated_stock_rows"])
        if len(normalized) < minimum_aggregated:
            raise RichDataError(
                "Tushare top_inst acceptance retained too few positive-activity stocks: "
                f"{len(normalized)} < {minimum_aggregated}"
            )
        observed_instruments = frozenset(normalized["instrument"].astype(str))
        absent_from_top_list = sorted(observed_instruments - top_list["instruments"])
        if absent_from_top_list:
            raise RichDataError(
                "Tushare top_inst stocks are absent from the accepted same-date top_list: "
                + ", ".join(absent_from_top_list)
            )
        temporary_destination = temporary_root / "top_inst.parquet"
        final_destination = run_root / "top_inst.parquet"
        atomic_write_frame(normalized, temporary_destination)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_top_inst_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_TOP_INST_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_TOP_INST_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "top_inst",
                "request_mode": "one completed local trading session per call",
                "provider_calls_issued": 1,
                "fields": list(TUSHARE_TOP_INST_RAW_FIELDS),
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "accepted_top_list_evidence": {
                "manifest_path": manifest_path(top_list["manifest_path"]),
                "manifest_sha256": top_list["manifest_sha256"],
                "frame_path": manifest_path(top_list["frame_path"]),
                "frame_content_sha256": top_list["frame_sha256"],
                "raw_rows": top_list["frame_rows"],
                "exact_duplicate_rows_preserved": top_list[
                    "exact_duplicate_rows_preserved"
                ],
                "unsupported_security_rows_excluded": top_list[
                    "unsupported_security_rows_excluded"
                ],
                "all_top_inst_stocks_present": True,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(normalized)),
                    "sha256": frame_digest(normalized),
                }
            ],
            "source_quality": {
                **quality,
                "unique_instruments": int(normalized["instrument"].nunique()),
                "factor_min": float(normalized["tushare_top_inst_net_buy_share"].min()),
                "factor_max": float(normalized["tushare_top_inst_net_buy_share"].max()),
                "duplicate_institution_seat_keys": 0,
                "provider_net_buy_used_only_for_integrity_reconciliation": True,
            },
            "availability_policy": {
                "documented_after_close_time": "20:00 Asia/Shanghai",
                "same_session_trade_allowed": False,
                "eligible_entry": "following local session open",
                "maximum_event_age_days": 0,
                "forward_fill_allowed": False,
            },
            "acceptance_status": (
                "accepted_entitlement_schema_formula_and_top_list_concordance_"
                "pending_full_history_protocol"
            ),
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_top_inst_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_TOP_INST_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_TOP_INST_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "top_inst",
                "request_mode": "one completed local trading session per call",
                "provider_calls_issued": int(provider_call_issued),
                "fields": list(TUSHARE_TOP_INST_RAW_FIELDS),
                "credentials_logged_or_stored": False,
            },
            "accepted_top_list_evidence": {
                "manifest_path": manifest_path(top_list["manifest_path"]),
                "manifest_sha256": top_list["manifest_sha256"],
                "frame_path": manifest_path(top_list["frame_path"]),
                "frame_content_sha256": top_list["frame_sha256"],
                "unsupported_security_rows_excluded": top_list[
                    "unsupported_security_rows_excluded"
                ],
            },
            "files": [],
            "acceptance_status": "rejected_stop_before_full_history_or_returns",
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def sync_tushare_top10_float_concentration_acceptance() -> Path:
    """Run the frozen three-call, no-return ownership acceptance exactly once."""

    contract = load_tushare_top10_float_concentration_contract()
    prior_records = tushare_top10_float_concentration_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare top-ten float concentration acceptance is one-shot and was "
            "already consumed: " + ", ".join(str(path) for path in prior_records)
        )
    context = validate_tushare_top10_float_local_context(contract)
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    symbols = tuple(str(value) for value in acceptance["fixed_symbols"])
    report_start = dt.datetime.strptime(
        str(acceptance["fixed_report_period_start"]), "%Y%m%d"
    ).date()
    report_end = dt.datetime.strptime(
        str(acceptance["fixed_report_period_end"]), "%Y%m%d"
    ).date()
    latest_announcement = dt.datetime.strptime(
        str(acceptance["latest_allowed_announcement_date"]), "%Y%m%d"
    ).date()
    run_id = new_run_id("tushare_top10_float_concentration_acceptance")
    run_root = (
        RAW_ROOT / "tushare" / "top10_float_concentration" / "acceptance" / run_id
    )
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(
            f"Tushare top-ten float concentration acceptance already exists: {run_id}"
        )
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    provider_calls_issued = 0
    source_rows_by_symbol: dict[str, int] = {}
    try:
        raw_by_symbol: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            provider_calls_issued += 1
            raw = fetch_tushare_top10_float_holders(
                symbol,
                report_period_start=report_start,
                report_period_end=report_end,
            )
            raw_by_symbol[symbol] = raw
            source_rows_by_symbol[symbol] = int(len(raw))
        if provider_calls_issued != int(acceptance["provider_calls"]):
            raise RichDataError(
                "Tushare top10_floatholders acceptance did not issue exactly the "
                "frozen three requests"
            )

        source_frames: list[pd.DataFrame] = []
        factor_frames: list[pd.DataFrame] = []
        quality_by_symbol: dict[str, dict[str, int]] = {}
        minimum_groups = int(acceptance["minimum_complete_report_groups_per_symbol"])
        minimum_pairs = int(
            acceptance["minimum_factor_ready_consecutive_pairs_per_symbol"]
        )
        for symbol in symbols:
            raw = raw_by_symbol[symbol]
            if raw.empty:
                raise RichDataError(
                    f"Tushare top10_floatholders acceptance returned no rows for {symbol}"
                )
            normalized_source, factors, quality = (
                canonicalize_tushare_top10_float_holders(
                    raw,
                    expected_ts_code=symbol,
                    report_period_start=report_start,
                    report_period_end=report_end,
                    latest_announcement_date=latest_announcement,
                )
            )
            if quality["complete_report_groups"] < minimum_groups:
                raise RichDataError(
                    "Tushare top10_floatholders acceptance has too few complete "
                    f"report groups for {symbol}: "
                    f"{quality['complete_report_groups']} < {minimum_groups}"
                )
            if quality["factor_ready_consecutive_pairs"] < minimum_pairs:
                raise RichDataError(
                    "Tushare top10_floatholders acceptance has no frozen "
                    f"consecutive-quarter factor pair for {symbol}"
                )
            source_frames.append(normalized_source)
            factor_frames.append(factors)
            quality_by_symbol[symbol] = quality

        normalized_source = (
            pd.concat(source_frames, ignore_index=True)
            .sort_values(
                [
                    "instrument",
                    "report_period",
                    "announcement_date",
                    "holder_name_sha256",
                ],
                kind="stable",
            )
            .reset_index(drop=True)
        )
        factors = (
            pd.concat(factor_frames, ignore_index=True)
            .sort_values(
                ["instrument", "report_period", "announcement_date"], kind="stable"
            )
            .reset_index(drop=True)
        )
        if normalized_source.columns.tolist() != list(
            TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS
        ):
            raise RichDataError(
                "top-ten float acceptance source columns do not match the frozen schema"
            )
        if factors.columns.tolist() != list(TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS):
            raise RichDataError(
                "top-ten float acceptance factor columns do not match the frozen schema"
            )
        if normalized_source.duplicated(
            [
                "announcement_date",
                "report_period",
                "instrument",
                "holder_name_sha256",
            ]
        ).any():
            raise RichDataError(
                "top-ten float acceptance contains a duplicate persisted holder key"
            )
        if factors.duplicated(
            ["instrument", "announcement_date", "report_period"]
        ).any():
            raise RichDataError(
                "top-ten float acceptance contains a duplicate factor key"
            )

        temporary_source = temporary_root / "holders_hashed.parquet"
        temporary_factors = temporary_root / "concentration_changes.parquet"
        final_source = run_root / "holders_hashed.parquet"
        final_factors = run_root / "concentration_changes.parquet"
        atomic_write_frame(normalized_source, temporary_source)
        atomic_write_frame(factors, temporary_factors)
        changes = factors["top10_float_concentration_change_pp"]
        concentrations = factors["top10_float_concentration_pct"]
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_top10_float_concentration_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": report_start.isoformat(),
            "requested_end": report_end.isoformat(),
            "data_contract": {
                "path": manifest_path(
                    DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT
                ),
                "sha256": file_digest(
                    DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT
                ),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "top10_floatholders",
                "request_mode": "one stock and one frozen report-period range per call",
                "symbols": list(symbols),
                "provider_calls_issued": provider_calls_issued,
                "fields": list(TUSHARE_TOP10_FLOAT_RAW_FIELDS),
                "source_rows_returned_by_symbol": source_rows_by_symbol,
                "forbidden_fields_requested_or_stored": [],
                "plaintext_holder_names_logged_or_stored": False,
                "credentials_logged_or_stored": False,
            },
            "local_no_return_context": context,
            "files": [
                {
                    "role": "normalized_source_with_hashed_holder_identity",
                    "path": manifest_path(final_source),
                    "rows": int(len(normalized_source)),
                    "sha256": frame_digest(normalized_source),
                },
                {
                    "role": "first_disclosed_consecutive_quarter_factor",
                    "path": manifest_path(final_factors),
                    "rows": int(len(factors)),
                    "sha256": frame_digest(factors),
                },
            ],
            "source_quality": {
                "by_symbol": quality_by_symbol,
                "input_rows": int(sum(source_rows_by_symbol.values())),
                "source_rows_written": int(len(normalized_source)),
                "unique_instruments": int(normalized_source["instrument"].nunique()),
                "factor_ready_consecutive_pairs": int(len(factors)),
                "factor_min": float(changes.min()),
                "factor_max": float(changes.max()),
                "concentration_min": float(concentrations.min()),
                "concentration_max": float(concentrations.max()),
                "duplicate_persisted_holder_keys": 0,
                "duplicate_factor_keys": 0,
                "plaintext_holder_names_persisted": False,
                "holder_identity_hash": "sha256_nfkc_trimmed_whitespace_collapsed_utf8",
            },
            "availability_policy": {
                "source_time_field": "ann_date",
                "eligible_entry": "first local session open strictly after ann_date",
                "same_announcement_session_trade_allowed": False,
                "maximum_event_age_calendar_days": 3,
                "forward_fill_beyond_event_age_allowed": False,
            },
            "acceptance_status": acceptance["success_status"],
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_top10_float_concentration_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": report_start.isoformat(),
            "requested_end": report_end.isoformat(),
            "data_contract": {
                "path": manifest_path(
                    DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT
                ),
                "sha256": file_digest(
                    DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT
                ),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "top10_floatholders",
                "request_mode": "one stock and one frozen report-period range per call",
                "symbols": list(symbols),
                "provider_calls_issued": provider_calls_issued,
                "fields": list(TUSHARE_TOP10_FLOAT_RAW_FIELDS),
                "source_rows_returned_by_symbol": source_rows_by_symbol,
                "plaintext_holder_names_logged_or_stored": False,
                "credentials_logged_or_stored": False,
            },
            "local_no_return_context": context,
            "files": [],
            "acceptance_status": (
                "rejected_stop_before_full_history_capacity_uniqueness_or_returns"
            ),
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def sync_tushare_earnings_forecast_acceptance() -> Path:
    """Run the frozen three-stock forecast acceptance exactly once without prices."""

    terminal_path = DEFAULT_TUSHARE_EARNINGS_FORECAST_ACCEPTANCE_RECORD
    if terminal_path.exists():
        load_tushare_earnings_forecast_acceptance_record(terminal_path)
        raise RichDataError(
            "Tushare earnings-forecast branch is terminal after one request and "
            "prior-mechanism overlap; another acceptance is forbidden"
        )
    contract = load_tushare_earnings_forecast_contract()
    prior_records = tushare_earnings_forecast_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare earnings-forecast acceptance is one-shot and was already "
            "consumed: " + ", ".join(str(path) for path in prior_records)
        )
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    symbols = tuple(str(value) for value in acceptance["fixed_symbols"])
    announcement_start = dt.datetime.strptime(
        str(acceptance["fixed_announcement_start"]), "%Y%m%d"
    ).date()
    announcement_end = dt.datetime.strptime(
        str(acceptance["fixed_announcement_end"]), "%Y%m%d"
    ).date()
    validate_range(
        announcement_start,
        announcement_end,
        allow_large=True,
        unit_count=len(symbols),
    )
    run_id = new_run_id("tushare_earnings_forecast_acceptance")
    run_root = RAW_ROOT / "tushare" / "earnings_forecast" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(
            f"Tushare earnings-forecast acceptance already exists: {run_id}"
        )
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    calls_issued = 0
    current_symbol: str | None = None
    try:
        frames: list[pd.DataFrame] = []
        quality_by_symbol: dict[str, dict[str, Any]] = {}
        total_source_rows = 0
        row_ceiling = int(
            contract["full_snapshot_contract"][
                "local_truncation_suspicion_row_ceiling_per_stock"
            ]
        )
        for symbol in symbols:
            current_symbol = symbol
            calls_issued += 1
            raw = fetch_tushare_earnings_forecast(
                symbol, announcement_start, announcement_end
            )
            total_source_rows += int(len(raw))
            if len(raw) >= row_ceiling:
                raise RichDataError(
                    "Tushare forecast acceptance reached the frozen local "
                    f"truncation-suspicion ceiling for {symbol}: {len(raw)}"
                )
            normalized, quality = canonicalize_tushare_earnings_forecast(
                raw,
                expected_ts_code=symbol,
                announcement_start=announcement_start,
                announcement_end=announcement_end,
            )
            quality_by_symbol[symbol] = quality
            frames.append(normalized)
        if calls_issued != int(acceptance["provider_calls"]):
            raise RichDataError(
                "Tushare earnings-forecast acceptance omitted a frozen request"
            )
        if total_source_rows < int(acceptance["minimum_total_source_rows"]):
            raise RichDataError(
                "Tushare earnings-forecast acceptance returned too few source rows: "
                f"{total_source_rows}"
            )
        combined = (
            pd.concat(frames, ignore_index=True)
            if frames
            else pd.DataFrame(columns=TUSHARE_EARNINGS_FORECAST_COLUMNS)
        )
        symbols_with_events = int(combined["instrument"].nunique())
        if symbols_with_events < int(
            acceptance["minimum_symbols_with_one_comparable_event"]
        ):
            raise RichDataError(
                "Tushare earnings-forecast acceptance retained comparable events "
                f"for only {symbols_with_events} frozen symbols"
            )
        event_key = ["instrument", "announcement_date", "report_period"]
        if combined.duplicated(event_key).any():
            raise RichDataError(
                "Tushare earnings-forecast acceptance has duplicate event keys"
            )
        combined = combined.sort_values(
            ["announcement_date", "instrument", "report_period"], kind="stable"
        ).reset_index(drop=True)
        temporary_destination = temporary_root / "earnings_forecast.parquet"
        final_destination = run_root / "earnings_forecast.parquet"
        atomic_write_frame(combined, temporary_destination)
        factor_name = "tushare_earnings_forecast_growth_midpoint"
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_earnings_forecast_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": announcement_start.isoformat(),
            "requested_end": announcement_end.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_EARNINGS_FORECAST_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_EARNINGS_FORECAST_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "forecast",
                "request_mode": "one stock and one frozen announcement-date range per call",
                "symbols": list(symbols),
                "provider_calls_issued": calls_issued,
                "fields": list(TUSHARE_EARNINGS_FORECAST_RAW_FIELDS),
                "forecast_vip_requested": False,
                "forbidden_fields_requested_or_stored": [],
                "raw_frames_persisted": False,
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(combined)),
                    "sha256": frame_digest(combined),
                }
            ],
            "source_quality": {
                "source_rows": total_source_rows,
                "rows_written": int(len(combined)),
                "symbols_with_comparable_events": symbols_with_events,
                "quality_by_symbol": quality_by_symbol,
                "duplicate_event_keys": 0,
                "factor_min": float(combined[factor_name].min()),
                "factor_max": float(combined[factor_name].max()),
            },
            "factor_policy": {
                "factor": factor_name,
                "formula": "(p_change_min + p_change_max) / 2",
                "direction": "higher_is_better",
                "comparable_types": list(
                    contract["point_in_time_and_version_policy"][
                        "comparable_forecast_types"
                    ]
                ),
                "noncomparable_types_excluded": list(
                    contract["point_in_time_and_version_policy"][
                        "non_comparable_types_excluded_and_counted"
                    ]
                ),
            },
            "availability_policy": {
                "event_date": "ann_date",
                "same_session_trade_allowed": False,
                "eligible_entry": "following local session open",
                "maximum_event_age_calendar_days": 3,
                "forward_fill_beyond_event_age_allowed": False,
            },
            "acceptance_status": acceptance["success_status"],
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_earnings_forecast_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": announcement_start.isoformat(),
            "requested_end": announcement_end.isoformat(),
            "failed_symbol": current_symbol,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_EARNINGS_FORECAST_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_EARNINGS_FORECAST_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "forecast",
                "symbols": list(symbols),
                "provider_calls_issued": calls_issued,
                "fields": list(TUSHARE_EARNINGS_FORECAST_RAW_FIELDS),
                "forecast_vip_requested": False,
                "credentials_logged_or_stored": False,
            },
            "files": [],
            "partial_snapshot_deleted": not temporary_root.exists(),
            "final_snapshot_published": run_root.exists(),
            "acceptance_status": "rejected_stop_before_full_history_or_returns",
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def sync_tushare_disclosure_promptness_acceptance() -> Path:
    """Run the frozen three-period disclosure-plan acceptance without prices."""

    terminal_path = DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_ACCEPTANCE_RECORD
    if terminal_path.exists():
        load_tushare_disclosure_promptness_acceptance_record(terminal_path)
        raise RichDataError(
            "Tushare disclosure-promptness branch is terminal after the first "
            "report-period rejection; another acceptance is forbidden"
        )
    contract = load_tushare_disclosure_promptness_contract()
    prior_records = tushare_disclosure_promptness_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare disclosure-promptness acceptance is one-shot and was already "
            "consumed: " + ", ".join(str(path) for path in prior_records)
        )
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    period_values = tuple(str(value) for value in acceptance["fixed_report_periods"])
    periods = tuple(
        dt.datetime.strptime(value, "%Y%m%d").date() for value in period_values
    )
    run_id = new_run_id("tushare_disclosure_promptness_acceptance")
    run_root = RAW_ROOT / "tushare" / "disclosure_promptness" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(
            f"Tushare disclosure-promptness acceptance already exists: {run_id}"
        )
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    calls_issued = 0
    current_period: str | None = None
    source_rows_by_period: dict[str, int] = {}
    quality_by_period: dict[str, dict[str, Any]] = {}
    try:
        frames: list[pd.DataFrame] = []
        row_ceiling = int(
            contract["source_selection"]["provider_documented_maximum_rows_per_call"]
        )
        for period in periods:
            current_period = period.strftime("%Y%m%d")
            calls_issued += 1
            raw = fetch_tushare_disclosure_plan(period)
            source_rows_by_period[current_period] = int(len(raw))
            if len(raw) >= row_ceiling:
                raise RichDataError(
                    "Tushare disclosure-promptness acceptance reached the frozen "
                    f"6000-row truncation ceiling for {current_period}: {len(raw)}"
                )
            if len(raw) < int(acceptance["minimum_source_rows_per_period"]):
                raise RichDataError(
                    "Tushare disclosure-promptness acceptance returned too few "
                    f"source rows for {current_period}: {len(raw)}"
                )
            normalized, quality = canonicalize_tushare_disclosure_plan(raw, period)
            quality_by_period[current_period] = quality
            if len(normalized) < int(acceptance["minimum_retained_rows_per_period"]):
                raise RichDataError(
                    "Tushare disclosure-promptness acceptance retained too few "
                    f"rows for {current_period}: {len(normalized)}"
                )
            if quality["distinct_lead_days"] < int(
                acceptance["minimum_distinct_lead_days_per_period"]
            ):
                raise RichDataError(
                    "Tushare disclosure-promptness acceptance has too few distinct "
                    f"lead-day values for {current_period}: "
                    f"{quality['distinct_lead_days']}"
                )
            frames.append(normalized)
        if calls_issued != int(acceptance["provider_calls"]):
            raise RichDataError(
                "Tushare disclosure-promptness acceptance omitted a frozen request"
            )
        combined = pd.concat(frames, ignore_index=True)
        event_key = ["instrument", "report_period"]
        if combined.duplicated(event_key).any():
            raise RichDataError(
                "Tushare disclosure-promptness acceptance has duplicate stock-period keys"
            )
        combined = combined.sort_values(
            ["announcement_date", "instrument", "report_period"], kind="stable"
        ).reset_index(drop=True)
        temporary_destination = temporary_root / "disclosure_promptness.parquet"
        final_destination = run_root / "disclosure_promptness.parquet"
        atomic_write_frame(combined, temporary_destination)
        factor_name = "tushare_disclosure_plan_lead_days"
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_disclosure_promptness_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "disclosure_date",
                "request_mode": "one frozen report period per call",
                "report_periods": list(period_values),
                "provider_calls_issued": calls_issued,
                "fields": list(TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS),
                "actual_date_requested_or_stored": False,
                "raw_frames_persisted": False,
                "modify_date_values_persisted": False,
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(combined)),
                    "sha256": frame_digest(combined),
                }
            ],
            "source_quality": {
                "source_rows": int(sum(source_rows_by_period.values())),
                "source_rows_by_period": source_rows_by_period,
                "rows_written": int(len(combined)),
                "quality_by_period": quality_by_period,
                "outside_target_bj_rows_excluded": int(
                    sum(
                        value["outside_target_bj_rows_excluded"]
                        for value in quality_by_period.values()
                    )
                ),
                "modify_date_context_rows": int(
                    sum(
                        value["modify_date_context_rows"]
                        for value in quality_by_period.values()
                    )
                ),
                "duplicate_stock_report_period_keys": 0,
                "factor_min": int(combined[factor_name].min()),
                "factor_max": int(combined[factor_name].max()),
                "factor_distinct_values": int(combined[factor_name].nunique()),
            },
            "factor_policy": {
                "factor": "tushare_disclosure_plan_promptness",
                "raw_column": factor_name,
                "formula": "calendar_days(pre_date - ann_date)",
                "direction": "lower_is_better",
                "score_if_all_future_gates_pass": (
                    "1 - cross_sectional_percentile_rank("
                    "tushare_disclosure_plan_lead_days)"
                ),
            },
            "availability_policy": {
                "event_date": "ann_date",
                "same_session_trade_allowed": False,
                "eligible_entry": "first local trading session open strictly after ann_date",
                "maximum_event_age_calendar_days": 3,
                "forward_fill_beyond_event_age_allowed": False,
            },
            "acceptance_status": acceptance["success_status"],
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_disclosure_promptness_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "failed_report_period": current_period,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "disclosure_date",
                "report_periods": list(period_values),
                "provider_calls_issued": calls_issued,
                "source_rows_by_period": source_rows_by_period,
                "fields": list(TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS),
                "actual_date_requested_or_stored": False,
                "modify_date_values_persisted": False,
                "credentials_logged_or_stored": False,
            },
            "completed_period_quality": quality_by_period,
            "files": [],
            "partial_snapshot_deleted": not temporary_root.exists(),
            "final_snapshot_published": run_root.exists(),
            "acceptance_status": (
                "rejected_stop_before_full_history_capacity_uniqueness_or_returns"
            ),
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def sync_tushare_audit_opinion_acceptance() -> Path:
    """Run the frozen three-stock audit-opinion acceptance without prices."""

    accepted_path = DEFAULT_TUSHARE_AUDIT_OPINION_ACCEPTANCE_RECORD
    if accepted_path.exists():
        load_tushare_audit_opinion_acceptance_record(accepted_path)
        raise RichDataError(
            "Tushare audit-opinion source acceptance is already consumed; another "
            "acceptance is forbidden"
        )
    contract = load_tushare_audit_opinion_contract()
    prior_records = tushare_audit_opinion_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare audit-opinion acceptance is one-shot and was already consumed: "
            + ", ".join(str(path) for path in prior_records)
        )
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    ts_codes = tuple(str(value) for value in acceptance["fixed_ts_codes"])
    announcement_start = dt.datetime.strptime(
        str(acceptance["announcement_start"]), "%Y%m%d"
    ).date()
    announcement_end = dt.datetime.strptime(
        str(acceptance["announcement_end"]), "%Y%m%d"
    ).date()
    run_id = new_run_id("tushare_audit_opinion_acceptance")
    run_root = RAW_ROOT / "tushare" / "audit_opinion" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(
            f"Tushare audit-opinion acceptance already exists: {run_id}"
        )
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    calls_issued = 0
    current_ts_code: str | None = None
    source_rows_by_stock: dict[str, int] = {}
    quality_by_stock: dict[str, dict[str, Any]] = {}
    try:
        frames: list[pd.DataFrame] = []
        row_ceiling = int(
            contract["source_selection"]["defensive_maximum_rows_per_single_stock_call"]
        )
        for ts_code in ts_codes:
            current_ts_code = ts_code
            calls_issued += 1
            raw = fetch_tushare_audit_opinions(
                ts_code, announcement_start, announcement_end
            )
            source_rows_by_stock[ts_code] = int(len(raw))
            if len(raw) >= row_ceiling:
                raise RichDataError(
                    "Tushare audit-opinion acceptance reached the frozen defensive "
                    f"row ceiling for {ts_code}: {len(raw)}"
                )
            if len(raw) < int(acceptance["minimum_source_rows_per_stock"]):
                raise RichDataError(
                    "Tushare audit-opinion acceptance returned too few source rows "
                    f"for {ts_code}: {len(raw)}"
                )
            normalized, quality = canonicalize_tushare_audit_opinions(
                raw, ts_code, announcement_start, announcement_end
            )
            quality_by_stock[ts_code] = quality
            if quality["source_report_rows_retained"] < int(
                acceptance["minimum_retained_rows_per_stock"]
            ):
                raise RichDataError(
                    "Tushare audit-opinion acceptance retained too few report rows "
                    f"for {ts_code}: {quality['source_report_rows_retained']}"
                )
            frames.append(normalized)
        if calls_issued != int(acceptance["provider_calls"]):
            raise RichDataError(
                "Tushare audit-opinion acceptance omitted a frozen request"
            )
        combined = pd.concat(frames, ignore_index=True)
        event_key = ["instrument", "announcement_date"]
        if combined.duplicated(event_key).any():
            raise RichDataError(
                "Tushare audit-opinion acceptance has duplicate stock-announcement keys"
            )
        combined = combined.sort_values(event_key, kind="stable").reset_index(drop=True)
        hashed_category_counts: dict[str, int] = {}
        for quality in quality_by_stock.values():
            for category_hash, count in quality[
                "hashed_opinion_category_counts"
            ].items():
                hashed_category_counts[category_hash] = hashed_category_counts.get(
                    category_hash, 0
                ) + int(count)
        if len(hashed_category_counts) < int(
            acceptance["minimum_distinct_hashed_opinion_categories_across_acceptance"]
        ):
            raise RichDataError(
                "Tushare audit-opinion acceptance has too few distinct hashed opinion "
                f"categories: {len(hashed_category_counts)}"
            )
        factor_name = "tushare_is_standard_unqualified_audit_opinion"
        distinct_factor_values = int(combined[factor_name].nunique())
        if distinct_factor_values < int(
            acceptance["minimum_distinct_factor_values_across_acceptance"]
        ):
            raise RichDataError(
                "Tushare audit-opinion acceptance has too few distinct binary factor "
                f"values: {distinct_factor_values}"
            )
        temporary_destination = temporary_root / "audit_opinion.parquet"
        final_destination = run_root / "audit_opinion.parquet"
        atomic_write_frame(combined, temporary_destination)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_audit_opinion_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_AUDIT_OPINION_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_AUDIT_OPINION_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "fina_audit",
                "request_mode": "one frozen stock and announcement-date range per call",
                "ts_codes": list(ts_codes),
                "announcement_start": acceptance["announcement_start"],
                "announcement_end": acceptance["announcement_end"],
                "provider_calls_issued": calls_issued,
                "fields": list(TUSHARE_AUDIT_OPINION_RAW_FIELDS),
                "raw_frames_persisted": False,
                "raw_or_normalized_audit_result_text_persisted": False,
                "audit_fee_agency_or_signer_requested": False,
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(combined)),
                    "sha256": frame_digest(combined),
                }
            ],
            "source_quality": {
                "source_rows": int(sum(source_rows_by_stock.values())),
                "source_rows_by_stock": source_rows_by_stock,
                "quality_by_stock": quality_by_stock,
                "stock_announcement_events_written": int(len(combined)),
                "duplicate_stock_announcement_keys": 0,
                "hashed_opinion_category_counts": dict(
                    sorted(hashed_category_counts.items())
                ),
                "distinct_hashed_opinion_categories": int(len(hashed_category_counts)),
                "factor_distinct_values": distinct_factor_values,
                "factor_value_counts": {
                    str(int(key)): int(value)
                    for key, value in combined[factor_name]
                    .value_counts()
                    .sort_index()
                    .items()
                },
            },
            "factor_policy": {
                "factor": "tushare_standard_unqualified_audit_opinion",
                "raw_column": factor_name,
                "formula": (
                    "1 if NFKC_trim(audit_result) == '标准无保留意见' else 0 "
                    "for any other complete nonempty opinion"
                ),
                "direction": "higher_is_better",
                "text_synonym_mapping_allowed": False,
            },
            "availability_policy": {
                "event_date": "ann_date",
                "same_session_trade_allowed": False,
                "eligible_entry": (
                    "first local trading session open strictly after ann_date"
                ),
                "maximum_event_age_calendar_days": 3,
                "forward_fill_beyond_event_age_allowed": False,
            },
            "acceptance_status": acceptance["success_status"],
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_audit_opinion_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "failed_ts_code": current_ts_code,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_AUDIT_OPINION_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_AUDIT_OPINION_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "fina_audit",
                "ts_codes": list(ts_codes),
                "announcement_start": acceptance["announcement_start"],
                "announcement_end": acceptance["announcement_end"],
                "provider_calls_issued": calls_issued,
                "source_rows_by_stock": source_rows_by_stock,
                "fields": list(TUSHARE_AUDIT_OPINION_RAW_FIELDS),
                "raw_frames_persisted": False,
                "raw_or_normalized_audit_result_text_persisted": False,
                "audit_fee_agency_or_signer_requested": False,
                "credentials_logged_or_stored": False,
            },
            "completed_stock_quality": quality_by_stock,
            "files": [],
            "partial_snapshot_deleted": not temporary_root.exists(),
            "final_snapshot_published": run_root.exists(),
            "acceptance_status": (
                "rejected_stop_before_full_history_capacity_uniqueness_or_returns"
            ),
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def sync_tushare_gross_margin_acceptance() -> Path:
    """Run the frozen three-stock initial gross-margin acceptance without prices."""

    accepted_path = DEFAULT_TUSHARE_GROSS_MARGIN_ACCEPTANCE_RECORD
    if accepted_path.exists():
        load_tushare_gross_margin_acceptance_record(accepted_path)
        raise RichDataError(
            "Tushare gross-margin source acceptance is already consumed; another "
            "acceptance is forbidden"
        )
    contract = load_tushare_gross_margin_contract()
    prior_records = tushare_gross_margin_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare gross-margin acceptance is one-shot and was already consumed: "
            + ", ".join(str(path) for path in prior_records)
        )
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    ts_codes = tuple(str(value) for value in acceptance["fixed_ts_codes"])
    report_period_start = dt.datetime.strptime(
        str(acceptance["report_period_start"]), "%Y%m%d"
    ).date()
    report_period_end = dt.datetime.strptime(
        str(acceptance["report_period_end"]), "%Y%m%d"
    ).date()
    run_id = new_run_id("tushare_gross_margin_acceptance")
    run_root = RAW_ROOT / "tushare" / "gross_margin" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare gross-margin acceptance already exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    calls_issued = 0
    current_ts_code: str | None = None
    source_rows_by_stock: dict[str, int] = {}
    quality_by_stock: dict[str, dict[str, Any]] = {}
    try:
        frames: list[pd.DataFrame] = []
        row_ceiling = int(
            contract["source_selection"]["provider_documented_maximum_rows_per_call"]
        )
        for ts_code in ts_codes:
            current_ts_code = ts_code
            calls_issued += 1
            raw = fetch_tushare_gross_margin_indicators(
                ts_code, report_period_start, report_period_end
            )
            source_rows_by_stock[ts_code] = int(len(raw))
            if len(raw) >= row_ceiling:
                raise RichDataError(
                    "Tushare gross-margin acceptance reached the documented row "
                    f"ceiling for {ts_code}: {len(raw)}"
                )
            if len(raw) < int(acceptance["minimum_source_rows_per_stock"]):
                raise RichDataError(
                    "Tushare gross-margin acceptance returned too few source rows "
                    f"for {ts_code}: {len(raw)}"
                )
            normalized, quality = canonicalize_tushare_gross_margin_indicators(
                raw, ts_code, report_period_start, report_period_end
            )
            quality_by_stock[ts_code] = quality
            if quality["initial_quarter_rows_retained"] < int(
                acceptance["minimum_initial_quarter_rows_per_stock"]
            ):
                raise RichDataError(
                    "Tushare gross-margin acceptance retained too few initial "
                    f"quarters for {ts_code}: "
                    f"{quality['initial_quarter_rows_retained']}"
                )
            if quality["derived_yoy_events_written"] < int(
                acceptance["minimum_derived_yoy_events_per_stock"]
            ):
                raise RichDataError(
                    "Tushare gross-margin acceptance derived too few year-over-year "
                    f"events for {ts_code}: {quality['derived_yoy_events_written']}"
                )
            frames.append(normalized)
        if calls_issued != int(acceptance["provider_calls"]):
            raise RichDataError(
                "Tushare gross-margin acceptance omitted a frozen request"
            )
        combined = pd.concat(frames, ignore_index=True)
        event_key = ["instrument", "announcement_date", "report_period"]
        if combined.duplicated(event_key).any():
            raise RichDataError(
                "Tushare gross-margin acceptance has duplicate stock-event keys"
            )
        combined = combined.sort_values(event_key, kind="stable").reset_index(drop=True)
        factor_name = "tushare_q_gross_margin_yoy_change_pp"
        distinct_values = int(combined[factor_name].nunique())
        if distinct_values < int(
            acceptance["minimum_distinct_derived_values_across_acceptance"]
        ):
            raise RichDataError(
                "Tushare gross-margin acceptance has too few distinct factor values: "
                f"{distinct_values}"
            )
        temporary_destination = temporary_root / "gross_margin_yoy_change.parquet"
        final_destination = run_root / "gross_margin_yoy_change.parquet"
        atomic_write_frame(combined, temporary_destination)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_gross_margin_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_GROSS_MARGIN_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_GROSS_MARGIN_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "fina_indicator",
                "request_mode": "one frozen stock and report-period range per call",
                "ts_codes": list(ts_codes),
                "report_period_start": acceptance["report_period_start"],
                "report_period_end": acceptance["report_period_end"],
                "provider_calls_issued": calls_issued,
                "fields": list(TUSHARE_GROSS_MARGIN_RAW_FIELDS),
                "source_rows_by_stock": source_rows_by_stock,
                "provider_documented_row_ceiling": row_ceiling,
                "raw_frames_persisted": False,
                "revised_values_persisted": False,
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(combined)),
                    "sha256": frame_digest(combined),
                }
            ],
            "source_quality": {
                "source_rows": int(sum(source_rows_by_stock.values())),
                "source_rows_by_stock": source_rows_by_stock,
                "rows_written": int(len(combined)),
                "quality_by_stock": quality_by_stock,
                "duplicate_factor_event_keys": 0,
                "initial_rows_retained": int(
                    sum(
                        value["initial_quarter_rows_retained"]
                        for value in quality_by_stock.values()
                    )
                ),
                "revised_rows_observed_but_not_used": int(
                    sum(
                        value["revised_rows_observed"]
                        for value in quality_by_stock.values()
                    )
                ),
                "factor_distinct_values": distinct_values,
                "factor_min": float(combined[factor_name].min()),
                "factor_max": float(combined[factor_name].max()),
            },
            "factor_policy": {
                "factor": "tushare_single_quarter_gross_margin_yoy_change",
                "raw_column": factor_name,
                "formula": (
                    "current_initial_q_gsprofit_margin - "
                    "same_fiscal_quarter_previous_year_initial_q_gsprofit_margin"
                ),
                "units": "percentage_points",
                "direction": "higher_is_better",
                "revised_rows_used": False,
            },
            "availability_policy": {
                "event_date": "current initial ann_date",
                "same_session_trade_allowed": False,
                "eligible_entry": (
                    "first local trading session open strictly after the current "
                    "initial ann_date"
                ),
                "maximum_event_age_calendar_days": 3,
                "forward_fill_beyond_event_age_allowed": False,
            },
            "acceptance_status": acceptance["success_status"],
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_gross_margin_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "failed_ts_code": current_ts_code,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_GROSS_MARGIN_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_GROSS_MARGIN_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "fina_indicator",
                "ts_codes": list(ts_codes),
                "report_period_start": acceptance["report_period_start"],
                "report_period_end": acceptance["report_period_end"],
                "provider_calls_issued": calls_issued,
                "source_rows_by_stock": source_rows_by_stock,
                "fields": list(TUSHARE_GROSS_MARGIN_RAW_FIELDS),
                "raw_frames_persisted": False,
                "revised_values_persisted": False,
                "credentials_logged_or_stored": False,
            },
            "completed_stock_quality": quality_by_stock,
            "files": [],
            "partial_snapshot_deleted": not temporary_root.exists(),
            "final_snapshot_published": run_root.exists(),
            "acceptance_status": (
                "rejected_stop_before_full_history_capacity_uniqueness_or_returns"
            ),
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def sync_tushare_management_continuity_acceptance() -> Path:
    """Run the frozen three-stock management-continuity acceptance without prices."""

    if DEFAULT_TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_RECORD.exists():
        load_tushare_management_continuity_acceptance_record(
            DEFAULT_TUSHARE_MANAGEMENT_CONTINUITY_ACCEPTANCE_RECORD
        )
        raise RichDataError(
            "Tushare management-continuity source acceptance is already consumed; "
            "another acceptance is forbidden"
        )
    contract = load_tushare_management_continuity_contract()
    prior_records = tushare_management_continuity_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare management-continuity acceptance is one-shot and was already "
            "consumed: " + ", ".join(str(path) for path in prior_records)
        )
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    ts_codes = tuple(str(value) for value in acceptance["fixed_ts_codes"])
    announcement_start = dt.datetime.strptime(
        str(acceptance["announcement_start"]), "%Y%m%d"
    ).date()
    announcement_end = dt.datetime.strptime(
        str(acceptance["announcement_end"]), "%Y%m%d"
    ).date()
    run_id = new_run_id("tushare_management_continuity_acceptance")
    run_root = RAW_ROOT / "tushare" / "management_continuity" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(
            f"Tushare management-continuity acceptance already exists: {run_id}"
        )
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    calls_issued = 0
    current_ts_code: str | None = None
    source_rows_by_stock: dict[str, int] = {}
    quality_by_stock: dict[str, dict[str, Any]] = {}
    try:
        frames: list[pd.DataFrame] = []
        row_ceiling = int(
            contract["source_selection"]["defensive_response_row_ceiling"]
        )
        for ts_code in ts_codes:
            current_ts_code = ts_code
            calls_issued += 1
            raw = fetch_tushare_management_continuity_rows(
                ts_code, announcement_start, announcement_end
            )
            source_rows_by_stock[ts_code] = int(len(raw))
            if len(raw) >= row_ceiling:
                raise RichDataError(
                    "Tushare management-continuity acceptance reached the frozen "
                    f"defensive row ceiling for {ts_code}: {len(raw)}"
                )
            if len(raw) < int(acceptance["minimum_source_rows_per_stock"]):
                raise RichDataError(
                    "Tushare management-continuity acceptance returned too few "
                    f"source rows for {ts_code}: {len(raw)}"
                )
            normalized, quality = canonicalize_tushare_management_continuity(
                raw, ts_code, announcement_start, announcement_end
            )
            quality_by_stock[ts_code] = quality
            if quality["stock_announcement_events_written"] < int(
                acceptance["minimum_events_per_stock"]
            ):
                raise RichDataError(
                    "Tushare management-continuity acceptance produced too few "
                    f"events for {ts_code}: "
                    f"{quality['stock_announcement_events_written']}"
                )
            frames.append(normalized)
        if calls_issued != int(acceptance["provider_calls"]):
            raise RichDataError(
                "Tushare management-continuity acceptance omitted a frozen request"
            )
        combined = pd.concat(frames, ignore_index=True)
        event_key = ["instrument", "announcement_date"]
        if combined.duplicated(event_key).any():
            raise RichDataError(
                "Tushare management-continuity acceptance has duplicate stock-event keys"
            )
        combined = combined.sort_values(event_key, kind="stable").reset_index(drop=True)
        if len(combined) < int(acceptance["minimum_events_across_acceptance"]):
            raise RichDataError(
                "Tushare management-continuity acceptance produced too few combined "
                f"events: {len(combined)}"
            )
        factor_name = "tushare_management_continuity_share"
        distinct_values = int(combined[factor_name].nunique())
        if distinct_values < int(
            acceptance["minimum_distinct_factor_values_across_acceptance"]
        ):
            raise RichDataError(
                "Tushare management-continuity acceptance has too few distinct factor "
                f"values: {distinct_values}"
            )
        total_identities = int(combined["manager_count"].sum())
        departing_identities = int(combined["departing_manager_count"].sum())
        nondeparting_identities = total_identities - departing_identities
        if departing_identities < 1:
            raise RichDataError(
                "Tushare management-continuity acceptance observed no departing identity"
            )
        if nondeparting_identities < 1:
            raise RichDataError(
                "Tushare management-continuity acceptance observed no nondeparting identity"
            )
        temporary_destination = temporary_root / "management_continuity.parquet"
        final_destination = run_root / "management_continuity.parquet"
        atomic_write_frame(combined, temporary_destination)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_management_continuity_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_MANAGEMENT_CONTINUITY_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_MANAGEMENT_CONTINUITY_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "stk_managers",
                "request_mode": (
                    "one frozen stock and announcement-date range per call"
                ),
                "ts_codes": list(ts_codes),
                "announcement_start": acceptance["announcement_start"],
                "announcement_end": acceptance["announcement_end"],
                "provider_calls_issued": calls_issued,
                "fields": list(TUSHARE_MANAGEMENT_CONTINUITY_RAW_FIELDS),
                "raw_frames_persisted": False,
                "plaintext_names_persisted": False,
                "identity_hashes_persisted": False,
                "forbidden_personal_or_role_fields_requested": False,
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(combined)),
                    "sha256": frame_digest(combined),
                }
            ],
            "source_quality": {
                "source_rows": int(sum(source_rows_by_stock.values())),
                "source_rows_by_stock": source_rows_by_stock,
                "quality_by_stock": quality_by_stock,
                "stock_announcement_events_written": int(len(combined)),
                "duplicate_stock_announcement_keys": 0,
                "manager_identity_rows": total_identities,
                "departing_identity_rows": departing_identities,
                "nondeparting_identity_rows": nondeparting_identities,
                "factor_distinct_values": distinct_values,
                "minimum_factor_value": float(combined[factor_name].min()),
                "maximum_factor_value": float(combined[factor_name].max()),
            },
            "factor_policy": {
                "factor": "tushare_management_continuity",
                "raw_column": factor_name,
                "formula": "1 - departing_manager_count / manager_count",
                "direction": "higher_is_better",
                "end_date_must_equal_ann_date_when_present": True,
                "title_or_role_weighting_allowed": False,
            },
            "privacy_policy": {
                "name_used_only_for_in_memory_identity_deduplication": True,
                "plaintext_name_persisted": False,
                "identity_hash_persisted": False,
                "provider_raw_frame_persisted": False,
            },
            "availability_policy": {
                "event_date": "ann_date",
                "same_session_trade_allowed": False,
                "eligible_entry": (
                    "first local trading session open strictly after ann_date"
                ),
                "maximum_event_age_calendar_days": 3,
                "forward_fill_beyond_event_age_allowed": False,
            },
            "acceptance_status": acceptance["success_status"],
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_management_continuity_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "failed_ts_code": current_ts_code,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_MANAGEMENT_CONTINUITY_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_MANAGEMENT_CONTINUITY_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "stk_managers",
                "ts_codes": list(ts_codes),
                "announcement_start": acceptance["announcement_start"],
                "announcement_end": acceptance["announcement_end"],
                "provider_calls_issued": calls_issued,
                "source_rows_by_stock": source_rows_by_stock,
                "fields": list(TUSHARE_MANAGEMENT_CONTINUITY_RAW_FIELDS),
                "raw_frames_persisted": False,
                "plaintext_names_persisted": False,
                "identity_hashes_persisted": False,
                "forbidden_personal_or_role_fields_requested": False,
                "credentials_logged_or_stored": False,
            },
            "completed_stock_quality": quality_by_stock,
            "files": [],
            "partial_snapshot_deleted": not temporary_root.exists(),
            "final_snapshot_published": run_root.exists(),
            "acceptance_status": (
                "rejected_stop_before_full_history_capacity_uniqueness_or_returns"
            ),
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def _fetch_tushare_stock_st_with_policy(
    trade_date: dt.date,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    retry_backoffs: list[float],
    last_request_started: list[float | None],
    request_attempts: list[int],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded session retry policy."""

    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        request_attempts[0] += 1
        try:
            return fetch_tushare_stock_st_membership(trade_date)
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[attempt])
    raise AssertionError("unreachable Tushare stock_st retry state")


def sync_tushare_stock_st_membership(
    *,
    allow_large: bool = False,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the one-shot complete 2019-2025 ST membership without factor values."""

    dataset = "tushare_stock_st_membership"
    with RichDataProcessLock(METADATA_ROOT / ".tushare_stock_st_membership.lock"):
        if DEFAULT_TUSHARE_ST_RECOVERY_RESEARCH_RECORD.exists():
            load_tushare_st_recovery_research_record()
            raise RichDataError(
                "Tushare ST-recovery branch is terminal after its sole full-source "
                "continuity failure; another full sync is forbidden"
            )
        prior_records = tushare_stock_st_full_snapshot_records()
        if prior_records:
            raise RichDataError(
                "Tushare stock_st full-source contract is already consumed: "
                + ", ".join(str(path) for path in prior_records)
            )
        source_chain = load_tushare_st_recovery_source_chain()
        contract = source_chain["contract"]
        snapshot = contract["full_snapshot_contract"]
        start = dt.date.fromisoformat(str(snapshot["requested_start"]))
        end = dt.date.fromisoformat(str(snapshot["requested_end"]))
        validate_range(start, end, allow_large=allow_large, unit_count=1)
        resolved_calendar = calendar_path.expanduser().resolve()
        expected_calendar = contract["local_context"]["calendar"]
        if not resolved_calendar.exists() or file_digest(resolved_calendar) != str(
            expected_calendar["file_sha256"]
        ):
            raise RichDataError("Tushare stock_st local calendar fingerprint mismatch")
        calendar = local_calendar_dates(start, end, resolved_calendar)
        expected_sessions = int(snapshot["requested_local_sessions"])
        if len(calendar) != expected_sessions:
            raise RichDataError(
                "Tushare stock_st local calendar session count changed: "
                f"expected {expected_sessions}, observed {len(calendar)}"
            )
        if calendar.empty:
            raise RichDataError("Tushare stock_st local calendar is empty")
        require_provider("tushare")

        run_id = new_run_id("tushare_stock_st_membership")
        parent = RAW_ROOT / "tushare" / "stock_st" / "membership" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(f"Tushare stock_st snapshot already exists: {run_id}")
        temporary_root.mkdir(parents=True)
        retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
        minimum_interval = float(snapshot["minimum_seconds_between_calls"])
        maximum_attempts = int(snapshot["maximum_attempts_per_session"])
        retry_backoffs = [float(value) for value in snapshot["retry_backoff_seconds"]]
        row_ceiling = int(
            contract["source_selection"]["documented_maximum_rows_per_call"]
        )
        last_request_started: list[float | None] = [None]
        request_attempts = [0]
        logical_sessions_issued = 0
        logical_sessions_completed = 0
        source_rows_observed = 0
        current_session: str | None = None
        files: list[dict[str, Any]] = []
        daily_quality: list[dict[str, Any]] = []
        total_bj_excluded = 0
        total_rows_written = 0
        published_manifest: Path | None = None
        try:
            for year in range(start.year, end.year + 1):
                partition_start = max(start, dt.date(year, 1, 1))
                partition_end = min(end, dt.date(year, 12, 31))
                partition_calendar = calendar[
                    (calendar >= pd.Timestamp(partition_start))
                    & (calendar <= pd.Timestamp(partition_end))
                ]
                if partition_calendar.empty:
                    raise RichDataError(
                        f"Tushare stock_st required {year} partition has no sessions"
                    )
                year_frames: list[pd.DataFrame] = []
                year_source_rows = 0
                year_bj_excluded = 0
                year_rows_written = 0
                for session in partition_calendar:
                    session_date = pd.Timestamp(session).date()
                    current_session = session_date.isoformat()
                    logical_sessions_issued += 1
                    raw = _fetch_tushare_stock_st_with_policy(
                        session_date,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        retry_backoffs=retry_backoffs,
                        last_request_started=last_request_started,
                        request_attempts=request_attempts,
                    )
                    source_rows = int(len(raw))
                    source_rows_observed += source_rows
                    year_source_rows += source_rows
                    if source_rows >= row_ceiling:
                        raise RichDataError(
                            f"Tushare stock_st {current_session} reached the strict "
                            f"{row_ceiling}-row ceiling"
                        )
                    normalized, quality = canonicalize_tushare_stock_st_membership(
                        raw, session_date
                    )
                    logical_sessions_completed += 1
                    bj_excluded = int(quality["outside_target_bj_rows_excluded"])
                    rows_written = int(quality["rows_written"])
                    total_bj_excluded += bj_excluded
                    total_rows_written += rows_written
                    year_bj_excluded += bj_excluded
                    year_rows_written += rows_written
                    daily_quality.append(
                        {
                            "trade_date": current_session,
                            "source_rows": source_rows,
                            "outside_target_bj_rows_excluded": bj_excluded,
                            "membership_rows_written": rows_written,
                        }
                    )
                    year_frames.append(normalized)
                partition_frame = (
                    pd.concat(year_frames, ignore_index=True)
                    .sort_values(["trade_date", "instrument"], kind="stable")
                    .reset_index(drop=True)
                )
                if partition_frame.empty:
                    raise RichDataError(
                        f"Tushare stock_st {year} partition has no membership rows"
                    )
                if tuple(partition_frame.columns) != TUSHARE_ST_MEMBERSHIP_COLUMNS:
                    raise RichDataError(
                        f"Tushare stock_st {year} partition columns changed"
                    )
                if partition_frame.duplicated(["trade_date", "instrument"]).any():
                    raise RichDataError(
                        f"Tushare stock_st {year} partition has duplicate keys"
                    )
                destination = temporary_root / f"{year}.parquet"
                atomic_write_frame(partition_frame, destination)
                files.append(
                    {
                        "year": year,
                        "requested_start": partition_start.isoformat(),
                        "requested_end": partition_end.isoformat(),
                        "logical_session_calls": int(len(partition_calendar)),
                        "source_rows": year_source_rows,
                        "outside_target_bj_rows_excluded": year_bj_excluded,
                        "rows": year_rows_written,
                        "path": manifest_path(run_root / destination.name),
                        "sha256": frame_digest(partition_frame),
                    }
                )
            if logical_sessions_completed != expected_sessions:
                raise RichDataError(
                    "Tushare stock_st full source omitted a calendar session: "
                    f"expected {expected_sessions}, completed {logical_sessions_completed}"
                )
            if tuple(item["year"] for item in files) != tuple(
                snapshot["required_partition_years"]
            ):
                raise RichDataError("Tushare stock_st annual partition set changed")
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": dataset,
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_ST_RECOVERY_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_ST_RECOVERY_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "mechanism_overlap_audit": contract["mechanism_identity"][
                    "mechanism_overlap_audit"
                ],
                "source_acceptance": {
                    "path": manifest_path(
                        DEFAULT_TUSHARE_ST_RECOVERY_ACCEPTANCE_RECORD
                    ),
                    "sha256": file_digest(
                        DEFAULT_TUSHARE_ST_RECOVERY_ACCEPTANCE_RECORD
                    ),
                    "status": source_chain["acceptance_record"]["status"],
                    "provider_calls_issued_by_dedicated_acceptance": 0,
                },
                "no_return_preregistration": {
                    "path": manifest_path(DEFAULT_TUSHARE_ST_RECOVERY_NO_RETURN_SPEC),
                    "sha256": file_digest(DEFAULT_TUSHARE_ST_RECOVERY_NO_RETURN_SPEC),
                    "status": source_chain["spec"]["status"],
                },
                "local_calendar": {
                    "path": manifest_path(resolved_calendar),
                    "sha256": file_digest(resolved_calendar),
                    "sessions_in_requested_range": int(len(calendar)),
                },
                "source_request": {
                    "api": "stock_st",
                    "frequency": "daily_membership",
                    "request_mode": "one complete local trading session per call",
                    "fields": list(TUSHARE_ST_MEMBERSHIP_RAW_FIELDS),
                    "forbidden_fields_requested_or_stored": [],
                    "logical_sessions_planned": expected_sessions,
                    "logical_sessions_issued": logical_sessions_issued,
                    "logical_sessions_completed": logical_sessions_completed,
                    "provider_request_attempts": request_attempts[0],
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_session": maximum_attempts,
                    "strict_response_row_ceiling": row_ceiling,
                    "credentials_logged_or_stored": False,
                },
                "files": files,
                "source_quality": {
                    "source_rows": source_rows_observed,
                    "membership_rows_written": total_rows_written,
                    "outside_target_bj_rows_excluded": total_bj_excluded,
                    "minimum_source_rows_per_session": int(
                        min(item["source_rows"] for item in daily_quality)
                    ),
                    "maximum_source_rows_per_session": int(
                        max(item["source_rows"] for item in daily_quality)
                    ),
                    "empty_source_sessions": 0,
                    "responses_at_row_ceiling": 0,
                    "missing_required_rows": 0,
                    "unsupported_type_rows": 0,
                    "duplicate_stock_date_keys": 0,
                    "daily": daily_quality,
                },
                "materialization_boundary": {
                    "raw_provider_frames_persisted": False,
                    "name_or_type_name_requested_or_persisted": False,
                    "static_st_membership_ranked": False,
                    "membership_transitions_derived": False,
                    "prior_spell_durations_derived": False,
                    "factor_values_derived_or_persisted": False,
                },
                "acceptance_status": snapshot["success_status"],
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            published_manifest = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, published_manifest)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                published_manifest = None
                raise
            return published_manifest
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            if published_manifest is None and run_root.exists():
                shutil.rmtree(run_root, ignore_errors=True)
            message = safe_exception_text(exc)
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": dataset,
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "failed_trade_date": current_session,
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_ST_RECOVERY_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_ST_RECOVERY_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "source_acceptance": {
                    "path": manifest_path(
                        DEFAULT_TUSHARE_ST_RECOVERY_ACCEPTANCE_RECORD
                    ),
                    "sha256": file_digest(
                        DEFAULT_TUSHARE_ST_RECOVERY_ACCEPTANCE_RECORD
                    ),
                },
                "no_return_preregistration": {
                    "path": manifest_path(DEFAULT_TUSHARE_ST_RECOVERY_NO_RETURN_SPEC),
                    "sha256": file_digest(DEFAULT_TUSHARE_ST_RECOVERY_NO_RETURN_SPEC),
                },
                "source_request": {
                    "api": "stock_st",
                    "fields": list(TUSHARE_ST_MEMBERSHIP_RAW_FIELDS),
                    "logical_sessions_planned": expected_sessions,
                    "logical_sessions_issued": logical_sessions_issued,
                    "logical_sessions_completed": logical_sessions_completed,
                    "provider_request_attempts": request_attempts[0],
                    "source_rows_observed": source_rows_observed,
                    "credentials_logged_or_stored": False,
                },
                "files": [],
                "partial_snapshot_deleted": not temporary_root.exists(),
                "final_snapshot_published": run_root.exists(),
                "acceptance_status": "terminal_source_failure_stop_before_transitions_factor_values_capacity_uniqueness_or_returns",
                "error_type": type(exc).__name__,
                "error": message,
                "raw_provider_frames_persisted": False,
                "name_or_type_name_requested_or_persisted": False,
                "membership_transitions_derived": False,
                "prior_spell_durations_derived": False,
                "factor_values_derived_or_persisted": False,
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            failure_path = RUNS_ROOT / f"{run_id}_source_failure.json"
            atomic_write_json(failure, failure_path)
            if isinstance(exc, RichDataError):
                raise RichDataError(
                    f"{message}; rejection_record={failure_path}"
                ) from exc
            raise


def _fetch_tushare_gross_margin_with_policy(
    ts_code: str,
    report_period_start: dt.date,
    report_period_end: dt.date,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    retry_backoffs: list[float],
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded stock-slice retries."""

    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_gross_margin_indicators(
                ts_code,
                report_period_start=report_period_start,
                report_period_end=report_period_end,
            )
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[attempt])
    raise AssertionError("unreachable Tushare gross-margin retry state")


def sync_tushare_gross_margin(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the frozen 2018-2025 initial gross-margin source without prices."""

    dataset = "tushare_single_quarter_gross_margin_yoy_change_events"
    with RichDataProcessLock(METADATA_ROOT / ".tushare_gross_margin.lock"):
        if DEFAULT_TUSHARE_GROSS_MARGIN_RESEARCH_RECORD.exists():
            load_tushare_gross_margin_research_record()
            raise RichDataError(
                "Tushare gross-margin branch is terminal after its full-source "
                "failure; another full sync is forbidden"
            )
        source_chain = load_tushare_gross_margin_source_chain()
        contract = source_chain["contract"]
        prior_full = tushare_gross_margin_full_snapshot_records()
        if prior_full:
            raise RichDataError(
                "Tushare gross-margin full-source attempt is one-shot and already "
                "exists: " + ", ".join(str(path) for path in prior_full)
            )
        if not allow_large:
            raise RichDataError(
                "Tushare gross-margin full snapshot requires --allow-large"
            )

        universe_path = universe_path.expanduser().resolve()
        calendar_path = calendar_path.expanduser().resolve()
        universe_context = contract["local_context"]["source_universe"]
        calendar_context = contract["local_context"]["calendar"]
        if (
            universe_path != resolve_record_path(universe_context["path"])
            or file_digest(universe_path) != universe_context["sha256"]
            or calendar_path != resolve_record_path(calendar_context["path"])
            or file_digest(calendar_path) != calendar_context["sha256"]
        ):
            raise RichDataError(
                "gross-margin full snapshot universe or calendar is not the frozen "
                "point-in-time source"
            )
        intervals = load_factor_universe_intervals(universe_path)
        snapshot = contract["full_snapshot_contract"]
        report_slices = tuple(
            (
                dt.datetime.strptime(start, "%Y%m%d").date(),
                dt.datetime.strptime(end, "%Y%m%d").date(),
            )
            for start, end in TUSHARE_GROSS_MARGIN_FULL_SLICES
        )
        total_planned_calls = int(snapshot["provider_calls"])
        if len(intervals) * len(report_slices) != total_planned_calls:
            raise RichDataError(
                "gross-margin source-universe or slice count changed: "
                f"{len(intervals)} * {len(report_slices)} != {total_planned_calls}"
            )
        source_start = dt.date.fromisoformat(
            str(snapshot["source_report_period_start"])
        )
        source_end = dt.date.fromisoformat(str(snapshot["source_report_period_end"]))
        development_start = dt.date.fromisoformat(
            str(snapshot["development_signal_start"])
        )
        development_end = dt.date.fromisoformat(str(snapshot["development_signal_end"]))
        if (
            report_slices[0][0] != source_start
            or report_slices[-1][1] != source_end
            or report_slices[0][1] + dt.timedelta(days=1) != report_slices[1][0]
        ):
            raise RichDataError("gross-margin frozen report-period slices changed")
        calendar = local_calendar_dates(
            development_start, development_end, calendar_path
        )
        if calendar.empty or calendar[-1] < pd.Timestamp(development_end):
            raise RichDataError(
                "gross-margin local calendar does not cover the development range"
            )
        require_provider("tushare")

        row_ceiling = int(
            contract["source_selection"]["provider_documented_maximum_rows_per_call"]
        )
        minimum_interval = float(snapshot["minimum_seconds_between_calls"])
        maximum_attempts = int(snapshot["maximum_attempts_per_stock_slice"])
        retry_backoffs = [float(value) for value in snapshot["retry_backoff_seconds"]]
        if len(retry_backoffs) < maximum_attempts - 1:
            raise RichDataError(
                "gross-margin retry backoff schedule is shorter than the contract"
            )

        run_id = new_run_id("tushare_gross_margin_full")
        parent = RAW_ROOT / "tushare" / "gross_margin" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Tushare gross-margin full snapshot already exists: {run_id}"
            )
        temporary_root.mkdir(parents=True)

        yearly_frames: dict[int, list[pd.DataFrame]] = {
            year: [] for year in range(development_start.year, development_end.year + 1)
        }
        fixed_report_periods = tuple(
            dt.date(year, month, day)
            for year in range(2019, 2026)
            for month, day in ((3, 31), (6, 30), (9, 30), (12, 31))
            if not (year == 2025 and month == 12)
        )
        observed_instruments_by_period: dict[str, set[str]] = {
            period.isoformat(): set() for period in fixed_report_periods
        }
        observed_rows_by_period: dict[str, int] = {
            period.isoformat(): 0 for period in fixed_report_periods
        }
        quality_keys = (
            "input_rows",
            "exact_five_field_duplicate_rows_collapsed",
            "initial_rows_observed",
            "revised_rows_observed",
            "missing_margin_rows_excluded",
            "ambiguous_initial_periods_excluded",
            "initial_quarter_rows_retained",
            "current_periods_without_prior_year_initial_excluded",
            "prior_announcement_not_earlier_excluded",
            "derived_yoy_events_written",
        )
        quality_totals = {key: 0 for key in quality_keys}
        source_rows_by_slice = {
            f"{start:%Y%m%d}-{end:%Y%m%d}": 0 for start, end in report_slices
        }
        empty_responses_by_slice = dict.fromkeys(source_rows_by_slice, 0)
        source_rows = 0
        factor_events_before_development_filter = 0
        development_factor_events = 0
        events_outside_development_range_excluded = 0
        instruments_without_development_events = 0
        instruments_without_development_events_examples: list[str] = []
        completed_provider_calls = 0
        completed_instruments = 0
        current_instrument: str | None = None
        current_slice: str | None = None
        last_request_started: list[float | None] = [None]
        started = time.monotonic()
        try:
            for interval in intervals.itertuples(index=False):
                current_instrument = str(interval.instrument)
                ts_code = tushare_ts_code_from_qlib_instrument(current_instrument)
                stock_raw_frames: list[pd.DataFrame] = []
                for slice_start, slice_end in report_slices:
                    current_slice = f"{slice_start:%Y%m%d}-{slice_end:%Y%m%d}"
                    raw = _fetch_tushare_gross_margin_with_policy(
                        ts_code,
                        slice_start,
                        slice_end,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        retry_backoffs=retry_backoffs,
                        last_request_started=last_request_started,
                    )
                    completed_provider_calls += 1
                    source_rows += int(len(raw))
                    source_rows_by_slice[current_slice] += int(len(raw))
                    if raw.empty:
                        empty_responses_by_slice[current_slice] += 1
                    if len(raw) >= row_ceiling:
                        raise RichDataError(
                            "Tushare gross-margin response reached the documented "
                            f"row ceiling for {ts_code} {current_slice}: {len(raw)}"
                        )
                    stock_raw_frames.append(raw)

                nonempty = [frame for frame in stock_raw_frames if not frame.empty]
                combined_raw = (
                    pd.concat(nonempty, ignore_index=True)
                    if nonempty
                    else pd.DataFrame()
                )
                normalized, quality = canonicalize_tushare_gross_margin_indicators(
                    combined_raw,
                    expected_ts_code=ts_code,
                    report_period_start=source_start,
                    report_period_end=source_end,
                )
                for key in quality_totals:
                    quality_totals[key] += int(quality.get(key, 0))
                factor_events_before_development_filter += int(len(normalized))
                if not normalized.empty:
                    announcement_dates = pd.to_datetime(
                        normalized["announcement_date"]
                    ).dt.normalize()
                    in_development = announcement_dates.between(
                        pd.Timestamp(development_start), pd.Timestamp(development_end)
                    )
                    events_outside_development_range_excluded += int(
                        (~in_development).sum()
                    )
                    normalized = normalized.loc[in_development].copy()
                    development_factor_events += int(len(normalized))
                if normalized.empty:
                    instruments_without_development_events += 1
                    if len(instruments_without_development_events_examples) < 20:
                        instruments_without_development_events_examples.append(
                            current_instrument
                        )
                else:
                    for period, period_frame in normalized.groupby(
                        "report_period", sort=True, observed=True
                    ):
                        period_key = pd.Timestamp(period).date().isoformat()
                        if period_key in observed_instruments_by_period:
                            observed_instruments_by_period[period_key].add(
                                current_instrument
                            )
                            observed_rows_by_period[period_key] += int(
                                len(period_frame)
                            )
                    years = pd.to_datetime(
                        normalized["announcement_date"]
                    ).dt.year.astype(int)
                    normalized = normalized.assign(_announcement_year=years)
                    for year, year_frame in normalized.groupby(
                        "_announcement_year", sort=True, observed=True
                    ):
                        year_value = int(year)
                        if year_value not in yearly_frames:
                            raise RichDataError(
                                "gross-margin canonical event fell outside the frozen "
                                f"announcement years: {year_value}"
                            )
                        yearly_frames[year_value].append(
                            year_frame.drop(columns="_announcement_year").loc[
                                :, list(TUSHARE_GROSS_MARGIN_COLUMNS)
                            ]
                        )
                completed_instruments += 1
                if completed_instruments % 25 == 0 or completed_instruments == len(
                    intervals
                ):
                    elapsed = max(time.monotonic() - started, 0.001)
                    print(
                        json.dumps(
                            {
                                "dataset": dataset,
                                "completed_instruments": completed_instruments,
                                "total_instruments": int(len(intervals)),
                                "completed_provider_calls": completed_provider_calls,
                                "total_provider_calls": total_planned_calls,
                                "source_rows": source_rows,
                                "development_factor_events": (
                                    development_factor_events
                                ),
                                "elapsed_minutes": round(elapsed / 60.0, 2),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )

            if completed_provider_calls != total_planned_calls:
                raise RichDataError(
                    "gross-margin full snapshot omitted one or more frozen calls"
                )
            files: list[dict[str, Any]] = []
            total_rows = 0
            duplicate_factor_event_keys = 0
            factor_min: float | None = None
            factor_max: float | None = None
            factor_name = "tushare_q_gross_margin_yoy_change_pp"
            for year in sorted(yearly_frames):
                frames = yearly_frames[year]
                if not frames:
                    raise RichDataError(
                        f"gross-margin {year} announcement partition has no events"
                    )
                partition = (
                    pd.concat(frames, ignore_index=True)
                    .sort_values(
                        ["announcement_date", "instrument", "report_period"],
                        kind="stable",
                    )
                    .reset_index(drop=True)
                )
                if tuple(partition.columns) != TUSHARE_GROSS_MARGIN_COLUMNS:
                    raise RichDataError(
                        f"gross-margin {year} partition columns changed"
                    )
                duplicates = int(
                    partition.duplicated(
                        ["instrument", "announcement_date", "report_period"]
                    ).sum()
                )
                duplicate_factor_event_keys += duplicates
                if duplicates:
                    raise RichDataError(
                        f"gross-margin {year} partition has duplicate event keys"
                    )
                factor = pd.to_numeric(partition[factor_name], errors="coerce")
                if (
                    factor.isna().any()
                    or not np.isfinite(factor.to_numpy(dtype=float, copy=False)).all()
                ):
                    raise RichDataError(
                        f"gross-margin {year} partition has a non-finite factor"
                    )
                year_min = float(factor.min())
                year_max = float(factor.max())
                factor_min = (
                    year_min if factor_min is None else min(factor_min, year_min)
                )
                factor_max = (
                    year_max if factor_max is None else max(factor_max, year_max)
                )
                destination = temporary_root / f"{year}.parquet"
                atomic_write_frame(partition, destination)
                total_rows += int(len(partition))
                files.append(
                    {
                        "announcement_year": int(year),
                        "path": manifest_path(run_root / destination.name),
                        "rows": int(len(partition)),
                        "sha256": frame_digest(partition),
                    }
                )
            if total_rows != development_factor_events:
                raise RichDataError(
                    "gross-margin annual partitions changed the retained row count"
                )

            report_period_coverage: list[dict[str, Any]] = []
            for period in fixed_report_periods:
                period_key = period.isoformat()
                period_ts = pd.Timestamp(period)
                active = set(
                    intervals.loc[
                        intervals["start_date"].le(period_ts)
                        & intervals["end_date"].ge(period_ts),
                        "instrument",
                    ].astype(str)
                )
                observed = observed_instruments_by_period[period_key]
                observed_active = observed & active
                report_period_coverage.append(
                    {
                        "report_period": period_key,
                        "expected_active_source_names": int(len(active)),
                        "observed_active_factor_names": int(len(observed_active)),
                        "observed_factor_rows": observed_rows_by_period[period_key],
                        "observed_names_outside_period_active_universe": int(
                            len(observed - active)
                        ),
                        "coverage": (
                            len(observed_active) / len(active) if active else None
                        ),
                    }
                )
            coverage_values = pd.Series(
                [
                    row["coverage"]
                    for row in report_period_coverage
                    if row["coverage"] is not None
                ],
                dtype="float64",
            )
            median_coverage = (
                float(coverage_values.median()) if len(coverage_values) else 0.0
            )
            p05_coverage = (
                float(coverage_values.quantile(0.05)) if len(coverage_values) else 0.0
            )
            observed_signal_years = len(files)
            completeness = contract["source_completeness_policy"]
            source_gate_passed = bool(
                total_rows
                >= int(completeness["minimum_complete_derived_factor_events"])
                and len(files) == len(yearly_frames)
                and len(coverage_values) == len(fixed_report_periods)
                and median_coverage
                >= float(completeness["minimum_median_report_period_coverage"])
                and p05_coverage
                >= float(completeness["minimum_p05_report_period_coverage"])
                and observed_signal_years
                >= int(completeness["minimum_observed_signal_years"])
                and duplicate_factor_event_keys == 0
            )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": dataset,
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source_report_period_start": source_start.isoformat(),
                "source_report_period_end": source_end.isoformat(),
                "development_signal_start": development_start.isoformat(),
                "development_signal_end": development_end.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_GROSS_MARGIN_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_GROSS_MARGIN_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                    "manifest_path": manifest_path(source_chain["manifest_path"]),
                    "manifest_sha256": file_digest(source_chain["manifest_path"]),
                    "factor_frame_path": manifest_path(source_chain["frame_path"]),
                    "factor_frame_content_sha256": frame_digest(source_chain["frame"]),
                },
                "point_in_time_source_universe": {
                    "path": manifest_path(universe_path),
                    "sha256": file_digest(universe_path),
                    "intervals": int(len(intervals)),
                    "survivorship_limitation": (
                        "current listing snapshot with point-in-time intervals; "
                        "not a historical delisting master"
                    ),
                },
                "local_calendar": {
                    "path": manifest_path(calendar_path),
                    "sha256": file_digest(calendar_path),
                    "development_sessions": int(len(calendar)),
                    "price_fields_loaded": [],
                },
                "source_request": {
                    "api": "fina_indicator",
                    "request_mode": (
                        "two frozen report-period slices per source-universe stock"
                    ),
                    "report_period_slices": [
                        {
                            "start": start.strftime("%Y%m%d"),
                            "end": end.strftime("%Y%m%d"),
                        }
                        for start, end in report_slices
                    ],
                    "fields": list(TUSHARE_GROSS_MARGIN_RAW_FIELDS),
                    "planned_instruments": int(len(intervals)),
                    "planned_provider_calls": total_planned_calls,
                    "completed_provider_calls": completed_provider_calls,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_stock_slice": maximum_attempts,
                    "retry_backoff_seconds": retry_backoffs,
                    "documented_row_ceiling_per_call": row_ceiling,
                    "source_rows": source_rows,
                    "source_rows_by_slice": source_rows_by_slice,
                    "empty_responses_by_slice": empty_responses_by_slice,
                    "raw_provider_frames_persisted": False,
                    "initial_or_revised_source_margin_levels_persisted": False,
                    "revised_values_used_or_persisted": False,
                    "forbidden_fields_requested_or_stored": [],
                    "credentials_logged_or_stored": False,
                },
                "files": files,
                "normalization_quality": {
                    **quality_totals,
                    "factor_events_before_development_filter": (
                        factor_events_before_development_filter
                    ),
                    "events_outside_development_range_excluded": (
                        events_outside_development_range_excluded
                    ),
                    "development_factor_events_written": total_rows,
                    "factor_min": factor_min,
                    "factor_max": factor_max,
                    "instruments_without_development_events": (
                        instruments_without_development_events
                    ),
                    "instruments_without_development_events_examples": (
                        instruments_without_development_events_examples
                    ),
                    "duplicate_factor_event_keys": duplicate_factor_event_keys,
                    "source_margin_levels_persisted": False,
                    "revised_values_used_or_persisted": False,
                },
                "source_completeness": {
                    "coverage_denominator": (
                        "factor_main_chinext_star instruments active at each fixed "
                        "2019Q1-2025Q3 report period"
                    ),
                    "fixed_report_periods": [
                        period.isoformat() for period in fixed_report_periods
                    ],
                    "complete_derived_factor_events": total_rows,
                    "minimum_complete_derived_factor_events": int(
                        completeness["minimum_complete_derived_factor_events"]
                    ),
                    "observed_signal_years": observed_signal_years,
                    "minimum_observed_signal_years": int(
                        completeness["minimum_observed_signal_years"]
                    ),
                    "median_report_period_coverage": median_coverage,
                    "minimum_median_report_period_coverage": float(
                        completeness["minimum_median_report_period_coverage"]
                    ),
                    "p05_report_period_coverage": p05_coverage,
                    "minimum_p05_report_period_coverage": float(
                        completeness["minimum_p05_report_period_coverage"]
                    ),
                    "report_periods": report_period_coverage,
                    "gate_passed_before_event_expansion_capacity_uniqueness_or_prices": (
                        source_gate_passed
                    ),
                },
                "factor_policy": {
                    "factor": "tushare_single_quarter_gross_margin_yoy_change",
                    "raw_column": factor_name,
                    "formula": contract["factor"]["formula"],
                    "units": "percentage_points",
                    "direction": "higher_is_better",
                    "initial_rows_only": True,
                    "eligible_entry": (
                        "first local trading session open strictly after the current "
                        "initial ann_date"
                    ),
                    "maximum_event_age_calendar_days": 3,
                },
                "acceptance_status": (
                    "full_source_completeness_passed_pending_no_return_capacity_and_uniqueness"
                    if source_gate_passed
                    else "full_source_completeness_failed_stop_before_capacity_uniqueness_or_prices"
                ),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            message = safe_exception_text(exc)
            if "row ceiling" in message:
                failure_code = "provider_row_ceiling_possible_truncation"
            elif "fields outside" in message or "lacks requested fields" in message:
                failure_code = "source_schema_mismatch"
            elif "duplicate" in message or "ambiguous" in message:
                failure_code = "source_duplicate_or_ambiguous_initial_version"
            elif (
                "invalid keys" in message
                or "unknown update_flag" in message
                or "non-standard report period" in message
                or "report period after" in message
                or "outside its request" in message
            ):
                failure_code = "source_identity_date_or_version_failure"
            else:
                failure_code = "provider_or_local_snapshot_failure"
            failure_path = RUNS_ROOT / f"{run_id}_source_failure.json"
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_source_failure",
                "dataset": dataset,
                "provider": "tushare",
                "run_id": run_id,
                "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source_report_period_start": source_start.isoformat(),
                "source_report_period_end": source_end.isoformat(),
                "development_signal_start": development_start.isoformat(),
                "development_signal_end": development_end.isoformat(),
                "failed_instrument": current_instrument,
                "failed_slice": current_slice,
                "completed_instruments_before_failure": completed_instruments,
                "completed_provider_calls_before_failure": completed_provider_calls,
                "total_planned_provider_calls": total_planned_calls,
                "source_rows_observed_before_failure": source_rows,
                "failure_code": failure_code,
                "error": message,
                "partial_snapshot_deleted": not temporary_root.exists(),
                "final_snapshot_published": run_root.exists(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_GROSS_MARGIN_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_GROSS_MARGIN_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                    "manifest_path": manifest_path(source_chain["manifest_path"]),
                    "manifest_sha256": file_digest(source_chain["manifest_path"]),
                },
                "source_request": {
                    "api": "fina_indicator",
                    "report_period_slices": [
                        {
                            "start": start.strftime("%Y%m%d"),
                            "end": end.strftime("%Y%m%d"),
                        }
                        for start, end in report_slices
                    ],
                    "fields": list(TUSHARE_GROSS_MARGIN_RAW_FIELDS),
                    "planned_provider_calls": total_planned_calls,
                    "completed_provider_calls": completed_provider_calls,
                    "source_rows_by_slice": source_rows_by_slice,
                    "raw_provider_frames_persisted": False,
                    "initial_or_revised_source_margin_levels_persisted": False,
                    "revised_values_used_or_persisted": False,
                    "credentials_logged_or_stored": False,
                },
                "files": [],
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            atomic_write_json(failure, failure_path)
            raise RichDataError(f"{message}; failure_record={failure_path}") from exc


def _fetch_tushare_audit_opinions_with_policy(
    ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    retry_backoffs: list[float],
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded stock retry policy."""

    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_audit_opinions(
                ts_code,
                announcement_start=announcement_start,
                announcement_end=announcement_end,
            )
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[attempt])
    raise AssertionError("unreachable Tushare audit-opinion retry state")


def sync_tushare_audit_opinions(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the frozen 2019-2025 audit-opinion source without prices."""

    with RichDataProcessLock(METADATA_ROOT / ".tushare_audit_opinion.lock"):
        source_chain = load_tushare_audit_opinion_source_chain()
        contract = source_chain["contract"]
        prior_full = tushare_audit_opinion_full_snapshot_records()
        if prior_full:
            raise RichDataError(
                "Tushare audit-opinion full-source attempt is one-shot and already "
                "exists: " + ", ".join(str(path) for path in prior_full)
            )
        if not allow_large:
            raise RichDataError(
                "Tushare audit-opinion full snapshot requires --allow-large"
            )

        universe_path = universe_path.expanduser().resolve()
        calendar_path = calendar_path.expanduser().resolve()
        universe_context = contract["local_context"]["source_universe"]
        calendar_context = contract["local_context"]["calendar"]
        if (
            universe_path != resolve_record_path(universe_context["path"])
            or file_digest(universe_path) != universe_context["sha256"]
            or calendar_path != resolve_record_path(calendar_context["path"])
            or file_digest(calendar_path) != calendar_context["sha256"]
        ):
            raise RichDataError(
                "audit-opinion full snapshot universe or calendar is not the "
                "frozen point-in-time source"
            )
        intervals = load_factor_universe_intervals(universe_path)
        snapshot = contract["full_snapshot_contract"]
        total_planned_calls = int(snapshot["provider_calls"])
        if len(intervals) != total_planned_calls:
            raise RichDataError(
                "audit-opinion source-universe count changed: "
                f"{len(intervals)} != {total_planned_calls}"
            )
        announcement_start = dt.date.fromisoformat(
            str(snapshot["development_signal_start"])
        )
        announcement_end = dt.date.fromisoformat(
            str(snapshot["development_signal_end"])
        )
        calendar = local_calendar_dates(
            announcement_start, announcement_end, calendar_path
        )
        if calendar.empty or calendar[-1] < pd.Timestamp(announcement_end):
            raise RichDataError(
                "audit-opinion local calendar does not cover the development range"
            )
        require_provider("tushare")

        row_ceiling = int(
            contract["source_selection"]["defensive_maximum_rows_per_single_stock_call"]
        )
        minimum_interval = float(snapshot["minimum_seconds_between_calls"])
        maximum_attempts = int(snapshot["maximum_attempts_per_stock"])
        retry_backoffs = [float(value) for value in snapshot["retry_backoff_seconds"]]
        if len(retry_backoffs) < maximum_attempts - 1:
            raise RichDataError(
                "audit-opinion retry backoff schedule is shorter than the contract"
            )

        run_id = new_run_id("tushare_audit_opinion_full")
        parent = RAW_ROOT / "tushare" / "audit_opinion" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Tushare audit-opinion full snapshot already exists: {run_id}"
            )
        temporary_root.mkdir(parents=True)

        yearly_frames: dict[int, list[pd.DataFrame]] = {
            year: []
            for year in range(announcement_start.year, announcement_end.year + 1)
        }
        annual_report_periods = tuple(
            dt.date(year, 12, 31)
            for year in range(announcement_start.year - 1, announcement_end.year)
        )
        annual_report_instruments: dict[str, set[str]] = {
            period.isoformat(): set() for period in annual_report_periods
        }
        annual_report_row_counts: dict[str, int] = {
            period.isoformat(): 0 for period in annual_report_periods
        }
        quality_totals = {
            "input_rows": 0,
            "exact_four_field_duplicate_rows_collapsed": 0,
            "source_report_rows_retained": 0,
            "stock_announcement_events_written": 0,
            "clean_report_rows": 0,
            "nonclean_report_rows": 0,
        }
        hashed_opinion_category_counts: dict[str, int] = {}
        source_rows = 0
        empty_responses = 0
        instruments_without_events = 0
        instruments_without_events_examples: list[str] = []
        completed_provider_calls = 0
        current_instrument: str | None = None
        last_request_started: list[float | None] = [None]
        started = time.monotonic()
        try:
            for interval in intervals.itertuples(index=False):
                current_instrument = str(interval.instrument)
                ts_code = tushare_ts_code_from_qlib_instrument(current_instrument)
                raw = _fetch_tushare_audit_opinions_with_policy(
                    ts_code,
                    announcement_start,
                    announcement_end,
                    minimum_interval=minimum_interval,
                    maximum_attempts=maximum_attempts,
                    retry_backoffs=retry_backoffs,
                    last_request_started=last_request_started,
                )
                completed_provider_calls += 1
                source_rows += int(len(raw))
                if raw.empty:
                    empty_responses += 1
                if len(raw) >= row_ceiling:
                    raise RichDataError(
                        "Tushare audit-opinion response reached the frozen defensive "
                        f"row ceiling for {ts_code}: {len(raw)}"
                    )
                normalized, quality = canonicalize_tushare_audit_opinions(
                    raw,
                    expected_ts_code=ts_code,
                    announcement_start=announcement_start,
                    announcement_end=announcement_end,
                )
                for key in quality_totals:
                    quality_totals[key] += int(quality.get(key, 0))
                for category_hash, count in (
                    quality.get("hashed_opinion_category_counts") or {}
                ).items():
                    hashed_opinion_category_counts[str(category_hash)] = (
                        hashed_opinion_category_counts.get(str(category_hash), 0)
                        + int(count)
                    )
                for period, count in (
                    quality.get("annual_report_period_counts") or {}
                ).items():
                    if period in annual_report_instruments:
                        annual_report_instruments[period].add(current_instrument)
                        annual_report_row_counts[period] += int(count)

                if normalized.empty:
                    instruments_without_events += 1
                    if len(instruments_without_events_examples) < 20:
                        instruments_without_events_examples.append(current_instrument)
                else:
                    years = pd.to_datetime(
                        normalized["announcement_date"]
                    ).dt.year.astype(int)
                    normalized = normalized.assign(_announcement_year=years)
                    for year, year_frame in normalized.groupby(
                        "_announcement_year", sort=True, observed=True
                    ):
                        year_value = int(year)
                        if year_value not in yearly_frames:
                            raise RichDataError(
                                "audit-opinion canonical event fell outside the "
                                f"frozen announcement years: {year_value}"
                            )
                        yearly_frames[year_value].append(
                            year_frame.drop(columns="_announcement_year").loc[
                                :, list(TUSHARE_AUDIT_OPINION_COLUMNS)
                            ]
                        )

                if (
                    completed_provider_calls % 50 == 0
                    or completed_provider_calls == total_planned_calls
                ):
                    elapsed = max(time.monotonic() - started, 0.001)
                    print(
                        json.dumps(
                            {
                                "dataset": "tushare_audit_opinion_events",
                                "completed_instruments": completed_provider_calls,
                                "total_instruments": total_planned_calls,
                                "source_rows": source_rows,
                                "factor_events": quality_totals[
                                    "stock_announcement_events_written"
                                ],
                                "elapsed_minutes": round(elapsed / 60.0, 2),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )

            if completed_provider_calls != total_planned_calls:
                raise RichDataError(
                    "audit-opinion full snapshot omitted one or more frozen calls"
                )
            files: list[dict[str, Any]] = []
            total_rows = 0
            duplicate_stock_announcement_keys = 0
            factor_name = "tushare_is_standard_unqualified_audit_opinion"
            factor_value_counts: dict[str, int] = {}
            for year in sorted(yearly_frames):
                frames = yearly_frames[year]
                if not frames:
                    raise RichDataError(
                        f"audit-opinion {year} announcement partition has no events"
                    )
                partition = (
                    pd.concat(frames, ignore_index=True)
                    .sort_values(["announcement_date", "instrument"], kind="stable")
                    .reset_index(drop=True)
                )
                if tuple(partition.columns) != TUSHARE_AUDIT_OPINION_COLUMNS:
                    raise RichDataError(
                        f"audit-opinion {year} partition columns changed"
                    )
                duplicates = int(
                    partition.duplicated(["instrument", "announcement_date"]).sum()
                )
                duplicate_stock_announcement_keys += duplicates
                if duplicates:
                    raise RichDataError(
                        f"audit-opinion {year} partition has duplicate event keys"
                    )
                if not partition[factor_name].isin({0, 1}).all():
                    raise RichDataError(
                        f"audit-opinion {year} partition contains a nonbinary value"
                    )
                for value, count in (
                    partition[factor_name].value_counts().sort_index().items()
                ):
                    key = str(int(value))
                    factor_value_counts[key] = factor_value_counts.get(key, 0) + int(
                        count
                    )
                destination = temporary_root / f"{year}.parquet"
                atomic_write_frame(partition, destination)
                total_rows += int(len(partition))
                files.append(
                    {
                        "announcement_year": int(year),
                        "path": manifest_path(run_root / destination.name),
                        "rows": int(len(partition)),
                        "sha256": frame_digest(partition),
                    }
                )

            annual_coverage: list[dict[str, Any]] = []
            for period in annual_report_periods:
                period_key = period.isoformat()
                period_ts = pd.Timestamp(period)
                active = set(
                    intervals.loc[
                        intervals["start_date"].le(period_ts)
                        & intervals["end_date"].ge(period_ts),
                        "instrument",
                    ].astype(str)
                )
                observed = annual_report_instruments[period_key]
                observed_active = observed & active
                annual_coverage.append(
                    {
                        "annual_report_period": period_key,
                        "expected_active_source_names": int(len(active)),
                        "observed_active_source_names": int(len(observed_active)),
                        "observed_report_rows": annual_report_row_counts[period_key],
                        "observed_names_outside_period_active_universe": int(
                            len(observed - active)
                        ),
                        "coverage": (
                            len(observed_active) / len(active) if active else None
                        ),
                    }
                )
            coverage_values = pd.Series(
                [
                    row["coverage"]
                    for row in annual_coverage
                    if row["coverage"] is not None
                ],
                dtype="float64",
            )
            median_coverage = (
                float(coverage_values.median()) if len(coverage_values) else 0.0
            )
            p05_coverage = (
                float(coverage_values.quantile(0.05)) if len(coverage_values) else 0.0
            )
            observed_source_years = int(
                sum(row["observed_active_source_names"] > 0 for row in annual_coverage)
            )
            completeness = contract["source_completeness_policy"]
            source_gate_passed = bool(
                len(files) == len(yearly_frames)
                and len(coverage_values) == len(annual_report_periods)
                and median_coverage
                >= float(completeness["minimum_median_annual_report_coverage"])
                and p05_coverage
                >= float(completeness["minimum_p05_annual_report_coverage"])
                and observed_source_years
                >= int(completeness["minimum_observed_source_years"])
                and duplicate_stock_announcement_keys == 0
            )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_audit_opinion_events",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": announcement_start.isoformat(),
                "requested_end": announcement_end.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_AUDIT_OPINION_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_AUDIT_OPINION_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                    "manifest_path": manifest_path(source_chain["manifest_path"]),
                    "manifest_sha256": file_digest(source_chain["manifest_path"]),
                    "factor_frame_path": manifest_path(source_chain["frame_path"]),
                    "factor_frame_content_sha256": frame_digest(source_chain["frame"]),
                },
                "point_in_time_source_universe": {
                    "path": manifest_path(universe_path),
                    "sha256": file_digest(universe_path),
                    "intervals": int(len(intervals)),
                    "survivorship_limitation": (
                        "current listing snapshot with point-in-time intervals; "
                        "not a historical delisting master"
                    ),
                },
                "local_calendar": {
                    "path": manifest_path(calendar_path),
                    "sha256": file_digest(calendar_path),
                    "development_sessions": int(len(calendar)),
                    "price_fields_loaded": [],
                },
                "source_request": {
                    "api": "fina_audit",
                    "request_mode": (
                        "one source-universe stock over the complete frozen "
                        "announcement-date range per call"
                    ),
                    "fields": list(TUSHARE_AUDIT_OPINION_RAW_FIELDS),
                    "planned_provider_calls": total_planned_calls,
                    "completed_provider_calls": completed_provider_calls,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_stock": maximum_attempts,
                    "retry_backoff_seconds": retry_backoffs,
                    "defensive_row_ceiling_per_call": row_ceiling,
                    "source_rows": source_rows,
                    "empty_responses": empty_responses,
                    "raw_provider_frames_persisted": False,
                    "raw_or_normalized_audit_result_text_persisted": False,
                    "audit_fee_agency_or_signer_requested_or_stored": False,
                    "forbidden_fields_requested_or_stored": [],
                    "credentials_logged_or_stored": False,
                },
                "files": files,
                "normalization_quality": {
                    **quality_totals,
                    "hashed_opinion_category_counts": dict(
                        sorted(hashed_opinion_category_counts.items())
                    ),
                    "distinct_hashed_opinion_categories": int(
                        len(hashed_opinion_category_counts)
                    ),
                    "factor_value_counts": dict(sorted(factor_value_counts.items())),
                    "instruments_without_events": instruments_without_events,
                    "instruments_without_events_examples": (
                        instruments_without_events_examples
                    ),
                    "duplicate_stock_announcement_report_period_keys": 0,
                    "duplicate_stock_announcement_keys": (
                        duplicate_stock_announcement_keys
                    ),
                    "raw_or_normalized_opinion_text_persisted": False,
                },
                "source_completeness": {
                    "coverage_denominator": (
                        "factor_main_chinext_star instruments active at each fixed "
                        "2018-2024 annual report period"
                    ),
                    "fixed_annual_report_periods": [
                        period.isoformat() for period in annual_report_periods
                    ],
                    "observed_source_years": observed_source_years,
                    "minimum_observed_source_years": int(
                        completeness["minimum_observed_source_years"]
                    ),
                    "median_annual_report_coverage": median_coverage,
                    "minimum_median_annual_report_coverage": float(
                        completeness["minimum_median_annual_report_coverage"]
                    ),
                    "p05_annual_report_coverage": p05_coverage,
                    "minimum_p05_annual_report_coverage": float(
                        completeness["minimum_p05_annual_report_coverage"]
                    ),
                    "annual": annual_coverage,
                    "gate_passed_before_event_expansion_capacity_uniqueness_or_prices": (
                        source_gate_passed
                    ),
                },
                "factor_policy": {
                    "factor": "tushare_standard_unqualified_audit_opinion",
                    "raw_column": factor_name,
                    "formula": contract["factor"]["formula"],
                    "direction": "higher_is_better",
                    "text_synonym_mapping_allowed": False,
                    "eligible_entry": (
                        "first local trading session open strictly after ann_date"
                    ),
                    "maximum_event_age_calendar_days": 3,
                },
                "acceptance_status": (
                    "full_source_completeness_passed_pending_no_return_capacity_and_uniqueness"
                    if source_gate_passed
                    else "full_source_completeness_failed_stop_before_capacity_uniqueness_or_prices"
                ),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            message = safe_exception_text(exc)
            if "row ceiling" in message:
                failure_code = "provider_row_ceiling_possible_truncation"
            elif "fields outside" in message or "lacks requested fields" in message:
                failure_code = "source_schema_mismatch"
            elif "duplicate" in message or "conflicting" in message:
                failure_code = "source_duplicate_or_conflicting_key"
            elif (
                "invalid keys" in message
                or "non-standard report period" in message
                or "report period after" in message
                or "outside its request" in message
            ):
                failure_code = "source_identity_date_or_opinion_failure"
            else:
                failure_code = "provider_or_local_snapshot_failure"
            failure_path = RUNS_ROOT / f"{run_id}_source_failure.json"
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_source_failure",
                "dataset": "tushare_audit_opinion_events",
                "provider": "tushare",
                "run_id": run_id,
                "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": announcement_start.isoformat(),
                "requested_end": announcement_end.isoformat(),
                "failed_instrument": current_instrument,
                "completed_provider_calls_before_failure": completed_provider_calls,
                "total_planned_provider_calls": total_planned_calls,
                "source_rows_observed_before_failure": source_rows,
                "failure_code": failure_code,
                "error": message,
                "partial_snapshot_deleted": not temporary_root.exists(),
                "final_snapshot_published": run_root.exists(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_AUDIT_OPINION_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_AUDIT_OPINION_CONTRACT),
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                },
                "raw_provider_frames_persisted": False,
                "raw_or_normalized_audit_result_text_persisted": False,
                "audit_fee_agency_or_signer_requested_or_stored": False,
                "credentials_logged_or_stored": False,
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            atomic_write_json(failure, failure_path)
            if isinstance(exc, RichDataError):
                raise RichDataError(
                    f"{message}; rejection_record={failure_path}"
                ) from exc
            raise


def sync_tushare_cash_conversion_acceptance() -> Path:
    """Run the frozen six-call, no-return accounting acceptance exactly once."""

    contract = load_tushare_cash_conversion_contract()
    prior_records = tushare_cash_conversion_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare cash-conversion acceptance is one-shot and was already "
            "consumed: " + ", ".join(str(path) for path in prior_records)
        )
    context = validate_tushare_cash_conversion_local_context(contract)
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    symbols = tuple(str(value) for value in acceptance["fixed_symbols"])
    endpoints = tuple(str(value) for value in acceptance["endpoints_per_symbol"])
    announcement_start = dt.datetime.strptime(
        str(acceptance["fixed_announcement_start"]), "%Y%m%d"
    ).date()
    announcement_end = dt.datetime.strptime(
        str(acceptance["fixed_announcement_end"]), "%Y%m%d"
    ).date()
    latest_actual = dt.datetime.strptime(
        str(acceptance["latest_allowed_actual_announcement_date"]), "%Y%m%d"
    ).date()
    row_ceiling = int(
        contract["source_selection"]["provider_documented_maximum_rows_per_call"]
    )
    run_id = new_run_id("tushare_cash_conversion_acceptance")
    run_root = RAW_ROOT / "tushare" / "cash_conversion" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare cash-conversion acceptance exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    provider_calls_issued = 0
    source_rows_by_symbol_endpoint: dict[str, dict[str, int]] = {
        symbol: {} for symbol in symbols
    }
    quality_by_symbol: dict[str, dict[str, Any]] = {}
    try:
        raw_by_symbol_endpoint: dict[tuple[str, str], pd.DataFrame] = {}
        for symbol in symbols:
            for endpoint in endpoints:
                provider_calls_issued += 1
                raw = fetch_tushare_cash_conversion_statement(
                    endpoint,
                    symbol,
                    announcement_start=announcement_start,
                    announcement_end=announcement_end,
                )
                raw_by_symbol_endpoint[(symbol, endpoint)] = raw
                source_rows_by_symbol_endpoint[symbol][endpoint] = int(len(raw))
        if provider_calls_issued != int(acceptance["provider_calls"]):
            raise RichDataError(
                "Tushare cash-conversion acceptance did not issue exactly six calls"
            )

        factor_frames: list[pd.DataFrame] = []
        minimum_periods = int(acceptance["minimum_usable_joined_periods_per_symbol"])
        for symbol in symbols:
            endpoint_frames: dict[str, pd.DataFrame] = {}
            endpoint_quality: dict[str, dict[str, Any]] = {}
            for endpoint in endpoints:
                raw = raw_by_symbol_endpoint[(symbol, endpoint)]
                if raw.empty:
                    raise RichDataError(
                        f"Tushare {endpoint} acceptance returned no rows for {symbol}"
                    )
                if len(raw) >= row_ceiling:
                    raise RichDataError(
                        f"Tushare {endpoint} acceptance reached the documented "
                        f"{row_ceiling}-row ceiling for {symbol}"
                    )
                canonical, quality = canonicalize_tushare_cash_conversion_endpoint(
                    raw,
                    endpoint=endpoint,
                    expected_ts_code=symbol,
                    announcement_start=announcement_start,
                    announcement_end=announcement_end,
                    latest_actual_announcement_date=latest_actual,
                )
                endpoint_frames[endpoint] = canonical
                endpoint_quality[endpoint] = quality
            factors, join_quality = derive_tushare_cash_conversion(
                endpoint_frames["income"], endpoint_frames["cashflow"]
            )
            if len(factors) < minimum_periods:
                raise RichDataError(
                    "Tushare cash-conversion acceptance has too few usable joined "
                    f"periods for {symbol}: {len(factors)} < {minimum_periods}"
                )
            quality_by_symbol[symbol] = {
                "income": endpoint_quality["income"],
                "cashflow": endpoint_quality["cashflow"],
                "join": join_quality,
            }
            factor_frames.append(factors)

        factors = (
            pd.concat(factor_frames, ignore_index=True)
            .sort_values(
                ["instrument", "report_period", "announcement_date"], kind="stable"
            )
            .reset_index(drop=True)
        )
        if factors.columns.tolist() != list(TUSHARE_CASH_CONVERSION_COLUMNS):
            raise RichDataError(
                "cash-conversion acceptance columns do not match the frozen schema"
            )
        if factors.duplicated(
            ["instrument", "announcement_date", "report_period"]
        ).any():
            raise RichDataError(
                "cash-conversion acceptance contains duplicate factor event keys"
            )
        observed_instruments = set(factors["instrument"].astype(str))
        expected_instruments = {
            qlib_symbol(symbol.split(".", 1)[0]) for symbol in symbols
        }
        if observed_instruments != expected_instruments:
            raise RichDataError(
                "cash-conversion acceptance does not retain every frozen instrument"
            )

        temporary_factor = temporary_root / "operating_cash_conversion.parquet"
        final_factor = run_root / "operating_cash_conversion.parquet"
        atomic_write_frame(factors, temporary_factor)
        values = factors["tushare_operating_cash_conversion"]
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_cash_conversion_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": announcement_start.isoformat(),
            "requested_end": announcement_end.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "apis": list(endpoints),
                "request_mode": (
                    "one stock and one frozen announcement-date range per endpoint call"
                ),
                "symbols": list(symbols),
                "provider_calls_issued": provider_calls_issued,
                "fields_by_endpoint": {
                    "income": list(TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS),
                    "cashflow": list(TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS),
                },
                "source_rows_returned_by_symbol_endpoint": (
                    source_rows_by_symbol_endpoint
                ),
                "provider_documented_row_ceiling_per_call": row_ceiling,
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "local_no_return_context": context,
            "files": [
                {
                    "role": "joined_point_in_time_cash_conversion_factor",
                    "path": manifest_path(final_factor),
                    "rows": int(len(factors)),
                    "sha256": frame_digest(factors),
                }
            ],
            "source_quality": {
                "by_symbol": quality_by_symbol,
                "input_rows": int(
                    sum(
                        sum(endpoint_rows.values())
                        for endpoint_rows in source_rows_by_symbol_endpoint.values()
                    )
                ),
                "usable_joined_periods": int(len(factors)),
                "unique_instruments": int(factors["instrument"].nunique()),
                "factor_min": float(values.min()),
                "factor_max": float(values.max()),
                "duplicate_factor_event_keys": 0,
                "raw_statement_frames_persisted": False,
                "update_flag_use": "manifest_counts_only_never_value_selection",
            },
            "availability_policy": {
                "source_time_fields": ["income.f_ann_date", "cashflow.f_ann_date"],
                "signal_source_date": "later accepted actual announcement date",
                "eligible_entry": (
                    "first local session open strictly after the later actual "
                    "announcement date"
                ),
                "same_announcement_session_trade_allowed": False,
                "maximum_event_age_calendar_days": 3,
                "forward_fill_beyond_event_age_allowed": False,
            },
            "acceptance_status": acceptance["success_status"],
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_cash_conversion_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": announcement_start.isoformat(),
            "requested_end": announcement_end.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "apis": list(endpoints),
                "request_mode": (
                    "one stock and one frozen announcement-date range per endpoint call"
                ),
                "symbols": list(symbols),
                "provider_calls_issued": provider_calls_issued,
                "fields_by_endpoint": {
                    "income": list(TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS),
                    "cashflow": list(TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS),
                },
                "source_rows_returned_by_symbol_endpoint": (
                    source_rows_by_symbol_endpoint
                ),
                "provider_documented_row_ceiling_per_call": row_ceiling,
                "forbidden_fields_requested_or_stored": [],
                "raw_statement_frames_persisted": False,
                "credentials_logged_or_stored": False,
            },
            "local_no_return_context": context,
            "observed_quality_before_rejection": quality_by_symbol,
            "files": [],
            "acceptance_status": (
                "rejected_stop_before_full_history_capacity_uniqueness_or_returns"
            ),
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def fetch_eastmoney_balance_sheet_partition(
    report_date: dt.date,
    *,
    contract: dict[str, Any] | None = None,
    session: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch one count-complete frozen Eastmoney balance-sheet partition."""

    frozen = contract or load_eastmoney_balance_sheet_resilience_contract()
    source = frozen["source"]
    request = source["request_parameters"]
    endpoint = str(source["endpoint"])
    page_size = int(request["pageSize"])
    maximum_pages = int(source["maximum_pages_per_partition"])
    maximum_attempts = int(source["maximum_attempts_per_page"])
    backoffs = [float(value) for value in source["retry_backoff_seconds"]]
    if session is None:
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - workspace dependency.
            raise RichDataError("requests is required for Eastmoney intake") from exc
        requester = requests
    else:
        requester = session

    base_params = {
        "sortColumns": str(request["sortColumns"]),
        "sortTypes": str(request["sortTypes"]),
        "pageSize": str(page_size),
        "reportName": str(source["report_name"]),
        "columns": str(request["columns"]),
        "filter": str(request["filter_template"]).replace(
            "YYYY-MM-DD", report_date.isoformat()
        ),
    }

    def fetch_page(page_number: int) -> dict[str, Any]:
        params = {**base_params, "pageNumber": str(page_number)}
        last_error: BaseException | None = None
        for attempt in range(maximum_attempts):
            try:
                response = requester.get(endpoint, params=params, timeout=30)
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                payload = response.json()
                result = payload.get("result") if isinstance(payload, dict) else None
                if not isinstance(result, dict):
                    raise RichDataError(
                        f"Eastmoney page {page_number} has no result object"
                    )
                if not isinstance(result.get("data"), list):
                    raise RichDataError(
                        f"Eastmoney page {page_number} has no data list"
                    )
                return result
            except Exception as exc:  # requests and schema failures share one policy.
                last_error = exc
                if attempt + 1 >= maximum_attempts:
                    break
                time.sleep(backoffs[attempt])
        assert last_error is not None
        raise RichDataError(
            f"Eastmoney balance-sheet page {page_number} failed after "
            f"{maximum_attempts} attempts: {safe_exception_text(last_error)}"
        ) from last_error

    first = fetch_page(1)
    try:
        pages = int(first["pages"])
        advertised_count = int(first["count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RichDataError(
            "Eastmoney balance-sheet page 1 has invalid pages or count"
        ) from exc
    if pages <= 0 or pages > maximum_pages or advertised_count <= 0:
        raise RichDataError(
            "Eastmoney balance-sheet advertised pages/count violate the frozen bounds: "
            f"pages={pages}, count={advertised_count}"
        )

    rows: list[dict[str, Any]] = []
    requested_pages: list[int] = []
    for page_number in range(1, pages + 1):
        result = first if page_number == 1 else fetch_page(page_number)
        try:
            result_pages = int(result["pages"])
            result_count = int(result["count"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RichDataError(
                f"Eastmoney balance-sheet page {page_number} metadata is invalid"
            ) from exc
        if result_pages != pages or result_count != advertised_count:
            raise RichDataError(
                "Eastmoney balance-sheet pagination metadata changed within the partition"
            )
        page_rows = result["data"]
        if any(not isinstance(row, dict) for row in page_rows):
            raise RichDataError(
                f"Eastmoney balance-sheet page {page_number} contains a non-object row"
            )
        rows.extend(page_rows)
        requested_pages.append(page_number)
    if requested_pages != list(range(1, pages + 1)) or len(rows) != advertised_count:
        raise RichDataError(
            "Eastmoney balance-sheet count-complete pagination failed: "
            f"received={len(rows)}, advertised={advertised_count}"
        )

    ordered_keys: list[str] = []
    seen_keys: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen_keys:
                seen_keys.add(key)
                ordered_keys.append(key)
    schema_sha256 = hashlib.sha256(
        json.dumps(ordered_keys, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return rows, {
        "report_date": report_date.isoformat(),
        "advertised_pages": pages,
        "requested_pages": requested_pages,
        "advertised_rows": advertised_count,
        "received_rows": len(rows),
        "page_size": page_size,
        "ordered_source_column_count": len(ordered_keys),
        "ordered_source_columns_sha256": schema_sha256,
        "provider_calls": pages,
    }


def fetch_eastmoney_core_profit_consistency_partition(
    report_date: dt.date,
    *,
    contract: dict[str, Any] | None = None,
    session: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch one count-complete frozen Eastmoney income-statement partition."""

    frozen = contract or load_eastmoney_core_profit_consistency_contract()
    return fetch_eastmoney_balance_sheet_partition(
        report_date,
        contract=frozen,
        session=session,
    )


def _eastmoney_core_profit_positional_frame(
    rows: list[dict[str, Any]],
    contract: dict[str, Any],
) -> tuple[pd.DataFrame, list[str]]:
    """Extract only the four predeclared income-statement positions."""

    if not rows or any(not isinstance(row, dict) for row in rows):
        raise RichDataError(
            "Eastmoney core-profit partition is empty or contains a non-object row"
        )
    ordered_keys: list[str] = []
    seen_keys: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen_keys:
                seen_keys.add(key)
                ordered_keys.append(key)
    schema = contract["source"]["source_schema_policy"]
    positions = schema["raw_json_data_object_zero_based_positions"]
    minimum_columns = int(schema["minimum_raw_columns"])
    if len(ordered_keys) < minimum_columns:
        raise RichDataError(
            "Eastmoney core-profit positional schema is too short: "
            f"{len(ordered_keys)} < {minimum_columns}"
        )
    if max(int(value) for value in positions.values()) >= len(ordered_keys):
        raise RichDataError("Eastmoney core-profit positional schema is incomplete")
    extracted = [
        {
            name: row.get(ordered_keys[int(positions[name])])
            for name in EASTMONEY_CORE_PROFIT_RAW_POSITION_NAMES
        }
        for row in rows
    ]
    return pd.DataFrame(extracted), ordered_keys


def canonicalize_eastmoney_core_profit_consistency(
    rows: list[dict[str, Any]],
    report_date: dt.date,
    *,
    contract: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Derive the sole frozen core-profit factor from four positional values."""

    frozen = contract or load_eastmoney_core_profit_consistency_contract()
    raw, ordered_keys = _eastmoney_core_profit_positional_frame(rows, frozen)
    codes = raw["stock_code"].astype("string").str.strip()
    complete_code = codes.str.fullmatch(r"\d{6}", na=False)
    supported_code = codes.str.fullmatch(
        r"(?:60[0135]\d{3}|00[0-3]\d{3}|30[01]\d{3})", na=False
    )
    instrument = pd.Series(pd.NA, index=raw.index, dtype="string")
    instrument.loc[supported_code] = codes.loc[supported_code].map(qlib_symbol)
    duplicate_keys = int(instrument.loc[supported_code].duplicated(keep=False).sum())
    if duplicate_keys:
        raise RichDataError(
            "Eastmoney core-profit partition contains duplicate instrument/report-period keys"
        )
    announcement = pd.to_datetime(
        raw["announcement_date"], errors="coerce"
    ).dt.normalize()
    operating_profit = pd.to_numeric(raw["operating_profit"], errors="coerce")
    total_profit = pd.to_numeric(raw["total_profit"], errors="coerce")
    finite_operating = np.isfinite(operating_profit)
    finite_total = np.isfinite(total_profit)
    positive_operating = operating_profit.gt(0.0)
    positive_total = total_profit.gt(0.0)
    denominator = np.maximum(operating_profit, total_profit)
    primary = np.minimum(operating_profit, total_profit) / denominator
    equivalent = 1.0 - (total_profit - operating_profit).abs() / denominator
    formula_error = (primary - equivalent).abs()
    maximum_error = float(
        frozen["acceptance_protocol"][
            "maximum_equivalent_formula_absolute_error"
        ]
    )
    formula_consistent = formula_error.le(maximum_error)
    complete_identity = supported_code & announcement.notna()
    valid = (
        complete_identity
        & finite_operating
        & finite_total
        & positive_operating
        & positive_total
        & np.isfinite(primary)
        & formula_consistent
    )
    result = pd.DataFrame(
        {
            "instrument": instrument.loc[valid].astype("string"),
            "report_date": pd.Timestamp(report_date),
            "announcement_date": announcement.loc[valid],
            "operating_profit": operating_profit.loc[valid].astype("float64"),
            "total_profit": total_profit.loc[valid].astype("float64"),
            "eastmoney_core_profit_consistency": primary.loc[valid].astype(
                "float64"
            ),
            "provider": "eastmoney",
        }
    )
    result = (
        result.loc[:, list(EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS)]
        .sort_values(["report_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    if (
        result.empty
        or result.duplicated(["instrument", "report_date"]).any()
        or not result["eastmoney_core_profit_consistency"].between(0.0, 1.0).all()
    ):
        raise RichDataError(
            "Eastmoney core-profit normalized frame failed frozen integrity checks"
        )
    accepted_error = formula_error.loc[valid]
    complete_identity_instruments = sorted(
        instrument.loc[complete_identity].dropna().astype(str).unique().tolist()
    )
    return result, {
        "input_rows": int(len(raw)),
        "ordered_source_column_count": int(len(ordered_keys)),
        "missing_or_malformed_stock_code_rows_excluded": int((~complete_code).sum()),
        "unsupported_board_rows_excluded": int((complete_code & ~supported_code).sum()),
        "missing_announcement_date_rows_excluded": int(announcement.isna().sum()),
        "complete_identity_main_chinext_names": int(
            len(complete_identity_instruments)
        ),
        "complete_identity_instruments_for_acceptance_only": (
            complete_identity_instruments
        ),
        "nonfinite_operating_or_total_profit_rows_excluded": int(
            (~finite_operating | ~finite_total).sum()
        ),
        "nonpositive_operating_profit_rows_excluded": int(
            (finite_operating & ~positive_operating).sum()
        ),
        "nonpositive_total_profit_rows_excluded": int(
            (finite_total & ~positive_total).sum()
        ),
        "equivalent_formula_inconsistent_rows_excluded": int(
            (
                complete_identity
                & finite_operating
                & finite_total
                & positive_operating
                & positive_total
                & ~formula_consistent
            ).sum()
        ),
        "accepted_formula_max_absolute_error": float(accepted_error.max()),
        "rows_written": int(len(result)),
    }


def canonicalize_eastmoney_balance_sheet_resilience(
    rows: list[dict[str, Any]],
    report_date: dt.date,
    *,
    contract: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Derive the sole frozen balance-sheet factor from five positional values."""

    frozen = contract or load_eastmoney_balance_sheet_resilience_contract()
    schema = frozen["source"]["source_schema_policy"]
    positions = schema["raw_json_data_object_zero_based_positions"]
    minimum_columns = int(schema["minimum_raw_columns"])
    maximum_formula_error = float(
        frozen["acceptance_protocol"]["maximum_formula_absolute_error"]
    )
    if not rows:
        raise RichDataError("Eastmoney balance-sheet partition returned no rows")
    if any(not isinstance(row, dict) for row in rows):
        raise RichDataError(
            "Eastmoney balance-sheet partition contains a non-object row"
        )

    ordered_keys: list[str] = []
    seen_keys: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen_keys:
                seen_keys.add(key)
                ordered_keys.append(key)
    if len(ordered_keys) < minimum_columns:
        raise RichDataError(
            "Eastmoney balance-sheet positional schema is too short: "
            f"{len(ordered_keys)} < {minimum_columns}"
        )
    maximum_position = max(int(value) for value in positions.values())
    if maximum_position >= len(ordered_keys):
        raise RichDataError("Eastmoney balance-sheet positional schema is incomplete")

    extracted: list[dict[str, Any]] = []
    for row in rows:
        extracted.append(
            {
                name: row.get(ordered_keys[int(positions[name])])
                for name in EASTMONEY_BALANCE_SHEET_RAW_POSITION_NAMES
            }
        )
    raw = pd.DataFrame(extracted)
    codes = raw["stock_code"].astype("string").str.strip()
    complete_code = codes.str.fullmatch(r"\d{6}", na=False)
    supported_code = codes.str.fullmatch(
        r"(?:60[0135]\d{3}|00[0-3]\d{3}|30[01]\d{3})", na=False
    )
    instrument = pd.Series(pd.NA, index=raw.index, dtype="string")
    instrument.loc[supported_code] = codes.loc[supported_code].map(qlib_symbol)
    duplicate_keys = int(instrument.loc[supported_code].duplicated(keep=False).sum())
    if duplicate_keys:
        raise RichDataError(
            "Eastmoney balance-sheet partition contains duplicate instrument/report-period keys"
        )

    announcement = pd.to_datetime(
        raw["announcement_date"], errors="coerce"
    ).dt.normalize()
    assets = pd.to_numeric(raw["total_assets"], errors="coerce")
    liabilities = pd.to_numeric(raw["total_liabilities"], errors="coerce")
    vendor_ratio = pd.to_numeric(
        raw["vendor_asset_liability_ratio_percent_for_formula_audit_only"],
        errors="coerce",
    )
    finite_assets = np.isfinite(assets)
    finite_liabilities = np.isfinite(liabilities)
    finite_ratio = np.isfinite(vendor_ratio)
    positive_assets = assets.gt(0.0)
    nonnegative_liabilities = liabilities.ge(0.0)
    liabilities_within_assets = liabilities.le(assets)
    derived = 1.0 - liabilities / assets
    formula_error = (1.0 - vendor_ratio / 100.0 - derived).abs()
    formula_consistent = formula_error.le(maximum_formula_error)
    valid = (
        supported_code
        & announcement.notna()
        & finite_assets
        & finite_liabilities
        & positive_assets
        & nonnegative_liabilities
        & liabilities_within_assets
        & finite_ratio
        & formula_consistent
    )

    result = pd.DataFrame(
        {
            "instrument": instrument.loc[valid].astype("string"),
            "report_date": pd.Timestamp(report_date),
            "announcement_date": announcement.loc[valid],
            "total_assets": assets.loc[valid].astype("float64"),
            "total_liabilities": liabilities.loc[valid].astype("float64"),
            "eastmoney_balance_sheet_resilience": derived.loc[valid].astype("float64"),
            "provider": "eastmoney",
        }
    )
    result = (
        result.loc[:, list(EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS)]
        .sort_values(["report_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    if (
        result.empty
        or result.duplicated(["instrument", "report_date"]).any()
        or not result["eastmoney_balance_sheet_resilience"].between(0.0, 1.0).all()
    ):
        raise RichDataError(
            "Eastmoney balance-sheet normalized frame failed the frozen integrity checks"
        )
    accepted_error = formula_error.loc[valid]
    accounting_base = (
        supported_code
        & announcement.notna()
        & finite_assets
        & finite_liabilities
        & positive_assets
        & nonnegative_liabilities
        & liabilities_within_assets
    )
    return result, {
        "input_rows": int(len(raw)),
        "ordered_source_column_count": int(len(ordered_keys)),
        "missing_or_malformed_stock_code_rows_excluded": int((~complete_code).sum()),
        "unsupported_board_rows_excluded": int((complete_code & ~supported_code).sum()),
        "missing_announcement_date_rows_excluded": int(announcement.isna().sum()),
        "nonfinite_asset_or_liability_rows_excluded": int(
            (~finite_assets | ~finite_liabilities).sum()
        ),
        "nonpositive_total_asset_rows_excluded": int(
            (finite_assets & ~positive_assets).sum()
        ),
        "negative_total_liability_rows_excluded": int(
            (finite_liabilities & ~nonnegative_liabilities).sum()
        ),
        "liability_above_asset_rows_excluded": int(
            (finite_assets & finite_liabilities & ~liabilities_within_assets).sum()
        ),
        "missing_or_nonfinite_vendor_ratio_rows_excluded": int(
            (accounting_base & ~finite_ratio).sum()
        ),
        "formula_inconsistent_rows_excluded": int(
            (accounting_base & finite_ratio & ~formula_consistent).sum()
        ),
        "accepted_formula_max_absolute_error": float(accepted_error.max()),
        "rows_written": int(len(result)),
    }


def load_eastmoney_balance_sheet_resilience_acceptance_record(
    path: Path = DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Verify the cross-clone terminal record for the consumed public probe."""

    path = path.expanduser().resolve()
    if file_digest(path) != EASTMONEY_BALANCE_SHEET_RESILIENCE_ACCEPTANCE_RECORD_SHA256:
        raise RichDataError(
            "Eastmoney balance-sheet-resilience acceptance-record fingerprint mismatch"
        )
    record = load_json_record(
        path,
        kind="a_share_eastmoney_balance_sheet_resilience_source_acceptance_record",
    )
    contract = record.get("data_contract") or {}
    mechanism = record.get("mechanism_audit") or {}
    manifest_link = record.get("acceptance_manifest") or {}
    frame_link = record.get("accepted_frame") or {}
    request = record.get("source_request") or {}
    observed = record.get("observed_result") or {}
    if (
        record.get("version") != 1
        or record.get("status")
        != "accepted_pending_frozen_full_history_and_no_return_gates"
        or record.get("created_at") != "2026-07-16T22:47:58Z"
        or contract.get("path")
        != "docs/a_share_eastmoney_balance_sheet_resilience_data_contract.json"
        or contract.get("sha256") != EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT_SHA256
        or contract.get("preregistered_at") != "2026-07-16T22:33:14Z"
        or contract.get("provider_rows_observed_before_freeze") is not False
        or contract.get("factor_values_observed_before_freeze") is not False
        or mechanism.get("path")
        != "docs/a_share_three_day_balance_sheet_resilience_mechanism_overlap_reaudit_20260717.json"
        or mechanism.get("sha256")
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_MECHANISM_AUDIT_SHA256
        or mechanism.get("source_locator_corrected_before_provider_rows") is not True
        or mechanism.get(
            "formula_direction_timing_threshold_or_gate_changed_during_correction"
        )
        is not False
        or manifest_link.get("path")
        != "data/metadata/rich_data/runs/20260716T224734Z_eastmoney_balance_sheet_resilience_acceptance_a890a7c4.json"
        or manifest_link.get("sha256")
        != "08badce50927da1083d684c1614e88ba260d3c2d54acf8d74cf59cf58c65ca8c"
        or manifest_link.get("run_id")
        != "20260716T224734Z_eastmoney_balance_sheet_resilience_acceptance_a890a7c4"
        or manifest_link.get("requested_report_date") != "2025-12-31"
        or manifest_link.get("acceptance_status")
        != "accepted_schema_formula_and_current_coverage_pending_full_history_no_return_gates"
        or frame_link.get("path")
        != "data/raw/a_share/rich/eastmoney/balance_sheet_resilience/acceptance/20260716T224734Z_eastmoney_balance_sheet_resilience_acceptance_a890a7c4/balance_sheet_resilience.parquet"
        or frame_link.get("content_sha256")
        != "a8c1c71071ecff9cf9b4d944b9962c861445c713d4fe2f12c479124e50850b25"
        or frame_link.get("file_sha256")
        != "1328eb3d32cba118281ee94eb3a07d8f4e312a2331f4e1e95c24f988c3b85014"
        or frame_link.get("rows") != 4543
        or tuple(frame_link.get("columns") or ())
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS
        or request.get("provider") != "eastmoney"
        or request.get("report_name") != "RPT_DMSK_FN_BALANCE"
        or request.get("advertised_pages") != 11
        or request.get("requested_pages") != list(range(1, 12))
        or request.get("provider_calls") != 11
        or request.get("advertised_rows") != 5218
        or request.get("received_rows") != 5218
        or request.get("ordered_source_column_count") != 57
        or request.get("ordered_source_columns_sha256")
        != "08dbc752c0ec71e56d9aea88c0a1ecfa0929dbe006c6b71bd6c7422d6b2515e3"
        or request.get("credentials_required_logged_or_stored") is not False
        or request.get("cookies_proxy_or_retail_session_used") is not False
        or request.get("unused_transported_fields_persisted") is not False
        or observed.get("all_market_source_rows") != 5218
        or observed.get("expected_point_in_time_holding_names") != 4581
        or observed.get("valid_holding_names") != 4543
        or observed.get("valid_holding_coverage") != 0.9917048679327658
        or observed.get("distinct_factor_values") != 4543
        or observed.get("accepted_formula_max_absolute_error") != 4.99933427988708e-13
        or observed.get("formula_inconsistent_rows_excluded") != 0
        or observed.get("schema_formula_and_current_coverage_gate_passed") is not True
        or record.get("price_fields_loaded") != []
        or record.get("open_close_or_forward_return_fields_read") is not False
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience acceptance record is incompatible"
        )

    manifest_file = resolve_record_path(str(manifest_link["path"]))
    frame_file = resolve_record_path(str(frame_link["path"]))
    if (
        not manifest_file.exists()
        or file_digest(manifest_file) != manifest_link["sha256"]
        or not frame_file.exists()
        or file_digest(frame_file) != frame_link["file_sha256"]
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience acceptance evidence fingerprint mismatch"
        )
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    files = list(manifest.get("files") or [])
    if (
        manifest.get("dataset") != "eastmoney_balance_sheet_resilience_acceptance"
        or manifest.get("provider") != "eastmoney"
        or manifest.get("run_id") != manifest_link["run_id"]
        or manifest.get("requested_report_date") != "2025-12-31"
        or manifest.get("acceptance_status") != manifest_link["acceptance_status"]
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
        or len(files) != 1
        or files[0].get("path") != frame_link["path"]
        or files[0].get("rows") != 4543
        or files[0].get("sha256") != frame_link["content_sha256"]
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience acceptance manifest identity mismatch"
        )
    frame = pd.read_parquet(frame_file)
    assets = pd.to_numeric(frame["total_assets"], errors="coerce")
    liabilities = pd.to_numeric(frame["total_liabilities"], errors="coerce")
    factor = pd.to_numeric(frame["eastmoney_balance_sheet_resilience"], errors="coerce")
    if (
        tuple(frame.columns) != EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS
        or len(frame) != 4543
        or frame_digest(frame) != frame_link["content_sha256"]
        or frame.duplicated(["instrument", "report_date"]).any()
        or not pd.to_datetime(frame["report_date"], errors="coerce")
        .dt.normalize()
        .eq(pd.Timestamp("2025-12-31"))
        .all()
        or pd.to_datetime(frame["announcement_date"], errors="coerce").isna().any()
        or not np.isfinite(assets).all()
        or not assets.gt(0.0).all()
        or not np.isfinite(liabilities).all()
        or not liabilities.ge(0.0).all()
        or not liabilities.le(assets).all()
        or not np.isfinite(factor).all()
        or not np.allclose(
            factor.to_numpy(dtype="float64"),
            1.0
            - liabilities.to_numpy(dtype="float64") / assets.to_numpy(dtype="float64"),
            rtol=0.0,
            atol=1e-12,
        )
        or not frame["provider"].eq("eastmoney").all()
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience accepted factor integrity audit failed"
        )
    return record


def load_eastmoney_balance_sheet_resilience_source_chain(
    path: Path = DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_NO_RETURN_SPEC,
) -> dict[str, Any]:
    """Verify the accepted source and frozen pre-history no-return protocol."""

    path = path.expanduser().resolve()
    if file_digest(path) != EASTMONEY_BALANCE_SHEET_RESILIENCE_NO_RETURN_SPEC_SHA256:
        raise RichDataError(
            "Eastmoney balance-sheet-resilience no-return spec fingerprint mismatch"
        )
    spec = load_json_record(
        path,
        kind="a_share_eastmoney_balance_sheet_resilience_no_return_preregistration",
    )
    contract = load_eastmoney_balance_sheet_resilience_contract()
    record = load_eastmoney_balance_sheet_resilience_acceptance_record()
    source_chain = spec.get("source_chain") or {}
    full = spec.get("full_source_snapshot_contract") or {}
    normalization = spec.get("normalization_contract") or {}
    capacity = spec.get("capacity_contract") or {}
    uniqueness = spec.get("uniqueness_contract") or {}
    expected_dates = [
        f"{year}-{month_day}"
        for year in range(2019, 2026)
        for month_day in ("03-31", "06-30", "09-30", "12-31")
    ]
    if (
        spec.get("version") != 1
        or spec.get("status")
        != "frozen_after_source_acceptance_before_full_source_capacity_uniqueness_prices_or_returns"
        or spec.get("preregistered_at") != "2026-07-16T22:49:30Z"
        or (source_chain.get("data_contract") or {}).get("sha256")
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT_SHA256
        or (source_chain.get("mechanism_audit") or {}).get("sha256")
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_MECHANISM_AUDIT_SHA256
        or (source_chain.get("acceptance_record") or {}).get("sha256")
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_ACCEPTANCE_RECORD_SHA256
        or (source_chain.get("acceptance_manifest") or {}).get("sha256")
        != "08badce50927da1083d684c1614e88ba260d3c2d54acf8d74cf59cf58c65ca8c"
        or (source_chain.get("accepted_frame") or {}).get("content_sha256")
        != "a8c1c71071ecff9cf9b4d944b9962c861445c713d4fe2f12c479124e50850b25"
        or (source_chain.get("accepted_frame") or {}).get("file_sha256")
        != "1328eb3d32cba118281ee94eb3a07d8f4e312a2331f4e1e95c24f988c3b85014"
        or (source_chain.get("accepted_frame") or {}).get("report_date") != "2025-12-31"
        or (source_chain.get("accepted_frame") or {}).get("rows") != 4543
        or (source_chain.get("accepted_ordered_source_schema") or {}).get(
            "ordered_source_column_count"
        )
        != 57
        or (source_chain.get("accepted_ordered_source_schema") or {}).get(
            "ordered_source_columns_sha256"
        )
        != "08dbc752c0ec71e56d9aea88c0a1ecfa0929dbe006c6b71bd6c7422d6b2515e3"
        or full.get("report_dates") != expected_dates
        or full.get("required_report_date_count") != 28
        or full.get("accepted_partition_reused_without_network") != "2025-12-31"
        or full.get("new_network_partitions") != 27
        or full.get("maximum_new_provider_calls") != 540
        or full.get("minimum_valid_active_holding_coverage_per_report_date") != 0.85
        or full.get("minimum_median_valid_active_holding_coverage") != 0.95
        or full.get("minimum_distinct_factor_values_per_nonempty_partition") != 100
        or tuple(normalization.get("columns") or ())
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS
        or normalization.get("factor_formula") != "1 - total_liabilities / total_assets"
        or normalization.get("maximum_formula_absolute_error") != 1e-8
        or capacity.get("must_run_before_comparison_fields_or_prices") is not True
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_observed_years") != 5
        or uniqueness.get("allowed_only_after_capacity_passes") is not True
        or uniqueness.get("dense_comparison_factor_count") != 46
        or uniqueness.get("minimum_pairwise_sessions_per_dense_comparison") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or spec.get("historical_provider_rows_observed_before_freeze") is not False
        or spec.get("historical_factor_values_observed_before_freeze") is not False
        or spec.get("price_fields_loaded") != []
        or spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience no-return spec does not match the frozen protocol"
        )
    for label, link in source_chain.items():
        if not isinstance(link, dict) or "path" not in link or "sha256" not in link:
            continue
        linked_path = resolve_record_path(str(link.get("path") or ""))
        if not linked_path.exists() or file_digest(linked_path) != link.get("sha256"):
            raise RichDataError(
                f"Eastmoney balance-sheet-resilience source-chain evidence changed: {label}"
            )
    frame_path = resolve_record_path(
        str((source_chain.get("accepted_frame") or {}).get("path") or "")
    )
    if not frame_path.exists() or file_digest(frame_path) != (
        source_chain.get("accepted_frame") or {}
    ).get("file_sha256"):
        raise RichDataError("Eastmoney balance-sheet-resilience accepted frame changed")
    accepted_frame = pd.read_parquet(frame_path)
    if (
        tuple(accepted_frame.columns) != EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS
        or len(accepted_frame) != 4543
        or frame_digest(accepted_frame)
        != (source_chain.get("accepted_frame") or {}).get("content_sha256")
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience accepted frame integrity failed"
        )
    return {
        "spec_path": path,
        "spec": spec,
        "contract": contract,
        "acceptance_record": record,
        "accepted_frame_path": frame_path,
        "accepted_frame": accepted_frame,
    }


def eastmoney_balance_sheet_resilience_acceptance_records() -> list[Path]:
    """Return prior local success or rejection manifests for the one-shot probe."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(
        RUNS_ROOT.glob("*eastmoney_balance_sheet_resilience_acceptance*.json")
    ):
        payload = load_json_record(path)
        if payload.get("dataset") == "eastmoney_balance_sheet_resilience_acceptance":
            records.append(path)
    return records


def sync_eastmoney_balance_sheet_resilience_acceptance(
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
) -> Path:
    """Run the sole frozen no-price public balance-sheet source acceptance."""

    if DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_ACCEPTANCE_RECORD.exists():
        load_eastmoney_balance_sheet_resilience_acceptance_record()
        raise RichDataError(
            "Eastmoney balance-sheet-resilience acceptance is permanently consumed; "
            "another provider request is forbidden"
        )
    with RichDataProcessLock(
        METADATA_ROOT / ".eastmoney_balance_sheet_resilience_acceptance.lock"
    ):
        if DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_ACCEPTANCE_RECORD.exists():
            load_eastmoney_balance_sheet_resilience_acceptance_record()
            raise RichDataError(
                "Eastmoney balance-sheet-resilience acceptance is permanently consumed; "
                "another provider request is forbidden"
            )
        prior_records = eastmoney_balance_sheet_resilience_acceptance_records()
        if prior_records:
            raise RichDataError(
                "Eastmoney balance-sheet-resilience acceptance is one-shot and already "
                f"consumed by {prior_records[-1]}"
            )
        contract = load_eastmoney_balance_sheet_resilience_contract()
        acceptance = contract["acceptance_protocol"]
        report_date = dt.date.fromisoformat(acceptance["fixed_report_date"])
        run_id = new_run_id("eastmoney_balance_sheet_resilience_acceptance")
        run_root = (
            RAW_ROOT / "eastmoney" / "balance_sheet_resilience" / "acceptance" / run_id
        )
        temporary_root = run_root.parent / f".{run_id}.tmp"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Eastmoney balance-sheet-resilience acceptance already exists: {run_id}"
            )
        retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
        provider_request_issued = False
        try:
            provider_request_issued = True
            raw_rows, request_quality = fetch_eastmoney_balance_sheet_partition(
                report_date, contract=contract
            )
            normalized, quality = canonicalize_eastmoney_balance_sheet_resilience(
                raw_rows, report_date, contract=contract
            )
            intervals = load_factor_universe_intervals(universe_path)
            report_session = pd.Timestamp(report_date)
            active_rows = intervals[
                intervals["start_date"].le(report_session)
                & intervals["end_date"].ge(report_session)
            ]
            active_instruments = set(active_rows["instrument"].astype(str))
            if not active_instruments:
                raise RichDataError(
                    "buyable holding universe has no active balance-sheet report-date names"
                )
            in_universe = normalized["instrument"].isin(active_instruments)
            outside_universe = int((~in_universe).sum())
            accepted = normalized.loc[in_universe].reset_index(drop=True)
            expected_names = int(len(active_instruments))
            observed_names = int(accepted["instrument"].nunique())
            coverage = observed_names / expected_names
            minimum_names = int(acceptance["minimum_valid_holding_names"])
            minimum_coverage = float(
                acceptance["minimum_valid_point_in_time_holding_coverage"]
            )
            if observed_names < minimum_names:
                raise RichDataError(
                    "Eastmoney balance-sheet acceptance has too few valid holding names: "
                    f"{observed_names} < {minimum_names}"
                )
            if coverage < minimum_coverage:
                raise RichDataError(
                    "Eastmoney balance-sheet holding coverage failed: "
                    f"{coverage:.6f} < {minimum_coverage:.6f}"
                )
            distinct_values = int(
                accepted["eastmoney_balance_sheet_resilience"].nunique(dropna=True)
            )
            minimum_values = int(acceptance["minimum_distinct_factor_values"])
            if distinct_values < minimum_values:
                raise RichDataError(
                    "Eastmoney balance-sheet acceptance lacks factor variation: "
                    f"{distinct_values} < {minimum_values}"
                )
            formula_error = float(quality["accepted_formula_max_absolute_error"])
            if formula_error > float(acceptance["maximum_formula_absolute_error"]):
                raise RichDataError(
                    "Eastmoney balance-sheet accepted formula audit exceeded tolerance"
                )
            if (
                tuple(accepted.columns) != EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS
                or accepted.duplicated(["instrument", "report_date"]).any()
            ):
                raise RichDataError(
                    "Eastmoney balance-sheet accepted frame violates the frozen schema"
                )

            temporary_destination = temporary_root / "balance_sheet_resilience.parquet"
            final_destination = run_root / "balance_sheet_resilience.parquet"
            atomic_write_frame(accepted, temporary_destination)
            resolved_universe = universe_path.expanduser().resolve()
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "eastmoney_balance_sheet_resilience_acceptance",
                "provider": "eastmoney",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "requested_report_date": report_date.isoformat(),
                "data_contract": {
                    "path": manifest_path(
                        DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT
                    ),
                    "sha256": file_digest(
                        DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT
                    ),
                    "preregistered_at": contract["preregistered_at"],
                },
                "mechanism_audit": contract["mechanism_selection"],
                "point_in_time_holding_universe": {
                    "path": manifest_path(resolved_universe),
                    "sha256": file_digest(resolved_universe),
                    "active_names_on_report_date": expected_names,
                },
                "source_request": {
                    "endpoint": contract["source"]["endpoint"],
                    "report_name": contract["source"]["report_name"],
                    "request_mode": "one fixed count-complete quarterly partition",
                    "provider_request_issued": provider_request_issued,
                    "credentials_required_logged_or_stored": False,
                    "cookies_proxy_or_retail_session_used": False,
                    "unused_transported_fields_persisted": False,
                    **request_quality,
                },
                "files": [
                    {
                        "path": manifest_path(final_destination),
                        "rows": int(len(accepted)),
                        "sha256": frame_digest(accepted),
                    }
                ],
                "source_quality": {
                    **quality,
                    "outside_point_in_time_holding_universe_rows_excluded": (
                        outside_universe
                    ),
                    "expected_active_holding_names": expected_names,
                    "valid_holding_names": observed_names,
                    "valid_holding_coverage": coverage,
                    "distinct_factor_values": distinct_values,
                },
                "acceptance_status": acceptance["success_status"],
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "eastmoney_balance_sheet_resilience_acceptance",
                "provider": "eastmoney",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "requested_report_date": report_date.isoformat(),
                "data_contract": {
                    "path": manifest_path(
                        DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT
                    ),
                    "sha256": file_digest(
                        DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT
                    ),
                },
                "source_request": {
                    "endpoint": contract["source"]["endpoint"],
                    "report_name": contract["source"]["report_name"],
                    "provider_request_issued": provider_request_issued,
                    "credentials_required_logged_or_stored": False,
                    "cookies_proxy_or_retail_session_used": False,
                },
                "files": [],
                "partial_snapshot_deleted": True,
                "acceptance_status": "terminal_schema_formula_or_current_coverage_rejected_stop_before_full_history_capacity_uniqueness_or_returns",
                "error_type": type(exc).__name__,
                "error": safe_exception_text(exc),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            failure_path = RUNS_ROOT / f"{run_id}.json"
            atomic_write_json(failure, failure_path)
            raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def load_eastmoney_core_profit_consistency_acceptance_record(
    path: Path = DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Verify the cross-clone record for the consumed public income probe."""

    path = path.expanduser().resolve()
    if (
        file_digest(path)
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_ACCEPTANCE_RECORD_SHA256
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency acceptance-record fingerprint mismatch"
        )
    record = load_json_record(
        path,
        kind="a_share_eastmoney_core_profit_consistency_source_acceptance_record",
    )
    contract = record.get("data_contract") or {}
    mechanism = record.get("mechanism_audit") or {}
    manifest_link = record.get("acceptance_manifest") or {}
    frame_link = record.get("accepted_frame") or {}
    request = record.get("source_request") or {}
    observed = record.get("observed_result") or {}
    if (
        record.get("version") != 1
        or record.get("status")
        != "accepted_pending_frozen_full_history_and_no_return_gates"
        or contract.get("sha256")
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT_SHA256
        or mechanism.get("sha256")
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_MECHANISM_AUDIT_SHA256
        or manifest_link.get("sha256")
        != "c7be7442df45d017c5c4b74500c9949f05f6142e09503b6ff989d1fcbc20ea12"
        or manifest_link.get("run_id")
        != "20260716T234306Z_eastmoney_core_profit_consistency_acceptance_722adbdf"
        or manifest_link.get("requested_report_date") != "2025-12-31"
        or manifest_link.get("acceptance_status")
        != "accepted_schema_formula_and_current_coverage_pending_full_history_no_return_gates"
        or frame_link.get("content_sha256")
        != "7a487d4fc8df60ecee8763772dd4aac4b88423aa491c1a580398b5008c84e794"
        or frame_link.get("file_sha256")
        != "2c7e83fb6916cd73073687cfb194df7862bd549cd244133dffd1baf7c2570f57"
        or frame_link.get("rows") != 3370
        or tuple(frame_link.get("columns") or ())
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS
        or request.get("report_name") != "RPT_DMSK_FN_INCOME"
        or request.get("advertised_pages") != 11
        or request.get("requested_pages") != list(range(1, 12))
        or request.get("provider_calls") != 11
        or request.get("advertised_rows") != 5218
        or request.get("received_rows") != 5218
        or request.get("ordered_source_column_count") != 46
        or request.get("ordered_source_columns_sha256")
        != "81e5eff36c353c65bbb7728780a4e9663fbbad7b779e44c74921ce57d1f6656f"
        or request.get("tushare_token_read") is not False
        or observed.get("expected_point_in_time_holding_names") != 4581
        or observed.get("complete_identity_holding_names") != 4574
        or observed.get("valid_factor_holding_names") != 3370
        or observed.get("distinct_factor_values") != 3369
        or not math.isclose(
            float(observed.get("complete_identity_holding_coverage")),
            0.9984719493560358,
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        or not math.isclose(
            float(observed.get("valid_factor_holding_coverage")),
            0.7356472385941935,
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        or observed.get("schema_formula_and_current_coverage_gate_passed")
        is not True
        or record.get("price_fields_loaded") != []
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency acceptance record is inconsistent"
        )
    for label, link in (
        ("contract", contract),
        ("mechanism audit", mechanism),
    ):
        linked_path = resolve_record_path(str(link.get("path") or ""))
        if not linked_path.exists() or file_digest(linked_path) != link.get("sha256"):
            raise RichDataError(
                f"Eastmoney core-profit-consistency {label} changed"
            )
    manifest_file = resolve_record_path(str(manifest_link.get("path") or ""))
    frame_file = resolve_record_path(str(frame_link.get("path") or ""))
    if (
        not manifest_file.exists()
        or file_digest(manifest_file) != manifest_link["sha256"]
        or not frame_file.exists()
        or file_digest(frame_file) != frame_link["file_sha256"]
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency acceptance evidence changed"
        )
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    files = list(manifest.get("files") or [])
    if (
        manifest.get("dataset") != "eastmoney_core_profit_consistency_acceptance"
        or manifest.get("run_id") != manifest_link["run_id"]
        or manifest.get("requested_report_date") != "2025-12-31"
        or manifest.get("acceptance_status") != manifest_link["acceptance_status"]
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or len(files) != 1
        or files[0].get("path") != frame_link["path"]
        or files[0].get("rows") != 3370
        or files[0].get("sha256") != frame_link["content_sha256"]
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency acceptance manifest changed"
        )
    frame = pd.read_parquet(frame_file)
    operating = pd.to_numeric(frame["operating_profit"], errors="coerce")
    total = pd.to_numeric(frame["total_profit"], errors="coerce")
    factor = pd.to_numeric(
        frame["eastmoney_core_profit_consistency"], errors="coerce"
    )
    recomputed = np.minimum(operating, total) / np.maximum(operating, total)
    if (
        tuple(frame.columns) != EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS
        or len(frame) != 3370
        or frame_digest(frame) != frame_link["content_sha256"]
        or frame.duplicated(["instrument", "report_date"]).any()
        or not operating.gt(0.0).all()
        or not total.gt(0.0).all()
        or not np.isfinite(factor).all()
        or not np.allclose(
            factor.to_numpy(dtype="float64"),
            recomputed.to_numpy(dtype="float64"),
            rtol=0.0,
            atol=1e-12,
        )
        or not frame["provider"].eq("eastmoney").all()
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency accepted factor integrity failed"
        )
    return record


def load_eastmoney_core_profit_consistency_source_chain(
    path: Path = DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_NO_RETURN_SPEC,
) -> dict[str, Any]:
    """Verify the accepted source and frozen pre-history no-return protocol."""

    path = path.expanduser().resolve()
    if file_digest(path) != EASTMONEY_CORE_PROFIT_CONSISTENCY_NO_RETURN_SPEC_SHA256:
        raise RichDataError(
            "Eastmoney core-profit no-return preregistration fingerprint mismatch"
        )
    spec = load_json_record(
        path,
        kind="a_share_eastmoney_core_profit_consistency_no_return_preregistration",
    )
    contract = load_eastmoney_core_profit_consistency_contract()
    record = load_eastmoney_core_profit_consistency_acceptance_record()
    chain = spec.get("source_chain") or {}
    full = spec.get("full_source_snapshot_contract") or {}
    normalization = spec.get("normalization_contract") or {}
    state = spec.get("conservative_state_contract") or {}
    capacity = spec.get("capacity_contract") or {}
    uniqueness = spec.get("uniqueness_contract") or {}
    expected_dates = [
        f"{year}-{month_day}"
        for year in range(2019, 2026)
        for month_day in ("03-31", "06-30", "09-30", "12-31")
    ]
    if (
        spec.get("version") != 1
        or spec.get("status")
        != "frozen_after_source_acceptance_before_full_source_capacity_uniqueness_prices_or_returns"
        or spec.get("preregistered_at") != "2026-07-16T23:46:00Z"
        or (chain.get("mechanism_audit") or {}).get("sha256")
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_MECHANISM_AUDIT_SHA256
        or (chain.get("data_contract") or {}).get("sha256")
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT_SHA256
        or (chain.get("acceptance_record") or {}).get("sha256")
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_ACCEPTANCE_RECORD_SHA256
        or (chain.get("acceptance_manifest") or {}).get("sha256")
        != "c7be7442df45d017c5c4b74500c9949f05f6142e09503b6ff989d1fcbc20ea12"
        or (chain.get("accepted_frame") or {}).get("content_sha256")
        != "7a487d4fc8df60ecee8763772dd4aac4b88423aa491c1a580398b5008c84e794"
        or (chain.get("accepted_frame") or {}).get("file_sha256")
        != "2c7e83fb6916cd73073687cfb194df7862bd549cd244133dffd1baf7c2570f57"
        or (chain.get("accepted_frame") or {}).get("rows") != 3370
        or (chain.get("accepted_ordered_source_schema") or {}).get(
            "ordered_source_column_count"
        )
        != 46
        or (chain.get("accepted_ordered_source_schema") or {}).get(
            "ordered_source_columns_sha256"
        )
        != "81e5eff36c353c65bbb7728780a4e9663fbbad7b779e44c74921ce57d1f6656f"
        or full.get("report_dates") != expected_dates
        or full.get("required_report_date_count") != 28
        or full.get("accepted_partition_reused_without_network") != "2025-12-31"
        or full.get("new_network_partitions") != 27
        or full.get("maximum_new_provider_calls") != 540
        or full.get("minimum_complete_identity_active_holding_coverage_per_report_date")
        != 0.85
        or full.get("minimum_median_complete_identity_active_holding_coverage")
        != 0.95
        or full.get("minimum_valid_factor_active_holding_coverage_per_report_date")
        != 0.45
        or full.get("minimum_median_valid_factor_active_holding_coverage") != 0.6
        or tuple(normalization.get("columns") or ())
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS
        or normalization.get("factor_formula")
        != "min(operating_profit, total_profit) / max(operating_profit, total_profit)"
        or normalization.get("maximum_formula_absolute_error") != 1e-12
        or state.get("clear_all_older_values_at_global_partition_activation")
        is not True
        or state.get("carry_older_value_when_new_partition_has_missing_or_invalid_instrument")
        is not False
        or state.get("late_older_correction_can_supersede_newer_period") is not False
        or state.get("maximum_age_calendar_days") != 550
        or capacity.get("must_run_before_comparison_fields_or_prices") is not True
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_observed_years") != 5
        or uniqueness.get("allowed_only_after_capacity_passes") is not True
        or uniqueness.get("dense_comparison_factor_count") != 47
        or len(uniqueness.get("dense_comparison_factors") or []) != 47
        or uniqueness.get("minimum_pairwise_sessions_per_dense_comparison") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or uniqueness.get("sparse_event_factors_loaded") != []
        or spec.get("historical_provider_rows_observed_before_freeze") is not False
        or spec.get("historical_factor_values_observed_before_freeze") is not False
        or spec.get("price_fields_loaded") != []
        or spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Eastmoney core-profit no-return spec does not match the frozen protocol"
        )
    for label, link in chain.items():
        if not isinstance(link, dict) or "path" not in link or "sha256" not in link:
            continue
        linked_path = resolve_record_path(str(link.get("path") or ""))
        if not linked_path.exists() or file_digest(linked_path) != link.get("sha256"):
            raise RichDataError(
                f"Eastmoney core-profit source-chain evidence changed: {label}"
            )
    frame_path = resolve_record_path(
        str((chain.get("accepted_frame") or {}).get("path") or "")
    )
    if not frame_path.exists() or file_digest(frame_path) != (
        chain.get("accepted_frame") or {}
    ).get("file_sha256"):
        raise RichDataError("Eastmoney core-profit accepted frame changed")
    accepted_frame = pd.read_parquet(frame_path)
    if (
        tuple(accepted_frame.columns)
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS
        or len(accepted_frame) != 3370
        or frame_digest(accepted_frame)
        != (chain.get("accepted_frame") or {}).get("content_sha256")
    ):
        raise RichDataError("Eastmoney core-profit accepted frame integrity failed")
    return {
        "spec_path": path,
        "spec": spec,
        "contract": contract,
        "acceptance_record": record,
        "accepted_frame_path": frame_path,
        "accepted_frame": accepted_frame,
    }


def eastmoney_core_profit_consistency_acceptance_records() -> list[Path]:
    """Return prior local manifests for the one-shot public income probe."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(
        RUNS_ROOT.glob("*eastmoney_core_profit_consistency_acceptance*.json")
    ):
        payload = load_json_record(path)
        if payload.get("dataset") == "eastmoney_core_profit_consistency_acceptance":
            records.append(path)
    return records


def sync_eastmoney_core_profit_consistency_acceptance(
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
) -> Path:
    """Run the sole frozen no-price public core-profit source acceptance."""

    if DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_ACCEPTANCE_RECORD.exists():
        load_eastmoney_core_profit_consistency_acceptance_record()
        raise RichDataError(
            "Eastmoney core-profit-consistency acceptance is permanently consumed; "
            "another provider request is forbidden"
        )
    with RichDataProcessLock(
        METADATA_ROOT / ".eastmoney_core_profit_consistency_acceptance.lock"
    ):
        if DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_ACCEPTANCE_RECORD.exists():
            load_eastmoney_core_profit_consistency_acceptance_record()
            raise RichDataError(
                "Eastmoney core-profit-consistency acceptance is permanently consumed; "
                "another provider request is forbidden"
            )
        prior_records = eastmoney_core_profit_consistency_acceptance_records()
        if prior_records:
            raise RichDataError(
                "Eastmoney core-profit-consistency acceptance is one-shot and already "
                f"consumed by {prior_records[-1]}"
            )
        contract = load_eastmoney_core_profit_consistency_contract()
        acceptance = contract["acceptance_protocol"]
        report_date = dt.date.fromisoformat(acceptance["fixed_report_date"])
        run_id = new_run_id("eastmoney_core_profit_consistency_acceptance")
        run_root = (
            RAW_ROOT
            / "eastmoney"
            / "core_profit_consistency"
            / "acceptance"
            / run_id
        )
        temporary_root = run_root.parent / f".{run_id}.tmp"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Eastmoney core-profit-consistency acceptance already exists: {run_id}"
            )
        retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
        provider_request_issued = False
        try:
            provider_request_issued = True
            raw_rows, request_quality = (
                fetch_eastmoney_core_profit_consistency_partition(
                    report_date, contract=contract
                )
            )
            normalized, quality = canonicalize_eastmoney_core_profit_consistency(
                raw_rows,
                report_date,
                contract=contract,
            )
            complete_identity_instruments = set(
                quality.pop("complete_identity_instruments_for_acceptance_only")
            )
            intervals = load_factor_universe_intervals(universe_path)
            report_session = pd.Timestamp(report_date)
            active_rows = intervals[
                intervals["start_date"].le(report_session)
                & intervals["end_date"].ge(report_session)
            ]
            active_instruments = set(active_rows["instrument"].astype(str))
            if not active_instruments:
                raise RichDataError(
                    "buyable holding universe has no active core-profit report-date names"
                )
            expected_names = int(len(active_instruments))
            complete_identity_names = int(
                len(complete_identity_instruments & active_instruments)
            )
            complete_identity_coverage = complete_identity_names / expected_names
            in_universe = normalized["instrument"].isin(active_instruments)
            outside_universe = int((~in_universe).sum())
            accepted = normalized.loc[in_universe].reset_index(drop=True)
            valid_factor_names = int(accepted["instrument"].nunique())
            valid_factor_coverage = valid_factor_names / expected_names
            if complete_identity_names < int(
                acceptance["minimum_complete_identity_holding_names"]
            ):
                raise RichDataError(
                    "Eastmoney core-profit acceptance has too few complete-identity "
                    f"holding names: {complete_identity_names}"
                )
            if complete_identity_coverage < float(
                acceptance["minimum_complete_identity_holding_coverage"]
            ):
                raise RichDataError(
                    "Eastmoney core-profit complete-identity coverage failed: "
                    f"{complete_identity_coverage:.6f}"
                )
            if valid_factor_names < int(
                acceptance["minimum_valid_factor_holding_names"]
            ):
                raise RichDataError(
                    "Eastmoney core-profit acceptance has too few valid factor names: "
                    f"{valid_factor_names}"
                )
            if valid_factor_coverage < float(
                acceptance["minimum_valid_factor_holding_coverage"]
            ):
                raise RichDataError(
                    "Eastmoney core-profit valid-factor coverage failed: "
                    f"{valid_factor_coverage:.6f}"
                )
            distinct_values = int(
                accepted["eastmoney_core_profit_consistency"].nunique(dropna=True)
            )
            if distinct_values < int(acceptance["minimum_distinct_factor_values"]):
                raise RichDataError(
                    "Eastmoney core-profit acceptance lacks factor variation: "
                    f"{distinct_values}"
                )
            if float(quality["accepted_formula_max_absolute_error"]) > float(
                acceptance["maximum_equivalent_formula_absolute_error"]
            ):
                raise RichDataError(
                    "Eastmoney core-profit accepted formula audit exceeded tolerance"
                )
            if (
                tuple(accepted.columns)
                != EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS
                or accepted.duplicated(["instrument", "report_date"]).any()
            ):
                raise RichDataError(
                    "Eastmoney core-profit accepted frame violates the frozen schema"
                )

            temporary_destination = temporary_root / "core_profit_consistency.parquet"
            final_destination = run_root / "core_profit_consistency.parquet"
            atomic_write_frame(accepted, temporary_destination)
            resolved_universe = universe_path.expanduser().resolve()
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "eastmoney_core_profit_consistency_acceptance",
                "provider": "eastmoney",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "requested_report_date": report_date.isoformat(),
                "data_contract": {
                    "path": manifest_path(
                        DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT
                    ),
                    "sha256": EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT_SHA256,
                    "preregistered_at": contract["preregistered_at"],
                },
                "mechanism_audit": contract["mechanism_selection"],
                "point_in_time_holding_universe": {
                    "path": manifest_path(resolved_universe),
                    "sha256": file_digest(resolved_universe),
                    "active_names_on_report_date": expected_names,
                },
                "source_request": {
                    "endpoint": contract["source"]["endpoint"],
                    "report_name": contract["source"]["report_name"],
                    "request_mode": "one fixed count-complete quarterly partition",
                    "provider_request_issued": provider_request_issued,
                    "credentials_required_logged_or_stored": False,
                    "tushare_token_read": False,
                    "cookies_proxy_or_retail_session_used": False,
                    "unused_transported_fields_persisted": False,
                    **request_quality,
                },
                "files": [
                    {
                        "path": manifest_path(final_destination),
                        "rows": int(len(accepted)),
                        "sha256": frame_digest(accepted),
                    }
                ],
                "source_quality": {
                    **quality,
                    "outside_point_in_time_holding_universe_rows_excluded": (
                        outside_universe
                    ),
                    "expected_active_holding_names": expected_names,
                    "complete_identity_holding_names": complete_identity_names,
                    "complete_identity_holding_coverage": (
                        complete_identity_coverage
                    ),
                    "valid_factor_holding_names": valid_factor_names,
                    "valid_factor_holding_coverage": valid_factor_coverage,
                    "distinct_factor_values": distinct_values,
                },
                "acceptance_status": acceptance["success_status"],
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "eastmoney_core_profit_consistency_acceptance",
                "provider": "eastmoney",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "requested_report_date": report_date.isoformat(),
                "data_contract": {
                    "path": manifest_path(
                        DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT
                    ),
                    "sha256": EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT_SHA256,
                },
                "source_request": {
                    "endpoint": contract["source"]["endpoint"],
                    "report_name": contract["source"]["report_name"],
                    "provider_request_issued": provider_request_issued,
                    "credentials_required_logged_or_stored": False,
                    "tushare_token_read": False,
                    "cookies_proxy_or_retail_session_used": False,
                },
                "files": [],
                "partial_snapshot_deleted": True,
                "acceptance_status": "terminal_schema_formula_or_current_coverage_rejected_stop_before_full_history_capacity_uniqueness_or_returns",
                "error_type": type(exc).__name__,
                "error": safe_exception_text(exc),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            failure_path = RUNS_ROOT / f"{run_id}.json"
            atomic_write_json(failure, failure_path)
            raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def load_eastmoney_balance_sheet_resilience_full_source_record(
    path: Path = DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_FULL_SOURCE_RECORD,
) -> dict[str, Any]:
    """Verify the cross-clone terminal record for the consumed full source."""

    path = path.expanduser().resolve()
    if (
        file_digest(path)
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_FULL_SOURCE_RECORD_SHA256
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience full-source-record fingerprint mismatch"
        )
    record = load_json_record(
        path,
        kind="a_share_eastmoney_balance_sheet_resilience_full_source_record",
    )
    contract = record.get("data_contract") or {}
    acceptance = record.get("source_acceptance_record") or {}
    spec = record.get("no_return_preregistration") or {}
    manifest_link = record.get("full_source_manifest") or {}
    snapshot = record.get("published_snapshot") or {}
    request = record.get("source_request") or {}
    coverage = record.get("coverage") or {}
    if (
        record.get("version") != 1
        or record.get("status")
        != "accepted_full_source_pending_no_return_capacity_and_uniqueness"
        or record.get("created_at") != "2026-07-16T22:58:31Z"
        or contract.get("sha256") != EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT_SHA256
        or acceptance.get("sha256")
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_ACCEPTANCE_RECORD_SHA256
        or spec.get("sha256")
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_NO_RETURN_SPEC_SHA256
        or manifest_link.get("path")
        != "data/metadata/rich_data/runs/20260716T225547Z_eastmoney_balance_sheet_resilience_b960bfe6.json"
        or manifest_link.get("sha256")
        != "b69e71c57ecbef956709e853d5da6054fd28f6c44d53ead2b51273641ecba9fe"
        or manifest_link.get("run_id")
        != "20260716T225547Z_eastmoney_balance_sheet_resilience_b960bfe6"
        or manifest_link.get("status")
        != "full_source_coverage_passed_pending_no_return_capacity_and_uniqueness"
        or snapshot.get("partition_count") != 28
        or snapshot.get("total_rows") != 113916
        or snapshot.get("minimum_partition_rows") != 3374
        or snapshot.get("maximum_partition_rows") != 4543
        or tuple(snapshot.get("columns") or ())
        != EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS
        or snapshot.get("canonical_partition_file_sha256_listing_sha256")
        != "669ea5aebbbe9467b5b538b4110ea7ed9de6fa8ca0f9e721545b0a8573ac68a3"
        or request.get("new_network_partitions") != 27
        or request.get("accepted_partitions_reused_without_network") != 1
        or request.get("new_provider_calls") != 277
        or request.get("ordered_source_column_count") != 57
        or request.get("ordered_source_columns_sha256")
        != "08dbc752c0ec71e56d9aea88c0a1ecfa0929dbe006c6b71bd6c7422d6b2515e3"
        or coverage.get("minimum_valid_active_holding_coverage") != 0.9374826340650181
        or coverage.get("median_valid_active_holding_coverage") != 0.9661019339064675
        or coverage.get("maximum_valid_active_holding_coverage") != 0.9917048679327658
        or coverage.get("all_28_partitions_present") is not True
        or coverage.get("source_coverage_gate_passed") is not True
        or record.get("price_fields_loaded") != []
        or record.get("open_close_or_forward_return_fields_read") is not False
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience full-source record is incompatible"
        )

    manifest_file = resolve_record_path(str(manifest_link["path"]))
    if (
        not manifest_file.exists()
        or file_digest(manifest_file) != manifest_link["sha256"]
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience full-source manifest changed"
        )
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    files = sorted(
        list(manifest.get("files") or []), key=lambda item: item.get("report_date", "")
    )
    expected_dates = [
        f"{year}-{month_day}"
        for year in range(2019, 2026)
        for month_day in ("03-31", "06-30", "09-30", "12-31")
    ]
    if (
        manifest.get("dataset") != "eastmoney_balance_sheet_resilience"
        or manifest.get("provider") != "eastmoney"
        or manifest.get("run_id") != manifest_link["run_id"]
        or manifest.get("status") != manifest_link["status"]
        or manifest.get("coverage")
        != {
            "maximum": 0.9917048679327658,
            "median": 0.9661019339064675,
            "minimum": 0.9374826340650181,
            "minimum_required_median": 0.95,
            "minimum_required_per_partition": 0.85,
            "source_coverage_gate_passed": True,
        }
        or [item.get("report_date") for item in files] != expected_dates
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience full-source manifest identity mismatch"
        )
    listing_lines: list[str] = []
    total_rows = 0
    for item in files:
        frame_path = resolve_record_path(str(item.get("path") or ""))
        if not frame_path.exists():
            raise RichDataError(
                f"Eastmoney balance-sheet-resilience partition is missing: {frame_path}"
            )
        listing_lines.append(f"{item['report_date']}\t{file_digest(frame_path)}\n")
        frame = pd.read_parquet(frame_path)
        assets = pd.to_numeric(frame["total_assets"], errors="coerce")
        liabilities = pd.to_numeric(frame["total_liabilities"], errors="coerce")
        factor = pd.to_numeric(
            frame["eastmoney_balance_sheet_resilience"], errors="coerce"
        )
        if (
            tuple(frame.columns) != EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS
            or len(frame) != int(item.get("rows") or -1)
            or frame_digest(frame) != item.get("sha256")
            or frame.duplicated(["instrument", "report_date"]).any()
            or not pd.to_datetime(frame["report_date"], errors="coerce")
            .dt.normalize()
            .eq(pd.Timestamp(item["report_date"]))
            .all()
            or pd.to_datetime(frame["announcement_date"], errors="coerce").isna().any()
            or not np.isfinite(assets).all()
            or not assets.gt(0.0).all()
            or not np.isfinite(liabilities).all()
            or not liabilities.ge(0.0).all()
            or not liabilities.le(assets).all()
            or not np.isfinite(factor).all()
            or not np.allclose(
                factor.to_numpy(dtype="float64"),
                1.0
                - liabilities.to_numpy(dtype="float64")
                / assets.to_numpy(dtype="float64"),
                rtol=0.0,
                atol=1e-12,
            )
            or not frame["provider"].eq("eastmoney").all()
        ):
            raise RichDataError(
                "Eastmoney balance-sheet-resilience full partition integrity failed: "
                f"{item['report_date']}"
            )
        total_rows += len(frame)
    listing_digest = hashlib.sha256("".join(listing_lines).encode("utf-8")).hexdigest()
    if (
        total_rows != snapshot["total_rows"]
        or listing_digest != snapshot["canonical_partition_file_sha256_listing_sha256"]
    ):
        raise RichDataError(
            "Eastmoney balance-sheet-resilience full snapshot aggregate changed"
        )
    return record


def eastmoney_balance_sheet_resilience_full_records() -> list[Path]:
    """Return prior local success or failure manifests for the full source."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*eastmoney_balance_sheet_resilience*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "eastmoney_balance_sheet_resilience":
            records.append(path)
    return records


def sync_eastmoney_balance_sheet_resilience(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
) -> Path:
    """Store the sole frozen 2019-2025 quarterly public balance-sheet snapshot."""

    if not allow_large:
        raise RichDataError(
            "pass --allow-large only after reviewing the accepted source and frozen 27-partition full-source protocol"
        )
    if DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_FULL_SOURCE_RECORD.exists():
        load_eastmoney_balance_sheet_resilience_full_source_record()
        raise RichDataError(
            "Eastmoney balance-sheet-resilience full snapshot is permanently consumed; "
            "another provider request is forbidden"
        )
    prior_records = eastmoney_balance_sheet_resilience_full_records()
    if prior_records:
        raise RichDataError(
            "Eastmoney balance-sheet-resilience full snapshot is one-shot and already "
            f"consumed by {prior_records[-1]}"
        )
    with RichDataProcessLock(
        METADATA_ROOT / ".eastmoney_balance_sheet_resilience.lock"
    ):
        if DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_FULL_SOURCE_RECORD.exists():
            load_eastmoney_balance_sheet_resilience_full_source_record()
            raise RichDataError(
                "Eastmoney balance-sheet-resilience full snapshot is permanently consumed; "
                "another provider request is forbidden"
            )
        prior_records = eastmoney_balance_sheet_resilience_full_records()
        if prior_records:
            raise RichDataError(
                "Eastmoney balance-sheet-resilience full snapshot is one-shot and already "
                f"consumed by {prior_records[-1]}"
            )
        chain = load_eastmoney_balance_sheet_resilience_source_chain()
        spec = chain["spec"]
        contract = chain["contract"]
        full = spec["full_source_snapshot_contract"]
        report_dates = [dt.date.fromisoformat(value) for value in full["report_dates"]]
        reused_date = dt.date.fromisoformat(
            full["accepted_partition_reused_without_network"]
        )
        intervals = load_factor_universe_intervals(universe_path)
        resolved_universe = universe_path.expanduser().resolve()
        run_id = new_run_id("eastmoney_balance_sheet_resilience")
        parent = RAW_ROOT / "eastmoney" / "balance_sheet_resilience" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Eastmoney balance-sheet-resilience snapshot already exists: {run_id}"
            )
        temporary_root.mkdir(parents=True)
        files: list[dict[str, Any]] = []
        partition_quality: list[dict[str, Any]] = []
        completed_network_partitions = 0
        provider_calls = 0
        current_report_date: dt.date | None = None
        retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
        accepted_schema = spec["source_chain"]["accepted_ordered_source_schema"]
        try:
            for index, report_date in enumerate(report_dates, start=1):
                current_report_date = report_date
                if report_date == reused_date:
                    normalized = chain["accepted_frame"].copy()
                    quality: dict[str, Any] = {
                        "input_rows": int(len(normalized)),
                        "rows_written": int(len(normalized)),
                        "accepted_formula_max_absolute_error": float(
                            chain["acceptance_record"]["observed_result"][
                                "accepted_formula_max_absolute_error"
                            ]
                        ),
                    }
                    request_quality = {
                        "provider_calls": 0,
                        "advertised_pages": 0,
                        "advertised_rows": int(len(normalized)),
                        "received_rows": int(len(normalized)),
                        "ordered_source_column_count": int(
                            accepted_schema["ordered_source_column_count"]
                        ),
                        "ordered_source_columns_sha256": accepted_schema[
                            "ordered_source_columns_sha256"
                        ],
                    }
                    source_mode = "reused_immutable_acceptance_partition"
                else:
                    raw_rows, request_quality = fetch_eastmoney_balance_sheet_partition(
                        report_date, contract=contract
                    )
                    if (
                        request_quality["ordered_source_column_count"]
                        != accepted_schema["ordered_source_column_count"]
                        or request_quality["ordered_source_columns_sha256"]
                        != accepted_schema["ordered_source_columns_sha256"]
                    ):
                        raise RichDataError(
                            "Eastmoney balance-sheet historical positional schema changed "
                            f"for {report_date.isoformat()}"
                        )
                    normalized, quality = (
                        canonicalize_eastmoney_balance_sheet_resilience(
                            raw_rows, report_date, contract=contract
                        )
                    )
                    completed_network_partitions += 1
                    provider_calls += int(request_quality["provider_calls"])
                    source_mode = "new_count_complete_public_partition"

                session = pd.Timestamp(report_date)
                active_rows = intervals[
                    intervals["start_date"].le(session)
                    & intervals["end_date"].ge(session)
                ]
                active_instruments = set(active_rows["instrument"].astype(str))
                if not active_instruments:
                    raise RichDataError(
                        "buyable holding universe has no active names for "
                        f"{report_date.isoformat()}"
                    )
                in_universe = normalized["instrument"].isin(active_instruments)
                outside_universe = int((~in_universe).sum())
                partition = normalized.loc[in_universe].reset_index(drop=True)
                expected_names = int(len(active_instruments))
                observed_names = int(partition["instrument"].nunique())
                coverage = observed_names / expected_names
                minimum_coverage = float(
                    full["minimum_valid_active_holding_coverage_per_report_date"]
                )
                if coverage < minimum_coverage:
                    raise RichDataError(
                        "Eastmoney balance-sheet historical coverage failed for "
                        f"{report_date.isoformat()}: {coverage:.6f} < {minimum_coverage:.6f}"
                    )
                distinct_values = int(
                    partition["eastmoney_balance_sheet_resilience"].nunique(dropna=True)
                )
                minimum_values = int(
                    full["minimum_distinct_factor_values_per_nonempty_partition"]
                )
                if distinct_values < minimum_values:
                    raise RichDataError(
                        "Eastmoney balance-sheet historical factor variation failed for "
                        f"{report_date.isoformat()}: {distinct_values} < {minimum_values}"
                    )
                if (
                    tuple(partition.columns)
                    != EASTMONEY_BALANCE_SHEET_RESILIENCE_COLUMNS
                    or partition.duplicated(["instrument", "report_date"]).any()
                ):
                    raise RichDataError(
                        "Eastmoney balance-sheet historical partition violates the frozen schema"
                    )
                filename = f"{report_date.isoformat()}.parquet"
                temporary_destination = temporary_root / filename
                final_destination = run_root / filename
                atomic_write_frame(partition, temporary_destination)
                files.append(
                    {
                        "path": manifest_path(final_destination),
                        "report_date": report_date.isoformat(),
                        "rows": int(len(partition)),
                        "sha256": frame_digest(partition),
                        "source_mode": source_mode,
                    }
                )
                partition_quality.append(
                    {
                        "report_date": report_date.isoformat(),
                        "source_mode": source_mode,
                        "expected_active_holding_names": expected_names,
                        "valid_holding_names": observed_names,
                        "valid_holding_coverage": coverage,
                        "distinct_factor_values": distinct_values,
                        "outside_point_in_time_holding_universe_rows_excluded": (
                            outside_universe
                        ),
                        "normalization": quality,
                        "request": request_quality,
                    }
                )
                print(
                    "Eastmoney balance-sheet full source "
                    f"{index}/{len(report_dates)}: {report_date.isoformat()} "
                    f"rows={len(partition)} coverage={coverage:.6f}"
                )

            coverages = [
                float(item["valid_holding_coverage"]) for item in partition_quality
            ]
            median_coverage = float(np.median(coverages))
            if median_coverage < float(
                full["minimum_median_valid_active_holding_coverage"]
            ):
                raise RichDataError(
                    "Eastmoney balance-sheet median historical coverage failed: "
                    f"{median_coverage:.6f}"
                )
            if (
                len(files) != int(full["required_report_date_count"])
                or completed_network_partitions != int(full["new_network_partitions"])
                or provider_calls > int(full["maximum_new_provider_calls"])
            ):
                raise RichDataError(
                    "Eastmoney balance-sheet full-source partition or call count changed"
                )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "eastmoney_balance_sheet_resilience",
                "provider": "eastmoney",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "requested_start_report_date": report_dates[0].isoformat(),
                "requested_end_report_date": report_dates[-1].isoformat(),
                "source_chain": {
                    "data_contract": {
                        "path": manifest_path(
                            DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT
                        ),
                        "sha256": EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT_SHA256,
                    },
                    "acceptance_record": {
                        "path": manifest_path(
                            DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_ACCEPTANCE_RECORD
                        ),
                        "sha256": EASTMONEY_BALANCE_SHEET_RESILIENCE_ACCEPTANCE_RECORD_SHA256,
                    },
                    "no_return_preregistration": {
                        "path": manifest_path(
                            DEFAULT_EASTMONEY_BALANCE_SHEET_RESILIENCE_NO_RETURN_SPEC
                        ),
                        "sha256": EASTMONEY_BALANCE_SHEET_RESILIENCE_NO_RETURN_SPEC_SHA256,
                    },
                },
                "point_in_time_holding_universe": {
                    "path": manifest_path(resolved_universe),
                    "sha256": file_digest(resolved_universe),
                },
                "source_request": {
                    "new_network_partitions": completed_network_partitions,
                    "accepted_partitions_reused_without_network": 1,
                    "new_provider_calls": provider_calls,
                    "maximum_allowed_new_provider_calls": int(
                        full["maximum_new_provider_calls"]
                    ),
                    "ordered_source_column_count": int(
                        accepted_schema["ordered_source_column_count"]
                    ),
                    "ordered_source_columns_sha256": accepted_schema[
                        "ordered_source_columns_sha256"
                    ],
                    "credentials_required_logged_or_stored": False,
                    "cookies_proxy_or_retail_session_used": False,
                    "unused_transported_fields_persisted": False,
                },
                "files": files,
                "partition_quality": partition_quality,
                "coverage": {
                    "minimum": float(min(coverages)),
                    "median": median_coverage,
                    "maximum": float(max(coverages)),
                    "minimum_required_per_partition": float(
                        full["minimum_valid_active_holding_coverage_per_report_date"]
                    ),
                    "minimum_required_median": float(
                        full["minimum_median_valid_active_holding_coverage"]
                    ),
                    "source_coverage_gate_passed": True,
                },
                "status": "full_source_coverage_passed_pending_no_return_capacity_and_uniqueness",
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "eastmoney_balance_sheet_resilience",
                "provider": "eastmoney",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "current_report_date": (
                    current_report_date.isoformat() if current_report_date else None
                ),
                "completed_network_partitions": completed_network_partitions,
                "new_provider_calls": provider_calls,
                "data_contract_sha256": (
                    EASTMONEY_BALANCE_SHEET_RESILIENCE_CONTRACT_SHA256
                ),
                "no_return_preregistration_sha256": (
                    EASTMONEY_BALANCE_SHEET_RESILIENCE_NO_RETURN_SPEC_SHA256
                ),
                "files": [],
                "partial_snapshot_deleted": True,
                "status": "terminal_full_source_rejected_stop_before_capacity_uniqueness_prices_or_returns",
                "error_type": type(exc).__name__,
                "error": safe_exception_text(exc),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            failure_path = RUNS_ROOT / f"{run_id}.json"
            atomic_write_json(failure, failure_path)
            raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def load_eastmoney_core_profit_consistency_full_source_record(
    path: Path = DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_FULL_SOURCE_RECORD,
) -> dict[str, Any]:
    """Verify the cross-clone record for the consumed public income source."""

    path = path.expanduser().resolve()
    if (
        file_digest(path)
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_FULL_SOURCE_RECORD_SHA256
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency full-source-record fingerprint mismatch"
        )
    record = load_json_record(
        path,
        kind="a_share_eastmoney_core_profit_consistency_full_source_record",
    )
    contract = record.get("data_contract") or {}
    acceptance = record.get("source_acceptance_record") or {}
    spec = record.get("no_return_preregistration") or {}
    manifest_link = record.get("full_source_manifest") or {}
    snapshot = record.get("published_snapshot") or {}
    request = record.get("source_request") or {}
    coverage = record.get("coverage") or {}
    identity_coverage = coverage.get("complete_identity") or {}
    factor_coverage = coverage.get("valid_factor") or {}
    if (
        record.get("version") != 1
        or record.get("status")
        != "accepted_full_source_pending_no_return_capacity_and_uniqueness"
        or record.get("created_at") != "2026-07-16T23:59:33Z"
        or contract.get("sha256")
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT_SHA256
        or acceptance.get("sha256")
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_ACCEPTANCE_RECORD_SHA256
        or spec.get("sha256")
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_NO_RETURN_SPEC_SHA256
        or manifest_link.get("path")
        != "data/metadata/rich_data/runs/20260716T235617Z_eastmoney_core_profit_consistency_760a3a16.json"
        or manifest_link.get("sha256")
        != "8e3519727eec27163140c3265bcc37de05c61fe4e17aa1ca8cac7ba7fab81b11"
        or manifest_link.get("run_id")
        != "20260716T235617Z_eastmoney_core_profit_consistency_760a3a16"
        or manifest_link.get("status")
        != "full_source_coverage_passed_pending_no_return_capacity_and_uniqueness"
        or snapshot.get("partition_count") != 28
        or snapshot.get("total_rows") != 92764
        or snapshot.get("minimum_partition_rows") != 2444
        or snapshot.get("maximum_partition_rows") != 3573
        or tuple(snapshot.get("columns") or ())
        != EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS
        or snapshot.get("independent_formula_max_absolute_error") != 0.0
        or snapshot.get("canonical_partition_file_sha256_listing_sha256")
        != "ae6cdebb0d8c4e693762e919ac105e4fef306190ed33b164261146937ec01a15"
        or request.get("new_network_partitions") != 27
        or request.get("accepted_partitions_reused_without_network") != 1
        or request.get("new_provider_calls") != 283
        or request.get("ordered_source_column_count") != 46
        or request.get("ordered_source_columns_sha256")
        != "81e5eff36c353c65bbb7728780a4e9663fbbad7b779e44c74921ce57d1f6656f"
        or request.get("every_new_partition_count_complete") is not True
        or request.get("every_historical_partition_matched_accepted_ordered_schema")
        is not True
        or request.get("tushare_token_read") is not False
        or identity_coverage.get("minimum") != 0.9408168935815504
        or identity_coverage.get("median") != 0.9695685118854752
        or identity_coverage.get("maximum") != 0.9989056686364631
        or factor_coverage.get("minimum") != 0.658050619278406
        or factor_coverage.get("median") != 0.7827672462837132
        or factor_coverage.get("maximum") != 0.8477032670105625
        or coverage.get("all_28_partitions_present") is not True
        or coverage.get("source_coverage_gate_passed") is not True
        or record.get("price_fields_loaded") != []
        or record.get("open_close_or_forward_return_fields_read") is not False
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency full-source record is incompatible"
        )

    manifest_file = resolve_record_path(str(manifest_link["path"]))
    if (
        not manifest_file.exists()
        or file_digest(manifest_file) != manifest_link["sha256"]
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency full-source manifest changed"
        )
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    files = sorted(
        list(manifest.get("files") or []), key=lambda item: item.get("report_date", "")
    )
    expected_dates = [
        f"{year}-{month_day}"
        for year in range(2019, 2026)
        for month_day in ("03-31", "06-30", "09-30", "12-31")
    ]
    if (
        manifest.get("dataset") != "eastmoney_core_profit_consistency"
        or manifest.get("provider") != "eastmoney"
        or manifest.get("run_id") != manifest_link["run_id"]
        or manifest.get("status") != manifest_link["status"]
        or manifest.get("coverage")
        != {
            "complete_identity": {
                "maximum": 0.9989056686364631,
                "median": 0.9695685118854752,
                "minimum": 0.9408168935815504,
                "minimum_required_median": 0.95,
                "minimum_required_per_partition": 0.85,
            },
            "source_coverage_gate_passed": True,
            "valid_factor": {
                "maximum": 0.8477032670105625,
                "median": 0.7827672462837132,
                "minimum": 0.658050619278406,
                "minimum_required_median": 0.6,
                "minimum_required_per_partition": 0.45,
            },
        }
        or [item.get("report_date") for item in files] != expected_dates
        or manifest.get("source_request", {}).get("tushare_token_read") is not False
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency full-source manifest identity mismatch"
        )

    partition_quality = list(manifest.get("partition_quality") or [])
    network_quality = [
        item
        for item in partition_quality
        if item.get("source_mode") == "new_count_complete_public_partition"
    ]
    if (
        len(partition_quality) != 28
        or len(network_quality) != 27
        or any(
            item.get("request", {}).get("advertised_rows")
            != item.get("request", {}).get("received_rows")
            or item.get("request", {}).get("ordered_source_column_count") != 46
            or item.get("request", {}).get("ordered_source_columns_sha256")
            != "81e5eff36c353c65bbb7728780a4e9663fbbad7b779e44c74921ce57d1f6656f"
            for item in network_quality
        )
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency historical source completeness changed"
        )

    listing_lines: list[str] = []
    total_rows = 0
    for item in files:
        frame_path = resolve_record_path(str(item.get("path") or ""))
        if not frame_path.exists():
            raise RichDataError(
                f"Eastmoney core-profit-consistency partition is missing: {frame_path}"
            )
        listing_lines.append(f"{item['report_date']}\t{file_digest(frame_path)}\n")
        frame = pd.read_parquet(frame_path)
        operating_profit = pd.to_numeric(frame["operating_profit"], errors="coerce")
        total_profit = pd.to_numeric(frame["total_profit"], errors="coerce")
        factor = pd.to_numeric(
            frame["eastmoney_core_profit_consistency"], errors="coerce"
        )
        expected = np.minimum(
            operating_profit.to_numpy(dtype="float64"),
            total_profit.to_numpy(dtype="float64"),
        ) / np.maximum(
            operating_profit.to_numpy(dtype="float64"),
            total_profit.to_numpy(dtype="float64"),
        )
        if (
            tuple(frame.columns) != EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS
            or len(frame) != int(item.get("rows") or -1)
            or frame_digest(frame) != item.get("sha256")
            or frame.duplicated(["instrument", "report_date"]).any()
            or not pd.to_datetime(frame["report_date"], errors="coerce")
            .dt.normalize()
            .eq(pd.Timestamp(item["report_date"]))
            .all()
            or pd.to_datetime(frame["announcement_date"], errors="coerce").isna().any()
            or not np.isfinite(operating_profit).all()
            or not operating_profit.gt(0.0).all()
            or not np.isfinite(total_profit).all()
            or not total_profit.gt(0.0).all()
            or not np.isfinite(factor).all()
            or not factor.between(0.0, 1.0, inclusive="both").all()
            or not np.allclose(
                factor.to_numpy(dtype="float64"),
                expected,
                rtol=0.0,
                atol=1e-12,
            )
            or not frame["provider"].eq("eastmoney").all()
        ):
            raise RichDataError(
                "Eastmoney core-profit-consistency full partition integrity failed: "
                f"{item['report_date']}"
            )
        total_rows += len(frame)
    listing_digest = hashlib.sha256("".join(listing_lines).encode("utf-8")).hexdigest()
    if (
        total_rows != snapshot["total_rows"]
        or listing_digest != snapshot["canonical_partition_file_sha256_listing_sha256"]
    ):
        raise RichDataError(
            "Eastmoney core-profit-consistency full snapshot aggregate changed"
        )
    return record


def eastmoney_core_profit_consistency_full_records() -> list[Path]:
    """Return prior local success or failure manifests for the full source."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*eastmoney_core_profit_consistency*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "eastmoney_core_profit_consistency":
            records.append(path)
    return records


def sync_eastmoney_core_profit_consistency(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
) -> Path:
    """Store the sole frozen 2019-2025 quarterly public income snapshot."""

    if not allow_large:
        raise RichDataError(
            "pass --allow-large only after reviewing the accepted source and frozen "
            "27-partition core-profit protocol"
        )
    if DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_FULL_SOURCE_RECORD.exists():
        load_eastmoney_core_profit_consistency_full_source_record()
        raise RichDataError(
            "Eastmoney core-profit-consistency full snapshot is permanently consumed; "
            "another provider request is forbidden"
        )
    prior_records = eastmoney_core_profit_consistency_full_records()
    if prior_records:
        raise RichDataError(
            "Eastmoney core-profit-consistency full snapshot is one-shot and already "
            f"consumed by {prior_records[-1]}"
        )
    with RichDataProcessLock(
        METADATA_ROOT / ".eastmoney_core_profit_consistency.lock"
    ):
        if DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_FULL_SOURCE_RECORD.exists():
            load_eastmoney_core_profit_consistency_full_source_record()
            raise RichDataError(
                "Eastmoney core-profit-consistency full snapshot is permanently "
                "consumed; another provider request is forbidden"
            )
        prior_records = eastmoney_core_profit_consistency_full_records()
        if prior_records:
            raise RichDataError(
                "Eastmoney core-profit-consistency full snapshot is one-shot and "
                f"already consumed by {prior_records[-1]}"
            )
        chain = load_eastmoney_core_profit_consistency_source_chain()
        spec = chain["spec"]
        contract = chain["contract"]
        full = spec["full_source_snapshot_contract"]
        report_dates = [dt.date.fromisoformat(value) for value in full["report_dates"]]
        reused_date = dt.date.fromisoformat(
            full["accepted_partition_reused_without_network"]
        )
        intervals = load_factor_universe_intervals(universe_path)
        resolved_universe = universe_path.expanduser().resolve()
        run_id = new_run_id("eastmoney_core_profit_consistency")
        parent = RAW_ROOT / "eastmoney" / "core_profit_consistency" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Eastmoney core-profit-consistency snapshot already exists: {run_id}"
            )
        temporary_root.mkdir(parents=True)
        files: list[dict[str, Any]] = []
        partition_quality: list[dict[str, Any]] = []
        completed_network_partitions = 0
        provider_calls = 0
        current_report_date: dt.date | None = None
        retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
        accepted_schema = spec["source_chain"]["accepted_ordered_source_schema"]
        try:
            for index, report_date in enumerate(report_dates, start=1):
                current_report_date = report_date
                if report_date == reused_date:
                    normalized = chain["accepted_frame"].copy()
                    complete_identity_names = int(
                        chain["acceptance_record"]["observed_result"][
                            "complete_identity_holding_names"
                        ]
                    )
                    quality: dict[str, Any] = {
                        "input_rows": 5218,
                        "rows_written": int(len(normalized)),
                        "accepted_formula_max_absolute_error": float(
                            chain["acceptance_record"]["observed_result"][
                                "accepted_formula_max_absolute_error"
                            ]
                        ),
                    }
                    request_quality = {
                        "provider_calls": 0,
                        "advertised_pages": 0,
                        "advertised_rows": int(len(normalized)),
                        "received_rows": int(len(normalized)),
                        "ordered_source_column_count": int(
                            accepted_schema["ordered_source_column_count"]
                        ),
                        "ordered_source_columns_sha256": accepted_schema[
                            "ordered_source_columns_sha256"
                        ],
                    }
                    source_mode = "reused_immutable_acceptance_partition"
                else:
                    raw_rows, request_quality = (
                        fetch_eastmoney_core_profit_consistency_partition(
                            report_date, contract=contract
                        )
                    )
                    if (
                        request_quality["ordered_source_column_count"]
                        != accepted_schema["ordered_source_column_count"]
                        or request_quality["ordered_source_columns_sha256"]
                        != accepted_schema["ordered_source_columns_sha256"]
                    ):
                        raise RichDataError(
                            "Eastmoney core-profit historical positional schema "
                            f"changed for {report_date.isoformat()}"
                        )
                    normalized, quality = (
                        canonicalize_eastmoney_core_profit_consistency(
                            raw_rows, report_date, contract=contract
                        )
                    )
                    complete_identity_instruments = set(
                        quality.pop(
                            "complete_identity_instruments_for_acceptance_only"
                        )
                    )
                    completed_network_partitions += 1
                    provider_calls += int(request_quality["provider_calls"])
                    source_mode = "new_count_complete_public_partition"

                session = pd.Timestamp(report_date)
                active_rows = intervals[
                    intervals["start_date"].le(session)
                    & intervals["end_date"].ge(session)
                ]
                active_instruments = set(active_rows["instrument"].astype(str))
                if not active_instruments:
                    raise RichDataError(
                        "buyable holding universe has no active names for "
                        f"{report_date.isoformat()}"
                    )
                if report_date != reused_date:
                    complete_identity_names = int(
                        len(complete_identity_instruments & active_instruments)
                    )
                expected_names = int(len(active_instruments))
                complete_identity_coverage = complete_identity_names / expected_names
                in_universe = normalized["instrument"].isin(active_instruments)
                outside_universe = int((~in_universe).sum())
                partition = normalized.loc[in_universe].reset_index(drop=True)
                valid_factor_names = int(partition["instrument"].nunique())
                valid_factor_coverage = valid_factor_names / expected_names
                if complete_identity_coverage < float(
                    full[
                        "minimum_complete_identity_active_holding_coverage_per_report_date"
                    ]
                ):
                    raise RichDataError(
                        "Eastmoney core-profit complete-identity coverage failed for "
                        f"{report_date.isoformat()}: {complete_identity_coverage:.6f}"
                    )
                if valid_factor_coverage < float(
                    full[
                        "minimum_valid_factor_active_holding_coverage_per_report_date"
                    ]
                ):
                    raise RichDataError(
                        "Eastmoney core-profit valid-factor coverage failed for "
                        f"{report_date.isoformat()}: {valid_factor_coverage:.6f}"
                    )
                distinct_values = int(
                    partition["eastmoney_core_profit_consistency"].nunique(
                        dropna=True
                    )
                )
                if distinct_values < int(
                    full["minimum_distinct_factor_values_per_nonempty_partition"]
                ):
                    raise RichDataError(
                        "Eastmoney core-profit historical variation failed for "
                        f"{report_date.isoformat()}: {distinct_values}"
                    )
                if (
                    tuple(partition.columns)
                    != EASTMONEY_CORE_PROFIT_CONSISTENCY_COLUMNS
                    or partition.duplicated(["instrument", "report_date"]).any()
                ):
                    raise RichDataError(
                        "Eastmoney core-profit historical partition violates the "
                        "frozen schema"
                    )
                filename = f"{report_date.isoformat()}.parquet"
                temporary_destination = temporary_root / filename
                final_destination = run_root / filename
                atomic_write_frame(partition, temporary_destination)
                files.append(
                    {
                        "path": manifest_path(final_destination),
                        "report_date": report_date.isoformat(),
                        "rows": int(len(partition)),
                        "sha256": frame_digest(partition),
                        "source_mode": source_mode,
                    }
                )
                partition_quality.append(
                    {
                        "report_date": report_date.isoformat(),
                        "source_mode": source_mode,
                        "expected_active_holding_names": expected_names,
                        "complete_identity_holding_names": complete_identity_names,
                        "complete_identity_holding_coverage": (
                            complete_identity_coverage
                        ),
                        "valid_factor_holding_names": valid_factor_names,
                        "valid_factor_holding_coverage": valid_factor_coverage,
                        "distinct_factor_values": distinct_values,
                        "outside_point_in_time_holding_universe_rows_excluded": (
                            outside_universe
                        ),
                        "normalization": quality,
                        "request": request_quality,
                    }
                )
                print(
                    "Eastmoney core-profit full source "
                    f"{index}/{len(report_dates)}: {report_date.isoformat()} "
                    f"rows={len(partition)} identity={complete_identity_coverage:.6f} "
                    f"factor={valid_factor_coverage:.6f}"
                )

            identity_coverages = [
                float(item["complete_identity_holding_coverage"])
                for item in partition_quality
            ]
            factor_coverages = [
                float(item["valid_factor_holding_coverage"])
                for item in partition_quality
            ]
            median_identity = float(np.median(identity_coverages))
            median_factor = float(np.median(factor_coverages))
            if median_identity < float(
                full["minimum_median_complete_identity_active_holding_coverage"]
            ):
                raise RichDataError(
                    "Eastmoney core-profit median complete-identity coverage failed: "
                    f"{median_identity:.6f}"
                )
            if median_factor < float(
                full["minimum_median_valid_factor_active_holding_coverage"]
            ):
                raise RichDataError(
                    "Eastmoney core-profit median valid-factor coverage failed: "
                    f"{median_factor:.6f}"
                )
            if (
                len(files) != int(full["required_report_date_count"])
                or completed_network_partitions
                != int(full["new_network_partitions"])
                or provider_calls > int(full["maximum_new_provider_calls"])
            ):
                raise RichDataError(
                    "Eastmoney core-profit full-source partition or call count changed"
                )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "eastmoney_core_profit_consistency",
                "provider": "eastmoney",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "requested_start_report_date": report_dates[0].isoformat(),
                "requested_end_report_date": report_dates[-1].isoformat(),
                "source_chain": {
                    "data_contract": {
                        "path": manifest_path(
                            DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT
                        ),
                        "sha256": EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT_SHA256,
                    },
                    "acceptance_record": {
                        "path": manifest_path(
                            DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_ACCEPTANCE_RECORD
                        ),
                        "sha256": (
                            EASTMONEY_CORE_PROFIT_CONSISTENCY_ACCEPTANCE_RECORD_SHA256
                        ),
                    },
                    "no_return_preregistration": {
                        "path": manifest_path(
                            DEFAULT_EASTMONEY_CORE_PROFIT_CONSISTENCY_NO_RETURN_SPEC
                        ),
                        "sha256": (
                            EASTMONEY_CORE_PROFIT_CONSISTENCY_NO_RETURN_SPEC_SHA256
                        ),
                    },
                },
                "point_in_time_holding_universe": {
                    "path": manifest_path(resolved_universe),
                    "sha256": file_digest(resolved_universe),
                },
                "source_request": {
                    "new_network_partitions": completed_network_partitions,
                    "accepted_partitions_reused_without_network": 1,
                    "new_provider_calls": provider_calls,
                    "maximum_allowed_new_provider_calls": int(
                        full["maximum_new_provider_calls"]
                    ),
                    "ordered_source_column_count": int(
                        accepted_schema["ordered_source_column_count"]
                    ),
                    "ordered_source_columns_sha256": accepted_schema[
                        "ordered_source_columns_sha256"
                    ],
                    "credentials_required_logged_or_stored": False,
                    "tushare_token_read": False,
                    "cookies_proxy_or_retail_session_used": False,
                    "unused_transported_fields_persisted": False,
                },
                "files": files,
                "partition_quality": partition_quality,
                "coverage": {
                    "complete_identity": {
                        "minimum": float(min(identity_coverages)),
                        "median": median_identity,
                        "maximum": float(max(identity_coverages)),
                        "minimum_required_per_partition": float(
                            full[
                                "minimum_complete_identity_active_holding_coverage_per_report_date"
                            ]
                        ),
                        "minimum_required_median": float(
                            full[
                                "minimum_median_complete_identity_active_holding_coverage"
                            ]
                        ),
                    },
                    "valid_factor": {
                        "minimum": float(min(factor_coverages)),
                        "median": median_factor,
                        "maximum": float(max(factor_coverages)),
                        "minimum_required_per_partition": float(
                            full[
                                "minimum_valid_factor_active_holding_coverage_per_report_date"
                            ]
                        ),
                        "minimum_required_median": float(
                            full[
                                "minimum_median_valid_factor_active_holding_coverage"
                            ]
                        ),
                    },
                    "source_coverage_gate_passed": True,
                },
                "conservative_state_contract": spec[
                    "conservative_state_contract"
                ],
                "status": "full_source_coverage_passed_pending_no_return_capacity_and_uniqueness",
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "eastmoney_core_profit_consistency",
                "provider": "eastmoney",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "current_report_date": (
                    current_report_date.isoformat() if current_report_date else None
                ),
                "completed_network_partitions": completed_network_partitions,
                "new_provider_calls": provider_calls,
                "data_contract_sha256": (
                    EASTMONEY_CORE_PROFIT_CONSISTENCY_CONTRACT_SHA256
                ),
                "no_return_preregistration_sha256": (
                    EASTMONEY_CORE_PROFIT_CONSISTENCY_NO_RETURN_SPEC_SHA256
                ),
                "files": [],
                "partial_snapshot_deleted": True,
                "status": "terminal_full_source_rejected_stop_before_capacity_uniqueness_prices_or_returns",
                "error_type": type(exc).__name__,
                "error": safe_exception_text(exc),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            failure_path = RUNS_ROOT / f"{run_id}.json"
            atomic_write_json(failure, failure_path)
            raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def tushare_free_float_scarcity_acceptance_records() -> list[Path]:
    """Return prior local acceptance or rejection manifests for this mechanism."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_free_float_scarcity_acceptance*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_free_float_scarcity_acceptance":
            records.append(path)
    return records


def sync_tushare_free_float_scarcity_acceptance(
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
) -> Path:
    """Run the sole frozen one-session free-float entitlement and coverage check."""

    if DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_ACCEPTANCE_RECORD.exists():
        load_tushare_free_float_scarcity_acceptance_record()
        raise RichDataError(
            "Tushare free-float-scarcity acceptance is permanently consumed; "
            "another provider request is forbidden"
        )
    with RichDataProcessLock(
        METADATA_ROOT / ".tushare_free_float_scarcity_acceptance.lock"
    ):
        if DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_ACCEPTANCE_RECORD.exists():
            load_tushare_free_float_scarcity_acceptance_record()
            raise RichDataError(
                "Tushare free-float-scarcity acceptance is permanently consumed; "
                "another provider request is forbidden"
            )
        contract = load_tushare_free_float_scarcity_contract()
        prior_records = tushare_free_float_scarcity_acceptance_records()
        if prior_records:
            raise RichDataError(
                "Tushare free-float-scarcity acceptance is one-shot and already "
                f"consumed by {prior_records[-1]}"
            )
        require_provider("tushare")
        acceptance = contract["acceptance_protocol"]
        trade_date = dt.date.fromisoformat(acceptance["fixed_completed_session"])
        run_id = new_run_id("tushare_free_float_scarcity_acceptance")
        run_root = RAW_ROOT / "tushare" / "free_float_scarcity" / "acceptance" / run_id
        temporary_root = run_root.parent / f".{run_id}.tmp"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Tushare free-float-scarcity acceptance already exists: {run_id}"
            )
        retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
        provider_request_issued = False
        try:
            provider_request_issued = True
            raw = fetch_tushare_free_float_scarcity(trade_date)
            minimum_rows = int(acceptance["minimum_all_market_source_rows"])
            if len(raw) < minimum_rows:
                raise RichDataError(
                    "Tushare daily_basic free-float acceptance returned too few "
                    f"all-market rows: {len(raw)} < {minimum_rows}"
                )
            row_ceiling = int(acceptance["provider_documented_maximum_rows_per_call"])
            if len(raw) >= row_ceiling:
                raise RichDataError(
                    "Tushare daily_basic free-float acceptance reached the provider "
                    "row ceiling; the all-market response may be truncated"
                )
            normalized, quality = canonicalize_tushare_free_float_scarcity(
                raw, trade_date, trade_date
            )
            intervals = load_factor_universe_intervals(universe_path)
            session = pd.Timestamp(trade_date)
            active_rows = intervals[
                intervals["start_date"].le(session) & intervals["end_date"].ge(session)
            ]
            active_instruments = set(active_rows["instrument"].astype(str))
            if not active_instruments:
                raise RichDataError(
                    "buyable holding universe has no active free-float acceptance-date names"
                )
            in_universe = normalized["instrument"].isin(active_instruments)
            outside_universe = int((~in_universe).sum())
            accepted = normalized.loc[in_universe].reset_index(drop=True)
            observed_names = int(accepted["instrument"].nunique())
            expected_names = int(len(active_instruments))
            coverage = observed_names / expected_names
            minimum_coverage = float(
                acceptance["minimum_valid_holding_universe_coverage"]
            )
            if coverage < minimum_coverage:
                raise RichDataError(
                    "Tushare daily_basic free-float holding coverage failed: "
                    f"{coverage:.6f} < {minimum_coverage:.6f}"
                )
            minimum_names = int(acceptance["minimum_valid_holding_names"])
            if observed_names < minimum_names:
                raise RichDataError(
                    "Tushare daily_basic free-float acceptance has too few valid "
                    f"holding names: {observed_names} < {minimum_names}"
                )
            distinct_values = int(
                accepted["tushare_free_float_scarcity"].nunique(dropna=True)
            )
            minimum_values = int(acceptance["minimum_distinct_factor_values"])
            if distinct_values < minimum_values:
                raise RichDataError(
                    "Tushare daily_basic free-float acceptance lacks factor variation: "
                    f"{distinct_values} < {minimum_values}"
                )
            if accepted.duplicated(["instrument", "trade_date"]).any():
                raise RichDataError(
                    "Tushare daily_basic free-float accepted frame contains duplicate keys"
                )

            temporary_destination = temporary_root / "free_float_scarcity.parquet"
            final_destination = run_root / "free_float_scarcity.parquet"
            atomic_write_frame(accepted, temporary_destination)
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_free_float_scarcity_acceptance",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "requested_start": trade_date.isoformat(),
                "requested_end": trade_date.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "mechanism_audit": contract["freeze_evidence"][
                    "mechanism_overlap_and_suspend_capacity_audit"
                ],
                "point_in_time_holding_universe": {
                    "path": manifest_path(universe_path.expanduser().resolve()),
                    "sha256": file_digest(universe_path.expanduser().resolve()),
                    "active_names": expected_names,
                },
                "source_request": {
                    "api": "daily_basic",
                    "request_mode": "one fixed completed local trading session",
                    "fields": list(TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS),
                    "provider_request_issued": provider_request_issued,
                    "forbidden_fields_requested_or_stored": [],
                    "credentials_logged_or_stored": False,
                },
                "files": [
                    {
                        "path": manifest_path(final_destination),
                        "rows": int(len(accepted)),
                        "sha256": frame_digest(accepted),
                    }
                ],
                "source_quality": {
                    **quality,
                    "outside_point_in_time_holding_universe_rows_excluded": (
                        outside_universe
                    ),
                    "expected_active_holding_names": expected_names,
                    "valid_free_float_holding_names": observed_names,
                    "valid_free_float_holding_coverage": coverage,
                    "distinct_factor_values": distinct_values,
                    "duplicate_event_key_rows": 0,
                    "scarcity_min": float(
                        accepted["tushare_free_float_scarcity"].min()
                    ),
                    "scarcity_max": float(
                        accepted["tushare_free_float_scarcity"].max()
                    ),
                },
                "acceptance_status": "accepted_entitlement_formula_and_current_coverage_pending_full_history_and_frozen_no_return_protocol",
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_free_float_scarcity_acceptance",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "requested_start": trade_date.isoformat(),
                "requested_end": trade_date.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT),
                },
                "source_request": {
                    "api": "daily_basic",
                    "fields": list(TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS),
                    "provider_request_issued": provider_request_issued,
                    "credentials_logged_or_stored": False,
                },
                "files": [],
                "partial_snapshot_deleted": True,
                "acceptance_status": "terminal_entitlement_schema_formula_or_current_coverage_rejected_stop_before_full_history_capacity_uniqueness_or_returns",
                "error_type": type(exc).__name__,
                "error": safe_exception_text(exc),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            failure_path = RUNS_ROOT / f"{run_id}.json"
            atomic_write_json(failure, failure_path)
            raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def tushare_free_float_scarcity_full_records() -> list[Path]:
    """Return prior local full-snapshot success or failure records."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_free_float_scarcity*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_free_float_scarcity":
            records.append(path)
    return records


def _fetch_tushare_free_float_scarcity_with_policy(
    trade_date: dt.date,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    retry_backoffs: list[float],
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and retry policy to share counts."""

    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_free_float_scarcity(trade_date)
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[attempt])
    raise AssertionError("unreachable Tushare free-float retry state")


def sync_tushare_free_float_scarcity(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the sole frozen 2019-2025 structural-scarcity source snapshot."""

    if DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_FULL_SOURCE_RECORD.exists():
        load_tushare_free_float_scarcity_full_source_record()
        raise RichDataError(
            "Tushare free-float-scarcity full snapshot is permanently consumed; "
            "another provider request is forbidden"
        )
    prior_records = tushare_free_float_scarcity_full_records()
    if prior_records:
        raise RichDataError(
            "Tushare free-float-scarcity full snapshot is one-shot and already "
            f"consumed by {prior_records[-1]}"
        )
    with RichDataProcessLock(METADATA_ROOT / ".tushare_free_float_scarcity.lock"):
        if DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_FULL_SOURCE_RECORD.exists():
            load_tushare_free_float_scarcity_full_source_record()
            raise RichDataError(
                "Tushare free-float-scarcity full snapshot is permanently consumed; "
                "another provider request is forbidden"
            )
        prior_records = tushare_free_float_scarcity_full_records()
        if prior_records:
            raise RichDataError(
                "Tushare free-float-scarcity full snapshot is one-shot and already "
                f"consumed by {prior_records[-1]}"
            )
        source_chain = load_tushare_free_float_scarcity_source_chain()
        contract = source_chain["contract"]
        spec = source_chain["spec"]
        full_contract = spec["full_source_snapshot_contract"]
        require_provider("tushare")
        start = dt.date.fromisoformat(full_contract["requested_start"])
        end = dt.date.fromisoformat(full_contract["requested_end"])
        validate_range(start, end, allow_large=allow_large, unit_count=1)
        all_intervals = load_factor_universe_intervals(universe_path)
        calendar = local_calendar_dates(start, end, calendar_path)
        expected_calls = int(full_contract["expected_provider_calls"])
        if len(calendar) != expected_calls:
            raise RichDataError(
                "Tushare free-float-scarcity local calendar changed: "
                f"{len(calendar)} != {expected_calls}"
            )
        overlap = all_intervals["start_date"].le(pd.Timestamp(end)) & all_intervals[
            "end_date"
        ].ge(pd.Timestamp(start))
        intervals = all_intervals.loc[overlap].copy()
        if intervals.empty:
            raise RichDataError(
                "holding universe has no instruments in the frozen free-float range"
            )

        run_id = new_run_id("tushare_free_float_scarcity")
        parent = RAW_ROOT / "tushare" / "free_float_scarcity" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Tushare free-float-scarcity snapshot already exists: {run_id}"
            )
        temporary_root.mkdir(parents=True)
        files: list[dict[str, Any]] = []
        all_daily_coverage: list[dict[str, Any]] = []
        quality_keys = (
            "input_rows",
            "missing_or_nonfinite_share_rows_excluded",
            "nonpositive_share_rows_excluded",
            "free_share_above_total_share_rows_excluded",
            "outside_point_in_time_holding_universe_rows_excluded",
            "rows_written",
        )
        quality_totals = {key: 0 for key in quality_keys}
        minimum_interval = float(full_contract["minimum_seconds_between_calls"])
        maximum_attempts = int(full_contract["maximum_attempts_per_session"])
        retry_backoffs = [
            float(value) for value in full_contract["retry_backoff_seconds"]
        ]
        last_request_started: list[float | None] = [None]
        completed_calls = 0
        current_session_date: dt.date | None = None
        current_year_quality = {key: 0 for key in quality_keys}
        try:
            for year in range(start.year, end.year + 1):
                partition_start = max(start, dt.date(year, 1, 1))
                partition_end = min(end, dt.date(year, 12, 31))
                partition_calendar = calendar[
                    (calendar >= pd.Timestamp(partition_start))
                    & (calendar <= pd.Timestamp(partition_end))
                ]
                if partition_calendar.empty:
                    continue
                year_frames: list[pd.DataFrame] = []
                current_year_quality = {key: 0 for key in quality_keys}
                for session in partition_calendar:
                    session_date = pd.Timestamp(session).date()
                    current_session_date = session_date
                    raw = _fetch_tushare_free_float_scarcity_with_policy(
                        session_date,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        retry_backoffs=retry_backoffs,
                        last_request_started=last_request_started,
                    )
                    if raw.empty:
                        raise RichDataError(
                            "Tushare free-float-scarcity returned an empty frame for "
                            f"{session_date.isoformat()}"
                        )
                    if len(raw) >= int(
                        full_contract["provider_documented_maximum_rows_per_call"]
                    ):
                        raise RichDataError(
                            "Tushare free-float-scarcity reached the provider row "
                            f"ceiling for {session_date.isoformat()}"
                        )
                    normalized, quality = canonicalize_tushare_free_float_scarcity(
                        raw, session_date, session_date
                    )
                    session_ts = pd.Timestamp(session)
                    active_rows = intervals[
                        intervals["start_date"].le(session_ts)
                        & intervals["end_date"].ge(session_ts)
                    ]
                    active_instruments = set(active_rows["instrument"].astype(str))
                    in_universe = normalized["instrument"].isin(active_instruments)
                    outside_universe = int((~in_universe).sum())
                    normalized = normalized.loc[in_universe].reset_index(drop=True)
                    quality["outside_point_in_time_holding_universe_rows_excluded"] = (
                        outside_universe
                    )
                    quality["rows_written"] = int(len(normalized))
                    for key in quality_keys:
                        current_year_quality[key] += int(quality.get(key, 0))
                    observed_names = int(normalized["instrument"].nunique())
                    expected_names = int(len(active_instruments))
                    all_daily_coverage.append(
                        {
                            "trade_date": session_date.isoformat(),
                            "expected_active_holding_names": expected_names,
                            "valid_free_float_holding_names": observed_names,
                            "coverage": (
                                observed_names / expected_names
                                if expected_names
                                else None
                            ),
                        }
                    )
                    if not normalized.empty:
                        year_frames.append(normalized)
                    completed_calls += 1
                    if completed_calls % 50 == 0 or completed_calls == expected_calls:
                        print(
                            json.dumps(
                                {
                                    "dataset": "tushare_free_float_scarcity",
                                    "progress_calls": completed_calls,
                                    "total_calls": expected_calls,
                                    "latest_session": session_date.isoformat(),
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                if not year_frames:
                    raise RichDataError(
                        f"Tushare free-float-scarcity {year} has no eligible rows"
                    )
                partition_frame = (
                    pd.concat(year_frames, ignore_index=True)
                    .sort_values(["trade_date", "instrument"], kind="stable")
                    .reset_index(drop=True)
                )
                if (
                    tuple(partition_frame.columns)
                    != TUSHARE_FREE_FLOAT_SCARCITY_COLUMNS
                ):
                    raise RichDataError(
                        f"Tushare free-float-scarcity {year} columns changed"
                    )
                if partition_frame.duplicated(["instrument", "trade_date"]).any():
                    raise RichDataError(
                        f"Tushare free-float-scarcity {year} has duplicate keys"
                    )
                destination = temporary_root / f"{year}.parquet"
                atomic_write_frame(partition_frame, destination)
                for key in quality_keys:
                    quality_totals[key] += current_year_quality[key]
                files.append(
                    {
                        "year": year,
                        "requested_start": partition_start.isoformat(),
                        "requested_end": partition_end.isoformat(),
                        "provider_calls": int(len(partition_calendar)),
                        "path": manifest_path(run_root / destination.name),
                        "rows": int(len(partition_frame)),
                        "sha256": frame_digest(partition_frame),
                        "quality": dict(current_year_quality),
                    }
                )
                print(
                    json.dumps(
                        {
                            "dataset": "tushare_free_float_scarcity",
                            "completed_year": year,
                            "rows": int(len(partition_frame)),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            if completed_calls != expected_calls or not files:
                raise RichDataError(
                    "Tushare free-float-scarcity full snapshot omitted a frozen call"
                )
            coverages = pd.Series(
                [
                    row["coverage"]
                    for row in all_daily_coverage
                    if row["coverage"] is not None
                ],
                dtype="float64",
            )
            median_coverage = float(coverages.median()) if len(coverages) else 0.0
            p05_coverage = float(coverages.quantile(0.05)) if len(coverages) else 0.0
            dates_with_minimum_names = int(
                sum(
                    row["valid_free_float_holding_names"] >= 50
                    for row in all_daily_coverage
                )
            )
            observed_years = len({int(item["year"]) for item in files})
            coverage_gate_passed = bool(
                len(coverages) == expected_calls
                and median_coverage
                >= float(
                    full_contract["minimum_median_valid_holding_universe_coverage"]
                )
                and p05_coverage
                >= float(full_contract["minimum_p05_valid_holding_universe_coverage"])
                and dates_with_minimum_names
                >= int(full_contract["minimum_sessions_with_fifty_valid_names"])
                and observed_years
                >= int(full_contract["minimum_observed_source_years"])
            )
            if not coverage_gate_passed:
                raise RichDataError(
                    "Tushare free-float-scarcity full source coverage gate failed"
                )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_free_float_scarcity",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "no_return_preregistration": {
                    "path": manifest_path(source_chain["spec_path"]),
                    "sha256": file_digest(source_chain["spec_path"]),
                    "preregistered_at": spec["preregistered_at"],
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                    "manifest_path": manifest_path(source_chain["manifest_path"]),
                    "manifest_sha256": file_digest(source_chain["manifest_path"]),
                    "run_id": source_chain["manifest"].get("run_id"),
                    "frame_path": manifest_path(source_chain["frame_path"]),
                    "frame_content_sha256": source_chain["manifest"]["files"][0][
                        "sha256"
                    ],
                },
                "point_in_time_holding_universe": {
                    "path": manifest_path(universe_path.expanduser().resolve()),
                    "sha256": file_digest(universe_path.expanduser().resolve()),
                    "intervals": int(len(all_intervals)),
                },
                "local_calendar": {
                    "path": manifest_path(calendar_path.expanduser().resolve()),
                    "sha256": file_digest(calendar_path.expanduser().resolve()),
                    "sessions_in_requested_range": int(len(calendar)),
                },
                "source_request": {
                    "api": "daily_basic",
                    "frequency": "daily_after_close",
                    "request_mode": "one completed local trading session per call",
                    "fields": list(TUSHARE_FREE_FLOAT_SCARCITY_RAW_FIELDS),
                    "forbidden_fields_requested_or_stored": [],
                    "credentials_logged_or_stored": False,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_session": maximum_attempts,
                    "completed_provider_calls": completed_calls,
                },
                "files": files,
                "normalization_quality": quality_totals,
                "coverage": {
                    "calendar_sessions": int(len(calendar)),
                    "observed_source_years": observed_years,
                    "median_valid_free_float_holding_universe_coverage": (
                        median_coverage
                    ),
                    "p05_valid_free_float_holding_universe_coverage": p05_coverage,
                    "sessions_with_at_least_fifty_valid_free_float_names": (
                        dates_with_minimum_names
                    ),
                    "gate_passed_before_comparison_fields_or_prices": True,
                    "daily": all_daily_coverage,
                },
                "factor_policy": {
                    "factor": "tushare_free_float_scarcity",
                    "formula": "1 - free_share / total_share",
                    "direction": "higher_is_better",
                    "earliest_entry": "next local trading session open",
                    "maximum_event_age_calendar_days": 0,
                },
                "acceptance_status": full_contract["required_success_status"],
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            shutil.rmtree(run_root, ignore_errors=True)
            message = safe_exception_text(exc)
            if "empty frame" in message:
                failure_code = "source_empty_session"
            elif "row ceiling" in message:
                failure_code = "provider_row_ceiling_possible_truncation"
            elif "duplicate" in message:
                failure_code = "source_duplicate_key"
            elif "outside the request" in message:
                failure_code = "source_date_outside_request"
            elif "fields outside" in message or "lacks requested fields" in message:
                failure_code = "source_schema_mismatch"
            elif "coverage gate failed" in message:
                failure_code = "full_source_coverage_gate_failed"
            elif "share" in message and "excluded" in message:
                failure_code = "source_share_domain_failure"
            else:
                failure_code = "provider_or_local_snapshot_failure"
            failure_path = RUNS_ROOT / f"{run_id}_source_failure.json"
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_source_failure",
                "dataset": "tushare_free_float_scarcity",
                "provider": "tushare",
                "run_id": run_id,
                "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "failed_session": (
                    current_session_date.isoformat()
                    if current_session_date is not None
                    else None
                ),
                "completed_provider_calls_before_failure": completed_calls,
                "total_planned_provider_calls": expected_calls,
                "failure_code": failure_code,
                "error": message,
                "partial_snapshot_deleted": not temporary_root.exists(),
                "final_snapshot_published": run_root.exists(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_FREE_FLOAT_SCARCITY_CONTRACT),
                },
                "no_return_preregistration": {
                    "path": manifest_path(source_chain["spec_path"]),
                    "sha256": file_digest(source_chain["spec_path"]),
                },
                "credentials_logged_or_stored": False,
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            atomic_write_json(failure, failure_path)
            if isinstance(exc, RichDataError):
                raise RichDataError(
                    f"{message}; rejection_record={failure_path}"
                ) from exc
            raise


def sync_tushare_daily_pb_acceptance(
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
) -> Path:
    """Run the frozen one-session daily PB entitlement and coverage check."""

    require_provider("tushare")
    contract = load_tushare_daily_pb_contract()
    acceptance = contract["acceptance_protocol"]
    trade_date = dt.date.fromisoformat(acceptance["fixed_completed_session"])
    run_id = new_run_id("tushare_daily_pb_acceptance")
    run_root = RAW_ROOT / "tushare" / "daily_pb" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare daily PB acceptance already exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        raw = fetch_tushare_daily_pb(trade_date)
        if len(raw) < int(acceptance["minimum_all_market_source_rows"]):
            raise RichDataError(
                "Tushare daily_basic PB acceptance returned too few all-market rows: "
                f"{len(raw)} < {acceptance['minimum_all_market_source_rows']}"
            )
        row_ceiling = int(
            contract["snapshot_contract"]["partition_policy"][
                "provider_documented_maximum_rows_per_call"
            ]
        )
        if len(raw) >= row_ceiling:
            raise RichDataError(
                "Tushare daily_basic PB acceptance reached the provider row ceiling; "
                "the all-market response may be truncated"
            )
        normalized, quality = canonicalize_tushare_daily_pb(raw, trade_date, trade_date)
        intervals = load_factor_universe_intervals(universe_path)
        session = pd.Timestamp(trade_date)
        active_rows = intervals[
            intervals["start_date"].le(session) & intervals["end_date"].ge(session)
        ]
        active_instruments = set(active_rows["instrument"].astype(str))
        if not active_instruments:
            raise RichDataError(
                "buyable holding universe has no active acceptance-date names"
            )
        in_universe = normalized["instrument"].isin(active_instruments)
        outside_universe = int((~in_universe).sum())
        accepted = normalized.loc[in_universe].reset_index(drop=True)
        observed_names = int(accepted["instrument"].nunique())
        expected_names = int(len(active_instruments))
        coverage = observed_names / expected_names
        minimum_coverage = float(
            acceptance["minimum_positive_pb_holding_universe_coverage"]
        )
        if coverage < minimum_coverage:
            raise RichDataError(
                "Tushare daily_basic PB acceptance positive-PB holding coverage failed: "
                f"{coverage:.6f} < {minimum_coverage:.6f}"
            )
        temporary_destination = temporary_root / "daily_pb.parquet"
        final_destination = run_root / "daily_pb.parquet"
        atomic_write_frame(accepted, temporary_destination)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_daily_pb_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "point_in_time_holding_universe": {
                "path": manifest_path(universe_path.expanduser().resolve()),
                "sha256": file_digest(universe_path.expanduser().resolve()),
                "active_names": expected_names,
            },
            "source_request": {
                "api": "daily_basic",
                "request_mode": "one completed local trading session per call",
                "fields": list(TUSHARE_DAILY_PB_RAW_FIELDS),
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(accepted)),
                    "sha256": frame_digest(accepted),
                }
            ],
            "source_quality": {
                **quality,
                "outside_point_in_time_holding_universe_rows_excluded": outside_universe,
                "expected_active_holding_names": expected_names,
                "positive_pb_holding_names": observed_names,
                "positive_pb_holding_coverage": coverage,
                "duplicate_event_key_rows": int(
                    accepted.duplicated(["instrument", "trade_date"]).sum()
                ),
                "book_to_market_min": float(
                    accepted["tushare_positive_book_to_market"].min()
                ),
                "book_to_market_max": float(
                    accepted["tushare_positive_book_to_market"].max()
                ),
            },
            "acceptance_status": "accepted_entitlement_formula_and_current_coverage_pending_full_history",
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_daily_pb_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
            },
            "source_request": {
                "api": "daily_basic",
                "fields": list(TUSHARE_DAILY_PB_RAW_FIELDS),
                "credentials_logged_or_stored": False,
            },
            "files": [],
            "acceptance_status": "entitlement_schema_or_current_coverage_rejected_stop_before_full_history",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def sync_tushare_sw_industry_breadth_acceptance() -> Path:
    """Run the frozen no-price SW2021 classification and membership probe."""

    require_provider("tushare")
    contract = load_tushare_sw_industry_breadth_contract()
    for link in (contract.get("local_context") or {}).values():
        source_path = resolve_record_path(str(link["path"]))
        if not source_path.exists() or file_digest(source_path) != link["sha256"]:
            raise RichDataError(
                f"Tushare SW industry-breadth local context changed: {link['path']}"
            )
    acceptance = contract["acceptance_protocol"]
    representative_l1 = str(acceptance["representative_l1_code"])
    run_id = new_run_id("tushare_sw2021_l1_acceptance")
    run_root = RAW_ROOT / "tushare" / "sw2021_l1" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare SW2021 L1 acceptance already exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        raw_classification = fetch_tushare_sw_classification()
        classification = canonicalize_tushare_sw_classification(raw_classification)
        minimum_classification = int(acceptance["minimum_classification_rows"])
        maximum_classification = int(acceptance["maximum_classification_rows"])
        if not minimum_classification <= len(classification) <= maximum_classification:
            raise RichDataError(
                "Tushare SW2021 L1 classification row count is outside the frozen range: "
                f"{len(classification)} not in [{minimum_classification}, "
                f"{maximum_classification}]"
            )
        if representative_l1 not in set(classification["index_code"].astype(str)):
            raise RichDataError(
                f"Tushare SW2021 classification lacks representative {representative_l1}"
            )

        provider_ceiling = int(
            contract["source_selection"]["provider_documented_maximum_rows_per_call"]
        )
        member_frames: list[pd.DataFrame] = []
        member_quality: list[dict[str, Any]] = []
        for is_new in contract["source"]["membership_is_new_values"]:
            raw_members = fetch_tushare_sw_members(representative_l1, str(is_new))
            if len(raw_members) >= provider_ceiling:
                raise RichDataError(
                    "Tushare SW membership acceptance reached the provider row ceiling: "
                    f"l1_code={representative_l1} is_new={is_new} rows={len(raw_members)}"
                )
            members, quality = canonicalize_tushare_sw_members(
                raw_members,
                expected_l1_code=representative_l1,
                expected_is_new=str(is_new),
            )
            minimum_key = (
                "minimum_current_representative_members"
                if is_new == "Y"
                else "minimum_historical_representative_members"
            )
            minimum_rows = int(acceptance[minimum_key])
            if len(members) < minimum_rows:
                raise RichDataError(
                    "Tushare SW membership acceptance returned too few rows: "
                    f"is_new={is_new} {len(members)} < {minimum_rows}"
                )
            member_frames.append(members)
            member_quality.append({"is_new": is_new, **quality})
        membership = (
            pd.concat(member_frames, ignore_index=True)
            .sort_values(
                ["l1_code", "l2_code", "l3_code", "instrument", "in_date", "is_new"],
                kind="stable",
            )
            .reset_index(drop=True)
        )
        duplicate_key = list(contract["full_snapshot_contract"]["duplicate_event_key"])
        if membership.duplicated(duplicate_key).any():
            raise RichDataError(
                "Tushare SW membership acceptance contains duplicate canonical intervals"
            )

        temporary_classification = temporary_root / "classification.parquet"
        temporary_membership = temporary_root / "membership.parquet"
        final_classification = run_root / "classification.parquet"
        final_membership = run_root / "membership.parquet"
        atomic_write_frame(classification, temporary_classification)
        atomic_write_frame(membership, temporary_membership)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_sw2021_l1_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "classification_api": "index_classify",
                "classification_parameters": contract["source"][
                    "classification_parameters"
                ],
                "classification_fields": list(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS),
                "membership_api": "index_member_all",
                "representative_l1_code": representative_l1,
                "membership_is_new_values": list(
                    contract["source"]["membership_is_new_values"]
                ),
                "membership_fields": list(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS),
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "dataset": "classification",
                    "path": manifest_path(final_classification),
                    "rows": int(len(classification)),
                    "sha256": frame_digest(classification),
                },
                {
                    "dataset": "membership",
                    "path": manifest_path(final_membership),
                    "rows": int(len(membership)),
                    "sha256": frame_digest(membership),
                },
            ],
            "source_quality": {
                "classification_rows": int(len(classification)),
                "classification_codes": classification["index_code"]
                .astype(str)
                .tolist(),
                "classification_duplicate_codes": int(
                    classification["index_code"].duplicated().sum()
                ),
                "membership_requests": member_quality,
                "membership_rows": int(len(membership)),
                "membership_unique_instruments": int(
                    membership["instrument"].nunique()
                ),
                "membership_duplicate_interval_rows": int(
                    membership.duplicated(duplicate_key).sum()
                ),
                "minimum_in_date": membership["in_date"].min().date().isoformat(),
                "maximum_dated_out_date": membership["out_date"]
                .max()
                .date()
                .isoformat(),
            },
            "acceptance_status": (
                "accepted_entitlement_schema_and_point_in_time_intervals_"
                "pending_full_membership_snapshot"
            ),
            "price_fields_loaded": [],
            "factor_values_constructed": False,
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_sw2021_l1_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
            },
            "source_request": {
                "classification_api": "index_classify",
                "membership_api": "index_member_all",
                "representative_l1_code": representative_l1,
                "classification_fields": list(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS),
                "membership_fields": list(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS),
                "credentials_logged_or_stored": False,
            },
            "files": [],
            "acceptance_status": (
                "entitlement_schema_or_interval_rejected_stop_before_full_membership"
            ),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "price_fields_loaded": [],
            "factor_values_constructed": False,
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def _fetch_tushare_sw_members_with_policy(
    l1_code: str,
    is_new: str,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    retry_backoffs: list[float],
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded retry policy to SW rows."""

    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_sw_members(l1_code, is_new)
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[attempt])
    raise AssertionError("unreachable Tushare SW membership retry state")


def sync_tushare_sw_industry_membership(*, allow_large: bool = False) -> Path:
    """Store the frozen 31-code by two-state SW2021 membership snapshot."""

    if not allow_large:
        raise RichDataError(
            "the frozen SW2021 membership snapshot requires --allow-large after "
            "reviewing the accepted 62-call preregistration"
        )
    with RichDataProcessLock(METADATA_ROOT / ".tushare_sw2021_l1_membership.lock"):
        source_chain = load_tushare_sw_industry_breadth_source_chain()
        require_provider("tushare")
        spec = source_chain["spec"]
        snapshot = spec["full_membership_snapshot"]
        contract = source_chain["contract"]
        classification_codes = [
            str(value) for value in snapshot["classification_codes"]
        ]
        is_new_values = [str(value) for value in snapshot["is_new_values"]]
        total_calls = len(classification_codes) * len(is_new_values)
        if total_calls != int(snapshot["expected_provider_calls"]):
            raise RichDataError("Tushare SW full-snapshot call count changed")

        run_id = new_run_id("tushare_sw2021_l1_membership")
        parent = RAW_ROOT / "tushare" / "sw2021_l1" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Tushare SW membership snapshot already exists: {run_id}"
            )
        temporary_root.mkdir(parents=True)
        minimum_interval = float(snapshot["minimum_seconds_between_calls"])
        maximum_attempts = int(snapshot["maximum_attempts_per_call"])
        retry_backoffs = [float(value) for value in snapshot["retry_backoff_seconds"]]
        if len(retry_backoffs) != maximum_attempts - 1:
            raise RichDataError("Tushare SW retry policy is internally inconsistent")
        provider_ceiling = int(snapshot["provider_documented_maximum_rows_per_call"])
        last_request_started: list[float | None] = [None]
        frames: list[pd.DataFrame] = []
        request_audit: list[dict[str, Any]] = []
        completed_calls = 0
        current_l1_code: str | None = None
        current_is_new: str | None = None
        try:
            for l1_code in classification_codes:
                for is_new in is_new_values:
                    current_l1_code = l1_code
                    current_is_new = is_new
                    raw = _fetch_tushare_sw_members_with_policy(
                        l1_code,
                        is_new,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        retry_backoffs=retry_backoffs,
                        last_request_started=last_request_started,
                    )
                    if len(raw) >= provider_ceiling:
                        raise RichDataError(
                            "Tushare SW membership reached the provider row ceiling; "
                            f"l1_code={l1_code} is_new={is_new} rows={len(raw)}"
                        )
                    normalized, quality = canonicalize_tushare_sw_members(
                        raw,
                        expected_l1_code=l1_code,
                        expected_is_new=is_new,
                    )
                    if not normalized.empty:
                        frames.append(normalized)
                    request_audit.append(
                        {
                            "l1_code": l1_code,
                            "is_new": is_new,
                            **quality,
                        }
                    )
                    completed_calls += 1
                    if completed_calls % 10 == 0 or completed_calls == total_calls:
                        print(
                            json.dumps(
                                {
                                    "dataset": "tushare_sw2021_l1_membership",
                                    "progress_calls": completed_calls,
                                    "total_calls": total_calls,
                                    "latest_l1_code": l1_code,
                                    "latest_is_new": is_new,
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
            if completed_calls != total_calls or len(request_audit) != total_calls:
                raise RichDataError(
                    "Tushare SW membership did not complete every frozen call"
                )
            if not frames:
                raise RichDataError(
                    "Tushare SW full membership snapshot returned no rows"
                )
            membership = (
                pd.concat(frames, ignore_index=True)
                .sort_values(
                    [
                        "l1_code",
                        "l2_code",
                        "l3_code",
                        "instrument",
                        "in_date",
                        "out_date",
                        "is_new",
                    ],
                    kind="stable",
                    na_position="last",
                )
                .reset_index(drop=True)
            )
            duplicate_key = list(
                contract["full_snapshot_contract"]["duplicate_event_key"]
            )
            if (
                tuple(membership.columns) != TUSHARE_SW_MEMBERSHIP_COLUMNS
                or membership.duplicated(duplicate_key).any()
                or not set(membership["l1_code"].astype(str)).issubset(
                    set(classification_codes)
                )
                or not set(membership["is_new"].astype(str)).issubset(
                    set(is_new_values)
                )
                or not membership["provider"].eq("tushare").all()
            ):
                raise RichDataError(
                    "Tushare SW full membership frame failed integrity checks"
                )
            temporary_frame = temporary_root / "membership.parquet"
            final_frame = run_root / "membership.parquet"
            atomic_write_frame(membership, temporary_frame)
            stored = pd.read_parquet(temporary_frame)
            if tuple(stored.columns) != TUSHARE_SW_MEMBERSHIP_COLUMNS or frame_digest(
                stored
            ) != frame_digest(membership):
                raise RichDataError(
                    "Tushare SW stored membership frame failed reread audit"
                )

            current_rows = int(membership["is_new"].eq("Y").sum())
            historical_rows = int(membership["is_new"].eq("N").sum())
            empty_requests = [
                {"l1_code": row["l1_code"], "is_new": row["is_new"]}
                for row in request_audit
                if int(row["rows_written"]) == 0
            ]
            unsupported_symbol_rows = int(
                sum(
                    int(row["unsupported_provider_symbol_rows_excluded"])
                    for row in request_audit
                )
            )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_sw2021_l1_membership",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "no_return_preregistration": {
                    "path": manifest_path(source_chain["spec_path"]),
                    "sha256": file_digest(source_chain["spec_path"]),
                    "preregistered_at": spec["preregistered_at"],
                },
                "symbol_normalization_repair": {
                    "path": manifest_path(source_chain["symbol_repair_path"]),
                    "sha256": file_digest(source_chain["symbol_repair_path"]),
                    "factor_formula_or_membership_interval_changed": False,
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                    "manifest_path": manifest_path(source_chain["manifest_path"]),
                    "manifest_sha256": file_digest(source_chain["manifest_path"]),
                    "run_id": source_chain["manifest"].get("run_id"),
                    "classification_frame_sha256": frame_digest(
                        source_chain["classification"]
                    ),
                    "membership_frame_sha256": frame_digest(source_chain["membership"]),
                },
                "source_request": {
                    "api": "index_member_all",
                    "classification_codes": classification_codes,
                    "is_new_values": is_new_values,
                    "expected_provider_calls": total_calls,
                    "completed_provider_calls": completed_calls,
                    "request_mode": "sequential_one_l1_code_and_one_is_new_state_per_call",
                    "fields": list(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS),
                    "forbidden_fields_requested_or_stored": [],
                    "credentials_logged_or_stored": False,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_call": maximum_attempts,
                },
                "files": [
                    {
                        "dataset": "membership",
                        "path": manifest_path(final_frame),
                        "rows": int(len(membership)),
                        "sha256": frame_digest(membership),
                    }
                ],
                "source_quality": {
                    "requests": request_audit,
                    "empty_requests": empty_requests,
                    "unsupported_provider_symbol_rows_excluded": (
                        unsupported_symbol_rows
                    ),
                    "membership_rows": int(len(membership)),
                    "current_membership_rows": current_rows,
                    "historical_membership_rows": historical_rows,
                    "unique_instruments": int(membership["instrument"].nunique()),
                    "l1_codes_with_rows": int(membership["l1_code"].nunique()),
                    "duplicate_interval_rows": int(
                        membership.duplicated(duplicate_key).sum()
                    ),
                    "minimum_in_date": membership["in_date"].min().date().isoformat(),
                    "maximum_dated_out_date": (
                        membership["out_date"].max().date().isoformat()
                        if membership["out_date"].notna().any()
                        else None
                    ),
                },
                "acceptance_status": snapshot["required_success_status"],
                "price_fields_loaded": [],
                "factor_values_constructed": False,
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            message = str(exc)
            if "row ceiling" in message:
                failure_code = "provider_row_ceiling_possible_truncation"
            elif "duplicate" in message:
                failure_code = "source_duplicate_interval"
            elif "fields outside" in message or "lacks requested fields" in message:
                failure_code = "source_schema_mismatch"
            elif "missing" in message or "interval" in message:
                failure_code = "source_interval_integrity_failure"
            else:
                failure_code = "provider_or_local_snapshot_failure"
            failure_path = RUNS_ROOT / f"{run_id}_source_failure.json"
            atomic_write_json(
                {
                    "schema_version": 1,
                    "kind": "a_share_rich_data_source_failure",
                    "dataset": "tushare_sw2021_l1_membership",
                    "provider": "tushare",
                    "run_id": run_id,
                    "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "failed_l1_code": current_l1_code,
                    "failed_is_new": current_is_new,
                    "completed_provider_calls_before_failure": completed_calls,
                    "total_planned_provider_calls": total_calls,
                    "failure_code": failure_code,
                    "partial_snapshot_deleted": not temporary_root.exists(),
                    "final_snapshot_published": run_root.exists(),
                    "data_contract": {
                        "path": manifest_path(
                            DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT
                        ),
                        "sha256": file_digest(
                            DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT
                        ),
                    },
                    "no_return_preregistration": {
                        "path": manifest_path(source_chain["spec_path"]),
                        "sha256": file_digest(source_chain["spec_path"]),
                    },
                    "symbol_normalization_repair": {
                        "path": manifest_path(source_chain["symbol_repair_path"]),
                        "sha256": file_digest(source_chain["symbol_repair_path"]),
                    },
                    "credentials_logged_or_stored": False,
                    "price_fields_loaded": [],
                    "factor_values_constructed": False,
                    "open_close_or_forward_return_fields_read": False,
                    "forward_return_fields_read": False,
                    "selection_or_promotion_allowed": False,
                },
                failure_path,
            )
            if isinstance(exc, RichDataError):
                raise RichDataError(
                    f"{message}; rejection_record={failure_path}"
                ) from exc
            raise


def load_tushare_moneyflow_acceptance() -> tuple[Path, dict[str, Any]]:
    """Verify the bound completed-session Tushare entitlement/schema probe."""

    contract = load_tushare_moneyflow_contract()
    acceptance = contract["acceptance_protocol"]
    path = resolve_record_path(acceptance["bound_manifest_path"])
    if file_digest(path) != acceptance["bound_manifest_sha256"]:
        raise RichDataError(
            "Tushare moneyflow acceptance manifest fingerprint mismatch"
        )
    manifest = load_json_record(path, kind="a_share_rich_data_snapshot")
    if (
        manifest.get("dataset") != "tushare_events"
        or manifest.get("provider") != "tushare"
        or manifest.get("requested_start") != "2026-07-13"
        or manifest.get("requested_end") != "2026-07-13"
        or "moneyflow" not in set(manifest.get("requested_datasets") or [])
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare moneyflow acceptance manifest identity mismatch")
    records = [
        item
        for item in manifest.get("files") or []
        if item.get("dataset") == "moneyflow"
    ]
    if len(records) != 1:
        raise RichDataError("Tushare acceptance must contain one moneyflow frame")
    record = records[0]
    quality = record.get("quality") or {}
    if (
        int(record.get("rows") or -1) != 5197
        or int(quality.get("missing_key_rows") or 0) != 0
        or int(quality.get("outside_requested_date_rows") or 0) != 0
        or int(quality.get("duplicate_event_key_rows") or 0) != 0
    ):
        raise RichDataError("Tushare moneyflow acceptance key audit failed")
    frame = load_snapshot_frame(record)
    normalized, _ = canonicalize_tushare_moneyflow(
        frame, dt.date(2026, 7, 13), dt.date(2026, 7, 13)
    )
    if normalized.empty or normalized["trade_date"].nunique() != 1:
        raise RichDataError("Tushare moneyflow acceptance formula audit failed")
    return path, manifest


def tushare_ts_code_from_qlib_instrument(instrument: str) -> str:
    """Convert one frozen SH/SZ Qlib instrument into a Tushare stock code."""

    value = str(instrument).strip().upper()
    if len(value) != 8 or value[:2] not in {"SH", "SZ"} or not value[2:].isdigit():
        raise RichDataError(f"invalid Qlib instrument for Tushare: {instrument}")
    return f"{value[2:]}.{value[:2]}"


def _fetch_tushare_cash_conversion_with_policy(
    endpoint: str,
    ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded endpoint retry policy."""

    retry_backoffs = (1.0, 2.0)
    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_cash_conversion_statement(
                endpoint,
                ts_code,
                announcement_start=announcement_start,
                announcement_end=announcement_end,
            )
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[min(attempt, len(retry_backoffs) - 1)])
    raise AssertionError("unreachable Tushare cash-conversion retry state")


def sync_tushare_cash_conversion(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the frozen 2019-2025 PIT cash-conversion snapshot without prices."""

    with RichDataProcessLock(METADATA_ROOT / ".tushare_cash_conversion.lock"):
        terminal_path = DEFAULT_TUSHARE_CASH_CONVERSION_RESEARCH_RECORD
        if terminal_path.exists():
            load_tushare_cash_conversion_research_record(terminal_path)
            raise RichDataError(
                "Tushare cash-conversion source version is terminal after its "
                "single repair retry; another full sync is forbidden"
            )
        source_chain = load_tushare_cash_conversion_source_chain()
        contract = source_chain["contract"]
        context = validate_tushare_cash_conversion_local_context(contract)
        prior_full = tushare_cash_conversion_full_snapshot_records()
        company_type_repair: dict[str, Any] | None = None
        if prior_full:
            company_type_repair = load_tushare_cash_conversion_company_type_repair()
            repair_failure_path = company_type_repair["failure_path"].resolve()
            if [path.resolve() for path in prior_full] != [repair_failure_path]:
                raise RichDataError(
                    "Tushare cash-conversion full snapshot or repair retry already "
                    "exists and cannot be repeated: "
                    + ", ".join(str(path) for path in prior_full)
                )
        if not allow_large:
            raise RichDataError(
                "Tushare cash-conversion full snapshot requires --allow-large"
            )
        universe_path = universe_path.expanduser().resolve()
        calendar_path = calendar_path.expanduser().resolve()
        universe_context = contract["local_context"]["holding_universe"]
        calendar_context = contract["local_context"]["calendar"]
        if (
            universe_path != resolve_record_path(universe_context["path"])
            or file_digest(universe_path) != universe_context["sha256"]
            or calendar_path != resolve_record_path(calendar_context["path"])
            or file_digest(calendar_path) != calendar_context["sha256"]
        ):
            raise RichDataError(
                "cash-conversion full snapshot universe or calendar is not the "
                "frozen point-in-time source"
            )
        require_provider("tushare")

        snapshot = contract["full_snapshot_contract"]
        gates = contract["no_return_gates"]
        completeness = gates["source_completeness"]
        acceptance = contract["acceptance_protocol"]
        announcement_start = dt.datetime.strptime(
            str(snapshot["announcement_start"]), "%Y%m%d"
        ).date()
        announcement_end = dt.datetime.strptime(
            str(snapshot["announcement_end"]), "%Y%m%d"
        ).date()
        development_start = dt.date.fromisoformat(snapshot["development_signal_start"])
        development_end = dt.date.fromisoformat(snapshot["development_signal_end"])
        latest_actual = dt.datetime.strptime(
            str(acceptance["latest_allowed_actual_announcement_date"]), "%Y%m%d"
        ).date()
        all_intervals = load_factor_universe_intervals(universe_path)
        overlap = all_intervals["start_date"].le(pd.Timestamp(development_end)) & (
            all_intervals["end_date"].ge(pd.Timestamp(development_start))
        )
        intervals = (
            all_intervals.loc[overlap].copy().sort_values("instrument", kind="stable")
        )
        if intervals.empty:
            raise RichDataError(
                "cash-conversion holding universe has no instruments in 2019-2025"
            )
        calendar = local_calendar_dates(development_start, latest_actual, calendar_path)
        if calendar.empty or calendar[-1] < pd.Timestamp(development_end):
            raise RichDataError(
                "cash-conversion local calendar cannot map the frozen signal range"
            )
        endpoints = ("income", "cashflow")
        total_planned_calls = int(len(intervals) * len(endpoints))
        if company_type_repair is not None:
            repair_protocol = company_type_repair["repair"]["unchanged_source_protocol"]
            if len(intervals) != int(
                repair_protocol["point_in_time_instrument_count"]
            ) or total_planned_calls != int(repair_protocol["provider_calls"]):
                raise RichDataError(
                    "cash-conversion company-type repair retry request count changed"
                )
        row_ceiling = int(snapshot["provider_documented_maximum_rows_per_call"])
        minimum_interval = float(snapshot["minimum_seconds_between_calls"])
        maximum_attempts = int(snapshot["maximum_attempts_per_symbol_endpoint"])

        run_id = new_run_id("tushare_cash_conversion_full")
        parent = RAW_ROOT / "tushare" / "cash_conversion" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Tushare cash-conversion full snapshot already exists: {run_id}"
            )
        temporary_root.mkdir(parents=True)
        yearly_frames: dict[int, list[pd.DataFrame]] = {
            year: [] for year in range(development_start.year, development_end.year + 1)
        }
        endpoint_quality_totals: dict[str, dict[str, int]] = {
            endpoint: {
                "input_rows": 0,
                "non_target_company_rows_excluded": 0,
                "target_company_periods_observed": 0,
                "adjustment_periods_excluded": 0,
                "no_type_one_periods_excluded": 0,
                "missing_metric_periods_excluded": 0,
                "ambiguous_type_one_periods_excluded": 0,
                "semantic_duplicate_rows_collapsed": 0,
                "accepted_periods": 0,
            }
            for endpoint in endpoints
        }
        update_flag_totals: dict[str, dict[str, int]] = {
            endpoint: {} for endpoint in endpoints
        }
        non_target_company_type_totals: dict[str, dict[str, int]] = {
            endpoint: {} for endpoint in endpoints
        }
        join_quality_totals = {
            "income_accepted_periods": 0,
            "cashflow_accepted_periods": 0,
            "income_only_periods_excluded": 0,
            "cashflow_only_periods_excluded": 0,
            "joined_periods_before_metric_policy": 0,
            "nonpositive_income_periods_excluded": 0,
            "nonfinite_cashflow_periods_excluded": 0,
            "nonfinite_derived_periods_excluded": 0,
            "usable_joined_periods": 0,
        }
        source_rows_by_endpoint = {endpoint: 0 for endpoint in endpoints}
        empty_responses_by_endpoint = {endpoint: 0 for endpoint in endpoints}
        signal_quality = {
            "without_next_calendar_session_excluded": 0,
            "outside_development_signal_range_excluded": 0,
            "outside_point_in_time_holding_interval_excluded": 0,
            "rows_written": 0,
        }
        no_factor_instruments = 0
        no_factor_instrument_examples: list[str] = []
        completed_provider_calls = 0
        completed_instruments = 0
        last_request_started: list[float | None] = [None]
        current_instrument: str | None = None
        current_endpoint: str | None = None
        started = time.monotonic()
        try:
            for interval in intervals.itertuples(index=False):
                current_instrument = str(interval.instrument)
                ts_code = tushare_ts_code_from_qlib_instrument(current_instrument)
                endpoint_frames: dict[str, pd.DataFrame] = {}
                for endpoint in endpoints:
                    current_endpoint = endpoint
                    raw = _fetch_tushare_cash_conversion_with_policy(
                        endpoint,
                        ts_code,
                        announcement_start,
                        announcement_end,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        last_request_started=last_request_started,
                    )
                    completed_provider_calls += 1
                    source_rows_by_endpoint[endpoint] += int(len(raw))
                    if raw.empty:
                        empty_responses_by_endpoint[endpoint] += 1
                    if len(raw) >= row_ceiling:
                        raise RichDataError(
                            f"Tushare {endpoint} {ts_code} reached the documented "
                            f"{row_ceiling}-row ceiling; response may be truncated"
                        )
                    canonical, quality = canonicalize_tushare_cash_conversion_endpoint(
                        raw,
                        endpoint=endpoint,
                        expected_ts_code=ts_code,
                        announcement_start=announcement_start,
                        announcement_end=announcement_end,
                        latest_actual_announcement_date=latest_actual,
                        allow_complete_integer_non_target_company_type_codes=(
                            company_type_repair is not None
                        ),
                    )
                    endpoint_frames[endpoint] = canonical
                    for key in endpoint_quality_totals[endpoint]:
                        endpoint_quality_totals[endpoint][key] += int(
                            quality.get(key, 0)
                        )
                    for flag, count in (
                        quality.get("update_flag_counts") or {}
                    ).items():
                        update_flag_totals[endpoint][str(flag)] = update_flag_totals[
                            endpoint
                        ].get(str(flag), 0) + int(count)
                    for company_type, count in (
                        quality.get("non_target_company_type_counts") or {}
                    ).items():
                        code = str(company_type)
                        non_target_company_type_totals[endpoint][code] = (
                            non_target_company_type_totals[endpoint].get(code, 0)
                            + int(count)
                        )

                factors, join_quality = derive_tushare_cash_conversion(
                    endpoint_frames["income"], endpoint_frames["cashflow"]
                )
                for key in join_quality_totals:
                    join_quality_totals[key] += int(join_quality.get(key, 0))
                if not factors.empty:
                    announcement_dates = pd.DatetimeIndex(
                        pd.to_datetime(factors["announcement_date"]).dt.normalize()
                    )
                    positions = calendar.searchsorted(announcement_dates, side="right")
                    signal_sessions = pd.Series(
                        pd.NaT, index=factors.index, dtype="datetime64[ns]"
                    )
                    has_next = positions < len(calendar)
                    if has_next.any():
                        signal_sessions.loc[has_next] = calendar.take(
                            positions[has_next]
                        ).to_numpy()
                    signal_quality["without_next_calendar_session_excluded"] += int(
                        (~has_next).sum()
                    )
                    in_development = signal_sessions.between(
                        pd.Timestamp(development_start), pd.Timestamp(development_end)
                    )
                    signal_quality["outside_development_signal_range_excluded"] += int(
                        (has_next & ~in_development).sum()
                    )
                    in_interval = signal_sessions.between(
                        pd.Timestamp(interval.start_date),
                        pd.Timestamp(interval.end_date),
                    )
                    signal_quality[
                        "outside_point_in_time_holding_interval_excluded"
                    ] += int((has_next & in_development & ~in_interval).sum())
                    retained = has_next & in_development & in_interval
                    factors = factors.loc[retained].copy()
                    signal_sessions = signal_sessions.loc[retained]
                    if not factors.empty:
                        factors["_signal_year"] = signal_sessions.dt.year.astype(int)
                        for year, year_frame in factors.groupby(
                            "_signal_year", sort=True, observed=True
                        ):
                            stored = year_frame.drop(columns="_signal_year").loc[
                                :, list(TUSHARE_CASH_CONVERSION_COLUMNS)
                            ]
                            yearly_frames[int(year)].append(stored)
                            signal_quality["rows_written"] += int(len(stored))
                if factors.empty:
                    no_factor_instruments += 1
                    if len(no_factor_instrument_examples) < 20:
                        no_factor_instrument_examples.append(current_instrument)
                completed_instruments += 1
                if completed_instruments % 25 == 0 or completed_instruments == len(
                    intervals
                ):
                    elapsed = max(time.monotonic() - started, 0.001)
                    print(
                        json.dumps(
                            {
                                "dataset": "tushare_operating_cash_conversion",
                                "completed_instruments": completed_instruments,
                                "total_instruments": int(len(intervals)),
                                "completed_provider_calls": completed_provider_calls,
                                "total_provider_calls": total_planned_calls,
                                "factor_rows_retained": signal_quality["rows_written"],
                                "elapsed_minutes": round(elapsed / 60.0, 2),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )

            if completed_provider_calls != total_planned_calls:
                raise RichDataError(
                    "cash-conversion full snapshot omitted one or more frozen calls"
                )
            files: list[dict[str, Any]] = []
            duplicate_event_keys = 0
            total_rows = 0
            for year in sorted(yearly_frames):
                frames = yearly_frames[year]
                if not frames:
                    continue
                partition = (
                    pd.concat(frames, ignore_index=True)
                    .sort_values(
                        ["announcement_date", "instrument", "report_period"],
                        kind="stable",
                    )
                    .reset_index(drop=True)
                )
                if tuple(partition.columns) != TUSHARE_CASH_CONVERSION_COLUMNS:
                    raise RichDataError(
                        f"cash-conversion {year} partition columns changed"
                    )
                duplicates = int(
                    partition.duplicated(
                        ["instrument", "announcement_date", "report_period"]
                    ).sum()
                )
                duplicate_event_keys += duplicates
                if duplicates:
                    raise RichDataError(
                        f"cash-conversion {year} partition has duplicate event keys"
                    )
                destination = temporary_root / f"{year}.parquet"
                atomic_write_frame(partition, destination)
                total_rows += int(len(partition))
                files.append(
                    {
                        "signal_year": int(year),
                        "path": manifest_path(run_root / destination.name),
                        "rows": int(len(partition)),
                        "sha256": frame_digest(partition),
                    }
                )
            observed_years = len(files)
            source_gate_passed = bool(
                total_rows >= int(completeness["minimum_complete_joined_factor_events"])
                and observed_years >= int(completeness["minimum_observed_signal_years"])
                and duplicate_event_keys == 0
            )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_operating_cash_conversion",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": announcement_start.isoformat(),
                "requested_end": announcement_end.isoformat(),
                "development_signal_start": development_start.isoformat(),
                "development_signal_end": development_end.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "company_type_source_repair": (
                    {
                        "path": manifest_path(company_type_repair["repair_path"]),
                        "sha256": file_digest(company_type_repair["repair_path"]),
                        "bound_first_failure_path": manifest_path(
                            company_type_repair["failure_path"]
                        ),
                        "bound_first_failure_sha256": file_digest(
                            company_type_repair["failure_path"]
                        ),
                        "full_from_scratch_restart": True,
                        "partial_snapshot_resumed": False,
                        "candidate_company_type": 1,
                        "complete_integer_non_target_company_types_excluded": True,
                    }
                    if company_type_repair is not None
                    else None
                ),
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                    "manifest_path": manifest_path(source_chain["manifest_path"]),
                    "manifest_sha256": file_digest(source_chain["manifest_path"]),
                    "factor_frame_path": manifest_path(source_chain["frame_path"]),
                    "factor_frame_content_sha256": frame_digest(source_chain["frame"]),
                },
                "local_no_return_context": context,
                "point_in_time_holding_universe": {
                    "path": manifest_path(universe_path),
                    "sha256": file_digest(universe_path),
                    "all_intervals": int(len(all_intervals)),
                    "requested_overlap_intervals": int(len(intervals)),
                },
                "local_calendar": {
                    "path": manifest_path(calendar_path),
                    "sha256": file_digest(calendar_path),
                    "mapping_sessions": int(len(calendar)),
                },
                "source_request": {
                    "apis": list(endpoints),
                    "request_mode": (
                        "one ts_code over the full frozen announcement-date range "
                        "for each endpoint"
                    ),
                    "fields_by_endpoint": {
                        "income": list(TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS),
                        "cashflow": list(TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS),
                    },
                    "planned_instruments": int(len(intervals)),
                    "planned_provider_calls": total_planned_calls,
                    "completed_provider_calls": completed_provider_calls,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_symbol_endpoint": maximum_attempts,
                    "retry_backoff_seconds": [1.0, 2.0],
                    "provider_documented_row_ceiling_per_call": row_ceiling,
                    "source_rows_by_endpoint": source_rows_by_endpoint,
                    "empty_responses_by_endpoint": empty_responses_by_endpoint,
                    "forbidden_fields_requested_or_stored": [],
                    "raw_statement_frames_persisted": False,
                    "credentials_logged_or_stored": False,
                },
                "files": files,
                "normalization_quality": {
                    "by_endpoint": endpoint_quality_totals,
                    "non_target_company_type_counts_by_endpoint": (
                        non_target_company_type_totals
                    ),
                    "update_flag_counts_by_endpoint": update_flag_totals,
                    "join": join_quality_totals,
                    "signal_and_universe": signal_quality,
                    "instruments_without_retained_factor": no_factor_instruments,
                    "instruments_without_retained_factor_examples": (
                        no_factor_instrument_examples
                    ),
                },
                "source_completeness": {
                    "complete_joined_factor_events": total_rows,
                    "minimum_required_events": int(
                        completeness["minimum_complete_joined_factor_events"]
                    ),
                    "observed_signal_years": observed_years,
                    "minimum_required_signal_years": int(
                        completeness["minimum_observed_signal_years"]
                    ),
                    "duplicate_factor_event_keys": duplicate_event_keys,
                    "gate_passed_before_prices": source_gate_passed,
                },
                "acceptance_status": (
                    "full_source_completeness_passed_pending_no_return_capacity_and_uniqueness"
                    if source_gate_passed
                    else "full_source_completeness_failed_stop_before_capacity_uniqueness_or_prices"
                ),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            message = safe_exception_text(exc)
            if "row ceiling" in message:
                failure_code = "provider_row_ceiling_possible_truncation"
            elif "fields outside" in message or "lacks requested fields" in message:
                failure_code = "source_schema_mismatch"
            elif "duplicate" in message:
                failure_code = "source_duplicate_key"
            elif "statement keys" in message:
                failure_code = "source_statement_key_failure"
            elif "unknown report" in message or "unknown company" in message:
                failure_code = "source_statement_type_failure"
            else:
                failure_code = "provider_or_local_snapshot_failure"
            failure_path = RUNS_ROOT / f"{run_id}_source_failure.json"
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_source_failure",
                "dataset": "tushare_operating_cash_conversion",
                "provider": "tushare",
                "run_id": run_id,
                "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": announcement_start.isoformat(),
                "requested_end": announcement_end.isoformat(),
                "failed_instrument": current_instrument,
                "failed_endpoint": current_endpoint,
                "completed_instruments_before_failure": completed_instruments,
                "completed_provider_calls_before_failure": completed_provider_calls,
                "total_planned_provider_calls": total_planned_calls,
                "failure_code": failure_code,
                "error": message,
                "partial_snapshot_deleted": not temporary_root.exists(),
                "final_snapshot_published": run_root.exists(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                },
                "company_type_source_repair": (
                    {
                        "path": manifest_path(company_type_repair["repair_path"]),
                        "sha256": file_digest(company_type_repair["repair_path"]),
                        "bound_first_failure_path": manifest_path(
                            company_type_repair["failure_path"]
                        ),
                        "bound_first_failure_sha256": file_digest(
                            company_type_repair["failure_path"]
                        ),
                        "retry_consumed_by_this_failure": True,
                    }
                    if company_type_repair is not None
                    else None
                ),
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                },
                "credentials_logged_or_stored": False,
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            atomic_write_json(failure, failure_path)
            if isinstance(exc, RichDataError):
                raise RichDataError(
                    f"{message}; rejection_record={failure_path}"
                ) from exc
            raise


def _fetch_tushare_moneyflow_with_policy(
    trade_date: dt.date,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    retry_backoffs: list[float],
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded retry policy."""

    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_moneyflow(trade_date)
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[attempt])
    raise AssertionError("unreachable Tushare retry state")


def sync_tushare_moneyflow(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the frozen 2019-2025 Tushare classified-flow history without prices."""

    with RichDataProcessLock(METADATA_ROOT / ".tushare_moneyflow.lock"):
        contract = load_tushare_moneyflow_contract()
        require_provider("tushare")
        acceptance_record = load_tushare_moneyflow_acceptance()
        snapshot_contract = contract["snapshot_contract"]
        partition_policy = snapshot_contract["partition_policy"]
        start = dt.date.fromisoformat(snapshot_contract["development_start"])
        end = dt.date.fromisoformat(snapshot_contract["development_end"])
        validate_range(start, end, allow_large=allow_large, unit_count=1)
        intervals = load_factor_universe_intervals(universe_path)
        calendar = local_calendar_dates(start, end, calendar_path)
        if calendar.empty:
            raise RichDataError(
                "local calendar has no sessions in the Tushare moneyflow range"
            )
        overlap = intervals["start_date"].le(pd.Timestamp(end)) & intervals[
            "end_date"
        ].ge(pd.Timestamp(start))
        intervals = intervals.loc[overlap].copy()
        if intervals.empty:
            raise RichDataError(
                "factor universe has no instruments in the frozen range"
            )

        run_id = new_run_id("tushare_moneyflow_daily")
        parent = RAW_ROOT / "tushare" / "moneyflow" / "daily" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(f"Tushare moneyflow snapshot already exists: {run_id}")
        temporary_root.mkdir(parents=True)
        files: list[dict[str, Any]] = []
        all_daily_coverage: list[dict[str, Any]] = []
        quality_totals = {
            "input_rows": 0,
            "missing_rows_excluded": 0,
            "zero_denominator_rows_excluded": 0,
            "outside_point_in_time_universe_rows_excluded": 0,
            "rows_written": 0,
        }
        minimum_interval = float(partition_policy["minimum_seconds_between_calls"])
        maximum_attempts = int(partition_policy["maximum_attempts_per_session"])
        retry_backoffs = [
            float(value) for value in partition_policy["retry_backoff_seconds"]
        ]
        last_request_started: list[float | None] = [None]
        try:
            for year in range(start.year, end.year + 1):
                partition_start = max(start, dt.date(year, 1, 1))
                partition_end = min(end, dt.date(year, 12, 31))
                partition_calendar = calendar[
                    (calendar >= pd.Timestamp(partition_start))
                    & (calendar <= pd.Timestamp(partition_end))
                ]
                if partition_calendar.empty:
                    continue
                year_frames: list[pd.DataFrame] = []
                year_quality = {
                    "input_rows": 0,
                    "missing_rows_excluded": 0,
                    "zero_denominator_rows_excluded": 0,
                    "outside_point_in_time_universe_rows_excluded": 0,
                    "rows_written": 0,
                }
                for session in partition_calendar:
                    session_date = pd.Timestamp(session).date()
                    raw = _fetch_tushare_moneyflow_with_policy(
                        session_date,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        retry_backoffs=retry_backoffs,
                        last_request_started=last_request_started,
                    )
                    if len(raw) >= int(
                        partition_policy["provider_documented_maximum_rows_per_call"]
                    ):
                        raise RichDataError(
                            f"Tushare moneyflow {session_date.isoformat()} reached the "
                            "provider row ceiling; the all-market response may be truncated"
                        )
                    normalized, quality = canonicalize_tushare_moneyflow(
                        raw, session_date, session_date
                    )
                    session_ts = pd.Timestamp(session)
                    active_rows = intervals[
                        intervals["start_date"].le(session_ts)
                        & intervals["end_date"].ge(session_ts)
                    ]
                    active_instruments = set(active_rows["instrument"].astype(str))
                    in_universe = normalized["instrument"].isin(active_instruments)
                    outside_universe = int((~in_universe).sum())
                    normalized = normalized.loc[in_universe].reset_index(drop=True)
                    quality["outside_point_in_time_universe_rows_excluded"] = (
                        outside_universe
                    )
                    quality["rows_written"] = int(len(normalized))
                    for key in year_quality:
                        year_quality[key] += int(quality.get(key, 0))
                    observed_names = int(normalized["instrument"].nunique())
                    expected_names = int(len(active_instruments))
                    all_daily_coverage.append(
                        {
                            "trade_date": session_date.isoformat(),
                            "expected_active_names": expected_names,
                            "positive_activity_factor_names": observed_names,
                            "coverage": (
                                observed_names / expected_names
                                if expected_names
                                else None
                            ),
                        }
                    )
                    if not normalized.empty:
                        year_frames.append(normalized)
                if not year_frames:
                    raise RichDataError(
                        f"Tushare moneyflow {year} partition has no eligible positive-activity rows"
                    )
                partition_frame = (
                    pd.concat(year_frames, ignore_index=True)
                    .sort_values(["trade_date", "instrument"], kind="stable")
                    .reset_index(drop=True)
                )
                if partition_frame.duplicated(["instrument", "trade_date"]).any():
                    raise RichDataError(
                        f"Tushare moneyflow {year} partition has duplicate stock-date keys"
                    )
                destination = temporary_root / f"{year}.parquet"
                atomic_write_frame(partition_frame, destination)
                for key in quality_totals:
                    quality_totals[key] += year_quality[key]
                files.append(
                    {
                        "year": year,
                        "requested_start": partition_start.isoformat(),
                        "requested_end": partition_end.isoformat(),
                        "provider_calls": int(len(partition_calendar)),
                        "path": manifest_path(run_root / destination.name),
                        "rows": int(len(partition_frame)),
                        "sha256": frame_digest(partition_frame),
                        "quality": year_quality,
                    }
                )
            if not files:
                raise RichDataError(
                    "Tushare moneyflow sync produced no completed partitions"
                )
            coverages = pd.Series(
                [
                    row["coverage"]
                    for row in all_daily_coverage
                    if row["coverage"] is not None
                ],
                dtype="float64",
            )
            median_coverage = float(coverages.median()) if len(coverages) else 0.0
            p05_coverage = float(coverages.quantile(0.05)) if len(coverages) else 0.0
            coverage_policy = contract["coverage_and_capacity_policy"]
            minimum_names = int(
                coverage_policy["minimum_eligible_names_per_cross_section"]
            )
            dates_with_minimum_names = int(
                sum(
                    row["positive_activity_factor_names"] >= minimum_names
                    for row in all_daily_coverage
                )
            )
            coverage_gate_passed = bool(
                len(coverages)
                and median_coverage
                >= float(coverage_policy["minimum_median_source_row_coverage"])
                and p05_coverage
                >= float(coverage_policy["minimum_p05_source_row_coverage"])
                and dates_with_minimum_names >= 200
            )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_moneyflow_daily",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_MONEYFLOW_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_MONEYFLOW_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "source_acceptance": {
                    "path": manifest_path(acceptance_record[0]),
                    "sha256": file_digest(acceptance_record[0]),
                    "run_id": acceptance_record[1].get("run_id"),
                    "status": contract["acceptance_protocol"]["status"],
                },
                "point_in_time_universe": {
                    "path": manifest_path(universe_path.expanduser().resolve()),
                    "sha256": file_digest(universe_path.expanduser().resolve()),
                    "intervals": int(
                        len(load_factor_universe_intervals(universe_path))
                    ),
                },
                "local_calendar": {
                    "path": manifest_path(calendar_path.expanduser().resolve()),
                    "sha256": file_digest(calendar_path.expanduser().resolve()),
                    "sessions_in_requested_range": int(len(calendar)),
                },
                "source_request": {
                    "api": "moneyflow",
                    "frequency": "daily",
                    "request_mode": "one completed local trading session per call",
                    "fields": list(TUSHARE_MONEYFLOW_RAW_FIELDS),
                    "forbidden_fields_requested_or_stored": [],
                    "credentials_logged_or_stored": False,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_session": maximum_attempts,
                },
                "files": files,
                "normalization_quality": quality_totals,
                "coverage": {
                    "calendar_sessions": int(len(calendar)),
                    "median_positive_activity_factor_coverage": median_coverage,
                    "p05_positive_activity_factor_coverage": p05_coverage,
                    "dates_with_at_least_fifty_factor_names": dates_with_minimum_names,
                    "gate_passed_before_prices": coverage_gate_passed,
                    "daily": all_daily_coverage,
                },
                "acceptance_status": (
                    "full_source_coverage_passed_pending_no_return_capacity"
                    if coverage_gate_passed
                    else "full_source_coverage_failed_stop_before_prices"
                ),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception:
            shutil.rmtree(temporary_root, ignore_errors=True)
            raise


def _fetch_tushare_daily_pb_with_policy(
    trade_date: dt.date,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    retry_backoffs: list[float],
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded retry policy to PB."""

    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_daily_pb(trade_date)
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[attempt])
    raise AssertionError("unreachable Tushare daily PB retry state")


def sync_tushare_daily_pb(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the frozen 2019-2025 positive book-to-market history without prices."""

    with RichDataProcessLock(METADATA_ROOT / ".tushare_daily_pb.lock"):
        contract = load_tushare_daily_pb_contract()
        source_chain = load_tushare_daily_pb_source_chain()
        require_provider("tushare")
        snapshot_contract = contract["snapshot_contract"]
        partition_policy = snapshot_contract["partition_policy"]
        start = dt.date.fromisoformat(snapshot_contract["development_start"])
        end = dt.date.fromisoformat(snapshot_contract["development_end"])
        validate_range(start, end, allow_large=allow_large, unit_count=1)
        all_intervals = load_factor_universe_intervals(universe_path)
        calendar = local_calendar_dates(start, end, calendar_path)
        if calendar.empty:
            raise RichDataError(
                "local calendar has no sessions in the Tushare daily PB range"
            )
        overlap = all_intervals["start_date"].le(pd.Timestamp(end)) & all_intervals[
            "end_date"
        ].ge(pd.Timestamp(start))
        intervals = all_intervals.loc[overlap].copy()
        if intervals.empty:
            raise RichDataError(
                "holding universe has no instruments in the frozen PB range"
            )

        run_id = new_run_id("tushare_daily_pb")
        parent = RAW_ROOT / "tushare" / "daily_pb" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(f"Tushare daily PB snapshot already exists: {run_id}")
        temporary_root.mkdir(parents=True)
        files: list[dict[str, Any]] = []
        all_daily_coverage: list[dict[str, Any]] = []
        quality_totals = {
            "input_rows": 0,
            "missing_pb_rows_excluded": 0,
            "nonpositive_pb_rows_excluded": 0,
            "outside_point_in_time_holding_universe_rows_excluded": 0,
            "rows_written": 0,
        }
        minimum_interval = float(partition_policy["minimum_seconds_between_calls"])
        maximum_attempts = int(partition_policy["maximum_attempts_per_session"])
        retry_backoffs = [
            float(value) for value in partition_policy["retry_backoff_seconds"]
        ]
        last_request_started: list[float | None] = [None]
        completed_calls = 0
        total_calls = int(len(calendar))
        current_session_date: dt.date | None = None
        try:
            for year in range(start.year, end.year + 1):
                partition_start = max(start, dt.date(year, 1, 1))
                partition_end = min(end, dt.date(year, 12, 31))
                partition_calendar = calendar[
                    (calendar >= pd.Timestamp(partition_start))
                    & (calendar <= pd.Timestamp(partition_end))
                ]
                if partition_calendar.empty:
                    continue
                year_frames: list[pd.DataFrame] = []
                year_quality = {
                    "input_rows": 0,
                    "missing_pb_rows_excluded": 0,
                    "nonpositive_pb_rows_excluded": 0,
                    "outside_point_in_time_holding_universe_rows_excluded": 0,
                    "rows_written": 0,
                }
                for session in partition_calendar:
                    session_date = pd.Timestamp(session).date()
                    current_session_date = session_date
                    raw = _fetch_tushare_daily_pb_with_policy(
                        session_date,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        retry_backoffs=retry_backoffs,
                        last_request_started=last_request_started,
                    )
                    if len(raw) >= int(
                        partition_policy["provider_documented_maximum_rows_per_call"]
                    ):
                        raise RichDataError(
                            f"Tushare daily PB {session_date.isoformat()} reached the "
                            "provider row ceiling; the all-market response may be truncated"
                        )
                    normalized, quality = canonicalize_tushare_daily_pb(
                        raw, session_date, session_date
                    )
                    session_ts = pd.Timestamp(session)
                    active_rows = intervals[
                        intervals["start_date"].le(session_ts)
                        & intervals["end_date"].ge(session_ts)
                    ]
                    active_instruments = set(active_rows["instrument"].astype(str))
                    in_universe = normalized["instrument"].isin(active_instruments)
                    outside_universe = int((~in_universe).sum())
                    normalized = normalized.loc[in_universe].reset_index(drop=True)
                    quality["outside_point_in_time_holding_universe_rows_excluded"] = (
                        outside_universe
                    )
                    quality["rows_written"] = int(len(normalized))
                    for key in year_quality:
                        year_quality[key] += int(quality.get(key, 0))
                    observed_names = int(normalized["instrument"].nunique())
                    expected_names = int(len(active_instruments))
                    all_daily_coverage.append(
                        {
                            "trade_date": session_date.isoformat(),
                            "expected_active_holding_names": expected_names,
                            "positive_pb_holding_names": observed_names,
                            "coverage": (
                                observed_names / expected_names
                                if expected_names
                                else None
                            ),
                        }
                    )
                    if not normalized.empty:
                        year_frames.append(normalized)
                    completed_calls += 1
                    if completed_calls % 50 == 0 or completed_calls == total_calls:
                        print(
                            json.dumps(
                                {
                                    "dataset": "tushare_daily_pb",
                                    "progress_calls": completed_calls,
                                    "total_calls": total_calls,
                                    "latest_session": session_date.isoformat(),
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                if not year_frames:
                    raise RichDataError(
                        f"Tushare daily PB {year} partition has no eligible positive-PB rows"
                    )
                partition_frame = (
                    pd.concat(year_frames, ignore_index=True)
                    .sort_values(["trade_date", "instrument"], kind="stable")
                    .reset_index(drop=True)
                )
                if tuple(partition_frame.columns) != TUSHARE_DAILY_PB_COLUMNS:
                    raise RichDataError(
                        f"Tushare daily PB {year} partition columns changed"
                    )
                if partition_frame.duplicated(["instrument", "trade_date"]).any():
                    raise RichDataError(
                        f"Tushare daily PB {year} partition has duplicate stock-date keys"
                    )
                destination = temporary_root / f"{year}.parquet"
                atomic_write_frame(partition_frame, destination)
                for key in quality_totals:
                    quality_totals[key] += year_quality[key]
                files.append(
                    {
                        "year": year,
                        "requested_start": partition_start.isoformat(),
                        "requested_end": partition_end.isoformat(),
                        "provider_calls": int(len(partition_calendar)),
                        "path": manifest_path(run_root / destination.name),
                        "rows": int(len(partition_frame)),
                        "sha256": frame_digest(partition_frame),
                        "quality": year_quality,
                    }
                )
                print(
                    json.dumps(
                        {
                            "dataset": "tushare_daily_pb",
                            "completed_year": year,
                            "rows": int(len(partition_frame)),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            if not files:
                raise RichDataError(
                    "Tushare daily PB sync produced no completed partitions"
                )
            coverages = pd.Series(
                [
                    row["coverage"]
                    for row in all_daily_coverage
                    if row["coverage"] is not None
                ],
                dtype="float64",
            )
            median_coverage = float(coverages.median()) if len(coverages) else 0.0
            p05_coverage = float(coverages.quantile(0.05)) if len(coverages) else 0.0
            coverage_policy = contract["source_completeness_policy"]
            dates_with_minimum_names = int(
                sum(
                    row["positive_pb_holding_names"] >= 50 for row in all_daily_coverage
                )
            )
            observed_years = len({int(item["year"]) for item in files})
            coverage_gate_passed = bool(
                len(coverages)
                and median_coverage
                >= float(
                    coverage_policy[
                        "minimum_median_positive_pb_holding_universe_coverage"
                    ]
                )
                and p05_coverage
                >= float(
                    coverage_policy["minimum_p05_positive_pb_holding_universe_coverage"]
                )
                and dates_with_minimum_names
                >= int(coverage_policy["minimum_sessions_with_fifty_positive_pb_names"])
                and observed_years
                >= int(coverage_policy["minimum_observed_source_years"])
            )
            spec = source_chain["spec"]
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_daily_pb",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "no_return_preregistration": {
                    "path": manifest_path(source_chain["spec_path"]),
                    "sha256": file_digest(source_chain["spec_path"]),
                    "preregistered_at": spec["preregistered_at"],
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                    "manifest_path": manifest_path(source_chain["manifest_path"]),
                    "manifest_sha256": file_digest(source_chain["manifest_path"]),
                    "run_id": source_chain["manifest"].get("run_id"),
                    "frame_path": manifest_path(source_chain["frame_path"]),
                    "frame_content_sha256": (
                        source_chain["manifest"]["files"][0]["sha256"]
                    ),
                },
                "point_in_time_holding_universe": {
                    "path": manifest_path(universe_path.expanduser().resolve()),
                    "sha256": file_digest(universe_path.expanduser().resolve()),
                    "intervals": int(len(all_intervals)),
                },
                "local_calendar": {
                    "path": manifest_path(calendar_path.expanduser().resolve()),
                    "sha256": file_digest(calendar_path.expanduser().resolve()),
                    "sessions_in_requested_range": int(len(calendar)),
                },
                "source_request": {
                    "api": "daily_basic",
                    "frequency": "daily_after_close",
                    "request_mode": "one completed local trading session per call",
                    "fields": list(TUSHARE_DAILY_PB_RAW_FIELDS),
                    "forbidden_fields_requested_or_stored": [],
                    "credentials_logged_or_stored": False,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_session": maximum_attempts,
                },
                "files": files,
                "normalization_quality": quality_totals,
                "coverage": {
                    "calendar_sessions": int(len(calendar)),
                    "observed_source_years": observed_years,
                    "median_positive_pb_holding_universe_coverage": median_coverage,
                    "p05_positive_pb_holding_universe_coverage": p05_coverage,
                    "sessions_with_at_least_fifty_positive_pb_names": (
                        dates_with_minimum_names
                    ),
                    "gate_passed_before_prices": coverage_gate_passed,
                    "daily": all_daily_coverage,
                },
                "acceptance_status": (
                    "full_source_coverage_passed_pending_no_return_uniqueness_and_capacity"
                    if coverage_gate_passed
                    else "full_source_coverage_failed_stop_before_uniqueness_capacity_or_prices"
                ),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            message = str(exc)
            if "missing keys" in message:
                failure_code = "source_missing_instrument_or_trade_date_key"
            elif "row ceiling" in message:
                failure_code = "provider_row_ceiling_possible_truncation"
            elif "duplicate" in message:
                failure_code = "source_duplicate_key"
            elif "outside the request" in message:
                failure_code = "source_date_outside_request"
            elif "fields outside" in message or "lacks requested fields" in message:
                failure_code = "source_schema_mismatch"
            elif "negative" in message or "infinite" in message:
                failure_code = "source_value_domain_failure"
            else:
                failure_code = "provider_or_local_snapshot_failure"
            failure_path = RUNS_ROOT / f"{run_id}_source_failure.json"
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_source_failure",
                "dataset": "tushare_daily_pb",
                "provider": "tushare",
                "run_id": run_id,
                "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "failed_session": (
                    current_session_date.isoformat()
                    if current_session_date is not None
                    else None
                ),
                "completed_provider_calls_before_failure": completed_calls,
                "total_planned_provider_calls": total_calls,
                "failure_code": failure_code,
                "partial_snapshot_deleted": not temporary_root.exists(),
                "final_snapshot_published": run_root.exists(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                },
                "no_return_preregistration": {
                    "path": manifest_path(source_chain["spec_path"]),
                    "sha256": file_digest(source_chain["spec_path"]),
                },
                "credentials_logged_or_stored": False,
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            atomic_write_json(failure, failure_path)
            if isinstance(exc, RichDataError):
                raise RichDataError(
                    f"{message}; rejection_record={failure_path}"
                ) from exc
            raise


def load_jqdata_moneyflow_acceptance(
    runs_root: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Load and verify the latest accepted four-symbol entitlement snapshot."""

    expected_symbols = {qlib_symbol(code) for code in DEFAULT_ACCEPTANCE_SYMBOLS}
    root = (runs_root or RUNS_ROOT).expanduser()
    for path in reversed(sorted(root.glob("*.json"))):
        try:
            manifest = load_json_record(path, kind="a_share_rich_data_snapshot")
        except RichDataError:
            continue
        if manifest.get("dataset") != "jqdata_moneyflow_pro_daily":
            continue
        if (
            manifest.get("provider") != "jqdata"
            or manifest.get("acceptance_status")
            != "accepted_entitlement_and_formula_pending_full_history"
        ):
            continue
        contract = manifest.get("data_contract") or {}
        request = manifest.get("source_request") or {}
        if (
            contract.get("sha256") != JQDATA_MONEYFLOW_CONTRACT_SHA256
            or request.get("fields") != list(JQDATA_MONEYFLOW_RAW_FIELDS)
            or request.get("forbidden_fields_requested_or_stored") != []
            or request.get("credentials_logged_or_stored") is not False
            or manifest.get("price_fields_loaded") != []
            or manifest.get("forward_return_fields_read") is not False
            or manifest.get("selection_or_promotion_allowed") is not False
        ):
            raise RichDataError(
                "JQData moneyflow acceptance manifest violates the frozen contract"
            )
        files = list(manifest.get("files") or [])
        if len(files) != 1:
            raise RichDataError(
                "JQData moneyflow acceptance must contain one daily partition"
            )
        frame = load_snapshot_frame(files[0])
        if (
            tuple(frame.columns) != JQDATA_MONEYFLOW_COLUMNS
            or set(frame["instrument"].astype(str)) != expected_symbols
            or frame["trade_date"].nunique() != 1
            or not frame["jqdata_large_order_net_inflow_share"].between(-1.0, 1.0).all()
        ):
            raise RichDataError(
                "JQData moneyflow acceptance data violates the frozen schema"
            )
        return path.resolve(), manifest
    raise RichDataError(
        "no accepted JQData moneyflow entitlement snapshot exists; "
        "run acceptance-jqdata-moneyflow first"
    )


def sync_jqdata_moneyflow(
    *,
    acceptance_date: dt.date | None = None,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the frozen JQData daily classified-flow snapshot without prices."""

    contract = load_jqdata_moneyflow_contract()
    require_provider("jqdata")
    acceptance = acceptance_date is not None
    if acceptance:
        start = end = acceptance_date
        codes = list(contract["acceptance_protocol"]["symbols"])
        intervals = None
        acceptance_record: tuple[Path, dict[str, Any]] | None = None
    else:
        acceptance_record = load_jqdata_moneyflow_acceptance()
        snapshot_contract = contract["snapshot_contract"]
        start = dt.date.fromisoformat(snapshot_contract["development_start"])
        end = dt.date.fromisoformat(snapshot_contract["development_end"])
        intervals = load_factor_universe_intervals(universe_path)
        overlap = intervals["start_date"].le(pd.Timestamp(end)) & intervals[
            "end_date"
        ].ge(pd.Timestamp(start))
        codes = intervals.loc[overlap, "instrument"].str[2:].astype(str).tolist()
        if not codes:
            raise RichDataError(
                "factor universe has no instruments in the frozen range"
            )
    validate_range(start, end, allow_large=allow_large, unit_count=len(codes))
    calendar = local_calendar_dates(start, end, calendar_path)
    if calendar.empty:
        raise RichDataError(
            "local calendar has no sessions in the JQData moneyflow range"
        )
    if acceptance and len(calendar) != 1:
        raise RichDataError(
            "JQData moneyflow acceptance date is not a local trading session"
        )

    run_id = new_run_id("jqdata_moneyflow_daily")
    parent = RAW_ROOT / "jqdata" / "moneyflow" / "daily" / "snapshots"
    run_root = parent / run_id
    temporary_root = parent / f".{run_id}.partial"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"JQData moneyflow snapshot already exists: {run_id}")
    temporary_root.mkdir(parents=True)
    files: list[dict[str, Any]] = []
    all_daily_coverage: list[dict[str, Any]] = []
    quality_totals = {
        "input_rows": 0,
        "missing_rows_excluded": 0,
        "zero_denominator_rows_excluded": 0,
        "outside_point_in_time_universe_rows_excluded": 0,
        "rows_written": 0,
    }
    try:
        for year in range(start.year, end.year + 1):
            partition_start = max(start, dt.date(year, 1, 1))
            partition_end = min(end, dt.date(year, 12, 31))
            partition_calendar = calendar[
                (calendar >= pd.Timestamp(partition_start))
                & (calendar <= pd.Timestamp(partition_end))
            ]
            if partition_calendar.empty:
                continue
            if intervals is None:
                partition_codes = codes
                partition_intervals = None
            else:
                overlap = intervals["start_date"].le(
                    pd.Timestamp(partition_end)
                ) & intervals["end_date"].ge(pd.Timestamp(partition_start))
                partition_intervals = intervals.loc[overlap].copy()
                partition_codes = (
                    partition_intervals["instrument"].str[2:].astype(str).tolist()
                )
            raw = fetch_jqdata_moneyflow_pro(
                partition_codes, partition_start, partition_end
            )
            if len(raw) >= int(
                contract["snapshot_contract"]["partition_policy"][
                    "provider_documented_maximum_rows_per_call"
                ]
            ):
                raise RichDataError(
                    f"JQData moneyflow {year} partition reached the provider row ceiling"
                )
            normalized, quality = canonicalize_jqdata_moneyflow(
                raw, partition_codes, partition_start, partition_end
            )
            outside_universe = 0
            if partition_intervals is not None and not normalized.empty:
                indexed = partition_intervals.set_index("instrument")
                starts = normalized["instrument"].map(indexed["start_date"])
                ends = normalized["instrument"].map(indexed["end_date"])
                in_universe = normalized["trade_date"].ge(starts) & normalized[
                    "trade_date"
                ].le(ends)
                outside_universe = int((~in_universe).sum())
                normalized = normalized.loc[in_universe].reset_index(drop=True)
            if normalized.empty:
                raise RichDataError(
                    f"JQData moneyflow {year} partition has no eligible positive-activity rows; "
                    "verify the separately purchased product entitlement"
                )
            if acceptance:
                observed = set(normalized["instrument"])
                expected = {qlib_symbol(code) for code in codes}
                if observed != expected:
                    missing = sorted(expected - observed)
                    raise RichDataError(
                        "JQData moneyflow acceptance did not return all four frozen symbols: "
                        + ", ".join(missing)
                    )
            observed_by_date = normalized.groupby("trade_date").size().to_dict()
            for date in partition_calendar:
                if partition_intervals is None:
                    expected_names = len(partition_codes)
                else:
                    expected_names = int(
                        (
                            partition_intervals["start_date"].le(date)
                            & partition_intervals["end_date"].ge(date)
                        ).sum()
                    )
                observed_names = int(observed_by_date.get(pd.Timestamp(date), 0))
                all_daily_coverage.append(
                    {
                        "trade_date": pd.Timestamp(date).date().isoformat(),
                        "expected_active_names": expected_names,
                        "positive_activity_factor_names": observed_names,
                        "coverage": (
                            observed_names / expected_names if expected_names else None
                        ),
                    }
                )
            destination = temporary_root / f"{year}.parquet"
            atomic_write_frame(normalized, destination)
            quality["outside_point_in_time_universe_rows_excluded"] = outside_universe
            quality["rows_written"] = int(len(normalized))
            for key in quality_totals:
                quality_totals[key] += int(quality.get(key, 0))
            files.append(
                {
                    "year": year,
                    "requested_start": partition_start.isoformat(),
                    "requested_end": partition_end.isoformat(),
                    "requested_symbols": len(partition_codes),
                    "path": manifest_path(run_root / destination.name),
                    "rows": int(len(normalized)),
                    "sha256": frame_digest(normalized),
                    "quality": quality,
                }
            )
        if not files:
            raise RichDataError(
                "JQData moneyflow sync produced no completed partitions"
            )
        coverages = pd.Series(
            [
                row["coverage"]
                for row in all_daily_coverage
                if row["coverage"] is not None
            ],
            dtype="float64",
        )
        median_coverage = float(coverages.median()) if len(coverages) else 0.0
        p05_coverage = float(coverages.quantile(0.05)) if len(coverages) else 0.0
        minimum_names = int(
            contract["coverage_and_capacity_policy"][
                "minimum_eligible_names_per_cross_section"
            ]
        )
        coverage_gate_passed = bool(
            len(coverages)
            and median_coverage
            >= float(
                contract["coverage_and_capacity_policy"][
                    "minimum_median_source_row_coverage"
                ]
            )
            and p05_coverage
            >= float(
                contract["coverage_and_capacity_policy"][
                    "minimum_p05_source_row_coverage"
                ]
            )
            and sum(
                row["positive_activity_factor_names"] >= minimum_names
                for row in all_daily_coverage
            )
            >= 200
        )
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "jqdata_moneyflow_pro_daily",
            "provider": "jqdata",
            "run_id": run_id,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_JQDATA_MONEYFLOW_CONTRACT),
                "sha256": file_digest(DEFAULT_JQDATA_MONEYFLOW_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_acceptance": (
                None
                if acceptance_record is None
                else {
                    "path": manifest_path(acceptance_record[0]),
                    "sha256": file_digest(acceptance_record[0]),
                    "run_id": acceptance_record[1].get("run_id"),
                    "status": acceptance_record[1].get("acceptance_status"),
                }
            ),
            "point_in_time_universe": (
                None
                if acceptance
                else {
                    "path": manifest_path(universe_path.expanduser().resolve()),
                    "sha256": file_digest(universe_path.expanduser().resolve()),
                    "intervals": int(len(intervals)),
                }
            ),
            "local_calendar": {
                "path": manifest_path(calendar_path.expanduser().resolve()),
                "sha256": file_digest(calendar_path.expanduser().resolve()),
                "sessions_in_requested_range": int(len(calendar)),
            },
            "source_request": {
                "api": "get_money_flow_pro",
                "frequency": "daily",
                "data_type": "money",
                "fields": list(JQDATA_MONEYFLOW_RAW_FIELDS),
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "files": files,
            "normalization_quality": quality_totals,
            "coverage": {
                "calendar_sessions": int(len(calendar)),
                "median_positive_activity_factor_coverage": median_coverage,
                "p05_positive_activity_factor_coverage": p05_coverage,
                "dates_with_at_least_fifty_factor_names": int(
                    sum(
                        row["positive_activity_factor_names"] >= minimum_names
                        for row in all_daily_coverage
                    )
                ),
                "gate_passed_before_prices": coverage_gate_passed,
                "daily": all_daily_coverage,
            },
            "acceptance_status": (
                "accepted_entitlement_and_formula_pending_full_history"
                if acceptance
                else (
                    "full_source_coverage_passed_pending_no_return_capacity"
                    if coverage_gate_passed
                    else "full_source_coverage_failed_stop_before_prices"
                )
            ),
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def advisory_lock_status(path: Path) -> dict[str, Any]:
    """Inspect an advisory lock without deleting, truncating, or acquiring it long-term."""

    path = path.expanduser().resolve()
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "recorded_owner_pid": None,
            "advisory_lock_currently_held": False,
        }
    try:
        with path.open("r", encoding="utf-8") as handle:
            owner = handle.read().strip() or None
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                held = True
            else:
                held = False
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except FileNotFoundError:  # The owner may exit between exists() and open().
        return {
            "path": str(path),
            "exists": False,
            "recorded_owner_pid": None,
            "advisory_lock_currently_held": False,
        }
    return {
        "path": str(path),
        "exists": True,
        "recorded_owner_pid": owner,
        "advisory_lock_currently_held": held,
    }


def baostock_5m_storage_status(data_root: Path) -> dict[str, Any]:
    """Summarize one five-minute storage root without network access or mutation."""

    resolved = data_root.expanduser().resolve()
    raw_root = resolved / "raw" / "a_share" / "rich" / "baostock" / "minutes" / "5m"
    runs_root = resolved / "metadata" / "rich_data" / "runs"
    availability_root = resolved / "metadata" / "rich_data" / "availability"
    preflight_root = resolved / "metadata" / "rich_data" / "preflights"
    raw_files = sorted(raw_root.rglob("*.parquet")) if raw_root.exists() else []
    run_paths = sorted(runs_root.glob("*.json")) if runs_root.exists() else []
    history_manifests: list[Path] = []
    for path in run_paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if record.get("dataset") == "baostock_five_minute_history":
            history_manifests.append(path)

    availability_paths = (
        sorted(availability_root.glob("*.json")) if availability_root.exists() else []
    )
    latest_probe: dict[str, Any] | None = None
    if availability_paths:
        latest_path = availability_paths[-1]
        try:
            record = load_json_record(
                latest_path, kind="a_share_baostock_5m_restoration_probe"
            )
        except (RichDataError, ValueError, OSError, json.JSONDecodeError):
            latest_probe = {
                "path": str(latest_path.resolve()),
                "record_valid": False,
                "status": "invalid_record",
                "created_at": None,
                "history_query_succeeded": False,
                "rows": 0,
            }
        else:
            latest_probe = {
                "path": str(latest_path.resolve()),
                "record_valid": True,
                "status": str(record.get("status") or "unknown"),
                "created_at": record.get("created_at"),
                "history_query_succeeded": bool(
                    record.get("history_query_succeeded", False)
                ),
                "rows": int(record.get("rows") or 0),
            }

    preflight_paths = (
        sorted(preflight_root.glob("*.json")) if preflight_root.exists() else []
    )
    latest_preflight: dict[str, Any] | None = None
    if preflight_paths:
        latest_path = preflight_paths[-1]
        try:
            record = load_json_record(latest_path, kind="a_share_baostock_5m_preflight")
        except (RichDataError, ValueError, OSError, json.JSONDecodeError):
            latest_preflight = {
                "path": str(latest_path.resolve()),
                "record_valid": False,
                "status": "invalid_record",
            }
        else:
            latest_preflight = {
                "path": str(latest_path.resolve()),
                "record_valid": True,
                "status": str(record.get("status") or "unknown"),
                "observed_free_gib": record.get("observed_free_gib"),
                "network_request_issued": bool(
                    record.get("network_request_issued", False)
                ),
            }

    return {
        "data_root": str(resolved),
        "network_request_issued": False,
        "raw_parquet_file_count": len(raw_files),
        "history_manifest_count": len(history_manifests),
        "latest_history_manifest": (
            str(history_manifests[-1].resolve()) if history_manifests else None
        ),
        "latest_restoration_probe": latest_probe,
        "latest_preflight": latest_preflight,
        "process_lock": advisory_lock_status(resolved / ".a_share_baostock_5m.lock"),
    }


def status_payload(data_root: Path = DATA_ROOT) -> dict[str, Any]:
    """Return safe machine-readable readiness information."""

    manifests = sorted(RUNS_ROOT.glob("*.json")) if RUNS_ROOT.exists() else []
    alignments = (
        sorted(ALIGNMENTS_ROOT.glob("*.json")) if ALIGNMENTS_ROOT.exists() else []
    )
    feature_runs = (
        sorted(FEATURE_RUNS_ROOT.glob("*.json")) if FEATURE_RUNS_ROOT.exists() else []
    )
    return {
        "repository": str(REPO_ROOT),
        "data_root": str(DATA_ROOT),
        "providers": [
            asdict(provider_availability(provider))
            | {"ready": provider_availability(provider).ready}
            for provider in PROVIDER_REQUIREMENTS
        ],
        "snapshot_manifest_count": len(manifests),
        "latest_snapshot_manifest": str(manifests[-1]) if manifests else None,
        "alignment_confirmation_count": len(alignments),
        "latest_alignment_confirmation": str(alignments[-1]) if alignments else None,
        "minute_feature_run_count": len(feature_runs),
        "latest_minute_feature_run": str(feature_runs[-1]) if feature_runs else None,
        "baostock_five_minute_storage": baostock_5m_storage_status(data_root),
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    status = subparsers.add_parser(
        "status", help="show safe provider readiness and stored snapshots"
    )
    status.add_argument(
        "--data-root",
        type=Path,
        default=DATA_ROOT,
        help="inspect this BaoStock five-minute storage root without network access",
    )

    minute = subparsers.add_parser(
        "sync-minutes", help="download explicit-symbol minute bars"
    )
    minute.add_argument("--provider", choices=sorted(MINUTE_FETCHERS), required=True)
    minute.add_argument(
        "--symbols",
        type=parse_symbols,
        required=True,
        help="comma-separated six-digit A-share codes",
    )
    minute.add_argument("--start", type=parse_date, required=True)
    minute.add_argument("--end", type=parse_date, required=True)
    minute.add_argument("--frequency", default="1m")
    minute.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm a request above 100 symbol-sessions",
    )

    acceptance = subparsers.add_parser(
        "acceptance", help="run a small minute-data acceptance download"
    )
    acceptance.add_argument(
        "--provider", choices=sorted(MINUTE_FETCHERS), required=True
    )
    acceptance.add_argument(
        "--date", type=parse_date, default=latest_completed_session_date()
    )
    acceptance.add_argument(
        "--symbols", type=parse_symbols, default=list(DEFAULT_ACCEPTANCE_SYMBOLS)
    )
    acceptance.add_argument("--frequency", default="1m")

    subparsers.add_parser(
        "acceptance-baostock-5m",
        help="run the frozen four-symbol BaoStock five-minute acceptance",
    )

    baostock_preflight = subparsers.add_parser(
        "preflight-baostock-5m",
        help="audit the frozen source chain and target storage without a network request",
    )
    baostock_preflight.add_argument("--data-root", type=Path, default=DATA_ROOT)
    baostock_preflight.add_argument(
        "--universe-file", type=Path, default=DEFAULT_FACTOR_UNIVERSE
    )
    baostock_preflight.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )

    baostock_restoration = subparsers.add_parser(
        "probe-baostock-5m-restoration",
        help="issue one accepted-date probe after an anonymous-provider cooldown",
    )
    baostock_restoration.add_argument("--data-root", type=Path, default=DATA_ROOT)

    baostock_history = subparsers.add_parser(
        "sync-baostock-5m",
        help="download the frozen 2020--2025 PIT-universe BaoStock five-minute snapshot",
    )
    baostock_history.add_argument(
        "--data-root",
        type=Path,
        default=DATA_ROOT,
        help="raw/metadata root; use a large external volume when the repository disk is full",
    )
    baostock_history.add_argument(
        "--universe-file", type=Path, default=DEFAULT_FACTOR_UNIVERSE
    )
    baostock_history.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    baostock_history.add_argument(
        "--workers",
        type=int,
        choices=range(1, BAOSTOCK_5M_MAX_WORKERS + 1),
        default=BAOSTOCK_5M_MAX_WORKERS,
    )
    baostock_history.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted full-universe, multi-year anonymous request",
    )

    events = subparsers.add_parser(
        "sync-tushare-events", help="download Tushare event tables after the close"
    )
    events.add_argument("--datasets", default=",".join(DEFAULT_EVENT_DATASETS))
    events.add_argument("--start", type=parse_date, required=True)
    events.add_argument("--end", type=parse_date, required=True)
    events.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm a request above 100 table-sessions",
    )

    ts_moneyflow = subparsers.add_parser(
        "sync-tushare-moneyflow",
        help="download the frozen 2019-2025 Tushare daily classified-moneyflow snapshot",
    )
    ts_moneyflow.add_argument(
        "--universe-file", type=Path, default=DEFAULT_FACTOR_UNIVERSE
    )
    ts_moneyflow.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    ts_moneyflow.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the licensed full-universe multi-year request after acceptance passes",
    )

    subparsers.add_parser(
        "acceptance-tushare-northbound-top10",
        help="run the frozen completed-session Northbound top-ten entitlement check",
    )

    subparsers.add_parser(
        "acceptance-tushare-top-inst",
        help="run the one-shot completed-session institution-seat acceptance",
    )

    subparsers.add_parser(
        "acceptance-tushare-top10-float-concentration",
        help="run the frozen three-symbol top-ten float concentration acceptance",
    )

    subparsers.add_parser(
        "acceptance-tushare-cash-conversion",
        help="run the frozen three-symbol income/cashflow accounting acceptance",
    )

    subparsers.add_parser(
        "acceptance-tushare-earnings-forecast",
        help="run the frozen three-symbol earnings-forecast acceptance",
    )

    subparsers.add_parser(
        "acceptance-tushare-disclosure-promptness",
        help="run the frozen three-period financial-report plan acceptance",
    )

    subparsers.add_parser(
        "acceptance-tushare-audit-opinion",
        help="run the frozen three-stock financial-audit-opinion acceptance",
    )

    subparsers.add_parser(
        "acceptance-tushare-gross-margin",
        help="run the frozen three-stock initial gross-margin-change acceptance",
    )

    subparsers.add_parser(
        "acceptance-tushare-management-continuity",
        help="run the frozen privacy-minimized management-continuity acceptance",
    )

    ts_stock_st = subparsers.add_parser(
        "sync-tushare-stock-st-membership",
        help="download the frozen 2019-2025 daily ST-membership source snapshot",
    )
    ts_stock_st.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    ts_stock_st.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the one-shot 1,699-call sequential licensed request",
    )

    ts_audit_opinion = subparsers.add_parser(
        "sync-tushare-audit-opinions",
        help="download the frozen 2019-2025 full-market audit-opinion snapshot",
    )
    ts_audit_opinion.add_argument(
        "--universe-file", type=Path, default=DEFAULT_FACTOR_UNIVERSE
    )
    ts_audit_opinion.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    ts_audit_opinion.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted 5,451-call sequential licensed request",
    )

    ts_gross_margin = subparsers.add_parser(
        "sync-tushare-gross-margin",
        help="download the frozen 2018-2025 initial gross-margin-change snapshot",
    )
    ts_gross_margin.add_argument(
        "--universe-file", type=Path, default=DEFAULT_FACTOR_UNIVERSE
    )
    ts_gross_margin.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    ts_gross_margin.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted 10,902-call sequential licensed request",
    )

    ts_cash_conversion = subparsers.add_parser(
        "sync-tushare-cash-conversion",
        help="download the frozen 2019-2025 PIT accounting cash-conversion snapshot",
    )
    ts_cash_conversion.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted 9,588-call sequential licensed request",
    )

    ts_free_float_acceptance = subparsers.add_parser(
        "acceptance-tushare-free-float-scarcity",
        help="run the frozen completed-session structural free-float acceptance",
    )
    ts_free_float_acceptance.add_argument(
        "--universe-file", type=Path, default=DEFAULT_BUYABLE_UNIVERSE
    )

    eastmoney_balance_acceptance = subparsers.add_parser(
        "acceptance-eastmoney-balance-sheet-resilience",
        help="run the frozen public quarterly balance-sheet resilience acceptance",
    )
    eastmoney_balance_acceptance.add_argument(
        "--universe-file", type=Path, default=DEFAULT_BUYABLE_UNIVERSE
    )

    eastmoney_core_profit_acceptance = subparsers.add_parser(
        "acceptance-eastmoney-core-profit-consistency",
        help="run the frozen public quarterly core-profit consistency acceptance",
    )
    eastmoney_core_profit_acceptance.add_argument(
        "--universe-file", type=Path, default=DEFAULT_BUYABLE_UNIVERSE
    )

    eastmoney_balance_full = subparsers.add_parser(
        "sync-eastmoney-balance-sheet-resilience",
        help="download the frozen 2019-2025 quarterly balance-sheet snapshot",
    )
    eastmoney_balance_full.add_argument(
        "--universe-file", type=Path, default=DEFAULT_BUYABLE_UNIVERSE
    )
    eastmoney_balance_full.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted one-shot 27-partition public request",
    )

    eastmoney_core_profit_full = subparsers.add_parser(
        "sync-eastmoney-core-profit-consistency",
        help="download the frozen 2019-2025 quarterly core-profit snapshot",
    )
    eastmoney_core_profit_full.add_argument(
        "--universe-file", type=Path, default=DEFAULT_BUYABLE_UNIVERSE
    )
    eastmoney_core_profit_full.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted one-shot 27-partition public request",
    )

    ts_free_float = subparsers.add_parser(
        "sync-tushare-free-float-scarcity",
        help="download the frozen 2019-2025 structural free-float snapshot",
    )
    ts_free_float.add_argument(
        "--universe-file", type=Path, default=DEFAULT_BUYABLE_UNIVERSE
    )
    ts_free_float.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    ts_free_float.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted 1699-call sequential licensed request",
    )

    ts_daily_pb_acceptance = subparsers.add_parser(
        "acceptance-tushare-daily-pb",
        help="run the frozen completed-session positive book-to-market acceptance",
    )
    ts_daily_pb_acceptance.add_argument(
        "--universe-file", type=Path, default=DEFAULT_BUYABLE_UNIVERSE
    )

    subparsers.add_parser(
        "acceptance-tushare-sw-industry-breadth",
        help="run the frozen no-price SW2021 L1 classification and interval probe",
    )

    ts_sw_membership = subparsers.add_parser(
        "sync-tushare-sw-industry-membership",
        help="download the frozen 31-code by two-state SW2021 L1 membership snapshot",
    )
    ts_sw_membership.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted and preregistered 62-call licensed request",
    )

    ts_daily_pb = subparsers.add_parser(
        "sync-tushare-daily-pb",
        help="download the frozen 2019-2025 Tushare positive book-to-market snapshot",
    )
    ts_daily_pb.add_argument(
        "--universe-file", type=Path, default=DEFAULT_BUYABLE_UNIVERSE
    )
    ts_daily_pb.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    ts_daily_pb.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the licensed full-universe multi-year request after acceptance and preregistration",
    )

    jq_moneyflow_acceptance = subparsers.add_parser(
        "acceptance-jqdata-moneyflow",
        help="verify JQData professional daily moneyflow entitlement on four frozen symbols",
    )
    jq_moneyflow_acceptance.add_argument(
        "--date", type=parse_date, default=latest_completed_session_date()
    )

    jq_moneyflow = subparsers.add_parser(
        "sync-jqdata-moneyflow",
        help="download the frozen 2019-2025 JQData professional daily moneyflow snapshot",
    )
    jq_moneyflow.add_argument(
        "--universe-file", type=Path, default=DEFAULT_FACTOR_UNIVERSE
    )
    jq_moneyflow.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    jq_moneyflow.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the licensed full-universe multi-year request after acceptance passes",
    )

    alignment = subparsers.add_parser(
        "confirm-minute-alignment",
        help="write a separate timestamp/volume confirmation for an accepted 1m snapshot",
    )
    alignment.add_argument("--manifest", type=Path, required=True)
    alignment.add_argument("--bar-label", choices=("start", "end"), required=True)
    alignment.add_argument("--volume-unit", choices=("shares", "lots"), required=True)
    alignment.add_argument(
        "--reviewed-boundaries",
        action="store_true",
        help="confirm the acceptance snapshot's first/last bars were reviewed",
    )
    alignment.add_argument("--output", type=Path)

    features = subparsers.add_parser(
        "build-minute-features",
        help="build the frozen close-known v1 minute features from a confirmed 1m snapshot",
    )
    features.add_argument("--manifest", type=Path, required=True)
    features.add_argument("--alignment", type=Path, required=True)
    features.add_argument(
        "--factor-spec", type=Path, default=DEFAULT_MINUTE_FACTOR_SPEC
    )
    features.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the rich-data CLI."""

    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            print(
                json.dumps(
                    status_payload(args.data_root),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "sync-minutes":
            manifest = sync_minutes(
                args.provider,
                args.symbols,
                args.start,
                args.end,
                args.frequency,
                args.allow_large,
            )
        elif args.command == "acceptance":
            manifest = sync_minutes(
                args.provider,
                args.symbols,
                args.date,
                args.date,
                args.frequency,
                False,
                acceptance=True,
            )
        elif args.command == "acceptance-baostock-5m":
            manifest = sync_baostock_5m_acceptance()
        elif args.command == "preflight-baostock-5m":
            manifest = write_baostock_5m_preflight(
                data_root=args.data_root,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
        elif args.command == "probe-baostock-5m-restoration":
            manifest = probe_baostock_5m_restoration(data_root=args.data_root)
        elif args.command == "sync-baostock-5m":
            manifest = sync_baostock_5m_history(
                allow_large=args.allow_large,
                data_root=args.data_root,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
                workers=args.workers,
            )
        elif args.command == "sync-tushare-events":
            datasets = [
                item.strip() for item in args.datasets.split(",") if item.strip()
            ]
            manifest = sync_tushare_events(
                datasets, args.start, args.end, args.allow_large
            )
        elif args.command == "sync-tushare-moneyflow":
            manifest = sync_tushare_moneyflow(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
        elif args.command == "acceptance-tushare-northbound-top10":
            manifest = sync_tushare_northbound_top10_acceptance()
        elif args.command == "acceptance-tushare-top-inst":
            manifest = sync_tushare_top_inst_acceptance()
        elif args.command == "acceptance-tushare-top10-float-concentration":
            manifest = sync_tushare_top10_float_concentration_acceptance()
        elif args.command == "acceptance-tushare-cash-conversion":
            manifest = sync_tushare_cash_conversion_acceptance()
        elif args.command == "acceptance-tushare-earnings-forecast":
            manifest = sync_tushare_earnings_forecast_acceptance()
        elif args.command == "acceptance-tushare-disclosure-promptness":
            manifest = sync_tushare_disclosure_promptness_acceptance()
        elif args.command == "acceptance-tushare-audit-opinion":
            manifest = sync_tushare_audit_opinion_acceptance()
        elif args.command == "acceptance-tushare-gross-margin":
            manifest = sync_tushare_gross_margin_acceptance()
        elif args.command == "acceptance-tushare-management-continuity":
            manifest = sync_tushare_management_continuity_acceptance()
        elif args.command == "sync-tushare-stock-st-membership":
            manifest = sync_tushare_stock_st_membership(
                allow_large=args.allow_large,
                calendar_path=args.calendar_file,
            )
        elif args.command == "sync-tushare-audit-opinions":
            manifest = sync_tushare_audit_opinions(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
        elif args.command == "sync-tushare-gross-margin":
            manifest = sync_tushare_gross_margin(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
        elif args.command == "sync-tushare-cash-conversion":
            manifest = sync_tushare_cash_conversion(allow_large=args.allow_large)
        elif args.command == "acceptance-tushare-free-float-scarcity":
            manifest = sync_tushare_free_float_scarcity_acceptance(
                universe_path=args.universe_file
            )
        elif args.command == "acceptance-eastmoney-balance-sheet-resilience":
            manifest = sync_eastmoney_balance_sheet_resilience_acceptance(
                universe_path=args.universe_file
            )
        elif args.command == "acceptance-eastmoney-core-profit-consistency":
            manifest = sync_eastmoney_core_profit_consistency_acceptance(
                universe_path=args.universe_file
            )
        elif args.command == "sync-eastmoney-balance-sheet-resilience":
            manifest = sync_eastmoney_balance_sheet_resilience(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
            )
        elif args.command == "sync-eastmoney-core-profit-consistency":
            manifest = sync_eastmoney_core_profit_consistency(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
            )
        elif args.command == "sync-tushare-free-float-scarcity":
            manifest = sync_tushare_free_float_scarcity(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
        elif args.command == "acceptance-tushare-daily-pb":
            manifest = sync_tushare_daily_pb_acceptance(
                universe_path=args.universe_file
            )
        elif args.command == "acceptance-tushare-sw-industry-breadth":
            manifest = sync_tushare_sw_industry_breadth_acceptance()
        elif args.command == "sync-tushare-sw-industry-membership":
            manifest = sync_tushare_sw_industry_membership(allow_large=args.allow_large)
        elif args.command == "sync-tushare-daily-pb":
            manifest = sync_tushare_daily_pb(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
        elif args.command == "acceptance-jqdata-moneyflow":
            manifest = sync_jqdata_moneyflow(acceptance_date=args.date)
        elif args.command == "sync-jqdata-moneyflow":
            manifest = sync_jqdata_moneyflow(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
        elif args.command == "confirm-minute-alignment":
            manifest = confirm_minute_alignment(
                args.manifest,
                bar_label=args.bar_label,
                volume_unit=args.volume_unit,
                reviewed_boundaries=args.reviewed_boundaries,
                output=args.output,
            )
        elif args.command == "build-minute-features":
            manifest = build_minute_features(
                args.manifest,
                args.alignment,
                factor_spec_path=args.factor_spec,
                output=args.output,
            )
        else:  # pragma: no cover - argparse enforces the known subcommands.
            raise RichDataError(f"unknown command: {args.command}")
    except RichDataError as exc:
        print(f"error: {exc}")
        return 2
    command_status = {
        "confirm-minute-alignment": "stored_alignment_confirmation",
        "build-minute-features": "stored_research_features",
        "acceptance-jqdata-moneyflow": "stored_entitlement_acceptance",
        "acceptance-baostock-5m": "stored_five_minute_acceptance",
        "preflight-baostock-5m": "stored_no_network_preflight",
        "probe-baostock-5m-restoration": "stored_provider_restoration_probe",
        "sync-baostock-5m": "stored_pending_no_return_feature_materialization",
        "sync-jqdata-moneyflow": "stored_pending_no_return_capacity",
        "sync-tushare-moneyflow": "stored_pending_no_return_capacity",
        "sync-tushare-daily-pb": "stored_pending_no_return_uniqueness_and_capacity",
        "acceptance-tushare-free-float-scarcity": (
            "stored_no_return_structural_free_float_acceptance"
        ),
        "acceptance-eastmoney-balance-sheet-resilience": (
            "stored_no_return_public_balance_sheet_acceptance"
        ),
        "acceptance-eastmoney-core-profit-consistency": (
            "stored_no_return_public_core_profit_acceptance"
        ),
        "sync-eastmoney-balance-sheet-resilience": (
            "stored_pending_no_return_capacity_and_uniqueness"
        ),
        "sync-eastmoney-core-profit-consistency": (
            "stored_pending_no_return_capacity_and_uniqueness"
        ),
        "sync-tushare-free-float-scarcity": (
            "stored_pending_no_return_capacity_and_uniqueness"
        ),
        "acceptance-tushare-top-inst": (
            "stored_no_return_entitlement_and_top_list_acceptance"
        ),
        "acceptance-tushare-top10-float-concentration": (
            "stored_no_return_ownership_concentration_acceptance"
        ),
        "acceptance-tushare-cash-conversion": (
            "stored_no_return_accounting_cash_conversion_acceptance"
        ),
        "acceptance-tushare-earnings-forecast": (
            "stored_no_return_earnings_forecast_acceptance"
        ),
        "acceptance-tushare-disclosure-promptness": (
            "stored_no_return_disclosure_promptness_acceptance"
        ),
        "acceptance-tushare-audit-opinion": (
            "stored_no_return_audit_opinion_acceptance"
        ),
        "acceptance-tushare-gross-margin": (
            "stored_no_return_initial_gross_margin_acceptance"
        ),
        "acceptance-tushare-management-continuity": (
            "stored_no_return_management_continuity_acceptance"
        ),
        "sync-tushare-stock-st-membership": (
            "stored_pending_no_return_st_recovery_capacity_and_uniqueness"
        ),
        "sync-tushare-audit-opinions": (
            "stored_pending_no_return_audit_opinion_capacity_and_uniqueness"
        ),
        "sync-tushare-gross-margin": (
            "stored_pending_no_return_gross_margin_capacity_and_uniqueness"
        ),
        "sync-tushare-cash-conversion": (
            "stored_pending_no_return_cash_conversion_capacity_and_uniqueness"
        ),
        "acceptance-tushare-sw-industry-breadth": (
            "stored_no_price_membership_acceptance"
        ),
        "sync-tushare-sw-industry-membership": (
            "stored_pending_no_return_factor_capacity_and_uniqueness"
        ),
    }.get(args.command, "stored_pending_acceptance")
    print(
        json.dumps(
            {"manifest": str(manifest), "status": command_status}, ensure_ascii=False
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

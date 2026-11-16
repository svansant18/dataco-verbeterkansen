"""Streamlit-side data access: one cached pipeline run and one shared filter contract.

No business logic lives here: filtering and KPIs come from analysis.kpis, the data from pipeline.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from analysis.kpis import Filters, apply_filters, delivery_kpis, financial_kpis, priority_table
from pipeline import RAW_FILENAME, PipelineResult, run_pipeline

ROOT = Path(__file__).resolve().parents[1]
ALL_MARKETS = "Alle markten"
ALL_CATEGORIES = "Alle categorieën"


def raw_csv_path() -> Path | None:
    """data/raw bevat meerdere CSV's (o.a. de omschrijving en de access logs): we gebruiken enkel de hoofdset."""
    path = ROOT / "data" / "raw" / RAW_FILENAME
    return path if path.is_file() else None


@st.cache_resource(show_spinner="Pipeline draait op de brondata (read-only)…")
def _cached_result(path_str: str, modified_ns: int) -> PipelineResult:
    _ = modified_ns  # a changed file invalidates the cache
    return run_pipeline(Path(path_str))


def get_result() -> PipelineResult | None:
    path = raw_csv_path()
    if path is None:
        return None
    return _cached_result(str(path), path.stat().st_mtime_ns)


def current_filters() -> Filters:
    market = st.session_state.get("global_market", ALL_MARKETS)
    category = st.session_state.get("global_category", ALL_CATEGORIES)
    period = st.session_state.get("global_period")
    d_from = d_to = None
    if isinstance(period, (tuple, list)) and len(period) == 2:
        d_from, d_to = pd.Timestamp(period[0]), pd.Timestamp(period[1])
    return Filters(
        market=None if market == ALL_MARKETS else market,
        category=None if category == ALL_CATEGORIES else category,
        date_from=d_from, date_to=d_to,
    )


@dataclass(frozen=True)
class Scope:
    result: PipelineResult
    filters: Filters
    fin: pd.DataFrame   # order lines, in scope, after filters
    ocs: pd.DataFrame   # order x market x category, after filters

    @property
    def empty(self) -> bool:
        return self.fin.empty


def get_scope() -> Scope | None:
    result = get_result()
    if result is None:
        return None
    f = current_filters()
    return Scope(
        result=result, filters=f,
        fin=apply_filters(result.financial_rows, f),
        ocs=apply_filters(result.order_category_shipping, f),
    )


def compute_priorities(scope: Scope):
    """DV4 reuses the DV1 and DV2 aggregates of the SAME filtered scope (no parallel formulas)."""
    keys = ["Market", "Category Name"]
    fin_kpi = financial_kpis(scope.fin, keys)
    del_kpi = delivery_kpis(scope.ocs, keys)
    table, refs = priority_table(fin_kpi, del_kpi)
    return table, refs, fin_kpi, del_kpi


def filter_options(result: PipelineResult) -> tuple[list[str], list[str], date, date]:
    fin = result.financial_rows
    markets = sorted(fin["Market"].unique())
    categories = sorted(fin["Category Name"].unique())
    return markets, categories, fin["order_date"].min().date(), fin["order_date"].max().date()

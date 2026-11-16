"""Streamlit-side data access: one cached pipeline run and one shared filter contract.

No business logic lives here: filtering and KPIs come from analysis.kpis, the data from pipeline.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from analysis.kpis import Filters, apply_filters, prioritize_selection
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


def processed_provenance() -> list[dict]:
    """Provenance manifests of processed versions (metadata only, no rows)."""
    out = []
    for meta in sorted((ROOT / "data" / "processed").glob("*.provenance.json")):
        try:
            out.append(json.loads(meta.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out


def processed_for(result: PipelineResult) -> dict | None:
    """Latest financial_lines provenance whose source hash equals the raw hash in use."""
    for prov in reversed(processed_provenance()):
        if prov.get("processed_file", "").startswith("dataco_financial_lines") and prov.get("source_sha256") == result.source_manifest["source_sha256"]:
            return prov
    return None


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
    fin: pd.DataFrame      # orderregels in de analysebasis, na alle filters
    ocs: pd.DataFrame      # order x markt x categorie, na alle filters
    ctx_fin: pd.DataFrame  # idem, maar enkel gefilterd op periode (voor de vaste referentie van DV4)
    ctx_ocs: pd.DataFrame

    @property
    def empty(self) -> bool:
        return self.fin.empty


def get_scope() -> Scope | None:
    result = get_result()
    if result is None:
        return None
    f = current_filters()
    period = Filters(date_from=f.date_from, date_to=f.date_to)
    ctx_fin = apply_filters(result.financial_rows, period)
    ctx_ocs = apply_filters(result.order_category_shipping, period)
    selection = Filters(market=f.market, category=f.category)
    return Scope(
        result=result, filters=f,
        fin=apply_filters(ctx_fin, selection), ocs=apply_filters(ctx_ocs, selection),
        ctx_fin=ctx_fin, ctx_ocs=ctx_ocs,
    )


def compute_priorities(scope: Scope):
    """DV4 en Overview: klassen met een vaste referentie; markt en categorie zoomen alleen in (zie prioritize_selection)."""
    return prioritize_selection(scope.ctx_fin, scope.ctx_ocs, market=scope.filters.market, category=scope.filters.category)


def filter_options(result: PipelineResult) -> tuple[list[str], list[str], date, date]:
    fin = result.financial_rows
    markets = sorted(fin["Market"].unique())
    categories = sorted(fin["Category Name"].unique())
    return markets, categories, fin["order_date"].min().date(), fin["order_date"].max().date()

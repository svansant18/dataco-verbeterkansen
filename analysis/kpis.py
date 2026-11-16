"""DataCo-KPI's: pure pandas-functies, zonder Streamlit.

Omzet, winst en marge (DV1), % vertraagde orders (DV2), korting en marge (DV3) en de
prioriteitsregel (DV4). De keuzes erachter staan in beslissingslogboek.md (D-006 t/m D-011).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIN_ORDERS = 30  # D-010: minimum unique eligible orders per market x category
# D-009 (approved by the student on 2026-11-16, logboek #9): discount classes on the 0-1 fraction.
DISCOUNT_BINS = (-0.0001, 0.0, 0.05, 0.10, 0.20, 1.0)
DISCOUNT_LABELS = ("0%", ">0-5%", ">5-10%", ">10-20%", ">20%")
REVENUE_COL = "Order Item Total"   # net of discount: profit ratio in the source is based on it
PROFIT_COL = "Order Profit Per Order"  # line-level profit (verified: varies within an order)

PRIORITY_ORDER = ("Prioriteit", "Optimaliseren", "Monitoren", "Sterk", "Onvoldoende data")


@dataclass(frozen=True)
class Filters:
    market: str | None = None       # None = all
    category: str | None = None
    date_from: pd.Timestamp | None = None
    date_to: pd.Timestamp | None = None   # inclusive, whole day

    def as_pairs(self) -> tuple[tuple[str, str], ...]:
        return (
            ("Markt", self.market or "Alle"),
            ("Categorie", self.category or "Alle"),
            ("Periode", f"{self.date_from.date() if self.date_from is not None else 'begin'} t/m {self.date_to.date() if self.date_to is not None else 'einde'}"),
        )


def apply_filters(df: pd.DataFrame, f: Filters, *, date_col: str = "order_date") -> pd.DataFrame:
    """One filter contract shared by every KPI, chart and table (filter consistency)."""
    mask = pd.Series(True, index=df.index)
    if f.market:
        mask &= df["Market"].eq(f.market)
    if f.category:
        mask &= df["Category Name"].eq(f.category)
    if f.date_from is not None:
        mask &= df[date_col] >= f.date_from
    if f.date_to is not None:
        mask &= df[date_col] < (f.date_to + pd.Timedelta(days=1))
    return df[mask]


def financial_kpis(df: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Revenue, profit, weighted margin (= sum profit / sum revenue), lines and unique orders.

    The margin is NEVER a mean of line margins; a zero revenue gives NaN (N/B).
    """
    keys = by or []
    if keys:
        g = df.groupby(keys, observed=True)
        out = g.agg(revenue=(REVENUE_COL, "sum"), profit=(PROFIT_COL, "sum"), gross_sales=("Sales", "sum"),
                    lines=("Order Item Id", "size"), orders=("Order Id", "nunique")).reset_index()
    else:
        out = pd.DataFrame([{
            "revenue": df[REVENUE_COL].sum(), "profit": df[PROFIT_COL].sum(), "gross_sales": df["Sales"].sum(),
            "lines": len(df), "orders": df["Order Id"].nunique(),
        }])
    out["margin_pct"] = np.where(out["revenue"] > 0, 100 * out["profit"] / out["revenue"].where(out["revenue"] > 0), np.nan)
    return out


def delivery_kpis(ocs: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Late % = late eligible orders / eligible orders; each order counted once per group (D-008).

    Canceled shipments are removed from the denominator and reported separately.
    """
    keys = by or []
    eligible = ocs[ocs["delivery_eligible"]]
    late = eligible[eligible["is_late"]]
    if keys:
        parts = [
            ocs.groupby(keys, observed=True)["Order Id"].nunique().rename("orders_all"),
            eligible.groupby(keys, observed=True)["Order Id"].nunique().rename("eligible_orders"),
            late.groupby(keys, observed=True)["Order Id"].nunique().rename("late_orders"),
        ]
        out = pd.concat(parts, axis=1).fillna(0).reset_index()
    else:
        out = pd.DataFrame([{
            "orders_all": ocs["Order Id"].nunique(),
            "eligible_orders": eligible["Order Id"].nunique(),
            "late_orders": late["Order Id"].nunique(),
        }])
    out[["orders_all", "eligible_orders", "late_orders"]] = out[["orders_all", "eligible_orders", "late_orders"]].astype(int)
    out["excluded_orders"] = out["orders_all"] - out["eligible_orders"]
    out["late_pct"] = np.where(out["eligible_orders"] > 0, 100 * out["late_orders"] / out["eligible_orders"].where(out["eligible_orders"] > 0), np.nan)
    return out


def discount_class(rate: pd.Series) -> pd.Series:
    """Discount fraction (0-1) -> ordered class label."""
    return pd.cut(rate, bins=list(DISCOUNT_BINS), labels=list(DISCOUNT_LABELS), include_lowest=True)


def margin_by_discount_class(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.assign(discount_class=discount_class(df["Order Item Discount Rate"]))
    return financial_kpis(tmp, ["discount_class"]).sort_values("discount_class").reset_index(drop=True)


def discount_margin_correlation(df: pd.DataFrame) -> dict[str, float | int | None]:
    """Descriptive association on line grain; n shown, no causal claim."""
    line = df.loc[df[REVENUE_COL] > 0, ["Order Item Discount Rate", PROFIT_COL, REVENUE_COL]]
    n = len(line)
    if n < 3 or line["Order Item Discount Rate"].nunique() < 2:
        return {"n": n, "pearson": None, "spearman": None}
    margin = line[PROFIT_COL] / line[REVENUE_COL]
    rate = line["Order Item Discount Rate"]
    # Spearman = Pearson op de rangen (gemiddelde rang bij gelijke waarden). Zo hoeft scipy niet geïnstalleerd te zijn:
    # pandas' corr(method="spearman") importeert scipy.stats, dat niet in requirements.txt staat.
    spearman = rate.rank(method="average").corr(margin.rank(method="average"))
    return {"n": n, "pearson": float(rate.corr(margin)), "spearman": float(spearman)}


def deterministic_sample(df: pd.DataFrame, n: int = 5000, seed: int = 42) -> pd.DataFrame:
    return df if len(df) <= n else df.sample(n=n, random_state=seed)


def priority_table(fin_kpi: pd.DataFrame, del_kpi: pd.DataFrame, *, min_orders: int = MIN_ORDERS) -> tuple[pd.DataFrame, dict[str, float | None]]:
    """DV4: transparent rules on DV1 + DV2 outputs only (D-010, spec proposal approved).

    Reference margin / late % = weighted totals of the same filtered scope. A segment needs
    >= min_orders eligible orders AND a known margin. 'Hoog volume' = revenue >= median of the
    segments that qualify.
    """
    keys = ["Market", "Category Name"]
    table = fin_kpi.merge(del_kpi[keys + ["eligible_orders", "late_orders", "late_pct"]], on=keys, how="inner")
    ref_margin = None if fin_kpi["revenue"].sum() <= 0 else 100 * fin_kpi["profit"].sum() / fin_kpi["revenue"].sum()
    ref_late = None if del_kpi["eligible_orders"].sum() <= 0 else 100 * del_kpi["late_orders"].sum() / del_kpi["eligible_orders"].sum()
    enough = (table["eligible_orders"] >= min_orders) & table["margin_pct"].notna() & table["late_pct"].notna()
    median_rev = table.loc[enough, "revenue"].median() if enough.any() else np.nan
    table["enough_data"] = enough
    table["high_volume"] = enough & (table["revenue"] >= median_rev)
    table["low_margin"] = enough & (table["margin_pct"] < ref_margin) if ref_margin is not None else False
    table["high_late"] = enough & (table["late_pct"] > ref_late) if ref_late is not None else False

    def label(r: pd.Series) -> tuple[str, str]:
        if not r["enough_data"]:
            return "Onvoldoende data", f"minder dan {min_orders} in aanmerking komende orders of onbekende marge"
        if r["high_volume"] and r["low_margin"] and r["high_late"]:
            return "Prioriteit", "hoge omzet, marge onder referentie én vertraging boven referentie"
        if r["high_late"]:
            return "Optimaliseren", "vertraging boven referentie"
        if r["low_margin"]:
            return "Monitoren", "marge onder referentie"
        return "Sterk", "geen duidelijke risicocombinatie"

    labelled = table.apply(label, axis=1, result_type="expand")
    table["priority"], table["reason"] = labelled[0], labelled[1]
    table["priority_rank"] = table["priority"].map({p: i for i, p in enumerate(PRIORITY_ORDER)})
    # deterministic: class, revenue desc, market, category
    table = table.sort_values(["priority_rank", "revenue", "Market", "Category Name"], ascending=[True, False, True, True]).reset_index(drop=True)
    refs = {"ref_margin_pct": ref_margin, "ref_late_pct": ref_late, "median_revenue_qualifying": None if np.isnan(median_rev) else float(median_rev), "min_orders": min_orders}
    return table, refs

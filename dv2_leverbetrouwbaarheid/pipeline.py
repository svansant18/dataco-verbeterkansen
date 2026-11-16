"""DV2 - Leverbetrouwbaarheid: percentage vertraagde unieke orders per markt en productcategorie.

Pure functies, geen Streamlit-imports. Leest enkel de verwerkte data uit `data/processed/`
(gemaakt door `pipeline_dataco`; geannuleerde en fraude-orders zijn daar al uitgesloten).

Afspraken:
- eenheid is de **unieke order** (`Order Id`), niet de orderlijn;
- vertraagd = `Late_delivery_risk` = 1 (= Delivery Status "Late delivery");
- per categorie telt een order mee in **elke** categorie die erin zit (de som over categorieën is dus
  groter dan het aantal orders).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PATH = ROOT / "data" / "processed" / "dataco_clean.csv"

# ruwe kolomnaam -> naam in deze analyse
KOLOMMEN = {
    "Order Id": "order_id",
    "Order Item Id": "orderlijn_id",
    "Market": "markt",
    "Category Name": "categorie",
    "Shipping Mode": "verzendmethode",
    "Late_delivery_risk": "vertraagd",
    "Delivery Status": "leverstatus",
    "Days for shipping (real)": "dagen_werkelijk",
    "Days for shipment (scheduled)": "dagen_gepland",
}

# Onder dit aantal orders markeren we een percentage als weinig betrouwbaar (waarschuwing, geen filter).
MIN_ORDERS = 30


@dataclass
class StapInfo:
    naam: str
    rijen_in: int
    rijen_uit: int
    reden: str
    voorbeeld: pd.DataFrame

    @property
    def rijen_weggevallen(self) -> int:
        return self.rijen_in - self.rijen_uit


@dataclass
class DV2Resultaat:
    stappen: list[StapInfo]
    totaal: dict[str, float]
    per_markt: pd.DataFrame
    per_categorie: pd.DataFrame
    per_combinatie: pd.DataFrame
    per_verzendmethode: pd.DataFrame
    per_markt_verzendmethode: pd.DataFrame


def samenvatten(df: pd.DataFrame, groep: list[str]) -> pd.DataFrame:
    """Aantal orders, vertraagde orders en percentage vertraagd per groep, meeste orders eerst.

    `df` heeft één rij per order (of per order-categorie bij groepering op categorie).
    """
    tabel = (
        df.groupby(groep)
        .agg(orders=("order_id", "size"), vertraagd=("vertraagd", "sum"))
        .reset_index()
    )
    tabel["pct_vertraagd"] = tabel["vertraagd"] / tabel["orders"]
    tabel["weinig_data"] = tabel["orders"] < MIN_ORDERS
    return tabel.sort_values("orders", ascending=False).reset_index(drop=True)


def load_processed(pad: Path = PROCESSED_PATH) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 1: lees enkel de nodige kolommen uit de verwerkte CSV."""
    if not pad.exists():
        raise FileNotFoundError(
            f"{pad} bestaat niet. Start `pipeline_dataco` en klik op 'Sla verwerkte data op als CSV'."
        )
    df = pd.read_csv(pad, usecols=list(KOLOMMEN)).rename(columns=KOLOMMEN)
    reden = (
        f"Enkel de {len(KOLOMMEN)} nodige kolommen ingelezen uit `data/processed/dataco_clean.csv`: "
        + ", ".join(f"{oud} → {nieuw}" for oud, nieuw in KOLOMMEN.items())
        + ". Geen rijen verwijderd."
    )
    return df, StapInfo("1. Inlezen", len(df), len(df), reden, df.head(5))


def check_input(df: pd.DataFrame) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 2: controleer de aannames waarop het ontdubbelen per order steunt. Faalt luid als er iets niet klopt."""
    per_order = df.groupby("order_id")
    controles = {
        "Geen lege waarden": int(df.isna().sum().sum()) == 0,
        "Vertraagd is overal 0 of 1": bool(df["vertraagd"].isin([0, 1]).all()),
        "Elke order heeft één waarde voor vertraagd": bool((per_order["vertraagd"].nunique() == 1).all()),
        "Elke order hoort bij één markt": bool((per_order["markt"].nunique() == 1).all()),
        "Elke order heeft één verzendmethode": bool((per_order["verzendmethode"].nunique() == 1).all()),
        "Geen 'Shipping canceled' meer (al uitgesloten)": bool((df["leverstatus"] != "Shipping canceled").all()),
        "Vertraagd = werkelijke dagen > geplande dagen": bool(
            (df["vertraagd"] == (df["dagen_werkelijk"] > df["dagen_gepland"]).astype(int)).all()
        ),
    }
    mislukt = [naam for naam, ok in controles.items() if not ok]
    if mislukt:
        raise ValueError("Controle mislukt: " + "; ".join(mislukt))
    reden = "Alle controles geslaagd, niets gewijzigd: " + "; ".join(controles) + "."
    return df, StapInfo("2. Controleren", len(df), len(df), reden, df.head(5))


def to_orders(df: pd.DataFrame) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 3: één rij per unieke order. Een order heeft tot 5 orderlijnen met dezelfde levering."""
    orders = df.drop_duplicates("order_id")[["order_id", "markt", "verzendmethode", "vertraagd"]].reset_index(drop=True)
    reden = (
        f"Ontdubbeld op `order_id`: {len(df):,} orderlijnen worden {len(orders):,} unieke orders. ".replace(",", ".")
        + "Dit is nodig omdat de levering per order geldt; tellen op lijnen zou orders met veel lijnen "
        "zwaarder laten meewegen. Markt, verzendmethode en vertraagd zijn per order gecontroleerd (stap 2)."
    )
    return orders, StapInfo("3. Naar orders", len(df), len(orders), reden, orders.head(5))


def to_order_categorie(df: pd.DataFrame) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 4: één rij per order en categorie. Een order telt mee in elke categorie die erin zit."""
    paren = df.drop_duplicates(["order_id", "categorie"])[["order_id", "markt", "categorie", "vertraagd"]]
    paren = paren.reset_index(drop=True)
    meerdere = int((df.groupby("order_id")["categorie"].nunique() > 1).sum())
    reden = (
        f"Ontdubbeld op order en categorie: {len(df):,} orderlijnen worden {len(paren):,} paren van order en categorie. ".replace(",", ".")
        + f"{meerdere:,} orders bevatten meer dan één categorie en tellen in elk daarvan mee, ".replace(",", ".")
        + "dus de som over categorieën is groter dan het aantal unieke orders. Alleen voor de categorie-analyse."
    )
    return paren, StapInfo("4. Order x categorie", len(df), len(paren), reden, paren.head(5))


def run_dv2(pad: Path = PROCESSED_PATH) -> DV2Resultaat:
    """Draai alle stappen van DV2."""
    df, info1 = load_processed(pad)
    df, info2 = check_input(df)
    orders, info3 = to_orders(df)
    paren, info4 = to_order_categorie(df)

    combinatie = samenvatten(paren, ["markt", "categorie"])
    return DV2Resultaat(
        stappen=[info1, info2, info3, info4],
        totaal={
            "orders": len(orders),
            "vertraagd": int(orders["vertraagd"].sum()),
            "pct_vertraagd": float(orders["vertraagd"].mean()),
        },
        per_markt=samenvatten(orders, ["markt"]),
        per_categorie=samenvatten(paren, ["categorie"]),
        per_combinatie=combinatie,
        per_verzendmethode=samenvatten(orders, ["verzendmethode"]),
        per_markt_verzendmethode=samenvatten(orders, ["markt", "verzendmethode"]),
    )

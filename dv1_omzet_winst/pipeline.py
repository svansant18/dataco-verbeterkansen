"""DV1 - Omzet en winst per markt en productcategorie.

Pure functies, geen Streamlit-imports. Leest enkel de verwerkte data uit `data/processed/`
(gemaakt door `pipeline_dataco`, stap 1 t/m 4).

Beslissingen (zie beslissingslogboek.md):
- omzet = `Order Item Total` (na korting)
- winst = `Order Profit Per Order`
- marge = som(winst) / som(omzet): gewogen marge, niet het gemiddelde van de marge per orderlijn
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PATH = ROOT / "data" / "processed" / "dataco_clean.csv"

# ruwe kolomnaam -> naam in deze analyse
KOLOMMEN = {
    "Market": "markt",
    "Category Name": "categorie",
    "Order Id": "order_id",
    "Order Item Id": "orderlijn_id",
    "Order Item Total": "omzet",
    "Order Profit Per Order": "winst",
}

# Onder dit aantal orderlijnen markeren we een marge als weinig betrouwbaar (enkel een waarschuwing, geen filter).
MIN_LIJNEN = 30


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
class DV1Resultaat:
    stappen: list[StapInfo]
    totaal: dict[str, float]
    per_markt: pd.DataFrame
    per_categorie: pd.DataFrame
    per_combinatie: pd.DataFrame


def samenvatten(df: pd.DataFrame, groep: list[str]) -> pd.DataFrame:
    """Omzet, winst, gewogen marge, orderlijnen en unieke orders per groep, grootste omzet eerst."""
    tabel = (
        df.groupby(groep)
        .agg(
            omzet=("omzet", "sum"),
            winst=("winst", "sum"),
            orderlijnen=("orderlijn_id", "size"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
    )
    tabel["marge"] = tabel["winst"] / tabel["omzet"]
    tabel["weinig_data"] = tabel["orderlijnen"] < MIN_LIJNEN
    return tabel.sort_values("omzet", ascending=False).reset_index(drop=True)


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
    """Stap 2: controleer de aannames waarop de berekening steunt. Faalt luid als er iets niet klopt."""
    controles = {
        "Geen lege waarden": int(df.isna().sum().sum()) == 0,
        "Elke orderlijn komt één keer voor": df["orderlijn_id"].is_unique,
        "Omzet is overal groter dan 0": bool((df["omzet"] > 0).all()),
        "Elke order hoort bij precies één markt": bool((df.groupby("order_id")["markt"].nunique() == 1).all()),
    }
    mislukt = [naam for naam, ok in controles.items() if not ok]
    if mislukt:
        raise ValueError("Controle mislukt: " + "; ".join(mislukt))
    reden = "Alle controles geslaagd, niets gewijzigd: " + "; ".join(controles) + "."
    return df, StapInfo("2. Controleren", len(df), len(df), reden, df.head(5))


def aggregate_markt_categorie(df: pd.DataFrame) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 3: samenvatten per markt x categorie. Elke rij is dan een combinatie, geen orderlijn meer."""
    tabel = samenvatten(df, ["markt", "categorie"])
    aantal_weinig = int(tabel["weinig_data"].sum())
    reden = (
        f"{len(df):,} orderlijnen samengevat tot {len(tabel)} combinaties van markt en categorie. ".replace(",", ".")
        + "Marge = som(winst) / som(omzet). "
        + f"{aantal_weinig} combinaties hebben minder dan {MIN_LIJNEN} orderlijnen en krijgen een waarschuwing "
        "(ze blijven wel in de resultaten)."
    )
    return tabel, StapInfo("3. Samenvatten", len(df), len(tabel), reden, tabel.head(5))


def run_dv1(pad: Path = PROCESSED_PATH) -> DV1Resultaat:
    """Draai alle stappen van DV1."""
    df, info1 = load_processed(pad)
    df, info2 = check_input(df)
    combinatie, info3 = aggregate_markt_categorie(df)

    totaal_omzet, totaal_winst = float(df["omzet"].sum()), float(df["winst"].sum())
    return DV1Resultaat(
        stappen=[info1, info2, info3],
        totaal={
            "omzet": totaal_omzet,
            "winst": totaal_winst,
            "marge": totaal_winst / totaal_omzet,
            "orderlijnen": len(df),
            "orders": int(df["order_id"].nunique()),
        },
        per_markt=samenvatten(df, ["markt"]),
        per_categorie=samenvatten(df, ["categorie"]),
        per_combinatie=combinatie,
    )

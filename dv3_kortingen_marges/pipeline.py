"""DV3 - Kortingen en marges: verband tussen kortingspercentage en gerealiseerde marge.

Pure functies, geen Streamlit-imports. Leest enkel de verwerkte data uit `data/processed/`
(gemaakt door `pipeline_dataco`; geannuleerde en fraude-orders zijn daar al uitgesloten).

Afspraken (zie beslissingslogboek.md):
- marge = som(winst) / som(omzet na korting), gewogen;
- kortingspercentage van een groep = som(korting) / som(bruto omzet), gewogen op omzet;
- een kortingsniveau is het kolomwaarde `Order Item Discount Rate` (18 vaste waarden, 0% tot 25%);
- kortingsklassen: 0% / 1-5% / 6-10% / 11-15% / 16-20% / 21-25%.
Deze module toont een verband (correlatie), nooit een oorzaak.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PATH = ROOT / "data" / "processed" / "dataco_clean.csv"

# ruwe kolomnaam -> naam in deze analyse
KOLOMMEN = {
    "Order Item Id": "orderlijn_id",
    "Market": "markt",
    "Category Name": "categorie",
    "Sales": "bruto",  # prijs x aantal, voor korting
    "Order Item Total": "omzet",  # na korting
    "Order Item Discount": "korting",  # bedrag
    "Order Item Discount Rate": "kortingspercentage",  # 0 tot 0,25 in 18 vaste stappen
    "Order Profit Per Order": "winst",  # per orderlijn
}

# Klassegrenzen op het afgeronde kortingspercentage (bovengrens inclusief) en hun labels.
KLASSE_GRENZEN = [-0.001, 0.0, 0.05, 0.10, 0.15, 0.20, 0.25]
KLASSE_LABELS = ["0%", "1-5%", "6-10%", "11-15%", "16-20%", "21-25%"]

# Onder dit aantal orderlijnen markeren we een groep als weinig betrouwbaar (waarschuwing, geen filter).
MIN_LIJNEN = 30

# Vuistregel om een correlatie in woorden te zetten (conventie, geen wet).
GRENS_GEEN, GRENS_ZWAK = 0.1, 0.3


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
class DV3Resultaat:
    stappen: list[StapInfo]
    totaal: dict[str, float]
    per_niveau: pd.DataFrame
    per_klasse: pd.DataFrame
    per_combinatie: pd.DataFrame
    verband_niveau: dict[str, float]
    verband_combinatie: dict[str, float]


def fmt_getal(n: float) -> str:
    """12345 -> '12.345' (Vlaamse duizendtallen)."""
    return f"{n:,.0f}".replace(",", ".")


def fmt_pct(x: float) -> str:
    """0.004 -> '0,4%'."""
    return f"{x * 100:.1f}".replace(".", ",") + "%"


def samenvatten(df: pd.DataFrame, groep: list[str]) -> pd.DataFrame:
    """Orderlijnen, omzet, winst, gewogen marge, gewogen korting en aandeel verlieslatende lijnen per groep."""
    tabel = (
        df.groupby(groep, observed=True)
        .agg(
            orderlijnen=("orderlijn_id", "size"),
            bruto=("bruto", "sum"),
            omzet=("omzet", "sum"),
            korting=("korting", "sum"),
            winst=("winst", "sum"),
            verlieslatend=("verlies", "sum"),
        )
        .reset_index()
    )
    tabel["marge"] = tabel["winst"] / tabel["omzet"]
    tabel["kortingspct"] = tabel["korting"] / tabel["bruto"]
    tabel["verlies_aandeel"] = tabel["verlieslatend"] / tabel["orderlijnen"]
    tabel["weinig_data"] = tabel["orderlijnen"] < MIN_LIJNEN
    return tabel


def verband(tabel: pd.DataFrame, x: str = "kortingspct", y: str = "marge") -> dict[str, float]:
    """Pearson-correlatie en rechte lijn (ongewogen kleinste kwadraten) tussen twee kolommen.

    Dit is een verband, geen oorzaak. `r_zonder_klein` laat groepen met weinig data weg.
    """
    helling = tabel[x].cov(tabel[y]) / tabel[x].var()
    resultaat = {
        "r": float(tabel[x].corr(tabel[y])),
        "helling": float(helling),
        "intercept": float(tabel[y].mean() - helling * tabel[x].mean()),
        "n": int(len(tabel)),
    }
    groot = tabel[~tabel["weinig_data"]]
    resultaat["r_zonder_klein"] = float(groot[x].corr(groot[y])) if len(groot) > 2 else float("nan")
    return resultaat


def beschrijf_verband(r: float) -> str:
    """Zet een correlatie in woorden volgens een vaste vuistregel."""
    sterkte = abs(r)
    if sterkte < GRENS_GEEN:
        return "geen merkbaar verband"
    richting = "positief" if r > 0 else "negatief"
    return f"een zwak {richting} verband" if sterkte < GRENS_ZWAK else f"een duidelijk {richting} verband"


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
    """Stap 2: controleer de aannames. Faalt luid bij een echte fout; meldt afrondingsverschillen."""
    # De gegeven percentages zijn afgerond; een klein deel wijkt daardoor licht af van korting / bruto.
    afwijkend_pct = (df["korting"] / df["bruto"]).round(2).ne(df["kortingspercentage"].round(2))
    afwijkend_omzet = (df["bruto"] - df["korting"] - df["omzet"]).abs() > 0.01
    controles = {
        "Geen lege waarden": int(df.isna().sum().sum()) == 0,
        "Elke orderlijn komt één keer voor": df["orderlijn_id"].is_unique,
        "Bruto omzet en omzet zijn groter dan 0": bool((df["bruto"] > 0).all() and (df["omzet"] > 0).all()),
        "Kortingspercentage ligt tussen 0 en 25%": bool(df["kortingspercentage"].between(0, 0.25).all()),
        "Kortingspercentage past bij korting / bruto (afgerond op 2 decimalen) voor minstens 99% van de lijnen": bool(
            afwijkend_pct.mean() < 0.01
        ),
        "Omzet = bruto - korting voor minstens 99% van de lijnen": bool(afwijkend_omzet.mean() < 0.01),
    }
    mislukt = [naam for naam, ok in controles.items() if not ok]
    if mislukt:
        raise ValueError("Controle mislukt: " + "; ".join(mislukt))
    reden = (
        "Alle controles geslaagd, niets gewijzigd: "
        + "; ".join(controles)
        + f". Afrondingsverschillen: {fmt_getal(afwijkend_pct.sum())} lijnen ({fmt_pct(afwijkend_pct.mean())}) "
        "waarvan het gegeven percentage niet gelijk is aan korting / bruto (afgerond op 2 decimalen), en "
        f"{fmt_getal(afwijkend_omzet.sum())} lijnen ({fmt_pct(afwijkend_omzet.mean())}) waarvan omzet niet exact "
        "bruto min korting is. We gebruiken de kolom `kortingspercentage` zoals gegeven voor de kortingsniveaus."
    )
    return df, StapInfo("2. Controleren", len(df), len(df), reden, df.head(5))


def add_classes(df: pd.DataFrame) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 3: voeg kortingsniveau, kortingsklasse en een verlies-vlag toe. Geen rijen verwijderd."""
    out = df.copy()
    out["niveau"] = out["kortingspercentage"].round(2)
    out["kortingsklasse"] = pd.cut(out["niveau"], bins=KLASSE_GRENZEN, labels=KLASSE_LABELS)
    if out["kortingsklasse"].isna().any():
        raise ValueError("Er zijn lijnen zonder kortingsklasse.")
    out["verlies"] = (out["winst"] < 0).astype(int)
    tellingen = out["kortingsklasse"].value_counts().reindex(KLASSE_LABELS)
    reden = (
        "Drie kolommen toegevoegd: `niveau` (kortingspercentage afgerond op 2 decimalen, "
        f"{out['niveau'].nunique()} verschillende waarden), `kortingsklasse` en `verlies` (1 als de winst van de lijn negatief is). "
        "Orderlijnen per klasse: " + ", ".join(f"{k} {fmt_getal(n)}" for k, n in tellingen.items()) + "."
    )
    return out, StapInfo("3. Klassen toevoegen", len(df), len(out), reden, out.head(5))


def aggregate_niveau(df: pd.DataFrame) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 4: samenvatten per kortingsniveau (18 vaste percentages)."""
    tabel = samenvatten(df, ["niveau"]).sort_values("niveau").reset_index(drop=True)
    reden = (
        f"{len(df):,} orderlijnen samengevat tot {len(tabel)} kortingsniveaus. ".replace(",", ".")
        + "Marge = som(winst) / som(omzet) per niveau. Dit zijn de punten van de eerste scatter."
    )
    return tabel, StapInfo("4. Per kortingsniveau", len(df), len(tabel), reden, tabel.head(5))


def aggregate_klasse(df: pd.DataFrame) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 5: samenvatten per kortingsklasse (6 klassen)."""
    tabel = samenvatten(df, ["kortingsklasse"]).sort_values("kortingsklasse").reset_index(drop=True)
    tabel["kortingsklasse"] = tabel["kortingsklasse"].astype(str)
    reden = f"{len(df):,} orderlijnen samengevat tot {len(tabel)} kortingsklassen.".replace(",", ".")
    return tabel, StapInfo("5. Per kortingsklasse", len(df), len(tabel), reden, tabel.head(5))


def aggregate_markt_categorie(df: pd.DataFrame) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 6: samenvatten per markt x categorie. Dit zijn de punten van de tweede scatter."""
    tabel = samenvatten(df, ["markt", "categorie"]).sort_values("omzet", ascending=False).reset_index(drop=True)
    aantal_weinig = int(tabel["weinig_data"].sum())
    reden = (
        f"{len(df):,} orderlijnen samengevat tot {len(tabel)} combinaties van markt en categorie. ".replace(",", ".")
        + f"{aantal_weinig} combinaties hebben minder dan {MIN_LIJNEN} orderlijnen en krijgen een waarschuwing "
        "(ze blijven wel in de resultaten). Kortingspercentage per combinatie = som(korting) / som(bruto)."
    )
    return tabel, StapInfo("6. Per markt en categorie", len(df), len(tabel), reden, tabel.head(5))


def run_dv3(pad: Path = PROCESSED_PATH) -> DV3Resultaat:
    """Draai alle stappen van DV3."""
    df, info1 = load_processed(pad)
    df, info2 = check_input(df)
    df, info3 = add_classes(df)
    niveau, info4 = aggregate_niveau(df)
    klasse, info5 = aggregate_klasse(df)
    combinatie, info6 = aggregate_markt_categorie(df)

    return DV3Resultaat(
        stappen=[info1, info2, info3, info4, info5, info6],
        totaal={
            "orderlijnen": len(df),
            "kortingspct": float(df["korting"].sum() / df["bruto"].sum()),
            "marge": float(df["winst"].sum() / df["omzet"].sum()),
            "verlies_aandeel": float(df["verlies"].mean()),
        },
        per_niveau=niveau,
        per_klasse=klasse,
        per_combinatie=combinatie,
        verband_niveau=verband(niveau),
        verband_combinatie=verband(combinatie),
    )

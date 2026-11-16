"""Pijplijn voor de DataCo-dataset.

Pure functies, één per stap, zonder Streamlit-imports. Elke stap geeft het resultaat terug
samen met een `StapInfo`: hoeveel rijen en kolommen erin en eruit gaan, waarom, en wat er
precies veranderde (`Wijzigingen`). De interface (`app.py`) toont enkel wat hier berekend wordt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "DataCoSupplyChainDataset.csv"
PROCESSED_PATH = ROOT / "data" / "processed" / "dataco_clean.csv"

ENCODING = "latin-1"  # utf-8 geeft een UnicodeDecodeError op dit bestand
DATUM_FORMAAT = "%m/%d/%Y %H:%M"  # bv. 1/31/2018 22:56
DATUMKOLOMMEN = ["order date (DateOrders)", "shipping date (DateOrders)"]

# Kolommen die we verwijderen, met de reden. Wat hier staat is een keuze (zie beslissingslogboek).
KOLOMMEN_WEG = {
    "Product Description": "Volledig leeg: geen enkele rij heeft een waarde",
    "Product Status": "Overal 0: bevat geen informatie",
    "Customer Email": "Gemaskeerd (XXXXXXXXX) en een persoonsgegeven",
    "Customer Password": "Gemaskeerd (XXXXXXXXX) en gevoelig",
    "Customer Fname": "Persoonsgegeven, niet nodig voor de deelvragen",
    "Customer Lname": "Persoonsgegeven, niet nodig voor de deelvragen",
    "Customer Street": "Persoonsgegeven (adres), niet nodig voor de deelvragen",
    "Product Image": "Link naar een afbeelding, niet nodig voor de deelvragen",
}

# Orders die we uitsluiten, met de reden (beslissing 1 in beslissingslogboek.md).
STATUSSEN_UITSLUITEN = {
    "CANCELED": "Geannuleerd: geen echte omzet",
    "SUSPECTED_FRAUD": "Vermoedelijke fraude: geen echte omzet",
}


# --------------------------------------------------------------------------- datastructuren


@dataclass
class Wijzigingen:
    """Wat er veranderd is tussen een tabel 'voor' en een tabel 'na'."""

    rijen_voor: int = 0
    rijen_na: int = 0
    kolommen_verwijderd: list[str] = field(default_factory=list)
    kolommen_toegevoegd: list[str] = field(default_factory=list)
    hernoemd: dict[str, str] = field(default_factory=dict)  # oude naam -> nieuwe naam
    dtype_gewijzigd: dict[str, tuple[str, str]] = field(default_factory=dict)  # nieuwe naam -> (voor, na)
    waarden_gewijzigd: dict[str, int] = field(default_factory=dict)  # nieuwe naam -> aantal
    lege_waarden: dict[str, tuple[int, int]] = field(default_factory=dict)  # nieuwe naam -> (voor, na)

    def is_leeg(self) -> bool:
        return not (
            self.kolommen_verwijderd
            or self.kolommen_toegevoegd
            or self.hernoemd
            or self.dtype_gewijzigd
            or self.waarden_gewijzigd
            or self.lege_waarden
            or self.rijen_voor != self.rijen_na
        )


@dataclass
class StapInfo:
    naam: str
    rijen_in: int
    rijen_uit: int
    kolommen_in: int
    kolommen_uit: int
    reden: str
    wijzigingen: Wijzigingen
    voorbeeld: pd.DataFrame  # eerste rijen na de stap
    weggevallen_detail: pd.DataFrame | None = None  # waarom rijen wegvielen, per reden

    @property
    def rijen_weggevallen(self) -> int:
        return self.rijen_in - self.rijen_uit


@dataclass
class PijplijnResultaat:
    ruw: pd.DataFrame
    schoon: pd.DataFrame
    stappen: list[StapInfo]
    totaal: Wijzigingen  # ruw -> schoon
    overzicht: pd.DataFrame  # per ruwe kolom: wat gebeurde ermee
    profiel_ruw: pd.DataFrame
    profiel_schoon: pd.DataFrame


# --------------------------------------------------------------------------- vergelijken


def _is_tekst(s: pd.Series) -> bool:
    return pd.api.types.is_string_dtype(s) or s.dtype == object


def compare(voor: pd.DataFrame, na: pd.DataFrame, hernoemd: dict[str, str] | None = None) -> Wijzigingen:
    """Vergelijk twee tabellen en beschrijf wat er veranderd is.

    `hernoemd` koppelt oude kolomnamen aan nieuwe namen. Gewijzigde waarden en lege cellen tellen we
    enkel op de rijen die in beide tabellen voorkomen (zelfde index); het aantal weggevallen rijen
    staat apart in `rijen_voor` en `rijen_na`.
    """
    hernoemd = hernoemd or {}
    naam_na = {c: hernoemd.get(c, c) for c in voor.columns}
    gemeenschappelijk = [(c, n) for c, n in naam_na.items() if n in na.columns]
    namen_na_gebruikt = {n for _, n in gemeenschappelijk}

    wijz = Wijzigingen(rijen_voor=len(voor), rijen_na=len(na))
    wijz.kolommen_verwijderd = [c for c, n in naam_na.items() if n not in na.columns]
    wijz.kolommen_toegevoegd = [c for c in na.columns if c not in namen_na_gebruikt]
    wijz.hernoemd = {c: n for c, n in gemeenschappelijk if c != n}

    # Waarden en lege cellen vergelijken we op de rijen die in beide tabellen voorkomen (zelfde index),
    # zodat weggevallen rijen het resultaat niet vertekenen.
    kan_uitlijnen = voor.index.is_unique and na.index.is_unique
    gedeelde_index = voor.index.intersection(na.index) if kan_uitlijnen else None
    for oud, nieuw in gemeenschappelijk:
        a, b = voor[oud], na[nieuw]
        if str(a.dtype) != str(b.dtype):
            wijz.dtype_gewijzigd[nieuw] = (str(a.dtype), str(b.dtype))
        if not kan_uitlijnen:
            continue
        a, b = a.loc[gedeelde_index], b.loc[gedeelde_index]
        nul_voor, nul_na = int(a.isna().sum()), int(b.isna().sum())
        if nul_voor != nul_na:
            wijz.lege_waarden[nieuw] = (nul_voor, nul_na)
        if _is_tekst(a) and _is_tekst(b):
            verschil = a.ne(b) & ~(a.isna() & b.isna())
            if verschil.any():
                wijz.waarden_gewijzigd[nieuw] = int(verschil.sum())
    return wijz


def voorbeelden_gewijzigd(
    voor: pd.DataFrame, na: pd.DataFrame, kolom_voor: str, kolom_na: str, n: int = 10
) -> pd.DataFrame:
    """Unieke (ruw, verwerkt)-paren van een tekstkolom waarvan de waarde veranderde."""
    gedeeld = voor.index.intersection(na.index)  # enkel rijen die niet wegvielen
    paar = pd.DataFrame({"ruw": voor.loc[gedeeld, kolom_voor], "verwerkt": na.loc[gedeeld, kolom_na]})
    paar = paar[paar["ruw"].ne(paar["verwerkt"]) & ~(paar["ruw"].isna() & paar["verwerkt"].isna())]
    return paar.drop_duplicates().head(n).reset_index(drop=True)


def kolom_overzicht(
    voor: pd.DataFrame, na: pd.DataFrame, wijz: Wijzigingen, redenen: dict[str, str] | None = None
) -> pd.DataFrame:
    """Eén rij per ruwe kolom: wat gebeurde ermee en waarom."""
    redenen = redenen or {}
    rijen = []
    for kolom in voor.columns:
        nieuw = wijz.hernoemd.get(kolom, kolom)
        if kolom in wijz.kolommen_verwijderd:
            status, dtype_na = "verwijderd", ""
            reden = redenen.get(kolom, "")
        else:
            dtype_na = str(na[nieuw].dtype)
            if kolom in wijz.hernoemd:
                status, reden = "hernoemd", f"nieuwe naam: {nieuw}"
            elif nieuw in wijz.dtype_gewijzigd:
                status, reden = "type aangepast", ""
            else:
                status, reden = "behouden", ""
        rijen.append(
            {
                "kolom (ruw)": kolom,
                "status": status,
                "type ruw": str(voor[kolom].dtype),
                "type verwerkt": dtype_na,
                "waarden gewijzigd": wijz.waarden_gewijzigd.get(nieuw, 0),
                "reden": reden,
            }
        )
    return pd.DataFrame(rijen)


def profile(df: pd.DataFrame) -> pd.DataFrame:
    """Dataprofiel per kolom: type, ingevuld/leeg, aantal unieke waarden, min en max."""
    rijen = []
    for kolom in df.columns:
        s = df[kolom]
        heeft_bereik = pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s)
        rijen.append(
            {
                "kolom": kolom,
                "type": str(s.dtype),
                "ingevuld": int(s.notna().sum()),
                "leeg": int(s.isna().sum()),
                "leeg (%)": round(100 * float(s.isna().mean()), 1),
                "unieke waarden": int(s.nunique()),
                "min": str(s.min()) if heeft_bereik else "",
                "max": str(s.max()) if heeft_bereik else "",
            }
        )
    return pd.DataFrame(rijen)


def _stap(
    naam: str, voor: pd.DataFrame, na: pd.DataFrame, reden: str, hernoemd=None, detail=None
) -> StapInfo:
    return StapInfo(
        naam=naam,
        rijen_in=len(voor),
        rijen_uit=len(na),
        kolommen_in=voor.shape[1],
        kolommen_uit=na.shape[1],
        reden=reden,
        wijzigingen=compare(voor, na, hernoemd),
        voorbeeld=na.head(5),
        weggevallen_detail=detail,
    )


# --------------------------------------------------------------------------- de stappen


def load_raw(pad: Path = RAW_PATH) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 1: lees de ruwe CSV in, ongewijzigd."""
    df = pd.read_csv(pad, encoding=ENCODING)
    reden = f"CSV ingelezen met encoding {ENCODING} (utf-8 werkt niet op dit bestand). Niets gewijzigd."
    return df, _stap("1. Inlezen", df, df, reden)


def clean_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 2: kolomnamen en tekst trimmen, datumkolommen omzetten naar datetime."""
    hernoemd = {c: c.strip() for c in df.columns if c != c.strip()}
    out = df.rename(columns=hernoemd)
    if out.columns.duplicated().any():
        raise ValueError("Na het trimmen van de kolomnamen zijn er dubbele namen.")
    for kolom in out.columns:
        if pd.api.types.is_string_dtype(out[kolom]):
            out[kolom] = out[kolom].str.strip()
    for kolom in DATUMKOLOMMEN:
        if kolom in out.columns:
            out[kolom] = pd.to_datetime(out[kolom], format=DATUM_FORMAAT)
    reden = (
        "Spaties vooraan en achteraan weggehaald uit kolomnamen en tekstwaarden (bv. 'Cameras ' wordt 'Cameras'). "
        f"Datumkolommen ({', '.join(DATUMKOLOMMEN)}) omgezet van tekst naar datetime (formaat m/d/jjjj u:mm). "
        "Geen rijen verwijderd."
    )
    return out, _stap("2. Opschonen", df, out, reden, hernoemd)


def drop_unusable_columns(
    df: pd.DataFrame, redenen: dict[str, str] | None = None
) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 3: verwijder kolommen zonder informatie en persoonsgegevens."""
    redenen = KOLOMMEN_WEG if redenen is None else redenen
    weg = [c for c in redenen if c in df.columns]
    out = df.drop(columns=weg)
    reden = "Kolommen verwijderd (geen rijen): " + "; ".join(f"{c} ({redenen[c]})" for c in weg)
    return out, _stap("3. Kolommen verwijderen", df, out, reden)


def exclude_orders(
    df: pd.DataFrame, redenen: dict[str, str] | None = None
) -> tuple[pd.DataFrame, StapInfo]:
    """Stap 4: sluit geannuleerde en fraude-orders uit (beslissing 1 in het logboek)."""
    redenen = STATUSSEN_UITSLUITEN if redenen is None else redenen
    weg = df["Order Status"].isin(redenen)
    out = df.loc[~weg]

    detail = (
        df.loc[weg]
        .groupby("Order Status")
        .agg(rijen=("Order Id", "size"), orders=("Order Id", "nunique"))
        .reset_index()
        .rename(columns={"Order Status": "orderstatus"})
    )
    detail.insert(1, "reden", detail["orderstatus"].map(redenen))

    # Orders met een uitgesloten lijn die ook andere lijnen hebben, zouden half in de data blijven.
    halve_orders = int(out["Order Id"].isin(df.loc[weg, "Order Id"]).sum())
    geannuleerde_zending = int(df.loc[weg, "Delivery Status"].eq("Shipping canceled").sum())
    reden = (
        "Rijen met orderstatus " + " of ".join(redenen) + " uitgesloten: geen echte omzet en winst. "
        f"{fmt_getal(int(weg.sum()))} rijen ({fmt_getal(int(df.loc[weg, 'Order Id'].nunique()))} orders) vallen weg. "
        f"Van die rijen hebben {fmt_getal(geannuleerde_zending)} ook Delivery Status 'Shipping canceled' "
        "(dezelfde rijen, dus ook het leverpercentage wordt hierdoor gefilterd). "
        f"Orders waarvan maar een deel van de lijnen wegvalt: {fmt_getal(halve_orders)} rijen."
    )
    return out, _stap("4. Orders uitsluiten", df, out, reden, detail=detail)


def fmt_getal(n: int) -> str:
    """12345 -> '12.345' (Vlaamse duizendtallen)."""
    return f"{n:,}".replace(",", ".")


# --------------------------------------------------------------------------- de pijplijn


def run_pipeline(pad: Path = RAW_PATH) -> PijplijnResultaat:
    """Draai alle stappen en vergelijk het eindresultaat met de ruwe tabel."""
    ruw, info1 = load_raw(pad)
    opgeschoond, info2 = clean_columns(ruw)
    zonder_kolommen, info3 = drop_unusable_columns(opgeschoond)
    schoon, info4 = exclude_orders(zonder_kolommen)

    hernoemd = info2.wijzigingen.hernoemd
    totaal = compare(ruw, schoon, hernoemd)
    return PijplijnResultaat(
        ruw=ruw,
        schoon=schoon,
        stappen=[info1, info2, info3, info4],
        totaal=totaal,
        overzicht=kolom_overzicht(ruw, schoon, totaal, KOLOMMEN_WEG),
        profiel_ruw=profile(ruw),
        profiel_schoon=profile(schoon),
    )


def save_processed(df: pd.DataFrame, pad: Path = PROCESSED_PATH) -> Path:
    """Schrijf de verwerkte tabel naar `data/processed/` (nooit naar `data/raw/`)."""
    pad.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(pad, index=False, encoding="utf-8")
    return pad

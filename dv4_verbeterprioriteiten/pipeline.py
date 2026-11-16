"""DV4 - Verbeterprioriteiten: welke combinaties van markt en categorie verdienen als eerste onderzoek?

Pure functies, geen Streamlit-imports. Synthetiseert DV1 (omzet en marge), DV2 (vertraagde orders) en
DV3 (korting) door hun pijplijnen te hergebruiken; die lezen zelf enkel uit `data/processed/`.

Werkwijze (zie beslissingslogboek.md):
- een combinatie heeft een **marge-probleem** als haar marge onder de totale marge ligt;
- een combinatie heeft een **leverprobleem** als haar percentage vertraagde orders boven het totaal ligt;
- rangschikking: eerst combinaties met twee problemen, dan met één, dan met geen; binnen elke groep op omzet;
- enkel combinaties met genoeg orderlijnen doen mee (instelbare drempel), want een marge op weinig lijnen is grotendeels ruis;
- DV3 (korting) telt niet mee in de rangschikking: daar was geen verband, we tonen het enkel als context.
De uitkomst is een volgorde om te onderzoeken, geen oorzaak en geen besparing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from dv1_omzet_winst import pipeline as p1
from dv2_leverbetrouwbaarheid import pipeline as p2
from dv3_kortingen_marges import pipeline as p3

STANDAARD_MIN_LIJNEN = 300  # onder deze drempel is een marge grotendeels ruis (zie data-exploration.md)

GROEPEN = {
    2: "Dubbel probleem: lage marge én veel vertraging",
    1: "Eén probleem: lage marge óf veel vertraging",
    0: "Op koers: marge en levering minstens gemiddeld",
}


def fmt_getal(n: float) -> str:
    """12345 -> '12.345' (Vlaamse duizendtallen)."""
    return f"{n:,.0f}".replace(",", ".")


def fmt_pct(x: float, decimalen: int = 1) -> str:
    """0.1203 -> '12,0%'."""
    return f"{x * 100:.{decimalen}f}".replace(".", ",") + "%"


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
class Basis:
    """De samengevoegde uitkomsten van DV1 tot DV3, nog zonder drempel of rangschikking."""

    tabel: pd.DataFrame
    totaal: dict[str, float]
    stappen: list[StapInfo]


@dataclass
class Prioriteit:
    tabel: pd.DataFrame  # alle combinaties, met kolom `meedoen` en `rang` (leeg voor wie niet meedoet)
    ranglijst: pd.DataFrame  # enkel wie meedoet, in volgorde van prioriteit
    stappen: list[StapInfo]
    kpis: dict[str, float]


def bouw_basis(pad: Path = p1.PROCESSED_PATH) -> Basis:
    """Stap 1 en 2: haal de uitkomsten van DV1, DV2 en DV3 op en voeg ze samen per markt en categorie."""
    r1, r2, r3 = p1.run_dv1(pad), p2.run_dv2(pad), p3.run_dv3(pad)
    a = r1.per_combinatie[["markt", "categorie", "omzet", "winst", "marge", "orderlijnen"]]
    b = r2.per_combinatie[["markt", "categorie", "orders", "vertraagd", "pct_vertraagd"]].rename(
        columns={"vertraagd": "vertraagde_orders"}
    )
    c = r3.per_combinatie[["markt", "categorie", "kortingspct", "verlies_aandeel"]]

    aantallen = {"DV1": len(a), "DV2": len(b), "DV3": len(c)}
    sleutels = [set(map(tuple, t[["markt", "categorie"]].values)) for t in (a, b, c)]
    if not (sleutels[0] == sleutels[1] == sleutels[2]):
        raise ValueError("DV1, DV2 en DV3 hebben niet dezelfde combinaties van markt en categorie.")
    tabel = a.merge(b, on=["markt", "categorie"], validate="one_to_one").merge(
        c, on=["markt", "categorie"], validate="one_to_one"
    )

    totaal = {
        "omzet": r1.totaal["omzet"],
        "winst": r1.totaal["winst"],
        "marge": r1.totaal["marge"],
        "pct_vertraagd": r2.totaal["pct_vertraagd"],
        "kortingspct": r3.totaal["kortingspct"],
        "orderlijnen": r1.totaal["orderlijnen"],
    }
    info1 = StapInfo(
        "1. Uitkomsten ophalen",
        r1.totaal["orderlijnen"],
        len(a),
        "De pijplijnen van DV1, DV2 en DV3 gedraaid op `data/processed/dataco_clean.csv`. Elk levert "
        + ", ".join(f"{n} combinaties ({k})" for k, n in aantallen.items())
        + " van markt en categorie. Referentie voor 'boven of onder gemiddeld': "
        f"marge {fmt_pct(totaal['marge'])} (som winst / som omzet, DV1) en {fmt_pct(totaal['pct_vertraagd'])} vertraagde "
        "unieke orders (DV2).",
        a.head(5),
    )
    info2 = StapInfo(
        "2. Samenvoegen",
        len(a),
        len(tabel),
        "Drie tabellen samengevoegd op markt en categorie (één op één). Gecontroleerd dat alle drie dezelfde "
        f"{len(tabel)} combinaties bevatten; niets verloren.",
        tabel.head(5),
    )
    return Basis(tabel, totaal, [info1, info2])


def bereken_prioriteit(basis: Basis, min_lijnen: int = STANDAARD_MIN_LIJNEN) -> Prioriteit:
    """Stap 3 tot 5: afwijkingen van het gemiddelde, drempel op betrouwbaarheid en rangschikking."""
    totaal = basis.totaal
    tabel = basis.tabel.copy()

    # Stap 3: afwijkingen en aantal problemen
    tabel["omzetaandeel"] = tabel["omzet"] / totaal["omzet"]
    tabel["marge_verschil"] = tabel["marge"] - totaal["marge"]  # negatief = lager dan gemiddeld
    tabel["vertraging_verschil"] = tabel["pct_vertraagd"] - totaal["pct_vertraagd"]  # positief = vaker vertraagd
    # Winst die de combinatie zou hebben op de totale marge, min wat ze nu heeft. Een maat voor het gewicht van het
    # margeverschil, geen besparing: er is geen aanwijzing dat de marge zou stijgen als je er iets aan doet.
    tabel["winstverschil"] = tabel["omzet"] * (totaal["marge"] - tabel["marge"])
    tabel["marge_probleem"] = tabel["marge_verschil"] < 0
    tabel["leverprobleem"] = tabel["vertraging_verschil"] > 0
    tabel["problemen"] = tabel["marge_probleem"].astype(int) + tabel["leverprobleem"].astype(int)
    tabel["groep"] = tabel["problemen"].map(GROEPEN)
    info3 = StapInfo(
        "3. Afwijkingen berekenen",
        len(tabel),
        len(tabel),
        "Per combinatie het verschil met het totaal: marge (lager dan gemiddeld = probleem) en percentage vertraagd "
        "(hoger dan gemiddeld = probleem). Dat levert 0, 1 of 2 problemen op. Er is bewust geen tolerantie: "
        "een combinatie die 0,01 procentpunt onder het gemiddelde zit, telt als 'onder gemiddeld'. "
        "Kolom `winstverschil` = omzet x (totale marge - eigen marge), enkel een maat voor het gewicht, geen besparing. "
        "Niets verwijderd. Aantal combinaties per groep: "
        + ", ".join(f"{GROEPEN[k].split(':')[0]} {int((tabel['problemen'] == k).sum())}" for k in (2, 1, 0))
        + ".",
        tabel.head(5),
    )

    # Stap 4: enkel combinaties met genoeg orderlijnen doen mee
    tabel["meedoen"] = tabel["orderlijnen"] >= min_lijnen
    meedoen = tabel[tabel["meedoen"]]
    weg = tabel[~tabel["meedoen"]]
    info4 = StapInfo(
        "4. Betrouwbaarheid",
        len(tabel),
        len(meedoen),
        f"Enkel combinaties met minstens {fmt_getal(min_lijnen)} orderlijnen doen mee in de rangschikking: een marge op weinig "
        f"lijnen is grotendeels ruis. {len(weg)} combinaties vallen af, samen {fmt_pct(weg['omzet'].sum() / totaal['omzet'])} "
        "van de omzet. Ze blijven zichtbaar in de matrix en de tabel, maar krijgen geen rang.",
        meedoen.head(5),
    )

    # Stap 5: rangschikking
    ranglijst = meedoen.sort_values(["problemen", "omzet"], ascending=[False, False]).reset_index(drop=True)
    ranglijst.insert(0, "rang", range(1, len(ranglijst) + 1))
    tabel = tabel.merge(ranglijst[["markt", "categorie", "rang"]], on=["markt", "categorie"], how="left")
    info5 = StapInfo(
        "5. Rangschikken",
        len(meedoen),
        len(ranglijst),
        "Eerst combinaties met twee problemen, dan met één, dan met geen. Binnen elke groep staat de grootste omzet vooraan, "
        "want daar is een verbetering het meest de moeite waard om uit te zoeken. Niets verwijderd.",
        ranglijst.head(5),
    )

    dubbel = ranglijst[ranglijst["problemen"] == 2]
    kpis = {
        "combinaties": len(tabel),
        "meedoen": len(ranglijst),
        "dubbel": len(dubbel),
        "dubbel_omzetaandeel": float(dubbel["omzet"].sum() / totaal["omzet"]),
        "meedoen_omzetaandeel": float(ranglijst["omzet"].sum() / totaal["omzet"]),
    }
    return Prioriteit(tabel, ranglijst, basis.stappen + [info3, info4, info5], kpis)

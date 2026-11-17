# Streamlit-app — gebruikershandleiding

**Status:** zes pagina's, gebouwd op de gepubliceerde DataCo-dataset (`data/raw/DataCoSupplyChainDataset.csv`).

## Navigatie en interactie

- Start met `streamlit run app.py` vanuit de projectroot; app gebruikt `st.navigation(..., position="top")` en géén zijbalk.
- Schermen: **Overview**, **DV1 Omzet & Winst**, **DV2 Leverbetrouwbaarheid**, **DV3 Kortingen & Marges**, **DV4 Verbeterprioriteiten**, **Data & Methode**.
- Globale filters: markt, categorie, periode. Filters mogen pas echte waarden tonen na goedgekeurde analysebasis; detail- en aggregatietabellen gebruiken dezelfde selectie.
- Per deelvraag: **Analyse**, uitklapbaar **Hoe is dit berekend?**, uitklapbaar **Onderliggende data**. Maak zichtbare tekst toegankelijk en herleidbaar; geef niet onnodig ruwe persoonsgegevens vrij.

## Rondleiding van 5–7 minuten

1. Toon centrale vraag en totale KPI's in Overview.
2. Selecteer een markt/categorie en ga naar DV1: verklaar omzetsom, winstsom en marge.
3. Ga naar DV2: toon het verschil tussen orderregels en unieke orders, statusmapping, teller/noemer en uitzonderingen.
4. Ga naar DV3: toon de kortingseenheid, waarnemingen, samenhang en het verschil tussen correlatie en causaliteit.
5. Ga naar DV4: klik een verbeterprioriteit aan, toon waarom deze op basis van DV1–DV3 gekozen is.
6. Open Data & Methode: volg ruwe bron → audit → processed-versie → aggregaties → visualisaties via rijentrechter en preview per stap.
7. Toon één test die een fout zou detecteren en een expliciete beslissing uit het logboek.

## Verwachte UI-staat

- Zonder gevalideerde CSV: ontbrekende KPI's tonen **N/B**, geen getekende mockupresultaten.
- Foutieve of incomplete bron: toon een menselijk leesbare waarschuwing zonder PII.
- Selectie met te weinig orders: toon N, waarschuwing en waarom de vergelijking mogelijk onbetrouwbaar is.
- Grafiek: correcte eenheden, labels, sortering, bronbestand/versie en passende tooltip.

## Controlepunten bij elke wijziging

- Sluiten de berekende waarden aan bij de onderliggende analysetabel en pure Python-functies?
- Is de actieve filterset voor KPI, grafiek en bewijs identiek?
- Kan een gebruiker de topprioriteit herleiden tot DV1, DV2, DV3 en de ruwe bronhash?
- Zijn PII en niet-goedgekeurde KPI's verborgen?
- Zijn wijzigingen aan de app ook bijgewerkt in dit handboek?

# DataCo — waar liggen de grootste verbeterkansen?

Streamlit-onderzoeksapp voor Syntra Data Science, Project 1. De app analyseert de DataCo supply-chain-dataset.

**Centrale onderzoeksvraag:** welke markten en productcategorieën bieden DataCo de grootste verbetermogelijkheden wanneer we omzet, winstgevendheid en leverbetrouwbaarheid samen analyseren?

| Deelvraag | Wat tonen we? | Weergave |
|---|---|---|
| **DV1 — Omzet & winst** | Omzet (na korting), winst en gewogen marge per markt en productcategorie | Bars + marge-heatmap |
| **DV2 — Leverbetrouwbaarheid** | Percentage vertraagde **unieke orders**, per markt en categorie | Marktbars + heatmap |
| **DV3 — Kortingen & marges** | Verband tussen kortingspercentage en gerealiseerde marge | Scatter (steekproef) + marge per kortingsklasse |
| **DV4 — Verbeterprioriteiten** | Welke markt-categoriecombinaties verdienen als eerste onderzoek? | Prioriteitenmatrix + top 5 |

DV4 synthetiseert DV1 tot DV3. De app claimt geen oorzakelijkheid en geen financiële besparing die de data niet onderbouwt.

De app heeft zes pagina's: Overview, DV1 tot DV4 en **Data & Methode** (rijentrechter, data-audit, KPI-definities, aannames).
Bovenaan staan filters voor markt, categorie en periode; er is geen zijbalk.

## Starten (Windows, PowerShell)

```
conda activate syntra-ds
streamlit run app.py
python -m pytest        # tests
```

## Bouwwijze: pijplijn van inspecteerbare stappen

- `pipeline.py` bevat pure functies, één per stap, zonder Streamlit-imports.
- De pagina Data & Methode toont elke stap in een eigen `st.expander`: hoeveel rijen erin en eruit gaan, waarom rijen
  wegvallen, en een voorbeeld van de data na de stap.
- Bovenaan staat een rijen-trechter die in één oogopslag toont waar data verdwijnt.
- Elke DV-pagina toont "Hoe is dit berekend?" en "Onderliggende data".

## Structuur

- `app.py` — startpunt: kopbalk, globale filters en navigatie naar de zes pagina's
- `pipeline.py` — pure datastappen: inlezen, valideren, opschonen, analysebasis, grain (orderlijn → order → order × categorie)
- `analysis/` — pure KPI-berekeningen (`kpis.py`) en het bewijscontract (`evidence.py`)
- `ui/` — gedeelde weergave (`common.py`) en data-toegang met cache (`data.py`)
- `views/` — de zes pagina's
- `tests/` — pytest voor pijplijn, KPI's, grain, data-levenscyclus en appstructuur
- `docs/` — specificatie, KPI-register, traceerbaarheid, architectuur, onderzoeksontwerp en gebruikershandleiding
- `data-exploration.md` — dataprofiel van de ruwe dataset en open vragen
- `beslissingslogboek.md` — gemaakte keuzes en waarom (V2.1 en V3 samengevoegd)
- `data/raw/` — ruwe downloads, nooit aanpassen (niet in git). Bronnen: zie `data-exploration.md`
- `data/processed/` — verwerkte tabellen met herkomst en SHA-256 (niet in git)
- `requirements.txt` — enkel wat de app importeert; `requirements-dev.txt` voegt `pytest` toe
- `.env` — geheimen (niet in git)

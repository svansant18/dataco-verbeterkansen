# DataCo — waar liggen de grootste verbeterkansen?

Streamlit-onderzoeksapp voor Syntra Data Science, Project 1. De app analyseert de DataCo supply-chain-dataset.

**Centrale onderzoeksvraag:** welke markten en productcategorieën bieden DataCo de grootste verbetermogelijkheden wanneer we omzet, winstgevendheid en leverbetrouwbaarheid samen analyseren?

| Deelvraag | Wat tonen we? | Weergave |
|---|---|---|
| **DV1 — Omzet & winst** | Omzet, winst en winstmarge per markt en productcategorie | Bars + marge-heatmap |
| **DV2 — Leverbetrouwbaarheid** | Percentage vertraagde **unieke orders**, per markt en categorie | Marktbars + risico-heatmap |
| **DV3 — Kortingen & marges** | Verband tussen kortingspercentage en gerealiseerde marge | Scatter + kortingsklassen |
| **DV4 — Verbeterprioriteiten** | Welke markt-categoriecombinaties verdienen als eerste onderzoek? | Prioriteitenmatrix + rangschikking |

DV4 synthetiseert DV1 tot DV3. De app claimt geen oorzakelijkheid en geen financiële besparing die de data niet onderbouwt.


## Starten (Windows, PowerShell)

```
conda activate syntra-ds
streamlit run app.py    # alles in één app, met bovenaan de keuze van sub-app
```

Een sub-app los starten kan ook:

```
streamlit run explore_raw_data/app.py
```

## Bouwwijze: pijplijn van inspecteerbare stappen

- `pipeline.py` bevat pure functies, één per stap, zonder Streamlit-imports.
- `app.py` toont elke stap in een eigen `st.expander`: hoeveel rijen erin en eruit gaan, waarom rijen
  wegvallen, en een voorbeeld van de data na de stap.
- Bovenaan staat een rijen-trechter die in één oogopslag toont waar data verdwijnt.

## Structuur

- `app.py` — starter: toont de keuze van sub-app bovenaan en laadt de gekozen sub-app
- `pipeline_dataco/` — `pipeline.py` (stappen) en `app.py` (toont stappen, trechter en ruw-vs-verwerkt)
- `dv1_omzet_winst/` — DV1: omzet, winst en marge per markt en categorie (leest `data/processed/dataco_clean.csv`)
- `dv2_leverbetrouwbaarheid/` — DV2: percentage vertraagde unieke orders per markt, categorie en verzendmethode
- `dv3_kortingen_marges/` — DV3: verband tussen kortingspercentage en marge (scatters en kortingsklassen)
- `explore_raw_data/app.py` — dataverkenner voor de ruwe bestanden (wordt bevroren na de pipeline; nog niet gebouwd)
- `data-exploration.md` — dataprofiel en open vragen
- `data/processed/` — verwerkte data uit de pijplijn (niet in git)
- `requirements.txt` — enkel wat de app importeert
- `data/raw/` — ruwe downloads, nooit aanpassen (niet in git). Bronnen: zie `data-exploration.md`;
- `.env` — geheimen (niet in git)
- `beslissingslogboek.md` — gemaakte keuzes en waarom

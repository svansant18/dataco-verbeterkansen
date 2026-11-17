# DataCo — waar liggen de grootste verbeterkansen?

Streamlit-onderzoeksapp voor Syntra Data Science, Project 1. De app analyseert de DataCo supply-chain-dataset.

**Live app:** https://dataco-verbeterkansen.streamlit.app (de eerste keer na een pauze kan het even duren voor ze wakker is)

**Centrale onderzoeksvraag:** welke markten en productcategorieën bieden DataCo de grootste verbetermogelijkheden wanneer we omzet, winstgevendheid en leverbetrouwbaarheid samen analyseren?

| Deelvraag | Wat tonen we? | Weergave |
|---|---|---|
| **DV1 — Omzet & winst** | Omzet (na korting), winst en gewogen marge per markt en productcategorie | Bars + marge-heatmap |
| **DV2 — Leverbetrouwbaarheid** | Percentage vertraagde **unieke orders**, per markt en categorie | Marktbars + heatmap |
| **DV3 — Kortingen & marges** | Verband tussen kortingspercentage en gerealiseerde marge | Scatter (steekproef) + marge per kortingsklasse |
| **DV4 — Verbeterprioriteiten** | Welke markt-categoriecombinaties verdienen als eerste onderzoek? | Prioriteitenmatrix + top 5 |

DV4 combineert DV1 (omzet en marge) en DV2 (% vertraagde orders) tot een prioriteitsklasse per markt × categorie; DV3 (korting) is geen invoer van die klasse maar een voorgestelde vervolgstap. De app claimt geen oorzakelijkheid en geen financiële besparing die de data niet onderbouwt.

De app heeft zes pagina's: Overview, DV1 tot DV4 en **Data & Methode** (rijentrechter, data-audit, KPI-definities, aannames).
Bovenaan staan filters voor markt, categorie en periode; er is geen zijbalk. De filters hangen van elkaar af: kies je een markt,
dan bieden de categorieën alleen wat in die markt voorkomt (en andersom), zodat je geen lege combinatie kan kiezen.
Kies je één markt, dan vergelijkt de linkergrafiek categorieën (anders markten); de heatmap rechts blijft staan.
Een filter op markt of categorie zoomt in op DV4: de referenties en klassen blijven die van het hele bedrijf in de gekozen periode.

## Starten (Windows, PowerShell)

```
conda activate syntra-ds
streamlit run app.py
python -m pytest        # tests
```

## Online zetten (Streamlit Community Cloud)

De ruwe CSV (met persoonsgegevens) staat nooit online. De app leest dan de publicatiebundel in `data/published/`; ze toont dezelfde cijfers.

1. Zet de repo op GitHub (`main`). `data/raw/` en `data/processed/` staan in `.gitignore`; alleen `data/published/` gaat mee.
2. Maak op share.streamlit.io een nieuwe app: repo, branch `main`, hoofdbestand `app.py`. Kies onder *Advanced settings* Python 3.12 of hoger.
3. Controleer de publieke URL: alle zes pagina's, de filters en de uitklappers "Hoe is dit berekend?".

Lokaal de online situatie nabootsen: zet de omgevingsvariabele `DATACO_BRON=bundel` en start `streamlit run app.py`.
Een nieuwe bundel maken (nieuwe versie, overschrijft nooit): `python -c "import pipeline; pipeline.build_published('.', 'v2')"`.

## Bronvermelding

Dataset: *DataCo SMART SUPPLY CHAIN FOR BIG DATA ANALYSIS*, Fabian Constante, Fernando Silva en António Pereira, Mendeley Data,
[doi:10.17632/8gx2fvg2k6](https://doi.org/10.17632/8gx2fvg2k6), gedownload via [Kaggle (shashwatwork)](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis).
Licentie volgens Mendeley: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (versie 4 en 5); volgens Kaggle:
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). We vermelden de bron in elk geval. Bewerkt: dit project gebruikt 13 van de 53 kolommen en laat geannuleerde en
vermoedelijk frauduleuze orders buiten de omzet en winst.

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
- `data/published/` — de publicatiebundel (wel in git): dezelfde twee tabellen, alleen analysekolommen, plus herkomst en een metabestand
- `requirements.txt` — enkel wat de app importeert; `requirements-dev.txt` voegt `pytest` toe
- `.env` — geheimen (niet in git)

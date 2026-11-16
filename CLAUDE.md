# Wat wil je maken? — Streamlit-app over grootste verbeterkansen op gebied van omzet, winstgevendheid en leverbetrouwbaarheid

Missie en vier deelvragen: zie `README.md`. Databronnen en ophaalmethodes: `data-exploration.md`.

## Afspraken

1. **Eén Streamlit-app met zes pagina's** (`app.py` met `st.navigation(position="top")` en globale filters
   voor markt, categorie en periode). Pagina's in `views/`: `overview.py`, `dv1.py` (omzet en winst), `dv2.py`
   (leverbetrouwbaarheid), `dv3.py` (kortingen en marges), `dv4.py` (verbeterprioriteiten, gebouwd op DV1 tot DV3)
   en `methode.py` (Data & Methode: rijentrechter, data-audit, KPI-definities, aannames).
   Lagen: `pipeline.py` (pure datastappen, geen Streamlit) → `analysis/` (pure KPI's en bewijs, geen Streamlit)
   → `ui/` (gedeelde weergave en data-toegang) → `views/` (enkel paginalayout). Geen KPI-formules in `views/`.
   Starten: `streamlit run app.py`. Een nieuwe pagina = een bestand in `views/` + één `st.Page` in `app.py`.
   De app leest de ruwe `data/raw/DataCoSupplyChainDataset.csv` (read-only) en rekent in het geheugen: er wordt
   niets weggeschreven. De herkomst is de SHA-256 van de ruwe bron, vóór en na de run gecontroleerd.
   Tests: `python -m pytest` (`requirements-dev.txt`).
2. `requirements.txt` bevat enkel wat de app importeert, met versienummers (streamlit, pandas, numpy, plotly);
   test-tools staan apart in `requirements-dev.txt`.
3. Een nieuw package? Vraag het EERST aan Steve, met reden en alternatief. Installeer niets zonder OK.
4. Data in `data/`, geheimen in `.env`. `data/`, `.env` en `__pycache__/` staan in `.gitignore`.
   `data/raw/` bevat de ruwe downloads en is **read-only voor Claude**: nooit aanpassen of
   overschrijven (`deny`-regel in `.claude/settings.json`). De app schrijft zelf niets weg; zou ze ooit afgeleide data
   bewaren, dan in `data/processed/`.
5. Standaardomgeving is de conda-environment `syntra-ds` (geen eigen `.venv`). Python:
   `C:\Users\steve\anaconda3\envs\syntra-ds\python.exe`.
6. Git-repo, branch `main`. Werk aan grote wijzigingen op een aparte branch en merge pas na akkoord
   (met een tag op de vorige versie, zodat je altijd terug kan). Commit elke werkende stap met een duidelijke boodschap, en nooit
   zonder dat Tim de wijziging zag.
7. Houd `README.md` kort en deze `CLAUDE.md` in sync met de afspraken.
8. **Geen zijbalk** (`st.sidebar`): alle bediening, filters en uitleg staan in de app zelf (hoofdpagina,
   tabs, expanders, kolommen). Algemene regel van de docent voor al de apps.

## Werkwijze

- Analyses: aannames die de uitkomst kunnen veranderen niet stil maken; noteer ze in
  `beslissingslogboek.md`. Run het commando `/timtim:logboek`.
- Echte cijfers uit de data, niet geschat.
- **Bouw als pijplijn van inspecteerbare stappen** (pijplijn & caching):
  - `pipeline.py` met pure functies: één per stap, geen Streamlit-imports.
  - De pagina Data & Methode (`views/methode.py`) toont elke stap in een eigen `st.expander`: hoeveel rijen erin
    en eruit gaan, waarom rijen wegvallen, en een voorbeeld van de data na de stap.
  - Bovenaan die pagina staat een rijen-trechter die in één oogopslag toont waar data verdwijnt.
  - Elke DV-pagina heeft de uitklappers "Hoe is dit berekend?" en "Onderliggende data".
- Beslissingen volgen het logboek: een afwijkende keuze eerst in `beslissingslogboek.md` zetten, dan pas in code.

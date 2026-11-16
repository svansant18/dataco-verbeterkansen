# Wat wil je maken? — Streamlit-app over grootste verbeterkansen op gebied van omzet, winstgevendheid en leverbetrouwbaarheid

Missie en vier ideeën: zie `README.md`. Databronnen en ophaalmethodes: `data-exploration.md`.

## Afspraken

1. Per sub-app één `app.py` voor de interface; de logica in aparte, benoemde functies. Sub-apps:
   `explore_raw_data/` (dataverkenner, **wordt bevroren** na de pipeline, zie 9; nog niet gebouwd),
   `pipeline_dataco/` (pijplijn en vergelijking ruw vs verwerkt), `dv1_omzet_winst/` (DV1), `dv2_leverbetrouwbaarheid/` (DV2) en `dv3_kortingen_marges/` (DV3); die
   lezen `data/processed/dataco_clean.csv`, dus eerst in `pipeline_dataco` op "Sla verwerkte data op" klikken. Verder de sub-apps voor de deelvragen bij de
   centrale vraag (zie `README.md`).
   Starten: `streamlit run app.py` (root-starter met sub-app-keuze bovenaan; laadt `<submap>\app.py`
   via `main()` en negeert hun `st.set_page_config`). Een sub-app los starten kan ook:
   `streamlit run <submap>\app.py`. Een nieuwe sub-app = een map met `app.py` + `main()` en één regel in
   `SUBAPPS` in de root-`app.py`. Elke sub-app leest enkel uit `data/`.
2. `requirements.txt` bevat enkel wat de app importeert, met versienummers (start: streamlit, pandas).
3. Een nieuw package? Vraag het EERST aan Steve, met reden en alternatief. Installeer niets zonder OK.
4. Data in `data/`, geheimen in `.env`. `data/`, `.env` en `__pycache__/` staan in `.gitignore`.
   `data/raw/` bevat de ruwe downloads en is **read-only voor Claude**: nooit aanpassen of
   overschrijven (`deny`-regel in `.claude/settings.json`). Afgeleide data komt in `data/processed/`.
5. Standaardomgeving is de conda-environment `syntra-ds` (geen eigen `.venv`). Python:
   `C:\Users\steve\anaconda3\envs\syntra-ds\python.exe`.
6. Git-repo, branch `main`. Commit elke werkende stap met een duidelijke boodschap, en nooit
   zonder dat Tim de wijziging zag.
7. Houd `README.md` kort en deze `CLAUDE.md` in sync met de afspraken.
8. **Geen zijbalk** (`st.sidebar`): alle bediening, filters en uitleg staan in de app zelf (hoofdpagina,
   tabs, expanders, kolommen). Algemene regel van de docent voor al de apps.
9. **`explore_raw_data/` wordt bevroren zodra de pipeline gemaakt is**: tot dan mag ze nog aangepast
   worden, daarna niet meer (afspraak, niet technisch afgedwongen). Deze app werkt altijd
   met de volledige ruwe bestanden in `data/raw/`, nooit met afgeleide of ingekorte data. Nieuwe analyses komen
   in een nieuwe sub-app.

## Werkwijze

- Analyses: aannames die de uitkomst kunnen veranderen niet stil maken; noteer ze in
  `beslissingslogboek.md`. Run het commando `/timtim:logboek`.
- Echte cijfers uit de data, niet geschat.
- **Bouw als pijplijn van inspecteerbare stappen** (pijplijn & caching):
  - `pipeline.py` met pure functies: één per stap, geen Streamlit-imports.
  - `app.py` toont elke stap in een eigen `st.expander`: hoeveel rijen erin en eruit gaan, waarom rijen
    wegvallen, en een voorbeeld van de data na de stap.
  - Bovenaan een rijen-trechter die in één oogopslag toont waar data verdwijnt.

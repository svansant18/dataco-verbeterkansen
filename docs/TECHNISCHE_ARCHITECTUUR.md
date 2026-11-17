# Technische architectuur — implementatieoverdracht

## Componenten

```text
read-only data/raw/  --(read + SHA-256)--> pipeline.py (pure functies)
                                        |-- schema-/grainaudit
                                        |-- kwaliteitscontrole/cleaning
                                        '-- metadata van input/output en dropredenen
                                                 |
                                         data/processed/<nieuwe-versie>        (lokaal, niet in git)
                                         + provenance JSON + hashes
                                         data/published/<versie>               (publicatiebundel, wel in git,
                                         enkel de 13 analysekolommen)           de app valt hierop terug zonder ruwe CSV)
                                                 |
                                analysis/kpis.py + analysis/evidence.py
                                                 |
                                ui/data.py (data ophalen met cache) + ui/common.py (weergave)
                                                 |
                      app.py + views/{overview,dv1,dv2,dv3,dv4,methode}.py
                                                 |
                          Data-to-Insight bewijs in Streamlit (zonder PII)
```

## Modules en contracten

- `app.py` is het Streamlit-entrypoint met bovenste navigatie en globale filters.
- `views/overview.py`, `views/dv1.py` … `views/methode.py`: uitsluitend presentatie en interactieve weergave; geen onafhankelijke KPI-formules uitvinden.
- `pipeline.py`: pure lees-/audit-/transformatiestappen en veilige `data/processed/`-persist; nooit Streamlit importeren.
- `analysis/kpis.py`: pure KPI-berekeningen met correcte aggregatie, edge cases en hergebruik voor grafieken.
- `analysis/evidence.py`: bewijscontract van bron naar formule en visualisatie.
- `ui/common.py`: gedeelde evidence- en weergavecomponenten. Werkelijke evidence uit `analysis` opbouwen na audit.
- `ui/data.py`: data-toegang met cache (`st.cache_resource`, sleutel = bestand + tijdstempel): de ruwe CSV lokaal, de publicatiebundel online; de globale filters en de afhankelijke filteropties.

## Immutable data en privacy

- `data/raw/`: alleen lezen. SHA-256 controleren vóór/na pipeline. Origineel nooit aanpassen, verplaatsen, verwijderen of overschrijven.
- `data/processed/`: **uitsluitend nieuwe** datasets met provenance; houd versie en verwerking bij. Overschrijf niet zonder expliciete toestemming.
- `.gitignore` sluit `data/*` uit, **behalve `data/published/`** (de publicatiebundel zonder persoonsgegevens), en daarnaast `.env` en `reports/local/`. De ruwe CSV en `data/processed/` gaan dus nooit naar git.
- Auditrapporten en Markdown bevatten alleen veilige tellingen, geaggregeerde resultaten en technische metadata — geen names/addresses/emails/transcripties.

## Diagrammen, filters en bewijs

Elk KPI-resultaat toont bronvelden, kolom-grain, teller/noemer, nullbeleid, filters, pipeline-stappen, beslissing-ID, testbewijs en veilige analysetabel. DV4 gebruikt exact dezelfde DV1- en DV2-berekeningen; geen nieuwe verborgen score.

## Wijziging, review en release

1. Lees documentatie + Git-status, definieer wijziging en acceptatietest.
2. Analyseer bron read-only, documenteer mogelijke aannames, vraag studentgoedkeuring.
3. Implementeer klein, test, reconcileer, documenteer.
4. Update `beslissingslogboek.md` en andere getroffen `.md`.
5. Commit elke werkende stap op een branch, pas nadat de wijziging is bekeken. Geen push, merge of deploy zonder toestemming.

## Gevalideerd en nog open

Gevalideerd:
- Dataset, bestandsschema, encoding (latin-1) en kolombetekenis: zie `data-exploration.md` en logboekrij 13.
- Caching in Streamlit (`st.cache_resource`) en een veilige publicatieset (`data/published/`, 13 analysekolommen, SHA-256-controle).
- Deployment: Streamlit Community Cloud, publiek, https://dataco-verbeterkansen.streamlit.app (logboekrij 19). Licentie en bronvermelding: logboekrij 13.

Nog open:
- Eigen aanvullende tests van de student (optioneel).

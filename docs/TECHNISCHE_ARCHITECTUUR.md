# Technische architectuur — implementatieoverdracht

## Componenten

```text
read-only data/raw/  --(read + SHA-256)--> pipeline.py (pure functies)
                                        |-- schema-/grainaudit
                                        |-- kwaliteitscontrole/cleaning
                                        '-- metadata van input/output en dropredenen
                                                 |
                                         data/processed/<nieuwe-versie>
                                         + provenance JSON + hashes
                                                 |
                                analysis/kpis.py + analysis/evidence.py
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

## Immutable data en privacy

- `data/raw/`: alleen lezen. SHA-256 controleren vóór/na pipeline. Origineel nooit aanpassen, verplaatsen, verwijderen of overschrijven.
- `data/processed/`: **uitsluitend nieuwe** datasets met provenance; houd versie en verwerking bij. Overschrijf niet zonder expliciete toestemming.
- `.gitignore` sluit `data/raw`, `data/processed`, `data/public`, `data/private` en secrets uit. Vereenvoudigd demo-data mag alleen na privacy- en licentiecontrole publiek gedeeld worden.
- Auditrapporten en Markdown bevatten alleen veilige tellingen, geaggregeerde resultaten en technische metadata — geen names/addresses/emails/transcripties.

## Diagrammen, filters en bewijs

Elk KPI-resultaat toont bronvelden, kolom-grain, teller/noemer, nullbeleid, filters, pipeline-stappen, beslissing-ID, testbewijs en veilige analysetabel. DV4 gebruikt exact dezelfde DV1–DV3-berekeningen; geen nieuwe verborgen score.

## Wijziging, review en release

1. Lees documentatie + Git-status, definieer wijziging en acceptatietest.
2. Analyseer bron read-only, documenteer mogelijke aannames, vraag studentgoedkeuring.
3. Implementeer klein, test, reconcileer, documenteer.
4. Update `beslissingslogboek.md` en andere getroffen `.md`.
5. Commit elke werkende stap op een branch, pas nadat de wijziging is bekeken. Geen push, merge of deploy zonder toestemming.

## Nog te valideren

- Echte dataset, bestandsschema, encodings en kolombetekenis.
- Performantie op de volledige bron, data caching in Streamlit en veilige publicatieset.
- Deploymentinstellingen, live URL, access control en data-licentie.
- Eigen aanvullende tests van de student (optioneel).

# Traceerbaarheid per deelvraag — bindende acceptatiecriteria (V3)

**Status: geïmplementeerd.** De app (zes pagina's, pijplijn, tests en publicatiebundel) is af en staat online
(https://dataco-verbeterkansen.streamlit.app); zie `README.md` en `beslissingslogboek.md`. Dit document blijft de lijst
met acceptatiecriteria per deelvraag, met de regels voor bewijs en status (`PENDING` / `VALIDATED`) die de app naleeft.

## Overkoepelend: één reproduceerbare bewijsketen

Iedere gepubliceerde KPI, grafiek, aanbeveling en verklarende zin moet worden opgebouwd uit:

1. **Raw bron**: hash, kolommen, betekenis/eenheden, oorspronkelijke rijgrain.
2. **Read-only audit**: nulls, sleutel(cardinaliteit), statusconflicten, winst-additiviteit en kortingseenheden.
3. **Pure pipeline**: iedere transformatie afzonderlijk testbaar; per stap naam, input-output,
   exclusieve uitsluitingsredenen, korte veilige voorbeeldpreview en codefunctieverwijzing.
4. **Processed**: nieuwe versie in `data/processed/` met provenance-manifest (raw + output SHA-256,
   transformaties, aantallen, beslissings-ID). **Nooit** een raw bestand wijzigen of vervangen.
5. **KPI en visualisatie**: goedgekeurde formule, teller/noemer waar van toepassing, juiste grain,
   filtercontext, getal, veilige onderliggende *geaggregeerde* tabel, testbewijs.
6. **Interpretatie**: conclusie op basis van dezelfde berekende cijfers, met onzekerheid,
   interpretatiegrenzen en waar nodig minimumaantallen.

**De source of truth is Python-data, niet de tekst in een Markdown-uitleg.**
`analysis/evidence.py` definieert een eerste gedeeld bewijscontract. Claude moet echte
berekeningen laten terugkeren als data + bijpassende evidence; koppelingen en filters moeten
real-time kloppen. `PENDING` mag nooit automatisch `VALIDATED` worden door het bestaan van
bestanden of een geslaagde structurele test.

## DV1 — Omzet, winst, gewogen marge

- Groepering per `Market` × `Category Name` op de door de audit bevestigde orderregelbron.
- Bevestig dat `Sales` en het winstveld werkelijk additief zijn; reconciliatie bron → markt → categorie.
- Winstmarge = 100 × som(valide winst) / som(valide omzet), niet gemiddelde van rijmarges.
- Toon sommen, noemer, N orderregels en uitzonderingen. De kaart, plot en detailtabel gebruiken dezelfde filters.

## DV2 — Leverbetrouwbaarheid

- Bevestig statusmapping en bepaal wat 'vertraagd', 'onbekend' en 'geannuleerd' betekenen.
- Werk op unieke `Order Id` na controle op statusconflicten; geen stilzwijgende `first()`.
- Per markt/categorie expliciete definitie van toegerekende orderpopulatie, en waarschuwing
  dat één order in meerdere categorieën kan voorkomen; niet als één algemeen totaal optellen.
- Toon teller, noemer, eventuele uitsluitingen en een geanonimiseerd onderbouwingsvoorbeeld.

## DV3 — Kortingen en marges

- Bepaal via audit of korting is opgeslagen als 0,2 of 20% en kies goedgekeurde behandeling.
- Definieer kortingsklassen, nul/missing beleid, steekproefomvang en correlatiemethode.
- Toon observaties die meetellen, geaggregeerde statistiek, scatterplot en expliciet
  dat correlatie geen causale verklaring is.

## DV4 — Verbeterprioriteiten

- Bouw uitsluitend op dezelfde **gevalideerde** DV1- en DV2-aggregaties (omzet, marge, % vertraagd); DV3 (korting) is een vervolgstap.
- Vereis vooraf goedgekeurde regels, drempels, minimaal aantal orders en tie-breaks.
- Toon voor ieder segment de onderliggende omzet, winst, marge, % vertraagd, het aantal orders en de reden van
  rangschikking. Terug te volgen naar DV1, DV2 en de methode (via gedeelde filtercontext).
- Geen verzonnen eurobesparingen, oorzakelijke uitspraken of resultaten uit mock-upbeelden.

## Data & Methode en publieke veiligheid

- Eén rijentrechter met alle daadwerkelijke exclusieve drop-redenen. Aggregatie van orderregels
  naar orders staat apart vermeld als **grain-wijziging, geen data-uitval**.
- `st.expander()` per echte pipelinefunctie: input/output, uitgesloten aantallen,
  redenverdeling, veilige data-preview vóór/na en codefunctienaam.
- Processed manifest tonen met veilige provenance-metadata, zonder lokale privé-paden of PII.
- Gedeelde globale filters (markt, categorie, periode) gelden consistent voor elk KPI en plot;
  de globale raw-audit blijft steeds gebaseerd op de onbewerkte dataset.
- Alle zes Streamlit-pagina's werken; publieke dataset/licentie/privacy is separaat goedgekeurd.

## Bewijs en kwaliteitscontrole

- Pytest: duplicaten, nulls, statusconflict, twee categorieën per order, nulomzet,
  discount unit/klasse grenzen, rijconservatie, DV4 tie-break en minimum N, filterreconciliatie,
  raw hash ongewijzigd, processed no-overwrite, privacyveilige publicatie.
- Herleidbaarheid in de app: DV4 prioriteit → DV1 en DV2 → bewijssectie → pipeline → processed provenance → raw brongranulariteit.
- Elke PASS-status krijgt een concrete uitvoer/test/URL/commit; anders `PENDING`/`NOT VERIFIED`.

**Geen tweede app of ML toevoegen.**

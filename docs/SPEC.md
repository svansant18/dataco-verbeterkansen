# DataCo — Functionele & technische specificatie van de Streamlit-onderzoeksapp

**Versie:** 1.0 · 15 november 2026  
**Status:** functionele specificatie van de app; businessdefinities volgen het beslissingslogboek.  
**Prioriteit:** dit document concretiseert `README.md` en vervangt geen reeds goedgekeurde bron-/KPI-beslissingen in `beslissingslogboek.md`.  
**Doelgroep:** ontwikkelaar/student en Claude Code.  
**Verplichte bijlage voor implementatiebewijs:** `docs/TRACEERBAARHEID_PER_DEELVRAAG.md` (DV1–DV4, E1/E2, processed provenance, QA). Deze bijlage is aanvullend bindend maar vervangt geen goedgekeurde businessbeslissingen.

---

## 0. Samenvatting en niet-onderhandelbare uitgangspunten

Bouw **één Python/Streamlit-app** met **zes logisch gescheiden pagina's** (soms hieronder 'subapps' genoemd). Gebruik géén zes losstaande Streamlit-processen en géén aparte EDA-app.

1. Executive Overview
2. DV1 — Omzet & Winst
3. DV2 — Leverbetrouwbaarheid
4. DV3 — Kortingen & Marges
5. DV4 — Verbeterprioriteiten
6. Data & Methode (met Data Quality, KPI-definities, aannames en beslissingslogboek als tabs)

**Centrale onderzoeksvraag**  
*Welke markten en productcategorieën bieden DataCo de grootste verbetermogelijkheden wanneer we omzet, winstgevendheid en leverbetrouwbaarheid samen analyseren?*

**DV1:** Welke markten en productcategorieën realiseren de hoogste omzet en winst, en waar blijven de marges achter?  
**DV2:** Welke markten en productcategorieën hebben het hoogste percentage vertraagde verzendingen?  
**DV3:** In welke mate hangen kortingspercentages samen met de gerealiseerde winstmarges?  
**DV4:** Welke markt-categoriecombinaties verdienen prioriteit op basis van hun commerciële prestaties en operationele risico's?

**Kernprincipe:** van elk getal, elk inzicht en elke aanbeveling moet de gebruiker kunnen teruggaan naar actieve filters, bronkolommen, granulariteit, transformaties, formules, uitzonderingen en controles. Een mooi dashboard zonder bewijs is onvoldoende.

**Voorkom schijnzekerheid:** toon geen 'gevalideerd' zonder bewijs, verzin geen ontbrekende kolommen, verzin geen uitkomsten en doe geen causale uitspraken over correlaties.

## 1. Ontwerpprincipes / look & feel

### 1.1 Stijl

- Rustig **licht canvas** (`#F7F9FC` of gelijkwaardig), **donkerblauwe header** (`#102A52`) en blauw/teal/violet als spaarzame accenten. Geen uitgebreide donkere zijbalk.
- Ruime witruimte; wit/lichtgrijs voor kaarten, subtiele borders, afgeronde hoeken. Eén visuele hiërarchie: titel → vraag → KPI's → maximaal **twee hoofdvisualisaties** → korte conclusie → optionele bewijslaag.
- Maximaal vier KPI-kaarten bovenaan een pagina; bij DV3 eventueel drie. Geen onnodige decoratieve grafieken.
- Positief/negatief niet uitsluitend met kleur aangeven; labels, units en betekenis van kleur altijd expliciet. Kleuren consistent tussen pagina's (omzet blauw, winst teal, marge violet, vertraging amber/rood).
- Desktop `layout="wide"`; op smalle schermen stapelen kolommen. Geen vaste pixelbreedtes voor dashboards; gebruik Streamlit-componenten en Plotly responsief.
- Tekst van de app in **het Nederlands**; technische kolomnamen behouden hun oorspronkelijke spelling in de methodologie.
- Kleine, altijd zichtbare aanduiding van datasetstatus: **demo / niet gevalideerd / gevalideerd**. Bepaal status op basis van echt bewijs, niet op basis van het bestaan van een bestand.

### 1.2 Navigatie

- Bovenaan de app: zes tabachtige navigatiekeuzes, volgorde zoals onder §0. **Geen sidebar voor primaire navigatie**.
- Aanbevolen implementatie: `st.Page` met `st.navigation([...], position="top")` en `page.run()`; vereiste Streamlit-versie volgens de geïnstalleerde API vastleggen. Gebruik een **éénmalig routerframe** in `app.py`.
- De globale filters zitten bovenaan het gedeelde frame: **Markt**, **Productcategorie** en **Orderdatum/periode**. 'Alle' is de standaard. Filterwaarden komen uit gevalideerde data.
- Filters blijven bij page switching behouden (shared widget keys / `st.session_state`). Een DV-pagina kan aanvullend eigen analysetabs/filters tonen.
- Navigatie moet in maximaal één klik van een overzicht naar de betreffende DV gaan.
- Geen afzonderlijke 'Conclusie'-pagina: de samenvattende conclusie komt onderaan **Overview** en het onderbouwde advies op **DV4**.
- Optioneel: 'Reset filters' en teruglink naar Overview. Niet verplicht: downloadknoppen voor veilige geaggregeerde resultaten.

### 1.3 Vaste informatiearchitectuur per deelvraag

Bovenaan: **titel, exacte deelvraag, actieve filters, KPI's en relevante grafieken**. Daaronder altijd:

1. **Analyse** — hoofdgrafieken en korte feitelijke inzichten.
2. **Hoe is dit berekend?** — uitklapbaar, met bronkolommen, KPI-ID's, formule, teller/noemer, grain, actieve filters, pipeline-stap, eventueel classificatiegrenzen en goedgekeurde beslissing.
3. **Onderliggende data** — uitklapbare veilige, inspecteerbare **geaggregeerde** tabel, met aantallen en een preview van relevante bronvelden/voorbeeldrecords waar dit publiek/privacyveilig is; geen persoonsgegevens.

Technisch: `st.expander` onder de hoofdgrafieken. Een DV-pagina mag daarnaast `st.tabs(["Analyse", "Details"])` gebruiken als dat de visuele rust verbetert; de twee bewijs-expanders blijven vindbaar.

---

## 2. De pagina's, exacte informatie en visuele acceptatie

### 2.1 Executive Overview

**Doel:** centrale onderzoeksvraag in één oogopslag, geen allesomvattende analyse en geen tweede informatiepaneel onder elk cijfer.

**Bovenkant:** projectnaam + korte subregel *Van ruwe data tot onderbouwde verbeterprioriteiten*. De centrale vraag in een compacte lichte banner (inklapbaar op mobiel).

**Vier KPI-kaarten**, alleen na validatie:
- Omzet (valuta, aggregatie over geldige financiële bronregels).
- Winst (valuta en gevalideerde additiviteit van het winstveld).
- Winstmarge (%) = totaal gevalideerde winst / totaal gevalideerde omzet × 100; **niet** het ongewogen gemiddelde van individuele marges.
- Vertraagde orders (%) = teller/noemer op gevalideerde ordergranulariteit; zie DV2 en §4.

**Twee hoofdvakken naast elkaar:**
1. Omzet per markt (horizontale gesorteerde balken, eventueel winst als klein tweede segment; keuze duidelijk in legenda).
2. Top verbeterprioriteiten: maximaal drie markt-categoriecombinaties met reden (DV4), als korte tabel of prioriteitskaarten; **geen tweede drukke heatmap op Overview**.

**Onderkant:** één compacte 'Wat leren we?'-samenvatting (2–3 evidence-based bullets) en de knop **Bekijk DV4**. Eventuele proceslijn *Bron → Audit → KPI → Analyse → Inzicht* hoogstens een kleine, collapsible rij. Bewijsdetails blijven op DV- en Data & Methode-pagina's.

**Fallback:** bij ontbreken van gevalideerde data toon heldere status 'Nog geen geverifieerde uitkomsten' en link naar Data & Methode; geen fictieve cijfers.

### 2.2 DV1 — Omzet & Winst

**Doel:** commerciële prestaties per markt en categorie tonen en aantonen waar marges achterblijven.

**KPI's:** omzet, winst, gewogen winstmarge, geldige orderregels / eventueel unieke orders (beide ondubbelzinnig gelabeld).

**Visualisatie A:** gesorteerde omzet & winst per markt (gegroepeerde bars of twee afzonderlijke reeksen met gedeelde betekenisvolle schaal).  
**Visualisatie B:** winstmarge-heatmap Markt × Productcategorie, met aantallen of datadekking in hover; geen impliciete 'goed/slecht' labeling zonder drempel.

**Details:** een geaggregeerde tabel Markt, Categorie, Omzet, Winst, Marge%, Aantal orderregels, Unieke orders (als toepasbaar). Sorteren op omzet/marge. Eventueel top/bottom met minimumaantal.

**Bewijs:** benoem verschil tussen optellen van winst en optellen van een reeds geaggregeerd/ordergebonden winstveld. Bij niet-additieve winst: definieer correct nieuw aggregatiepad, anders geen winstgrafiek.

**Inzicht:** één tot drie feitelijke bevindingen, consequenties en beperkingen, gegenereerd uit de echte berekende tabellen; nooit hardcoded demo-inzichten.

### 2.3 DV2 — Leverbetrouwbaarheid

**Doel:** robuust percentage vertraagde orders per markt en categorie tonen.

**KPI's:** unieke in aanmerking komende orders, aantal vertraagde orders, percentage vertraagde orders, aandeel orders met onbekende/uitgesloten status.

**Visualisatie A:** gesorteerde bars % vertraagde orders per markt, met numerator/denominator in hover.  
**Visualisatie B:** heatmap Markt × Productcategorie van het % vertraagde orders; lage aantallen markeren of filteren conform goedgekeurde minimumdrempel.

**Businesscontract, pas definitief na audit:**
- Onderzoek `Order Id`, `Order Item Id`, `Delivery Status`, eventueel `Late_delivery_risk` en de beschikbare datumvelden; behoud werkelijke bronkolomnamen uit de CSV.
- **Eén order telt maar één keer binnen een groep** bij de KPI 'percentage vertraagde orders'. De inhoudelijke statusdefinitie en behandeling van `Shipping canceled`, onbekend, inconsistent en onvolledig moeten worden geaudit en goedgekeurd.
- Eén order kan **meerdere productcategorieën bevatten**. Binnen iedere markt-categoriecombinatie telt die order één keer, maar sommatie van categorie-aantallen hoeft NIET gelijk te zijn aan het totaal aantal unieke orders. Dat verschil staat zichtbaar in de tooltip en uitleg.
- Als orderregels voor hetzelfde order-ID verschillende statuswaarden hebben, toon de inconsistenties; kies niet stilzwijgend `first()`.
- Als later 'vertraagde verzending' en 'vertraagde bezorging' verschillen volgens de brondefinitie, label de gekozen KPI overeenkomstig. Vergelijkbare definities expliciet houden.

**Bewijs:** voorbeelden van tellers/noemers en het `drop_duplicates`/orderaggregatiepad; test met een handgemaakt order met meerdere orderregels en twee categorieën.

### 2.4 DV3 — Kortingen & Marges

**Doel:** beschrijvende samenhang tussen korting en marge tonen, niet een oorzakelijk effect.

**KPI's:** centrale kortingsmaat (definitie), gewogen winstmarge, geldig aantal orderregels; correlatie alleen indien statistisch verantwoord.

**Visualisatie A:** scatterplot korting% (x) versus regel- of ordergebonden marge% (y), met hover bij veilige data, bij groot volume een **deterministische of duidelijk beschreven steekproef** / densityplot. Een regressielijn is optioneel en nooit bewijs voor causaliteit.

**Visualisatie B:** gemiddelde/gewogen marge per kortingsklasse met aantallen (tabel of boxplot). Mogelijke demonstratieklassen: 0%, >0–5%, >5–10%, >10–20%, >20%; **klassen worden definitief door student goedgekeurd**.

**Controle:** is `Order Item Discount Rate` een fractie 0–1 of percentage 0–100? Zo niet homogeen, rapporteren en niet blind verdubbelen. Marges bij nulomzet worden `N/A` (geen 0%-waarde). Bepaal of een regelgebonden marge afleidbaar is uit dezelfde regelwinst/omzet.

**Bewijs:** aantal waarnemingen na filters, afwijkende waarden, uitsluitingsgronden, gebruikte kortingsklassen en correlatieconfiguratie (Pearson/Spearman of geen).

**Interpretatietekst:** 'Samenhang, geen oorzakelijk bewijs'. Kleine categorieën en databeperkingen vermelden.

### 2.5 DV4 — Verbeterprioriteiten

**Doel:** direct de centrale vraag beantwoorden met een begrijpelijke, reproduceerbare prioriteitenregel.

**Invoer:** uitsluitend gevalideerde geaggregeerde Markt × Categorie-KPI's uit DV1–DV3; *geen nieuwe brondefinities* in DV4.

**Visualisatie A:** bubbeldiagram x = % vertraagde orders; y = gewogen winstmarge%; bubbelgrootte = omzet. Hover toont markt, categorie, omzet, winst, marge, late percentage, aantallen en reden voor classificatie.

**Visualisatie B:** gesorteerde Top 5 (of 10) combinaties met reden, expliciet gebruikte drempels, databasis/steekproefgrootte en prioriteitslabel.

**Voorstel voor prioriteitslogica, ter goedkeuring — niet hardcoderen vóór akkoord:**
- Minimum **30 unieke relevante orders** per markt-categoriecombinatie voor een stabiele shippingvergelijking. Segmenten onder dit minimum krijgen 'onvoldoende data', géén 'laag risico'.
- Vergelijk marge en vertraging met vooraf vastgelegde data-afhankelijke referenties (bv. globale gewogen marge respectievelijk globale late rate) en volume met omzetkwartielen. De exacte drempels worden na de audit met de student overeengekomen.
- Houd liefst **transparante beslisregels in plaats van een arbitraire samengestelde 0–100-score**. Voorbeeld classificaties: 'Prioriteit — hoge omzet, lage marge én hoog leverrisico', 'Optimaliseren — hoog leverrisico', 'Monitoren — laag volume of aandachtspunt', 'Sterk — geen duidelijke risicocombinatie'. Deze labels zijn pas definitief na goedkeuring.
- Gebruik deterministische sortering (prioriteitsklasse, omzet dalend, naam alfabetisch) en documenteer tie-breaks.
- Een 'verbeterkans' is een hypothese/onderzoekprioriteit, **geen bewezen eurobesparing**. Geen fictief besparingspotentieel op de kaart.

**Korte afsluiting op deze pagina:** één alinea met expliciet antwoord op de centrale onderzoeksvraag + drie actievoorstellen (oorzaken onderzoeken, korting/marge verifiëren, monitoren). Alleen dataondersteunde conclusies; geen bewezen causaliteit claimen.

**Bewijs:** klikbare/uitklapbare prioriteitsregel met gebruikte variabelen, exacte drempels, in aanmerking komende records, uitgesloten groepen, tie-breaks en beslissings-ID.

### 2.6 Data & Methode — bewijscentrum

**Doel:** de gebruiker kan in de app zelf de totale route van CSV tot inzichten inspecteren.

**Vier interne tabs binnen dezelfde pagina (geen extra pagina):**
1. **Rijentrechter & Pipeline** (standaard actief)
2. **Data-audit**
3. **KPI-definities & Formules**
4. **Aannames & keuzes**

#### Tab 1 — Rijentrechter & Pipeline

- Rijentrechter van het aantal **bronrijen**: `start → na validatie → na cleaning → analysebasis`. Ieder verschil moet met *onderling exclusieve* primaire uitsluitingsredenen verklaard worden. Som uitsluitingsredenen = aantal echte weggegooide bronrijen.
- Apart paneel 'Grainconversies': `N bronregels → M unieke orders`, `P markt-categorie combinaties` en eventueel `Q order-categorie relaties`. Dit is **aggregatie**, geen data-uitval en hoort niet onterecht in dezelfde trechter.
- Voor **iedere verwerkingsstap** een `st.expander`: naam functie, doel, input/outputaantallen, aantallen per uitsluitingsreden, relevante kolommen, een privacyveilige datavoorbeeldweergave NA de stap, eventuele validatiefouten.
- Expander voor `Read` en `Schema audit`; `Validation`; `Cleaning`; `Order/orderline-granularity`; `KPI input preparation`; `Aggregation`. Alleen feitelijk uitgevoerde stappen groen markeren.
- Bij filtering onderscheid tussen **globale pipeline-trechter (ongefilterde bron)** en **actieve analysepopulatie (na markt/categorie/periodefilters)**. Laat filters de historische globale rijentrechter niet verkeerd herschrijven.

#### Tab 2 — KPI-definities & Formules

- Tabel met: KPI-ID, label, betekenis, formule, teller, noemer, eenheid, grain, bronkolommen, populatie, uitval/NULL-regels, aggregatie, pipeline-stap, beslissing-ID, beperkingen.
- Gebruik **één metadataregister in Python** als bron voor de UI en de tests, niet een herhaalde handmatige uitleg op iedere pagina.
- Voor elk KPI: minimaal één kleine rekenvoorbeeldtabel met **fictieve** of geanonimiseerde waarden om de logica uit te leggen. Label die als didactisch voorbeeld, niet als DataCo-uitkomst.
- Voor iedere DV kunnen gebruikers een specifiek KPI-ID kiezen en de herkomstinformatie lezen.

#### Tab 3 — Data Quality & Aannames

- Grootte van de dataset, kolommen, nulls, duplicaten, conflicterende orderstatussen, anomalieën, uitsluitingen, consistentiecheck per KPI.
- Maak aannames expliciet, bijv. `order-status`, `order-categorie-overlap`, `gewogen marge`, `kortingseenheid`, `minimum-aantal orders`, `dataset dekking`.
- Geen gefingeerde volledig-groen-status. Bij onzekerheid 'Open / Nog niet gecontroleerd'.
- Waarschuw voor volledige data die meer `Customer Email`, `Customer Password` of andere identificatoren kunnen bevatten: deze nooit zichtbaar maken in publieke previews.

#### Tab 4 — Beslissingen & Tests

- Alleen **goedgekeurde** keuzes + rationale + referentie naar `beslissingslogboek.md` en testbewijs (testnaam / git commit indien beschikbaar). Open keuzes apart als `PENDING`.

---

## 3. Technische architectuur / bestanden

**Beperk architectuur tot noodzakelijke lagen.** Vertrek vanuit het bestaande minimale starterpakket. Voeg geen tweede app, groot framework, database of Power BI toe.

```text
project-root/
├── README.md                       # Wat en waarom
├── CLAUDE.md                       # Ontwikkelregels voor Claude Code
├── app.py                          # Streamlit-router + gedeelde filters
├── views/                         # Zes pagina's in één Streamlit-proces
│   ├── overview.py
│   ├── dv1.py
│   ├── dv2.py
│   ├── dv3.py
│   ├── dv4.py
│   └── methode.py
├── ui/common.py                    # Herbruikbare UI en bewijs-expanders
├── pipeline.py                     # Pure data-audit en ETL; geen Streamlit
├── analysis/kpis.py               # Pure KPI-hulpfuncties; DV1–DV4 uitbouwen
├── tests/                         # pytest voor data, grain, KPI en structuur
├── beslissingslogboek.md          # Beslissingen en aannames (V2.1 + V3 samengevoegd)
├── docs/                          # SPEC, KPI_REGISTER, ONDERZOEKSONTWERP, traceerbaarheid, architectuur
├── data/raw/                       # Immutabele lokale bron: genegeerd door Git
├── data/processed/                 # Alle gewijzigde data + provenance: genegeerd door Git
└── requirements.txt
```

De implementatie mag eenvoudiger zijn als Claude kan aantonen dat alle gebruikersfunctionaliteit aanwezig blijft; **geen dubbele businesslogica in de UI**. `app.py` is het gezamenlijke frame en router. `views/*.py` bevatten enkel paginalayout, `analysis` de berekeningen. `pipeline.py` levert een gestructureerde audit voor de Streamlit-expanders.

### 3.1 Pseudocode voor navigatie en gedeelde filters

```python
import streamlit as st

st.set_page_config(page_title="DataCo | Supply Chain Insights", layout="wide")
# Init shared state, get approved data status, render global market/category/date filters.
# Define six st.Page objects with unique url_path values.
# pg = st.navigation(pages, position="top")
# pg.run()
```

Geen sidebar radio uit de huidige starter meer; migratie mag **na vrijgave van de pipeline-ready-poort** in een aparte commit. Gebruik `st.navigation(position="top")` (Streamlit-versie controleren) voor zes pagina's. De filters moeten vóór `pg.run()` gemaakt worden, zodat hun waarden tussen pagina's behouden blijven.

### 3.2 Gecentraliseerd dataresultaat

`run_pipeline(source)` produceert minimaal:

- `financial_rows`: veilige gevalideerde orderregelbasis.
- `order_shipping`: gevalideerde unieke orderstatusbasis, als de audit dit toelaat.
- `order_category_shipping`: gecontroleerde order-categorie-relaties voor DV2.
- `stage_audit`: tabellen van uitsluitend echt verwijderde bronrijen per stap, redenen en aantallen.
- `grain_audit`: unieke orders, orderregels, overlaps, inconsistenties en cardinaliteit.
- `quality_report`: missings/invalids en resultaat van checks.
- `source_manifest`: bestandsnaam/hash, importtijd en relevante schema-informatie (geen persoonsgegevens).

Het object mag een dataclass/dict zijn. Het mag **niet** afhankelijk zijn van Streamlit. Hergebruik dezelfde gevalideerde output in alle zes pagina's.

### 3.3 KPI-/evidencecontract

Iedere zichtbare metriek en iedere kolom in de DV4-tabel moet herleidbaar zijn naar metadata:

```text
metric_id, label, unit, source_columns, logical_grain,
eligible_population, formula, numerator, denominator,
aggregation, filters, missing_value_rule, pipeline_stages,
decision_id, validation_test_ids, caveat
```

Metadata wordt niet handmatig in elke visualisatie gedupliceerd. Alle tabellen en grafieken moeten het actuele filtercontract delen. Bij gewijzigde filters de KPI's opnieuw uit de gevalideerde *gefilterde* basis berekenen en het aantal gebruikte records actualiseren.

---

## 4. KPI-businessregels en open data-audit

### 4.1 Audit vóór implementatie

De Data Auditor rapporteert **feitelijke** naam/spelling, type, aantal nulls, cardinaliteiten en semantiek van minimaal de volgende verwachte DataCo-velden (niet stilzwijgend aannemen dat ze in de lokale bron exact zo heten):

| Logisch veld | Mogelijke DataCo-kolom | Waarom controleren? |
|---|---|---|
| Order ID | `Order Id` | Grain voor leverbetrouwbaarheid |
| Orderregel ID | `Order Item Id` | Grain voor financiën/kortingen |
| Markt | `Market` | Groepering |
| Categorie | `Category Name` | Groepering |
| Omzet | `Sales` | Optellen alleen na controle |
| Winst | `Order Profit Per Order` | Mogelijk misleidende naam / additiviteit |
| Korting | `Order Item Discount Rate` | Fractie of percentage? |
| Levering | `Delivery Status`, `Late_delivery_risk` | Betekenis van vertraagd, onbekend/geannuleerd |
| Datum | `order date (DateOrders)` o.i.d. | Periodefilter en parsing |

Genereer een read-only auditrapport inclusief uitzonderingen en voorstellen. Bij conflicten formuleert Claude één korte vraag aan de student met impact op DV1–DV4. **Geen inhoudelijke regels definitief implementeren voordat de betrokken keuzes goedgekeurd zijn.**

### 4.2 Voorlopige KPI-formules (geen fictieve verificatie)

- **Revenue** = som van een gevalideerd additief verkoopveld op het correcte grain. Controles voor negatieve/nulwaarden en mogelijke retours.
- **Profit** = som van gevalideerde **additieve regelwinst** of correct afgeleide waarde. Bevestig dat de bron geen per-order totaal herhaalt over orderregels.
- **Profit Margin %** = 100 × `sum(valid_profit)` / `sum(valid_sales)`; als noemer nul of ongeldig, toon `N/A` en tel deze groep in quality report.
- **Late Shipping %** = 100 × `count_distinct(late eligible orders)` / `count_distinct(eligible orders)`. De precieze label-/statusmap wordt expliciet goedgekeurd.
- **Discount %** = geverifieerde kortingseenheid; voor DV3 kies *expliciet* of het regelniveau-gemiddelde, gewogen kortingspercentage of een ander getal op de KPI-kaart staat. Gebruik geen verwisselbare maatnamen.
- **Correlation** = gekozen statistische samenhang tussen geldige paren op één consistent observatiegrain, `n` tonen en de methode benoemen; na data-audit beslissen of deze metriek voldoende onderbouwd is.
- **Priority** = reproduceerbare, goedgekeurde classificatie met minimaal relevante omvang, bekende marges, bekende verzendstatus, per segment verklaarde criteria; geen verzonnen score of eurobesparing.

### 4.3 Cruciale edge cases

1. Eén order met 3 regels en 2 categorieën: unieke order = 1 totaal; maximaal 1 per categorie; categorieën niet optellen tot algemeen ordertotaal.
2. Order met verschillende statussen op regels: stop of zet in 'onbeslist' volgens expliciete keuze; geen willekeurige `first`.
3. Ontbrekende/ongeldige status: toon aparte kwaliteitscategorie en sluit alleen uit de specifieke KPI-noemer als goedgekeurd; indien geen orders overblijven `N/A`.
4. Korting 0.20 versus 20: auditeer units; dubbele omzetting voorkomen.
5. Geldige marge bij zero sales? geen deling door nul, toon `N/A`.
6. Eén segment met zeer weinig orders: expliciet label 'onvoldoende data' voordat een ranking mogelijk is.
7. Negatieve winst/marge: mag niet stilzwijgend verwijderd worden, tenzij businessregel.
8. Datumfilter: orderdatum, niet zomaar verzenddatum; tijdzone/format check.
9. Bronwaarden met PII: nooit in scherm/tabel/export/log/public Git; data-audit mag kolomnamen rapporteren.
10. Aggregatie van orderregels naar orders telt **niet** als rijverlies in de datakwaliteitstrechter.

---

## 5. Traceerbaarheid: van ruwe data naar conclusie

**Verplichte keten per resultaat:**

```text
Bronbestand + bronkolommen
    → schema-/grain-audit
    → expliciete kwaliteitsregels
    → analysepopulatie + actieve filters
    → KPI-formule en teller/noemer
    → aggregatie (markt × categorie)
    → grafiek / tabel
    → feitelijk inzicht
    → DV4-prioriteitsregel + voorgestelde actie
```

Per grafiek of KPI moet 'Hoe is dit berekend?' aantonen:

- **WAT:** beschrijving, eenheid, exacte formule en gekozen grain.
- **WAAR:** bronkolommen, populatie en pipelinefuncties.
- **HOEVEEL:** recordaantal, teller, noemer, uitgesloten/ongeldige waarnemingen.
- **WAAROM:** gemaakte aannames, goedgekeurde beslissing, caveat.
- **CONTROLE:** reproduceerbare tests en eventueel rekenvoorbeeld.

Per conclusie/advies:

- Bewijzende KPI-waarden en segmenten noemen; nooit tekst genereren die niet uit die tabellen volgt.
- Vergelijkingsdrempel en referentieperiode vermelden.
- Benoem **onzekerheid** en alternatieve verklaringen.
- Onderscheid een aanwijzing voor verbetering van een bewezen oorzaak of bewezen besparing.

## 6. Filtering, caching, betrouwbaarheid en privacy

- Globale filters werken op DV1–DV4 en Overview, behoud bij navigatie. Markt/categorie-opties komen uit geauditeerde data. Datumfilter standaard volledige beschikbare periode.
- Een filter met nul geldige rijen geeft een heldere **geen data**-melding en KPI=`N/A`, zonder kapotte grafieken.
- De **globale bronrijentrechter** gebruikt altijd het volledige bronbestand. Toon apart de gefilterde analysepopulatie; geen misleidende vergelijking van filters met data cleaning.
- `st.cache_data` voor deterministische geverifieerde tabellen. Bij nieuwe data/parameters een juiste cache key of invalidatie. Geen verborgen stale output.
- Plotly-grafieken waar interactieve hover nodig is; pandas voor grouping; Streamlit native cards/tabs/expanders voor UI. Geen zware custom CSS tenzij noodzakelijk.
- Dataset heeft mogelijk identificerende kolommen. `data/raw/` en secrets niet committen of publiek hosten. Bescherm geen persoonsgegevens enkel door kolommen in de frontend te verbergen; gebruik **afgeleide, gereviewde veilige data** voor publieke deployment. Bewijs de brontransformatie lokaal; publiceer alleen geaggregeerde methodologie-data en veilig gemaakte previews.
- CSV-exports uitsluitend geaggregeerd en privacy-reviewed. Eén deelvraag mag geen autorisatie vereisen; voorkom dat een openbare URL privédata ontsluit.
- Als veilige publieke databasis niet beschikbaar is, geen deployment met raw CSV forceren: eerst expliciet privacybesluit.
- **Bronbescherming:** profielrapporten (`write_profile`) worden nooit binnen `data/raw/` of `data/processed/` weggeschreven. Processed datasets blijven versiegebonden en immutabel.

---

## 7. Acceptatiecriteria

| ID | Acceptatiecriterium | Vereist bewijs |
|---|---|---|
| E1 | Elk belangrijk getal is te verklaren | Klik in de app op 'Hoe is dit berekend?', formule, bron en aantallen zichtbaar |
| E2 | Alle echt uitgesloten bronrijen zijn verantwoord | Rijentrechter + `st.expander` per stap + redenen die optellen |
| E3 | Aannames/beperkingen expliciet | Data & Methode, bij DV2/DV3/DV4 en in het logboek |
| E4 | Concrete beslissingen | Logboek: keuze, alternatieven, reden, impact, datum/status |

**Geen criterium vooraf als PASS markeren.** Een structurele pytest die `app.py` ziet bewijst nog niet dat appfunctionaliteit werkt.

### Minimale tests (uitbreiden na echte audit)

1. Stage-conservation: in = out + exclusieve uitsluitingsredenen.
2. Niet-additieve herhaalde orderwinst detecteren of correct uitsluiten.
3. Unieke orders dedupliceren bij meerdere orderregels.
4. Eén order in twee categorieën: categorie-aantallen mogen niet als totaal gebruikt worden.
5. Conflict tussen orderstatussen => expliciete unresolved-fout/status.
6. Nulomzet => marge `N/A`.
7. Kortingseenheid en grensgevallen rond kortingsklassen.
8. Eén gesorteerd DV4-resultaat uit gecontroleerde voorbeeld-KPI's, inclusief tie-break en minimum N.
9. Filterconsistentie (zelfde scope voor KPI, plot en detailtabel).
10. **Eigen test van de student** (optioneel): een testcase na review 'wat testen de bestaande tests niet?', met eigen redenering in het logboek.

### Streamlit-interactiechecks

- Alle zes pagina's openen zonder runtimefouten.
- Markt/categorie/periodefilter wijzigt alle passende KPI's en visualisaties, niet de globale bron-audit.
- Alle DV-pagina's tonen beide bewijs-expanders; geen persoonsgegevens in hun voorbeelden.
- Lege datasets, nulnoemers en open definities veroorzaken geen crash en tonen geen valse cijfers.
- DV4-prioriteit herleidbaar tot DV1/2/3-metingen.

---

## 8. Definitie van gereed (Definition of Done)

**Functioneel:** zes pagina's, werkende topnav en consistente filters, valide KPI's uit echte CSV, DV1–DV4 grafieken, transparante DV4-aanbeveling, methodologie en kwaliteitsinformatie.

**Technisch:** pure `pipeline.py`; scheiding UI/businesslogic; geauditeerde ordergranulariteit; exacte rijentrechter; reproduceerbare pytest-suite; geen data leak; app lokaal en veilig publiek bereikbaar.

**Uitlegbaarheid:** alle belangrijke cijfers zijn uitlegbaar **in de Streamlit-app zelf**.

**Status in dit document:** specificatie; het bewijs dat iets werkt zijn de tests en de app zelf.


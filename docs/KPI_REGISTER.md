# KPI-register

Dit is het register van alle KPI's in de app, met per KPI de formule, de populatie en de controles. De **bron van waarheid** is `analysis/evidence.py`
(`KPI_REGISTER`); in de app staat hetzelfde onder *Data & Methode → KPI-definities*. Dit bestand is daaruit gemaakt, en een test
(`test_kpi_register_document_matches_the_code`) bewaakt dat ze niet uit elkaar lopen.

| KPI-ID | KPI | DV | Formule | Teller | Noemer | Grain | Beslissing |
|---|---|---|---|---|---|---|---|
| K-REV | Omzet (netto, na korting) | DV1 | som(Order Item Total) over de orderregels in de analysebasis | som Order Item Total | - | orderregel | D-007 |
| K-PROFIT | Winst | DV1 | som(Order Profit Per Order); veld verschilt binnen een order, dus regelgebonden en additief | som winst | - | orderregel | D-007 |
| K-MARGIN | Gewogen winstmarge | DV1 | 100 x som(winst) / som(omzet) - NIET het gemiddelde van regelmarges | som winst | som omzet | markt x categorie (uit regels) | D-007 |
| K-ORDERS | Unieke orders / orderregels | DV1 | nunique(Order Id) en count(Order Item Id) in de analysebasis | - | - | order resp. orderregel | D-007 |
| K-LATEPCT | % vertraagde orders | DV2 | 100 x vertraagde in aanmerking komende orders / in aanmerking komende orders | orders met Delivery Status = 'Late delivery' | orders met Delivery Status <> 'Shipping canceled' | unieke order (per markt x categorie) | D-008 |
| K-EXCL | Uitgesloten orders (Shipping canceled) | DV2 | orders met Delivery Status = 'Shipping canceled' (uit de noemer van K-LATEPCT) | uitgesloten orders | alle orders in de selectie | unieke order | D-008 |
| K-DISC | Marge per kortingsklasse | DV3 | gewogen marge per kortingsklasse (som winst / som omzet) | som winst | som omzet | orderregel | D-009 |
| K-CORR | Correlatie tussen korting en regelmarge | DV3 | Spearman = Pearson op de rangen van het kortingspercentage en de regelmarge (winst / omzet) per orderregel; Pearson staat ter vergelijking in de hulptekst | - | - | orderregel | D-009 |
| K-PRIO | Verbeterprioriteit | DV4 | min. 30 orders; Prioriteit = omzet >= mediaan van kwalificerende segmenten EN marge < referentiemarge EN vertraging > referentie-% | - | - | markt x categorie | D-010 |

## Per KPI: bron, ontbrekende waarden, controles en beperking

### K-REV · Omzet (netto, na korting)

- **Eenheid:** EUR/USD (bronvaluta niet vastgelegd)
- **Bronkolommen:** `Order Item Total`
- **Ontbrekend of nul:** geen ontbrekende waarden in de analysebasis (pipeline-stap Validatie)
- **Pipeline-stappen:** Validatie → Opschonen → Analysebasis (omzet/winst)
- **Controles (tests):** `tests/test_dataco_kpis.py::test_stage_conservation`; `tests/test_dataco_kpis.py::test_filter_consistency`
- **Beperking:** Omzet = Order Item Total (na korting), omdat het winstveld daarop is gebaseerd (A-1, bevestigd in logboek 3). Bruto Sales staat in de detailtabel.

### K-PROFIT · Winst

- **Eenheid:** zelfde valuta
- **Bronkolommen:** `Order Profit Per Order`
- **Ontbrekend of nul:** negatieve winst blijft behouden (geen stille verwijdering)
- **Pipeline-stappen:** Validatie → Analysebasis (omzet/winst)
- **Controles (tests):** `tests/test_dataco_real_pipeline.py::test_profit_is_line_level_in_real_data`
- **Beperking:** Additiviteit geverifieerd: de waarde varieert binnen 45.902 orders; ze is geen herhaald ordertotaal.

### K-MARGIN · Gewogen winstmarge

- **Eenheid:** %
- **Bronkolommen:** `Order Profit Per Order`, `Order Item Total`
- **Ontbrekend of nul:** omzet <= 0 geeft N/B (geen 0%)
- **Pipeline-stappen:** Analysebasis (omzet/winst)
- **Controles (tests):** `tests/test_dataco_kpis.py::test_margin_is_weighted_not_mean_of_margins`; `tests/test_dataco_kpis.py::test_zero_revenue_margin_is_nan`
- **Beperking:** Marges van kleine groepen zijn instabiel; kijk altijd naar het aantal regels/orders.

### K-ORDERS · Unieke orders / orderregels

- **Eenheid:** aantal
- **Bronkolommen:** `Order Id`, `Order Item Id`
- **Ontbrekend of nul:** -
- **Pipeline-stappen:** Analysebasis (omzet/winst)
- **Controles (tests):** `tests/test_dataco_kpis.py::test_order_with_two_categories_counts_once_per_group`
- **Beperking:** Een order met meerdere categorieën telt in elke categorie mee: categorie-aantallen zijn géén ordertotaal.

### K-LATEPCT · % vertraagde orders

- **Eenheid:** %
- **Bronkolommen:** `Order Id`, `Delivery Status`, `Market`, `Category Name`
- **Ontbrekend of nul:** noemer 0 geeft N/B; groepen < 30 orders worden gemarkeerd 'onvoldoende data'
- **Pipeline-stappen:** Order x categorie-grain
- **Controles (tests):** `tests/test_dataco_kpis.py::test_order_with_two_categories_counts_once_per_group`; `tests/test_dataco_kpis.py::test_conflicting_status_raises`; `tests/test_dataco_kpis.py::test_canceled_shipping_out_of_denominator`
- **Beperking:** 'Advance shipping' en 'Shipping on time' tellen als niet-vertraagd. Late_delivery_risk is in de bron identiek aan Late delivery (0 afwijkingen).

### K-EXCL · Uitgesloten orders (Shipping canceled)

- **Eenheid:** aantal / %
- **Bronkolommen:** `Delivery Status`
- **Ontbrekend of nul:** -
- **Pipeline-stappen:** Order x categorie-grain
- **Controles (tests):** `tests/test_dataco_kpis.py::test_canceled_shipping_out_of_denominator`
- **Beperking:** Deze orders vallen ook buiten de omzet/winst-analysebasis (D-007): beide populaties zijn identiek.

### K-DISC · Marge per kortingsklasse

- **Eenheid:** %
- **Bronkolommen:** `Order Item Discount Rate`, `Order Item Discount`, `Sales`, `Order Profit Per Order`, `Order Item Total`
- **Ontbrekend of nul:** omzet <= 0 geeft geen marge (N/B)
- **Pipeline-stappen:** Analysebasis (omzet/winst)
- **Controles (tests):** `tests/test_dataco_kpis.py::test_discount_class_boundaries`
- **Beperking:** Kortingsklassen: D-009, goedgekeurd (logboek 9). Korting is een fractie 0-0,25. Teller en noemer zijn de totalen van de hele selectie; de marge per klasse staat in de staafgrafiek en de tabel.

### K-CORR · Correlatie tussen korting en regelmarge

- **Eenheid:** correlatiecoëfficiënt (-1 tot +1)
- **Bronkolommen:** `Order Item Discount Rate`, `Order Profit Per Order`, `Order Item Total`
- **Ontbrekend of nul:** regels met omzet <= 0 vallen uit de correlatie
- **Pipeline-stappen:** Analysebasis (omzet/winst)
- **Controles (tests):** `tests/test_kpis.py::test_spearman_with_ties_matches_hand_calculation`; `tests/test_dataco_real_analytics.py::test_dv3_spearman_matches_independent_rank_correlation`
- **Beperking:** Samenhang, geen oorzakelijk bewijs. Berekend op alle orderregels in de selectie, niet op de steekproef van 5.000 punten in de scatter.

### K-PRIO · Verbeterprioriteit

- **Eenheid:** klasse
- **Bronkolommen:** `K-REV`, `K-MARGIN`, `K-LATEPCT`
- **Ontbrekend of nul:** < 30 orders of onbekende marge = 'Onvoldoende data' (nooit 'laag risico')
- **Pipeline-stappen:** DV1 → DV2
- **Controles (tests):** `tests/test_dataco_kpis.py::test_priority_min_orders_and_tiebreak`
- **Beperking:** Hypothese/onderzoeksprioriteit, geen bewezen oorzaak of eurobesparing. Referenties = gewogen totalen van alle markten en categorieën in de gekozen periode; een filter op markt of categorie zoomt alleen in.

## Afspraken

- Een KPI krijgt pas een plaats in dit register met een formule, een bronveld, een grain, een regel voor ontbrekende waarden, een beslissing en minstens één test.
- Bij een nieuwe of gewijzigde KPI pas je `analysis/evidence.py` aan en maak je dit bestand opnieuw; de test faalt als ze niet overeenkomen.
- Geen fictieve uitkomsten opnemen. Categorie-aantallen van unieke orders kunnen overlappen en zijn niet zonder meer optelbaar.
- Correlatie is geen oorzakelijk bewijs.

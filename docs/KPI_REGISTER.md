# KPI-register — definities nog te bevestigen met echte dataset

De kolomnamen hieronder zijn **kandidaten uit de gebruikelijke DataCo-dictionary**, geen bewezen velden in jouw lokale CSV. De Data Auditor controleert betekenis en grain voordat de implementatie als geldig geldt.

| KPI-ID | KPI | Voorlopige logica | Grain / bron | Status |
|---|---|---|---|---|
| FIN-01 | Omzet | Som van geldige `Sales` waarden | Orderregel als bronveld additief is | PENDING AUDIT |
| FIN-02 | Winst | Som van een **gevalideerd additief** winstveld | Eerst auditen (`Order Profit Per Order` kan misleidend heten) | PENDING AUDIT |
| FIN-03 | Winstmarge | `100 × SUM(gevalideerde winst) / SUM(omzet)` | Markt/categorie, gewogen | PENDING AUDIT |
| OPS-01 | % vertraagde orders | `100 × unieke vertraagde orders / unieke geldige orders` | Order binnen markt/categorie; statusmapping open | PENDING AUDIT |
| COM-01 | Kortingspercentage | Audit schaal `0.2` vs `20`; bepaal aggregatieweging | Orderregel | PENDING AUDIT |
| COM-02 | Kortingsklasse | Indeling naar vooraf goedgekeurde drempels | Orderregel | PENDING DECISION |
| STAT-01 | Korting-marge samenhang | Correlatie waar statistisch verantwoord | Audit onafhankelijke observaties, missings, extreme waarden | PENDING DECISION |
| RISK-01 | Verbeterprioriteit | Transparante, goedgekeurde beslisregels op FIN/OPS/COM | Markt × categorie, met minimum N | PENDING DECISION |

## Vereiste registratie na audit

Voor elke KPI: beschrijving, eenheid, exact bronveld, juiste grain, teller/noemer, geldige populatie, nul-/missingpolicy, filters, pure Python-functie, eventuele statuscode, beslissing-ID en bewijs-test.

**Geen fictieve KPI-uitkomsten opnemen.** Bij ontbrekende definities de app N/B laten tonen. Categorie-aantallen van unieke orders kunnen overlappen en zijn niet zonder meer optelbaar. Correlatie is géén oorzakelijkheid.

**V4:** bij elke nieuwe gevalideerde KPI wordt dit register tegelijk met de pure Python-berekening en test bijgewerkt. Alleen een goedgekeurde keuze verandert `PENDING` in een concrete definitie.

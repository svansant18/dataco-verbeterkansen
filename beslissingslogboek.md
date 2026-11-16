# Beslissingslogboek — DataCo verbeterkansen

Samengevoegd uit het V2.1-logboek (nummers `#1`–`#11`) en het V3-logboek (`D-001`–`D-013`, `A-1`–`A-5`).
Elke beslissing staat één keer in dit bestand; de oude nummers staan tussen haakjes in de kolom **ID**.

**Status:** `Geldt` = de app volgt deze beslissing · `Open` = nog te bevestigen door Steve · `Vervangen` / `Vervallen` = door Steve vervangen of geschrapt
(staat onderaan, met de reden) · `Niet overgenomen` = hoort bij V3-onderdelen die in dit project niet bestaan.

"(nog in te vullen door Steve)" in de kolom *Waarom* betekent dat de reden van Steve zelf ontbreekt; die vul ik niet in.
`—` betekent dat de bron (V3) die informatie niet noteerde.

## 1. Beslissingen die gelden

| ID | Datum | Beslissing | Voorstel van de AI | Wat ik deed | Waarom | Alternatief dat ik overwoog | Status |
|---|---|---|---|---|---|---|---|
| D-001 | 2026-11-16 | Onderzoek: centrale vraag met precies DV1–DV4 (omzet/winst, leverbetrouwbaarheid, kortingen/marges, prioriteiten) | Optie 1 | aanvaard | — | — | Geldt |
| D-002 (+ S-1) | 2026-11-16 | Eén Streamlit-app met zes pagina's (Overview, DV1–DV4, Data & Methode) en navigatie bovenaan, zonder zijbalk | Eén app met `st.navigation(position="top")` | aanvaard | — | Aparte sub-apps per deelvraag (V2.1-opzet) | Geldt |
| D-003 | 2026-11-16 | Vormgeving: rustige witte contentruimte, donkerblauwe bovenbalk, weinig grafieken per pagina | — | aanvaard | — | — | Geldt |
| D-004 | 2026-11-16 | Traceerbaarheid: "Hoe is dit berekend?" en "Onderliggende data" bij elke DV; Data & Methode apart | — | aanvaard | — | — | Geldt |
| D-006 | 2026-11-16 | Bron = `DataCoSupplyChainDataset.csv` (180.519 regels, 53 kolommen, latin1, orders 2015-01-01 t/m 2018-01-31). De licentie en publieke herbruikbaarheid zijn niet gecontroleerd | — | bron aanvaard | — | — | Geldt (licentie **Open**) |
| D-007 (#1) | 2026-11-16 | Geannuleerde en fraude-orders weglaten uit omzet, winst en leverpercentage: CANCELED 3.692 + SUSPECTED_FRAUD 4.062 = 7.754 regels (2.855 orders); analysebasis = 172.765 regels. `Shipping canceled` zijn exact dezelfde rijen. Negatieve winst blijft staan (32.295 regels). Het winstveld `Order Profit Per Order` is regelgebonden en optelbaar | Weglaten van `CANCELED` en `SUSPECTED_FRAUD`; overige statussen blijven | aanvaard | Geannuleerde en fraude-orders geven een vertekend beeld voor de deelvraag omdat het geen omzet is | Enkel `COMPLETE` en `CLOSED` houden (79.107 rijen); of alles houden | Geldt |
| A-1 (#3) | 2026-11-16 | Omzet = `Order Item Total` (netto, na korting), niet `Sales` (bruto). `Total = Sales − Discount` klopt voor 100% van de analyseregels (`data-exploration.md` noemt 99,3% op alle rijen; dat verschil is niet verder onderzocht). De winstratio uit de bron klopt voor 96,4% van de regels met `Order Item Total` en voor 17,7% met `Sales` | Omzet na korting als hoofdmaat | aanvaard | Het meest logisch is dat we de omzet na korting geven | Bruto omzet `Sales`; of beide tonen (bruto staat in de detailtabellen) | Geldt (door Steve aanvaard als #3; V3 had dit nog als *Open*) |
| D-007b (#2, #4) | 2026-11-16 | Marge = `Order Profit Per Order` / `Order Item Total`, **gewogen**: som(winst) / som(omzet), niet het gemiddelde van regelmarges. Dit komt overeen met `Order Item Profit Ratio` | Marge op omzet na korting; gewogen, zodat grote orders zwaarder meetellen | aanvaard | #2: omdat we met de omzet na korting werken, gebruiken we die ook voor de marge. #4: (nog in te vullen door Steve) | Marge op `Sales` (omzet voor korting); gemiddelde van de marge per orderlijn | Geldt |
| D-008 | 2026-11-16 | Vertraagd = `Delivery Status` = `Late delivery`. `Advance shipping` en `Shipping on time` = niet vertraagd. `Shipping canceled` (7.754 regels) gaat uit de noemer en wordt apart gerapporteerd. Geen order met tegenstrijdige statussen; een onbekende status stopt de pijplijn | — | aanvaard | — | — | Geldt |
| A-2 | 2026-11-16 | DV2 gebruikt alle orders buiten `Shipping canceled`; dat valt samen met de omzetbasis (D-007): dezelfde 62.897 orders | — | geverifieerd | Kruistabel: `Shipping canceled` = CANCELED + SUSPECTED_FRAUD, geen overlap met andere statussen | — | Geldt |
| A-3 | 2026-11-16 | Het datumfilter werkt op `order date (DateOrders)`, formaat `%m/%d/%Y %H:%M`, einddag inclusief | — | geverifieerd | 0 onparseerbare datums | — | Geldt |
| #6 | 2026-11-16 | DV2: een order telt mee in elke categorie die erin zit. Op de V3-pijplijn nagerekend: 42.634 van 62.897 orders hebben meer dan één categorie; 152.630 paren van order en categorie | In elke categorie meetellen | aanvaard | (nog in te vullen door Steve) | Enkel tellen bij de categorie met de meeste omzet, zodat elke order één keer telt | Geldt |
| D-009 (#9) | 2026-11-16 | DV3: kortingsklassen 0% / >0–5% / >5–10% / >10–20% / >20% en gewogen kortingspercentage (som korting / som `Sales`). Eenheid van korting is een fractie 0–0,25 | Vijf klassen volgens V3 | aanvaard (Steve koos op 2026-11-16 de V3-indeling boven zijn eigen zes klassen, zie §2) | (nog in te vullen door Steve) | Zes klassen van 5 procentpunt (V2.1 #9) | Geldt |
| A-5 (#8) | 2026-11-16 | DV3: scatter van een deterministische steekproef van 5.000 orderlijnen (seed 42), met Spearman- en Pearson-correlatie op regelniveau | Steekproef + beide correlaties | aanvaard (Steve koos op 2026-11-16 voor V3, zie §2) | (nog in te vullen door Steve) | Twee scatters per kortingsniveau (18 punten) en per markt × categorie (162 punten) (V2.1 #8) | Geldt, maar V3 had dit als *Open*: bevestigen |
| D-010 (#10, #11, A-4) | 2026-11-16 | DV4: een combinatie van markt × categorie heeft minstens **30 unieke in aanmerking komende orders** nodig. **Prioriteit** = omzet ≥ mediaan van de kwalificerende segmenten **én** marge onder de referentiemarge **én** vertraging boven de referentie. Referenties = gewogen totalen van de actieve selectie. Vier klassen: Prioriteit, Optimaliseren, Monitoren, Sterk. Geen score, en DV3 telt niet mee | V3-regel | aanvaard (Steve koos op 2026-11-16 de V3-regel boven zijn kwadranten en drempel 300, zie §2) | (nog in te vullen door Steve) | Kwadranten met rangschikking op omzet en drempel 300 (V2.1 #10, #11); gecombineerde score met gewichten; twee aparte rangschikkingen | Geldt |
| A-4 | 2026-11-16 | DV4: de referenties voor marge en vertraging volgen de actieve filters, niet vast de hele dataset. Klassen kunnen dus veranderen als je filtert | Referentie volgt de selectie | — | Houdt DV4 consistent met DV1/DV2 onder dezelfde selectie | Vaste referentie op de volledige dataset | **Open**, bevestigen |
| #5 | 2026-11-16 | Minimumdrempel van 30 voor betrouwbare cijfers: V2.1 telde orderlijnen en markeerde de marge met `*`. In de V3-app telt de drempel **unieke orders** en worden te kleine segmenten uitgesloten (DV1-tekst, DV2-heatmap leeg, DV4 `Onvoldoende data`). Het getal 30 blijft | Drempel van 30, combinaties blijven in de resultaten | aanvaard (V2.1) | (nog in te vullen door Steve) | Die combinaties weglaten, of een andere drempel (of geen) gebruiken | Geldt in de V3-vorm; eenheid (orders i.p.v. lijnen) **bevestigen** |

## 2. Beslissingen in deze sessie (ombouw van V2.1 naar de V3-functies)

| ID | Datum | Beslissing | Voorstel van de AI | Wat ik deed | Waarom | Alternatief dat ik overwoog | Status |
|---|---|---|---|---|---|---|---|
| S-1 | 2026-11-16 | V2.1 wordt omgebouwd naar de V3-structuur: één app met `views/`, `ui/`, `analysis/` en globale filters. De sub-apps `pipeline_dataco`, `dv1`–`dv4` en de lege `explore_raw_data/` verdwijnen op de branch `v3-functioneel` (`main` blijft ongewijzigd) | V3-structuur overnemen | aanvaard | (nog in te vullen door Steve) | De sub-apps behouden en de V3-functies erin bouwen | Geldt |
| S-2 | 2026-11-16 | Omvang: app, pijplijn, tests en docs worden overgenomen. Docent-check, no-AI-onderdelen, agents, skills, hooks, sprint-scripts, CI en presentatie niet | App + tests + docs | aanvaard | Steve: de docent-check en no-AI zijn niet nodig | Alles behalve docent en no-AI; of enkel de app | Geldt |
| S-3 | 2026-11-16 | Bij botsingen tussen V2.1 en V3 wint V3, per botsing beslist: DV3-klassen, DV3-scatter, DV4-regel en drempel, en de tab Verzendmethode in DV2 vervalt | V3 op alle vier | aanvaard | (nog in te vullen door Steve) | V2.1-keuzes behouden | Geldt |
| S-4 | 2026-11-16 | `data/raw/` bevat drie CSV's. De V3-code zocht "precies één CSV"; nu wordt vast `DataCoSupplyChainDataset.csv` gebruikt (tests en pijplijn). De omschrijving en `tokenized_access_logs.csv` blijven buiten scope | — | technische aanpassing | Zonder deze aanpassing vindt de app geen bron | Andere bestanden uit `data/raw/` verplaatsen (niet toegestaan: `data/raw/` is read-only) | Geldt |

| S-5 | 2026-11-16 | DV3: de Spearman-correlatie wordt berekend als Pearson op de gemiddelde rangen, niet met `Series.corr(method="spearman")`. Dat laatste importeert `scipy.stats`, en `scipy` staat niet in `requirements.txt`. Op de 172.765 orderlijnen is het resultaat gelijk (−0,0013017408699874354 met scipy, −0,001301740869987438 zonder; verschil 3·10⁻¹⁸). Een test bewaakt dit, ook met gelijke waarden | Review met Context7 vond de verborgen scipy-afhankelijkheid; twee opties: rangcorrelatie of scipy toevoegen | aanvaard: rangcorrelatie | Geen extra package nodig (CLAUDE.md afspraak 3) en een lichte `requirements.txt`. (Reden van Steve zelf: nog in te vullen) | `scipy==1.18.1` toevoegen aan `requirements.txt` (code blijft identiek aan V3) | Geldt |

## 3. Vervangen of vervallen (V2.1)

| Oud ID | Beslissing in V2.1 | Wat ermee gebeurd is | Vervangen door |
|---|---|---|---|
| #7 | DV2: extra tab Verzendmethode (percentage vertraagd verschilt per methode sterk: 40% tot 100%; per markt nauwelijks) | **Vervallen**: de tab zit niet in V3 en Steve koos op 2026-11-16 voor weglaten. De bevinding zelf is niet weerlegd | — |
| #8 | DV3: twee scatters in aparte tabs (18 en 162 punten); per orderlijn zou 172.765 punten in 18 verticale stroken geven | **Vervangen** | A-5 |
| #9 | DV3: zes kortingsklassen (0% / 1–5 / 6–10 / 11–15 / 16–20 / 21–25%) | **Vervangen** | D-009 |
| #10 | DV4: kwadranten; probleem = marge onder het totaal (12,0%) of vertraging boven het totaal (57,3%); rangschikking op omzet; DV3 telt niet mee | **Vervangen** | D-010 |
| #11 | DV4: minstens 300 orderlijnen, instelbaar van 30 tot 1.000. Onderbouwing: onder ca. 300 lijnen is een marge grotendeels ruis (standaardfout ca. 2,7 procentpunt tegenover een verschil van 4,8 tussen combinaties) | **Vervangen**: de V3-regel gebruikt 30 orders. De ruisredenering blijft inhoudelijk geldig en is een argument om de drempel later te verhogen | D-010 |

## 4. Niet overgenomen uit V3

| ID | Onderwerp | Reden |
|---|---|---|
| D-005 | AI-werkwijze met hoofdsessie, drie review-agents en drie skills | Agents en skills zitten niet in dit project (S-2) |
| D-012 | `data-analyst` en `/data-viz` toevoegen | Idem |
| D-013 | Verplicht contextcheckpoint en documentatie-updates via scripts | De scripts en hooks zitten niet in dit project (S-2) |
| D-011 | Release: geen `data/published/`-bundel; de app leest lokaal de ruwe CSV en is niet deploybaar op Community Cloud zonder bundel | Deployen valt buiten deze ombouw; blijft **Open** als je later wilt publiceren |

## Sjabloon voor een nieuwe beslissing

Gebruik `/timtim:logboek`, of voeg een rij toe met: ID, datum, beslissing, voorstel van de AI, wat ik deed (aanvaard / aangepast / verworpen), waarom, alternatief, status.

*Het logboek is een geheugensteun. De bewijslast van een belangrijke KPI moet ook in de Streamlit-app toegankelijk zijn.*

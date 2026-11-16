# Dataverkenning: DataCo supply-chain

Alle cijfers zijn berekend op `data/raw/DataCoSupplyChainDataset.csv` (ongewijzigd). De pijplijn
(`pipeline.py`) toont dezelfde informatie live in de app, op de pagina Data & Methode.

## Bronnen (`data/raw/`)

| Bestand | Inhoud | Gebruikt? |
|---|---|---|
| `DataCoSupplyChainDataset.csv` | 180 519 orderlijnen x 53 kolommen (96 MB) | **Ja**, alle deelvragen |
| `DescriptionDataCoSupplyChain.csv` | Omschrijving per kolom | Documentatie |
| `tokenized_access_logs.csv` | Weblog (Product, Category, Date, Month, Hour, Department, ip, url) | Nee, buiten scope |

## Inlezen

- Encoding is **latin-1**: inlezen als utf-8 geeft een `UnicodeDecodeError`.
- Geen dubbele rijen. De kolomnamen in de CSV hebben geen overtollige spaties (die staan enkel in de omschrijving).

## Structuur: een rij is een orderlijn, geen order

- 180 519 unieke `Order Item Id` (een rij per orderlijn), maar slechts **65 752 unieke `Order Id`**, met maximaal 5 lijnen per order.
- Per order zijn `Market`, orderdatum en `Late_delivery_risk` overal gelijk (0 orders met afwijkende waarden). Ontdubbelen op `Order Id` voor leveringsstatistieken is dus veilig.
- **Gevolg voor DV2:** een percentage vertraagde *unieke orders* vraagt ontdubbelen op `Order Id`; tellen op rijen geeft een ander getal.

## Periode en datatypes

- Orderdatums lopen van **2015-01-01 t/m 2018-01-31**. De laatste order is van 2018-01-31 23:38.
- Typen in de ruwe data: 29 numerieke kolommen en 24 tekstkolommen. Daaronder zitten 2 datumkolommen als **tekst** (`order date (DateOrders)`, `shipping date (DateOrders)`, formaat `m/d/jjjj u:mm`). De pijplijn zet de twee datumkolommen om naar datetime.

## Ontbrekende waarden

| Kolom | Leeg |
|---|---|
| `Product Description` | 100% (180 519) |
| `Order Zipcode` | 155 679 (86%) |
| `Customer Lname` | 8 |
| `Customer Zipcode` | 3 |

Alle andere kolommen zijn volledig ingevuld. `Product Status` is overal 0 en bevat dus geen informatie.

## Categorieen

- **`Market` (5):** LATAM 51 594 · Europe 50 252 · Pacific Asia 41 260 · USCA 25 799 · Africa 11 614 (rijen).
- **`Category Name`:** 50 productcategorieen, zeer ongelijk verdeeld (Cleats 24 551 rijen, `As Seen on TV!` 68). Sommige namen hadden een spatie achteraan (`'Cameras '`, `'Books '`, `'CDs '`, `'Baby '`).
- Ook `Order Region` (17 925 waarden), `Product Name` (1 774) en `Department Name` (362) hadden spaties vooraan of achteraan. De pijplijn trimt dat.
- **`Order Status` (9):** COMPLETE 59 491 · PENDING_PAYMENT 39 832 · PROCESSING 21 902 · PENDING 20 227 · CLOSED 19 616 · ON_HOLD 9 804 · SUSPECTED_FRAUD 4 062 · CANCELED 3 692 · PAYMENT_REVIEW 1 893.
- **`Delivery Status` (4):** Late delivery 98 977 · Advance shipping 41 592 · Shipping on time 32 196 · Shipping canceled 7 754.
- **`Shipping Mode` (4):** Standard Class 107 752 · Second Class 35 216 · First Class 27 814 · Same Day 9 737.
- **`Type` (4):** DEBIT 69 295 · TRANSFER 49 883 · PAYMENT 41 725 · CASH 19 616.

## Verbanden tussen kolommen (gecontroleerd)

| Bevinding | Gevolg |
|---|---|
| `Late_delivery_risk` = 1 precies wanneer `Delivery Status` = "Late delivery" | Dezelfde informatie, kies er een en benoem welke. |
| "Shipping canceled" (7 754) staat bij `Late_delivery_risk` = 0 | Geannuleerde zendingen tellen mee als "niet laat" tenzij je ze uit de noemer haalt (**aanname**). |
| `Late_delivery_risk` komt in 97,5% van de rijen overeen met "echte dagen > geplande dagen" | De vlag volgt niet overal de dagenkolommen; kies bewust welke je gebruikt. |
| `Benefit per order` = `Order Profit Per Order` (100%) | Dubbele kolom. |
| `Sales per customer` = `Order Item Total` (100%) | Dubbele kolom. |
| `Category Id` = `Product Category Id` (100%) | Dubbele kolom. |
| `Product Price` = `Order Item Product Price` (100%) | Dubbele kolom. |
| `Sales` = `Order Item Product Price` x `Order Item Quantity` (100%) | `Sales` is bruto, vóór korting. |
| `Order Item Total` = `Sales` - `Order Item Discount` (99,3%) | Bijna altijd; 0,7% wijkt af. |
| `Order Item Discount` = `Sales` x `Order Item Discount Rate` (94,4%) | Een deel wijkt af (afrondingen of andere basis), nog uit te zoeken. |
| `Order Item Profit Ratio` = `Order Profit Per Order` / `Order Item Total` (100%) | Dit is de marge, op omzet na korting. |
| `Order Profit Per Order` is negatief bij 33 784 rijen | Een groot deel van de lijnen is verlieslatend. |
| `Days for shipping (real)` loopt van 0 tot 6 dagen | |
| Elke markt heeft 3 tot 6 `Order Region`-waarden en elke regio hoort bij precies één markt | `Order Region` is een verfijning van `Market`. |

## Privacy

`Customer Email` en `Customer Password` zijn gemaskeerd (`XXXXXXXXX`). `Customer Fname`, `Customer Lname` en `Customer Street` zijn persoonsgegevens. Ze zijn niet nodig voor de deelvragen en de pijplijn verwijdert ze (stap 3).

## Welke kolommen horen bij welke deelvraag? (voorstel, nog te bevestigen)

| Deelvraag | Kolommen |
|---|---|
| **DV1 Omzet & winst** | `Market`, `Order Region`, `Category Name`, `Order Id`, `Order Item Id`, `order date (DateOrders)`, `Sales`, `Order Item Total`, `Order Profit Per Order`, `Order Item Quantity`, `Order Status` |
| **DV2 Leverbetrouwbaarheid** | `Order Id`, `Market`, `Category Name`, `Delivery Status`, `Late_delivery_risk`, `Days for shipping (real)`, `Days for shipment (scheduled)`, `Shipping Mode`, `Order Status` |
| **DV3 Kortingen & marges** | `Order Item Discount`, `Order Item Discount Rate`, `Order Item Profit Ratio`, `Order Profit Per Order`, `Sales`, `Order Item Total`, `Market`, `Category Name` |
| **DV4 Prioriteiten** | Samengesteld uit DV1 t/m DV3 per markt x categorie |

## Hoe betrouwbaar is een marge op weinig orderlijnen? (onderbouwing van de drempel in DV4)

De marge per orderlijn (`Order Item Profit Ratio`) heeft een standaardafwijking van **0,467**. Een gemiddelde over *n* lijnen heeft dan een standaardfout van ongeveer 0,467 / wortel(*n*). Dit is een **ruwe schatting**: de app gebruikt de gewogen marge (som winst / som omzet), niet het gewone gemiddelde.

| Orderlijnen | Standaardfout van de marge |
|---|---|
| 30 | ca. 8,5 procentpunt |
| 100 | ca. 4,7 procentpunt |
| 300 | ca. 2,7 procentpunt |
| 1 000 | ca. 1,5 procentpunt |

Ter vergelijking: de marges van de 162 combinaties van markt en categorie verschillen onderling met een standaardafwijking van **4,8 procentpunt**. Onder ongeveer 300 lijnen is een verschil in marge tussen combinaties dus grotendeels ruis. Daarom is de drempel in DV4 instelbaar met 300 als standaard. 47 van de 162 combinaties hebben minder dan 100 lijnen (samen 1,5% van de omzet).

## Open vragen (aannames voor `beslissingslogboek.md`)

1. Tellen `CANCELED` en `SUSPECTED_FRAUD` mee in omzet en winst?
2. Hoe behandelen we "Shipping canceled" in het percentage vertraagde orders (in of uit de noemer)?
3. Welke maat voor marge: `Order Profit Per Order` / `Order Item Total` (= `Order Item Profit Ratio`) of op `Sales` (voor korting)?
4. Welke van de dubbele kolommen houden we als standaard?

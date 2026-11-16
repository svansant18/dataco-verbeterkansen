# Beslissingslogboek — DataCo verbeterkansen

| # | Datum | Beslissing | Voorstel van de AI | Wat ik deed | Waarom | Alternatief dat ik overwoog |
|---|---|---|---|---|---|---|
| 1 | 2026-11-16 | Geannuleerde en fraude-orders weglaten uit omzet, winst en leverpercentage (7 754 rijen, 2 855 orders; `Shipping canceled` is exact dezelfde rijen) | Weglaten van `CANCELED` en `SUSPECTED_FRAUD`; de overige statussen blijven | aanvaard | Geannuleerde en fraude orders geven een vertekend beeld voor de deelvraag omdat het geen omzet is | Enkel `COMPLETE` en `CLOSED` houden (79 107 rijen); of alles houden |
| 2 | 2026-11-16 | Marge = `Order Profit Per Order` / `Order Item Total` (omzet na korting) | Marge op omzet na korting; komt overeen met `Order Item Profit Ratio` | aanvaard | Omdat we met de omzet na korting gaan werken dienen we deze ook te gebruiken in de berekening van de marge | Marge op `Sales` (omzet voor korting) |
| 3 | 2026-11-16 | Omzet = `Order Item Total` (na korting) | Omzet na korting als hoofdmaat | aanvaard | Het meest logisch is dat we de omzet na korting geven | Bruto omzet `Sales`; of beide tonen |
| 4 | 2026-11-16 | Gewogen marge per markt en categorie: som(winst) / som(omzet) | Gewogen marge, zodat grote orders zwaarder meetellen | aanvaard | _(nog in te vullen door Steve)_ | Gemiddelde van de marge per orderlijn |
| 5 | 2026-11-16 | Marges op minder dan 30 orderlijnen markeren met * in de heatmap (waarschuwing, geen filter; 9 combinaties van markt x categorie) | Drempel van 30 orderlijnen, combinaties blijven in de resultaten | aanvaard | _(nog in te vullen door Steve)_ | Die combinaties weglaten, of een andere drempel (of geen) gebruiken |

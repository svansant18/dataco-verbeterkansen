# Onderzoeksontwerp — computationeel denken

**Status:** uitgangsontwerp van de analyse; de definitieve keuzes staan in `beslissingslogboek.md`.

## Centrale vraag

Welke markten en productcategorieën bieden DataCo de grootste verbetermogelijkheden wanneer we omzet, winstgevendheid en leverbetrouwbaarheid samen analyseren?

## Vier pijlers

1. **Decompositie:** splits de centrale vraag in DV1 omzet/winst/marge, DV2 vertraagde orders, DV3 korting/marge en DV4 geïntegreerde verbeterprioriteiten. DV4 gebruikt bevindingen uit DV1–DV3.
2. **Patroonherkenning:** zoek combinaties met veel omzet maar lage marge, ongewoon veel vertraagde orders, of verschillen in marges tussen kortingsklassen. Toon ook uitzonderingen en steekproefgroottes.
3. **Abstractie:** gebruik alleen betekenisvolle bronvelden; kies aantoonbaar een juist grain (order versus orderregel) en geldige tellers/noemers. Definieer markt × categorie en wees expliciet over categorie-overlap.
4. **Algoritme:** CSV lezen → schema/key/grain audit → expliciete cleaning → verifieerbare aggregatie → KPI's en filters → DV1–DV3 resultaten → transparante DV4-prioritering → conclusie met bewijslast.

## Oorspronkelijke ontwerpvereisten

- Schets eerst een overzicht met zes pagina's en drie globale filters.
- Maximaal twee hoofdvisualisaties per DV-pagina; uitgebreide uitleg in expanders.
- Maak voor elke DV expliciet de bronvelden, gegevensgranulariteit, formule, kwaliteitsregels en verwachte output zichtbaar.

## Te documenteren vóór coding

- Geselecteerde DataCo CSV + bron/licentie, exacte kolomnaam/eenheid/betekenis.
- Statusdefinitie 'vertraagde order', unknown/canceled en conflictpolicy.
- Eventuele noodzaak voor een minimumaantal orders bij DV2/DV4.
- Definitie van winst en gewogen marge, behandeling van nulomzet.
- Kortingsklassen en correlatie/steekproefbeleid.
- DV4-thresholds en vergelijking met welk referentiepunt.

Deze antwoorden worden pas bindend wanneer de student de keuzes in `beslissingslogboek.md` goedkeurt.

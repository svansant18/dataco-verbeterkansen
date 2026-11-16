"""Het KPI-register: voor elk getal in de app de bron, formule, regel bij ontbrekende waarden,
beslissing en de tests die het controleren. De uitklapper "Hoe is dit berekend?" toont dit rechtstreeks.
"""

# ---------------------------------------------------------------------------
# KPI register (single source for the UI explanations and the tests).
# ---------------------------------------------------------------------------
_T = "tests/test_dataco_kpis.py::"
_R = "tests/test_dataco_real_pipeline.py::"

KPI_REGISTER: dict[str, dict] = {
    "K-REV": dict(
        question_id="DV1", label="Omzet (netto, na korting)", unit="EUR/USD (bronvaluta niet vastgelegd)",
        source_columns=("Order Item Total",), grain="orderregel",
        formula="som(Order Item Total) over de orderregels in de analysebasis",
        numerator="som Order Item Total", denominator="-", aggregation="som per markt/categorie",
        missing_rule="geen ontbrekende waarden in de analysebasis (pipeline-stap Validatie)",
        pipeline_stages=("Validatie", "Opschonen", "Analysebasis (omzet/winst)"), decision_id="D-007",
        test_ids=(_T + "test_stage_conservation", _T + "test_filter_consistency"),
        caveat="Omzet = Order Item Total (na korting), omdat het winstveld daarop is gebaseerd (A-1, bevestigd in logboek 3). Bruto Sales staat in de detailtabel.",
    ),
    "K-PROFIT": dict(
        question_id="DV1", label="Winst", unit="zelfde valuta", source_columns=("Order Profit Per Order",), grain="orderregel",
        formula="som(Order Profit Per Order); veld verschilt binnen een order, dus regelgebonden en additief",
        numerator="som winst", denominator="-", aggregation="som per markt/categorie",
        missing_rule="negatieve winst blijft behouden (geen stille verwijdering)",
        pipeline_stages=("Validatie", "Analysebasis (omzet/winst)"), decision_id="D-007",
        test_ids=(_R + "test_profit_is_line_level_in_real_data",),
        caveat="Additiviteit geverifieerd: de waarde varieert binnen 45.902 orders; ze is geen herhaald ordertotaal.",
    ),
    "K-MARGIN": dict(
        question_id="DV1", label="Gewogen winstmarge", unit="%", source_columns=("Order Profit Per Order", "Order Item Total"), grain="markt x categorie (uit regels)",
        formula="100 x som(winst) / som(omzet) - NIET het gemiddelde van regelmarges",
        numerator="som winst", denominator="som omzet", aggregation="gewogen",
        missing_rule="omzet <= 0 geeft N/B (geen 0%)", pipeline_stages=("Analysebasis (omzet/winst)",), decision_id="D-007",
        test_ids=(_T + "test_margin_is_weighted_not_mean_of_margins", _T + "test_zero_revenue_margin_is_nan"),
        caveat="Marges van kleine groepen zijn instabiel; kijk altijd naar het aantal regels/orders.",
    ),
    "K-ORDERS": dict(
        question_id="DV1", label="Unieke orders / orderregels", unit="aantal", source_columns=("Order Id", "Order Item Id"), grain="order resp. orderregel",
        formula="nunique(Order Id) en count(Order Item Id) in de analysebasis", numerator="-", denominator="-", aggregation="telling",
        missing_rule="-", pipeline_stages=("Analysebasis (omzet/winst)",), decision_id="D-007",
        test_ids=(_T + "test_order_with_two_categories_counts_once_per_group",),
        caveat="Een order met meerdere categorieën telt in elke categorie mee: categorie-aantallen zijn géén ordertotaal.",
    ),
    "K-LATEPCT": dict(
        question_id="DV2", label="% vertraagde orders", unit="%", source_columns=("Order Id", "Delivery Status", "Market", "Category Name"), grain="unieke order (per markt x categorie)",
        formula="100 x vertraagde in aanmerking komende orders / in aanmerking komende orders",
        numerator="orders met Delivery Status = 'Late delivery'", denominator="orders met Delivery Status <> 'Shipping canceled'", aggregation="unieke orders per groep",
        missing_rule="noemer 0 geeft N/B; groepen < 30 orders worden gemarkeerd 'onvoldoende data'",
        pipeline_stages=("Order x categorie-grain",), decision_id="D-008",
        test_ids=(_T + "test_order_with_two_categories_counts_once_per_group", _T + "test_conflicting_status_raises", _T + "test_canceled_shipping_out_of_denominator"),
        caveat="'Advance shipping' en 'Shipping on time' tellen als niet-vertraagd. Late_delivery_risk is in de bron identiek aan Late delivery (0 afwijkingen).",
    ),
    "K-EXCL": dict(
        question_id="DV2", label="Uitgesloten orders (Shipping canceled)", unit="aantal / %", source_columns=("Delivery Status",), grain="unieke order",
        formula="orders met Delivery Status = 'Shipping canceled' (uit de noemer van K-LATEPCT)", numerator="uitgesloten orders", denominator="alle orders in de selectie", aggregation="telling",
        missing_rule="-", pipeline_stages=("Order x categorie-grain",), decision_id="D-008",
        test_ids=(_T + "test_canceled_shipping_out_of_denominator",), caveat="Deze orders vallen ook buiten de omzet/winst-analysebasis (D-007): beide populaties zijn identiek.",
    ),
    "K-DISC": dict(
        question_id="DV3", label="Marge per kortingsklasse en correlatie", unit="%", source_columns=("Order Item Discount Rate", "Order Item Discount", "Sales", "Order Profit Per Order", "Order Item Total"), grain="orderregel",
        formula="gewogen marge per klasse (som winst / som omzet); correlatie korting vs. regelmarge (Pearson en Spearman)",
        numerator="som winst", denominator="som omzet", aggregation="gewogen per klasse",
        missing_rule="omzet <= 0 valt uit de correlatie", pipeline_stages=("Analysebasis (omzet/winst)",), decision_id="D-009",
        test_ids=(_T + "test_discount_class_boundaries",),
        caveat="Kortingsklassen: D-009, goedgekeurd (logboek 9). Korting is een fractie 0-0,25. Samenhang is geen oorzakelijk bewijs.",
    ),
    "K-PRIO": dict(
        question_id="DV4", label="Verbeterprioriteit", unit="klasse", source_columns=("K-REV", "K-MARGIN", "K-LATEPCT"), grain="markt x categorie",
        formula="min. 30 orders; Prioriteit = omzet >= mediaan van kwalificerende segmenten EN marge < referentiemarge EN vertraging > referentie-%",
        numerator="-", denominator="-", aggregation="beslisregels, geen score",
        missing_rule="< 30 orders of onbekende marge = 'Onvoldoende data' (nooit 'laag risico')", pipeline_stages=("DV1", "DV2"), decision_id="D-010",
        test_ids=(_T + "test_priority_min_orders_and_tiebreak",),
        caveat="Hypothese/onderzoeksprioriteit, geen bewezen oorzaak of eurobesparing. Referenties = gewogen totalen van alle markten en categorieën in de gekozen periode; een filter op markt of categorie zoomt alleen in.",
    ),
}


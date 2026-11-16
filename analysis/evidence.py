"""DataCo evidence metadata (no raw records, Streamlit import, or AI assertions).

This is a validated *interface* for evidence, not populated DataCo evidence.
A VALIDATED record must be backed by reproducible real-data computations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["PENDING", "VALIDATED", "BLOCKED"]


@dataclass(frozen=True)
class EvidenceRecord:
    question_id: str
    metric_id: str
    source_columns: tuple[str, ...]
    formula: str
    grain: str
    pipeline_steps: tuple[str, ...] = ()
    applied_filters: tuple[tuple[str, str], ...] = ()
    input_rows: int | None = None
    analysis_rows: int | None = None
    excluded_rows: int | None = None
    numerator: float | None = None
    denominator: float | None = None
    result: float | None = None
    decision_id: str | None = None
    code_function: str | None = None
    test_ids: tuple[str, ...] = ()
    raw_sha256: str | None = None
    processed_sha256: str | None = None
    processed_file: str | None = None
    status: Status = "PENDING"

    def __post_init__(self):
        if self.question_id not in {"DV1", "DV2", "DV3", "DV4"}:
            raise ValueError("question_id must be DV1, DV2, DV3 or DV4")
        if self.status not in {"PENDING", "VALIDATED", "BLOCKED"}:
            raise ValueError("Invalid evidence status")
        for field in ("input_rows", "analysis_rows", "excluded_rows"):
            val = getattr(self, field)
            if val is not None and val < 0:
                raise ValueError(f"{field} cannot be negative")
        if self.input_rows is not None and self.analysis_rows is not None:
            if self.analysis_rows > self.input_rows:
                raise ValueError("analysis_rows cannot exceed input_rows for row-filtering stages")
        if self.excluded_rows is not None and self.input_rows is not None and self.analysis_rows is not None:
            if self.input_rows != self.analysis_rows + self.excluded_rows:
                raise ValueError("Row accounting mismatch")
        if self.status == "VALIDATED":
            essential = (
                self.source_columns and self.formula and self.grain and self.pipeline_steps
                and self.decision_id and self.code_function and self.test_ids
                and self.raw_sha256 and self.processed_sha256 and self.processed_file
                and self.input_rows is not None and self.analysis_rows is not None
                and self.result is not None
            )
            if not essential:
                raise ValueError("Cannot mark KPI evidence VALIDATED without provenance, decision and tests")

    def as_display_metadata(self) -> dict:
        """Public *metadata only*; contains no raw rows or customer values."""
        return {
            "question_id": self.question_id,
            "metric_id": self.metric_id,
            "source_columns": list(self.source_columns),
            "formula": self.formula,
            "grain": self.grain,
            "pipeline_steps": list(self.pipeline_steps),
            "applied_filters": dict(self.applied_filters),
            "input_rows": self.input_rows,
            "analysis_rows": self.analysis_rows,
            "excluded_rows": self.excluded_rows,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "result": self.result,
            "decision_id": self.decision_id,
            "code_function": self.code_function,
            "test_ids": list(self.test_ids),
            "status": self.status,
            # Keep full file paths & hashes in methodology/secure internal evidence only.
        }


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


def build_record(
    metric_id: str, *, filters: tuple[tuple[str, str], ...], input_rows: int, analysis_rows: int,
    numerator: float | None, denominator: float | None, result: float | None,
    raw_sha256: str | None, processed_sha256: str | None, processed_file: str | None,
) -> EvidenceRecord:
    """EvidenceRecord for a metric under the current filters; VALIDATED only with full provenance."""
    d = KPI_REGISTER[metric_id]
    complete = bool(raw_sha256 and processed_sha256 and processed_file and result is not None)
    return EvidenceRecord(
        question_id=d["question_id"], metric_id=metric_id, source_columns=d["source_columns"], formula=d["formula"], grain=d["grain"],
        pipeline_steps=d["pipeline_stages"], applied_filters=filters, input_rows=input_rows, analysis_rows=analysis_rows,
        excluded_rows=input_rows - analysis_rows, numerator=numerator, denominator=denominator, result=result,
        decision_id=d["decision_id"], code_function="analysis.kpis / pipeline.run_pipeline", test_ids=d["test_ids"],
        raw_sha256=raw_sha256, processed_sha256=processed_sha256, processed_file=processed_file,
        status="VALIDATED" if complete else "PENDING",
    )

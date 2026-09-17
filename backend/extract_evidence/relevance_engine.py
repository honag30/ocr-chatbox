from typing import Tuple, List
from .schemas import (
    CashflowRelevance,
    FundingRelevance,
    EconomicArtifact,
    EvidenceFact
)

class RelevanceEngine:
    """
    Calculates Cashflow Impact and Funding Relevance.
    Enforces strict financial truth rules:
    - Payer name alone != Organization account confirmed.
    - Contract cannot be ACTUAL cashflow.
    - Funding Engine ONLY outputs Evidence Roles/Reason Codes, NEVER funding approval/decision.
    """

    @staticmethod
    def calculate(
        doc_type: str,
        artifacts: List[EconomicArtifact],
        facts: List[EvidenceFact],
        organization_confirmed: bool = False
    ) -> Tuple[CashflowRelevance, FundingRelevance]:
        amt_fact = next((f for f in facts if f.fact_type in ["TOTAL_AMOUNT", "GROSS_AMOUNT"]), None)
        if not amt_fact:
            amt_fact = next((f for f in facts if f.fact_type == "AMOUNT"), None)

        due_fact = next((f for f in facts if f.fact_type in ["DUE_DATE", "MATURITY_DATE"]), None)

        amount_val = float(amt_fact.value) if (amt_fact and isinstance(amt_fact.value, (int, float))) else None
        expected_date_val = str(due_fact.value) if due_fact else None

        cf_rel = CashflowRelevance()
        fund_rel = FundingRelevance()

        # 1. INVOICE (VAT_INVOICE, SALES_INVOICE, PURCHASE_INVOICE)
        if doc_type in ["VAT_INVOICE", "SALES_INVOICE"]:
            cf_rel = CashflowRelevance(
                relevance="HIGH",
                direction="INFLOW",
                cashflow_status="FORECAST_INPUT",
                amount=amount_val,
                currency="VND",
                expected_date=expected_date_val,
                basis="RECEIVABLE",
                confidence=0.92,
                account_ownership_confirmed=organization_confirmed
            )
            fund_rel = FundingRelevance(
                relevance="HIGH",
                evidence_roles=["RECEIVABLE_PROOF", "REVENUE_PROOF", "CASHFLOW_FORECAST_INPUT"],
                reason_codes=["DOCUMENTED_RECEIVABLE", "CONFIRMED_INVOICE"]
            )

        elif doc_type == "PURCHASE_INVOICE":
            cf_rel = CashflowRelevance(
                relevance="HIGH",
                direction="OUTFLOW",
                cashflow_status="FORECAST_INPUT",
                amount=amount_val,
                currency="VND",
                expected_date=expected_date_val,
                basis="PAYABLE",
                confidence=0.92,
                account_ownership_confirmed=organization_confirmed
            )
            fund_rel = FundingRelevance(
                relevance="MEDIUM",
                evidence_roles=["PAYABLE_PROOF", "CASHFLOW_FORECAST_INPUT"],
                reason_codes=["DOCUMENTED_PAYABLE"]
            )

        # 2. CONTRACT (PURCHASE_CONTRACT, SALES_CONTRACT, SERVICE_CONTRACT, etc.)
        elif "CONTRACT" in doc_type or doc_type == "PURCHASE_ORDER":
            is_sales = doc_type == "SALES_CONTRACT"
            cf_rel = CashflowRelevance(
                relevance="HIGH",
                direction="INFLOW" if is_sales else "OUTFLOW",
                cashflow_status="COMMITMENT",
                amount=amount_val,
                currency="VND",
                expected_date=expected_date_val,
                basis="CONTRACTUAL_COMMITMENT",
                confidence=0.90,
                account_ownership_confirmed=False
            )
            fund_rel = FundingRelevance(
                relevance="HIGH",
                evidence_roles=["CONTRACT_PROOF", "CASHFLOW_FORECAST_INPUT"],
                reason_codes=["CONTRACTUAL_OBLIGATION", "FUTURE_REVENUE_COMMITMENT"]
            )

        # 3. BANK TRANSFER / STATEMENT (ACTUAL CASH - ENFORCE ACCOUNT OWNERSHIP CHECK)
        elif doc_type in ["BANK_TRANSFER_PROOF", "BANK_STATEMENT"]:
            if organization_confirmed:
                direction_val = "OUTFLOW"  # or INFLOW based on payee/payer confirmation
                status_val = "ACTUAL"
                basis_val = "SETTLED_CASH_CONFIRMED"
            else:
                # CRITICAL RULE 4: Unconfirmed account ownership -> CANDIDATE_OUTFLOW / UNKNOWN
                direction_val = "CANDIDATE_OUTFLOW"
                status_val = "ACTUAL"
                basis_val = "SETTLED_CASH_UNCONFIRMED_ACCOUNT"

            cf_rel = CashflowRelevance(
                relevance="HIGH",
                direction=direction_val,
                cashflow_status=status_val,
                amount=amount_val,
                currency="VND",
                basis=basis_val,
                confidence=0.95 if organization_confirmed else 0.80,
                account_ownership_confirmed=organization_confirmed
            )

            # Multiple evidence roles supported! (Section 9)
            fund_rel = FundingRelevance(
                relevance="HIGH",
                evidence_roles=[
                    "SETTLEMENT_PROOF",
                    "CASHFLOW_ACTUAL",
                    "TRANSACTION_PROOF",
                    "PAYMENT_PROOF"
                ],
                reason_codes=["VERIFIED_BANK_SETTLEMENT" if organization_confirmed else "UNCONFIRMED_ACCOUNT_OWNERSHIP"]
            )

        # 4. DELIVERY / WAREHOUSE (ECONOMIC EVENT / EXECUTION)
        elif doc_type in ["DELIVERY_ACCEPTANCE_RECORD", "WAREHOUSE_ISSUE_NOTE"]:
            cf_rel = CashflowRelevance(
                relevance="MEDIUM",
                direction="INFLOW",
                cashflow_status="FORECAST_INPUT",
                amount=amount_val,
                currency="VND",
                basis="EXECUTION_EVIDENCE",
                confidence=0.88,
                account_ownership_confirmed=False
            )
            fund_rel = FundingRelevance(
                relevance="HIGH",
                evidence_roles=["ECONOMIC_EVENT_PROOF", "TRANSACTION_PROOF"],
                reason_codes=["DELIVERY_ACCEPTANCE_COMPLETED"]
            )

        # 5. ASSET DOCUMENT
        elif doc_type == "ASSET_DOCUMENT":
            cf_rel = CashflowRelevance(
                relevance="NONE",
                direction="NONE",
                cashflow_status="NONE",
                basis="ASSET_OWNERSHIP",
                confidence=0.95
            )
            fund_rel = FundingRelevance(
                relevance="HIGH",
                evidence_roles=["ASSET_PROOF", "COLLATERAL_PROOF"],
                reason_codes=["VERIFIED_ASSET_OWNERSHIP"]
            )

        # 6. LOAN AGREEMENT / FUNDING
        elif doc_type in ["LOAN_AGREEMENT", "FUNDING_DOCUMENT"]:
            cf_rel = CashflowRelevance(
                relevance="HIGH",
                direction="INFLOW",
                cashflow_status="FORECAST_INPUT",
                amount=amount_val,
                currency="VND",
                expected_date=expected_date_val,
                basis="DEBT_FACILITY",
                confidence=0.93
            )
            fund_rel = FundingRelevance(
                relevance="HIGH",
                evidence_roles=["DEBT_PROOF", "FUNDING_FACILITY_PROOF"],
                reason_codes=["EXISTING_CREDIT_FACILITY"]
            )

        # 7. UNKNOWN FALLBACK
        else:
            cf_rel = CashflowRelevance(
                relevance="UNKNOWN",
                direction="UNKNOWN",
                cashflow_status="UNKNOWN",
                confidence=0.30
            )
            fund_rel = FundingRelevance(
                relevance="NONE",
                evidence_roles=[],
                reason_codes=["UNCLASSIFIED_DOCUMENT"]
            )

        return cf_rel, fund_rel

import re
from typing import List, Optional, Dict, Any
from .schemas import (
    EconomicArtifact,
    EconomicMeaning,
    CounterpartyInfo,
    EvidenceFact
)
from .fact_extractor import AtomicFactExtractor

class EconomicInterpreter:
    """
    Translates Evidence Facts & Document Type into structured, document-specific Economic Artifacts.
    Status is strictly INTERPRETED / CANDIDATE.
    """

    @staticmethod
    def interpret(doc_type: str, facts: List[EvidenceFact], doc_result: Optional[dict] = None) -> List[EconomicArtifact]:
        artifacts: List[EconomicArtifact] = []

        # 1. Helper lookups for facts
        def get_fact_val(fact_types: List[str]) -> Optional[Any]:
            for ft in fact_types:
                f = next((x for x in facts if x.fact_type == ft), None)
                if f and f.value is not None:
                    return f.value
            return None

        # Key facts
        amount_val = get_fact_val(["TOTAL_AMOUNT", "GROSS_AMOUNT", "AMOUNT", "ASSET_VALUE"])
        if amount_val is not None:
            try:
                amount_val = float(amount_val)
            except (ValueError, TypeError):
                amount_val = None

        doc_date_val = str(get_fact_val(["DOCUMENT_DATE", "INVOICE_DATE", "TRANSACTION_DATE", "CONTRACT_DATE"]) or "") or None
        due_date_val = str(get_fact_val(["DUE_DATE", "MATURITY_DATE", "EXPIRY_DATE"]) or "") or None

        def get_best_party(fact_types: List[str]) -> Optional[str]:
            for f in facts:
                if f.fact_type in fact_types and f.confidence >= 0.98 and f.value:
                    val_s = str(f.value).strip()
                    if len(val_s) >= 4 and val_s.lower() not in ["hàng", "đơn vị", "bên", "người", "khách hàng"]:
                        return val_s
            for f in facts:
                if f.fact_type in fact_types and f.value:
                    val_s = str(f.value).strip()
                    if len(val_s) >= 4 and val_s.lower() not in ["hàng", "đơn vị", "bên", "người", "khách hàng"]:
                        return val_s
            return None

        payee_name = get_best_party(["PAYEE", "SELLER"])
        payer_name = get_best_party(["PAYER", "BUYER"])
        general_party = get_best_party(["PARTY"])

        tax_codes = [str(f.value) for f in facts if f.fact_type == "TAX_CODE"]
        tax_code_seller = tax_codes[0] if len(tax_codes) > 0 else None
        tax_code_buyer = tax_codes[1] if len(tax_codes) > 1 else None

        # Build Counterparty objects
        is_bank = ("BANK" in doc_type)
        is_sales = ("SALES" in doc_type or doc_type == "VAT_INVOICE")
        is_delivery = (doc_type in ["WAREHOUSE_ISSUE_NOTE", "DELIVERY_ACCEPTANCE_RECORD"])

        payee_clean = payee_name or (general_party if general_party != payer_name else None)
        payer_clean = payer_name or (general_party if general_party != payee_name else None)

        payee_cp = CounterpartyInfo(
            name=payee_clean or ("UNSPECIFIED_BENEFICIARY" if is_bank else "UNSPECIFIED_SELLER"),
            role="BENEFICIARY" if is_bank else ("SUPPLIER" if "PURCHASE" in doc_type else "SELLER"),
            tax_code=tax_code_seller
        ) if (payee_clean or is_bank) else None

        payer_cp = CounterpartyInfo(
            name=payer_clean or ("UNSPECIFIED_REMITTER" if is_bank else "UNSPECIFIED_BUYER"),
            role="REMITTER" if is_bank else ("CUSTOMER" if is_sales else ("RECIPIENT" if is_delivery else "BUYER")),
            tax_code=tax_code_buyer
        ) if (payer_clean or is_bank) else None

        primary_cp = payer_cp if is_sales else (payee_cp or CounterpartyInfo(name=general_party or "UNSPECIFIED_COUNTERPARTY"))

        evidence_ids = [f.evidence_fact_id for f in facts]

        # ---------------------------------------------------------
        # TAILORED DATA EXTRACTION PER DOCUMENT TYPE
        # ---------------------------------------------------------

        # CATEGORY 1: INVOICES (VAT_INVOICE, SALES_INVOICE, PURCHASE_INVOICE)
        if doc_type in ["VAT_INVOICE", "PURCHASE_INVOICE", "SALES_INVOICE"]:
            ob_type = "RECEIVABLE" if doc_type in ["SALES_INVOICE", "VAT_INVOICE"] else "PAYABLE"
            
            # Extract structured line items
            line_items = AtomicFactExtractor.extract_invoice_table_items(doc_result) if doc_result else []

            # Tax category summaries
            full_text = doc_result.get("full_text", "") if doc_result else ""
            tax_exempt_subtotal = None
            taxable_subtotal_10 = None
            vat_amount_10 = None

            if full_text:
                m_kct = re.search(r'Cộng tiền chuyển nhượng[^\n]*\:\s*([\d\.\,]+)', full_text, re.IGNORECASE)
                if m_kct:
                    tax_exempt_subtotal = AtomicFactExtractor.parse_float_safe(m_kct.group(1))

                m_tax10 = re.search(r'Cộng tiền hàng hóa[^\n]*10\%\:\s*([\d\.\,]+)', full_text, re.IGNORECASE)
                if m_tax10:
                    taxable_subtotal_10 = AtomicFactExtractor.parse_float_safe(m_tax10.group(1))

                m_vat10 = re.search(r'Tiền thuế Giá trị gia tăng[^\n]*\:\s*([\d\.\,]+)', full_text, re.IGNORECASE)
                if m_vat10:
                    vat_amount_10 = AtomicFactExtractor.parse_float_safe(m_vat10.group(1))

            subtotal_amount = get_fact_val(["NET_AMOUNT"])
            vat_amount = get_fact_val(["VAT_AMOUNT"]) or vat_amount_10

            invoice_extra: Dict[str, Any] = {
                "invoice_number": get_fact_val(["INVOICE_NUMBER", "DOCUMENT_NUMBER"]),
                "contract_reference": get_fact_val(["CONTRACT_NUMBER"]),
                "subtotal_amount": subtotal_amount,
                "vat_amount": vat_amount,
                "tax_exempt_subtotal": tax_exempt_subtotal,
                "taxable_subtotal_10": taxable_subtotal_10,
                "vat_amount_10": vat_amount_10,
                "total_payment_amount": amount_val,
                "line_items": line_items,
                "payment_method": get_fact_val(["TRANSACTION_REMARK", "PAYMENT_METHOD"]),
                "bank_name": get_fact_val(["BANK_NAME"]),
                "bank_account": get_fact_val(["BANK_ACCOUNT"]),
                "tax_code_seller": tax_code_seller,
                "tax_code_buyer": tax_code_buyer
            }

            artifacts.append(
                EconomicArtifact(
                    artifact_type="INVOICE",
                    economic_meaning=EconomicMeaning(
                        economic_object="OBLIGATION",
                        obligation_type=ob_type,
                        amount=amount_val,
                        currency="VND",
                        issue_date=doc_date_val,
                        due_date=due_date_val,
                        payer=payer_cp,
                        payee=payee_cp,
                        counterparty=primary_cp,
                        extra=invoice_extra
                    ),
                    evidence_refs=evidence_ids,
                    status="CANDIDATE"
                )
            )

        # CATEGORY 2: CONTRACTS & ORDERS (PURCHASE_CONTRACT, SALES_CONTRACT, SERVICE_CONTRACT, etc.)
        elif "CONTRACT" in doc_type or doc_type == "PURCHASE_ORDER":
            is_sales = doc_type == "SALES_CONTRACT"
            ob_type = "COMMITMENT"

            contract_items = AtomicFactExtractor.extract_structured_table_items(doc_result, doc_type=doc_type) if doc_result else []
            contract_extra: Dict[str, Any] = {
                "contract_number": get_fact_val(["CONTRACT_NUMBER", "DOCUMENT_NUMBER"]),
                "contract_date": doc_date_val,
                "total_contract_value": amount_val,
                "party_a_buyer": payer_name,
                "party_b_seller": payee_name,
                "payment_terms": get_fact_val(["PAYMENT_TERM"]),
                "due_date": due_date_val,
                "line_items": contract_items
            }

            artifacts.append(
                EconomicArtifact(
                    artifact_type="PURCHASE_ORDER" if doc_type == "PURCHASE_ORDER" else "CONTRACT",
                    economic_meaning=EconomicMeaning(
                        economic_object="OBLIGATION",
                        obligation_type=ob_type,
                        amount=amount_val,
                        currency="VND",
                        issue_date=doc_date_val,
                        due_date=due_date_val,
                        payer=payer_cp,
                        payee=payee_cp,
                        counterparty=payer_cp if is_sales else payee_cp,
                        extra=contract_extra
                    ),
                    evidence_refs=evidence_ids,
                    status="CANDIDATE"
                )
            )

        # CATEGORY 3: BANK PROOF & STATEMENTS (BANK_TRANSFER_PROOF, BANK_STATEMENT)
        elif doc_type in ["BANK_TRANSFER_PROOF", "BANK_STATEMENT"]:
            statement_items = AtomicFactExtractor.extract_structured_table_items(doc_result, doc_type=doc_type) if doc_result else []
            bank_extra: Dict[str, Any] = {
                "bank_reference": get_fact_val(["BANK_REFERENCE"]),
                "transaction_date": doc_date_val,
                "transfer_amount": amount_val,
                "sender_name": payer_name,
                "recipient_name": payee_name,
                "bank_name": get_fact_val(["BANK_NAME"]),
                "bank_account": get_fact_val(["BANK_ACCOUNT"]),
                "transfer_remark": get_fact_val(["TRANSACTION_REMARK"]),
                "statement_transactions": statement_items
            }

            artifacts.append(
                EconomicArtifact(
                    artifact_type="SETTLEMENT",
                    economic_meaning=EconomicMeaning(
                        economic_object="SETTLEMENT",
                        obligation_type="SETTLED_CASH",
                        amount=amount_val,
                        currency="VND",
                        issue_date=doc_date_val,
                        payer=payer_cp,
                        payee=payee_cp,
                        counterparty=payee_cp or payer_cp,
                        extra=bank_extra
                    ),
                    evidence_refs=evidence_ids,
                    status="CANDIDATE"
                )
            )

        # CATEGORY 4: WAREHOUSE & DELIVERY (WAREHOUSE_ISSUE_NOTE, DELIVERY_ACCEPTANCE_RECORD)
        elif doc_type in ["WAREHOUSE_ISSUE_NOTE", "DELIVERY_ACCEPTANCE_RECORD"]:
            delivery_items = AtomicFactExtractor.extract_structured_table_items(doc_result, doc_type=doc_type) if doc_result else []
            delivery_extra: Dict[str, Any] = {
                "delivery_document_number": get_fact_val(["DOCUMENT_NUMBER"]),
                "issue_date": doc_date_val,
                "deliverer": payee_name,
                "recipient": payer_name,
                "delivered_amount": amount_val,
                "acceptance_status": get_fact_val(["ACCEPTANCE_STATUS", "STATUS"]) or "COMPLETED",
                "items": delivery_items
            }

            artifacts.append(
                EconomicArtifact(
                    artifact_type="ECONOMIC_EVENT",
                    economic_meaning=EconomicMeaning(
                        economic_object="ECONOMIC_EVENT",
                        obligation_type="EXECUTION_PROOF",
                        amount=amount_val,
                        currency="VND",
                        issue_date=doc_date_val,
                        payer=payer_cp,
                        payee=payee_cp,
                        counterparty=primary_cp,
                        extra=delivery_extra
                    ),
                    evidence_refs=evidence_ids,
                    status="CANDIDATE"
                )
            )

        # CATEGORY 5: ASSET DOCUMENTS (ASSET_DOCUMENT)
        elif doc_type == "ASSET_DOCUMENT":
            asset_extra: Dict[str, Any] = {
                "certificate_number": get_fact_val(["DOCUMENT_NUMBER"]),
                "issue_date": doc_date_val,
                "asset_owner": general_party or payee_name or payer_name,
                "asset_type": get_fact_val(["ASSET_TYPE", "ASSET"]) or "REAL_ESTATE_OR_EQUIPMENT",
                "asset_location": get_fact_val(["ADDRESS"]),
                "expiry_date": due_date_val
            }

            artifacts.append(
                EconomicArtifact(
                    artifact_type="ASSET",
                    economic_meaning=EconomicMeaning(
                        economic_object="ASSET",
                        obligation_type="COLLATERAL_OR_PROPERTY",
                        amount=amount_val,
                        currency="VND",
                        issue_date=doc_date_val,
                        due_date=due_date_val,
                        counterparty=CounterpartyInfo(name=asset_extra["asset_owner"], role="OWNER"),
                        extra=asset_extra
                    ),
                    evidence_refs=evidence_ids,
                    status="CANDIDATE"
                )
            )

        # CATEGORY 6: LOAN & CREDIT FACILITIES (LOAN_AGREEMENT, FUNDING_DOCUMENT)
        elif doc_type in ["LOAN_AGREEMENT", "FUNDING_DOCUMENT"]:
            loan_extra: Dict[str, Any] = {
                "facility_agreement_number": get_fact_val(["CONTRACT_NUMBER", "DOCUMENT_NUMBER"]),
                "agreement_date": doc_date_val,
                "lender": payee_name,
                "borrower": payer_name,
                "credit_limit": amount_val,
                "interest_rate": get_fact_val(["INTEREST_RATE"]),
                "repayment_term": get_fact_val(["REPAYMENT_TERM", "PAYMENT_TERM"]),
                "maturity_date": due_date_val
            }

            artifacts.append(
                EconomicArtifact(
                    artifact_type="FUNDING_FACILITY",
                    economic_meaning=EconomicMeaning(
                        economic_object="FUNDING_FACILITY",
                        obligation_type="DEBT_OR_CREDIT_LINE",
                        amount=amount_val,
                        currency="VND",
                        issue_date=doc_date_val,
                        due_date=due_date_val,
                        payer=payer_cp,
                        payee=payee_cp,
                        counterparty=payee_cp or payer_cp,
                        extra=loan_extra
                    ),
                    evidence_refs=evidence_ids,
                    status="CANDIDATE"
                )
            )

        # CATEGORY 7: UNKNOWN FALLBACK
        else:
            artifacts.append(
                EconomicArtifact(
                    artifact_type="UNKNOWN",
                    economic_meaning=EconomicMeaning(
                        economic_object="UNKNOWN",
                        obligation_type="UNCLASSIFIED",
                        amount=amount_val,
                        currency="VND",
                        issue_date=doc_date_val,
                        counterparty=primary_cp,
                        extra={"raw_doc_type": doc_type}
                    ),
                    evidence_refs=evidence_ids,
                    status="CANDIDATE"
                )
            )

        return artifacts

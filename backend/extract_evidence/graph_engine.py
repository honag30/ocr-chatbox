from typing import List
from .schemas import DocumentRelationship, EvidenceFact

class DocumentGraphEngine:
    """
    Detects cross-document relationships to build the Document Graph.
    Chain: CONTRACT -> PURCHASE_ORDER -> DELIVERY_ACCEPTANCE -> INVOICE -> BANK_TRANSFER
    Relationships: SUPPORTS, SETTLED_BY, FULFILLS, REFERENCES
    """

    @staticmethod
    def detect_relationships(doc_id: str, doc_type: str, facts: List[EvidenceFact]) -> List[DocumentRelationship]:
        relationships: List[DocumentRelationship] = []

        # Find contract reference in invoice or bank transfer
        contract_fact = next((f for f in facts if f.fact_type == "CONTRACT_NUMBER"), None)
        invoice_fact = next((f for f in facts if f.fact_type == "INVOICE_NUMBER"), None)

        # 1. Invoice or Contract settled by Bank Transfer / Statement
        if doc_type in ["BANK_TRANSFER_PROOF", "BANK_STATEMENT"]:
            if invoice_fact and invoice_fact.value:
                target_doc_id = f"DOC-INV-{invoice_fact.value}"
                relationships.append(
                    DocumentRelationship(
                        from_document_id=doc_id,
                        relationship="SETTLED_BY",
                        to_document_id=target_doc_id,
                        confidence=0.95
                    )
                )
            elif contract_fact and contract_fact.value:
                target_doc_id = f"DOC-CON-{contract_fact.value}"
                relationships.append(
                    DocumentRelationship(
                        from_document_id=doc_id,
                        relationship="SETTLED_BY",
                        to_document_id=target_doc_id,
                        confidence=0.95
                    )
                )

        # 2. Invoice supported by Contract
        if doc_type in ["VAT_INVOICE", "SALES_INVOICE", "PURCHASE_INVOICE"]:
            if contract_fact and contract_fact.value:
                target_doc_id = f"DOC-CON-{contract_fact.value}"
                relationships.append(
                    DocumentRelationship(
                        from_document_id=target_doc_id,
                        relationship="SUPPORTS",
                        to_document_id=doc_id,
                        confidence=0.96
                    )
                )

        # 3. Delivery / Acceptance fulfills Purchase Order or Contract
        if doc_type in ["DELIVERY_ACCEPTANCE_RECORD", "WAREHOUSE_ISSUE_NOTE"]:
            if contract_fact and contract_fact.value:
                target_doc_id = f"DOC-CON-{contract_fact.value}"
                relationships.append(
                    DocumentRelationship(
                        from_document_id=doc_id,
                        relationship="FULFILLS",
                        to_document_id=target_doc_id,
                        confidence=0.94
                    )
                )

        return relationships

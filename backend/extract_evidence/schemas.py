import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# CONSTANTS & ENUMS
# ---------------------------------------------------------

DOCUMENT_TYPES = [
    "VAT_INVOICE",
    "PURCHASE_INVOICE",
    "SALES_INVOICE",
    "PURCHASE_CONTRACT",
    "SALES_CONTRACT",
    "SERVICE_CONTRACT",
    "ASSET_PURCHASE_CONTRACT",
    "PURCHASE_ORDER",
    "WAREHOUSE_ISSUE_NOTE",
    "DELIVERY_ACCEPTANCE_RECORD",
    "BANK_TRANSFER_PROOF",
    "BANK_STATEMENT",
    "LOAN_AGREEMENT",
    "FUNDING_DOCUMENT",
    "ASSET_DOCUMENT",
    "UNKNOWN"
]

FACT_TYPES = [
    "PARTY", "PAYER", "PAYEE", "PARTY_ROLE",
    "DOCUMENT_NUMBER", "DOCUMENT_DATE",
    "CONTRACT_NUMBER", "CONTRACT_DATE",
    "INVOICE_NUMBER", "INVOICE_DATE",
    "AMOUNT", "CURRENCY", "VAT_AMOUNT", "NET_AMOUNT", "GROSS_AMOUNT",
    "ITEM", "ITEM_CODE", "QUANTITY", "UNIT", "UNIT_PRICE",
    "PAYMENT_TERM", "PAYMENT_METHOD", "DUE_DATE",
    "BANK_NAME", "BANK_ACCOUNT", "BANK_REFERENCE", "TRANSACTION_DATE",
    "ADDRESS", "TAX_CODE",
    "INTEREST_RATE", "MATURITY_DATE", "REPAYMENT_TERM",
    "ASSET", "ASSET_TYPE", "ASSET_VALUE",
    "STATUS", "SIGNATURE", "ACCEPTANCE_STATUS"
]

ECONOMIC_ARTIFACT_TYPES = [
    "CONTRACT", "INVOICE", "PURCHASE_ORDER", "OBLIGATION",
    "ECONOMIC_EVENT", "SETTLEMENT", "ASSET", "FUNDING_FACILITY"
]

OBJECT_BINDING_TYPES = [
    "PARTY", "RELATIONSHIP", "CONTRACT", "TRANSACTION",
    "OBLIGATION", "ECONOMIC_EVENT", "SETTLEMENT", "ASSET", "FUNDING_FACILITY"
]

CASHFLOW_DIRECTIONS = ["INFLOW", "OUTFLOW", "CANDIDATE_INFLOW", "CANDIDATE_OUTFLOW", "NONE", "UNKNOWN"]
CASHFLOW_STATUSES = ["ACTUAL", "FORECAST_INPUT", "COMMITMENT", "NONE", "UNKNOWN"]

# 3 DISTINCT STATUS GROUPS (Section 12)
LIFECYCLE_STATUSES = ["EXTRACTED", "INTERPRETED", "CANDIDATE", "VERIFIED", "PUBLISHED"]
VERIFICATION_STATUSES = ["UNVERIFIED", "REVIEW_REQUIRED", "VERIFIED", "REJECTED"]
PUBLISH_STATUSES = ["PENDING", "ELIGIBLE", "PUBLISHED", "BLOCKED"]


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------

class DocumentMetadata(BaseModel):
    document_id: str
    artifact_id: str
    document_type: str = "UNKNOWN"
    document_number: Optional[str] = None
    document_date: Optional[str] = None
    organization_id: Optional[str] = None
    version: int = 1


class FactSource(BaseModel):
    document_id: str
    artifact_id: str
    page: int = 1
    text: str = ""
    bbox: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])


class EvidenceFact(BaseModel):
    evidence_fact_id: str
    fact_type: str
    value: Any
    currency: Optional[str] = "VND"
    source: FactSource
    confidence: float = 1.0
    verification_status: str = "UNVERIFIED"


class CounterpartyInfo(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None  # PAYER, PAYEE, CUSTOMER, SUPPLIER
    tax_code: Optional[str] = None
    account_number: Optional[str] = None
    account_ownership_confirmed: bool = False  # CRITICAL RULE 4: False unless explicit organization ownership is proven!


class EconomicMeaning(BaseModel):
    economic_object: str
    obligation_type: Optional[str] = None  # RECEIVABLE, PAYABLE, COMMITMENT, EXECUTION, SETTLEMENT
    amount: Optional[float] = None
    currency: str = "VND"
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    payer: Optional[CounterpartyInfo] = None
    payee: Optional[CounterpartyInfo] = None
    counterparty: Optional[CounterpartyInfo] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class EconomicArtifact(BaseModel):
    artifact_type: str
    economic_meaning: EconomicMeaning
    evidence_refs: List[str] = Field(default_factory=list)
    status: str = "CANDIDATE"  # INTERPRETED / CANDIDATE


class ObjectBinding(BaseModel):
    object_type: str
    object_id: Optional[str] = None  # MUST BE null if not matched with authority
    candidate_name: Optional[str] = None
    candidate_reference: Optional[str] = None  # e.g., "08/2026"
    match_status: str = "CANDIDATE"  # CANDIDATE, MATCHED
    confidence: float = 0.90


class CashflowRelevance(BaseModel):
    relevance: str = "UNKNOWN"  # HIGH, MEDIUM, LOW, NONE
    direction: str = "UNKNOWN"  # INFLOW, OUTFLOW, CANDIDATE_INFLOW, CANDIDATE_OUTFLOW, NONE, UNKNOWN
    cashflow_status: str = "UNKNOWN"  # ACTUAL, FORECAST_INPUT, COMMITMENT, NONE, UNKNOWN
    amount: Optional[float] = None
    currency: str = "VND"
    expected_date: Optional[str] = None
    basis: Optional[str] = None  # RECEIVABLE, PAYABLE, COMMITMENT, SETTLEMENT, EXECUTION, UNCONFIRMED_ACCOUNT
    confidence: float = 0.90
    account_ownership_confirmed: bool = False  # CRITICAL RULE 4


class FundingRelevance(BaseModel):
    relevance: str = "NONE"  # HIGH, MEDIUM, LOW, NONE
    evidence_roles: List[str] = Field(default_factory=list)  # SETTLEMENT_PROOF, CASHFLOW_ACTUAL, etc.
    reason_codes: List[str] = Field(default_factory=list)
    # NEVER OUTPUT approved_funding or funding_amount!


class FieldConfidences(BaseModel):
    overall: float = 0.0
    fields: Dict[str, float] = Field(default_factory=dict)  # amount, date, payer, payee, reference, etc.


class TrustGovernance(BaseModel):
    confidence: FieldConfidences = Field(default_factory=FieldConfidences)
    lifecycle_status: str = "CANDIDATE"  # EXTRACTED, INTERPRETED, CANDIDATE, VERIFIED, PUBLISHED
    verification_status: str = "UNVERIFIED"  # UNVERIFIED, REVIEW_REQUIRED, VERIFIED, REJECTED
    review_required: bool = False
    publish_status: str = "PENDING"  # PENDING, ELIGIBLE, PUBLISHED, BLOCKED
    review_notes: Optional[str] = None


class ExtractionModelInfo(BaseModel):
    provider: str = "Core OCR & Evidence Engine"
    model_name: str = "SMEMONEY Evidence Engine"
    version: str = "1.0.0"


class ProvenanceInfo(BaseModel):
    document_id: str
    artifact_id: str
    source: FactSource
    extraction_method: str = "OCR_AI"
    model: ExtractionModelInfo = Field(default_factory=ExtractionModelInfo)
    extracted_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))


class LineageInfo(BaseModel):
    lineage_id: str
    parent_document_id: str


class ConflictValue(BaseModel):
    value: Any
    source: str


class ConflictItem(BaseModel):
    field: str
    values: List[ConflictValue]
    status: str = "REVIEW_REQUIRED"
    description: Optional[str] = None


class DocumentRelationship(BaseModel):
    from_document_id: str = Field(..., alias="from")
    relationship: str  # SUPPORTS, SETTLED_BY, FULFILLS, REFERENCES
    to_document_id: str = Field(..., alias="to")
    confidence: float = 0.95

    class Config:
        populate_by_name = True


class EvidencePackage(BaseModel):
    evidence_package_id: str
    document: DocumentMetadata
    evidence_facts: List[EvidenceFact] = Field(default_factory=list)
    economic_artifacts: List[EconomicArtifact] = Field(default_factory=list)
    object_bindings: List[ObjectBinding] = Field(default_factory=list)
    document_relationships: List[DocumentRelationship] = Field(default_factory=list)
    cashflow_relevance: CashflowRelevance = Field(default_factory=CashflowRelevance)
    funding_relevance: FundingRelevance = Field(default_factory=FundingRelevance)
    trust: TrustGovernance = Field(default_factory=TrustGovernance)
    provenance: ProvenanceInfo
    lineage: LineageInfo
    conflicts: List[ConflictItem] = Field(default_factory=list)

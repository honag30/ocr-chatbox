"""
SMEMONEY Evidence Extraction Engine Module
"""

from .pipeline import EvidenceExtractionEngine
from .schemas import (
    EvidencePackage,
    DocumentMetadata,
    EvidenceFact,
    EconomicArtifact,
    ObjectBinding,
    CashflowRelevance,
    FundingRelevance,
    TrustGovernance,
    ProvenanceInfo,
    LineageInfo,
    ConflictItem,
    DocumentRelationship,
)

__all__ = [
    "EvidenceExtractionEngine",
    "EvidencePackage",
    "DocumentMetadata",
    "EvidenceFact",
    "EconomicArtifact",
    "ObjectBinding",
    "CashflowRelevance",
    "FundingRelevance",
    "TrustGovernance",
    "ProvenanceInfo",
    "LineageInfo",
    "ConflictItem",
    "DocumentRelationship",
]

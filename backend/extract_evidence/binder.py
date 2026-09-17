from typing import List
from .schemas import ObjectBinding, EvidenceFact, EconomicArtifact

class ObjectBinder:
    """
    Generates Object Binding candidates for DataHub integration.
    Enforces Text Match != Object Truth rule.
    Does NOT auto-assign canonical object_id without explicit authority.
    """

    @staticmethod
    def bind_objects(facts: List[EvidenceFact], artifacts: List[EconomicArtifact]) -> List[ObjectBinding]:
        bindings: List[ObjectBinding] = []

        # Party candidates (Payer / Payee / General Party)
        payer_fact = next((f for f in facts if f.fact_type in ["PAYER", "PARTY"]), None)
        payee_fact = next((f for f in facts if f.fact_type == "PAYEE"), None)

        if payer_fact and payer_fact.value:
            bindings.append(
                ObjectBinding(
                    object_type="PARTY",
                    object_id=None,  # MUST be null until canonical DataHub binding authority confirms
                    candidate_name=str(payer_fact.value),
                    match_status="CANDIDATE",
                    confidence=payer_fact.confidence
                )
            )

        if payee_fact and payee_fact.value:
            bindings.append(
                ObjectBinding(
                    object_type="PARTY",
                    object_id=None,
                    candidate_name=str(payee_fact.value),
                    match_status="CANDIDATE",
                    confidence=payee_fact.confidence
                )
            )

        # Contract reference candidate (e.g., "Thanh toán HĐ 08/2026" -> candidate_reference="08/2026")
        contract_fact = next((f for f in facts if f.fact_type in ["CONTRACT_NUMBER", "BANK_REFERENCE"]), None)
        if contract_fact and contract_fact.value:
            bindings.append(
                ObjectBinding(
                    object_type="CONTRACT",
                    object_id=None,  # MUST BE null! Do NOT auto-bind canonical CONTRACT-08-2026!
                    candidate_name=f"Contract candidate ({contract_fact.value})",
                    candidate_reference=str(contract_fact.value),
                    match_status="CANDIDATE",
                    confidence=0.82
                )
            )

        # Obligation / Event / Settlement / Funding from Economic Artifacts
        for art in artifacts:
            obj_type = art.economic_meaning.economic_object
            if obj_type in ["OBLIGATION", "ECONOMIC_EVENT", "SETTLEMENT", "ASSET", "FUNDING_FACILITY"]:
                bindings.append(
                    ObjectBinding(
                        object_type=obj_type,
                        object_id=None,
                        candidate_name=f"{art.artifact_type} Candidate ({art.economic_meaning.obligation_type or 'UNCLASSIFIED'})",
                        match_status="CANDIDATE",
                        confidence=0.91
                    )
                )

        return bindings

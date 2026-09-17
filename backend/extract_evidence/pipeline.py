import os
import json
import time
import uuid
from typing import Dict, Any, Optional

from .schemas import (
    EvidencePackage,
    DocumentMetadata,
    TrustGovernance,
    FieldConfidences,
    ProvenanceInfo,
    LineageInfo,
    FactSource,
    ExtractionModelInfo
)
from .classifier import DocumentClassifier
from .fact_extractor import AtomicFactExtractor
from .economic_interpreter import EconomicInterpreter
from .binder import ObjectBinder
from .relevance_engine import RelevanceEngine
from .conflict_detector import ConflictDetector
from .graph_engine import DocumentGraphEngine


class EvidenceExtractionEngine:
    """
    Main Evidence Extraction Engine for SMEMONEY CORE-DOC.
    Orchestrates the 16-step Evidence Extraction Pipeline while respecting
    all 15 Non-Negotiable Financial Truth Principles.
    """

    def __init__(self):
        pass

    def _resolve_extracted_data(self, doc_result: dict, doc_id: str = "") -> Optional[dict]:
        """Tìm nạp file _extracted.json tương ứng nếu chưa có trong doc_result."""
        if not doc_result:
            return None

        ext = doc_result.get("extracted_data")
        if ext and isinstance(ext, dict):
            return ext

        # Thử tìm file [OCR] {base_name}_extracted.json trong thư mục output
        file_path = doc_result.get("file_path", "")
        base_name = ""
        if file_path:
            raw_base = os.path.splitext(os.path.basename(file_path))[0]
            base_name = raw_base.replace("[OCR]", "").strip()
        if not base_name:
            orig = doc_result.get("original_filename", "")
            if orig:
                base_name = os.path.splitext(os.path.basename(orig))[0]
                base_name = base_name.replace("[OCR]", "").strip()
        if not base_name and doc_id:
            base_name = os.path.splitext(os.path.basename(doc_id))[0]
            base_name = base_name.replace("[OCR]", "").strip()

        if base_name:
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(curr_dir))
            
            candidate_paths = [
                os.path.join(root_dir, "output", f"[OCR] {base_name}", f"[OCR] {base_name}_extracted.json"),
                os.path.join(root_dir, "output", f"[OCR] {base_name}", f"{base_name}_extracted.json"),
                os.path.join(root_dir, "output", base_name, f"[OCR] {base_name}_extracted.json"),
                os.path.join(root_dir, "output", base_name, f"{base_name}_extracted.json"),
            ]

            # Quét trực tiếp các file kết thúc bằng _extracted.json trong thư mục
            for dir_cand in [os.path.join(root_dir, "output", f"[OCR] {base_name}"), os.path.join(root_dir, "output", base_name)]:
                if os.path.isdir(dir_cand):
                    for fn in os.listdir(dir_cand):
                        if fn.endswith("_extracted.json"):
                            candidate_paths.append(os.path.join(dir_cand, fn))

            for cp in candidate_paths:
                if os.path.exists(cp):
                    try:
                        with open(cp, "r", encoding="utf-8") as f:
                            ext_json = json.load(f)
                            if ext_json and isinstance(ext_json, dict):
                                doc_result["extracted_data"] = ext_json
                                return ext_json
                    except Exception:
                        pass

        # Fallback: Gọi trực tiếp StructuredExtractor
        try:
            from services.structured_extractor import StructuredExtractor
        except ImportError:
            try:
                from backend.services.structured_extractor import StructuredExtractor
            except ImportError:
                StructuredExtractor = None

        if StructuredExtractor:
            try:
                ext_json = StructuredExtractor().extract(doc_result)
                if ext_json and isinstance(ext_json, dict):
                    doc_result["extracted_data"] = ext_json
                    return ext_json
            except Exception as e:
                print(f"[EvidenceExtractionEngine] Cảnh báo gọi StructuredExtractor: {e}")

        return None

    def extract_evidence(
        self,
        doc_id: str,
        artifact_id: str,
        doc_result: dict,
        organization_id: str = "ORG-DEFAULT",
        organization_account_confirmed: bool = False
    ) -> EvidencePackage:
        full_text = doc_result.get("full_text", "")
        category_hint = doc_result.get("category", "")

        # Ưu tiên tìm và nạp JSON Extract
        extracted_data = self._resolve_extracted_data(doc_result, doc_id=doc_id)

        # Step 2: Classify Document into 16 MVP Types
        doc_type, cls_confidence = DocumentClassifier.classify(full_text, category_hint, doc_result)

        # Đồng bộ doc_type từ JSON Extract nếu phân loại thô chưa chắc chắn
        if extracted_data:
            canon_type = extracted_data.get("document_type", "").lower()

            # Nhận diện lại nếu extracted_data là dạng phẳng hoặc 'other'
            if canon_type == "other" or doc_type == "UNKNOWN":
                # 1. Bank transfer
                if any(k in extracted_data for k in ["sender_bank", "receiver_bank", "recipient_bank", "receiver_account", "receiver_account_number", "recipient_account_number", "sender_account_number", "sender_name", "receiver_name", "recipient_name", "transaction_code", "transaction_id", "transaction_time", "transaction_status", "transfer_type"]) or \
                   ("chuyen" in str(extracted_data.get("note", "")).lower()) or \
                   ("chuyen" in str(extracted_data.get("description", "")).lower()) or \
                   ("transaction_details" in extracted_data) or \
                   ("beneficiary" in extracted_data) or \
                   ("recipient" in extracted_data):
                    canon_type = "bank_transfer"
                    extracted_data["document_type"] = "bank_transfer"
                # 2. Warehouse voucher
                elif any(k in extracted_data for k in ["export_from_warehouse", "delivery_location", "total_requested_quantity", "total_actual_quantity", "form_number", "circular", "debit_account", "credit_account", "voucher_metadata", "voucher_info", "company_info"]) or \
                     (isinstance(extracted_data.get("document_number"), str) and ("XK" in extracted_data["document_number"] or "NK" in extracted_data["document_number"])):
                    canon_type = "warehouse_voucher"
                    extracted_data["document_type"] = "warehouse_voucher"
                # 3. Contract
                elif extracted_data.get("contract_number") and not extracted_data.get("invoice_number"):
                    canon_type = "contract"
                    extracted_data["document_type"] = "contract"
                # 4. Invoice
                elif extracted_data.get("invoice_number") or extracted_data.get("invoice_symbol") or "invoice_details" in extracted_data:
                    canon_type = "invoice"
                    extracted_data["document_type"] = "invoice"

            type_map = {
                "invoice": "VAT_INVOICE",
                "contract": "PURCHASE_CONTRACT" if "PURCHASE" in doc_type else ("SALES_CONTRACT" if "SALES" in doc_type else "SERVICE_CONTRACT"),
                "bank_transfer": "BANK_TRANSFER_PROOF",
                "warehouse_voucher": "WAREHOUSE_ISSUE_NOTE",
                "other": "UNKNOWN"
            }
            if canon_type in type_map and (doc_type == "UNKNOWN" or cls_confidence < 0.90 or canon_type in ["bank_transfer", "warehouse_voucher", "contract"]):
                doc_type = type_map[canon_type]
                cls_confidence = 0.98

        # Step 4 & 5: Extract Atomic Facts & Source Provenance (Ưu tiên lấy từ JSON Extract)
        facts = AtomicFactExtractor.extract_facts(doc_id, artifact_id, doc_result, doc_type=doc_type)

        # Extract doc number / date from facts for Document Metadata
        doc_num_fact = next((f for f in facts if f.fact_type in ["INVOICE_NUMBER", "DOCUMENT_NUMBER"]), None)
        if not doc_num_fact:
            doc_num_fact = next((f for f in facts if f.fact_type == "CONTRACT_NUMBER"), None)
        if not doc_num_fact:
            doc_num_fact = next((f for f in facts if f.fact_type == "BANK_REFERENCE"), None)

        doc_date_fact = next((f for f in facts if f.fact_type in ["DOCUMENT_DATE", "INVOICE_DATE"]), None)
        if not doc_date_fact:
            doc_date_fact = next((f for f in facts if f.fact_type in ["CONTRACT_DATE", "TRANSACTION_DATE"]), None)

        doc_meta = DocumentMetadata(
            document_id=doc_id,
            artifact_id=artifact_id,
            document_type=doc_type,
            document_number=str(doc_num_fact.value) if doc_num_fact else None,
            document_date=str(doc_date_fact.value) if doc_date_fact else None,
            organization_id=organization_id,
            version=1
        )

        # Step 6 & 7: Build Economic Artifact & Detect Economic Meaning
        economic_artifacts = EconomicInterpreter.interpret(doc_type, facts, doc_result=doc_result)

        # Step 8: Suggest Object Binding Candidates (Text Match != Object Truth)
        object_bindings = ObjectBinder.bind_objects(facts, economic_artifacts)

        # Step 9: Detect Cross-document Relationship (Document Graph)
        relationships = DocumentGraphEngine.detect_relationships(doc_id, doc_type, facts)

        # Step 10 & 11: Calculate Cashflow Relevance & Funding Relevance
        cashflow_rel, funding_rel = RelevanceEngine.calculate(
            doc_type,
            economic_artifacts,
            facts,
            organization_confirmed=organization_account_confirmed
        )

        # Step 12: Calculate Field-Level Confidences (Section 7)
        fields_conf = {}
        for f in facts:
            fields_conf[f.fact_type.lower()] = f.confidence
        fields_conf["classification"] = cls_confidence

        fact_confs = [f.confidence for f in facts] if facts else [cls_confidence]
        overall_conf = round(sum(fact_confs) / len(fact_confs), 2) if fact_confs else 0.50

        # Step 13: Detect Conflicts (Conflict -> REVIEW)
        conflicts = ConflictDetector.detect_conflicts(facts)

        # Step 14: Set Governance & Lifecycle Statuses (3 distinct status groups)
        review_req = False
        verif_status = "UNVERIFIED"
        pub_status = "PENDING"
        lifecycle = "CANDIDATE"

        # Trigger REVIEW_REQUIRED if:
        # 1. Overall confidence < 0.70
        # 2. Conflicts exist
        # 3. Document type is UNKNOWN
        # 4. Bank transfer account ownership is unconfirmed (CRITICAL RULE 4)
        if (
            overall_conf < 0.70
            or conflicts
            or doc_type == "UNKNOWN"
            or (doc_type in ["BANK_TRANSFER_PROOF", "BANK_STATEMENT"] and not organization_account_confirmed)
        ):
            review_req = True
            verif_status = "REVIEW_REQUIRED"
            pub_status = "BLOCKED"
        else:
            pub_status = "ELIGIBLE"

        trust = TrustGovernance(
            confidence=FieldConfidences(
                overall=overall_conf,
                fields=fields_conf
            ),
            lifecycle_status=lifecycle,
            verification_status=verif_status,
            review_required=review_req,
            publish_status=pub_status
        )

        provenance = ProvenanceInfo(
            document_id=doc_id,
            artifact_id=artifact_id,
            source=FactSource(
                document_id=doc_id,
                artifact_id=artifact_id,
                page=1,
                text=full_text[:300],
                bbox=[0.0, 0.0, 100.0, 100.0]
            ),
            extraction_method="OCR_AI",
            model=ExtractionModelInfo(
                provider="Core OCR & Evidence Engine",
                model_name="SMEMONEY Evidence Engine",
                version="1.0.0"
            ),
            extracted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        lineage = LineageInfo(
            lineage_id=f"LIN-{uuid.uuid4().hex[:8].upper()}",
            parent_document_id=doc_id
        )

        package_id = f"EP-{uuid.uuid4().hex[:8].upper()}"

        evidence_package = EvidencePackage(
            evidence_package_id=package_id,
            document=doc_meta,
            evidence_facts=facts,
            economic_artifacts=economic_artifacts,
            object_bindings=object_bindings,
            document_relationships=relationships,
            cashflow_relevance=cashflow_rel,
            funding_relevance=funding_rel,
            trust=trust,
            provenance=provenance,
            lineage=lineage,
            conflicts=conflicts
        )

        return evidence_package

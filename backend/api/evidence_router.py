import os
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from extract_evidence import EvidenceExtractionEngine, EvidencePackage
    from services.document_service import DocumentService
    from db import (
        save_evidence_package,
        get_evidence_package_by_id,
        update_evidence_verification_status,
        update_evidence_publish_status,
        get_all_document_relationships
    )
except ImportError:
    from backend.extract_evidence import EvidenceExtractionEngine, EvidencePackage
    from backend.services.document_service import DocumentService
    from backend.db import (
        save_evidence_package,
        get_evidence_package_by_id,
        update_evidence_verification_status,
        update_evidence_publish_status,
        get_all_document_relationships
    )

router = APIRouter(prefix="/api/evidence", tags=["Evidence Extraction Engine"])
engine = EvidenceExtractionEngine()
doc_service = DocumentService()


class ExtractEvidenceRequest(BaseModel):
    file_path: Optional[str] = None
    document_id: Optional[str] = None
    artifact_id: Optional[str] = None
    organization_id: Optional[str] = "ORG-DEFAULT"


class VerifyEvidenceRequest(BaseModel):
    notes: Optional[str] = None


class PublishEvidenceRequest(BaseModel):
    status: str = "PUBLISHED"


@router.post("/extract")
def extract_evidence_endpoint(request: ExtractEvidenceRequest):
    """
    Trích xuất Evidence Truth từ tài liệu.
    Nhận file_path hoặc document_id/artifact_id, chạy 16 bước pipeline bóc tách facts, economic artifacts,
    relevance, confidence, conflict & relationship.
    """
    try:
        if not request.file_path and not request.document_id:
            raise HTTPException(status_code=400, detail="Vui lòng cung cấp 'file_path' hoặc 'document_id'.")

        file_path = request.file_path
        if file_path:
            real_path = doc_service.resolve_file_path(file_path)
            doc_result = doc_service.process_file(real_path)
        else:
            # Fallback mock/test doc result
            doc_result = {"full_text": "Sample document content", "category": "van_ban"}

        doc_id = request.document_id or f"DOC-{uuid.uuid4().hex[:8].upper()}"
        art_id = request.artifact_id or f"ART-{uuid.uuid4().hex[:8].upper()}"

        package = engine.extract_evidence(
            doc_id=doc_id,
            artifact_id=art_id,
            doc_result=doc_result,
            organization_id=request.organization_id or "ORG-DEFAULT"
        )

        package_dict = package.model_dump(by_alias=True)

        # Save to DB
        save_evidence_package(package_dict)

        return package_dict
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi bóc tách Evidence: {str(e)}")


@router.get("/graph")
def get_document_graph():
    """Lấy danh sách các cạnh mối quan hệ giữa các tài liệu (Document Graph)."""
    try:
        rels = get_all_document_relationships()
        return {
            "status": "success",
            "total_edges": len(rels),
            "document_relationships": rels
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy Document Graph: {str(e)}")


@router.get("/{evidence_package_id}")
def get_evidence_package(evidence_package_id: str):
    """Lấy thông tin Evidence Package theo ID."""
    pkg = get_evidence_package_by_id(evidence_package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy Evidence Package ID: {evidence_package_id}")
    return pkg


@router.post("/{evidence_package_id}/verify")
def verify_evidence_package(evidence_package_id: str, request: VerifyEvidenceRequest = VerifyEvidenceRequest()):
    """Xác nhận Evidence Truth (VERIFIED)."""
    success = update_evidence_verification_status(evidence_package_id, "VERIFIED", notes=request.notes)
    if not success:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hoặc không thể cập nhật Evidence Package ID: {evidence_package_id}")
    return {
        "status": "success",
        "evidence_package_id": evidence_package_id,
        "verification_status": "VERIFIED",
        "publish_status": "ELIGIBLE"
    }


@router.post("/{evidence_package_id}/reject")
def reject_evidence_package(evidence_package_id: str, request: VerifyEvidenceRequest = VerifyEvidenceRequest()):
    """Từ chối Evidence Truth (REJECTED)."""
    success = update_evidence_verification_status(evidence_package_id, "REJECTED", notes=request.notes)
    if not success:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hoặc không thể cập nhật Evidence Package ID: {evidence_package_id}")
    return {
        "status": "success",
        "evidence_package_id": evidence_package_id,
        "verification_status": "REJECTED",
        "publish_status": "BLOCKED"
    }


@router.post("/{evidence_package_id}/publish")
def publish_evidence_package(evidence_package_id: str, request: PublishEvidenceRequest = PublishEvidenceRequest()):
    """Xuất bản Evidence Truth sang DataHub (PUBLISHED / BLOCKED)."""
    success = update_evidence_publish_status(evidence_package_id, request.status)
    if not success:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hoặc không thể xuất bản Evidence Package ID: {evidence_package_id}")
    return {
        "status": "success",
        "evidence_package_id": evidence_package_id,
        "publish_status": request.status
    }

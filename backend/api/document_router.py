import os
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

try:
    from config import UPLOAD_DIR
    from services.document_service import SUPPORTED_EXTENSIONS
    from api.chat_router import chat_service, format_ai_error
except ImportError:
    from backend.config import UPLOAD_DIR
    from backend.services.document_service import SUPPORTED_EXTENSIONS
    from backend.api.chat_router import chat_service, format_ai_error

try:
    from db import get_all_ocr_documents, get_ocr_document_by_id, get_ocr_document_by_name
except ImportError:
    from backend.db import get_all_ocr_documents, get_ocr_document_by_id, get_ocr_document_by_name

router = APIRouter(tags=["Document Management"])


class SelectFileRequest(BaseModel):
    file_path: Optional[str] = None
    file_id: Optional[int] = None
    doc_id: Optional[int] = None
    file_name: Optional[str] = None
    instruction: Optional[str] = None


@router.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    instruction: Optional[str] = Form(None)
):
    """Tải lên file, xử lý OCR, trích xuất JSON tinh gọn và lưu trực tiếp vào CSDL."""
    try:
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Định dạng file '{ext}' không được hỗ trợ. Các định dạng hợp lệ: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        summary, doc_result = chat_service.upload_and_summarize_stream(
            file.file,
            filename,
            user_instruction=instruction
        )

        return {
            "status": "success",
            "filename": filename,
            "summary": summary,
            "doc_result": doc_result,
            "messages": chat_service.memory.get_messages()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=format_ai_error(e))


@router.post("/api/select-file")
def select_existing_file(request: SelectFileRequest):
    """Chọn tài liệu đã lưu trong CSDL để phân tích / hỏi đáp."""
    try:
        doc = None
        # 1. Tra cứu theo ID (doc_id, file_id hoặc file_path dạng số)
        target_id = request.doc_id or request.file_id
        if not target_id and request.file_path and request.file_path.strip().isdigit():
            target_id = int(request.file_path.strip())

        if target_id:
            doc = get_ocr_document_by_id(target_id)

        # 2. Nếu chưa tìm thấy, tra cứu theo tên file
        if not doc:
            target_name = request.file_name or (os.path.basename(request.file_path) if request.file_path else None)
            if target_name:
                doc = get_ocr_document_by_name(target_name)

        # Nếu tìm thấy trong CSDL MySQL, tải trực tiếp dữ liệu từ DB (không cần đọc ổ đĩa)
        if doc:
            summary, doc_result = chat_service.load_document_from_db(
                doc,
                user_instruction=request.instruction
            )
            return {
                "status": "success",
                "filename": doc.get("file_name", "Tài liệu"),
                "summary": summary,
                "doc_result": doc_result,
                "messages": chat_service.memory.get_messages()
            }

        # 3. Fallback: Nếu là file vật lý trên đĩa
        if request.file_path and os.path.exists(request.file_path):
            summary, doc_result = chat_service.upload_and_summarize(
                request.file_path,
                user_instruction=request.instruction
            )
            return {
                "status": "success",
                "filename": doc_result.get("original_filename", os.path.basename(request.file_path)),
                "summary": summary,
                "doc_result": doc_result,
                "messages": chat_service.memory.get_messages()
            }

        identifier = request.file_name or request.file_path or target_id or "không xác định"
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy tài liệu '{identifier}' trong cơ sở dữ liệu."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=format_ai_error(e))


@router.get("/api/files")
def list_available_files():
    """Lấy danh sách toàn bộ tài liệu đã xử lý lưu trong MySQL Database."""
    file_list = []
    try:
        docs = get_all_ocr_documents(limit=500)
        for d in docs:
            fname = d.get("file_name") or "document"
            ext = d.get("file_type") or os.path.splitext(fname)[1].lower() or ".pdf"
            size = d.get("file_size") or 1024
            file_list.append({
                "id": d.get("id"),
                "name": fname,
                "path": str(d.get("id")),
                "size": size,
                "category": d.get("category", "unclassified"),
                "status": d.get("status", "completed"),
                "created_at": d.get("created_at"),
                "extension": ext
            })
    except Exception as e:
        print(f"[DocumentRouter] Lỗi khi truy vấn CSDL: {e}")

    return {
        "status": "success",
        "total": len(file_list),
        "files": file_list
    }


@router.get("/api/documents/{doc_id}")
def get_document_detail(doc_id: int):
    """Lấy chi tiết kết quả trích xuất JSON tinh gọn từ Database theo ID."""
    doc = get_ocr_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu ID: {doc_id}")
    return {
        "status": "success",
        "document": doc
    }

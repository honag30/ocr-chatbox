import os
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

try:
    from config import DOC_DIR, INPUT_DIR, UPLOAD_DIR
    from services.document_service import SUPPORTED_EXTENSIONS
    from api.chat_router import chat_service, format_ai_error
except ImportError:
    from backend.config import DOC_DIR, INPUT_DIR, UPLOAD_DIR
    from backend.services.document_service import SUPPORTED_EXTENSIONS
    from backend.api.chat_router import chat_service, format_ai_error

router = APIRouter(tags=["Document Management"])


class SelectFileRequest(BaseModel):
    file_path: str
    instruction: Optional[str] = None


@router.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    instruction: Optional[str] = Form(None)
):
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
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=format_ai_error(e))


@router.get("/api/files")
def list_available_files():
    file_list = []
    if os.path.exists(DOC_DIR):
        for root, _, files in os.walk(DOC_DIR):
            rel_folder = os.path.relpath(root, DOC_DIR)
            category_name = rel_folder if rel_folder != "." else "doc"
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    fp = os.path.join(root, f)
                    file_list.append({
                        "name": f,
                        "path": os.path.join("doc", rel_folder, f) if rel_folder != "." else os.path.join("doc", f),
                        "absolute_path": fp,
                        "category": category_name,
                        "size": os.path.getsize(fp),
                        "extension": ext
                    })

    return {
        "status": "success",
        "total": len(file_list),
        "files": file_list
    }

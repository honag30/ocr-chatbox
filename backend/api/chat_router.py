from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from services.chat_service import ChatService
    from db.repositories import get_all_chat_sessions, delete_chat_session
except ImportError:
    from backend.services.chat_service import ChatService
    from backend.db.repositories import get_all_chat_sessions, delete_chat_session

router = APIRouter(tags=["Chat & Sessions"])

# Singleton ChatService
chat_service = ChatService()


class ChatRequest(BaseModel):
    message: str


class SwitchSessionRequest(BaseModel):
    session_id: str


def format_ai_error(e: Exception) -> str:
    if isinstance(e, HTTPException):
        return e.detail
    err_str = str(e)
    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str:
        return "Hệ thống tạm thời quá tải hoặc bạn đã hết lượt dùng thử miễn phí Gemini API (20 lượt/ngày)."
    if "401" in err_str or "403" in err_str or "API_KEY" in err_str:
        return "Khóa API Gemini không hợp lệ. Vui lòng kiểm tra cấu hình GEMINI_API_KEY."
    clean_err = err_str.split("\n")[0] if "\n" in err_str else err_str
    if len(clean_err) > 200:
        clean_err = clean_err[:200] + "..."
    return f"Đã xảy ra lỗi khi xử lý: {clean_err}"


@router.get("/api/sessions")
def get_sessions():
    try:
        sessions = get_all_chat_sessions()
        return {
            "status": "success",
            "sessions": sessions,
            "current_session_id": chat_service.memory.session_id
        }
    except Exception:
        return {
            "status": "success",
            "sessions": [],
            "current_session_id": chat_service.memory.session_id
        }


@router.post("/api/sessions")
def create_session():
    new_id = chat_service.create_new_session("Cuộc trò chuyện mới")
    return {
        "status": "success",
        "session_id": new_id,
        "messages": [],
        "active_doc": None
    }


@router.post("/api/sessions/switch")
def switch_session(request: SwitchSessionRequest):
    chat_service.switch_session(request.session_id)
    return {
        "status": "success",
        "session_id": request.session_id,
        "messages": chat_service.memory.get_messages(),
        "active_doc": chat_service.last_doc_result
    }


@router.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    try:
        delete_chat_session(session_id)
        if chat_service.memory.session_id == session_id:
            chat_service.create_new_session("Cuộc trò chuyện mới")
        sessions = get_all_chat_sessions()
        return {
            "status": "success",
            "sessions": sessions,
            "current_session_id": chat_service.memory.session_id,
            "messages": chat_service.memory.get_messages(),
            "active_doc": chat_service.last_doc_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=format_ai_error(e))


@router.get("/api/history")
def get_history():
    return {
        "status": "success",
        "session_id": chat_service.memory.session_id,
        "messages": chat_service.memory.get_messages(),
        "active_doc": chat_service.last_doc_result
    }


@router.post("/api/clear")
def clear_history():
    chat_service.clear_history()
    return {
        "status": "success",
        "message": "Đã xóa toàn bộ lịch sử và ngữ cảnh tài liệu."
    }


@router.get("/api/doc-result")
def get_doc_result():
    if chat_service.last_doc_result is None:
        return {"status": "empty", "doc_result": None}
    return {"status": "success", "doc_result": chat_service.last_doc_result}


@router.post("/api/chat")
def send_chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Tin nhắn không được để trống.")
    try:
        answer = chat_service.send_message(request.message)
        return {
            "status": "success",
            "answer": answer,
            "messages": chat_service.memory.get_messages()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=format_ai_error(e))

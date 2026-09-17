from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from services.chat_service import ChatService
    from db.repositories import get_all_chat_sessions, delete_chat_session
    from config import key_manager
except ImportError:
    from backend.services.chat_service import ChatService
    from backend.db.repositories import get_all_chat_sessions, delete_chat_session
    from backend.config import key_manager

router = APIRouter(prefix="/api/chatbox", tags=["Chat & Sessions"])

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
    if "model" in err_str.lower() and ("not found" in err_str.lower() or "no longer available" in err_str.lower() or "model_error" in err_str.lower()):
        return "Model AI chỉ định trong file .env không hợp lệ hoặc đã dừng hỗ trợ. Hệ thống khuyến nghị đặt MODEL_NAME=gemini-3.6-flash trong file .env."
    if "AllAPIKeysExhaustedError" in err_str or "tất cả các api keys" in err_str.lower() or "hết hạn hoặc chạm ngưỡng" in err_str.lower():
        return "Tất cả các API Key đều đã hết hạn hoặc hết hạn mức sử dụng (quota). Vui lòng cập nhật hoặc thêm API Key mới vào file .env."
    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str:
        return "Hệ thống tạm thời quá tải hoặc các API key đang chạm ngưỡng giới hạn (vui lòng thử lại sau giây lát hoặc thêm API key mới vào .env)."
    if "401" in err_str or "403" in err_str or "API_KEY" in err_str:
        return "Khóa API Gemini không hợp lệ hoặc đã hết hạn. Vui lòng kiểm tra lại cấu hình GEMINI_API_KEY trong file .env."
    clean_err = err_str.split("\n")[0] if "\n" in err_str else err_str
    if len(clean_err) > 200:
        clean_err = clean_err[:200] + "..."
    return f"Đã xảy ra lỗi khi xử lý: {clean_err}"


@router.get("/keys/status")
def get_key_status():
    """Kiểm tra trạng thái các API Key đang hoạt động trong cơ chế xoay vòng."""
    return {
        "status": "success",
        "data": key_manager.get_status()
    }


@router.get("/sessions")
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


@router.post("/sessions")
def create_session():
    new_id = chat_service.create_new_session("Cuộc trò chuyện mới")
    return {
        "status": "success",
        "session_id": new_id,
        "messages": [],
        "active_doc": None
    }


@router.post("/sessions/switch")
def switch_session(request: SwitchSessionRequest):
    chat_service.switch_session(request.session_id)
    return {
        "status": "success",
        "session_id": request.session_id,
        "messages": chat_service.memory.get_messages(),
        "active_doc": chat_service.last_doc_result
    }


@router.delete("/sessions/{session_id}")
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


@router.get("/history")
def get_history():
    return {
        "status": "success",
        "session_id": chat_service.memory.session_id,
        "messages": chat_service.memory.get_messages(),
        "active_doc": chat_service.last_doc_result
    }


@router.post("/clear")
def clear_history():
    chat_service.clear_history()
    return {
        "status": "success",
        "message": "Đã xóa toàn bộ lịch sử và ngữ cảnh tài liệu."
    }


@router.get("/doc-result")
def get_doc_result():
    if chat_service.last_doc_result is None:
        return {"status": "empty", "doc_result": None}
    return {"status": "success", "doc_result": chat_service.last_doc_result}


@router.post("/chat")
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

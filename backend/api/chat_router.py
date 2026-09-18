from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query
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
    user_id: Optional[str] = None
    actor_id: Optional[str] = None
    session_id: Optional[str] = None


class SwitchSessionRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    actor_id: Optional[str] = None


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "Cuộc trò chuyện mới"
    user_id: Optional[str] = None
    actor_id: Optional[str] = None


class ClearHistoryRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    actor_id: Optional[str] = None


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
def get_sessions(
    user_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_actor_id: Optional[str] = Header(None, alias="X-Actor-Id")
):
    uid = str(user_id or actor_id or x_user_id or x_actor_id or "default_user")
    try:
        sessions = get_all_chat_sessions(user_id=uid)
        return {
            "status": "success",
            "sessions": sessions,
            "user_id": uid,
            "actor_id": uid,
            "current_session_id": chat_service.memory.session_id
        }
    except Exception:
        return {
            "status": "success",
            "sessions": [],
            "user_id": uid,
            "actor_id": uid,
            "current_session_id": chat_service.memory.session_id
        }


@router.post("/api/sessions")
def create_session(
    request: Optional[CreateSessionRequest] = None,
    user_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_actor_id: Optional[str] = Header(None, alias="X-Actor-Id")
):
    title = (request.title if request and request.title else "Cuộc trò chuyện mới")
    uid = str((request.user_id if request and request.user_id else None) or (request.actor_id if request and request.actor_id else None) or user_id or actor_id or x_user_id or x_actor_id or "default_user")
    new_id = chat_service.create_new_session(title=title, user_id=uid)
    return {
        "status": "success",
        "session_id": new_id,
        "user_id": uid,
        "actor_id": uid,
        "messages": [],
        "active_doc": None
    }


@router.post("/api/sessions/switch")
def switch_session(
    request: SwitchSessionRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_actor_id: Optional[str] = Header(None, alias="X-Actor-Id")
):
    uid = str(request.user_id or request.actor_id or x_user_id or x_actor_id or "default_user")
    chat_service.switch_session(request.session_id, user_id=uid)
    return {
        "status": "success",
        "session_id": request.session_id,
        "user_id": uid,
        "actor_id": uid,
        "messages": chat_service.memory.get_messages(),
        "active_doc": chat_service.last_doc_result
    }


@router.delete("/api/sessions/{session_id}")
def delete_session(
    session_id: str,
    user_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_actor_id: Optional[str] = Header(None, alias="X-Actor-Id")
):
    uid = str(user_id or actor_id or x_user_id or x_actor_id or "default_user")
    try:
        delete_chat_session(session_id, user_id=uid)
        if chat_service.memory.session_id == session_id:
            chat_service.create_new_session("Cuộc trò chuyện mới", user_id=uid)
        sessions = get_all_chat_sessions(user_id=uid)
        return {
            "status": "success",
            "sessions": sessions,
            "user_id": uid,
            "actor_id": uid,
            "current_session_id": chat_service.memory.session_id,
            "messages": chat_service.memory.get_messages(),
            "active_doc": chat_service.last_doc_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=format_ai_error(e))


@router.get("/api/history")
def get_history(
    session_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_actor_id: Optional[str] = Header(None, alias="X-Actor-Id")
):
    uid = str(user_id or actor_id or x_user_id or x_actor_id or "default_user")
    if session_id:
        chat_service.switch_session(session_id, user_id=uid)
    else:
        chat_service._prepare_context(user_id=uid)
    return {
        "status": "success",
        "session_id": chat_service.memory.session_id,
        "user_id": uid,
        "actor_id": uid,
        "messages": chat_service.memory.get_messages(),
        "active_doc": chat_service.last_doc_result
    }


@router.post("/api/clear")
def clear_history(
    request: Optional[ClearHistoryRequest] = None,
    user_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_actor_id: Optional[str] = Header(None, alias="X-Actor-Id")
):
    uid = str((request.user_id if request and request.user_id else None) or (request.actor_id if request and request.actor_id else None) or user_id or actor_id or x_user_id or x_actor_id or "default_user")
    sid = (request.session_id if request and request.session_id else None) or session_id
    chat_service.clear_history(session_id=sid, user_id=uid)
    return {
        "status": "success",
        "user_id": uid,
        "actor_id": uid,
        "message": "Đã xóa toàn bộ lịch sử và ngữ cảnh tài liệu."
    }


@router.get("/api/doc-result")
def get_doc_result():
    if chat_service.last_doc_result is None:
        return {"status": "empty", "doc_result": None}
    return {"status": "success", "doc_result": chat_service.last_doc_result}


@router.post("/api/chat")
def send_chat(
    request: ChatRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_actor_id: Optional[str] = Header(None, alias="X-Actor-Id")
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Tin nhắn không được để trống.")
    uid = str(request.user_id or request.actor_id or x_user_id or x_actor_id or "default_user")
    try:
        answer = chat_service.send_message(request.message, user_id=uid, session_id=request.session_id)
        return {
            "status": "success",
            "answer": answer,
            "user_id": uid,
            "actor_id": uid,
            "session_id": chat_service.memory.session_id,
            "messages": chat_service.memory.get_messages()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=format_ai_error(e))

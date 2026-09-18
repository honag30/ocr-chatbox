import os

try:
    from services.memory_service import ChatMemory
    from services.ai_service import AIService
    from services.document_service import DocumentService
except ImportError:
    try:
        from .memory_service import ChatMemory
        from .ai_service import AIService
        from .document_service import DocumentService
    except ImportError:
        from backend.services.memory_service import ChatMemory
        from backend.services.ai_service import AIService
        from backend.services.document_service import DocumentService



class ChatService:

    def __init__(self):
        self.memory = ChatMemory()
        self.ai = AIService()
        self.doc_service = DocumentService()
        self.last_doc_result: dict | None = None

    def _prepare_context(self, user_id: str = "default_user", session_id: str = None):
        """Đảm bảo đúng session_id và user_id trong bộ nhớ."""
        user_id = user_id or "default_user"
        if session_id and (session_id != self.memory.session_id or user_id != self.memory.user_id):
            self.memory.switch_session(session_id, user_id)
        elif user_id != self.memory.user_id:
            self.memory.set_user_id(user_id)

    def send_message(self, message: str, user_id: str = "default_user", session_id: str = None) -> str:
        """Gửi tin nhắn trò chuyện thông thường hoặc câu hỏi tiếp nối về tài liệu theo user_id."""
        self._prepare_context(user_id, session_id)
        self.memory.add_user_message(message)
        messages = self.memory.get_messages()
        answer = self.ai.chat(messages)
        self.memory.add_assistant_message(answer)
        return answer

    def upload_and_summarize_stream(self, file_source, filename: str, user_instruction: str = None, user_id: str = "default_user", session_id: str = None) -> tuple[str, dict]:
        """Xử lý file từ upload stream/bytes theo user_id."""
        self._prepare_context(user_id, session_id)
        doc_result = self.doc_service.process_file_pipeline(file_source, filename, user_id=user_id)
        return self._summarize_and_save_context(doc_result, user_instruction, user_id=user_id)

    def upload_and_summarize(self, file_path: str, user_instruction: str = None, user_id: str = "default_user", session_id: str = None) -> tuple[str, dict]:
        """Xử lý file từ đường dẫn theo user_id."""
        self._prepare_context(user_id, session_id)
        real_path = self.doc_service.resolve_file_path(file_path)
        filename = os.path.basename(real_path)
        doc_result = self.doc_service.process_file_pipeline(real_path, filename, user_id=user_id)
        return self._summarize_and_save_context(doc_result, user_instruction, user_id=user_id)

    def _summarize_and_save_context(self, doc_result: dict, user_instruction: str = None, user_id: str = "default_user") -> tuple[str, dict]:
        """Định dạng ngữ cảnh tài liệu, gọi Gemini AI tóm tắt và lưu vào bộ nhớ theo user_id."""
        doc_context = self.doc_service.format_document_context(doc_result)
        summary = self.ai.summarize_document(doc_context, user_instruction)

        filename = doc_result.get("original_filename", "Tài liệu")
        context_prompt = (
            f"[HỆ THỐNG]: Người dùng vừa tải lên tài liệu '{filename}'. "
            f"Dưới đây là toàn bộ nội dung và bảng biểu đã trích xuất từ tài liệu này:\n\n"
            f"{doc_context}\n\n"
            f"Hãy ghi nhớ nội dung tài liệu này để trả lời các câu hỏi tiếp theo của người dùng."
        )

        user_req_text = f"Tải lên và tóm tắt tài liệu: {filename}"
        if user_instruction:
            user_req_text += f" (Yêu cầu thêm: {user_instruction})"

        self.memory.add_user_message(
            content=f"{context_prompt}\n\n{user_req_text}",
            display_content=user_req_text,
            doc_result=doc_result
        )
        self.memory.add_assistant_message(summary, doc_result=doc_result)
        self.last_doc_result = doc_result

        return summary, doc_result

    def load_document_from_db(self, doc_record: dict, user_instruction: str = None, user_id: str = "default_user", session_id: str = None) -> tuple[str, dict]:
        """Tải tài liệu đã lưu trong CSDL MySQL vào ngữ cảnh phiên chat hiện tại và tóm tắt."""
        self._prepare_context(user_id, session_id)
        import json
        ocr_data = doc_record.get("ocr_data_json") or {}
        if isinstance(ocr_data, str):
            try:
                ocr_data = json.loads(ocr_data)
            except Exception:
                ocr_data = {}

        file_name = doc_record.get("file_name", "Tài liệu")
        category = doc_record.get("category", "unclassified")
        full_text = doc_record.get("extracted_text", "")

        doc_result = {
            "original_filename": file_name,
            "file_path": doc_record.get("file_path", ""),
            "document_type": category,
            "category": category,
            "full_text": full_text,
            "ocr_data_json": ocr_data,
            "data": ocr_data.get("data", {}) if isinstance(ocr_data, dict) else {},
            "tables": [],
            "total_pages": ocr_data.get("file_metadata", {}).get("total_pages", 1) if isinstance(ocr_data, dict) else 1,
            "extraction_method": "database_cache",
            "status": "success"
        }
        return self._summarize_and_save_context(doc_result, user_instruction, user_id=user_id)

    def switch_session(self, session_id: str, user_id: str = "default_user"):
        """Chuyển sang phiên trò chuyện khác theo user_id."""
        user_id = user_id or "default_user"
        self.memory.switch_session(session_id, user_id)
        self.last_doc_result = None
        for msg in reversed(self.memory.get_messages()):
            if msg.get("doc_result"):
                self.last_doc_result = msg["doc_result"]
                break

    def create_new_session(self, title: str = "Cuộc trò chuyện mới", user_id: str = "default_user") -> str:
        """Tạo một phiên trò chuyện mới cho user_id."""
        user_id = user_id or "default_user"
        import uuid
        new_session_id = f"session_{uuid.uuid4().hex[:12]}"
        try:
            try:
                from db import ensure_chat_session
            except ImportError:
                from backend.db import ensure_chat_session
            ensure_chat_session(new_session_id, user_id=user_id, title=title)
        except Exception:
            pass
        self.memory.switch_session(new_session_id, user_id)
        self.last_doc_result = None
        return new_session_id

    def clear_history(self, session_id: str = None, user_id: str = "default_user"):
        """Xóa toàn bộ lịch sử hội thoại."""
        self._prepare_context(user_id, session_id)
        self.memory.clear()
        self.last_doc_result = None

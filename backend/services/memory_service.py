import uuid
try:
    from db import save_chat_message, get_chat_history, update_session_title, clear_session_messages
except ImportError:
    try:
        from backend.db import save_chat_message, get_chat_history, update_session_title, clear_session_messages
    except ImportError:
        save_chat_message = None
        get_chat_history = None
        update_session_title = None
        clear_session_messages = None


class ChatMemory:
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        self.messages = []
        self.load_history()

    def load_history(self):
        self.messages = []
        if get_chat_history:
            history = get_chat_history(self.session_id)
            if history:
                self.messages = history

    def switch_session(self, new_session_id: str):
        self.session_id = new_session_id
        self.load_history()

    def add_user_message(self, content: str, display_content: str = None, doc_result: dict = None):
        is_first_msg = (len(self.messages) == 0)
        
        msg = {
            "role": "user",
            "content": content
        }
        if display_content:
            msg["display_content"] = display_content
        if doc_result:
            msg["doc_result"] = doc_result
        self.messages.append(msg)

        if is_first_msg and update_session_title:
            raw_title = display_content or content
            clean_title = raw_title.replace("[HỆ THỐNG]:", "").strip()
            if len(clean_title) > 40:
                clean_title = clean_title[:40] + "..."
            if clean_title:
                update_session_title(self.session_id, clean_title)

        if save_chat_message:
            save_chat_message(
                session_id=self.session_id,
                role="user",
                content=content,
                display_content=display_content,
                doc_result_json=doc_result
            )

    def add_assistant_message(self, content: str, doc_result: dict = None):
        msg = {
            "role": "assistant",
            "content": content
        }
        if doc_result:
            msg["doc_result"] = doc_result
        self.messages.append(msg)

        if save_chat_message:
            save_chat_message(
                session_id=self.session_id,
                role="assistant",
                content=content,
                doc_result_json=doc_result
            )

    def get_messages(self):
        return self.messages

    def clear(self):
        self.messages = []
        if clear_session_messages:
            clear_session_messages(self.session_id)

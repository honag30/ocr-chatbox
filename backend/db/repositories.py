import json
import logging
from .connection import get_connection, logger


def get_ocr_document_by_hash(file_hash):
    """Tìm kiếm bản ghi tài liệu OCR đã trích xuất thành công theo mã SHA-256 hash."""
    if not file_hash:
        return None
    sql = "SELECT * FROM ocr_documents WHERE file_hash = %s AND status = 'completed' ORDER BY id DESC LIMIT 1;"
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, (file_hash,))
            row = cursor.fetchone()
        conn.close()
        if row and row.get("ocr_data_json"):
            try:
                row["ocr_data_json"] = json.loads(row["ocr_data_json"])
            except Exception:
                pass
        return row
    except Exception as e:
        logger.error(f"Lỗi khi tìm ocr_document theo hash: {e}")
        return None


def get_ocr_document_by_id(doc_id):
    """Lấy chi tiết tài liệu theo ID."""
    sql = "SELECT * FROM ocr_documents WHERE id = %s LIMIT 1;"
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, (doc_id,))
            row = cursor.fetchone()
        conn.close()
        if row and row.get("ocr_data_json"):
            try:
                row["ocr_data_json"] = json.loads(row["ocr_data_json"])
            except Exception:
                pass
        return row
    except Exception as e:
        logger.error(f"Lỗi khi lấy ocr_document theo ID: {e}")
        return None


def get_all_ocr_documents(category=None, limit=100):
    """Lấy danh sách các tài liệu đã OCR."""
    if category:
        sql = "SELECT id, file_name, file_type, category, status, created_at FROM ocr_documents WHERE category = %s ORDER BY id DESC LIMIT %s;"
        params = (category, limit)
    else:
        sql = "SELECT id, file_name, file_type, category, status, created_at FROM ocr_documents ORDER BY id DESC LIMIT %s;"
        params = (limit,)

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        conn.close()
        for r in rows:
            if r.get("created_at"):
                r["created_at"] = r["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        return rows
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách ocr_documents: {e}")
        return []


def save_ocr_document(file_name, file_path, file_size=0, file_type="", file_hash=None, category="unclassified", extracted_text="", ocr_data_json=None, eval_report="", status="completed", error_message=None):
    """Lưu hoặc cập nhật thông tin file và kết quả trích xuất OCR vào bảng ocr_documents."""
    json_str = json.dumps(ocr_data_json, ensure_ascii=False) if isinstance(ocr_data_json, (dict, list)) else ocr_data_json

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            existing_id = None
            if file_hash:
                cursor.execute("SELECT id FROM ocr_documents WHERE file_hash = %s LIMIT 1;", (file_hash,))
                row = cursor.fetchone()
                if row:
                    existing_id = row["id"]
            
            if not existing_id and file_name and file_size > 0:
                cursor.execute("SELECT id FROM ocr_documents WHERE file_name = %s AND file_size = %s LIMIT 1;", (file_name, file_size))
                row = cursor.fetchone()
                if row:
                    existing_id = row["id"]

            if existing_id:
                update_sql = """
                UPDATE ocr_documents
                SET file_name = %s, file_path = %s, file_size = %s, file_type = %s, file_hash = %s,
                    category = %s, extracted_text = %s, ocr_data_json = %s, eval_report = %s,
                    status = %s, error_message = %s, created_at = CURRENT_TIMESTAMP
                WHERE id = %s;
                """
                cursor.execute(update_sql, (file_name, file_path, file_size, file_type, file_hash, category, extracted_text, json_str, eval_report, status, error_message, existing_id))
                conn.close()
                logger.info(f"✅ Đã cập nhật bản ghi ocr_document ID: {existing_id} (thay vì insert trùng).")
                return existing_id

            insert_sql = """
            INSERT INTO ocr_documents (file_name, file_path, file_size, file_type, file_hash, category, extracted_text, ocr_data_json, eval_report, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (file_name, file_path, file_size, file_type, file_hash, category, extracted_text, json_str, eval_report, status, error_message))
            doc_id = cursor.lastrowid
        conn.close()
        return doc_id
    except Exception as e:
        logger.error(f"Lỗi khi lưu ocr_document vào database: {e}")
        return None


def cleanup_duplicate_documents():
    """Dọn dẹp các bản ghi trùng lặp trong bảng ocr_documents."""
    sql_hash = """
    DELETE d1 FROM ocr_documents d1
    INNER JOIN ocr_documents d2 
    WHERE d1.id < d2.id 
      AND d1.file_hash IS NOT NULL 
      AND d1.file_hash = d2.file_hash;
    """
    sql_name_size = """
    DELETE d1 FROM ocr_documents d1
    INNER JOIN ocr_documents d2 
    WHERE d1.id < d2.id 
      AND d1.file_name = d2.file_name 
      AND d1.file_size = d2.file_size;
    """
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            del1 = cursor.execute(sql_hash)
            del2 = cursor.execute(sql_name_size)
            total = del1 + del2
            print(f"🧹 Đã xóa thành công {total} bản ghi trùng lặp trong ocr_documents.")
        conn.close()
        return total
    except Exception as e:
        logger.error(f"Lỗi khi dọn dẹp bản ghi trùng lặp: {e}")
        return 0


def ensure_chat_session(session_id, title="New Chat"):
    """Tạo hoặc cập nhật phiên chat trong bảng chat_sessions."""
    sql = """
    INSERT INTO chat_sessions (session_id, title)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE updated_at=CURRENT_TIMESTAMP;
    """
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, (session_id, title))
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu chat_session: {e}")
        return False


def save_chat_message(session_id, role, content, display_content=None, document_id=None, doc_result_json=None):
    """Lưu một tin nhắn chat vào bảng chat_messages."""
    ensure_chat_session(session_id)
    doc_json_str = json.dumps(doc_result_json, ensure_ascii=False) if isinstance(doc_result_json, (dict, list)) else doc_result_json

    sql = """
    INSERT INTO chat_messages (session_id, role, content, display_content, document_id, doc_result_json)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, (session_id, role, content, display_content, document_id, doc_json_str))
            msg_id = cursor.lastrowid
        conn.close()
        return msg_id
    except Exception as e:
        logger.error(f"Lỗi khi lưu chat_message: {e}")
        return None


def get_chat_history(session_id):
    """Lấy lịch sử tin nhắn của một phiên chat."""
    sql = """
    SELECT role, content, display_content, doc_result_json, created_at
    FROM chat_messages
    WHERE session_id = %s
    ORDER BY id ASC;
    """
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, (session_id,))
            rows = cursor.fetchall()
        conn.close()

        messages = []
        for r in rows:
            msg = {
                "role": r["role"],
                "content": r["content"]
            }
            if r.get("display_content"):
                msg["display_content"] = r["display_content"]
            if r.get("doc_result_json"):
                try:
                    msg["doc_result"] = json.loads(r["doc_result_json"])
                except Exception:
                    msg["doc_result"] = r["doc_result_json"]
            messages.append(msg)
        return messages
    except Exception as e:
        logger.error(f"Lỗi khi đọc chat history: {e}")
        return []


def get_all_chat_sessions():
    """Lấy danh sách tất cả các phiên trò chuyện."""
    sql = """
    SELECT 
        s.session_id,
        s.title,
        s.created_at,
        s.updated_at,
        COUNT(m.id) AS message_count,
        (
            SELECT COALESCE(display_content, content)
            FROM chat_messages 
            WHERE session_id = s.session_id 
            ORDER BY id DESC LIMIT 1
        ) AS last_message
    FROM chat_sessions s
    LEFT JOIN chat_messages m ON s.session_id = m.session_id
    GROUP BY s.session_id, s.title, s.created_at, s.updated_at
    ORDER BY s.updated_at DESC;
    """
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        conn.close()
        for r in rows:
            if r.get("created_at"):
                r["created_at"] = r["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            if r.get("updated_at"):
                r["updated_at"] = r["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
        return rows
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách chat_sessions: {e}")
        return []


def update_session_title(session_id, title):
    """Cập nhật tiêu đề phiên chat."""
    sql = "UPDATE chat_sessions SET title = %s WHERE session_id = %s;"
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, (title, session_id))
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật tiêu đề chat_session: {e}")
        return False


def delete_chat_session(session_id):
    """Xóa phiên trò chuyện và tin nhắn."""
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM chat_messages WHERE session_id = %s;", (session_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE session_id = %s;", (session_id,))
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi xóa chat_session: {e}")
        return False


def clear_session_messages(session_id):
    """Xóa tin nhắn trong phiên trò chuyện."""
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM chat_messages WHERE session_id = %s;", (session_id,))
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi xóa tin nhắn của session: {e}")
        return False

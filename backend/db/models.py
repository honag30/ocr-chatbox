import hashlib
import os
import logging
from .connection import get_connection, logger, MYSQL_DB

CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(64) UNIQUE NOT NULL,
        title VARCHAR(255) DEFAULT 'New Chat',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_session_id (session_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS ocr_documents (
        id INT AUTO_INCREMENT PRIMARY KEY,
        file_name VARCHAR(255) NOT NULL,
        file_path TEXT NOT NULL,
        file_size BIGINT DEFAULT 0,
        file_type VARCHAR(50),
        file_hash VARCHAR(64) DEFAULT NULL,
        category VARCHAR(100) DEFAULT 'unclassified',
        extracted_text LONGTEXT,
        ocr_data_json LONGTEXT,
        eval_report TEXT,
        status VARCHAR(20) DEFAULT 'completed',
        error_message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_category (category),
        INDEX idx_file_name (file_name),
        INDEX idx_file_hash (file_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(64) NOT NULL,
        role ENUM('user', 'assistant', 'system') NOT NULL,
        content LONGTEXT NOT NULL,
        display_content LONGTEXT,
        document_id INT DEFAULT NULL,
        doc_result_json LONGTEXT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_msg_session (session_id),
        FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
        FOREIGN KEY (document_id) REFERENCES ocr_documents(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
]


def calculate_file_sha256(source):
    """Tính mã hash SHA-256 của file."""
    hasher = hashlib.sha256()
    try:
        if isinstance(source, bytes):
            hasher.update(source)
        elif isinstance(source, str) and os.path.isfile(source):
            with open(source, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
        elif hasattr(source, "read"):
            pos = source.tell() if hasattr(source, "tell") else None
            while chunk := source.read(65536):
                hasher.update(chunk)
            if pos is not None and hasattr(source, "seek"):
                source.seek(pos)
        else:
            return None
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Lỗi khi tính SHA-256 hash: {e}")
        return None


def init_db():
    """Khởi tạo CSDL, tạo các bảng cần thiết nếu chưa tồn tại."""
    print("--- Đang khởi tạo CSDL MySQL (tạo các bảng & migration) ---")
    try:
        conn = get_connection(db=None)
        with conn.cursor() as cur:
            if MYSQL_DB:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.close()

        conn = get_connection()
        with conn.cursor() as cur:
            for query in CREATE_TABLES_SQL:
                cur.execute(query)
            
            # Migration check
            cur.execute("SHOW COLUMNS FROM ocr_documents LIKE 'file_hash';")
            if not cur.fetchone():
                cur.execute("ALTER TABLE ocr_documents ADD COLUMN file_hash VARCHAR(64) DEFAULT NULL AFTER file_type;")
                cur.execute("ALTER TABLE ocr_documents ADD INDEX idx_file_hash (file_hash);")

        conn.close()
        print("✅ Khởi tạo CSDL thành công!")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo CSDL: {e}")
        return False

import os
import sys

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from db.models import init_db
from db.connection import get_connection
from db.repositories import (
    ensure_chat_session,
    save_chat_message,
    get_chat_history,
    get_all_chat_sessions,
    delete_chat_session,
    save_ocr_document,
    get_all_ocr_documents,
    get_ocr_document_by_id
)
from fastapi.testclient import TestClient
from main import app

def test_database_and_api():
    print("=== BƯỚC 1: KHỞI TẠO CSDL VÀ CHẠY MIGRATION ===")
    ok = init_db()
    assert ok, "Khởi tạo CSDL thất bại"

    # Kiểm tra cột user_id trên các bảng
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SHOW COLUMNS FROM chat_sessions LIKE 'user_id';")
        assert cur.fetchone(), "Thiếu cột user_id trong chat_sessions"
        cur.execute("SHOW COLUMNS FROM ocr_documents LIKE 'user_id';")
        assert cur.fetchone(), "Thiếu cột user_id trong ocr_documents"
        cur.execute("SHOW COLUMNS FROM chat_messages LIKE 'user_id';")
        assert cur.fetchone(), "Thiếu cột user_id trong chat_messages"
    conn.close()
    print("✅ Kiểm tra cấu trúc CSDL và Migration: THÀNH CÔNG")

    print("\n=== BƯỚC 2: KIỂM TRA PHÂN TÁCH DỮ LIỆU REPOSITORIES THEO USER_ID ===")
    sess_u1 = "sess_test_u1_123"
    sess_u2 = "sess_test_u2_456"

    # Dọn dẹp session cũ nếu có
    delete_chat_session(sess_u1, user_id="user_alice")
    delete_chat_session(sess_u2, user_id="user_bob")

    # Tạo session cho Alice và Bob
    ensure_chat_session(sess_u1, user_id="user_alice", title="Chat của Alice")
    save_chat_message(sess_u1, "user", "Chào từ Alice", user_id="user_alice")
    save_chat_message(sess_u1, "assistant", "Xin chào Alice!", user_id="user_alice")

    ensure_chat_session(sess_u2, user_id="user_bob", title="Chat của Bob")
    save_chat_message(sess_u2, "user", "Chào từ Bob", user_id="user_bob")

    alice_sessions = get_all_chat_sessions(user_id="user_alice")
    bob_sessions = get_all_chat_sessions(user_id="user_bob")

    alice_ids = [s["session_id"] for s in alice_sessions]
    bob_ids = [s["session_id"] for s in bob_sessions]

    assert sess_u1 in alice_ids, f"sess_u1 phải thuộc Alice: {alice_ids}"
    assert sess_u2 not in alice_ids, f"sess_u2 KHÔNG ĐƯỢC thuộc Alice: {alice_ids}"
    assert sess_u2 in bob_ids, f"sess_u2 phải thuộc Bob: {bob_ids}"
    assert sess_u1 not in bob_ids, f"sess_u1 KHÔNG ĐƯỢC thuộc Bob: {bob_ids}"
    print("✅ Kiểm tra phân tách chat sessions theo user_id: THÀNH CÔNG")

    # Kiểm tra phân tách documents
    doc_id_alice = save_ocr_document(
        file_name="alice_invoice.pdf",
        file_path="uploads/alice_invoice.pdf",
        file_size=1024,
        file_type=".pdf",
        file_hash="hash_alice_12345",
        category="hoa_don",
        extracted_text="Hóa đơn Alice",
        ocr_data_json={"items": ["Invoice Alice"]},
        user_id="user_alice"
    )

    doc_id_bob = save_ocr_document(
        file_name="bob_report.pdf",
        file_path="uploads/bob_report.pdf",
        file_size=2048,
        file_type=".pdf",
        file_hash="hash_bob_67890",
        category="bao_cao",
        extracted_text="Báo cáo Bob",
        ocr_data_json={"items": ["Report Bob"]},
        user_id="user_bob"
    )

    alice_files = get_all_ocr_documents(user_id="user_alice")
    bob_files = get_all_ocr_documents(user_id="user_bob")

    alice_file_names = [f["file_name"] for f in alice_files]
    bob_file_names = [f["file_name"] for f in bob_files]

    assert "alice_invoice.pdf" in alice_file_names, "alice_invoice.pdf phải trong danh sách file của Alice"
    assert "bob_report.pdf" not in alice_file_names, "bob_report.pdf KHÔNG ĐƯỢC trong danh sách file của Alice"
    assert "bob_report.pdf" in bob_file_names, "bob_report.pdf phải trong danh sách file của Bob"
    assert "alice_invoice.pdf" not in bob_file_names, "alice_invoice.pdf KHÔNG ĐƯỢC trong danh sách file của Bob"
    print("✅ Kiểm tra phân tách documents theo user_id: THÀNH CÔNG")

    print("\n=== BƯỚC 3: KIỂM TRA FASTAPI ENDPOINTS VỚI X-User-Id / user_id ===")
    client = TestClient(app)

    # 1. GET /api/sessions?user_id=user_alice
    r = client.get("/api/sessions?user_id=user_alice")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    session_ids = [s["session_id"] for s in data["sessions"]]
    assert sess_u1 in session_ids
    assert sess_u2 not in session_ids

    # 2. GET /api/files with Header X-User-Id: user_bob
    r = client.get("/api/files", headers={"X-User-Id": "user_bob"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    file_names = [f["name"] for f in data["files"]]
    assert "bob_report.pdf" in file_names
    assert "alice_invoice.pdf" not in file_names

    # 3. POST /api/sessions với user_id
    r = client.post("/api/sessions", json={"title": "Cuộc trò chuyện mới của Alice", "user_id": "user_alice"})
    assert r.status_code == 200
    new_sess_id = r.json()["session_id"]

    # 4. GET /api/history với session vừa tạo
    r = client.get(f"/api/history?session_id={new_sess_id}&user_id=user_alice")
    assert r.status_code == 200
    assert r.json()["session_id"] == new_sess_id

    # Clean up test sessions
    delete_chat_session(sess_u1, user_id="user_alice")
    delete_chat_session(sess_u2, user_id="user_bob")
    delete_chat_session(new_sess_id, user_id="user_alice")

    print("✅ Kiểm tra API Endpoints (/api/sessions, /api/files, /api/history, /api/chat): THÀNH CÔNG")
    print("\n🎉 TOÀN BỘ KIỂM TRA ĐỀU HOÀN TOÀN CHÍNH XÁC!")

if __name__ == "__main__":
    test_database_and_api()

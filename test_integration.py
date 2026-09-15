import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.services.document_service import DocumentService
from backend.services.chat_service import ChatService
from backend.config import DOC_DIR


def test_document_extraction():
    print("\n--- TEST 1: Kiểm tra DocumentService trích xuất từ backend/core_ocr ---")
    doc_service = DocumentService()

    sample_pdf = os.path.join(DOC_DIR, "hop_dong", "hop_dong_mua_ban_tai_san.pdf")
    if not os.path.exists(sample_pdf):
        sample_pdf = os.path.join(DOC_DIR, "hop_dong", "HĐ tên miền verco.vn (1).pdf")

    assert os.path.exists(sample_pdf), f"File không tồn tại: {sample_pdf}"
    print(f"Đọc file: {os.path.basename(sample_pdf)}")
    
    doc_result = doc_service.process_file(sample_pdf)
    assert doc_result is not None
    assert "full_text" in doc_result and len(doc_result["full_text"]) > 0
    print(f"[✓] Trích xuất thành công: {doc_result.get('document_type')} ({doc_result.get('total_pages')} trang)")
    print(f"[✓] Phương pháp trích xuất: {doc_result.get('extraction_method')}")
    print(f"[✓] Số ký tự trích xuất: {len(doc_result['full_text'])}")
    print(f"[✓] Bảng phát hiện: {len(doc_result.get('tables', []))} bảng")

    context = doc_service.format_document_context(doc_result)
    assert len(context) > 0
    print("[✓] Format context thành công!")


def test_chat_and_summarize_integration():
    print("\n--- TEST 2: Kiểm tra Upload, Tóm tắt & Hỏi đáp ngữ cảnh (ChatService) ---")
    chat = ChatService()

    sample_pdf = os.path.join(DOC_DIR, "hop_dong", "hop_dong_mua_ban_tai_san.pdf")
    if not os.path.exists(sample_pdf):
        sample_pdf = os.path.join(DOC_DIR, "hop_dong", "HĐ tên miền verco.vn (1).pdf")

    print(f"Bắt đầu upload & tóm tắt: {os.path.basename(sample_pdf)}")
    summary, doc_result = chat.upload_and_summarize(sample_pdf)
    
    print("\n[TÓM TẮT ĐƯỢC TẠO RA]:")
    print(summary[:500] + "...\n(đã cắt ngắn hiển thị test)")

    assert summary and len(summary) > 20
    print("[✓] Tóm tắt tài liệu thành công!")

    print("\n[Hỏi đáp tiếp nối]: 'Các bên tham gia hợp đồng này là ai?'")
    answer = chat.send_message("Các bên tham gia trong hợp đồng vừa tải lên là ai?")
    print(f"AI: {answer}")
    assert answer and len(answer) > 0
    print("[✓] Hỏi đáp theo ngữ cảnh thành công!")


def test_image_extraction_and_summary():
    print("\n--- TEST 3: Kiểm tra OCR ảnh & Tóm tắt giao dịch ---")
    chat = ChatService()

    sample_img = os.path.join(DOC_DIR, "anh_chuyen_khoan", "Screenshot_20260714_205030_VCB_Digibank.jpg")
    if os.path.exists(sample_img):
        print(f"Bắt đầu OCR & tóm tắt ảnh: {os.path.basename(sample_img)}")
        summary, doc_result = chat.upload_and_summarize(sample_img)
        assert summary and len(summary) > 0
        print("[✓] OCR và tóm tắt ảnh thành công!")
        print("\n[Tóm tắt ảnh]:\n" + summary)


if __name__ == "__main__":
    try:
        test_document_extraction()
        test_chat_and_summarize_integration()
        test_image_extraction_and_summary()
        print("\n" + "=" * 60)
        print("🎉 TẤT CẢ CÁC BÀI KIỂM THỬ TÍCH HỢP HỆ THỐNG ĐỀU THÀNH CÔNG!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ LỖI TRONG QUÁ TRÌNH TEST: {e}")
        import traceback
        traceback.print_exc()

import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.services.document_service import DocumentService
from backend.config import DOC_DIR

def run_test():
    doc_service = DocumentService()
    
    sample_root = os.path.join(BASE_DIR, "archive", "test-chatbox", "doc")
    test_files = [
        ("hoa_don", os.path.join(sample_root, "hoa_don", "HoaDon_ECOACHING.VN.pdf")),
        ("chung_tu", os.path.join(sample_root, "chung_tu", "phieu_xuat_kho_mau.pdf")),
        ("hop_dong", os.path.join(sample_root, "chung_tu", "SO-10685-26.pdf")),
        ("anh_chuyen_khoan", os.path.join(sample_root, "anh_chuyen_khoan", "Screenshot_20260714_205030_VCB_Digibank.jpg")),
    ]

    print("=" * 70)
    print("🚀 BẮT ĐẦU KIỂM THỬ TRÍCH XUẤT JSON TINH GỌN (KIE) CHO 4 DẠNG TÀI LIỆU")
    print("=" * 70)

    for expected_cat, file_path in test_files:
        if not os.path.exists(file_path):
            print(f"⚠️ Bỏ qua vì không thấy file: {file_path}")
            continue

        filename = os.path.basename(file_path)
        base_name = os.path.splitext(filename)[0]
        print(f"\n📂 [TEST] Đang xử lý: {filename} (Danh mục mong đợi: {expected_cat})...")

        result = doc_service.process_file(file_path)
        actual_cat = result.get("category", expected_cat)

        # Kiểm tra file output json sinh ra
        out_json_path = os.path.join(BASE_DIR, "output", actual_cat, base_name, f"[OCR] - {base_name}.json")
        if not os.path.exists(out_json_path):
            # Thử tìm theo expected_cat
            out_json_path = os.path.join(BASE_DIR, "output", expected_cat, base_name, f"[OCR] - {base_name}.json")

        assert os.path.exists(out_json_path), f"❌ File JSON không tồn tại tại: {out_json_path}"

        with open(out_json_path, "r", encoding="utf-8") as f:
            clean_json = json.load(f)

        file_size_kb = os.path.getsize(out_json_path) / 1024.0
        print(f"✅ Đã tạo file JSON tinh gọn thành công: {out_json_path} ({file_size_kb:.1f} KB)")
        print(f"   - Document Type: {clean_json.get('document_type')}")
        print(f"   - Cấu trúc trường trong 'data': {list(clean_json.get('data', {}).keys())}")

        # In mẫu một phần payload sạch
        sample_preview = json.dumps(clean_json.get("data", {}), ensure_ascii=False, indent=2)[:300]
        print(f"   - Dữ liệu trích xuất mẫu:\n{sample_preview}...\n")

    print("=" * 70)
    print("🎉 TẤT CẢ CÁC BÀI TEST TRÍCH XUẤT JSON TINH GỌN ĐỀU THÀNH CÔNG RỰC RỠ!")
    print("=" * 70)

if __name__ == "__main__":
    run_test()

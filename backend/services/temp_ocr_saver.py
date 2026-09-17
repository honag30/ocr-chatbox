"""
temp_ocr_saver.py - LOGIC TẠM THỜI (SẼ XÓA SAU NÀY)
Mục đích: Lưu lại toàn bộ kết quả OCR đã đọc từ các tài liệu vào thư mục riêng:
[OCR] {tên tài liệu}
Bao gồm:
- [OCR] {tên tài liệu}.txt : Nội dung text trích xuất chi tiết
- [OCR] {tên tài liệu}.json: Cấu trúc JSON đầy đủ của doc_result
"""

import os
import json


def save_temp_ocr_folder(filename: str, doc_result: dict, base_output_dir: str = None) -> str:
    """
    Tạo folder [OCR] {tên tài liệu} và lưu lại toàn bộ kết quả OCR đã đọc (text, json).
    """
    try:
        raw_name = os.path.basename(filename)
        base_name = os.path.splitext(raw_name)[0]
        if not base_name:
            base_name = "document"

        # Tên folder theo đúng yêu cầu: [OCR] {tên tài liệu}
        folder_name = f"[OCR] {base_name}"

        # Xác định thư mục output ở cấp root dự án (d:\AI\ocr\output)
        if not base_output_dir:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            root_dir = os.path.dirname(backend_dir)
            base_output_dir = os.path.join(root_dir, "output")

        target_dir = os.path.join(base_output_dir, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        full_text = doc_result.get("full_text", "")
        pages = doc_result.get("pages", [])
        category = doc_result.get("category", "khac")
        source_type = doc_result.get("source_type", "unknown")
        extraction_method = doc_result.get("extraction_method", "unknown")
        total_pages = doc_result.get("total_pages", len(pages) if pages else 1)

        # 1. Lưu file TXT
        txt_path = os.path.join(target_dir, f"[OCR] {base_name}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"=== KẾT QUẢ OCR: {raw_name} ===\n")
            f.write(f"Tên tài liệu: {base_name}\n")
            f.write(f"Danh mục phân loại: {category}\n")
            f.write(f"Định dạng nguồn: {source_type}\n")
            f.write(f"Phương pháp trích xuất: {extraction_method}\n")
            f.write(f"Tổng số trang: {total_pages}\n")
            f.write("=" * 60 + "\n\n")

            if pages and len(pages) > 1:
                for pg in pages:
                    p_num = pg.get("page", 1)
                    p_method = pg.get("method", extraction_method)
                    f.write(f"--- TRANG {p_num} (Method: {p_method}) ---\n")
                    f.write(pg.get("text", "").strip() + "\n\n")
            else:
                f.write(full_text.strip() + "\n")

        # 2. Lưu file JSON đầy đủ
        json_path = os.path.join(target_dir, f"[OCR] {base_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(doc_result, f, ensure_ascii=False, indent=2, default=str)

        # 3. Trích xuất và lưu file _extracted.json chuẩn hóa theo 5 Schema
        try:
            from services.structured_extractor import StructuredExtractor
        except ImportError:
            try:
                from backend.services.structured_extractor import StructuredExtractor
            except ImportError:
                StructuredExtractor = None

        if StructuredExtractor:
            try:
                extractor = StructuredExtractor()
                target_doc_type = doc_result.get("document_type") or category
                extracted_data = extractor.extract(doc_result, target_type=target_doc_type)
                doc_result["extracted_data"] = extracted_data

                extracted_json_path = os.path.join(target_dir, f"[OCR] {base_name}_extracted.json")
                with open(extracted_json_path, "w", encoding="utf-8") as f:
                    json.dump(extracted_data, f, ensure_ascii=False, indent=2, default=str)
                print(f"[TEMP_OCR_SAVER] 📋 Đã trích xuất và lưu dữ liệu cấu trúc: '{extracted_json_path}'")
            except Exception as e_ext:
                print(f"[TEMP_OCR_SAVER] Cảnh báo lỗi trích xuất dữ liệu cấu trúc: {e_ext}")

        print(f"[TEMP_OCR_SAVER] 📁 Đã lưu kết quả OCR vào folder: '{target_dir}'")
        return target_dir
    except Exception as e:
        print(f"[TEMP_OCR_SAVER] Cảnh báo lỗi lưu folder tạm: {e}")
        return ""

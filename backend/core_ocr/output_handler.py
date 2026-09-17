import os
import sys
import json
from datetime import datetime

# Ensure sys.path includes package dirs
CORE_OCR_DIR = os.path.dirname(os.path.abspath(__file__))
CHATBOX_DIR = os.path.dirname(CORE_OCR_DIR)

for p in [CORE_OCR_DIR, CHATBOX_DIR, os.path.join(CORE_OCR_DIR, "schemas"), os.path.join(CORE_OCR_DIR, "extractors"), os.path.join(CORE_OCR_DIR, "summary"), os.path.join(CORE_OCR_DIR, "renderer")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from entity_extractor import extract_entities
from llm_extractor import LLMExtractor
from summary_generator import generate_document_summary
from summary_renderer import render_document_summary
from document_classifier import get_classification_metadata

def format_line(index: int, conf: float, text: str) -> str:
    """
    Định dạng dòng kết quả theo chuẩn gọn: [### - %%] Nội dung dòng
    """
    conf_val = conf * 100.0 if conf is not None else 100.0
    return f"[{index:03d} - {conf_val:.1f}%] {text}"


def save_ocr_output(
    original_filename: str,
    category_code: str,
    doc_result: dict,
    eval_report: str = "",
    output_base_dir: str = "output"
) -> tuple[str, str]:
    """
    Lưu kết quả đọc/trích xuất tài liệu:
    - Trích xuất thông tin trọng tâm tinh gọn (Clean / Essential Key Information Extraction - KIE).
    - Xuất file [OCR] - {base_name}.json CHỈ chứa các thông tin quan trọng để xử lý downstream.
    - Xuất file [OCR] - {base_name}.txt cho việc đọc hiểu và kiểm tra.
    - Lưu vào CSDL MySQL (nếu có kết nối).
    """
    full_text = doc_result.get("full_text", "")
    base_name = os.path.splitext(original_filename)[0]

    # 1. Phân loại và chuẩn hóa document_type
    type_map = {
        "hop_dong": "contract",
        "contract": "contract",
        "hoa_don": "invoice",
        "invoice": "invoice",
        "chung_tu": "voucher",
        "voucher": "voucher",
        "anh_chuyen_khoan": "bank_transfer",
        "bank_transfer": "bank_transfer",
        "khac": "unknown"
    }
    doc_type = type_map.get(category_code, "unknown")

    # 2. Trích xuất thông tin có cấu trúc tinh gọn (KIE)
    llm_ext = LLMExtractor()
    structured_data, extraction_metadata = llm_ext.extract(doc_result, doc_type)

    # Lấy payload sạch nằm trong trường "data"
    if isinstance(structured_data, dict) and "data" in structured_data:
        clean_data = structured_data["data"]
    else:
        clean_data = structured_data

    # Generate Summary
    doc_summary = generate_document_summary(structured_data, doc_type, doc_result)

    # 3. Tạo thư mục output chuẩn
    doc_folder = os.path.join(output_base_dir, category_code, base_name)
    os.makedirs(doc_folder, exist_ok=True)

    out_filename_txt = f"[OCR] - {base_name}.txt"
    out_filename_json = f"[OCR] - {base_name}.json"
    out_filename_kie = f"[KIE] - {base_name}.json"

    out_path_txt = os.path.join(doc_folder, out_filename_txt)
    out_path_json = os.path.join(doc_folder, out_filename_json)
    out_path_kie = os.path.join(doc_folder, out_filename_kie)

    # 4. Ghi file TXT (Văn bản + Summary để kiểm tra thủ công)
    with open(out_path_txt, "w", encoding="utf-8") as out:
        out.write(f"=== KẾT QUẢ TRÍCH XUẤT TÀI LIỆU: {original_filename} ===\n")
        out.write(f"Danh mục: {category_code}\n")
        out.write(f"Loại tài liệu (Document Type): {doc_type}\n")
        out.write(f"Định dạng nguồn (Source Type): {doc_result.get('source_type')}\n")
        out.write(f"Phương pháp trích xuất: {doc_result.get('extraction_method')}\n\n")

        # In Document Summary rendered
        root_temp = {
            "document_type": doc_type,
            "document_summary": doc_summary,
            "structured_data": structured_data
        }
        out.write(render_document_summary(root_temp) + "\n\n")

        out.write("--- NỘI DUNG VĂN BẢN ĐỌC ĐƯỢC ---\n")
        out.write(full_text + "\n\n")

        tables = doc_result.get("tables", [])
        if tables:
            out.write("--- CẤU TRÚC BẢNG TRÍCH XUẤT ---\n")
            for t_idx, tbl in enumerate(tables, 1):
                out.write(f"\n[Bảng {t_idx} - Trang {tbl.get('page', 1)}]\n")
                out.write(tbl.get("markdown", "") + "\n")

        if eval_report:
            out.write("\n" + eval_report + "\n")

    # 5. Ghi file JSON TINH GỌN (Chỉ chứa thông tin quan trọng)
    clean_json_output = {
        "document_type": category_code,
        "file_metadata": {
            "file_name": original_filename,
            "category": category_code,
            "source_type": doc_result.get("source_type"),
            "total_pages": doc_result.get("total_pages", 1),
            "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "data": clean_data
    }

    with open(out_path_json, "w", encoding="utf-8") as jout:
        json.dump(clean_json_output, jout, ensure_ascii=False, indent=2)

    with open(out_path_kie, "w", encoding="utf-8") as kjout:
        json.dump(clean_json_output, kjout, ensure_ascii=False, indent=2)

    # 6. Đồng bộ lưu vào CSDL MySQL (nếu có cấu hình DB)
    doc_result["key_information"] = clean_data
    doc_result["structured_data"] = structured_data
    try:
        from db import save_ocr_document
        file_path = doc_result.get("file_path", "")
        file_size = os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
        file_type = os.path.splitext(original_filename)[1].lower()

        doc_id = save_ocr_document(
            file_name=original_filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            category=category_code,
            extracted_text=full_text,
            ocr_data_json=clean_json_output,
            eval_report=eval_report,
            status="completed"
        )
        if doc_id:
            print(f"[OutputHandler] ✅ Đã lưu JSON tinh gọn vào MySQL Database (ID: {doc_id}) và folder: {out_path_json}")
    except Exception as db_err:
        pass

    return out_path_txt, out_path_json


def display_ocr_result(original_filename: str, doc_result: dict, eval_report: str = "", category_code: str = ""):
    """
    Hiển thị kết quả trích xuất văn bản, summary theo document_type và báo cáo lên console.
    """
    full_text = doc_result.get("full_text", "")
    type_map = {
        "hop_dong": "contract",
        "contract": "contract",
        "hoa_don": "invoice",
        "invoice": "invoice",
        "chung_tu": "voucher",
        "voucher": "voucher",
        "anh_chuyen_khoan": "bank_transfer",
        "bank_transfer": "bank_transfer",
        "khac": "unknown"
    }
    doc_type = type_map.get(category_code, "unknown")

    # Dynamic extraction for display
    llm_ext = LLMExtractor()
    structured_data, _ = llm_ext.extract(doc_result, doc_type)
    doc_summary = generate_document_summary(structured_data, doc_type, doc_result)

    root_temp = {
        "document_type": doc_type,
        "document_summary": doc_summary,
        "structured_data": structured_data
    }

    print("\n" + render_document_summary(root_temp))
    print(f"\n--- KẾT QUẢ ĐỌC VĂN BẢN TRỰC TIẾP: {original_filename} ---")
    print(full_text[:500] + ("..." if len(full_text) > 500 else ""))

    tables = doc_result.get("tables", [])
    if tables:
        print("\n--- BẢNG PHÁT HIỆN ĐƯỢC (TABLE STRUCTURE) ---")
        for t_idx, tbl in enumerate(tables, 1):
            print(f"\n[Bảng {t_idx} - Trang {tbl.get('page', 1)}]")
            print(tbl.get("markdown", ""))

    if eval_report:
        print("\n" + eval_report)


def display_category_header(cat_name: str, folder_path: str):
    print(f"\n" + "=" * 60)
    print(f"  TRÍCH XUẤT TÀI LIỆU DANH MỤC: {cat_name.upper()}")
    print(f"  Thư mục tài liệu gốc: {folder_path}")
    print("=" * 60)


def display_all_completed_summary(total_processed: int, category_code: str = None):
    if category_code:
        print(f"\n=> HOÀN THÀNH TRÍCH XUẤT! Tất cả kết quả đã lưu vào thư mục 'output/{category_code}/'")
    else:
        print(f"\n=> TỔNG CỘNG ĐÃ OCR HOÀN TẤT {total_processed} FILE! Kết quả được lưu tại thư mục 'output/'.")

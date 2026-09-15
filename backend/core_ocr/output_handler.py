import os
import sys
import json

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
    - Nếu kết nối MySQL thành công và lưu vào CSDL thành công -> bỏ qua lưu file vào folder.
    - Nếu chưa lưu được vào DB -> fallback lưu vào folder output standard.
    """
    # 1. Thử lưu vào CSDL MySQL
    try:
        from db import save_ocr_document
        
        file_path = doc_result.get("file_path", "")
        file_size = os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
        file_type = os.path.splitext(original_filename)[1].lower()
        full_text = doc_result.get("full_text", "")

        doc_id = save_ocr_document(
            file_name=original_filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            category=category_code,
            extracted_text=full_text,
            ocr_data_json=doc_result,
            eval_report=eval_report,
            status="completed"
        )
        if doc_id:
            print(f"[OutputHandler] ✅ Đã lưu kết quả OCR thành công vào MySQL Database (ID: {doc_id}). Bỏ qua lưu folder output.")
            return f"DB_DOC_ID:{doc_id}", f"DB_DOC_ID:{doc_id}"
    except Exception as db_err:
        print(f"[OutputHandler] Không thể lưu vào MySQL DB ({db_err}). Tiến hành lưu vào folder output...")

    # 2. Fallback lưu vào folder output
    base_name = os.path.splitext(original_filename)[0]
    doc_folder = os.path.join(output_base_dir, category_code, base_name)
    os.makedirs(doc_folder, exist_ok=True)

    out_filename_txt = f"[OCR] - {base_name}.txt"
    out_filename_json = f"[OCR] - {base_name}.json"

    out_path_txt = os.path.join(doc_folder, out_filename_txt)
    out_path_json = os.path.join(doc_folder, out_filename_json)

    full_text = doc_result.get("full_text", "")
    extracted_entities = extract_entities(doc_result, category_code)
    entity_fields = extracted_entities.get("fields", {})

    # Classification & Document Understanding Layer
    type_map = {
        "hop_dong": "contract",
        "hoa_don": "invoice",
        "chung_tu": "voucher",
        "anh_chuyen_khoan": "bank_transfer",
        "khac": "unknown"
    }
    doc_type = type_map.get(category_code, "unknown")

    classification_meta = {
        "document_type": doc_type,
        "category": category_code,
        "confidence": 0.95 if doc_type != "unknown" else 0.42,
        "reason": f"Phân loại danh mục '{category_code}' tự động thành loại tài liệu '{doc_type}'."
    }

    # Extract Structured Data via LLMExtractor (Gemini / Rule-based fallback)
    llm_ext = LLMExtractor()
    structured_data, extraction_metadata = llm_ext.extract(doc_result, doc_type)

    # Generate Summary
    doc_summary = generate_document_summary(structured_data, doc_type, doc_result)

    # 1. Lưu file TXT
    with open(out_path_txt, "w", encoding="utf-8") as out:
        out.write(f"=== KẾT QUẢ TRÍCH XUẤT TÀI LIỆU: {original_filename} ===\n")
        out.write(f"Danh mục: {category_code}\n")
        out.write(f"Loại tài liệu (Document Type): {doc_type}\n")
        out.write(f"Định dạng nguồn (Source Type): {doc_result.get('source_type')}\n")
        out.write(f"Phương pháp trích xuất (Method): {doc_result.get('extraction_method')}\n\n")

        # In Document Summary rendered
        root_temp = {
            "document_type": doc_type,
            "document_summary": doc_summary,
            "structured_data": structured_data
        }
        out.write(render_document_summary(root_temp) + "\n\n")

        out.write("--- NỘI DUNG VĂN BẢN ---\n")
        out.write(full_text + "\n\n")

        tables = doc_result.get("tables", [])
        if tables:
            out.write("--- CẤU TRÚC BẢNG TRÍCH XUẤT ---\n")
            for t_idx, tbl in enumerate(tables, 1):
                out.write(f"\n[Bảng {t_idx} - Trang {tbl.get('page', 1)}]\n")
                out.write(tbl.get("markdown", "") + "\n")

        if entity_fields:
            out.write("\n--- THÔNG TIN TRÍCH XUẤT CẤU TRÚC (EXTRACTED ENTITIES) ---\n")
            for k, v in entity_fields.items():
                if isinstance(v, list):
                    v_str = ", ".join(map(str, v))
                else:
                    v_str = str(v)
                out.write(f"• {k}: {v_str}\n")

        if eval_report:
            out.write("\n" + eval_report + "\n")

    # 2. Lưu file JSON mở rộng (Bảo tồn 100% tất cả các trường cũ)
    ocr_lines_legacy = []
    line_idx = 1
    for pg in doc_result.get("pages", []):
        pg_lines = pg.get("lines", [])
        pg_confs = pg.get("confidences", [])
        for i, l in enumerate(pg_lines):
            conf_val = pg_confs[i] * 100.0 if (pg_confs and i < len(pg_confs) and pg_confs[i] is not None) else None
            ocr_lines_legacy.append({
                "index": line_idx,
                "page": pg.get("page", 1),
                "text": l,
                "confidence": conf_val
            })
            line_idx += 1

    json_data = {
        "original_filename": original_filename,
        "category": category_code,
        "document_type": doc_type,
        "source_type": doc_result.get("source_type"),
        "extraction_method": doc_result.get("extraction_method"),
        "has_table": doc_result.get("has_table", False),
        "total_pages": doc_result.get("total_pages", 1),
        "extracted_entities": entity_fields,
        "pages": doc_result.get("pages", []),
        "full_text": full_text,
        "tables": doc_result.get("tables", []),
        "ocr_lines": ocr_lines_legacy,

        # New Document Understanding Layers
        "document_summary": doc_summary,
        "structured_data": structured_data,
        "classification": classification_meta,
        "extraction_metadata": extraction_metadata
    }

    with open(out_path_json, "w", encoding="utf-8") as jout:
        json.dump(json_data, jout, ensure_ascii=False, indent=2)

    return out_path_txt, out_path_json


def display_ocr_result(original_filename: str, doc_result: dict, eval_report: str = "", category_code: str = ""):
    """
    Hiển thị kết quả trích xuất văn bản, summary theo document_type và báo cáo lên console.
    """
    full_text = doc_result.get("full_text", "")
    type_map = {
        "hop_dong": "contract",
        "hoa_don": "invoice",
        "chung_tu": "voucher",
        "anh_chuyen_khoan": "bank_transfer",
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

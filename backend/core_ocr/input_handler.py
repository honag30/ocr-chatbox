import os
import re
import cv2
import numpy as np
import pymupdf  # fitz

from normalizer import normalize_vietnamese_text, is_usable_text, detect_headers_footers
from image_processor import preprocess_image
from ocr_utils import group_results_by_line
from table_detector import extract_table_from_raw_results, format_table_to_markdown, extract_native_pdf_tables_from_page

# ---------------------------------------------------------------------------
# Shared EasyOCR singleton — dùng chung toàn bộ ứng dụng, chỉ load 1 lần
# ---------------------------------------------------------------------------
_ocr_reader = None

def get_ocr_reader():
    """
    Khởi tạo EasyOCR Reader một lần duy nhất (Lazy singleton).
    Dùng chung giữa document_reader/input_handler và document_classifier để tránh load model 2 lần.
    """
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            print("[System] Initializing EasyOCR Reader (vi, en) — CPU mode...")
            _ocr_reader = easyocr.Reader(
                ['vi', 'en'],
                gpu=False,
                verbose=False,
            )
        except Exception as e:
            print(f"[System] ⚠️ EasyOCR không khả dụng ({e}). Sẽ sử dụng Multimodal Vision OCR tự động.")
            return None
    return _ocr_reader

# ---------------------------------------------------------------------------
# Tham số OCR tối ưu cho CPU
# ---------------------------------------------------------------------------
_OCR_PARAMS_CPU = {
    "decoder": "greedy",       # greedy nhanh hơn beamsearch 3-5x, đủ chính xác
    "beamWidth": 5,            # chỉ dùng khi decoder='beamsearch'
    "text_threshold": 0.5,     # tăng từ 0.4 → 0.5: lọc bớt noise, tăng tốc
    "low_text": 0.25,          # tăng nhẹ để bỏ false positive text
    "link_threshold": 0.4,
    "mag_ratio": 2.0,          # không phóng to nữa — đã xử lý trong preprocess_image
    "batch_size": 1,           # tăng nếu có nhiều ảnh cùng lúc
    "paragraph": False,        # tắt paragraph mode để giữ nguyên cấu trúc dòng
}

# DPI render PDF scan — 150 là đủ cho EasyOCR, giảm pixel ~43% so với 200
_PDF_SCAN_DPI = 150


def classify_text_element(line: str) -> dict:
    """
    Phân loại từng dòng/đoạn văn bản thành cấu trúc:
    heading | list | paragraph
    """
    line_clean = line.strip()
    if not line_clean:
        return {"type": "paragraph", "text": ""}

    # 1. Heading (Ví dụ: ĐIỀU 1, MỤC I, CHƯƠNG II, hoặc IN HOA HOÀN TOÀN có chữ ngắn)
    heading_patterns = [
        r'^(ĐIỀU|Đieu|CHƯƠNG|Chương|MỤC|Mục|PHẦN|Phần)\s+\d+',
        r'^[I|V|X]+\.\s+',
        r'^\d+\.\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]',
    ]
    is_heading = any(re.search(pat, line_clean) for pat in heading_patterns)
    if not is_heading and line_clean.isupper() and len(line_clean) < 80 and not line_clean.endswith('.'):
        is_heading = True

    if is_heading:
        return {"type": "heading", "text": line_clean}

    # 2. List Item (Ví dụ: - ..., + ..., 1.1 ..., a) ...)
    list_patterns = [
        r'^[•\-\*\+]\s+',
        r'^\d+\.\d+(\.\d+)?\s+',
        r'^[a-z]\)\s+',
    ]
    if any(re.search(pat, line_clean) for pat in list_patterns):
        return {"type": "list", "text": line_clean}

    return {"type": "paragraph", "text": line_clean}


def read_pdf(file_path: str, include_header: bool = True, include_footer: bool = True) -> dict:
    """
    Đọc file PDF theo từng trang:
    - Trang nào có text layer hợp lệ -> Native Text & Table Extraction
    - Trang nào không có text / scan / font lỗi -> Render thành ảnh -> EasyOCR
    - Nhận diện Header/Footer và hỗ trợ bao gồm hoặc loại bỏ.
    """
    doc = pymupdf.open(file_path)
    total_pages = len(doc)
    print(f"[PDF] Detected {total_pages} page(s) in '{os.path.basename(file_path)}'")

    page_results = []
    page_texts_raw = []

    native_pages_count = 0
    ocr_pages_count = 0
    all_tables = []

    for idx in range(total_pages):
        page_num = idx + 1
        page = doc[idx]
        native_text = page.get_text("text") or ""
        native_text = normalize_vietnamese_text(native_text)

        tables_in_page = []

        # 1. Kiểm tra chất lượng Native Text
        usable = is_usable_text(native_text, min_length=20)

        if usable:
            native_pages_count += 1
            print(f"  [Page {page_num}/{total_pages}] Native text extraction (Success)")

            # Extract bảng bằng thuật toán Native PDF Spatial Classification
            tables_in_page = extract_native_pdf_tables_from_page(page, page_num)

            lines = [l.strip() for l in native_text.split('\n') if l.strip()]
            elements = [classify_text_element(l) for l in lines]

            page_results.append({
                "page": page_num,
                "method": "native_text",
                "confidence": None,
                "text": native_text,
                "lines": lines,
                "elements": elements,
                "tables": tables_in_page
            })
            page_texts_raw.append(native_text)
        else:
            ocr_pages_count += 1
            print(f"  [Page {page_num}/{total_pages}] No usable text layer -> Fallback to OCR")

            # Render trang thành ảnh — DPI 150 thay vì 200 (giảm pixel ~43%)
            pix = page.get_pixmap(dpi=_PDF_SCAN_DPI)
            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))

            if pix.n == 4:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

            # fast_mode=True: không upscale cứng 2x, dùng GaussianBlur thay fastNlMeans
            processed_img = preprocess_image(img_np, image_input_is_np=True, fast_mode=True)

            reader = get_ocr_reader()
            raw_results = reader.readtext(
                processed_img,
                decoder=_OCR_PARAMS_CPU["decoder"],
                text_threshold=_OCR_PARAMS_CPU["text_threshold"],
                low_text=_OCR_PARAMS_CPU["low_text"],
                link_threshold=_OCR_PARAMS_CPU["link_threshold"],
                mag_ratio=_OCR_PARAMS_CPU["mag_ratio"],
                batch_size=_OCR_PARAMS_CPU["batch_size"],
                paragraph=_OCR_PARAMS_CPU["paragraph"],
            )

            ocr_lines, ocr_confs = group_results_by_line(raw_results, y_tolerance=20)
            avg_conf = round(sum(ocr_confs) / max(1, len(ocr_confs)) * 100.0, 2) if ocr_confs else 0.0

            # Phát hiện bảng từ OCR + OpenCV grid
            if not tables_in_page:
                matrix, found, struct_t = extract_table_from_raw_results(raw_results, image=processed_img)
                if found:
                    headers = matrix[0] if matrix else []
                    rows = matrix[1:] if len(matrix) > 1 else []
                    table_obj = {
                        "type": "table",
                        "page": page_num,
                        "detection_method": struct_t.get("detection_method", "ocr_table"),
                        "headers": headers,
                        "rows": rows,
                        "matrix": matrix,
                        "markdown": format_table_to_markdown(matrix)
                    }
                    tables_in_page.append(table_obj)

            # Giải phóng ảnh khỏi bộ nhớ ngay sau khi dùng
            del pix, img_np, processed_img

            page_text_ocr = normalize_vietnamese_text("\n".join(ocr_lines))
            elements = [classify_text_element(l) for l in ocr_lines]

            page_results.append({
                "page": page_num,
                "method": "ocr",
                "confidence": avg_conf,
                "text": page_text_ocr,
                "lines": ocr_lines,
                "confidences": ocr_confs,
                "elements": elements,
                "tables": tables_in_page
            })
            page_texts_raw.append(page_text_ocr)

        if tables_in_page:
            all_tables.extend(tables_in_page)

    doc.close()

    # Determine source_type & extraction_method
    if ocr_pages_count == 0:
        source_type = "pdf_text"
        extraction_method = "native_text"
    elif native_pages_count == 0:
        source_type = "pdf_scan"
        extraction_method = "ocr"
    else:
        source_type = "pdf_mixed"
        extraction_method = "mixed"

    # Header / Footer detection
    headers_set, footers_set = detect_headers_footers(page_texts_raw)

    full_text_lines = []
    for pr in page_results:
        for l in pr.get("lines", []):
            l_clean = l.strip()
            if not include_header and l_clean in headers_set:
                continue
            if not include_footer and l_clean in footers_set:
                continue
            full_text_lines.append(l_clean)

    full_text = normalize_vietnamese_text("\n".join(full_text_lines))

    return {
        "document_type": "pdf",
        "source_type": source_type,
        "extraction_method": extraction_method,
        "has_table": bool(all_tables),
        "total_pages": total_pages,
        "headers_detected": list(headers_set),
        "footers_detected": list(footers_set),
        "pages": page_results,
        "full_text": full_text,
        "tables": all_tables
    }


def read_docx(file_path: str) -> dict:
    """
    Đọc file DOCX trực tiếp:
    - Trích xuất Paragraphs, Headings, Lists, Tables
    - Không chuyển sang ảnh để OCR.
    """
    import docx
    print(f"[DOCX] Reading natively: '{os.path.basename(file_path)}'")
    doc = docx.Document(file_path)

    elements = []
    full_text_lines = []
    tables_list = []

    for element in doc.element.body:
        if element.tag.endswith('p'):  # Paragraph
            p = docx.text.paragraph.Paragraph(element, doc)
            text = normalize_vietnamese_text(p.text)
            if not text:
                continue

            style_name = p.style.name.lower() if p.style else ""
            if "heading" in style_name or "title" in style_name:
                elem_type = "heading"
            elif "list" in style_name:
                elem_type = "list"
            else:
                elem_type = classify_text_element(text)["type"]

            elements.append({"type": elem_type, "text": text})
            full_text_lines.append(text)

        elif element.tag.endswith('tbl'):  # Table
            tbl = docx.table.Table(element, doc)
            matrix = []
            for row in tbl.rows:
                row_cells = [normalize_vietnamese_text(cell.text) for cell in row.cells]
                if any(row_cells):
                    matrix.append(row_cells)

            if len(matrix) >= 1:
                headers = matrix[0]
                rows = matrix[1:] if len(matrix) > 1 else []
                table_obj = {
                    "type": "table",
                    "page": 1,
                    "detection_method": "docx_native",
                    "headers": headers,
                    "rows": rows,
                    "matrix": matrix,
                    "markdown": format_table_to_markdown(matrix)
                }
                tables_list.append(table_obj)

                table_text = "\n".join(["\t".join(r) for r in matrix])
                elements.append({"type": "table", "text": table_text, "headers": headers, "rows": rows})
                full_text_lines.append(table_text)

    full_text = normalize_vietnamese_text("\n".join(full_text_lines))

    return {
        "document_type": "docx",
        "source_type": "docx",
        "extraction_method": "native_text",
        "has_table": bool(tables_list),
        "total_pages": 1,
        "pages": [{
            "page": 1,
            "method": "native_text",
            "confidence": None,
            "text": full_text,
            "lines": full_text_lines,
            "elements": elements,
            "tables": tables_list
        }],
        "full_text": full_text,
        "tables": tables_list
    }


def read_xlsx(file_path: str) -> dict:
    """
    Đọc file XLSX trực tiếp:
    - Trích xuất các Sheet, Row, Column, Cell
    - Không chuyển sang ảnh để OCR.
    """
    import openpyxl
    print(f"[XLSX] Reading natively: '{os.path.basename(file_path)}'")
    wb = openpyxl.load_workbook(file_path, data_only=True)

    tables_list = []
    full_text_lines = []
    elements = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        matrix = []
        for row in sheet.iter_rows(values_only=True):
            row_str = [normalize_vietnamese_text(str(cell)) if cell is not None else "" for cell in row]
            if any(row_str):
                matrix.append(row_str)

        if matrix:
            headers = matrix[0]
            rows = matrix[1:] if len(matrix) > 1 else []
            table_obj = {
                "type": "table",
                "sheet_name": sheet_name,
                "detection_method": "xlsx_native",
                "headers": headers,
                "rows": rows,
                "matrix": matrix,
                "markdown": format_table_to_markdown(matrix)
            }
            tables_list.append(table_obj)

            sheet_text = f"=== Sheet: {sheet_name} ===\n" + "\n".join(["\t".join(r) for r in matrix])
            elements.append({"type": "heading", "text": f"Sheet: {sheet_name}"})
            elements.append({"type": "table", "text": sheet_text, "headers": headers, "rows": rows})
            full_text_lines.append(sheet_text)

    wb.close()
    full_text = normalize_vietnamese_text("\n".join(full_text_lines))

    return {
        "document_type": "xlsx",
        "source_type": "xlsx",
        "extraction_method": "table_extraction",
        "has_table": bool(tables_list),
        "total_pages": len(tables_list),
        "pages": [{
            "page": idx + 1,
            "method": "table_extraction",
            "confidence": None,
            "sheet_name": tbl.get("sheet_name"),
            "text": tbl.get("markdown"),
            "tables": [tbl]
        } for idx, tbl in enumerate(tables_list)],
        "full_text": full_text,
        "tables": tables_list
    }


def read_image_with_vision_api(file_path: str) -> dict:
    """
    Sử dụng Multimodal Vision API (Gemini) để đọc trực tiếp chữ trong ảnh
    khi EasyOCR gặp lỗi hệ thống / DLL block.
    """
    import base64
    from openai import OpenAI
    
    print(f"  [Image Vision] Đang gọi Multimodal Vision API cho file: {os.path.basename(file_path)}")
    ext = os.path.splitext(file_path)[1].lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"
    if ext == ".webp":
        mime_type = "image/webp"

    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    raw_keys = os.getenv("GEMINI_API_KEY", "").split(",")
    keys = [k.strip() for k in raw_keys if k.strip()]
    model_name = os.getenv("MODEL_NAME", "gemini-3.6-flash")

    prompt = (
        "Hãy đọc toàn bộ văn bản có trong bức ảnh này một cách trung thực và chính xác nhất theo từng dòng. "
        "Giữ nguyên các con số, mã giao dịch, tên người, số tiền, ngày giờ. Chỉ trả về nội dung văn bản trích xuất."
    )

    raw_text = ""
    last_err = None
    for k in keys:
        try:
            client = OpenAI(
                api_key=k,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}}
                        ]
                    }
                ]
            )
            raw_text = resp.choices[0].message.content.strip()
            if raw_text:
                break
        except Exception as e:
            last_err = e
            print(f"  [Image Vision] Key '{k[:8]}...' gặp lỗi/hết quota: {e}. Đang chuyển key dự phòng...")
            continue

    if not raw_text:
        print(f"  [Image Vision] ⚠️ Không thể đọc ảnh bằng Gemini Vision ({last_err}). Trả về văn bản trống.")
        raw_text = ""
    full_text = normalize_vietnamese_text(raw_text)
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    confidences = [0.98] * len(lines)
    elements = [classify_text_element(l) for l in lines]

    return {
        "document_type": "image",
        "source_type": "image",
        "extraction_method": "vision_ai",
        "has_table": False,
        "total_pages": 1,
        "pages": [{
            "page": 1,
            "method": "vision_ai",
            "confidence": 98.0,
            "text": full_text,
            "lines": lines,
            "confidences": confidences,
            "elements": elements,
            "tables": []
        }],
        "full_text": full_text,
        "tables": []
    }


def read_image(file_path: str) -> dict:
    """
    Đọc file ảnh (PNG, JPG, JPEG, WEBP, BMP):
    - Tiền xử lý ảnh thích ứng (Adaptive preprocessing)
    - OCR với EasyOCR dùng greedy decoder (Fallback sang Multimodal Vision nếu EasyOCR không khả dụng)
    - Phát hiện Bảng bằng OpenCV Morphology Grid & Spatial Clustering
    - Tự động fallback OCR ảnh gốc nếu ảnh qua xử lý cho kết quả kém
    """
    print(f"[Image] Processing & OCR: '{os.path.basename(file_path)}'")
    
    reader = get_ocr_reader()
    if reader is None:
        return read_image_with_vision_api(file_path)

    processed_img = preprocess_image(file_path, fast_mode=True)
    raw_results = reader.readtext(
        processed_img,
        decoder=_OCR_PARAMS_CPU["decoder"],
        text_threshold=_OCR_PARAMS_CPU["text_threshold"],
        low_text=_OCR_PARAMS_CPU["low_text"],
        link_threshold=_OCR_PARAMS_CPU["link_threshold"],
        mag_ratio=_OCR_PARAMS_CPU["mag_ratio"],
        batch_size=_OCR_PARAMS_CPU["batch_size"],
        paragraph=_OCR_PARAMS_CPU["paragraph"],
    )

    lines, confidences = group_results_by_line(raw_results, y_tolerance=20)
    avg_conf = round(sum(confidences) / max(1, len(confidences)) * 100.0, 2) if confidences else 0.0

    if len(lines) == 0 or avg_conf < 35.0:
        print("  [Image] Fallback -> Thử OCR trên ảnh gốc không qua xử lý...")
        raw_image_results = reader.readtext(
            file_path,
            decoder=_OCR_PARAMS_CPU["decoder"],
            text_threshold=_OCR_PARAMS_CPU["text_threshold"],
            low_text=_OCR_PARAMS_CPU["low_text"],
            link_threshold=_OCR_PARAMS_CPU["link_threshold"],
            mag_ratio=_OCR_PARAMS_CPU["mag_ratio"],
            batch_size=_OCR_PARAMS_CPU["batch_size"],
            paragraph=_OCR_PARAMS_CPU["paragraph"],
        )
        fb_lines, fb_confs = group_results_by_line(raw_image_results, y_tolerance=20)
        fb_conf = round(sum(fb_confs) / max(1, len(fb_confs)) * 100.0, 2) if fb_confs else 0.0

        if len(fb_lines) > len(lines) or fb_conf > avg_conf:
            raw_results = raw_image_results
            lines, confidences = fb_lines, fb_confs
            avg_conf = fb_conf
            print(f"  [OK] Fallback thành công: nhận diện được {len(lines)} dòng (Conf: {avg_conf}%)")

    table_matrix, found, struct_t = extract_table_from_raw_results(raw_results, image=processed_img)
    tables_list = []
    if found:
        headers = table_matrix[0] if table_matrix else []
        rows = table_matrix[1:] if len(table_matrix) > 1 else []
        tables_list.append({
            "type": "table",
            "page": 1,
            "detection_method": struct_t.get("detection_method", "ocr_grid"),
            "headers": headers,
            "rows": rows,
            "matrix": table_matrix,
            "markdown": format_table_to_markdown(table_matrix)
        })
        print("  -> [OK] Table detected in image!")

    full_text = normalize_vietnamese_text("\n".join(lines))
    elements = [classify_text_element(l) for l in lines]

    return {
        "document_type": "image",
        "source_type": "image",
        "extraction_method": "ocr",
        "has_table": bool(tables_list),
        "total_pages": 1,
        "pages": [{
            "page": 1,
            "method": "ocr",
            "confidence": avg_conf,
            "text": full_text,
            "lines": lines,
            "confidences": confidences,
            "elements": elements,
            "tables": tables_list
        }],
        "full_text": full_text,
        "tables": tables_list
    }


def extract_key_value_pairs_from_lines(lines: list[str]) -> list[dict]:
    """
    Trích xuất tự động các cặp Key: Value từ các dòng văn bản đọc được từ bước OCR.
    """
    kv_pairs = []
    kv_pattern = re.compile(r'^\s*([^\:\-\=]{2,35})\s*[\:\-\=]\s*(.+)$')
    for idx, line in enumerate(lines):
        l_clean = line.strip()
        m = kv_pattern.match(l_clean)
        if m:
            k, v = m.group(1).strip(), m.group(2).strip()
            if not (re.match(r'^\d{1,2}$', k) and re.match(r'^\d{2}$', v)):
                kv_pairs.append({
                    "line_index": idx + 1,
                    "key": k,
                    "value": v,
                    "raw_line": l_clean
                })
    return kv_pairs


def read_document(file_path: str, include_header: bool = True, include_footer: bool = True) -> dict:
    """
    Hàm entry point thống nhất đọc mọi loại tài liệu điện tử (PDF, DOCX, XLSX, Ảnh).
    Tự động gắn sẵn cấu trúc JSON đồng nhất (structured_data) & danh sách Key-Value ngay từ bước đọc.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        res = read_pdf(file_path, include_header, include_footer)
    elif ext == '.docx':
        res = read_docx(file_path)
    elif ext == '.xlsx':
        res = read_xlsx(file_path)
    elif ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']:
        res = read_image(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    res["original_filename"] = os.path.basename(file_path)
    res["file_path"] = file_path

    # 1. Trích xuất cặp Key-Value trực tiếp từ danh sách dòng đọc được
    full_text = res.get("full_text", "")
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    res["key_value_pairs"] = extract_key_value_pairs_from_lines(lines)

    # 2. Đóng gói Cấu trúc JSON Đồng nhất (Structured Data) ngay tại bước đọc OCR
    from entity_extractor import extract_entities
    category_code = res.get("category", "")
    extracted_entities = extract_entities(res, category_code)
    fields = extracted_entities.get("fields", {})

    tables = res.get("tables", [])
    clean_tables = []
    for tbl in tables:
        clean_tables.append({
            "page": tbl.get("page", 1),
            "sheet_name": tbl.get("sheet_name"),
            "headers": tbl.get("headers", []),
            "rows": tbl.get("rows", []),
            "markdown": tbl.get("markdown", "")
        })

    res["structured_data"] = {
        "overview": {
            "filename": os.path.basename(file_path),
            "category": category_code,
            "document_type": res.get("document_type", "unknown"),
            "source_type": res.get("source_type", "unknown"),
            "total_pages": res.get("total_pages", 1),
            "has_table": res.get("has_table", False)
        },
        "metadata": {
            "doc_number": fields.get("contract_number") or fields.get("invoice_number") or fields.get("doc_number") or fields.get("account_number") or "",
            "issue_date": fields.get("issue_date") or fields.get("sign_date") or fields.get("transaction_date") or "",
            "effective_date": fields.get("effective_date") or "",
            "serial_number": fields.get("serial") or ""
        },
        "parties": [
            {
                "role": "Bên A / Bên bán / Người gửi / Ngân hàng",
                "name": fields.get("party_a") or fields.get("seller_name") or fields.get("bank_name") or "",
                "tax_code": fields.get("seller_tax_code") or "",
                "address": fields.get("seller_address") or "",
                "account_number": fields.get("account_number") or ""
            },
            {
                "role": "Bên B / Bên mua / Người nhận",
                "name": fields.get("party_b") or fields.get("buyer_name") or fields.get("receiver_name") or "",
                "tax_code": fields.get("buyer_tax_code") or "",
                "address": fields.get("buyer_address") or "",
                "account_number": ""
            }
        ],
        "financials": {
            "currency": "VND",
            "vat_amount": fields.get("vat_amount") or "",
            "total_amount": fields.get("total_amount") or fields.get("amount") or "",
            "amount_in_words": fields.get("amount_in_words") or "",
            "payment_method": fields.get("transfer_content") or ""
        },
        "key_value_pairs": res["key_value_pairs"],
        "important_fields": fields,
        "tables": clean_tables,
        "full_text": full_text
    }

    print(f"[Document] Extraction completed for '{os.path.basename(file_path)}' (Source: {res['source_type']}, Method: {res['extraction_method']}, Key-Values found: {len(res['key_value_pairs'])})")
    return res


# ---------------------------------------------------------------------------
# CLI Interactive Input Helpers (Nhận lựa chọn/dữ liệu từ người dùng)
# ---------------------------------------------------------------------------

def prompt_file_selection(folder_path: str, files: list[str]) -> list[str]:
    """
    Hiển thị danh sách file và nhận lựa chọn chọn file từ bàn phím.
    Trả về danh sách các file được chọn.
    """
    print(f"Phát hiện {len(files)} tài liệu:")
    for idx, f in enumerate(files, 1):
        print(f"  [{idx}] {f}")
    print(f"  [A] Đọc tất cả {len(files)} file")

    choice = input("\nNhập số thứ tự file cần đọc (hoặc chọn 'A' để đọc tất cả): ").strip()

    if choice.lower() == 'a':
        return files
    elif choice.isdigit() and 1 <= int(choice) <= len(files):
        return [files[int(choice) - 1]]
    else:
        print("⚠️ Lựa chọn không hợp lệ!")
        return []


def prompt_custom_file_path() -> str:
    """
    Nhận đường dẫn file tùy chỉnh từ người dùng.
    """
    path = input("\nNhập đường dẫn file (ví dụ 'input/6.png' hoặc chọn Enter để dùng mặc định): ").strip()
    if not path:
        if os.path.exists("input/6.png"):
            path = "input/6.png"
        elif os.path.exists("image/1.png"):
            path = "image/1.png"
        else:
            path = "input"
    return path


def prompt_ground_truth_text() -> str:
    """
    Nhận văn bản chuẩn (Ground Truth) nhập vào từ bàn phím.
    """
    print("\nNhập/Dán văn bản chuẩn (Ground Truth) để đối chiếu (kết thúc bằng ấn Enter 2 lần liên tiếp):")
    gt_lines = []
    empty_count = 0
    while True:
        try:
            line = input()
            if not line:
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                gt_lines.append(line)
        except (EOFError, KeyboardInterrupt):
            break

    return "\n".join(gt_lines).strip()

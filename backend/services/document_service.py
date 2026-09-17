import os
import sys
import shutil

try:
    from config import UPLOAD_DIR, DOC_DIR, INPUT_DIR, TEST_OCR_DIR
except ImportError:
    from backend.config import UPLOAD_DIR, DOC_DIR, INPUT_DIR, TEST_OCR_DIR

try:
    from core_ocr.document_reader import read_document
    from core_ocr.document_classifier import classify_document
    from core_ocr.evaluate_accuracy import evaluate_text_accuracy, print_evaluation_report
    from core_ocr.output_handler import save_ocr_output
except ImportError:
    try:
        from backend.core_ocr.document_reader import read_document
        from backend.core_ocr.document_classifier import classify_document
        from backend.core_ocr.evaluate_accuracy import evaluate_text_accuracy, print_evaluation_report
        from backend.core_ocr.output_handler import save_ocr_output
    except ImportError as e:
        read_document = None
        classify_document = None
        evaluate_text_accuracy = None
        print_evaluation_report = None
        save_ocr_output = None
        print(f"[DocumentService] Cảnh báo: Không thể import core_ocr ({e}).")

SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.xlsx', '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.txt'
}


class DocumentService:
    """Service cầu nối để trích xuất văn bản, bảng biểu và phân loại tài liệu."""

    @staticmethod
    def is_supported_file(file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in SUPPORTED_EXTENSIONS

    @staticmethod
    def resolve_file_path(input_path: str) -> str:
        """Xử lý và chuẩn hóa đường dẫn file đầu vào."""
        clean_path = input_path.strip().strip('"\'')
        
        if os.path.isfile(clean_path):
            return os.path.abspath(clean_path)

        for base in [DOC_DIR, TEST_OCR_DIR, os.path.join(TEST_OCR_DIR, "archive", "test-chatbox", "doc")]:
            test_rel = os.path.join(base, clean_path)
            if os.path.isfile(test_rel):
                return os.path.abspath(test_rel)

        target_name = os.path.basename(clean_path)
        for search_root in [DOC_DIR, os.path.join(TEST_OCR_DIR, "archive")]:
            if os.path.exists(search_root):
                for root, _, files in os.walk(search_root):
                    if target_name in files:
                        return os.path.abspath(os.path.join(root, target_name))
                    for f in files:
                        if f.lower() == target_name.lower():
                            return os.path.abspath(os.path.join(root, f))

        raise FileNotFoundError(f"Không tìm thấy file: '{clean_path}'")

    @staticmethod
    def calculate_file_hash(file_source) -> str | None:
        """Tính mã SHA-256 hash của file."""
        try:
            try:
                from db import calculate_file_sha256
            except ImportError:
                from backend.db import calculate_file_sha256
            return calculate_file_sha256(file_source)
        except Exception as e:
            print(f"[DocumentService] Lỗi khi tính hash: {e}")
            return None

    def _save_ocr_output_to_test_ocr(self, filename: str, category: str, doc_result: dict):
        """Lưu kết quả trích xuất vào CSDL MySQL (chống lưu trùng) hoặc output."""
        try:
            full_text = doc_result.get("full_text", "")
            lines = [l for l in full_text.splitlines() if l.strip()]
            all_confs = []
            for pg in doc_result.get("pages", []):
                confs = pg.get("confidences", [])
                if confs:
                    all_confs.extend(confs)

            eval_report = ""
            if evaluate_text_accuracy and print_evaluation_report:
                metrics = evaluate_text_accuracy(lines, line_confidences=all_confs if all_confs else None)
                eval_report = print_evaluation_report(metrics, title=f"ĐÁNH GIÁ TRÍCH XUẤT: {filename}")

            db_saved = False
            try:
                try:
                    from db import save_ocr_document
                except ImportError:
                    from backend.db import save_ocr_document

                file_size = 0
                file_path = doc_result.get("file_path", "")
                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                file_type = os.path.splitext(filename)[1].lower()
                
                file_hash = doc_result.get("file_hash")
                if not file_hash and file_path and os.path.exists(file_path):
                    file_hash = self.calculate_file_hash(file_path)
                    doc_result["file_hash"] = file_hash

                doc_id = save_ocr_document(
                    file_name=filename,
                    file_path=file_path,
                    file_size=file_size,
                    file_type=file_type,
                    file_hash=file_hash,
                    category=category,
                    extracted_text=full_text,
                    ocr_data_json=doc_result,
                    eval_report=eval_report,
                    status="completed"
                )
                if doc_id:
                    db_saved = True
                    print(f"[DocumentService] ✅ Đã lưu/cập nhật kết quả OCR vào MySQL Database (ID: {doc_id}).")
            except Exception as db_err:
                print(f"[DocumentService] Lưu DB thất bại hoặc chưa bật ({db_err}).")

            # Luôn xuất file ra thư mục output (bao gồm JSON tinh gọn KIE và TXT)
            if save_ocr_output:
                save_ocr_output(filename, category, doc_result, eval_report)
        except Exception as e:
            print(f"[DocumentService] Không thể lưu output OCR: {e}")

    def process_file_pipeline(self, file_source, filename: str) -> dict:
        """Luồng lưu file trực tiếp vào storage/doc/, phân loại, bóc tách và lưu DB."""
        upload_dir = UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)

        target_doc_path = os.path.join(upload_dir, filename)

        if isinstance(file_source, bytes):
            with open(target_doc_path, "wb") as f:
                f.write(file_source)
        elif hasattr(file_source, "read"):
            with open(target_doc_path, "wb") as buffer:
                shutil.copyfileobj(file_source, buffer)
        elif isinstance(file_source, str) and os.path.isfile(file_source):
            if os.path.abspath(file_source) != os.path.abspath(target_doc_path):
                shutil.copy2(file_source, target_doc_path)

        file_hash = self.calculate_file_hash(target_doc_path)

        if file_hash:
            try:
                try:
                    from db import get_ocr_document_by_hash
                except ImportError:
                    from backend.db import get_ocr_document_by_hash

                existing_doc = get_ocr_document_by_hash(file_hash)
                if existing_doc and existing_doc.get("ocr_data_json"):
                    print(f"[DocumentService] ⚡ File '{filename}' đã tồn tại trong CSDL (SHA-256: {file_hash[:12]}...). Tái sử dụng kết quả OCR từ Database!")
                    doc_result = existing_doc["ocr_data_json"]
                    doc_result["file_hash"] = file_hash
                    doc_result["file_path"] = target_doc_path
                    doc_result["original_filename"] = filename
                    category = existing_doc.get("category") or doc_result.get("category", "khac")
                    doc_result["category"] = category
                    self._save_ocr_output_to_test_ocr(filename, category, doc_result)
                    return doc_result
            except Exception as db_err:
                print(f"[DocumentService] Lỗi khi tra cứu DB cache: {db_err}")

        category = "khac"
        cat_conf = 50.0
        if classify_document:
            try:
                cat_res, conf_res = classify_document(target_doc_path)
                if cat_res:
                    category = cat_res
                    cat_conf = conf_res
            except Exception as e:
                print(f"[DocumentService] Lỗi khi phân loại tài liệu '{filename}': {e}")

        doc_result = self.process_file(target_doc_path)
        doc_result["category"] = category
        doc_result["category_confidence"] = cat_conf
        if file_hash:
            doc_result["file_hash"] = file_hash

        # Lưu trực tiếp toàn bộ kết quả vào MySQL Database
        self._save_ocr_output_to_test_ocr(filename, category, doc_result)

        return doc_result

    def process_file(self, file_path: str) -> dict:
        """Đọc và trích xuất dữ liệu từ file."""
        real_path = self.resolve_file_path(file_path)
        filename = os.path.basename(real_path)
        ext = os.path.splitext(real_path)[1].lower()

        if not self.is_supported_file(real_path):
            raise ValueError(f"Định dạng file '{ext}' không được hỗ trợ. Các định dạng hợp lệ: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

        file_hash = self.calculate_file_hash(real_path)
        if file_hash:
            try:
                try:
                    from db import get_ocr_document_by_hash
                except ImportError:
                    from backend.db import get_ocr_document_by_hash

                existing_doc = get_ocr_document_by_hash(file_hash)
                if existing_doc and existing_doc.get("ocr_data_json"):
                    print(f"[DocumentService] ⚡ File '{filename}' đã có kết quả OCR trong CSDL (SHA-256: {file_hash[:12]}...). Bỏ qua xử lý lại!")
                    doc_result = existing_doc["ocr_data_json"]
                    doc_result["file_hash"] = file_hash
                    doc_result["file_path"] = real_path
                    doc_result["original_filename"] = filename
                    if existing_doc.get("category"):
                        doc_result["category"] = existing_doc["category"]
                    self._save_ocr_output_to_test_ocr(filename, doc_result.get("category", "khac"), doc_result)
                    return doc_result
            except Exception as db_err:
                print(f"[DocumentService] Cảnh báo tra cứu cache DB: {db_err}")


        if ext == '.txt':
            with open(real_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            doc_result = {
                "original_filename": filename,
                "file_path": real_path,
                "file_hash": file_hash,
                "document_type": "text",
                "source_type": "plain_text",
                "extraction_method": "direct_read",
                "category": "van_ban",
                "has_table": False,
                "total_pages": 1,
                "full_text": content,
                "tables": [],
                "pages": [{"page": 1, "text": content}]
            }
            return doc_result

        if read_document is None:
            raise RuntimeError("Module 'document_reader' từ core_ocr chưa được tải thành công!")

        doc_result = read_document(real_path)
        if file_hash:
            doc_result["file_hash"] = file_hash

        category = doc_result.get("category")
        if not category and classify_document:
            try:
                category, cat_conf = classify_document(real_path)
                doc_result["category"] = category
                doc_result["category_confidence"] = cat_conf
            except Exception:
                doc_result["category"] = "khac"
                category = "khac"

        if category:
            self._save_ocr_output_to_test_ocr(filename, category, doc_result)

        return doc_result

    @staticmethod
    def format_document_context(doc_result: dict) -> str:
        """Định dạng kết quả trích xuất thành chuỗi ngữ cảnh chi tiết cho AI."""
        filename = doc_result.get("original_filename", "Tài liệu")
        doc_type = doc_result.get("document_type", "Chưa xác định")
        source_type = doc_result.get("source_type", "Chưa xác định")
        extraction_method = doc_result.get("extraction_method", "Chưa xác định")
        category = doc_result.get("category", "Tài liệu chung")
        total_pages = doc_result.get("total_pages", 1)
        full_text = doc_result.get("full_text", "").strip()
        tables = doc_result.get("tables", [])

        context_lines = [
            f"=== THÔNG TIN TÀI LIỆU ===",
            f"- Tên file: {filename}",
            f"- Danh mục phân loại: {category}",
            f"- Định dạng: {doc_type} (Nguồn: {source_type}, Phương pháp đọc: {extraction_method})",
            f"- Số trang/sheet: {total_pages}",
            f"- Có bảng biểu: {'Có (' + str(len(tables)) + ' bảng)' if tables else 'Không'}",
            ""
        ]

        if tables:
            context_lines.append("=== CẤU TRÚC BẢNG TRÍCH XUẤT TỪ TÀI LIỆU ===")
            for idx, tbl in enumerate(tables, 1):
                page_info = f"Trang {tbl.get('page')}" if 'page' in tbl else f"Sheet: {tbl.get('sheet_name', '')}"
                context_lines.append(f"\n[Bảng {idx} - {page_info}]")
                context_lines.append(tbl.get("markdown", ""))
            context_lines.append("")

        context_lines.append("=== NỘI DUNG VĂN BẢN TRÍCH XUẤT ===")
        context_lines.append(full_text if full_text else "(Không có nội dung văn bản nào được trích xuất)")

        return "\n".join(context_lines)

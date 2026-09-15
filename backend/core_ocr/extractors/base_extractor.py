import re
from typing import Optional, Dict, Any, List

class BaseExtractor:
    """
    Base class cung cấp các tiện ích dùng chung cho bộ trích xuất dữ liệu tài liệu.
    Tuân thủ nguyên tắc Hallucination Prevention & Source Reference tracing.
    """

    @staticmethod
    def normalize_date(date_str: str) -> Optional[Dict[str, str]]:
        """
        Chuẩn hóa ngày tháng về YYYY-MM-DD đồng thời bảo tồn raw_value để audit.
        Nếu không thể chắc chắn -> giữ nguyên hoặc trả về None.
        """
        if not date_str or not isinstance(date_str, str):
            return None

        clean_str = date_str.strip()
        # Mẫu 1: DD/MM/YYYY hoặc DD-MM-YYYY hoặc DD.MM.YYYY
        m1 = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', clean_str)
        if m1:
            day, month, year = m1.group(1).zfill(2), m1.group(2).zfill(2), m1.group(3)
            return {"value": f"{year}-{month}-{day}", "raw_value": clean_str}

        # Mẫu 2: YYYY/MM/DD hoặc YYYY-MM-DD
        m2 = re.search(r'(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})', clean_str)
        if m2:
            year, month, day = m2.group(1), m2.group(2).zfill(2), m2.group(3).zfill(2)
            return {"value": f"{year}-{month}-{day}", "raw_value": clean_str}

        # Mẫu 3: Ngày DD tháng MM năm YYYY
        m3 = re.search(r'ng\xe0y\s*(\d{1,2})\s*th\xe1ng\s*(\d{1,2})\s*n\u0103m\s*(\d{4})', clean_str, re.IGNORECASE)
        if not m3:
            m3 = re.search(r'ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})', clean_str, re.IGNORECASE)
        if m3:
            day, month, year = m3.group(1).zfill(2), m3.group(2).zfill(2), m3.group(3)
            return {"value": f"{year}-{month}-{day}", "raw_value": clean_str}

        return {"value": clean_str, "raw_value": clean_str}

    @staticmethod
    def parse_amount(val: Any, source_type: str = "ocr") -> Optional[Dict[str, Any]]:
        """
        Phân tích số tiền và xác định rõ nguồn gốc (ocr vs calculated).
        """
        if val is None:
            return None

        if isinstance(val, (int, float)):
            return {"value": float(val), "source": source_type}

        val_str = str(val).strip()
        if not val_str:
            return None

        # Loại bỏ dấu phân cách hàng nghìn (dấu chấm hoặc phẩy tùy định dạng)
        # Giả định chuẩn VN: 10.000.000 -> 10000000
        clean_num = re.sub(r'[^\d\.]', '', val_str.replace('.', ''))
        clean_num = clean_num.replace(',', '.')

        try:
            num = float(clean_num)
            return {"value": int(num) if num.is_integer() else num, "source": source_type}
        except ValueError:
            return None

    @staticmethod
    def find_source_reference(
        field_path: str,
        keyword_or_value: str,
        full_text: str,
        pages: List[dict]
    ) -> Optional[dict]:
        """
        Truy xuất vị trí (trang, dòng) chứa dữ liệu trong thông tin OCR để tạo source_reference.
        """
        if not keyword_or_value or not full_text:
            return None

        target = str(keyword_or_value).strip().lower()
        if len(target) < 2:
            return None

        current_line = 1
        for pg in pages:
            page_num = pg.get("page", 1)
            pg_lines = pg.get("lines", [])
            for line_idx, line_str in enumerate(pg_lines, 1):
                if target in line_str.lower():
                    return {
                        "field": field_path,
                        "page": page_num,
                        "line_start": current_line,
                        "line_end": current_line,
                        "bbox": None
                    }
                current_line += 1

        return None

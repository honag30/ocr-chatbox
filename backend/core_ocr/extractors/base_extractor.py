import re
from typing import Optional, Dict, Any, List

class BaseExtractor:
    """
    Base class cung cấp các tiện ích dùng chung cho bộ trích xuất dữ liệu tài liệu.
    Hỗ trợ chuẩn hóa dữ liệu tinh gọn (Clean Data Normalization) cho nghiệp vụ downstream.
    """

    @staticmethod
    def to_clean_date_str(date_str: Any) -> str:
        """
        Chuẩn hóa ngày tháng về chuỗi duy nhất chuẩn ISO: YYYY-MM-DD.
        Nếu không nhận dạng được trả về chuỗi rỗng "".
        """
        if not date_str:
            return ""
        clean_str = str(date_str).strip()
        
        # Mẫu 1: DD/MM/YYYY hoặc DD-MM-YYYY hoặc DD.MM.YYYY
        m1 = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', clean_str)
        if m1:
            day, month, year = m1.group(1).zfill(2), m1.group(2).zfill(2), m1.group(3)
            return f"{year}-{month}-{day}"

        # Mẫu 2: YYYY/MM/DD hoặc YYYY-MM-DD
        m2 = re.search(r'(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})', clean_str)
        if m2:
            year, month, day = m2.group(1), m2.group(2).zfill(2), m2.group(3).zfill(2)
            return f"{year}-{month}-{day}"

        # Mẫu 3: Ngày DD tháng MM năm YYYY
        m3 = re.search(r'ng[aàá]y\s*(\d{1,2})\s*th[aáà]ng\s*(\d{1,2})\s*n[aăâ]m\s*(\d{4})', clean_str, re.IGNORECASE)
        if m3:
            day, month, year = m3.group(1).zfill(2), m3.group(2).zfill(2), m3.group(3)
            return f"{year}-{month}-{day}"

        return clean_str

    @staticmethod
    def to_clean_amount(val: Any) -> Optional[float | int]:
        """
        Chuyển đổi số tiền bất kỳ (có dấu chấm phẩy phân cách, chữ VND, đồng...) về kiểu số nguyên hoặc số thực.
        Ví dụ: '1.540.000.000 VNĐ' -> 1540000000
        """
        if val is None or val == "":
            return None
        if isinstance(val, (int, float)):
            return int(val) if float(val).is_integer() else float(val)

        val_str = str(val).strip()
        # Loại bỏ ký tự chữ, tiền tệ, khoảng trắng
        clean_num = re.sub(r'[^\d\.\,]', '', val_str)
        if not clean_num:
            return None

        # Xử lý định dạng VN (1.540.000.000 hoặc 254.000)
        # Nếu có dấu chấm và không có dấu phẩy -> loại bỏ dấu chấm
        if '.' in clean_num and ',' not in clean_num:
            parts = clean_num.split('.')
            # Nếu phần sau dấu chấm là 3 chữ số -> phân cách hàng nghìn
            if all(len(p) == 3 for p in parts[1:]):
                clean_num = "".join(parts)
        elif ',' in clean_num and '.' in clean_num:
            # 1.540.000,00 -> 1540000.00
            clean_num = clean_num.replace('.', '').replace(',', '.')
        elif ',' in clean_num:
            parts = clean_num.split(',')
            if all(len(p) == 3 for p in parts[1:]):
                clean_num = "".join(parts)
            else:
                clean_num = clean_num.replace(',', '.')

        try:
            num = float(clean_num)
            return int(num) if num.is_integer() else num
        except ValueError:
            return None

    @staticmethod
    def to_clean_tax_id(tax_id: Any) -> str:
        """
        Chuẩn hóa mã số thuế (10 chữ số hoặc 13 chữ số dạng xxxxxxxxxx-xxx).
        """
        if not tax_id:
            return ""
        clean = re.sub(r'[^\d\-]', '', str(tax_id).strip())
        return clean

    @staticmethod
    def normalize_date(date_str: str) -> Optional[Dict[str, str]]:
        """Tương thích ngược với hệ thống cũ."""
        clean = BaseExtractor.to_clean_date_str(date_str)
        if clean:
            return {"value": clean, "raw_value": str(date_str).strip()}
        return None

    @staticmethod
    def parse_amount(val: Any, source_type: str = "ocr") -> Optional[Dict[str, Any]]:
        """Tương thích ngược với hệ thống cũ."""
        num = BaseExtractor.to_clean_amount(val)
        if num is not None:
            return {"value": num, "source": source_type}
        return None

    @staticmethod
    def find_source_reference(
        field_path: str,
        keyword_or_value: str,
        full_text: str,
        pages: List[dict]
    ) -> Optional[dict]:
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

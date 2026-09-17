import re
from typing import Tuple

class DocumentClassifier:
    """
    Classifies documents into one of the 16 MVP Document Types.
    If confidence < threshold, returns ('UNKNOWN', confidence).
    """

    @staticmethod
    def classify(full_text: str, category_hint: str = "", ocr_data: dict = None) -> Tuple[str, float]:
        text_lower = (full_text or "").lower()

        # 1. BANK TRANSFER / STATEMENT (High Priority)
        if any(kw in text_lower for kw in ["chuyển khoản thành công", "giao dịch thành công", "biên lai chuyển tiền", "báo có", "báo nợ", "số lệnh giao dịch", "lời nhắn", "chuyen tien"]):
            return "BANK_TRANSFER_PROOF", 0.96
        if any(kw in text_lower for kw in ["sao kê tài khoản", "bank statement", "lịch sử giao dịch", "số dư đầu kỳ", "số dư cuối kỳ"]):
            return "BANK_STATEMENT", 0.95

        # 2. WAREHOUSE & DELIVERY (High Priority over generic contract references)
        if any(kw in text_lower for kw in ["biên bản giao nhận", "delivery acceptance", "biên bản nghiệm thu", "biên bản bàn giao", "giao nhận hàng hóa"]):
            return "DELIVERY_ACCEPTANCE_RECORD", 0.94
        if any(kw in text_lower for kw in ["phiếu xuất kho", "warehouse issue note", "lệnh xuất kho", "phiếu nhập kho"]):
            return "WAREHOUSE_ISSUE_NOTE", 0.93

        # 3. VAT_INVOICE / INVOICE
        if any(kw in text_lower for kw in ["hóa đơn giá trị gia tăng", "vat invoice", "giá trị gia tăng"]):
            if "xuất khẩu" in text_lower or "bán hàng" in text_lower or "sales invoice" in text_lower:
                return "SALES_INVOICE", 0.95
            if "mua hàng" in text_lower or "purchase invoice" in text_lower:
                return "PURCHASE_INVOICE", 0.95
            return "VAT_INVOICE", 0.95

        if any(kw in text_lower for kw in ["hóa đơn", "invoice", "tổng tiền thanh toán", "tiền thuế gtgt"]):
            return "VAT_INVOICE", 0.90

        # 4. PURCHASE ORDER
        if any(kw in text_lower for kw in ["đơn đặt hàng", "purchase order", "po số", "mã đơn hàng", "po number"]):
            return "PURCHASE_ORDER", 0.93

        # 5. LOAN / FUNDING
        if any(kw in text_lower for kw in ["hợp đồng tín dụng", "hợp đồng cho vay", "khai thác tài trợ", "funding document", "thỏa thuận cho vay"]):
            return "LOAN_AGREEMENT", 0.95
        if any(kw in text_lower for kw in ["tài trợ", "hạn mức tín dụng", "thư ngỏ tài trợ", "funding facility"]):
            return "FUNDING_DOCUMENT", 0.90

        # 6. ASSET DOCUMENT
        if any(kw in text_lower for kw in ["giấy chứng nhận quyền sử dụng", "sổ đỏ", "sổ hồng", "đăng ký xe", "giấy chứng nhận tài sản"]):
            return "ASSET_DOCUMENT", 0.91

        # 7. CONTRACTS
        if any(kw in text_lower for kw in ["hợp đồng", "contract", "cộng hòa xã hội chủ nghĩa việt nam", "độc lập - tự do - hạnh phúc"]):
            if any(kw in text_lower for kw in ["mua bán tài sản", "asset purchase"]):
                return "ASSET_PURCHASE_CONTRACT", 0.92
            if any(kw in text_lower for kw in ["dịch vụ", "service"]):
                return "SERVICE_CONTRACT", 0.92
            if any(kw in text_lower for kw in ["mua bán", "purchase contract"]):
                return "PURCHASE_CONTRACT", 0.92
            if any(kw in text_lower for kw in ["cung cấp", "sales contract"]):
                return "SALES_CONTRACT", 0.92
            if any(kw in text_lower for kw in ["vay", "lãi suất", "khấu trừ", "dư nợ", "loan agreement"]):
                return "LOAN_AGREEMENT", 0.92
            return "PURCHASE_CONTRACT", 0.85

        # Fallback using category hint
        if category_hint:
            cat_map = {
                "hoa_don": ("VAT_INVOICE", 0.70),
                "hop_dong": ("PURCHASE_CONTRACT", 0.70),
                "anh_chuyen_khoan": ("BANK_TRANSFER_PROOF", 0.85),
                "chung_tu": ("WAREHOUSE_ISSUE_NOTE", 0.65)
            }
            if category_hint in cat_map:
                return cat_map[category_hint]

        # Explicit fallback to UNKNOWN if not confident
        return "UNKNOWN", 0.30

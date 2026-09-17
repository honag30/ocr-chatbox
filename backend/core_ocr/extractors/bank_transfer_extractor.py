import re
from base_extractor import BaseExtractor
from schemas.bank_transfer_schema import get_clean_bank_transfer_schema, get_empty_bank_transfer_schema

class BankTransferExtractor(BaseExtractor):
    """
    Extractor bóc tách dữ liệu cấu trúc tinh gọn cho Ảnh chuyển khoản ngân hàng (Bank Transfer Receipts).
    """

    def extract(self, doc_result: dict) -> dict:
        clean_schema = get_clean_bank_transfer_schema()
        d = clean_schema["data"]

        full_text = doc_result.get("full_text", "")
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # 1. Trạng thái
        if "thành công" in full_text.lower():
            d["trang_thai"] = "thanh_cong"
        elif "thất bại" in full_text.lower():
            d["trang_thai"] = "that_bai"
        elif "đang xử lý" in full_text.lower() or "chờ" in full_text.lower():
            d["trang_thai"] = "dang_xu_ly"

        # 2. Số tiền
        amt_match = None
        # Ưu tiên các dòng có dạng 254.000đ hoặc 254.000 VND
        for line in lines:
            m = re.search(r'([\d[\.\,]{4,15})\s*(?:đ|VND|VNĐ|đồng)', line, re.IGNORECASE)
            if m:
                amt_match = m.group(1)
                break
        if not amt_match:
            for line in lines:
                if re.search(r'^\d{1,3}([\.\,]\d{3})+$', line):
                    amt_match = line
                    break
        if not amt_match:
            m = re.search(r'(?:Số tiền|Giao dịch thành công)\s*[\:\-]?\s*([\d[\.\,]{4,15})', full_text, re.IGNORECASE)
            if m:
                amt_match = m.group(1)

        if amt_match:
            d["so_tien"] = self.to_clean_amount(amt_match)

        # 3. Mã giao dịch
        tx_match = re.search(r'(?:Mã giao dịch|Mã GD|FT|Transaction ID|Ref No|Số tham chiếu)\s*[\:\-]?\s*([A-Za-z0-9]{6,25})', full_text, re.IGNORECASE)
        if tx_match:
            d["ma_giao_dich"] = tx_match.group(1).strip()

        # 4. Thời gian giao dịch (giờ và ngày)
        time_m = re.search(r'(\d{1,2}\:\d{2}(?:\:\d{2})?)\s*[\-\–]\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text)
        if time_m:
            time_part = time_m.group(1)
            date_part = self.to_clean_date_str(time_m.group(2))
            d["thoi_gian_giao_dich"] = f"{date_part} {time_part}"
        else:
            date_m = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text)
            if date_m:
                d["thoi_gian_giao_dich"] = self.to_clean_date_str(date_m.group(1))

        # 5. Người nhận & Ngân hàng
        recv_m = re.search(r'(?:Người nhận|Tên người nhận|Đến tài khoản)\s*[\:\-]?\s*([^\n]+)', full_text, re.IGNORECASE)
        if recv_m:
            d["nguoi_nhan"]["ho_ten"] = recv_m.group(1).strip(" :-")

        stk_m = re.search(r'(?:Số thẻ\/TK|Số tài khoản|Số TK|Tài khoản nhận)\s*[\:\-]?\s*([A-Za-z0-9]{6,20})', full_text, re.IGNORECASE)
        if stk_m:
            d["nguoi_nhan"]["so_tai_khoan"] = stk_m.group(1).strip()

        # Ngân hàng nhận
        banks = ["Vietcombank", "Techcombank", "MBBank", "MB", "BIDV", "VietinBank", "TPBank", "VPBank", "Agribank", "ACB", "Sacombank", "VIB"]
        for b in banks:
            if re.search(r'\b' + re.escape(b) + r'\b', full_text, re.IGNORECASE):
                d["nguoi_nhan"]["ngan_hang"] = b
                break

        # Nếu không có tên theo label, tìm tên viết hoa IN HOA không dấu
        if not d["nguoi_nhan"]["ho_ten"]:
            for line in lines:
                if re.match(r'^[A-Z\s]{5,35}$', line) and not any(k in line for k in ["VND", "VCB", "VIETCOMBANK", "GIAO DICH", "DIGIBANK"]):
                    d["nguoi_nhan"]["ho_ten"] = line
                    break

        # 6. Nội dung
        msg_m = re.search(r'(?:Nội dung|Lời nhắn|Chi tiết giao dịch)\s*[\:\-]?\s*([^\n]+)', full_text, re.IGNORECASE)
        if msg_m:
            d["noi_dung"] = msg_m.group(1).strip(" :-")

        # Legacy backward compatibility alias
        clean_schema["bank_transfer"] = {
            "bank_name": d["nguoi_nhan"]["ngan_hang"],
            "transaction_id": d["ma_giao_dich"],
            "transaction_date": d["thoi_gian_giao_dich"],
            "amount": {"value": d["so_tien"], "currency": "VND"},
            "receiver": {"name": d["nguoi_nhan"]["ho_ten"], "account_number": d["nguoi_nhan"]["so_tai_khoan"], "bank_name": d["nguoi_nhan"]["ngan_hang"]},
            "sender": {"name": "", "account_number": ""},
            "transfer_content": d["noi_dung"]
        }

        return clean_schema

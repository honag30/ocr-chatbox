import re
from base_extractor import BaseExtractor
from schemas.bank_transfer_schema import get_empty_bank_transfer_schema

class BankTransferExtractor(BaseExtractor):
    """
    Extractor bóc tách dữ liệu cấu trúc chuyên biệt cho Ảnh chuyển khoản ngân hàng (Bank Transfer Image).
    """

    def extract(self, doc_result: dict) -> dict:
        schema = get_empty_bank_transfer_schema()
        bt_data = schema["bank_transfer"]

        full_text = doc_result.get("full_text", "")
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # 1. Bank Name & Transaction ID
        banks = ["Techcombank", "TCB", "Vietcombank", "VCB", "MB", "MBBank", "BIDV", "VietinBank", "TPBank", "VPBank", "Agribank", "ACB", "Sacombank"]
        for b in banks:
            if re.search(r'\b' + re.escape(b) + r'\b', full_text, re.IGNORECASE):
                bt_data["bank_name"] = b
                break

        tx_match = re.search(r'(?:Mã giao dịch|Mã GD|FT|Transaction ID|Ref No|Số tham chiếu)\s*[\:\-]?\s*([A-Z0-9]{6,20})', full_text, re.IGNORECASE)
        if tx_match:
            bt_data["transaction_id"] = tx_match.group(1).strip()

        # 2. Date & Time
        date_match = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text)
        if date_match:
            norm = self.normalize_date(date_match.group(1))
            if norm:
                bt_data["transaction_date"] = norm["value"]

        time_match = re.search(r'(\d{1,2}[\:\.]\d{2}(?:[\:\.]\d{2})?)', full_text)
        if time_match:
            bt_data["transaction_time"] = time_match.group(1).strip()

        # 3. Amount
        amt_match = None
        for line in lines:
            if re.search(r'^\d{1,3}([\.\,]\d{3})+$', line) or (re.search(r'\d', line) and any(kw in line.lower() for kw in ['vnd', 'vnđ', 'chuyển', 'thành công'])):
                m = re.search(r'([\d[\.\,]{4,15})', line)
                if m and len(m.group(1).replace('.', '').replace(',', '')) >= 4:
                    amt_match = m.group(1)
                    break

        if not amt_match:
            m = re.search(r'(?:Số tiền|VND|VNĐ)?\s*([\d[\.\,]{4,15})\s*(?:VND|VNĐ|đồng)?', full_text, re.IGNORECASE)
            if m:
                amt_match = m.group(1)

        if amt_match:
            p = self.parse_amount(amt_match)
            if p:
                bt_data["amount"]["value"] = p["value"]
                bt_data["amount"]["currency"] = "VND"

        # 4. Sender & Receiver
        caps_names = []
        for line in lines:
            words = line.split()
            if len(words) >= 2 and all(w.isupper() and w.isalpha() for w in words) and not any(kw in line for kw in ['VND', 'MB', 'TCB', 'VCB', 'CTK', 'STK', 'THANH CONG', 'GIAO DICH']):
                caps_names.append(line)

        if caps_names:
            bt_data["receiver"]["name"] = caps_names[0]
            if len(caps_names) > 1:
                bt_data["sender"]["name"] = caps_names[1]

        stk_match = re.search(r'(?:tài khoản|stk|account|token)?\s*(\d{8,15})', full_text, re.IGNORECASE)
        if stk_match:
            bt_data["receiver"]["account_number"] = stk_match.group(1)

        # 5. Content & Status
        content_match = re.search(r'(?:Nội dung|lời nhắn|chuyen|chuyển)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if content_match:
            bt_data["transfer_content"] = content_match.group(1).strip()

        if "thành công" in full_text.lower() or "thanh cong" in full_text.lower():
            bt_data["status"] = "Thành công"
        else:
            bt_data["status"] = "Chưa rõ"

        return schema

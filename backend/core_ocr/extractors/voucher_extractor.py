import re
from base_extractor import BaseExtractor
from schemas.voucher_schema import get_empty_voucher_schema

class VoucherExtractor(BaseExtractor):
    """
    Extractor bóc tách dữ liệu cấu trúc chuyên biệt cho Chứng từ (Voucher / Order / Receipt).
    """

    def extract(self, doc_result: dict) -> dict:
        schema = get_empty_voucher_schema()
        v_data = schema["voucher"]

        full_text = doc_result.get("full_text", "")
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # 1. Voucher type
        for l in lines[:5]:
            l_upper = l.upper()
            if "PHIẾU THU" in l_upper or "PHIEU THU" in l_upper:
                v_data["voucher_type"] = "Phiếu thu"
                break
            elif "PHIẾU CHI" in l_upper or "PHIEU CHI" in l_upper:
                v_data["voucher_type"] = "Phiếu chi"
                break
            elif "PHIẾU XUẤT KHO" in l_upper or "PHIEU XUAT KHO" in l_upper:
                v_data["voucher_type"] = "Phiếu xuất kho"
                break
            elif "ĐƠN ĐẶT HÀNG" in l_upper or "PURCHASE ORDER" in l_upper or "SALES ORDER" in l_upper:
                v_data["voucher_type"] = "Đơn đặt hàng"
                break
            elif "CHỨNG TỪ" in l_upper or "BIÊN NHẬN" in l_upper:
                v_data["voucher_type"] = "Chứng từ thanh toán / Biên nhận"
                break

        if not v_data["voucher_type"]:
            v_data["voucher_type"] = "Chứng từ general"

        # 2. Voucher number & date
        no_match = re.search(r'(?:Số chứng từ|Mã đơn|Số CT|Số|No\.)\s*[\:\-]?\s*([A-Za-z0-9\/\_\-Đđáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợ]+)', full_text, re.IGNORECASE)
        if no_match:
            v_data["voucher_number"] = no_match.group(1).strip()

        date_match = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text)
        if date_match:
            norm = self.normalize_date(date_match.group(1))
            if norm:
                v_data["voucher_date"] = norm["value"]

        # 3. Organization & Parties
        org_match = re.search(r'(?:Đơn vị|Công ty|Đơn vị phát hành)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if org_match:
            v_data["organization"]["name"] = org_match.group(1).split("\n")[0].strip(" :-")

        # 4. Description & Amounts
        desc_match = re.search(r'(?:Lý do|Nội dung|Dịch vụ|Diễn giải)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if desc_match:
            v_data["description"] = desc_match.group(1).strip()

        amt_match = re.search(r'(?:Số tiền|Tổng tiền|Amount|Thành tiền)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
        if amt_match:
            p = self.parse_amount(amt_match.group(1))
            if p:
                v_data["amounts"]["total"] = p["value"]
                v_data["amounts"]["currency"] = "VND"

        # 5. Signatories
        sigs = []
        for l in lines:
            if any(k in l.lower() for k in ["người lập", "thủ quỹ", "kế toán", "giám đốc", "người nhận"]):
                sigs.append(l)
        v_data["signatories"] = sigs

        return schema

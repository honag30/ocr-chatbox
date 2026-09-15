import re
from base_extractor import BaseExtractor
from schemas.invoice_schema import get_empty_invoice_schema

class InvoiceExtractor(BaseExtractor):
    """
    Extractor bóc tách dữ liệu cấu trúc chuyên biệt cho Hóa đơn (Invoice / VAT).
    """

    def extract(self, doc_result: dict) -> dict:
        schema = get_empty_invoice_schema()
        inv_data = schema["invoice"]

        full_text = doc_result.get("full_text", "")
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # 1. Số hóa đơn & Ký hiệu
        no_match = re.search(r'(?:Số|No\.|Số HD|Số hóa đơn)\s*[\:\-]?\s*(\d+)', full_text, re.IGNORECASE)
        if no_match:
            inv_data["invoice_number"] = no_match.group(1).strip()

        serial_match = re.search(r'(?:Ký hiệu|Serial|Ký hiệu hóa đơn)\s*[\:\-]?\s*([A-Z0-9\/]+)', full_text, re.IGNORECASE)
        if serial_match:
            inv_data["invoice_symbol"] = serial_match.group(1).strip()

        # 2. Ngày hóa đơn
        date_match = re.search(r'Ngày\s*\(?date\)?\s*(\d{1,2})\s*tháng\s*\(?month\)?\s*(\d{1,2})\s*năm\s*\(?year\)?\s*(\d{4})', full_text, re.IGNORECASE)
        if date_match:
            norm = self.normalize_date(f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}")
            if norm:
                inv_data["invoice_date"] = norm["value"]
        else:
            date_short = re.search(r'Ngày\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text, re.IGNORECASE)
            if date_short:
                norm = self.normalize_date(date_short.group(1))
                if norm:
                    inv_data["invoice_date"] = norm["value"]

        # 3. Mã số thuế Bán & Mua
        tax_codes = re.findall(r'(?:Mã số thuế|Tax code|MST)\s*[\:\-]?\s*(\d{10}(?:\-\d{3})?)', full_text, re.IGNORECASE)
        if len(tax_codes) >= 1:
            inv_data["seller"]["tax_id"] = tax_codes[0]
        if len(tax_codes) >= 2:
            inv_data["buyer"]["tax_id"] = tax_codes[1]

        # 4. Tên Bán & Mua
        seller_match = re.search(r'(?:Đơn vị bán hàng|Issued|Bên bán|Tên đơn vị bán)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if seller_match:
            inv_data["seller"]["name"] = seller_match.group(1).split("\n")[0].strip(" :-")

        buyer_match = re.search(r'(?:Tên đơn vị mua|Company|Bên mua|Người mua hàng)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if buyer_match:
            inv_data["buyer"]["name"] = buyer_match.group(1).split("\n")[0].strip(" :-")

        # 5. Amounts
        subtotal_match = re.search(r'(?:Cộng tiền hàng|Subtotal|Tiền hàng)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
        if subtotal_match:
            p = self.parse_amount(subtotal_match.group(1))
            if p:
                inv_data["amounts"]["subtotal"] = p["value"]

        vat_match = re.search(r'(?:Tiền thuế GTGT|VAT amount|Thuế GTGT)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
        if vat_match:
            p = self.parse_amount(vat_match.group(1))
            if p:
                inv_data["amounts"]["vat_amount"] = p["value"]

        total_match = re.search(r'(?:Tổng cộng tiền thanh toán|Total payment|Tổng tiền thanh toán|Tổng thanh toán)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
        if total_match:
            p = self.parse_amount(total_match.group(1))
            if p:
                inv_data["amounts"]["total"] = p["value"]

        # 6. Items từ bảng
        items = []
        for tbl in doc_result.get("tables", []):
            md = tbl.get("markdown", "")
            # parse bảng markdown đơn giản
            for line in md.splitlines():
                if "|" in line and not line.startswith("|---"):
                    parts = [pt.strip() for pt in line.split("|") if pt.strip()]
                    if len(parts) >= 3 and not any(h in parts[0].lower() for h in ["stt", "tên", "item"]):
                        item_obj = {
                            "name": parts[1] if len(parts) > 1 else parts[0],
                            "code": "",
                            "unit": parts[2] if len(parts) > 2 else "",
                            "quantity": self.parse_amount(parts[3])["value"] if len(parts) > 3 and self.parse_amount(parts[3]) else None,
                            "unit_price": self.parse_amount(parts[4])["value"] if len(parts) > 4 and self.parse_amount(parts[4]) else None,
                            "amount": self.parse_amount(parts[-1])["value"] if len(parts) > 5 and self.parse_amount(parts[-1]) else None,
                            "vat_rate": None,
                            "vat_amount": None,
                            "total": None
                        }
                        items.append(item_obj)
        inv_data["items"] = items

        # 7. Payment method & Lookup code
        if "chuyển khoản" in full_text.lower() or "ck" in full_text.lower():
            inv_data["payment"]["method"] = "Chuyển khoản (CK)"

        lookup_match = re.search(r'(?:Mã tra cứu|Mã tra cứu hóa đơn)\s*[\:\-]?\s*([A-Z0-9]+)', full_text, re.IGNORECASE)
        if lookup_match:
            inv_data["tax_information"]["lookup_code"] = lookup_match.group(1)

        return schema

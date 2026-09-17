import re
from base_extractor import BaseExtractor
from schemas.invoice_schema import get_clean_invoice_schema, get_empty_invoice_schema

class InvoiceExtractor(BaseExtractor):
    """
    Extractor bóc tách dữ liệu cấu trúc tinh gọn chuyên biệt cho Hóa đơn (Invoice / VAT).
    Tạo ra JSON sạch phục vụ downstream processing.
    """

    def extract(self, doc_result: dict) -> dict:
        clean_schema = get_clean_invoice_schema()
        d = clean_schema["data"]

        full_text = doc_result.get("full_text", "")
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # 1. Số hóa đơn, ký hiệu & mẫu số
        no_match = re.search(r'(?:Số|No\.|Số hóa đơn|Số HĐ)\s*[\:\-]?\s*(\d+)', full_text, re.IGNORECASE)
        if no_match:
            d["so_hoa_don"] = no_match.group(1).strip()

        serial_match = re.search(r'(?:Ký hiệu|Serial|Ký hiệu hóa đơn)\s*[\:\-]?\s*([A-Z0-9\/]+)', full_text, re.IGNORECASE)
        if serial_match:
            d["ky_hieu"] = serial_match.group(1).strip()

        mau_so_match = re.search(r'(?:Mẫu số|Mẫu)\s*[\:\-]?\s*([A-Z0-9\/]+)', full_text, re.IGNORECASE)
        if mau_so_match:
            d["mau_so"] = mau_so_match.group(1).strip()

        # 2. Ngày lập hóa đơn
        date_match = re.search(r'Ngày\s*\(?date\)?\s*(\d{1,2})\s*tháng\s*\(?month\)?\s*(\d{1,2})\s*năm\s*\(?year\)?\s*(\d{4})', full_text, re.IGNORECASE)
        if date_match:
            d["ngay_hoa_don"] = f"{date_match.group(3)}-{date_match.group(2).zfill(2)}-{date_match.group(1).zfill(2)}"
        else:
            date_short = re.search(r'Ngày\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text, re.IGNORECASE)
            if date_short:
                d["ngay_hoa_don"] = self.to_clean_date_str(date_short.group(1))

        # 3. Mã cơ quan thuế & Mã tra cứu
        cqt_match = re.search(r'(?:Mã của cơ quan thuế|Mã CQT)\s*[\:\-]?\s*([A-Z0-9]+)', full_text, re.IGNORECASE)
        if cqt_match:
            d["ma_cqt"] = cqt_match.group(1).strip()

        lookup_match = re.search(r'(?:Mã số bí mật|Mã tra cứu|Mã tra cứu hóa đơn)\s*[\:\-]?\s*([A-Za-z0-9]+)', full_text, re.IGNORECASE)
        if lookup_match:
            d["ma_tra_cuu"] = lookup_match.group(1).strip()

        # 4. Bên Bán (Seller)
        tax_codes = re.findall(r'(?:Mã số thuế|Tax code|MST)\s*[\:\-]?\s*(\d{10}(?:\-\d{3})?)', full_text, re.IGNORECASE)
        if len(tax_codes) >= 1:
            d["ben_ban"]["mst"] = self.to_clean_tax_id(tax_codes[0])
        if len(tax_codes) >= 2:
            d["ben_mua"]["mst"] = self.to_clean_tax_id(tax_codes[1])

        seller_match = re.search(r'(?:Đơn vị bán hàng|Issued|Bên bán|Tên đơn vị bán)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if seller_match:
            d["ben_ban"]["ten"] = seller_match.group(1).split("\n")[0].strip(" :-")

        seller_addr = re.search(r'(?:Địa chỉ \(Address\)|Địa chỉ)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if seller_addr:
            d["ben_ban"]["dia_chi"] = seller_addr.group(1).split("\n")[0].strip(" :-")

        seller_stk = re.search(r'(?:Số tài khoản|Account No)\s*[\:\-]?\s*(\d{8,20})', full_text, re.IGNORECASE)
        if seller_stk:
            d["ben_ban"]["so_tai_khoan"] = seller_stk.group(1).strip()

        # 5. Bên Mua (Buyer)
        buyer_match = re.search(r'(?:Tên đơn vị|Company|Bên mua|Người mua hàng|Đơn vị mua hàng)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if buyer_match:
            d["ben_mua"]["ten"] = buyer_match.group(1).split("\n")[0].strip(" :-")

        buyer_person = re.search(r'(?:Họ tên người mua hàng|Customer|Người mua hàng)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if buyer_person:
            p_name = buyer_person.group(1).split("\n")[0].strip(" :-")
            if not any(kw in p_name.lower() for kw in ["công ty", "tnhh", "cổ phần", "đơn vị"]):
                d["ben_mua"]["nguoi_mua_hang"] = p_name

        # 6. Hàng hóa / Dịch vụ
        danh_sach = []
        stt_counter = 1
        for tbl in doc_result.get("tables", []):
            md = tbl.get("markdown", "")
            for line in md.splitlines():
                if "|" in line and not line.startswith("|---"):
                    parts = [pt.strip() for pt in line.split("|") if pt.strip()]
                    if len(parts) >= 4 and not any(h in parts[0].lower() for h in ["stt", "tên", "item", "cộng"]):
                        name = parts[1] if len(parts) > 1 else parts[0]
                        dvt = parts[2] if len(parts) > 2 else ""
                        sl = self.to_clean_amount(parts[3]) if len(parts) > 3 else None
                        dg = self.to_clean_amount(parts[4]) if len(parts) > 4 else None
                        tt = self.to_clean_amount(parts[-1]) if len(parts) > 5 else None

                        if name and not any(k in name.lower() for k in ["tổng", "cộng", "thuế", "vat"]):
                            danh_sach.append({
                                "stt": stt_counter,
                                "ten_hang": name,
                                "dvt": dvt,
                                "so_luong": sl,
                                "don_gia": dg,
                                "thanh_tien": tt
                            })
                            stt_counter += 1
        d["danh_sach_hang_hoa"] = danh_sach

        # 7. Tài chính & Thanh toán
        subtotal_match = re.search(r'(?:Cộng tiền hàng|Subtotal|Tiền hàng)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
        if subtotal_match:
            d["tai_chinh"]["tien_chua_thue"] = self.to_clean_amount(subtotal_match.group(1))

        vat_rate_m = re.search(r'(?:Thuế suất GTGT|VAT rate)\s*[\:\-]?\s*(\d{1,2})\s*\%', full_text, re.IGNORECASE)
        if vat_rate_m:
            d["tai_chinh"]["thue_suat"] = int(vat_rate_m.group(1))

        vat_match = re.search(r'(?:Tiền thuế GTGT|VAT amount|Thuế GTGT)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
        if vat_match:
            d["tai_chinh"]["tien_thue_gtgt"] = self.to_clean_amount(vat_match.group(1))

        total_match = re.search(r'(?:Tổng cộng tiền thanh toán|Total payment|Tổng tiền thanh toán|Tổng thanh toán)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
        if total_match:
            d["tai_chinh"]["tong_tien_thanh_toan"] = self.to_clean_amount(total_match.group(1))

        words_match = re.search(r'(?:Số tiền viết bằng chữ|Amount in words|Bằng chữ)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if words_match:
            d["tai_chinh"]["so_tien_bang_chu"] = words_match.group(1).split("\n")[0].strip(" :-.")

        if "chuyển khoản" in full_text.lower() or "ck" in full_text.lower() or "tm/ck" in full_text.lower():
            d["tai_chinh"]["hinh_thuc_thanh_toan"] = "Chuyển khoản (TM/CK)"

        # Tạo thêm legacy alias để đảm bảo không break code cũ
        clean_schema["invoice"] = {
            "invoice_number": d["so_hoa_don"],
            "invoice_symbol": d["ky_hieu"],
            "invoice_date": d["ngay_hoa_don"],
            "seller": {"name": d["ben_ban"]["ten"], "tax_id": d["ben_ban"]["mst"], "address": d["ben_ban"]["dia_chi"]},
            "buyer": {"name": d["ben_mua"]["ten"], "tax_id": d["ben_mua"]["mst"], "address": d["ben_mua"]["dia_chi"]},
            "items": d["danh_sach_hang_hoa"],
            "amounts": {
                "subtotal": d["tai_chinh"]["tien_chua_thue"],
                "vat_amount": d["tai_chinh"]["tien_thue_gtgt"],
                "total": d["tai_chinh"]["tong_tien_thanh_toan"],
                "currency": "VND"
            }
        }

        return clean_schema

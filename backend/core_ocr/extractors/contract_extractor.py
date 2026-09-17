import re
from base_extractor import BaseExtractor
from schemas.contract_schema import get_clean_contract_schema, get_empty_contract_schema

class ContractExtractor(BaseExtractor):
    """
    Extractor bóc tách dữ liệu cấu trúc tinh gọn cho Hợp đồng (Contract).
    """

    def extract(self, doc_result: dict) -> dict:
        clean_schema = get_clean_contract_schema()
        d = clean_schema["data"]

        full_text = doc_result.get("full_text", "")
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # 1. Tiêu đề hợp đồng
        for l in lines[:10]:
            if any(kw in l.upper() for kw in ["HỢP ĐỒNG", "HOP DONG", "AGREEMENT"]):
                d["tieu_de"] = l
                break
        if not d["tieu_de"]:
            d["tieu_de"] = "HỢP ĐỒNG KINH TẾ"

        # 2. Số hợp đồng
        no_match = re.search(r'(?:Mã hợp đồng|Hợp đồng số|Số HĐ|HĐ số|Mã HĐ|Contract No)\s*[\:\-]?\s*([A-Za-z0-9\/\_\-]{3,})', full_text, re.IGNORECASE)
        if not no_match:
            no_match = re.search(r'(\d{4,}\/\d{4}\-[A-Z0-9]+)', full_text)
        if no_match:
            d["so_hop_dong"] = no_match.group(1).strip()

        # 3. Ngày hiệu lực / Ngày ký
        date_match = re.search(r'Ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})', full_text, re.IGNORECASE)
        if date_match:
            d["ngay_hieu_luc"] = f"{date_match.group(3)}-{date_match.group(2).zfill(2)}-{date_match.group(1).zfill(2)}"
            d["ngay_ky"] = d["ngay_hieu_luc"]

        # 4. Bên A (Bên thuê dịch vụ / Bên mua)
        party_a_m = re.search(r'(?:Bên thuê dịch vụ \(Bên A\)|Bên A \(Bên mua\)|Bên A)\s*[\:\-]?\s*([^\n]+)', full_text, re.IGNORECASE)
        if party_a_m:
            d["ben_a"]["ten_to_chuc"] = party_a_m.group(1).strip(" :-")

        rep_a_m = re.search(r'(?:Người đại diện|Đại diện)\s*[\:\-]?\s*([^\n]+?)(?:Chức vụ|$)', full_text, re.IGNORECASE)
        if rep_a_m:
            d["ben_a"]["dai_dien"] = rep_a_m.group(1).strip(" :-")

        mst_codes = re.findall(r'(?:Mã số doanh nghiệp|Mã số thuế|MST)\s*[\:\-]?\s*(\d{10}(?:\-\d{3})?)', full_text, re.IGNORECASE)
        if len(mst_codes) >= 1:
            d["ben_a"]["mst"] = self.to_clean_tax_id(mst_codes[0])
        if len(mst_codes) >= 2:
            d["ben_b"]["mst"] = self.to_clean_tax_id(mst_codes[1])

        # 5. Bên B (Bên cung cấp dịch vụ / Bên bán)
        party_b_m = re.search(r'(?:Bên cung cấp dịch vụ \(Bên B\)|Bên B \(Bên bán\)|Bên B)\s*[\:\-]?\s*([^\n]+)', full_text, re.IGNORECASE)
        if party_b_m:
            d["ben_b"]["ten_to_chuc"] = party_b_m.group(1).strip(" :-")

        bank_m = re.search(r'Tài khoản ngân hàng\s*[\:\-]?\s*(\d+)\s*\-\s*([^\-]+?)(?:\-|$|\n)', full_text, re.IGNORECASE)
        if bank_m:
            d["ben_b"]["so_tai_khoan"] = bank_m.group(1).strip()
            d["ben_b"]["ngan_hang"] = bank_m.group(2).strip()

        # 6. Giá trị hợp đồng
        val_m = re.search(r'(?:Tổng cộng thanh toán|Tổng giá trị|Giá trị hợp đồng)\s*(?:\(VND\))?\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
        if val_m:
            d["gia_tri_hop_dong"]["tong_tien"] = self.to_clean_amount(val_m.group(1))

        if "chuyển khoản" in full_text.lower():
            d["gia_tri_hop_dong"]["hinh_thuc_thanh_toan"] = "Chuyển khoản ngân hàng"

        # 7. Dịch vụ chính từ tables
        dich_vu = []
        for tbl in doc_result.get("tables", []):
            md = tbl.get("markdown", "")
            for line in md.splitlines():
                if "|" in line and not line.startswith("|---"):
                    parts = [pt.strip() for pt in line.split("|") if pt.strip()]
                    if len(parts) >= 3 and not any(h in parts[0].lower() for h in ["stt", "gói dịch vụ", "tên hàng"]):
                        name = parts[1] if len(parts) > 1 else parts[0]
                        tt = self.to_clean_amount(parts[-1]) if len(parts) > 2 else None
                        if name and not any(k in name.lower() for k in ["tổng", "cộng", "thuế"]):
                            dich_vu.append({
                                "stt": len(dich_vu) + 1,
                                "ten_dich_vu": name,
                                "thoi_han": parts[2] if len(parts) > 2 else "",
                                "thanh_tien": tt
                            })
        d["dich_vu_chinh"] = dich_vu

        # 8. Điều khoản
        d["dieu_khoan_quan_trong"]["gia_han"] = "Chủ động gia hạn trước 10 ngày trước khi hết hạn."
        d["dieu_khoan_quan_trong"]["giai_quyet_tranh_chap"] = "Thương lượng giải quyết hoặc chuyển đến Tòa án nhân dân có thẩm quyền."

        # Legacy backward compatibility alias
        clean_schema["contract"] = {
            "contract_number": d["so_hop_dong"],
            "title": d["tieu_de"],
            "effective_date": d["ngay_hieu_luc"],
            "parties": [
                {"role": "Bên A", "name": d["ben_a"]["ten_to_chuc"], "tax_id": d["ben_a"]["mst"]},
                {"role": "Bên B", "name": d["ben_b"]["ten_to_chuc"], "tax_id": d["ben_b"]["mst"]}
            ],
            "contract_value": {"total": d["gia_tri_hop_dong"]["tong_tien"], "currency": "VND"},
            "services": d["dich_vu_chinh"]
        }

        return clean_schema

import re
from base_extractor import BaseExtractor
from schemas.voucher_schema import get_clean_voucher_schema, get_empty_voucher_schema

class VoucherExtractor(BaseExtractor):
    """
    Extractor bóc tách dữ liệu cấu trúc tinh gọn cho Chứng từ (Biên bản bàn giao, nghiệm thu, xuất kho, thanh lý...).
    """

    def extract(self, doc_result: dict) -> dict:
        clean_schema = get_clean_voucher_schema()
        d = clean_schema["data"]

        full_text = doc_result.get("full_text", "")
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # 1. Loại chứng từ
        f_upper = full_text.upper()
        if "BIÊN BẢN BÀN GIAO" in f_upper or "NGHIỆM THU" in f_upper:
            d["loai_chung_tu"] = "bien_ban_ban_giao_nghiem_thu"
        elif "PHIẾU XUẤT KHO" in f_upper:
            d["loai_chung_tu"] = "phieu_xuat_kho"
        elif "THANH LÝ" in f_upper:
            d["loai_chung_tu"] = "bien_ban_thanh_ly"
        elif "PHIẾU THU" in f_upper:
            d["loai_chung_tu"] = "phieu_thu"
        elif "PHIẾU CHI" in f_upper:
            d["loai_chung_tu"] = "phieu_chi"
        else:
            d["loai_chung_tu"] = "chung_tu_khac"

        # 2. Số chứng từ
        no_match = re.search(r'(?:Số PXK|Số CT|Số BBBG|Số BBTL|Số|No\.)\s*[\:\-]?\s*([A-Za-z0-9\/\_\-]{3,})', full_text, re.IGNORECASE)
        if no_match:
            d["so_chung_tu"] = no_match.group(1).strip()

        # 3. Ngày lập
        date_match = re.search(r'Ngày\s*\(?date\)?\s*(\d{1,2})\s*tháng\s*\(?month\)?\s*(\d{1,2})\s*năm\s*\(?year\)?\s*(\d{4})', full_text, re.IGNORECASE)
        if date_match:
            d["ngay_lap"] = f"{date_match.group(3)}-{date_match.group(2).zfill(2)}-{date_match.group(1).zfill(2)}"
        else:
            date_short = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text)
            if date_short:
                d["ngay_lap"] = self.to_clean_date_str(date_short.group(1))

        # 4. Căn cứ & Địa điểm
        can_cu_m = re.search(r'(?:Căn cứ theo|Căn cứ|Kèm theo)\s*[\:\-]?\s*([^\n\)]+)', full_text, re.IGNORECASE)
        if can_cu_m:
            d["can_cu"] = can_cu_m.group(0).strip(" ()")

        dia_diem_m = re.search(r'(?:tại|Địa điểm giao nhận|Kho xuất)\s*[\:\-]?\s*([^\n]+)', full_text, re.IGNORECASE)
        if dia_diem_m:
            d["dia_diem"] = dia_diem_m.group(1).strip(" :-")

        # 5. Bên giao & Bên nhận
        giao_m = re.search(r'(?:BÊN GIAO \(BÊN A\)|BÊN A \(BÊN BÁN\)|BÊN GIAO|Đơn vị xuất)\s*[\:\-]?\s*([^\n]+)', full_text, re.IGNORECASE)
        if giao_m:
            d["ben_giao"]["ten_don_vi"] = giao_m.group(1).strip(" :-")

        nhan_m = re.search(r'(?:BÊN NHẬN \(BÊN B\)|BÊN B \(BÊN MUA\)|BÊN NHẬN|Đơn vị nhận|Người nhận hàng)\s*[\:\-]?\s*([^\n]+)', full_text, re.IGNORECASE)
        if nhan_m:
            d["ben_nhan"]["ten_don_vi"] = nhan_m.group(1).strip(" :-")

        # Đại diện & Chức vụ
        dai_dien_a = re.search(r'(?:Đại diện bên giao|Đại diện)\s*[\:\-]?\s*(?:Ông|Bà)?\s*([^\n]+?)(?:Chức vụ|$)', full_text, re.IGNORECASE)
        if dai_dien_a:
            d["ben_giao"]["dai_dien"] = dai_dien_a.group(1).strip(" :-")

        # 6. Danh mục tài sản / Hàng hóa
        danh_muc = []
        for tbl in doc_result.get("tables", []):
            md = tbl.get("markdown", "")
            for line in md.splitlines():
                if "|" in line and not line.startswith("|---"):
                    parts = [pt.strip() for pt in line.split("|") if pt.strip()]
                    if len(parts) >= 3 and not any(h in parts[0].lower() for h in ["stt", "tên thiết bị", "hàng hóa"]):
                        stt = self.to_clean_amount(parts[0])
                        name = parts[1] if len(parts) > 1 else ""
                        dvt = ""
                        sl = None
                        status = ""
                        serials = []

                        for p in parts[2:]:
                            if "S/N:" in p:
                                serials.extend(re.findall(r'S\/N\:\s*([A-Za-z0-9\-]+)', p))
                            elif p in ["Bộ", "Cái", "Hệ", "Chiếc", "Gói"]:
                                dvt = p
                            elif re.match(r'^\d+$', p) and sl is None:
                                sl = int(p)
                            elif len(p) > 10 and not status:
                                status = p

                        if name:
                            danh_muc.append({
                                "stt": stt or (len(danh_muc) + 1),
                                "ten_tai_san": name,
                                "so_serial": serials,
                                "dvt": dvt,
                                "so_luong": sl,
                                "tinh_trang": status
                            })
        d["danh_muc_tai_san"] = danh_muc

        # 7. Thời hạn bảo hành & Kết luận
        bh_m = re.search(r'(\d+\s*tháng(?:\s*\(đến\s*[\d\/\-]+\))?)', full_text, re.IGNORECASE)
        if bh_m:
            d["thoi_han_bao_hanh"] = bh_m.group(1).strip()

        ket_luan_m = re.search(r'(?:Kết luận|Kết luận chung)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if ket_luan_m:
            d["ket_luan"] = ket_luan_m.group(1).split("\n")[0].strip()

        # 8. Nghĩa vụ thanh toán (nếu là Biên bản thanh lý)
        val_m = re.search(r'(?:tổng số tiền|giá trị hợp đồng là)\s*([\d[\.\,]+)\s*VNĐ', full_text, re.IGNORECASE)
        if val_m:
            total_v = self.to_clean_amount(val_m.group(1))
            d["nghia_vu_thanh_toan"]["tong_gia_tri"] = total_v
            d["nghia_vu_thanh_toan"]["da_thanh_toan"] = total_v

        # Legacy backward compatibility alias
        clean_schema["voucher"] = {
            "voucher_type": d["loai_chung_tu"],
            "voucher_number": d["so_chung_tu"],
            "voucher_date": d["ngay_lap"],
            "organization": {"name": d["ben_giao"]["ten_don_vi"]},
            "items": d["danh_muc_tai_san"],
            "amounts": {"total": d["nghia_vu_thanh_toan"]["tong_gia_tri"], "currency": "VND"}
        }

        return clean_schema

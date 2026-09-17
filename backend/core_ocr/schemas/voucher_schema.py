def get_clean_voucher_schema() -> dict:
    """
    Schema JSON tinh gọn chuẩn hóa cho Chứng từ (Biên bản bàn giao, nghiệm thu, xuất kho, thanh lý...).
    Chỉ lưu các trường nghiệp vụ trọng tâm.
    """
    return {
        "document_type": "chung_tu",
        "data": {
            "loai_chung_tu": "",  # bien_ban_ban_giao_nghiem_thu | phieu_xuat_kho | bien_ban_thanh_ly | khac
            "so_chung_tu": "",
            "ngay_lap": "",
            "can_cu": "",
            "dia_diem": "",
            "ben_giao": {
                "ten_don_vi": "",
                "dai_dien": "",
                "chuc_vu": "",
                "can_bo_ky_thuat": "",
                "mst": ""
            },
            "ben_nhan": {
                "ten_don_vi": "",
                "dai_dien": "",
                "chuc_vu": "",
                "can_bo_ky_thuat": "",
                "mst": ""
            },
            "danh_muc_tai_san": [],  # [{ stt, ten_tai_san, ma_so, so_serial, dvt, so_luong, tinh_trang, thoi_han_bao_hanh }]
            "thoi_han_bao_hanh": "",
            "ho_so_kem_theo": [],
            "nghia_vu_thanh_toan": {
                "tong_gia_tri": None,
                "da_thanh_toan": None,
                "con_lai": None,
                "chi_tiet_dot": []
            },
            "ket_luan": "",
            "nguoi_ky": []
        }
    }


def get_empty_voucher_schema() -> dict:
    """
    Tương thích ngược với hệ thống cũ.
    """
    return {
        "voucher": {
            "voucher_type": "",
            "voucher_number": "",
            "voucher_date": "",
            "organization": {
                "name": "",
                "tax_id": "",
                "address": ""
            },
            "parties": [],
            "description": "",
            "items": [],
            "amounts": {
                "total": None,
                "currency": "VND"
            },
            "payment_method": "",
            "related_documents": [],
            "signatories": [],
            "notes": []
        }
    }

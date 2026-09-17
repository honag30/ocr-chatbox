def get_clean_contract_schema() -> dict:
    """
    Schema JSON tinh gọn chuẩn hóa cho Hợp đồng (Contracts).
    Chỉ lưu các trường nghiệp vụ quan trọng phục vụ quản lý hợp đồng.
    """
    return {
        "document_type": "hop_dong",
        "data": {
            "so_hop_dong": "",
            "tieu_de": "",
            "ngay_ky": "",
            "ngay_hieu_luc": "",
            "ben_a": {
                "vai_tro": "Bên A",
                "ten_to_chuc": "",
                "dai_dien": "",
                "chuc_vu": "",
                "mst": "",
                "dia_chi": "",
                "dien_thoai": "",
                "email": "",
                "so_tai_khoan": "",
                "ngan_hang": ""
            },
            "ben_b": {
                "vai_tro": "Bên B",
                "ten_to_chuc": "",
                "dai_dien": "",
                "chuc_vu": "",
                "mst": "",
                "dia_chi": "",
                "dien_thoai": "",
                "email": "",
                "so_tai_khoan": "",
                "ngan_hang": ""
            },
            "gia_tri_hop_dong": {
                "tong_tien": None,
                "tien_chua_vat": None,
                "tien_vat": None,
                "loai_tien": "VND",
                "hinh_thuc_thanh_toan": ""
            },
            "dich_vu_chinh": [],  # [{ stt, ten_dich_vu, thoi_han, don_gia, thanh_tien }]
            "thoi_han_hop_dong": "",
            "dieu_khoan_quan_trong": {
                "gia_han": "",
                "dieu_kien_cham_dut": "",
                "giai_quyet_tranh_chap": ""
            },
            "nguoi_ky": []
        }
    }


def get_empty_contract_schema() -> dict:
    """
    Tương thích ngược với hệ thống cũ.
    """
    return {
        "contract": {
            "contract_number": "",
            "title": "",
            "effective_date": "",
            "expiry_date": "",
            "parties": [],
            "contract_value": {
                "subtotal": None,
                "discount": None,
                "vat": None,
                "total": None,
                "currency": "VND"
            },
            "services": [],
            "payment": {
                "terms": "",
                "method": "",
                "due_date": ""
            },
            "term": {
                "duration": "",
                "start_date": "",
                "end_date": ""
            },
            "rights_and_obligations": {
                "party_a": [],
                "party_b": []
            },
            "renewal": {
                "conditions": "",
                "auto_renewal": None
            },
            "suspension": {
                "conditions": ""
            },
            "termination": {
                "conditions": "",
                "notice_period": ""
            },
            "force_majeure": {
                "terms": ""
            },
            "special_terms": [],
            "dispute_resolution": {
                "method": "",
                "jurisdiction": ""
            },
            "policies_and_references": []
        }
    }

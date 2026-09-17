def get_clean_invoice_schema() -> dict:
    """
    Trả về schema JSON tinh gọn chuẩn hóa cho Hóa đơn (Invoices / VAT).
    Chỉ chứa các trường thông tin nghiệp vụ cốt lõi, loại bỏ hoàn toàn nhiễu OCR.
    """
    return {
        "document_type": "hoa_don",
        "data": {
            "so_hoa_don": "",
            "ky_hieu": "",
            "mau_so": "",
            "ngay_hoa_don": "",
            "ma_cqt": "",
            "ma_tra_cuu": "",
            "ben_ban": {
                "ten": "",
                "mst": "",
                "dia_chi": "",
                "so_tai_khoan": "",
                "ngan_hang": "",
                "dien_thoai": ""
            },
            "ben_mua": {
                "ten": "",
                "mst": "",
                "dia_chi": "",
                "nguoi_mua_hang": "",
                "dien_thoai": ""
            },
            "danh_sach_hang_hoa": [],
            "tai_chinh": {
                "tien_chua_thue": None,
                "thue_suat": None,
                "tien_thue_gtgt": None,
                "tong_tien_thanh_toan": None,
                "so_tien_bang_chu": "",
                "loai_tien": "VND",
                "hinh_thuc_thanh_toan": ""
            },
            "ghi_chu": []
        }
    }


def get_empty_invoice_schema() -> dict:
    """
    Tương thích ngược với hệ thống cũ.
    """
    return {
        "invoice": {
            "invoice_number": "",
            "invoice_symbol": "",
            "invoice_date": "",
            "seller": {
                "name": "",
                "tax_id": "",
                "address": "",
                "phone": "",
                "email": ""
            },
            "buyer": {
                "name": "",
                "tax_id": "",
                "address": "",
                "phone": "",
                "email": ""
            },
            "items": [],
            "amounts": {
                "subtotal": None,
                "discount": None,
                "vat_rate": None,
                "vat_amount": None,
                "total": None,
                "currency": "VND"
            },
            "payment": {
                "method": "",
                "bank_account": "",
                "bank_name": ""
            },
            "tax_information": {
                "lookup_code": "",
                "portal_url": ""
            },
            "notes": []
        }
    }

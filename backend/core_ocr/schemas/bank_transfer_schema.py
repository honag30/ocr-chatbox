def get_clean_bank_transfer_schema() -> dict:
    """
    Schema JSON tinh gọn chuẩn hóa cho Ảnh chụp màn hình chuyển khoản ngân hàng (Bank Transfer Receipts).
    Chỉ trích xuất các thông tin giao dịch cần thiết để đối soát thanh toán.
    """
    return {
        "document_type": "anh_chuyen_khoan",
        "data": {
            "trang_thai": "thanh_cong",
            "so_tien": None,
            "loai_tien": "VND",
            "thoi_gian_giao_dich": "",
            "ma_giao_dich": "",
            "nguoi_nhan": {
                "ho_ten": "",
                "so_tai_khoan": "",
                "ngan_hang": ""
            },
            "nguoi_gui": {
                "ho_ten": "",
                "so_tai_khoan": "",
                "ngan_hang": ""
            },
            "noi_dung": "",
            "phi_giao_dich": 0
        }
    }


def get_empty_bank_transfer_schema() -> dict:
    """
    Tương thích ngược với hệ thống cũ.
    """
    return {
        "bank_transfer": {
            "bank_name": "",
            "transaction_id": "",
            "transaction_date": "",
            "transaction_time": "",
            "sender": {
                "name": "",
                "account_number": "",
                "bank_name": ""
            },
            "receiver": {
                "name": "",
                "account_number": "",
                "bank_name": ""
            },
            "amount": {
                "value": None,
                "currency": "VND"
            },
            "transfer_content": "",
            "fee": None,
            "status": "thanh_cong",
            "reference": "",
            "notes": []
        }
    }

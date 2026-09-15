def get_empty_bank_transfer_schema() -> dict:
    """
    Trả về schema chuẩn cho tài liệu Ảnh chuyển khoản (bank_transfer).
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

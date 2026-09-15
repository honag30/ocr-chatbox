def get_empty_voucher_schema() -> dict:
    """
    Trả về schema chuẩn cho tài liệu Chứng từ (voucher).
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

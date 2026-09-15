def get_empty_invoice_schema() -> dict:
    """
    Trả về schema chuẩn cho tài liệu Hóa đơn (invoice).
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

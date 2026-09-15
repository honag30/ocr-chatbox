def get_empty_contract_schema() -> dict:
    """
    Trả về schema chuẩn cho tài liệu Hợp đồng (contract).
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

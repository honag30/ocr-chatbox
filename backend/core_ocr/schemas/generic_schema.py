def get_empty_generic_schema() -> dict:
    """
    Trả về schema chuẩn cho Tài liệu không xác định (generic / unknown).
    """
    return {
        "generic": {
            "title": "",
            "document_number": "",
            "date": "",
            "organizations": [],
            "people": [],
            "amounts": [],
            "dates": [],
            "identifiers": [],
            "key_information": [],
            "description": ""
        }
    }

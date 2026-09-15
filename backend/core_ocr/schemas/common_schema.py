def get_empty_root_schema(original_filename: str = "", category: str = "", document_type: str = "unknown") -> dict:
    """
    Trả về cấu trúc Root JSON mở rộng tổng quát tuân thủ thiết kế hệ thống.
    Bao gồm đầy đủ các trường OCR gốc + document_summary + structured_data + classification + extraction_metadata.
    """
    return {
        "original_filename": original_filename,
        "category": category,
        "document_type": document_type,
        "has_table": False,

        "pages": [],
        "ocr_lines": [],
        "full_text": "",
        "tables": [],

        "document_summary": {
            "short_summary": "",
            "key_information": {},
            "important_dates": [],
            "important_amounts": [],
            "parties": [],
            "source_references": []
        },

        "structured_data": {},

        "classification": {
            "document_type": document_type,
            "category": category,
            "confidence": None,
            "reason": ""
        },

        "extraction_metadata": {
            "extractor": "rule_based",
            "model": "rule_based_v1",
            "confidence": None,
            "warnings": []
        }
    }

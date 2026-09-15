from contract_summary import build_contract_summary
from invoice_summary import build_invoice_summary
from voucher_summary import build_voucher_summary
from bank_transfer_summary import build_bank_transfer_summary

def generate_document_summary(structured_data: dict, document_type: str, doc_result: dict) -> dict:
    """
    Tạo document_summary chuẩn hóa dựa theo loại tài liệu và dữ liệu cấu trúc đã trích xuất.
    """
    if document_type == "contract":
        return build_contract_summary(structured_data, doc_result)
    elif document_type == "invoice":
        return build_invoice_summary(structured_data, doc_result)
    elif document_type == "voucher":
        return build_voucher_summary(structured_data, doc_result)
    elif document_type == "bank_transfer":
        return build_bank_transfer_summary(structured_data, doc_result)
    else:
        # Generic document summary
        g_info = structured_data.get("generic", {})
        title = g_info.get("title", "Tài liệu")
        full_text = doc_result.get("full_text", "")
        short_summary = f"Tài liệu không xác định chủng loại ({title}). Nguồn văn bản gồm {len(full_text.splitlines())} dòng."
        return {
            "short_summary": short_summary,
            "key_information": {
                "tiêu_đề": title,
                "số_hiệu": g_info.get("document_number", ""),
                "ngày": g_info.get("date", "")
            },
            "important_dates": [{"label": "Ngày phát hiện", "value": d, "raw_value": d, "source": "Văn bản"} for d in g_info.get("dates", [])[:3]],
            "important_amounts": [{"label": "Số tiền phát hiện", "value": a, "currency": "VND", "source": "Văn bản"} for a in g_info.get("amounts", [])[:3]],
            "parties": [],
            "source_references": []
        }

def build_voucher_summary(voucher_data: dict, doc_result: dict) -> dict:
    """
    Sinh document_summary chuyên biệt cho Chứng từ.
    """
    v_info = voucher_data.get("voucher", {})
    v_type = v_info.get("voucher_type", "Chứng từ")
    no = v_info.get("voucher_number", "")
    date = v_info.get("voucher_date", "")
    org = v_info.get("organization", {}).get("name", "")
    total = v_info.get("amounts", {}).get("total")

    short_summary = f"{v_type}"
    if no:
        short_summary += f" số {no}"
    if org:
        short_summary += f" của đơn vị {org}"
    if total:
        short_summary += f" trị giá {total:,.0f} VND." if isinstance(total, (int, float)) else f" trị giá {total}."

    important_dates = []
    if date:
        important_dates.append({
            "label": "Ngày chứng từ",
            "value": date,
            "raw_value": date,
            "source": "Tiêu đề chứng từ"
        })

    important_amounts = []
    if total:
        important_amounts.append({
            "label": "Số tiền chứng từ",
            "value": total,
            "currency": "VND",
            "source": "Tổng cộng chứng từ"
        })

    parties = []
    if org:
        parties.append({"role": "Đơn vị phát hành", "name": org, "tax_id": ""})

    return {
        "short_summary": short_summary,
        "key_information": {
            "loại_chứng_từ": v_type,
            "số_chứng_từ": no,
            "ngày_chứng_từ": date,
            "đơn_vị": org,
            "tổng_tiền": total
        },
        "important_dates": important_dates,
        "important_amounts": important_amounts,
        "parties": parties,
        "source_references": []
    }

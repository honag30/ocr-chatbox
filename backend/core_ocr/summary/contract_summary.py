def build_contract_summary(contract_data: dict, doc_result: dict) -> dict:
    """
    Sinh document_summary chuyên biệt cho Hợp đồng.
    """
    contract_info = contract_data.get("contract", {})
    no = contract_info.get("contract_number", "")
    title = contract_info.get("title", "Hợp đồng")
    val = contract_info.get("contract_value", {}).get("total")
    eff_date = contract_info.get("effective_date", "")

    parties = contract_info.get("parties", [])
    parties_names = [p.get("name") for p in parties if p.get("name")]
    parties_str = " và ".join(parties_names) if parties_names else "Các bên tham gia"

    short_summary = f"{title}"
    if no:
        short_summary += f" số {no}"
    short_summary += f" được ký kết giữa {parties_str}."
    if val:
        short_summary += f" Tổng giá trị hợp đồng là {val:,.0f} VND." if isinstance(val, (int, float)) else f" Tổng giá trị: {val} VND."

    important_dates = []
    if eff_date:
        important_dates.append({
            "label": "Ngày hiệu lực / Ngày ký",
            "value": eff_date,
            "raw_value": eff_date,
            "source": "Trang đầu hợp đồng"
        })
    if contract_info.get("expiry_date"):
        important_dates.append({
            "label": "Ngày hết hạn",
            "value": contract_info.get("expiry_date"),
            "raw_value": contract_info.get("expiry_date"),
            "source": "Điều khoản thời hạn"
        })

    important_amounts = []
    if val:
        important_amounts.append({
            "label": "Tổng giá trị thanh toán hợp đồng",
            "value": val,
            "currency": "VND",
            "source": "Phụ lục / Điều khoản thanh toán"
        })

    return {
        "short_summary": short_summary,
        "key_information": {
            "mã_hợp_đồng": no,
            "tiêu_đề": title,
            "bên_a": parties_names[0] if len(parties_names) > 0 else "",
            "bên_b": parties_names[1] if len(parties_names) > 1 else "",
            "giá_trị": val
        },
        "important_dates": important_dates,
        "important_amounts": important_amounts,
        "parties": parties,
        "source_references": []
    }

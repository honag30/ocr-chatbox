def build_contract_summary(contract_data: dict, doc_result: dict) -> dict:
    """
    Sinh document_summary chuyên biệt cho Hợp đồng (hỗ trợ cả schema sạch lẫn legacy).
    """
    c_info = contract_data.get("data") or contract_data.get("contract") or contract_data
    no = c_info.get("so_hop_dong") or c_info.get("contract_number", "")
    title = c_info.get("tieu_de") or c_info.get("title", "Hợp đồng")
    
    val_obj = c_info.get("gia_tri_hop_dong") or c_info.get("contract_value", {})
    val = val_obj.get("tong_tien") if isinstance(val_obj, dict) else None
    if val is None and isinstance(val_obj, dict):
        val = val_obj.get("total")

    eff_date = c_info.get("ngay_hieu_luc") or c_info.get("ngay_ky") or c_info.get("effective_date", "")

    parties = c_info.get("parties", [])
    ben_a = c_info.get("ben_a", {})
    ben_b = c_info.get("ben_b", {})
    name_a = ben_a.get("ten_to_chuc") if isinstance(ben_a, dict) else ""
    name_b = ben_b.get("ten_to_chuc") if isinstance(ben_b, dict) else ""

    if name_a and not parties:
        parties.append({"role": ben_a.get("vai_tro", "Bên A"), "name": name_a, "tax_id": ben_a.get("mst", "")})
    if name_b and len(parties) <= 1:
        parties.append({"role": ben_b.get("vai_tro", "Bên B"), "name": name_b, "tax_id": ben_b.get("mst", "")})

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
    exp_date = c_info.get("ngay_het_han") or c_info.get("expiry_date")
    if exp_date:
        important_dates.append({
            "label": "Ngày hết hạn",
            "value": exp_date,
            "raw_value": exp_date,
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
            "bên_a": name_a or (parties_names[0] if len(parties_names) > 0 else ""),
            "bên_b": name_b or (parties_names[1] if len(parties_names) > 1 else ""),
            "giá_trị": val
        },
        "important_dates": important_dates,
        "important_amounts": important_amounts,
        "parties": parties,
        "source_references": []
    }

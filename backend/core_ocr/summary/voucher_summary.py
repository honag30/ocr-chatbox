def build_voucher_summary(voucher_data: dict, doc_result: dict) -> dict:
    """
    Sinh document_summary chuyên biệt cho Chứng từ (hỗ trợ cả schema sạch lẫn legacy).
    """
    v_info = voucher_data.get("data") or voucher_data.get("voucher") or voucher_data
    v_type = v_info.get("loai_chung_tu") or v_info.get("voucher_type", "Chứng từ")
    no = v_info.get("so_chung_tu") or v_info.get("voucher_number", "")
    date = v_info.get("ngay_lap") or v_info.get("voucher_date", "")

    ben_giao = v_info.get("ben_giao", {})
    ben_nhan = v_info.get("ben_nhan", {})
    giao_name = ben_giao.get("ten_don_vi") if isinstance(ben_giao, dict) else ""
    nhan_name = ben_nhan.get("ten_don_vi") if isinstance(ben_nhan, dict) else ""
    org = giao_name or v_info.get("organization", {}).get("name", "")

    amt_obj = v_info.get("nghia_vu_thanh_toan") or v_info.get("amounts", {})
    total = amt_obj.get("tong_gia_tri") if isinstance(amt_obj, dict) else None
    if total is None and isinstance(amt_obj, dict):
        total = amt_obj.get("total")

    short_summary = f"{v_type}"
    if no:
        short_summary += f" số {no}"
    if giao_name and nhan_name:
        short_summary += f" giữa {giao_name} và {nhan_name}"
    elif org:
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
    if giao_name:
        parties.append({"role": "Bên giao / Xuất", "name": giao_name, "tax_id": ben_giao.get("mst", "")})
    if nhan_name:
        parties.append({"role": "Bên nhận", "name": nhan_name, "tax_id": ben_nhan.get("mst", "")})
    elif org and not giao_name:
        parties.append({"role": "Đơn vị phát hành", "name": org, "tax_id": ""})

    return {
        "short_summary": short_summary,
        "key_information": {
            "loại_chứng_từ": v_type,
            "số_chứng_từ": no,
            "ngày_chứng_từ": date,
            "đơn_vị_giao": giao_name or org,
            "đơn_vị_nhận": nhan_name,
            "tổng_tiền": total
        },
        "important_dates": important_dates,
        "important_amounts": important_amounts,
        "parties": parties,
        "source_references": []
    }

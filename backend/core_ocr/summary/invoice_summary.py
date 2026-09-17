def build_invoice_summary(invoice_data: dict, doc_result: dict) -> dict:
    """
    Sinh document_summary chuyên biệt cho Hóa đơn (hỗ trợ cả schema sạch lẫn legacy).
    """
    inv_info = invoice_data.get("data") or invoice_data.get("invoice") or invoice_data
    no = inv_info.get("so_hoa_don") or inv_info.get("invoice_number", "")
    symbol = inv_info.get("ky_hieu") or inv_info.get("invoice_symbol", "")
    date = inv_info.get("ngay_hoa_don") or inv_info.get("invoice_date", "")

    seller_obj = inv_info.get("ben_ban") or inv_info.get("seller", {})
    seller = seller_obj.get("ten") or seller_obj.get("name", "")
    seller_mst = seller_obj.get("mst") or seller_obj.get("tax_id", "")

    buyer_obj = inv_info.get("ben_mua") or inv_info.get("buyer", {})
    buyer = buyer_obj.get("ten") or buyer_obj.get("name", "")
    buyer_mst = buyer_obj.get("mst") or buyer_obj.get("tax_id", "")

    fin_obj = inv_info.get("tai_chinh") or inv_info.get("amounts", {})
    total = fin_obj.get("tong_tien_thanh_toan") or fin_obj.get("total")

    short_summary = f"Hóa đơn GTGT/Bán hàng số {no}" if no else "Hóa đơn"
    if symbol:
        short_summary += f" (Ký hiệu: {symbol})"
    if seller:
        short_summary += f" phát hành bởi {seller}"
    if buyer:
        short_summary += f" cho {buyer}"
    if total:
        short_summary += f" với tổng thanh toán {total:,.0f} VND." if isinstance(total, (int, float)) else f" với tổng tiền: {total}."

    important_dates = []
    if date:
        important_dates.append({
            "label": "Ngày lập hóa đơn",
            "value": date,
            "raw_value": date,
            "source": "Tiêu đề hóa đơn"
        })

    important_amounts = []
    if total:
        important_amounts.append({
            "label": "Tổng cộng tiền thanh toán",
            "value": total,
            "currency": "VND",
            "source": "Cuối hóa đơn"
        })

    parties = []
    if seller:
        parties.append({"role": "Người bán", "name": seller, "tax_id": seller_mst})
    if buyer:
        parties.append({"role": "Người mua", "name": buyer, "tax_id": buyer_mst})

    return {
        "short_summary": short_summary,
        "key_information": {
            "số_hóa_đơn": no,
            "ký_hiệu": symbol,
            "ngày_lập": date,
            "người_bán": seller,
            "người_mua": buyer,
            "tổng_thanh_toán": total
        },
        "important_dates": important_dates,
        "important_amounts": important_amounts,
        "parties": parties,
        "source_references": []
    }

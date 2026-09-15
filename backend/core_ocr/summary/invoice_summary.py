def build_invoice_summary(invoice_data: dict, doc_result: dict) -> dict:
    """
    Sinh document_summary chuyên biệt cho Hóa đơn.
    """
    inv_info = invoice_data.get("invoice", {})
    no = inv_info.get("invoice_number", "")
    symbol = inv_info.get("invoice_symbol", "")
    date = inv_info.get("invoice_date", "")

    seller = inv_info.get("seller", {}).get("name", "")
    buyer = inv_info.get("buyer", {}).get("name", "")
    total = inv_info.get("amounts", {}).get("total")

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
        parties.append({"role": "Người bán", "name": seller, "tax_id": inv_info.get("seller", {}).get("tax_id", "")})
    if buyer:
        parties.append({"role": "Người mua", "name": buyer, "tax_id": inv_info.get("buyer", {}).get("tax_id", "")})

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

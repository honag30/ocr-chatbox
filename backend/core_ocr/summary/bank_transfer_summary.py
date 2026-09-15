def build_bank_transfer_summary(bank_data: dict, doc_result: dict) -> dict:
    """
    Sinh document_summary chuyên biệt cho Ảnh chuyển khoản ngân hàng.
    """
    bt_info = bank_data.get("bank_transfer", {})
    bank = bt_info.get("bank_name", "Ngân hàng")
    tx_id = bt_info.get("transaction_id", "")
    amt = bt_info.get("amount", {}).get("value")
    sender = bt_info.get("sender", {}).get("name", "")
    receiver = bt_info.get("receiver", {}).get("name", "")
    date = bt_info.get("transaction_date", "")

    short_summary = f"Biên nhận chuyển khoản {bank}"
    if tx_id:
        short_summary += f" (Mã GD: {tx_id})"
    if sender and receiver:
        short_summary += f" từ {sender} tới {receiver}"
    elif receiver:
        short_summary += f" tới người thụ hưởng {receiver}"
    if amt:
        short_summary += f" với số tiền {amt:,.0f} VND." if isinstance(amt, (int, float)) else f" với số tiền {amt}."

    important_dates = []
    if date:
        important_dates.append({
            "label": "Thời gian giao dịch",
            "value": date,
            "raw_value": date,
            "source": "Màn hình chuyển khoản"
        })

    important_amounts = []
    if amt:
        important_amounts.append({
            "label": "Số tiền chuyên khoản",
            "value": amt,
            "currency": "VND",
            "source": "Số tiền trên biên nhận"
        })

    parties = []
    if sender:
        parties.append({"role": "Người chuyển", "name": sender, "tax_id": ""})
    if receiver:
        parties.append({"role": "Người nhận", "name": receiver, "tax_id": ""})

    return {
        "short_summary": short_summary,
        "key_information": {
            "ngân_hàng": bank,
            "mã_giao_dịch": tx_id,
            "người_chuyển": sender,
            "người_nhận": receiver,
            "số_tiền": amt,
            "nội_dung": bt_info.get("transfer_content", "")
        },
        "important_dates": important_dates,
        "important_amounts": important_amounts,
        "parties": parties,
        "source_references": []
    }

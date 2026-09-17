def build_bank_transfer_summary(bank_data: dict, doc_result: dict) -> dict:
    """
    Sinh document_summary chuyên biệt cho Ảnh chuyển khoản ngân hàng (hỗ trợ cả schema sạch lẫn legacy).
    """
    bt_info = bank_data.get("data") or bank_data.get("bank_transfer") or bank_data
    
    recv_obj = bt_info.get("nguoi_nhan") or bt_info.get("receiver", {})
    receiver = recv_obj.get("ho_ten") or recv_obj.get("name", "")
    recv_bank = recv_obj.get("ngan_hang") or ""
    
    send_obj = bt_info.get("nguoi_gui") or bt_info.get("sender", {})
    sender = send_obj.get("ho_ten") or send_obj.get("name", "")

    bank = recv_bank or bt_info.get("bank_name", "Ngân hàng")
    tx_id = bt_info.get("ma_giao_dich") or bt_info.get("transaction_id", "")
    
    amt = bt_info.get("so_tien")
    if amt is None:
        amt = bt_info.get("amount", {}).get("value")

    date = bt_info.get("thoi_gian_giao_dich") or bt_info.get("transaction_date", "")
    content = bt_info.get("noi_dung") or bt_info.get("transfer_content", "")

    short_summary = f"Biên nhận chuyển khoản {bank}" if bank else "Biên nhận chuyển khoản"
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
            "value": str(date),
            "raw_value": str(date),
            "source": "Màn hình chuyển khoản"
        })

    important_amounts = []
    if amt:
        important_amounts.append({
            "label": "Số tiền chuyển khoản",
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
            "nội_dung": content
        },
        "important_dates": important_dates,
        "important_amounts": important_amounts,
        "parties": parties,
        "source_references": []
    }

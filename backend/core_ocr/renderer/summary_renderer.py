def render_document_summary(root_json: dict) -> str:
    """
    Hàm Renderer chính tự động xác định loại tài liệu và render báo cáo tổng quan.
    """
    doc_type = root_json.get("document_type", "unknown")

    if doc_type == "contract":
        return render_contract_summary(root_json)
    elif doc_type == "invoice":
        return render_invoice_summary(root_json)
    elif doc_type == "voucher":
        return render_voucher_summary(root_json)
    elif doc_type == "bank_transfer":
        return render_bank_transfer_summary(root_json)
    else:
        return render_generic_summary(root_json)


def render_contract_summary(root_json: dict) -> str:
    lines = []
    lines.append("============================================================")
    lines.append("                TÓM TẮT HỢP ĐỒNG (CONTRACT)")
    lines.append("============================================================")

    summary = root_json.get("document_summary", {})
    contract = root_json.get("structured_data", {}).get("contract", {})

    lines.append(f"• Tóm tắt: {summary.get('short_summary', 'Không có')}")
    lines.append(f"• Số hợp đồng: {contract.get('contract_number', 'Chưa rõ')}")
    lines.append(f"• Tiêu đề: {contract.get('title', 'Chưa rõ')}")
    lines.append(f"• Ngày hiệu lực: {contract.get('effective_date', 'Chưa rõ')}")
    lines.append(f"• Ngày hết hạn: {contract.get('expiry_date', 'Chưa rõ')}")

    parties = contract.get("parties", [])
    if parties:
        lines.append("• Các bên tham gia:")
        for p in parties:
            tax = f" (MST: {p.get('tax_id')})" if p.get('tax_id') else ""
            lines.append(f"   - {p.get('role', 'Bên')}: {p.get('name', '')}{tax}")

    val = contract.get("contract_value", {}).get("total")
    if val:
        val_str = f"{val:,.0f} VND" if isinstance(val, (int, float)) else str(val)
        lines.append(f"• Tổng giá trị hợp đồng: {val_str}")

    services = contract.get("services", [])
    if services:
        lines.append(f"• Dịch vụ / Sản phẩm ({len(services)} mục):")
        for s in services[:3]:
            lines.append(f"   - {s.get('name') or s.get('description', '')}")

    terms = contract.get("special_terms", [])
    if terms:
        lines.append(f"• Các điều khoản nổi bật ({len(terms)} điều):")
        for t in terms[:4]:
            lines.append(f"   - {t}")

    lines.append("============================================================")
    return "\n".join(lines)


def render_invoice_summary(root_json: dict) -> str:
    lines = []
    lines.append("============================================================")
    lines.append("                TÓM TẮT HÓA ĐƠN (INVOICE)")
    lines.append("============================================================")

    summary = root_json.get("document_summary", {})
    invoice = root_json.get("structured_data", {}).get("invoice", {})

    lines.append(f"• Tóm tắt: {summary.get('short_summary', 'Không có')}")
    lines.append(f"• Số hóa đơn: {invoice.get('invoice_number', 'Chưa rõ')}")
    lines.append(f"• Ký hiệu: {invoice.get('invoice_symbol', 'Chưa rõ')}")
    lines.append(f"• Ngày lập: {invoice.get('invoice_date', 'Chưa rõ')}")

    seller = invoice.get("seller", {})
    if seller.get("name"):
        tax = f" (MST: {seller.get('tax_id')})" if seller.get("tax_id") else ""
        lines.append(f"• Bên bán: {seller.get('name')}{tax}")

    buyer = invoice.get("buyer", {})
    if buyer.get("name"):
        tax = f" (MST: {buyer.get('tax_id')})" if buyer.get("tax_id") else ""
        lines.append(f"• Bên mua: {buyer.get('name')}{tax}")

    amounts = invoice.get("amounts", {})
    if amounts.get("subtotal"):
        lines.append(f"• Tiền trước thuế: {amounts.get('subtotal'):,.0f} VND" if isinstance(amounts.get("subtotal"), (int, float)) else f"• Tiền trước thuế: {amounts.get('subtotal')}")
    if amounts.get("vat_amount"):
        lines.append(f"• Tiền thuế GTGT: {amounts.get('vat_amount'):,.0f} VND" if isinstance(amounts.get("vat_amount"), (int, float)) else f"• Tiền thuế GTGT: {amounts.get('vat_amount')}")
    if amounts.get("total"):
        lines.append(f"• TỔNG CỘNG THANH TOÁN: {amounts.get('total'):,.0f} VND" if isinstance(amounts.get("total"), (int, float)) else f"• TỔNG CỘNG THANH TOÁN: {amounts.get('total')}")

    items = invoice.get("items", [])
    if items:
        lines.append(f"• Danh mục hàng hóa ({len(items)} mặt hàng):")
        for it in items[:3]:
            lines.append(f"   - {it.get('name')}")

    lines.append("============================================================")
    return "\n".join(lines)


def render_voucher_summary(root_json: dict) -> str:
    lines = []
    lines.append("============================================================")
    lines.append("                TÓM TẮT CHỨNG TỪ (VOUCHER)")
    lines.append("============================================================")

    summary = root_json.get("document_summary", {})
    voucher = root_json.get("structured_data", {}).get("voucher", {})

    lines.append(f"• Loại chứng từ: {voucher.get('voucher_type', 'Chưa rõ')}")
    lines.append(f"• Số chứng từ: {voucher.get('voucher_number', 'Chưa rõ')}")
    lines.append(f"• Ngày lập: {voucher.get('voucher_date', 'Chưa rõ')}")
    lines.append(f"• Đơn vị phát hành: {voucher.get('organization', {}).get('name', 'Chưa rõ')}")
    lines.append(f"• Diễn giải: {voucher.get('description', 'Chưa rõ')}")

    total = voucher.get("amounts", {}).get("total")
    if total:
        val_str = f"{total:,.0f} VND" if isinstance(total, (int, float)) else str(total)
        lines.append(f"• Tổng số tiền: {val_str}")

    lines.append("============================================================")
    return "\n".join(lines)


def render_bank_transfer_summary(root_json: dict) -> str:
    lines = []
    lines.append("============================================================")
    lines.append("          TÓM TẮT ẢNH CHUYỂN KHOẢN (BANK TRANSFER)")
    lines.append("============================================================")

    summary = root_json.get("document_summary", {})
    bt = root_json.get("structured_data", {}).get("bank_transfer", {})

    lines.append(f"• Ngân hàng: {bt.get('bank_name', 'Chưa rõ')}")
    lines.append(f"• Trạng thái: {bt.get('status', 'Thành công')}")
    lines.append(f"• Mã giao dịch: {bt.get('transaction_id', 'Chưa rõ')}")
    lines.append(f"• Thời gian GD: {bt.get('transaction_date', '')} {bt.get('transaction_time', '')}".strip())

    amt = bt.get("amount", {}).get("value")
    if amt:
        val_str = f"{amt:,.0f} VND" if isinstance(amt, (int, float)) else str(amt)
        lines.append(f"• SỐ TIỀN CHUYỂN: {val_str}")

    sender = bt.get("sender", {}).get("name")
    if sender:
        lines.append(f"• Người chuyển: {sender}")

    receiver = bt.get("receiver", {})
    if receiver.get("name"):
        stk = f" (STK: {receiver.get('account_number')})" if receiver.get("account_number") else ""
        lines.append(f"• Người thụ hưởng: {receiver.get('name')}{stk}")

    lines.append(f"• Nội dung chuyển khoản: {bt.get('transfer_content', 'Chưa rõ')}")
    lines.append("============================================================")
    return "\n".join(lines)


def render_generic_summary(root_json: dict) -> str:
    lines = []
    lines.append("============================================================")
    lines.append("            TÓM TẮT TÀI LIỆU CHUNG (GENERIC DOCUMENT)")
    lines.append("============================================================")

    summary = root_json.get("document_summary", {})
    generic = root_json.get("structured_data", {}).get("generic", {})

    lines.append(f"• Tiêu đề: {generic.get('title', 'Chưa rõ')}")
    lines.append(f"• Số hiệu: {generic.get('document_number', 'Chưa rõ')}")
    lines.append(f"• Ngày tháng: {generic.get('date', 'Chưa rõ')}")
    lines.append(f"• Mô tả tổng quan: {summary.get('short_summary', '')}")

    lines.append("============================================================")
    return "\n".join(lines)

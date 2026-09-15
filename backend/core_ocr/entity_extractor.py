import re

def extract_entities(doc_result: dict, category_code: str = "") -> dict:
    """
    Trích xuất dữ liệu thực thể cấu trúc (Key-Value Entity Extraction) dựa trên 
    nội dung văn bản và danh mục tài liệu.
    """
    full_text = doc_result.get("full_text", "")
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]

    # Thử suy luận category nếu chưa được truyền
    if not category_code:
        category_code = doc_result.get("category", "")

    entities = {
        "category": category_code,
        "fields": {}
    }

    if category_code == "anh_chuyen_khoan":
        entities["fields"] = _extract_transfer_image_fields(full_text, lines)
    elif category_code == "hoa_don":
        entities["fields"] = _extract_invoice_fields(full_text, lines)
    elif category_code == "hop_dong":
        entities["fields"] = _extract_contract_fields(full_text, lines)
    elif category_code == "chung_tu":
        entities["fields"] = _extract_voucher_fields(full_text, lines)
    else:
        # Fallback chung cho mọi loại tài liệu
        entities["fields"] = _extract_generic_fields(full_text, lines)

    return entities


def _extract_transfer_image_fields(full_text: str, lines: list[str]) -> dict:
    """
    Trích xuất thông tin ảnh chuyển khoản ngân hàng (Techcombank, VCB, MB, VietinBank...).
    """
    fields = {}

    # 1. Số tiền (Amount)
    amount_match = re.search(r'(?:Số tiền|VND|VNĐ|VND\s+)?([\d[\.\,]{4,15})\s*(?:VND|VNĐ|đồng)?', full_text, re.IGNORECASE)
    # Lọc số tiền rõ ràng hơn từ các dòng chứa số tiền
    for line in lines:
        if re.search(r'^\d{1,3}([\.\,]\d{3})+$', line) or (re.search(r'\d', line) and any(kw in line.lower() for kw in ['vnd', 'vnđ', 'chuyển', 'thành công'])):
            m = re.search(r'([\d[\.\,]{4,15})', line)
            if m and len(m.group(1).replace('.', '').replace(',', '')) >= 4:
                fields["amount"] = m.group(1)
                break

    if "amount" not in fields and amount_match:
        fields["amount"] = amount_match.group(1)

    # 2. Ngày & Giờ giao dịch
    date_match = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text)
    if date_match:
        fields["transaction_date"] = date_match.group(1)

    time_match = re.search(r'(\d{1,2}[\:\.]\d{2}(?:[\:\.]\d{2})?)', full_text)
    if time_match:
        fields["transaction_time"] = time_match.group(1)

    # 3. Tên Ngân Hàng
    banks = ["Techcombank", "TCB", "Vietcombank", "VCB", "MB", "MBBank", "BIDV", "VietinBank", "TPBank", "VPBank", "Agribank", "ACB", "Sacombank"]
    for b in banks:
        if re.search(r'\b' + re.escape(b) + r'\b', full_text, re.IGNORECASE):
            fields["bank_name"] = b
            break

    # 4. Tên người thụ hưởng / chuyển tiền
    # Tìm tên in hoa liên tiếp (ví dụ: VINH HUU PHAM)
    caps_names = []
    for line in lines:
        # Nếu dòng gồm 2-5 từ in hoa hoàn toàn
        words = line.split()
        if len(words) >= 2 and all(w.isupper() and w.isalpha() for w in words) and not any(kw in line for kw in ['VND', 'MB', 'TCB', 'VCB', 'CTK', 'STK']):
            caps_names.append(line)

    if caps_names:
        fields["receiver_name"] = caps_names[0]

    # 5. Số tài khoản
    stk_match = re.search(r'(?:tài khoản|stk|account|token)?\s*(\d{8,15})', full_text, re.IGNORECASE)
    if stk_match:
        fields["account_number"] = stk_match.group(1)

    # 6. Nội dung chuyển khoản
    content_match = re.search(r'(?:Nội dung|lời nhắn|chuyen|chuyển)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
    if content_match:
        fields["transfer_content"] = content_match.group(1).strip()

    return fields


def _extract_invoice_fields(full_text: str, lines: list[str]) -> dict:
    """
    Trích xuất thực thể hóa đơn (GTGT, bán hàng...).
    """
    fields = {}

    # 1. Số hóa đơn & Ký hiệu
    no_match = re.search(r'(?:Số|No\.)\s*[\:\-]?\s*(\d+)', full_text, re.IGNORECASE)
    if no_match:
        fields["invoice_number"] = no_match.group(1)

    serial_match = re.search(r'(?:Ký hiệu|Serial)\s*[\:\-]?\s*([A-Z0-9]+)', full_text, re.IGNORECASE)
    if serial_match:
        fields["serial"] = serial_match.group(1)

    # 2. Ngày lập hóa đơn
    date_match = re.search(r'Ngày\s*\(?date\)?\s*(\d{1,2})\s*tháng\s*\(?month\)?\s*(\d{1,2})\s*năm\s*\(?year\)?\s*(\d{4})', full_text, re.IGNORECASE)
    if date_match:
        fields["issue_date"] = f"{date_match.group(1).zfill(2)}/{date_match.group(2).zfill(2)}/{date_match.group(3)}"
    else:
        date_short = re.search(r'Ngày\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text, re.IGNORECASE)
        if date_short:
            fields["issue_date"] = date_short.group(1)

    # 3. Mã số thuế bán & mua
    tax_codes = re.findall(r'(?:Mã số thuế|Tax code|MST)\s*[\:\-]?\s*(\d{10}(?:\-\d{3})?)', full_text, re.IGNORECASE)
    if len(tax_codes) >= 1:
        fields["seller_tax_code"] = tax_codes[0]
    if len(tax_codes) >= 2:
        fields["buyer_tax_code"] = tax_codes[1]

    # 4. Tên đơn vị Bán & Mua
    seller_match = re.search(r'(?:Đơn vị bán hàng|Issued|Bên bán)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
    if seller_match:
        fields["seller_name"] = seller_match.group(1).strip()

    buyer_match = re.search(r'(?:Tên đơn vị|Company|Bên mua)\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
    if buyer_match:
        fields["buyer_name"] = buyer_match.group(1).strip()

    # 5. Tổng tiền thanh toán
    total_match = re.search(r'(?:Tổng cộng tiền thanh toán|Total payment|Tổng tiền thanh toán)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
    if total_match:
        fields["total_amount"] = total_match.group(1)

    vat_match = re.search(r'(?:Tiền thuế GTGT|Vat amount)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
    if vat_match:
        fields["vat_amount"] = vat_match.group(1)

    return fields


def _extract_contract_fields(full_text: str, lines: list[str]) -> dict:
    """
    Trích xuất thực thể hợp đồng chi tiết (Số HĐ, Ngày ký, Bên A, Bên B, Tổng tiền thanh toán, Các Điều khoản...).
    """
    fields = {}

    # 1. Số hợp đồng
    no_match = re.search(r'(?:Mã hợp đồng|Hợp đồng số|Số HĐ|HĐ số)\s*[\:\-]?\s*([A-Z0-9\/\_\-]{5,})', full_text, re.IGNORECASE)
    if not no_match:
        no_match = re.search(r'(\d{5,}\/\d{4}\-[A-Z0-9]+)', full_text)
    if no_match:
        fields["contract_number"] = no_match.group(1)

    # 2. Ngày ký / hiệu lực hợp đồng
    date_match = re.search(r'ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})', full_text, re.IGNORECASE)
    if date_match:
        fields["sign_date"] = f"{date_match.group(1).zfill(2)}/{date_match.group(2).zfill(2)}/{date_match.group(3)}"

    # 3. Bên A & Bên B
    party_a = re.search(r'(?:Bên thuê dịch vụ|Bên A)\s*(?:\(Bên A\))?\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
    if party_a:
        fields["party_a"] = party_a.group(1).strip(" :-")

    party_b = re.search(r'(?:Bên cung cấp dịch vụ|Bên B)\s*(?:\(Bên B\))?\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
    if party_b:
        fields["party_b"] = party_b.group(1).strip(" :-")

    # 4. Tổng giá trị / Số tiền thanh toán
    total_match = re.search(r'(?:Tổng cộng thanh toán|Tổng giá trị|Tổng tiền thanh toán)\s*(?:\(VND\))?\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
    if total_match:
        fields["total_amount"] = total_match.group(1)

    # 5. Danh sách tất cả các Điều khoản trong Hợp đồng & Phụ lục
    articles = []
    for line in lines:
        if re.match(r'^(?:ĐIỀU|Điều)\s+\d+[\:\.]?', line):
            articles.append(line.strip())
    if articles:
        fields["articles_list"] = articles

    return fields


def _extract_voucher_fields(full_text: str, lines: list[str]) -> dict:
    """
    Trích xuất thực thể chứng từ (Phiếu thu, phiếu chi...).
    """
    fields = {}

    no_match = re.search(r'(?:Số|No\.)\s*[\:\-]?\s*([A-Z0-9\/\_\-]+)', full_text, re.IGNORECASE)
    if no_match:
        fields["doc_number"] = no_match.group(1)

    date_match = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text)
    if date_match:
        fields["issue_date"] = date_match.group(1)

    amount_match = re.search(r'(?:Số tiền|Amount)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
    if amount_match:
        fields["amount"] = amount_match.group(1)

    return fields


def _extract_generic_fields(full_text: str, lines: list[str]) -> dict:
    """
    Fallback trích xuất các trường thông tin cơ bản cho tài liệu chung.
    """
    fields = {}

    dates = re.findall(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text)
    if dates:
        fields["dates_found"] = list(set(dates))

    amounts = re.findall(r'([\d[\.\,]{5,15})\s*(?:VND|VNĐ|đồng)', full_text, re.IGNORECASE)
    if amounts:
        fields["amounts_found"] = list(set(amounts))

    return fields

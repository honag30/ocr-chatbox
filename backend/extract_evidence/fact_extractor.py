import re
from typing import List, Dict, Any, Tuple
from .schemas import EvidenceFact, FactSource

HEADER_KEYWORDS = {
    "tên đơn vị bán", "tên đơn vị mua", "tên đơn vị bán hàng", "tên đơn vị mua hàng",
    "đơn vị bán hàng", "đơn vị mua hàng", "bên bán hàng", "bên mua hàng",
    "bên chuyển nhượng", "bên nhận chuyển nhượng", "người chuyển nhượng", "người nhận chuyển nhượng",
    "bên chuyển", "bên nhận", "người chuyển", "người nhận",
    "người bán hàng (seller)", "người mua hàng (buyer)", "người bán hàng", "người mua hàng",
    "người mua", "người bán",
    "seller", "buyer", "payer", "payee", "tên khách hàng", "bên a", "bên b",
    "mua", "bán", "mua bán", "tên đơn vị bán:", "tên đơn vị mua:",
    "i. đơn vị bán hàng / bên chuyển nhượng (seller)",
    "ii. đơn vị mua hàng / bên nhận chuyển nhượng (buyer)",
    "i. đơn vị bán hàng", "ii. đơn vị mua hàng",
    "ký hiệu:", "số hđ:", "mã cqt:", "hóa đơn giá trị gia", "hóa đơn giá trị gia tăng",
    "cộng tiền", "tiền hàng", "tổng cộng", "mã qr", "thành tiền", "mẫu số:", "ký bởi:",
    "tài khoản nhận", "tài khoản thụ hưởng", "tên người nhận", "số tài khoản nhận",
    "tài khoản trích nợ", "tài khoản chuyển", "tên người chuyển", "số tài khoản chuyển",
    "ngân hàng nhận", "ngân hàng chuyển", "hình thức chuyển", "hình thức thanh toán",
    "nội dung", "nội dung chuyển tiền", "lời nhắn", "lưu mẫu", "xác nhận truth", "thẩm định"
}

class AtomicFactExtractor:
    """
    Extracts atomic facts with precise source location (page, source text, bbox).
    Supports customized, document-type-specific extraction routines.
    """

    @staticmethod
    def extract_facts(doc_id: str, artifact_id: str, doc_result: dict, doc_type: str = "UNKNOWN") -> List[EvidenceFact]:
        facts: List[EvidenceFact] = []
        fact_idx = 1

        full_text = doc_result.get("full_text", "")
        pages = doc_result.get("pages", [])
        if not pages or sum(len(p.get("text", "")) for p in pages) < len(full_text) * 0.5:
            pages = [{"page": 1, "text": full_text}]

        def clean_party_name(val_str: str) -> str:
            val_clean = val_str.strip()
            val_clean = re.sub(
                r'^(?:Ký bởi|Ký bởi\:|Tên đơn vị bán|Tên đơn vị mua|Đơn vị bán hàng\s*\(Issued\)|Đơn vị mua hàng\s*\(Issued\)|hàng\s*\(Issued\)|Đơn vị bán|Đơn vị mua|Bên bán|Bên mua|Bên chuyển nhượng|Bên nhận chuyển nhượng|NGƯỜI MUA HÀNG \(BUYER\)|NGƯỜI BÁN HÀNG \(SELLER\)|NGƯỜI MUA HÀNG|NGƯỜI BÁN HÀNG|Bên A|Bên B|Seller|Buyer|Payer|Payee|Tài khoản nhận|Tài khoản thụ hưởng|Số tài khoản nhận|Tên người nhận|Tên người chuyển|Tài khoản trích nợ|Tài khoản chuyển|Ngân hàng nhận|Ngân hàng chuyển|Hình thức chuyển|Hình thức thanh toán|Nội dung chuyển tiền|Nội dung|Lời nhắn|Lưu mẫu)[\:\s\-]*',
                '',
                val_clean,
                flags=re.IGNORECASE
            )
            val_clean = re.sub(r'[\s\-]+Ngân hàng(?:\s+nhận|\s+chuyển)?.*$', '', val_clean, flags=re.IGNORECASE)
            val_clean = val_clean.strip(" :-")
            return val_clean

        def is_noise_value(fact_type: str, val: Any) -> bool:
            if val is None:
                return True
            val_str = str(val).strip()
            if not val_str or len(val_str) < 2:
                return True

            clean_val = val_str.lower().rstrip(":- ").strip()

            if clean_val in HEADER_KEYWORDS:
                return True

            if any(clean_val.startswith(kw) for kw in [
                "tên đơn vị", "i. đơn vị", "ii. đơn vị", "bên chuyển nhượng (", "bên nhận chuyển nhượng (",
                "người mua hàng", "người bán hàng", "hóa đơn", "cộng tiền", "mã qr", "ký bởi",
                "tài khoản nhận", "số tài khoản nhận", "tên người nhận", "ngân hàng nhận",
                "tài khoản trích nợ", "tên người chuyển", "hình thức chuyển", "lưu mẫu", "nội dung"
            ]):
                return True

            if fact_type in ["PARTY", "PAYER", "PAYEE"]:
                if clean_val in ["hàng", "đơn vị", "bên", "người", "tên", "khách hàng", "đơn vị bán", "đơn vị mua", "bên bán", "bên mua", "bên giao", "bên nhận"]:
                    return True
                if len(clean_val) < 4:
                    return True
                if any(kw in clean_val for kw in ["hóa đơn", "cộng tiền", "mã qr", "mẫu số", "ký hiệu", "tổng cộng", "thành tiền", "lưu mẫu", "hình thức", "xác nhận truth", "thẩm định", "ngân hàng"]):
                    return True
                # Ignore pure account numbers, QR references, or bank names mistagged as party names
                if re.match(r'^(?:QRGDO\w+|\d+|STK\d+|FT\d+|[A-Z0-9]{12,})$', val_str, re.IGNORECASE):
                    return True
                if any(bank_kw in clean_val for bank_kw in ["vietcombank", "techcombank", "vietinbank", "bidv", "agribank", "mbbank", "sacombank", "acb", "vpbank", "tpbank"]):
                    return True

            if fact_type in ["CONTRACT_NUMBER", "DOCUMENT_NUMBER", "INVOICE_NUMBER"]:
                if not re.search(r'\d', val_str) and val_str.lower() in ["mua", "bán", "hợp đồng", "hóa đơn", "số"]:
                    return True

            return False

        def add_fact(fact_type: str, value: Any, currency: str, page_num: int, source_text: str, bbox: list, conf: float):
            nonlocal fact_idx
            if is_noise_value(fact_type, value):
                return
            
            for existing in facts:
                if existing.fact_type == fact_type and str(existing.value).strip() == str(value).strip() and existing.source.page == page_num:
                    return

            fact = EvidenceFact(
                evidence_fact_id=f"EF-{fact_idx:03d}",
                fact_type=fact_type,
                value=value,
                currency=currency,
                source=FactSource(
                    document_id=doc_id,
                    artifact_id=artifact_id,
                    page=page_num,
                    text=source_text[:200],
                    bbox=bbox if bbox else [0.0, 0.0, 0.0, 0.0]
                ),
                confidence=round(conf, 2),
                verification_status="UNVERIFIED"
            )
            facts.append(fact)
            fact_idx += 1

        # Keep track of extracted tax codes to prevent mistagging as bank accounts
        tax_codes_found = set()

        # ---------------------------------------------------------
        # 0. ƯU TIÊN TRÍCH XUẤT ATOMIC FACTS TỪ JSON EXTRACT (extracted_data)
        # ---------------------------------------------------------
        ext_data = doc_result.get("extracted_data") if doc_result else None
        if ext_data and isinstance(ext_data, dict):
            def find_source(val):
                if val is None:
                    return 1, "", [10.0, 10.0, 100.0, 30.0]
                s_val = str(val).strip()
                if not s_val:
                    return 1, "", [10.0, 10.0, 100.0, 30.0]
                for p_d in pages:
                    p_num = p_d.get("page", 1)
                    p_txt = p_d.get("text", "")
                    if s_val in p_txt:
                        for l in p_txt.splitlines():
                            if s_val in l:
                                return p_num, l.strip()[:200], [10.0, 10.0, 100.0, 30.0]
                        return p_num, s_val, [10.0, 10.0, 100.0, 30.0]
                return 1, s_val, [10.0, 10.0, 100.0, 30.0]

            def parse_num(v):
                if v is None:
                    return None
                try:
                    if isinstance(v, (int, float)):
                        return float(v)
                    cleaned = str(v).replace(",", "").replace(".", "").replace("VND", "").replace("VNĐ", "").strip()
                    return float(cleaned)
                except Exception:
                    return None

            def extract_party_dict(party_data, role_payer=False):
                if not party_data:
                    return
                if isinstance(party_data, str):
                    p_str = party_data.strip()
                    if p_str and not is_noise_value("PARTY", p_str):
                        p, t, b = find_source(p_str)
                        if role_payer:
                            add_fact("PAYER", p_str, None, p, t, b, 0.99)
                            add_fact("BUYER", p_str, None, p, t, b, 0.99)
                        else:
                            add_fact("PAYEE", p_str, None, p, t, b, 0.99)
                            add_fact("SELLER", p_str, None, p, t, b, 0.99)
                        add_fact("PARTY", p_str, None, p, t, b, 0.99)
                    return
                if isinstance(party_data, dict):
                    name = party_data.get("name") or party_data.get("account_name") or party_data.get("company_name")
                    if name and not is_noise_value("PARTY", name):
                        p, t, b = find_source(name)
                        if role_payer:
                            add_fact("PAYER", str(name), None, p, t, b, 0.99)
                            add_fact("BUYER", str(name), None, p, t, b, 0.99)
                        else:
                            add_fact("PAYEE", str(name), None, p, t, b, 0.99)
                            add_fact("SELLER", str(name), None, p, t, b, 0.99)
                        add_fact("PARTY", str(name), None, p, t, b, 0.99)

                    tc = party_data.get("tax_code") or party_data.get("tax_code_or_id") or party_data.get("mst")
                    if tc:
                        p, t, b = find_source(tc)
                        add_fact("TAX_CODE", str(tc), None, p, t, b, 0.99)
                        tax_codes_found.add(str(tc))

                    addr = party_data.get("address")
                    if addr:
                        p, t, b = find_source(addr)
                        add_fact("ADDRESS", str(addr), None, p, t, b, 0.95)

                    acc = party_data.get("bank_account") or party_data.get("account_number")
                    if acc:
                        p, t, b = find_source(acc)
                        add_fact("BANK_ACCOUNT", str(acc), None, p, t, b, 0.98)

                    b_name = party_data.get("bank_name")
                    if b_name:
                        p, t, b = find_source(b_name)
                        add_fact("BANK_NAME", str(b_name), None, p, t, b, 0.98)

                    rep = party_data.get("representative") or party_data.get("contact_person")
                    if rep and not is_noise_value("PARTY", rep):
                        p, t, b = find_source(rep)
                        add_fact("PARTY", str(rep), None, p, t, b, 0.96)

            def safe_dict(v):
                return v if isinstance(v, dict) else {}

            # 1. Document Numbers & Identifiers
            inv_no = (
                ext_data.get("invoice_number") or
                safe_dict(ext_data.get("metadata")).get("invoice_number") or
                safe_dict(ext_data.get("invoice_details")).get("invoice_number")
            )
            if inv_no:
                p, t, b = find_source(inv_no)
                add_fact("INVOICE_NUMBER", str(inv_no), None, p, t, b, 0.99)

            inv_ser = (
                ext_data.get("invoice_symbol") or
                safe_dict(ext_data.get("metadata")).get("serial") or
                safe_dict(ext_data.get("metadata")).get("symbol") or
                safe_dict(ext_data.get("invoice_details")).get("serial")
            )
            if inv_ser:
                p, t, b = find_source(inv_ser)
                add_fact("INVOICE_SERIAL", str(inv_ser), None, p, t, b, 0.98)

            cnt_no = (
                ext_data.get("contract_number") or
                safe_dict(ext_data.get("metadata")).get("contract_number") or
                safe_dict(ext_data.get("commercial_terms")).get("contract_number")
            )
            if cnt_no:
                p, t, b = find_source(cnt_no)
                add_fact("CONTRACT_NUMBER", str(cnt_no), None, p, t, b, 0.99)

            doc_no = (
                ext_data.get("document_number") or
                safe_dict(ext_data.get("voucher_metadata")).get("voucher_number") or
                safe_dict(ext_data.get("voucher_info")).get("voucher_number") or
                safe_dict(ext_data.get("metadata")).get("tax_authority_code") or
                safe_dict(ext_data.get("invoice_details")).get("tax_authority_code")
            )
            if doc_no:
                p, t, b = find_source(doc_no)
                add_fact("DOCUMENT_NUMBER", str(doc_no), None, p, t, b, 0.99)

            bank_ref = (
                ext_data.get("transaction_id") or
                ext_data.get("transaction_code") or
                safe_dict(ext_data.get("transaction_details")).get("transaction_id")
            )
            if bank_ref:
                p, t, b = find_source(bank_ref)
                add_fact("BANK_REFERENCE", str(bank_ref), None, p, t, b, 0.99)

            # 2. Amounts & Values
            tot_amt = (
                ext_data.get("total_amount") if ext_data.get("total_amount") is not None else
                (ext_data.get("amount") if ext_data.get("amount") is not None else
                (ext_data.get("total_payment") if ext_data.get("total_payment") is not None else
                (safe_dict(ext_data.get("financials")).get("total_payment") if safe_dict(ext_data.get("financials")).get("total_payment") is not None else
                (safe_dict(ext_data.get("commercial_terms")).get("total_value") if safe_dict(ext_data.get("commercial_terms")).get("total_value") is not None else
                (safe_dict(ext_data.get("transaction_details")).get("amount") if safe_dict(ext_data.get("transaction_details")).get("amount") is not None else
                (safe_dict(ext_data.get("totals")).get("total_amount") if safe_dict(ext_data.get("totals")).get("total_amount") is not None else
                (safe_dict(ext_data.get("total_summary")).get("total_amount") if safe_dict(ext_data.get("total_summary")).get("total_amount") is not None else
                safe_dict(ext_data.get("summary")).get("total_amount"))))))))
            )
            if tot_amt is not None:
                parsed_amt = parse_num(tot_amt)
                if parsed_amt is not None:
                    p, t, b = find_source(tot_amt)
                    cur = ext_data.get("currency") or safe_dict(ext_data.get("transaction_details")).get("currency") or "VND"
                    add_fact("TOTAL_AMOUNT", parsed_amt, cur, p, t, b, 0.99)
                    add_fact("AMOUNT", parsed_amt, cur, p, t, b, 0.99)
                    add_fact("GROSS_AMOUNT", parsed_amt, cur, p, t, b, 0.99)

            subtot = (
                ext_data.get("subtotal") if ext_data.get("subtotal") is not None else
                (ext_data.get("sub_total") if ext_data.get("sub_total") is not None else
                (ext_data.get("subtotal_amount") if ext_data.get("subtotal_amount") is not None else
                (safe_dict(ext_data.get("financials")).get("subtotal_amount") if safe_dict(ext_data.get("financials")).get("subtotal_amount") is not None else
                (safe_dict(ext_data.get("financials")).get("taxable_amount_10") if safe_dict(ext_data.get("financials")).get("taxable_amount_10") is not None else
                safe_dict(ext_data.get("summary")).get("subtotal")))))
            )
            if subtot is not None:
                parsed_sub = parse_num(subtot)
                if parsed_sub is not None:
                    p, t, b = find_source(subtot)
                    add_fact("NET_AMOUNT", parsed_sub, "VND", p, t, b, 0.98)

            vat_amt = (
                ext_data.get("vat_amount") if ext_data.get("vat_amount") is not None else
                (safe_dict(ext_data.get("financials")).get("vat_amount") if safe_dict(ext_data.get("financials")).get("vat_amount") is not None else
                (safe_dict(ext_data.get("commercial_terms")).get("vat_value") if safe_dict(ext_data.get("commercial_terms")).get("vat_value") is not None else
                safe_dict(ext_data.get("summary")).get("vat_amount")))
            )
            if vat_amt is not None:
                parsed_vat = parse_num(vat_amt)
                if parsed_vat is not None:
                    p, t, b = find_source(vat_amt)
                    add_fact("VAT_AMOUNT", parsed_vat, "VND", p, t, b, 0.98)

            # 3. Dates
            d_val = (
                ext_data.get("invoice_date") or
                ext_data.get("contract_date") or
                ext_data.get("issue_date") or
                ext_data.get("date") or
                safe_dict(ext_data.get("voucher_info")).get("date") or
                ext_data.get("transaction_date") or
                ext_data.get("transaction_time") or
                safe_dict(ext_data.get("metadata")).get("issue_date") or
                safe_dict(ext_data.get("metadata")).get("effective_date") or
                safe_dict(ext_data.get("transaction_details")).get("transaction_time") or
                safe_dict(ext_data.get("voucher_metadata")).get("date")
            )
            if d_val:
                p, t, b = find_source(d_val)
                s_date = str(d_val).strip()
                date_part = s_date[:10] if len(s_date) >= 10 else s_date
                add_fact("DOCUMENT_DATE", date_part, None, p, t, b, 0.99)
                if ext_data.get("contract_date") or safe_dict(ext_data.get("metadata")).get("effective_date"):
                    add_fact("CONTRACT_DATE", s_date, None, p, t, b, 0.99)
                if ext_data.get("invoice_date") or safe_dict(ext_data.get("metadata")).get("issue_date"):
                    add_fact("INVOICE_DATE", s_date, None, p, t, b, 0.99)
                if ext_data.get("transaction_date") or ext_data.get("transaction_time"):
                    add_fact("TRANSACTION_DATE", s_date, None, p, t, b, 0.99)

            exp_date = safe_dict(ext_data.get("metadata")).get("expiration_date") or ext_data.get("due_date")
            if exp_date:
                p, t, b = find_source(exp_date)
                add_fact("DUE_DATE", str(exp_date)[:10], None, p, t, b, 0.98)

            # 4. Parties & Stakeholders
            # Sellers / Payees / Deliverers
            for seller_key in ["seller", "supplier", "party_b", "company_name", "company_info", "remitter"]:
                if seller_key in ext_data:
                    is_remitter = (seller_key == "remitter")
                    extract_party_dict(ext_data[seller_key], role_payer=is_remitter)

            # Buyers / Payers / Recipients
            is_bank_doc = (ext_data.get("document_type") == "bank_transfer" or any(k in ext_data for k in ["sender_bank", "receiver_bank", "recipient_bank", "transaction_code", "transaction_id"]))
            for buyer_key in ["buyer", "customer", "party_a", "receiver_name", "recipient_name", "beneficiary", "recipient"]:
                if buyer_key in ext_data:
                    is_ben = buyer_key in ["beneficiary", "recipient"] or (buyer_key in ["receiver_name", "recipient_name"] and is_bank_doc)
                    extract_party_dict(ext_data[buyer_key], role_payer=not is_ben)

            if "voucher_info" in ext_data and isinstance(ext_data["voucher_info"], dict):
                v_info = ext_data["voucher_info"]
                if v_info.get("receiver_name"):
                    extract_party_dict(v_info["receiver_name"], role_payer=True)
                if v_info.get("export_warehouse"):
                    p, t, b = find_source(v_info["export_warehouse"])
                    add_fact("ADDRESS", str(v_info["export_warehouse"]), None, p, t, b, 0.95)
                if v_info.get("delivery_location"):
                    p, t, b = find_source(v_info["delivery_location"])
                    add_fact("ADDRESS", str(v_info["delivery_location"]), None, p, t, b, 0.95)
                if v_info.get("reason"):
                    p, t, b = find_source(v_info["reason"])
                    add_fact("TRANSACTION_REMARK", str(v_info["reason"]), None, p, t, b, 0.96)

            if "sender" in ext_data:
                extract_party_dict(ext_data["sender"], role_payer=True)
            if ext_data.get("sender_name"):
                extract_party_dict(ext_data["sender_name"], role_payer=True)

            if "payment_info" in ext_data and isinstance(ext_data["payment_info"], dict):
                p_info = ext_data["payment_info"]
                if p_info.get("account_name"):
                    extract_party_dict(p_info["account_name"], role_payer=False)
                if p_info.get("account_number"):
                    p, t, b = find_source(p_info["account_number"])
                    add_fact("BANK_ACCOUNT", str(p_info["account_number"]), None, p, t, b, 0.98)
                if p_info.get("bank_name"):
                    p, t, b = find_source(p_info["bank_name"])
                    add_fact("BANK_NAME", str(p_info["bank_name"]), None, p, t, b, 0.98)

            # 5. Accounts and Banks (flat keys)
            for acc_key in ["receiver_account", "receiver_account_number", "recipient_account_number", "sender_account_number"]:
                if ext_data.get(acc_key):
                    p, t, b = find_source(ext_data[acc_key])
                    add_fact("BANK_ACCOUNT", str(ext_data[acc_key]), None, p, t, b, 0.99)

            for bnk_key in ["receiver_bank", "recipient_bank", "sender_bank", "bank_name"]:
                if ext_data.get(bnk_key):
                    p, t, b = find_source(ext_data[bnk_key])
                    add_fact("BANK_NAME", str(ext_data[bnk_key]), None, p, t, b, 0.99)

            if ext_data.get("tax_code"):
                p, t, b = find_source(ext_data["tax_code"])
                add_fact("TAX_CODE", str(ext_data["tax_code"]), None, p, t, b, 0.99)
                tax_codes_found.add(str(ext_data["tax_code"]))

            for addr_key in ["address", "export_from_warehouse", "delivery_location"]:
                if ext_data.get(addr_key):
                    p, t, b = find_source(ext_data[addr_key])
                    add_fact("ADDRESS", str(ext_data[addr_key]), None, p, t, b, 0.95)

            for note_key in ["note", "description", "content", "reason"]:
                if ext_data.get(note_key) and isinstance(ext_data[note_key], str):
                    p, t, b = find_source(ext_data[note_key])
                    add_fact("TRANSACTION_REMARK", str(ext_data[note_key]), None, p, t, b, 0.96)

            # Payment method
            pay_m = ext_data.get("payment_method") or safe_dict(ext_data.get("buyer")).get("payment_method") or safe_dict(ext_data.get("commercial_terms")).get("payment_method")
            if pay_m and isinstance(pay_m, str):
                p, t, b = find_source(pay_m)
                add_fact("PAYMENT_METHOD", str(pay_m), None, p, t, b, 0.96)

            # 6. Entities array if present
            if "entities" in ext_data and isinstance(ext_data["entities"], dict):
                ents = ext_data["entities"]
                for d in ents.get("dates", []):
                    p, t, b = find_source(d)
                    add_fact("DOCUMENT_DATE", str(d), None, p, t, b, 0.95)
                for a in ents.get("amounts", []):
                    p, t, b = find_source(a)
                    add_fact("TOTAL_AMOUNT", float(a), "VND", p, t, b, 0.95)
                for org in ents.get("organizations", []):
                    p, t, b = find_source(org)
                    add_fact("PARTY", str(org), None, p, t, b, 0.95)

        for page_data in pages:
            page_num = page_data.get("page", 1)
            p_text = page_data.get("text", "")
            p_lines = [l.strip() for l in p_text.splitlines() if l.strip()]

            # ---------------------------------------------------------
            # 1. DOCUMENT NUMBERS & IDENTIFIERS
            # ---------------------------------------------------------
            if doc_type in ["VAT_INVOICE", "PURCHASE_INVOICE", "SALES_INVOICE", "BANK_TRANSFER_PROOF", "BANK_STATEMENT", "UNKNOWN"]:
                inv_match = re.search(r'(?:Số HĐ|Số hóa đơn|hoa don|hóa đơn|Invoice No|No\.|Số\s*\([^)]*\))\s*[\:\-]?\s*\n?\s*([A-Z0-9\/\_\-]{3,20})', p_text, re.IGNORECASE)
                if inv_match and re.search(r'\d', inv_match.group(1)):
                    add_fact("INVOICE_NUMBER", inv_match.group(1).strip(), None, page_num, inv_match.group(0), [10.0, 10.0, 100.0, 30.0], 0.98)

                serial_match = re.search(r'(?:Ký hiệu|Serial)\s*(?:\([^)]*\))?\s*[\:\-]?\s*([A-Z0-9]{4,10})', p_text, re.IGNORECASE)
                if serial_match:
                    add_fact("INVOICE_SERIAL", serial_match.group(1).strip(), None, page_num, serial_match.group(0), [10.0, 10.0, 100.0, 30.0], 0.96)

            if "CONTRACT" in doc_type or doc_type in ["PURCHASE_ORDER", "LOAN_AGREEMENT", "VAT_INVOICE", "SALES_INVOICE", "PURCHASE_INVOICE", "UNKNOWN"]:
                cnt_match = re.search(r'(?:Mã hợp đồng|Hợp đồng mua bán BĐS số|Hợp đồng mua bán số|Hợp đồng số|Contract No|HĐMB)\s*[\:\-]?\s*\n?\s*([A-Za-z0-9\/\_\-\u00C0-\u1EF9]{3,30})', p_text, re.IGNORECASE)
                if cnt_match and re.search(r'\d', cnt_match.group(1)):
                    num_val = cnt_match.group(1).strip()
                    add_fact("CONTRACT_NUMBER", num_val, None, page_num, cnt_match.group(0), [10.0, 10.0, 100.0, 30.0], 0.99)

            if doc_type in ["BANK_TRANSFER_PROOF", "BANK_STATEMENT", "UNKNOWN"]:
                ref_match = re.search(r'(?:Mã giao dịch|Số lệnh|Reference|FT\d+)\s*[\:\-]?\s*([A-Z0-9]{8,25})', p_text, re.IGNORECASE)
                if ref_match:
                    add_fact("BANK_REFERENCE", ref_match.group(1), None, page_num, ref_match.group(0), [10.0, 20.0, 120.0, 40.0], 0.99)

            if doc_type in ["ASSET_DOCUMENT", "WAREHOUSE_ISSUE_NOTE", "DELIVERY_ACCEPTANCE_RECORD"]:
                doc_num_m = re.search(r'(?:Số GCN|Số|Số phiếu|Số biên bản|No\.)\s*[\:\-]?\s*([A-Za-z0-9\/\_\-]{3,25})', p_text, re.IGNORECASE)
                if doc_num_m and re.search(r'\d', doc_num_m.group(1)):
                    add_fact("DOCUMENT_NUMBER", doc_num_m.group(1).strip(), None, page_num, doc_num_m.group(0), [10.0, 10.0, 100.0, 30.0], 0.96)

            # ---------------------------------------------------------
            # 2. DATES
            # ---------------------------------------------------------
            doc_date_match = re.search(r'(?:Ngày|Date)\s*(?:\(date\)\s*)?(\d{1,2})\s*tháng\s*(?:\(month\)\s*)?(\d{1,2})\s*năm\s*(?:\(year\)\s*)?(\d{4})', p_text, re.IGNORECASE)
            if doc_date_match:
                formatted_date = f"{doc_date_match.group(3)}-{doc_date_match.group(2).zfill(2)}-{doc_date_match.group(1).zfill(2)}"
                add_fact("DOCUMENT_DATE", formatted_date, None, page_num, doc_date_match.group(0), [10.0, 50.0, 200.0, 70.0], 0.96)
            
            sign_date_match = re.search(r'(?:Ngày ký|Ngày lập|Ngày giao dịch)\s*[\:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', p_text, re.IGNORECASE)
            if sign_date_match:
                parts = re.split(r'[\/\-\.]', sign_date_match.group(1))
                if len(parts) == 3:
                    f_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                    add_fact("DOCUMENT_DATE", f_date, None, page_num, sign_date_match.group(0), [10.0, 50.0, 200.0, 70.0], 0.96)

            cnt_date_match = re.search(r'Hợp đồng[^\n]*ngày\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', p_text, re.IGNORECASE)
            if cnt_date_match:
                parts = re.split(r'[\/\-\.]', cnt_date_match.group(1))
                if len(parts) == 3:
                    add_fact("CONTRACT_DATE", f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}", None, page_num, cnt_date_match.group(0), [10.0, 50.0, 200.0, 70.0], 0.95)

            exp_date_match = re.search(r'(?:thời hạn|hạn thanh toán|due date|đến ngày|đến|ngày đáo hạn)\s*[\:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', p_text, re.IGNORECASE)
            if exp_date_match:
                parts = re.split(r'[\/\-\.]', exp_date_match.group(1))
                if len(parts) == 3:
                    add_fact("DUE_DATE", f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}", None, page_num, exp_date_match.group(0), [10.0, 80.0, 200.0, 100.0], 0.95)

            # Standalone date match for receipts if no prefix matched
            if not any(f.fact_type == "DOCUMENT_DATE" for f in facts):
                std_date_match = re.search(r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b', p_text)
                if std_date_match:
                    day, month, year = std_date_match.group(1), std_date_match.group(2), std_date_match.group(3)
                    add_fact("DOCUMENT_DATE", f"{year}-{month.zfill(2)}-{day.zfill(2)}", None, page_num, std_date_match.group(0), [10.0, 50.0, 200.0, 70.0], 0.95)

            # ---------------------------------------------------------
            # 3. PARTIES, TAX CODES, AMOUNTS, & SPECIAL FIELDS
            # ---------------------------------------------------------
            for idx, line in enumerate(p_lines):
                line_lower = line.lower()

                # Tax Code
                tax_match = re.search(r'(?:Mã số thuế|Tax code|MST)\s*[\:\-]?\s*(\d{10}(?:\-\d{3})?)', line, re.IGNORECASE)
                if tax_match:
                    tc_val = tax_match.group(1).strip()
                    tax_codes_found.add(tc_val)
                    add_fact("TAX_CODE", tc_val, None, page_num, line, [10.0, 120.0, 250.0, 140.0], 0.98)

                # Dedicated Bank Sender / Payer info in transfer memo (e.g. "Nguyen Kim Hung chuyen token")
                if doc_type in ["BANK_TRANSFER_PROOF", "BANK_STATEMENT", "UNKNOWN"]:
                    payer_memo_match = re.search(r'^([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ][a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+(?:\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ][a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+)+)\s+(?:chuyen|chuyển|tt|thanh toan)', line, re.IGNORECASE)
                    if payer_memo_match:
                        add_fact("PAYER", payer_memo_match.group(1).strip(), None, page_num, line, [10.0, 150.0, 300.0, 170.0], 0.95)

                    # Uppercase recipient name on bank receipt (e.g., "PHAM HUU VINH")
                    if re.match(r'^[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ\s]{5,40}$', line.strip()) and not any(kw in line.upper() for kw in ["MB", "PRIORITY", "CHUYỂN TIỀN", "THÀNH CÔNG", "VND", "VNĐ", "GIAO DỊCH", "NGÂN HÀNG"]):
                        add_fact("PAYEE", line.strip(), None, page_num, line, [10.0, 160.0, 300.0, 180.0], 0.95)

                # Parties: Payee / Seller / Party B
                if any(kw in line_lower for kw in ["bên bán", "đơn vị bán", "seller", "bên chuyển nhượng", "bên b", "ngân hàng cho vay", "bên giao"]):
                    val = p_lines[idx+1] if (idx + 1 < len(p_lines) and p_lines[idx+1].startswith(":")) else line
                    val_clean = clean_party_name(val)
                    if val_clean and len(val_clean) > 3 and val_clean.lower() not in HEADER_KEYWORDS:
                        add_fact("PAYEE", val_clean, None, page_num, line, [10.0, 150.0, 300.0, 170.0], 0.95)

                # Parties: Payer / Buyer / Party A
                elif any(kw in line_lower for kw in ["bên mua", "đơn vị mua", "buyer", "bên nhận chuyển nhượng", "bên a", "bên vay", "khách hàng", "bên nhận", "người mua hàng", "tên đơn vị"]):
                    val = p_lines[idx+1] if (idx + 1 < len(p_lines) and p_lines[idx+1].startswith(":")) else line
                    val_clean = clean_party_name(val)
                    if val_clean and len(val_clean) > 3 and val_clean.lower() not in HEADER_KEYWORDS:
                        add_fact("PAYER", val_clean, None, page_num, line, [10.0, 170.0, 300.0, 190.0], 0.95)

                elif (line.startswith(": CÔNG TY") or line.startswith("CÔNG TY") or line.startswith("Ký bởi: CÔNG TY")) and not any(kw in line_lower for kw in ["tên đơn vị", "i. đơn vị", "ii. đơn vị"]):
                    val_clean = clean_party_name(line)
                    if val_clean and len(val_clean) > 3 and val_clean.lower() not in HEADER_KEYWORDS:
                        if not any(val_clean.lower() in str(f.value).lower() for f in facts if f.fact_type in ["PAYER", "PAYEE", "PARTY"]):
                            add_fact("PARTY", val_clean, None, page_num, line, [10.0, 150.0, 300.0, 170.0], 0.92)

                # ---------------------------------------------------------
                # DOCUMENT-TYPE SPECIFIC EXTRACTION LOGIC
                # ---------------------------------------------------------
                search_text = f"{line} {p_lines[idx+1]}" if (idx + 1 < len(p_lines)) else line

                # Specifics for LOAN / FUNDING
                if doc_type in ["LOAN_AGREEMENT", "FUNDING_DOCUMENT"]:
                    ir_match = re.search(r'(?:lãi suất|interest rate)\s*[\:\-]?\s*(\d+(?:\.\d+)?\s*\%(?:\/năm|\/tháng)?)', search_text, re.IGNORECASE)
                    if ir_match:
                        add_fact("INTEREST_RATE", ir_match.group(1), None, page_num, search_text, [10.0, 200.0, 200.0, 220.0], 0.96)
                    
                    term_match = re.search(r'(?:kỳ hạn|thời hạn vay)\s*[\:\-]?\s*(\d+\s*(?:tháng|năm))', search_text, re.IGNORECASE)
                    if term_match:
                        add_fact("REPAYMENT_TERM", term_match.group(1), None, page_num, search_text, [10.0, 220.0, 200.0, 240.0], 0.95)

                # Specifics for ASSETS
                if doc_type == "ASSET_DOCUMENT":
                    asset_match = re.search(r'(?:tài sản|danh mục|quyền sử dụng đất|nhà xưởng|xe ô tô)\s*[\:\-]?\s*([^\n]+)', line, re.IGNORECASE)
                    if asset_match and len(asset_match.group(1).strip()) > 3:
                        add_fact("ASSET_TYPE", asset_match.group(1).strip(), None, page_num, line, [10.0, 250.0, 200.0, 270.0], 0.92)

                # Specifics for DELIVERY / WAREHOUSE
                if doc_type in ["WAREHOUSE_ISSUE_NOTE", "DELIVERY_ACCEPTANCE_RECORD"]:
                    if any(kw in line_lower for kw in ["đã nghiệm thu", "đã bàn giao", "hoàn thành", "accepted"]):
                        add_fact("ACCEPTANCE_STATUS", "COMPLETED", None, page_num, line, [10.0, 280.0, 200.0, 300.0], 0.95)

                # Standard Amount Parsing
                amount_keywords = ["tổng cộng tiền thanh toán", "tổng tiền thanh toán", "tổng cộng thanh toán", "tổng tiền phải thanh toán", "total payment", "total amount", "hạn mức tín dụng", "giá trị hợp đồng", "số tiền chuyển", "số tiền giao dịch", "số tiền thanh toán", "giá trị giao dịch"]
                
                # Check for explicit bank transfer amount line (e.g., 'Số tiền: 500.000.000 VNĐ')
                is_bank_amount_line = doc_type in ["BANK_TRANSFER_PROOF", "BANK_STATEMENT"] and any(kw in line_lower for kw in ["số tiền", "tiền chuyển", "số tiền giao dịch", "số tiền thanh toán", "vnd", "vnđ", "đ", "amount"])

                if any(kw in line_lower for kw in amount_keywords) or is_bank_amount_line:
                    num_match = re.search(r'([\d\.\,]{4,18})', line)
                    if not num_match:
                        num_match = re.search(r'([\d\.\,]{4,18})', search_text)
                    if num_match:
                        raw_val = num_match.group(1).replace(".", "").replace(",", "")
                        if raw_val.isdigit() and len(raw_val) >= 4:
                            amount_val = float(raw_val)
                            add_fact("TOTAL_AMOUNT", amount_val, "VND", page_num, search_text, [120.0, 350.0, 420.0, 390.0], 0.99)

                elif any(kw in line_lower for kw in ["không chịu thuế", "kct"]):
                    num_match = re.search(r'(?:không chịu thuế|kct)[^\d]*([\d\.\,]{4,18})', search_text, re.IGNORECASE)
                    if not num_match:
                        num_match = re.search(r'([\d\.\,]{4,18})', search_text)
                    if num_match:
                        raw_val = num_match.group(1).replace(".", "").replace(",", "")
                        if raw_val.isdigit() and len(raw_val) >= 4:
                            add_fact("TAX_EXEMPT_SUBTOTAL", float(raw_val), "VND", page_num, search_text, [120.0, 350.0, 420.0, 390.0], 0.97)

                elif any(kw in line_lower for kw in ["tiền thuế giá trị gia tăng", "tiền thuế gtgt", "vat amount"]):
                    vat_match = re.search(r'(?:tiền thuế giá trị gia tăng|tiền thuế gtgt|vat amount)[^\:\n]*[\:\-]\s*([\d\.\,]{4,18})', search_text, re.IGNORECASE)
                    if not vat_match:
                        vat_match = re.search(r'(?:tiền thuế giá trị gia tăng|tiền thuế gtgt|vat amount)[^\d]*(?:\d+\%\s*[\:\-]?)?\s*([\d\.\,]{4,18})', search_text, re.IGNORECASE)
                    if vat_match:
                        raw_val = vat_match.group(1).replace(".", "").replace(",", "")
                        if raw_val.isdigit() and len(raw_val) >= 4:
                            add_fact("VAT_AMOUNT", float(raw_val), "VND", page_num, search_text, [120.0, 390.0, 420.0, 410.0], 0.97)

                elif any(kw in line_lower for kw in ["tổng tiền chịu thuế", "tiền chịu thuế"]):
                    taxable_match = re.search(r'(?:tổng tiền chịu thuế|tiền chịu thuế)[^\d]*([\d\.\,]{4,18})', search_text, re.IGNORECASE)
                    if taxable_match:
                        raw_val = taxable_match.group(1).replace(".", "").replace(",", "")
                        if raw_val.isdigit() and len(raw_val) >= 4:
                            add_fact("TAXABLE_SUBTOTAL", float(raw_val), "VND", page_num, search_text, [120.0, 350.0, 420.0, 390.0], 0.97)

                elif any(kw in line_lower for kw in ["cộng tiền", "tiền hàng", "subtotal"]):
                    num_match = re.search(r'(?:cộng tiền|tiền hàng|subtotal)[^\d]*([\d\.\,]{4,18})', search_text, re.IGNORECASE)
                    if not num_match:
                        num_match = re.search(r'([\d\.\,]{4,18})', search_text)
                    if num_match:
                        raw_val = num_match.group(1).replace(".", "").replace(",", "")
                        if raw_val.isdigit() and len(raw_val) >= 4:
                            add_fact("NET_AMOUNT", float(raw_val), "VND", page_num, search_text, [120.0, 350.0, 420.0, 390.0], 0.97)

                else:
                    # Ignore area/quantity lines containing units like m², m2, m, hệ thống, cái,...
                    if not re.search(r'[\d\.\,]+\s*(?:m²|m2|m|cm|mm|hệ thống|bộ|cái|chiếc|kg|tấn|yến|g|l|m3|m³|sàn)\b', line, re.IGNORECASE):
                        amt_match = re.search(r'\b([\d]{1,3}(?:[\.\,]\d{3})+)\b(?:\s*(?:VND|VNĐ|đ|USD))?', line, re.IGNORECASE)
                        if not amt_match:
                            amt_match = re.search(r'([\d\.\,]{4,18})\s*(?:VND|VNĐ|đ|USD)', line, re.IGNORECASE)
                        if amt_match:
                            raw_val = amt_match.group(1).replace(".", "").replace(",", "")
                            if raw_val.isdigit() and len(raw_val) >= 4:
                                amount_val = float(raw_val)
                                if not any(f.value == amount_val for f in facts if f.fact_type in ["TOTAL_AMOUNT", "VAT_AMOUNT", "NET_AMOUNT"]):
                                    # For bank transfer proof, any valid monetary value is TOTAL_AMOUNT
                                    if doc_type in ["BANK_TRANSFER_PROOF", "BANK_STATEMENT"] or any(kw in line_lower for kw in ["tổng", "thành tiền", "cộng tiền", "thanh toán", "giá trị"]):
                                        ft_to_add = "TOTAL_AMOUNT" if doc_type in ["BANK_TRANSFER_PROOF", "BANK_STATEMENT"] else "AMOUNT"
                                        add_fact(ft_to_add, amount_val, "VND", page_num, line, [120.0, 350.0, 420.0, 390.0], 0.95)

                # Bank Details & Bank Name - Require explicit bank context keywords
                bank_match = re.search(r'\b(Techcombank|TCB|Vietcombank|VCB|VietinBank|BIDV|Agribank|MBBank|MB|ACB|TPBank|VPBank|Sacombank|HDBank|MSB|VIB|SeABank|Eximbank|OCB|LPBank|Shinhan|Standard Chartered|Bac A Bank|Kienlongbank|PVComBank|NCB|BaoVietBank|VietBank)\b', line, re.IGNORECASE)
                if bank_match:
                    # Context check: must be near bank/account/transfer keywords
                    if any(kw in line_lower for kw in ["tại", "ngân hàng", "tài khoản", "stk", "chuyển khoản", "bank", "chi nhánh"]):
                        b_found = bank_match.group(0)
                        clean_b = re.sub(r'^[\:\-\s\d\t]*tại\s*', '', line, flags=re.IGNORECASE)
                        clean_b = re.sub(r'^(?:Tài khoản ngân hàng|Tài khoản|STK|Ngân hàng|\'|\s|nhận|chuyển)+[\:\s\-]*', '', clean_b, flags=re.IGNORECASE).strip(" :-'")
                        clean_b = re.sub(r'^\d{8,20}\s*tại\s*', '', clean_b, flags=re.IGNORECASE).strip(" :-'")
                        final_b = b_found if (not clean_b or "nhận" in clean_b.lower() or "chuyển" in clean_b.lower()) else clean_b
                        add_fact("BANK_NAME", final_b, None, page_num, line, [10.0, 200.0, 250.0, 220.0], 0.95)

                # Dedicated Bank Account extraction - Prevent tax codes & year numbers from mistagging as STK
                stk_match = re.search(r'(?:tài khoản ngân hàng|tài khoản|stk|account|tk|số tài khoản|tài khoản nợ|tài khoản có|tài khoản trích nợ|tài khoản thụ hưởng)\s*(?:ngân hàng)?\s*[\:\-]?\s*(\d{8,20})', search_text, re.IGNORECASE)
                if not stk_match:
                    if any(kw in line_lower for kw in ["tài khoản", "stk", "account", "tk", "ngân hàng", "bank"]):
                        stk_match = re.search(r'\b(\d{8,16})\b', line)

                if stk_match:
                    num_acc = stk_match.group(1)
                    if num_acc not in tax_codes_found and not any(kw in line.lower() for kw in ["mã số thuế", "mst", "tax code"]) and not re.search(r'(?:202\d|201\d)', num_acc):
                        add_fact("BANK_ACCOUNT", num_acc, None, page_num, search_text, [10.0, 230.0, 250.0, 250.0], 0.96)

                # Dedicated Bank Sender / Payer
                if any(kw in line_lower for kw in ["tài khoản trích nợ", "tài khoản chuyển", "người chuyển", "tài khoản nợ", "tài khoản nguồn", "tên người chuyển", "tk nợ", "tk chuyển", "from account", "sender"]):
                    val = p_lines[idx+1] if (idx + 1 < len(p_lines) and (p_lines[idx+1].startswith(":") or not re.search(r'\d', p_lines[idx+1]))) else line
                    val_clean = clean_party_name(val)
                    if val_clean and len(val_clean) > 3 and val_clean.lower() not in HEADER_KEYWORDS:
                        add_fact("PAYER", val_clean, None, page_num, search_text, [10.0, 170.0, 300.0, 190.0], 0.96)
                        add_fact("PARTY", val_clean, None, page_num, search_text, [10.0, 170.0, 300.0, 190.0], 0.96)

                # Dedicated Bank Recipient / Payee
                if any(kw in line_lower for kw in ["tài khoản thụ hưởng", "tài khoản nhận", "người nhận", "tài khoản có", "tên người nhận", "tk có", "tk nhận", "to account", "beneficiary"]):
                    recip_m = re.search(r'Tên người nhận[\:\s]+([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ\s]+?)(?=\s+Ngân hàng|\s+Số|\s+Tài khoản|\s+Mã|\s+STK|$)', line, re.IGNORECASE)
                    if recip_m and len(recip_m.group(1).strip()) > 2:
                        val_clean = recip_m.group(1).strip()
                    else:
                        val = p_lines[idx+1] if (idx + 1 < len(p_lines) and (p_lines[idx+1].startswith(":") or not re.search(r'\d', p_lines[idx+1]))) else line
                        val_clean = clean_party_name(val)
                    if val_clean and len(val_clean) > 3 and val_clean.lower() not in HEADER_KEYWORDS:
                        add_fact("PAYEE", val_clean, None, page_num, search_text, [10.0, 150.0, 300.0, 170.0], 0.96)
                        add_fact("PARTY", val_clean, None, page_num, search_text, [10.0, 150.0, 300.0, 170.0], 0.96)

                # Bank Transfer Remark / Memo
                if any(kw in line_lower for kw in ["chuyen khoan", "chuyển khoản", "tt token", "noi dung", "nội dung", "lời nhắn", "nội dung chuyển tiền", "hình thức thanh toán"]):
                    clean_rem = re.sub(r'^(?:Hình thức thanh toán|Nội dung chuyển tiền|Nội dung|Lời nhắn)[\:\s\-]*', '', search_text, flags=re.IGNORECASE).strip(" :-")
                    clean_rem = re.sub(r'[\s\-]*Phí chuyển tiền.*$', '', clean_rem, flags=re.IGNORECASE).strip(" :-")
                    if clean_rem:
                        add_fact("TRANSACTION_REMARK", clean_rem, None, page_num, search_text, [10.0, 240.0, 350.0, 260.0], 0.95)

        # ---------------------------------------------------------
        # 5. STRUCTURED TABLE FACTS & CROSS-VALIDATION
        # ---------------------------------------------------------
        table_items = AtomicFactExtractor.extract_structured_table_items(doc_result, doc_type=doc_type)
        if table_items:
            has_total = any(f.fact_type in ["TOTAL_AMOUNT", "GROSS_AMOUNT"] for f in facts)
            valid_amounts = [
                it["amount"] for it in table_items 
                if isinstance(it.get("amount"), (int, float)) and it["amount"] > 0
            ]
            if valid_amounts:
                calc_sum = round(sum(valid_amounts), 2)
                # Bổ sung fact tổng các dòng bảng để phục vụ kiểm toán và đối chiếu xung đột
                add_fact("TABLE_SUM_AMOUNT", calc_sum, "VND", 1, f"Tổng cộng {len(valid_amounts)} dòng trong bảng", [10.0, 350.0, 250.0, 380.0], 0.96)
                if not has_total:
                    # Gán luôn TOTAL_AMOUNT nếu trước đó regex trong văn bản chưa bắt được
                    add_fact("TOTAL_AMOUNT", calc_sum, "VND", 1, f"Suy luận từ tổng {len(valid_amounts)} dòng bảng", [10.0, 350.0, 250.0, 380.0], 0.92)

            # Facts đặc thù cho Sao kê ngân hàng
            if doc_type in ["BANK_STATEMENT", "BANK_TRANSFER_PROOF"]:
                debits = [it["debit"] for it in table_items if isinstance(it.get("debit"), (int, float))]
                credits = [it["credit"] for it in table_items if isinstance(it.get("credit"), (int, float))]
                if debits:
                    add_fact("TOTAL_DEBIT_AMOUNT", round(sum(debits), 2), "VND", 1, "Tổng tiền ghi nợ sao kê", [10.0, 350.0, 250.0, 380.0], 0.95)
                if credits:
                    add_fact("TOTAL_CREDIT_AMOUNT", round(sum(credits), 2), "VND", 1, "Tổng tiền ghi có sao kê", [10.0, 350.0, 250.0, 380.0], 0.95)

        if not facts:
            add_fact("STATUS", "READ_ONLY", None, 1, full_text[:100], [0.0, 0.0, 0.0, 0.0], 0.50)

        return facts

    @staticmethod
    def parse_float_safe(val_str: Any) -> Optional[float]:
        """Safely parse numbers with dots/commas format (e.g. 3.500,0 or 24.500.000.000 or -1.500)."""
        if val_str is None:
            return None
        s = str(val_str).strip()
        if not s:
            return None

        try:
            from core_ocr.normalizer import normalize_financial_number
            val = normalize_financial_number(s)
            if val is not None:
                return val
        except Exception:
            try:
                from backend.core_ocr.normalizer import normalize_financial_number
                val = normalize_financial_number(s)
                if val is not None:
                    return val
            except Exception:
                pass

        # Fallback parsing
        is_negative = s.startswith("-") or (s.startswith("(") and s.endswith(")"))
        cleaned = re.sub(r'[^\d\.\,]', '', s)
        if "." in cleaned and "," in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            parts = cleaned.split(",")
            if len(parts[-1]) in (1, 2):
                cleaned = "".join(parts[:-1]) + "." + parts[-1]
            else:
                cleaned = "".join(parts)
        elif "." in cleaned:
            parts = cleaned.split(".")
            if len(parts[-1]) in (1, 2) and len(parts) == 2:
                cleaned = parts[0] + "." + parts[1]
            else:
                cleaned = "".join(parts)

        try:
            num = float(cleaned)
            return -num if is_negative else num
        except ValueError:
            return None

    COLUMN_SYNONYMS = {
        "stt": ["stt", "số tt", "no.", "stt/no", "nō", "số thứ tự", "đợt", "kỳ", "item no"],
        "name": [
            "tên hàng hóa", "danh mục tài sản", "hàng hóa", "diễn giải", "dịch vụ", 
            "nội dung", "tên hàng", "danh mục", "tên tài sản", "description", "item", 
            "tên sản phẩm", "hạng mục", "chỉ tiêu", "nội dung giao dịch", "diễn giải giao dịch",
            "tên công việc", "quy cách", "loại tài sản"
        ],
        "code": ["mã số", "mã hàng", "code", "mã", "thuyết minh", "mã định danh", "kỳ hiệu"],
        "unit": ["đvt", "đơn vị tính", "đơn vị", "unit", "dvt"],
        "qty": [
            "diện tích", "số lượng", "soluong", "qty", "quantity", 
            "diện tích / số lượng", "diện tích/số lượng", "số lượng/diện tích", "khối lượng"
        ],
        "price": ["đơn giá", "dongia", "unit price", "price", "giá", "đơn giá (vnđ)", "giá trị"],
        "vat": ["thuế suất", "gtgt", "vat", "vat rate", "thuế suất gtgt", "% thuế", "tỷ lệ thuế"],
        "amount": [
            "thành tiền", "thanhtien", "amount", "tổng tiền", "thành tiền (vnđ)", 
            "thành tiền sau thuế", "total", "giá trị", "số tiền", "số tiền thanh toán"
        ],
        "trans_date": ["ngày gd", "ngày giao dịch", "ngày", "date", "trans date"],
        "debit": ["ghi nợ", "số tiền ghi nợ", "nợ", "debit", "rút tiền", "tiền ra"],
        "credit": ["ghi có", "số tiền ghi có", "có", "credit", "nộp tiền", "tiền vào"],
        "balance": ["số dư", "số dư cuối", "balance", "số dư sau gd"],
        "current_period": ["kỳ này", "năm nay", "kỳ báo cáo", "số cuối năm", "quý này", "tháng này", "current year"],
        "previous_period": ["kỳ trước", "năm trước", "kỳ so sánh", "số đầu năm", "quý trước", "tháng trước", "previous year"],
        "percentage": ["tỷ lệ", "tỷ lệ thanh toán", "%", "tiến độ", "percentage"]
    }

    @classmethod
    def extract_structured_table_items(cls, doc_result: dict, doc_type: str = "UNKNOWN") -> List[Dict[str, Any]]:
        """
        Trích xuất dữ liệu dòng có cấu trúc từ ma trận Bảng (Invoice, Contract, Statement, Report).
        Ưu tiên lấy trực tiếp từ JSON Extract (extracted_data) nếu có.
        """
        # 1. Ưu tiên lấy từ JSON Extract
        ext_data = doc_result.get("extracted_data") if doc_result else None
        if ext_data and isinstance(ext_data, dict):
            raw_items = ext_data.get("items")
            if raw_items and isinstance(raw_items, list) and len(raw_items) > 0:
                res_items = []
                for idx, it in enumerate(raw_items, 1):
                    res_items.append({
                        "line_number": it.get("line_number") or it.get("item_order") or it.get("stt") or idx,
                        "item_name": (it.get("item_name") or it.get("description") or it.get("product_name") or "").replace("\n", " ").strip(),
                        "unit": it.get("unit"),
                        "quantity": cls.parse_float_safe(it.get("quantity_exported") or it.get("actual_quantity") or it.get("quantity_requested") or it.get("requested_quantity") or it.get("quantity") or it.get("quantity_actual")),
                        "unit_price": cls.parse_float_safe(it.get("unit_price")),
                        "vat_rate": str(it.get("vat_rate")) if it.get("vat_rate") is not None else None,
                        "amount": cls.parse_float_safe(it.get("amount") or it.get("total_amount"))
                    })
                if res_items:
                    return res_items

        items: List[Dict[str, Any]] = []
        tables = doc_result.get("tables", []) if doc_result else []

        for tbl in tables:
            matrix = tbl.get("matrix", [])
            if not matrix or len(matrix) < 2:
                continue

            header_idx = -1
            col_map = {}

            # Dò tìm dòng Header (quét tối đa 10 dòng đầu của bảng)
            for r_i, row in enumerate(matrix[:10]):
                row_str = " ".join(row).lower()
                # Kiểm tra nếu dòng chứa ít nhất 1 từ khóa định danh header
                found_syns = []
                for col_key, synonyms in cls.COLUMN_SYNONYMS.items():
                    if any(syn in row_str for syn in synonyms):
                        found_syns.append(col_key)

                if len(found_syns) >= 2 or any(k in row_str for k in cls.COLUMN_SYNONYMS["name"]):
                    header_idx = r_i
                    for c_i, cell in enumerate(row):
                        cell_l = cell.lower().strip()
                        for col_key, synonyms in cls.COLUMN_SYNONYMS.items():
                            if col_key not in col_map and any(syn in cell_l for syn in synonyms):
                                col_map[col_key] = c_i
                    break

            if header_idx == -1:
                continue

            current_item = None
            for r_i in range(header_idx + 1, len(matrix)):
                row = matrix[r_i]
                row_str = " ".join(row).strip()
                if not row_str:
                    continue

                # Bỏ qua dòng tổng kết / chân bảng
                if any(kw in row_str.lower() for kw in ["cộng tiền", "tổng cộng", "tiền thuế", "grand total", "subtotal"]):
                    continue

                def get_cell(key: str) -> str:
                    return row[col_map[key]].strip() if key in col_map and col_map[key] < len(row) else ""

                stt_val = get_cell("stt")
                name_val = get_cell("name")
                unit_val = get_cell("unit")
                qty_val = get_cell("qty")
                price_val = get_cell("price")
                vat_val = get_cell("vat")
                amt_val = get_cell("amount")
                debit_val = get_cell("debit")
                credit_val = get_cell("credit")
                bal_val = get_cell("balance")
                tdate_val = get_cell("trans_date")
                pct_val = get_cell("percentage")
                cur_val = get_cell("current_period")
                prev_val = get_cell("previous_period")

                # Xác định có phải dòng mới không
                is_new_item = False
                if stt_val and re.match(r'^\d+$', stt_val):
                    is_new_item = True
                elif tdate_val and re.search(r'\d', tdate_val):
                    is_new_item = True
                elif name_val and (price_val or amt_val or debit_val or credit_val or cur_val or (stt_val and stt_val.isdigit())):
                    is_new_item = True
                elif not current_item and (name_val or amt_val):
                    is_new_item = True

                if is_new_item:
                    if current_item:
                        items.append(current_item)

                    current_item = {
                        "line_number": int(stt_val) if stt_val.isdigit() else len(items) + 1,
                        "item_name": name_val.replace("\n", " ").strip() if name_val else None,
                        "unit": unit_val.replace("\n", " ").strip() if unit_val else None,
                        "quantity": cls.parse_float_safe(qty_val),
                        "unit_price": cls.parse_float_safe(price_val),
                        "vat_rate": vat_val.replace("\n", " ").strip() if vat_val else None,
                        "amount": cls.parse_float_safe(amt_val),
                        "debit": cls.parse_float_safe(debit_val),
                        "credit": cls.parse_float_safe(credit_val),
                        "balance": cls.parse_float_safe(bal_val),
                        "transaction_date": tdate_val if tdate_val else None,
                        "percentage": cls.parse_float_safe(pct_val),
                        "current_period": cls.parse_float_safe(cur_val),
                        "previous_period": cls.parse_float_safe(prev_val)
                    }
                else:
                    if current_item and name_val:
                        if current_item.get("item_name"):
                            current_item["item_name"] += " " + name_val.strip()
                        else:
                            current_item["item_name"] = name_val.strip()
                        if not current_item.get("unit") and unit_val:
                            current_item["unit"] = unit_val.strip()
                        if current_item.get("quantity") is None and qty_val:
                            current_item["quantity"] = cls.parse_float_safe(qty_val)

            if current_item:
                items.append(current_item)

        # Fallback: Trích xuất bằng Regex từ text thuần nếu không phát hiện được bảng
        if not items and doc_result:
            full_text = doc_result.get("full_text", "")
            lines = [l.strip() for l in full_text.splitlines() if l.strip()]
            for l in lines:
                m = re.match(r'^(\d+)\s+([^\n]+?)\s+([a-zA-Z²\s]+)\s+([\d\.\,]+)\s+([\d\.\,]+)\s+(KCT|\d+\%)\s+([\d\.\,]+)$', l)
                if m:
                    items.append({
                        "line_number": int(m.group(1)),
                        "item_name": m.group(2).strip(),
                        "unit": m.group(3).strip(),
                        "quantity": cls.parse_float_safe(m.group(4)),
                        "unit_price": cls.parse_float_safe(m.group(5)),
                        "vat_rate": m.group(6),
                        "amount": cls.parse_float_safe(m.group(7))
                    })

        return items

    @classmethod
    def extract_invoice_table_items(cls, doc_result: dict) -> List[Dict[str, Any]]:
        """Hàm tương thích ngược với pipeline hiện có."""
        return cls.extract_structured_table_items(doc_result, doc_type="VAT_INVOICE")



import os
import re
import json
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

try:
    from config import key_manager, MODEL_NAME
except ImportError:
    try:
        from backend.config import key_manager, MODEL_NAME
    except ImportError:
        try:
            from services.key_rotator import KeyManager
        except ImportError:
            from backend.services.key_rotator import KeyManager
        key_manager = KeyManager()
        MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")


# =====================================================================
# DATA NORMALIZATION HELPERS
# =====================================================================

def normalize_number(val: Any) -> Optional[float | int]:
    """
    Chuẩn hóa số tiền / số lượng:
    - Loại bỏ dấu chấm / phẩy phân cách hàng nghìn (ví dụ: '308,000' -> 308000; '24.500.000.000' -> 24500000000).
    - Trả về int nếu là số nguyên, float nếu có phần thập phân, hoặc None nếu rỗng/không hợp lệ.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val) if float(val).is_integer() else float(val)

    s = str(val).strip()
    if not s:
        return None

    # Loại bỏ tiền tệ hoặc ký hiệu đơn vị
    s = re.sub(r'(?i)\b(vnd|vnđ|đ|usd|\$|đồng|d)\b', '', s).strip()

    # Kiểm tra phần trăm
    if s.endswith('%'):
        num_part = s.rstrip('%').strip()
        try:
            return float(num_part)
        except ValueError:
            return None

    # Chuẩn hóa dấu phân cách
    if '.' in s and ',' in s:
        if s.rfind(',') > s.rfind('.'):
            # Kiểu VN/Châu Âu: 24.500.000,50 -> chấm là nghìn, phẩy là thập phân
            s = s.replace('.', '').replace(',', '.')
        else:
            # Kiểu Mỹ: 24,500,000.50 -> phẩy là nghìn, chấm là thập phân
            s = s.replace(',', '')
    elif '.' in s:
        parts = s.split('.')
        if len(parts) > 2:
            s = s.replace('.', '')
        elif len(parts) == 2:
            if len(parts[1]) == 3 and int(parts[0]) > 0:
                s = s.replace('.', '')
    elif ',' in s:
        parts = s.split(',')
        if len(parts) > 2:
            s = s.replace(',', '')
        elif len(parts) == 2:
            if len(parts[1]) == 3 and int(parts[0]) > 0:
                s = s.replace(',', '')
            else:
                s = s.replace(',', '.')

    clean_s = re.sub(r'[^\d\.\-]', '', s)
    if not clean_s or clean_s == '-':
        return None

    try:
        f = float(clean_s)
        return int(f) if f.is_integer() else round(f, 4)
    except ValueError:
        return None


def normalize_date(val: Any) -> Optional[str]:
    """
    Chuẩn hóa ngày tháng về định dạng ISO 'YYYY-MM-DD' hoặc 'YYYY-MM-DD HH:mm:ss'.
    """
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None

    # Loại bỏ các từ phụ trợ như (date), (month), (year), ThứBa, Thứ Ba...
    clean_s = re.sub(r'\((?:date|month|year)\)', '', s, flags=re.IGNORECASE)
    clean_s = re.sub(r'Thứ\s*[^\s\d]+', '', clean_s, flags=re.IGNORECASE)
    clean_s = clean_s.strip()

    # Tìm giờ phút nếu có (ví dụ: 20:50 hoặc 20.50)
    time_found = None
    time_m = re.search(r'(\d{1,2})[\:\.](\d{2})(?:[\:\.](\d{2}))?', clean_s)
    if time_m:
        h = time_m.group(1).zfill(2)
        m = time_m.group(2)
        sec = time_m.group(3) if time_m.group(3) else "00"
        time_found = f"{h}:{m}:{sec}"

    # Định dạng ISO YYYY-MM-DD
    m_iso = re.search(r'(\d{4})[\/\-\.](\d{2})[\/\-\.](\d{2})', clean_s)
    if m_iso:
        date_iso = f"{m_iso.group(1)}-{m_iso.group(2)}-{m_iso.group(3)}"
        return f"{date_iso} {time_found}" if time_found else date_iso

    # Định dạng: Ngày DD tháng MM năm YYYY
    m_vn = re.search(r'ng[aàá]y\s*(\d{1,2})\s*th[aá]ng\s*(\d{1,2})\s*n[aă]m\s*(\d{4})', clean_s, re.IGNORECASE)
    if m_vn:
        d, m, y = m_vn.group(1).zfill(2), m_vn.group(2).zfill(2), m_vn.group(3)
        date_iso = f"{y}-{m}-{d}"
        return f"{date_iso} {time_found}" if time_found else date_iso

    # Định dạng DD/MM/YYYY hoặc DD-MM-YYYY hoặc DD.MM.YYYY
    m_dmy = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', clean_s)
    if m_dmy:
        d, m, y = m_dmy.group(1).zfill(2), m_dmy.group(2).zfill(2), m_dmy.group(3)
        date_iso = f"{y}-{m}-{d}"
        return f"{date_iso} {time_found}" if time_found else date_iso

    return s


# =====================================================================
# EMPTY TEMPLATES FOR THE 5 CANONICAL SCHEMAS
# =====================================================================

def get_empty_invoice() -> dict:
    return {
        "document_type": "invoice",
        "metadata": {
            "invoice_number": None,
            "serial": None,
            "tax_authority_code": None,
            "issue_date": None
        },
        "seller": {
            "name": None,
            "tax_code": None,
            "address": None,
            "bank_account": None,
            "bank_name": None
        },
        "buyer": {
            "name": None,
            "tax_code": None,
            "address": None,
            "payment_method": None
        },
        "items": [],
        "financials": {
            "subtotal_amount": 0,
            "vat_amount": 0,
            "total_payment": 0,
            "amount_in_words": None
        }
    }


def get_empty_contract() -> dict:
    return {
        "document_type": "contract",
        "metadata": {
            "contract_number": None,
            "contract_title": None,
            "effective_date": None,
            "expiration_date": None
        },
        "party_a": {
            "name": None,
            "tax_code_or_id": None,
            "representative": None,
            "position": None,
            "address": None,
            "phone": None
        },
        "party_b": {
            "name": None,
            "tax_code_or_id": None,
            "representative": None,
            "position": None,
            "address": None,
            "phone": None
        },
        "commercial_terms": {
            "total_value": 0,
            "vat_value": 0,
            "payment_method": None,
            "services_or_scope_summary": None
        }
    }


def get_empty_bank_transfer() -> dict:
    return {
        "document_type": "bank_transfer",
        "transaction_details": {
            "transaction_id": None,
            "amount": 0,
            "currency": "VND",
            "transaction_time": None,
            "status": "Thành công",
            "content": None
        },
        "beneficiary": {
            "account_number": None,
            "account_name": None,
            "bank_name": None
        },
        "remitter": {
            "account_number": None,
            "account_name": None
        }
    }


def get_empty_warehouse_voucher() -> dict:
    return {
        "document_type": "warehouse_voucher",
        "voucher_metadata": {
            "voucher_type": "Xuất kho",
            "voucher_number": None,
            "date": None,
            "debit_account": None,
            "credit_account": None,
            "attached_documents": None
        },
        "stakeholders": {
            "deliverer_or_receiver_name": None,
            "department": None,
            "warehouse_name": None,
            "warehouse_location": None
        },
        "items": [],
        "totals": {
            "total_quantity": 0.0,
            "total_amount": 0,
            "amount_in_words": None
        }
    }


def get_empty_other() -> dict:
    return {
        "document_type": "other",
        "status": "pending_manual_review",
        "title_or_header": None,
        "summary": "Tài liệu chưa được phân loại hoặc không thuộc 4 nhóm chính.",
        "entities": {
            "dates": [],
            "amounts": [],
            "organizations": [],
            "people": [],
            "reference_numbers": []
        }
    }


# =====================================================================
# RULE-BASED EXTRACTION ENGINE (OFFLINE FALLBACK)
# =====================================================================

class RuleBasedExtractor:
    """Bộ trích xuất thuần quy tắc (Regex/Parser), chạy 100% offline không cần API Key."""

    @staticmethod
    def _search_field(full_text: str, label_patterns: List[str], max_lines: int = 2) -> Optional[str]:
        """Tìm giá trị theo nhãn, hỗ trợ cả trường hợp giá trị nằm ở dòng tiếp theo."""
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]
        for idx, line in enumerate(lines):
            for pat in label_patterns:
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    # Kiểm tra xem giá trị có nằm ngay trên dòng đó không
                    val_inline = line[m.end():].strip(" :-")
                    if val_inline and len(val_inline) > 0:
                        return val_inline
                    # Nếu dòng đó chỉ có nhãn, lấy dòng kế tiếp
                    if idx + 1 < len(lines):
                        next_line = lines[idx + 1].strip()
                        if next_line:
                            return next_line
        return None

    @staticmethod
    def extract_invoice(full_text: str, tables: list = None) -> dict:
        data = get_empty_invoice()
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # 1. Metadata
        # Số hóa đơn
        inv_no = RuleBasedExtractor._search_field(full_text, [
            r'Số\s*\(No\.\)\s*[\:\-]?',
            r'Số\s*HĐ\s*[\:\-]?',
            r'Số\s*hóa\s*đơn\s*[\:\-]?',
            r'\bSố\s*[\:\-]\s*'
        ])
        if inv_no:
            m_dig = re.search(r'(\d+)', inv_no)
            if m_dig:
                data["metadata"]["invoice_number"] = m_dig.group(1)

        # Ký hiệu
        serial = RuleBasedExtractor._search_field(full_text, [
            r'Ký\s*hiệu\s*\(Serial\)\s*[\:\-]?',
            r'Ký\s*hiệu\s*[\:\-]?',
            r'Serial\s*[\:\-]?'
        ])
        if serial:
            m_s = re.search(r'([A-Z0-9\/]+)', serial)
            if m_s:
                data["metadata"]["serial"] = m_s.group(1)

        # Mã CQT
        cqt = RuleBasedExtractor._search_field(full_text, [
            r'Mã\s*của\s*cơ\s*quan\s*thuế\s*[\:\-]?',
            r'Mã\s*CQT\s*[\:\-]?'
        ])
        if cqt:
            m_cqt = re.search(r'([A-Z0-9\-]+)', cqt)
            if m_cqt:
                data["metadata"]["tax_authority_code"] = m_cqt.group(1)

        # Ngày hóa đơn
        m_date = re.search(r'ng[aàá]y\s*(?:\([^\)]+\))?\s*(\d{1,2})\s*th[aá]ng\s*(?:\([^\)]+\))?\s*(\d{1,2})\s*n[aă]m\s*(?:\([^\)]+\))?\s*(\d{4})', full_text, re.IGNORECASE)
        if not m_date:
            m_date = re.search(r'ng[aàá]y\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text, re.IGNORECASE)
        if m_date:
            data["metadata"]["issue_date"] = normalize_date(m_date.group(0))

        # 2. Đơn vị bán hàng
        seller_name = RuleBasedExtractor._search_field(full_text, [
            r'Đơn\s*vị\s*bán\s*hàng\s*\(Issued\)\s*[\:\-]?',
            r'Tên\s*đơn\s*vị\s*bán\s*[\:\-]?',
            r'Đơn\s*vị\s*bán\s*[\:\-]?'
        ])
        if seller_name:
            data["seller"]["name"] = seller_name

        seller_tax = RuleBasedExtractor._search_field(full_text, [
            r'Mã\s*số\s*thuế\s*\(Tax\s*code\)\s*[\:\-]?',
            r'Mã\s*số\s*thuế\s*[\:\-]?'
        ])
        if seller_tax:
            m_st = re.search(r'(\d{10}(?:\-\d{3})?)', seller_tax)
            if m_st:
                data["seller"]["tax_code"] = m_st.group(1)

        # 3. Đơn vị mua hàng
        buyer_name = RuleBasedExtractor._search_field(full_text, [
            r'Tên\s*đơn\s*vị\s*\(Company\)\s*[\:\-]?',
            r'Tên\s*đơn\s*vị\s*mua\s*[\:\-]?',
            r'Đơn\s*vị\s*mua\s*hàng\s*[\:\-]?',
            r'Họ\s*tên\s*người\s*mua\s*hàng\s*\(Customer\)\s*[\:\-]?'
        ])
        if buyer_name and buyer_name != "(Customer):":
            buyer_clean = re.sub(r'^(?:Tên\s*đơn\s*vị\s*\(Company\)|Đơn\s*vị\s*mua\s*hàng|Người\s*mua\s*hàng|Bên\s*mua)[\:\s\-]*', '', buyer_name, flags=re.IGNORECASE).strip()
            data["buyer"]["name"] = buyer_clean or buyer_name

        if data["seller"]["name"]:
            seller_clean = re.sub(r'^(?:Đơn\s*vị\s*bán\s*hàng\s*\(Issued\)|Tên\s*đơn\s*vị\s*bán|Đơn\s*vị\s*bán)[\:\s\-]*', '', data["seller"]["name"], flags=re.IGNORECASE).strip()
            data["seller"]["name"] = seller_clean or data["seller"]["name"]

        # Tìm MST thứ 2 trong văn bản (thường là MST bên mua)
        all_msts = re.findall(r'(?:Mã số thuế|Tax code|MST)[^\d]*(\d{10}(?:\-\d{3})?)', full_text, re.IGNORECASE)
        if len(all_msts) >= 2:
            data["seller"]["tax_code"] = all_msts[0]
            data["buyer"]["tax_code"] = all_msts[1]
        elif len(all_msts) == 1 and not data["seller"]["tax_code"]:
            data["seller"]["tax_code"] = all_msts[0]

        # Địa chỉ
        addresses = re.findall(r'(?:Địa\s*chỉ\s*\(Address\)|Địa\s*chỉ)\s*[\:\-]?\s*([^\n]+)', full_text, re.IGNORECASE)
        if len(addresses) >= 1:
            data["seller"]["address"] = addresses[0].strip()
        if len(addresses) >= 2:
            data["buyer"]["address"] = addresses[1].strip()

        # Hình thức thanh toán
        m_pay = RuleBasedExtractor._search_field(full_text, [
            r'Hình\s*thức\s*thanh\s*toán\s*\(Payment\s*method\)\s*[\:\-]?',
            r'Hình\s*thức\s*thanh\s*toán\s*[\:\-]?'
        ])
        if m_pay:
            data["buyer"]["payment_method"] = m_pay

        # 4. Financials
        subtotal = RuleBasedExtractor._search_field(full_text, [
            r'Cộng\s*tiền\s*hàng\s*hóa,\s*dịch\s*vụ\s*\(Invoice\s*total\)\s*[\:\-]?',
            r'Cộng\s*tiền\s*hàng\s*[\:\-]?',
            r'Tổng\s*tiền\s*hàng\s*[\:\-]?'
        ])
        if subtotal:
            data["financials"]["subtotal_amount"] = normalize_number(subtotal) or 0

        # Thuế GTGT: tìm dòng có số tiền thực tế (loại bỏ dòng rỗng)
        vat_matches = re.findall(r'(?:Tổng\s*tiền\s*thuế\s*GTGT|Tiền\s*thuế\s*GTGT)(?:\s*\d+\%)?\s*[\:\-]?\s*([1-9][\d\.\,]+)', full_text, re.IGNORECASE)
        if vat_matches:
            data["financials"]["vat_amount"] = normalize_number(vat_matches[0]) or 0
        else:
            vat_amt = RuleBasedExtractor._search_field(full_text, [
                r'Tổng\s*tiền\s*thuế\s*GTGT\s*[\:\-]?',
                r'Tiền\s*thuế\s*GTGT\s*[\:\-]?'
            ])
            if vat_amt:
                data["financials"]["vat_amount"] = normalize_number(vat_amt) or 0

        total_pay = RuleBasedExtractor._search_field(full_text, [
            r'Tổng\s*cộng\s*tiền\s*thanh\s*toán\s*\(Total\s*payment\)\s*[\:\-]?',
            r'Tổng\s*cộng\s*tiền\s*thanh\s*toán\s*[\:\-]?',
            r'Tổng\s*tiền\s*thanh\s*toán\s*[\:\-]?'
        ])
        if total_pay:
            data["financials"]["total_payment"] = normalize_number(total_pay) or 0

        words = RuleBasedExtractor._search_field(full_text, [
            r'Số\s*tiền\s*viết\s*bằng\s*chữ\s*\(Amount\s*in\s*words\)\s*[\:\-]?',
            r'Số\s*tiền\s*viết\s*bằng\s*chữ\s*[\:\-]?',
            r'Bằng\s*chữ\s*[\:\-]?'
        ])
        if words:
            data["financials"]["amount_in_words"] = words

        # 5. Items từ tables hoặc từ các khối text có cấu trúc
        if tables:
            for tb in tables:
                rows = tb.get("rows", [])
                for idx, r in enumerate(rows, 1):
                    if len(r) >= 4:
                        desc = str(r[1]).strip() if len(r) > 1 else ""
                        if not desc or desc.lower() in ("tên hàng hóa, dịch vụ", "description"):
                            continue
                        unit = str(r[2]).strip() if len(r) > 2 else None
                        qty = normalize_number(r[3]) if len(r) > 3 else 1.0
                        price = normalize_number(r[4]) if len(r) > 4 else 0
                        total = normalize_number(r[-1]) if len(r) > 5 else 0
                        data["items"].append({
                            "item_order": len(data["items"]) + 1,
                            "description": desc,
                            "unit": unit,
                            "quantity": float(qty) if qty is not None else 1.0,
                            "unit_price": price or 0,
                            "vat_rate": "10%",
                            "total_amount": total or 0
                        })

        # Nếu tables rỗng, thử quét text các block dịch vụ/hàng hóa
        if not data["items"]:
            item_blocks = re.findall(r'(\d+)\s*\n([^\n]+(?:\n[^\n]+)?)\s*\nGói\s*\n(\d+)\s*\n([\d\.\,]+)\s*\n([\d\.\,]+)', full_text)
            for itm in item_blocks:
                idx_str, desc_str, q_str, p_str, t_str = itm
                data["items"].append({
                    "item_order": int(idx_str),
                    "description": desc_str.replace('\n', ' ').strip(),
                    "unit": "Gói",
                    "quantity": float(normalize_number(q_str) or 1.0),
                    "unit_price": normalize_number(p_str) or 0,
                    "vat_rate": "10%",
                    "total_amount": normalize_number(t_str) or 0
                })

        return data

    @staticmethod
    def extract_contract(full_text: str, tables: list = None) -> dict:
        data = get_empty_contract()
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # Metadata
        m_title = re.search(r'(HỢP\s+ĐỒNG\s+[^\n]+)', full_text, re.IGNORECASE)
        data["metadata"]["contract_title"] = m_title.group(1).strip() if m_title else "Hợp đồng"

        c_num = RuleBasedExtractor._search_field(full_text, [
            r'Hợp\s*đồng\s*số\s*[\:\-]?',
            r'Số\s*HĐ\s*[\:\-]?',
            r'Mã\s*hợp\s*đồng\s*[\:\-]?'
        ])
        if c_num:
            data["metadata"]["contract_number"] = c_num

        m_date = re.search(r'ng[aàá]y\s*(\d{1,2})\s*th[aá]ng\s*(\d{1,2})\s*n[aă]m\s*(\d{4})', full_text, re.IGNORECASE)
        if m_date:
            data["metadata"]["effective_date"] = normalize_date(m_date.group(0))

        # Parties
        pa_name = RuleBasedExtractor._search_field(full_text, [
            r'Bên\s*thuê\s*dịch\s*vụ\s*\(Bên\s*A\)\s*[\:\-]?',
            r'Bên\s*A\s*[\:\-]?'
        ])
        if pa_name:
            data["party_a"]["name"] = pa_name

        pb_name = RuleBasedExtractor._search_field(full_text, [
            r'Bên\s*cung\s*cấp\s*dịch\s*vụ\s*\(Bên\s*B\)\s*[\:\-]?',
            r'Bên\s*B\s*[\:\-]?'
        ])
        if pb_name:
            data["party_b"]["name"] = pb_name

        reps = re.findall(r'Người\s*đại\s*diện\s*[\:\-]?\s*([^\n\t]+)', full_text, re.IGNORECASE)
        if len(reps) >= 1:
            data["party_a"]["representative"] = reps[0].strip()
        if len(reps) >= 2:
            data["party_b"]["representative"] = reps[1].strip()

        pos = re.findall(r'Chức\s*vụ\s*[\:\-]?\s*([^\n\t]+)', full_text, re.IGNORECASE)
        if len(pos) >= 1:
            data["party_a"]["position"] = pos[0].strip()
        if len(pos) >= 2:
            data["party_b"]["position"] = pos[1].strip()

        # Commercial terms
        val = RuleBasedExtractor._search_field(full_text, [
            r'Tổng\s*cộng\s*thanh\s*toán\s*\(VND\)\s*[\:\-]?',
            r'Tổng\s*cộng\s*thanh\s*toán\s*[\:\-]?',
            r'Tổng\s*giá\s*trị\s*hợp\s*đồng\s*[\:\-]?'
        ])
        if val:
            data["commercial_terms"]["total_value"] = normalize_number(val) or 0

        vat = RuleBasedExtractor._search_field(full_text, [
            r'Thuế\s*VAT\s*[\:\-]?',
            r'Tiền\s*thuế\s*GTGT\s*[\:\-]?'
        ])
        if vat:
            data["commercial_terms"]["vat_value"] = normalize_number(vat) or 0

        data["commercial_terms"]["services_or_scope_summary"] = data["metadata"]["contract_title"]
        return data

    @staticmethod
    def extract_bank_transfer(full_text: str) -> dict:
        data = get_empty_bank_transfer()

        # 1. Số tiền
        # Thử tìm các số tiền có định dạng 308,000 hoặc theo sau VND
        m_amt = re.search(r'([\d\.\,]{3,})\s*(?:VND|VNĐ|đ)', full_text, re.IGNORECASE)
        if not m_amt:
            m_amt = re.search(r'(?:VND|VNĐ|đ)\s*\n\s*([\d\.\,]{3,})', full_text, re.IGNORECASE)
        if not m_amt:
            m_amt = re.search(r'Giao\s*dịch\s*thành\s*công[\!\s\n]+([\d\.\,]{3,})', full_text, re.IGNORECASE)
        if m_amt:
            data["transaction_details"]["amount"] = normalize_number(m_amt.group(1)) or 0

        # 2. Mã giao dịch
        tx_id = RuleBasedExtractor._search_field(full_text, [
            r'Mã\s*giao\s*dịch\s*[\:\-]?',
            r'Mã\s*GD\s*[\:\-]?',
            r'Mã\s*tham\s*chiếu\s*[\:\-]?',
            r'Số\s*tham\s*chiếu\s*[\:\-]?'
        ])
        if tx_id:
            m_clean = re.search(r'([A-Z0-9]+)', tx_id)
            if m_clean:
                data["transaction_details"]["transaction_id"] = m_clean.group(1)

        # 3. Thời gian giao dịch
        m_time = re.search(r'(\d{1,2}[\:\.]\d{2}(?:[\:\.]\d{2})?\s+[^\n\d]*\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text, re.IGNORECASE)
        if not m_time:
            m_time = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}(?:\s+\d{1,2}[\:\.]\d{2})?)', full_text)
        if m_time:
            data["transaction_details"]["transaction_time"] = normalize_date(m_time.group(1))

        # 4. Người nhận / Thụ hưởng
        # Số tài khoản nhận
        acc_recv = RuleBasedExtractor._search_field(full_text, [
            r'Số\s*tài\s*khoản\s*nhận\s*[\:\-]?',
            r'Tài\s*khoản\s*nhận\s*[\:\-]?',
            r'Tài\s*khoản\s*thụ\s*hưởng\s*[\:\-]?'
        ])
        if acc_recv:
            data["beneficiary"]["account_number"] = acc_recv.strip()

        # Tên người nhận
        name_recv = RuleBasedExtractor._search_field(full_text, [
            r'Tên\s*người\s*nhận\s*[\:\-]?',
            r'Tên\s*người\s*thụ\s*hưởng\s*[\:\-]?'
        ])
        if name_recv:
            data["beneficiary"]["account_name"] = name_recv.strip()

        # Ngân hàng nhận
        bank_recv = RuleBasedExtractor._search_field(full_text, [
            r'Ngân\s*hàng\s*(?:\'\s*)?nhận\s*[\:\-]?',
            r'Ngân\s*hàng\s*thụ\s*hưởng\s*[\:\-]?'
        ])
        if bank_recv:
            data["beneficiary"]["bank_name"] = bank_recv.strip()

        # 5. Nội dung chuyển tiền
        content = RuleBasedExtractor._search_field(full_text, [
            r'Nội\s*dung\s*chuyển\s*tiền\s*[\:\-]?',
            r'Nội\s*dung\s*[\:\-]?',
            r'Lời\s*nhắn\s*[\:\-]?'
        ])
        if content:
            data["transaction_details"]["content"] = content.strip()

        return data

    @staticmethod
    def extract_warehouse_voucher(full_text: str, tables: list = None) -> dict:
        data = get_empty_warehouse_voucher()

        if "NHẬP KHO" in full_text.upper() or "NHAP KHO" in full_text.upper():
            data["voucher_metadata"]["voucher_type"] = "Nhập kho"
        else:
            data["voucher_metadata"]["voucher_type"] = "Xuất kho"

        v_no = RuleBasedExtractor._search_field(full_text, [
            r'Mã\s*phiếu\s*[\:\-]?',
            r'Số\s*[\:\-]?',
            r'Phiếu\s*số\s*[\:\-]?'
        ])
        if v_no:
            data["voucher_metadata"]["voucher_number"] = v_no

        m_date = re.search(r'ng[aàá]y\s*(\d{1,2})\s*th[aá]ng\s*(\d{1,2})\s*n[aă]m\s*(\d{4})', full_text, re.IGNORECASE)
        if m_date:
            data["voucher_metadata"]["date"] = normalize_date(m_date.group(0))

        person = RuleBasedExtractor._search_field(full_text, [
            r'Họ\s*và\s*tên\s*người\s*nhận\s*[\:\-]?',
            r'Người\s*nhận\s*hàng\s*[\:\-]?',
            r'Người\s*giao\s*hàng\s*[\:\-]?'
        ])
        if person:
            data["stakeholders"]["deliverer_or_receiver_name"] = person

        wh = RuleBasedExtractor._search_field(full_text, [
            r'Xuất\s*tại\s*kho\s*[\:\-]?',
            r'Nhập\s*tại\s*kho\s*[\:\-]?',
            r'Địa\s*điểm\s*kho\s*[\:\-]?',
            r'Tại\s*kho\s*[\:\-]?'
        ])
        if wh:
            data["stakeholders"]["warehouse_name"] = wh

        tot = RuleBasedExtractor._search_field(full_text, [
            r'Tổng\s*cộng\s*tiền\s*[\:\-]?',
            r'Tổng\s*cộng\s*[\:\-]?',
            r'Thành\s*tiền\s*[\:\-]?'
        ])
        if tot:
            data["totals"]["total_amount"] = normalize_number(tot) or 0

        words = RuleBasedExtractor._search_field(full_text, [
            r'Tổng\s*số\s*tiền\s*viết\s*bằng\s*chữ\s*[\:\-]?',
            r'Bằng\s*chữ\s*[\:\-]?'
        ])
        if words:
            data["totals"]["amount_in_words"] = words

        return data

    @staticmethod
    def extract_other(full_text: str) -> dict:
        data = get_empty_other()
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]
        if lines:
            data["title_or_header"] = lines[0][:150]

        dates = re.findall(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text)
        data["entities"]["dates"] = [normalize_date(d) for d in set(dates) if normalize_date(d)]

        amounts = re.findall(r'([\d\.\,]{4,})\s*(?:VND|VNĐ|đ|đồng)', full_text, re.IGNORECASE)
        clean_amounts = []
        for a in set(amounts):
            num = normalize_number(a)
            if num and num > 0:
                clean_amounts.append(num)
        data["entities"]["amounts"] = clean_amounts

        orgs = re.findall(r'((?:CÔNG TY|TẬP ĐOÀN|DOANH NGHIỆP|CHI NHÁNH|NGÂN HÀNG)[^\n\,\.]{4,60})', full_text, re.IGNORECASE)
        data["entities"]["organizations"] = list(set(o.strip() for o in orgs))[:5]

        return data


# =====================================================================
# MAIN STRUCTURED EXTRACTOR SERVICE
# =====================================================================

class StructuredExtractor:
    """
    Dịch vụ chính điều phối bóc tách dữ liệu theo đúng 5 bộ Schema JSON chuẩn:
    - invoice
    - contract
    - bank_transfer
    - warehouse_voucher
    - other
    """

    def __init__(self):
        self.key_manager = key_manager
        self.model_name = MODEL_NAME or "gemini-2.5-flash"
        self.rule_extractor = RuleBasedExtractor()

    def extract(self, doc_result: dict, target_type: str = None) -> dict:
        """
        Thực hiện trích xuất dữ liệu.
        Nếu target_type chưa được chỉ định, sẽ lấy từ doc_result['document_type'] hoặc 'category'.
        """
        full_text = doc_result.get("full_text", "")
        tables = doc_result.get("tables", [])

        # Xác định document_type hợp lệ
        valid_types = {"invoice", "contract", "bank_transfer", "warehouse_voucher", "other"}
        doc_type = target_type or doc_result.get("document_type") or doc_result.get("category") or "other"

        alias_map = {
            "hoa_don": "invoice",
            "hop_dong": "contract",
            "anh_chuyen_khoan": "bank_transfer",
            "chung_tu": "warehouse_voucher",
            "khac": "other"
        }
        doc_type = alias_map.get(doc_type, doc_type)
        if doc_type not in valid_types:
            doc_type = "other"

        # 1. Thử gọi LLM nếu có API key khả dụng
        if self.key_manager.has_available_keys():
            try:
                llm_data = self._call_llm(full_text, tables, doc_type)
                if llm_data and isinstance(llm_data, dict):
                    return self._enforce_and_clean_schema(llm_data, doc_type)
            except Exception as e:
                print(f"⚠️ [StructuredExtractor] Lỗi khi gọi LLM API ({e}). Tự động fallback sang Rule-based Extractor.")

        # 2. Fallback sang Rule-based Extractor
        return self._extract_rule_based(full_text, tables, doc_type)

    def _extract_rule_based(self, full_text: str, tables: list, doc_type: str) -> dict:
        if doc_type == "invoice":
            res = self.rule_extractor.extract_invoice(full_text, tables)
        elif doc_type == "contract":
            res = self.rule_extractor.extract_contract(full_text, tables)
        elif doc_type == "bank_transfer":
            res = self.rule_extractor.extract_bank_transfer(full_text)
        elif doc_type == "warehouse_voucher":
            res = self.rule_extractor.extract_warehouse_voucher(full_text, tables)
        else:
            res = self.rule_extractor.extract_other(full_text)

        return self._enforce_and_clean_schema(res, doc_type)

    def _call_llm(self, full_text: str, tables: list, doc_type: str) -> Optional[dict]:
        """Gọi Gemini API với prompt bám sát quy tắc và schema người dùng yêu cầu, hỗ trợ xoay vòng key tự động."""
        prompt = f"""
Bạn là chuyên gia trích xuất tài liệu OCR chính xác cao.

### QUY TẮC BẮT BUỘC:
1. Phân loại (document_type): Tự động xác định chính xác một trong các giá trị:
   - "invoice": Hóa đơn GTGT, hóa đơn bán hàng, hóa đơn điện tử.
   - "contract": Hợp đồng kinh tế, dịch vụ, mua bán, phụ lục hợp đồng.
   - "bank_transfer": Ảnh chụp màn hình chuyển khoản ngân hàng, biên lai giao dịch Internet/Mobile Banking.
   - "warehouse_voucher": Phiếu xuất kho, phiếu nhập kho, biên bản giao nhận hàng hóa.
   - "other": Tất cả tài liệu không thuộc 4 nhóm trên hoặc không xác định rõ ràng.

2. Chuẩn hóa dữ liệu:
   - Số tiền/Số lượng: Chuyển về dạng số thuần túy (number), loại bỏ dấu chấm/phẩy phân cách (ví dụ: "308,000" -> 308000; "24.500.000.000" -> 24500000000).
   - Ngày tháng: Chuẩn hóa theo ISO "YYYY-MM-DD" (nếu có giờ thì theo ISO 8601).
   - Trường không tìm thấy: Để giá trị null (hoặc mảng rỗng [] nếu là danh sách).

3. Định dạng đầu ra:
   - Chỉ trả về DUY NHẤT một chuỗi JSON hợp lệ, không bọc thẻ giải thích bên ngoài.

---
Tài liệu được chỉ định là: "{doc_type}"

### DỮ LIỆU ĐẦU VÀO:
VĂN BẢN OCR:
{full_text}

BẢNG BIỂU (NẾU CÓ):
{json.dumps(tables, ensure_ascii=False) if tables else "[]"}
"""
        model_name = self.model_name
        if model_name in ("gemini-3", "gemini-3-flash", "gemini-3.0-flash", "", "gemini-2.5-flash"):
            model_name = "gemini-3.6-flash"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }

        def _do_request(api_key: str):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidate = data.get("candidates", [])[0]
                text_resp = candidate["content"]["parts"][0]["text"].strip()
                if text_resp.startswith("```json"):
                    text_resp = text_resp[7:]
                if text_resp.startswith("```"):
                    text_resp = text_resp[3:]
                if text_resp.endswith("```"):
                    text_resp = text_resp[:-3]
                return json.loads(text_resp.strip())

        return self.key_manager.execute_with_retry(_do_request)

    def _enforce_and_clean_schema(self, data: dict, doc_type: str) -> dict:
        """Kiểm tra và chuẩn hóa triệt để kiểu dữ liệu (numbers, dates, nulls) trong schema."""
        data["document_type"] = doc_type

        def clean_val(v):
            if isinstance(v, dict):
                return {k: clean_val(sub_v) for k, sub_v in v.items()}
            elif isinstance(v, list):
                return [clean_val(item) for item in v]
            elif isinstance(v, str):
                v_strip = v.strip()
                if v_strip.lower() in ("null", "none", "n/a", ""):
                    return None
                return v_strip
            return v

        cleaned = clean_val(data)

        # Enforce number types in items and totals
        if doc_type == "invoice":
            fin = cleaned.get("financials", {})
            for f_key in ["subtotal_amount", "vat_amount", "total_payment"]:
                fin[f_key] = normalize_number(fin.get(f_key)) or 0
            for itm in cleaned.get("items", []):
                itm["quantity"] = float(normalize_number(itm.get("quantity")) or 0.0)
                itm["unit_price"] = normalize_number(itm.get("unit_price")) or 0
                itm["total_amount"] = normalize_number(itm.get("total_amount")) or 0
            if "metadata" in cleaned and cleaned["metadata"].get("issue_date"):
                cleaned["metadata"]["issue_date"] = normalize_date(cleaned["metadata"]["issue_date"])

        elif doc_type == "contract":
            comm = cleaned.get("commercial_terms", {})
            comm["total_value"] = normalize_number(comm.get("total_value")) or 0
            comm["vat_value"] = normalize_number(comm.get("vat_value")) or 0
            if "metadata" in cleaned:
                if cleaned["metadata"].get("effective_date"):
                    cleaned["metadata"]["effective_date"] = normalize_date(cleaned["metadata"]["effective_date"])
                if cleaned["metadata"].get("expiration_date"):
                    cleaned["metadata"]["expiration_date"] = normalize_date(cleaned["metadata"]["expiration_date"])

        elif doc_type == "bank_transfer":
            tx = cleaned.get("transaction_details", {})
            tx["amount"] = normalize_number(tx.get("amount")) or 0
            if tx.get("transaction_time"):
                tx["transaction_time"] = normalize_date(tx.get("transaction_time"))

        elif doc_type == "warehouse_voucher":
            totals = cleaned.get("totals", {})
            totals["total_quantity"] = float(normalize_number(totals.get("total_quantity")) or 0.0)
            totals["total_amount"] = normalize_number(totals.get("total_amount")) or 0
            for itm in cleaned.get("items", []):
                itm["quantity_requested"] = float(normalize_number(itm.get("quantity_requested")) or 0.0)
                itm["quantity_actual"] = float(normalize_number(itm.get("quantity_actual")) or 0.0)
                itm["unit_price"] = normalize_number(itm.get("unit_price")) or 0
                itm["total_amount"] = normalize_number(itm.get("total_amount")) or 0
            if "voucher_metadata" in cleaned and cleaned["voucher_metadata"].get("date"):
                cleaned["voucher_metadata"]["date"] = normalize_date(cleaned["voucher_metadata"]["date"])

        elif doc_type == "other":
            ent = cleaned.get("entities", {})
            ent["amounts"] = [normalize_number(a) for a in ent.get("amounts", []) if normalize_number(a) is not None]
            ent["dates"] = [normalize_date(d) for d in ent.get("dates", []) if normalize_date(d) is not None]

        return cleaned

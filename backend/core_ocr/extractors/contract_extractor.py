import re
from base_extractor import BaseExtractor
from schemas.contract_schema import get_empty_contract_schema

class ContractExtractor(BaseExtractor):
    """
    Extractor bóc tách dữ liệu cấu trúc chuyên biệt cho Hợp đồng (Contract).
    """

    def extract(self, doc_result: dict) -> dict:
        schema = get_empty_contract_schema()
        contract_data = schema["contract"]

        full_text = doc_result.get("full_text", "")
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # 1. Title
        for l in lines[:5]:
            if any(kw in l.upper() for kw in ["HỢP ĐỒNG", "HOP DONG", "BIÊN BẢN", "AGREEMENT"]):
                contract_data["title"] = l
                break

        # 2. Contract Number
        no_match = re.search(r'(?:Mã hợp đồng|Hợp đồng số|Số HĐ|HĐ số|Mã HĐ|Contract No)\s*[\:\-]?\s*([A-Za-z0-9\/\_\-Đđáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ]{3,})', full_text, re.IGNORECASE)
        if not no_match:
            no_match = re.search(r'(\d{4,}\/\d{4}\-[A-Z0-9]+)', full_text)
        if no_match:
            contract_data["contract_number"] = no_match.group(1).strip()

        # 3. Effective & Expiry Dates
        date_match = re.search(r'ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})', full_text, re.IGNORECASE)
        if date_match:
            norm = self.normalize_date(f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}")
            if norm:
                contract_data["effective_date"] = norm["value"]

        exp_match = re.search(r'(?:Hết hạn|Thời hạn hợp đồng đến|Hạn hiệu lực|Hiệu lực đến)\s*[\:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text, re.IGNORECASE)
        if exp_match:
            norm_exp = self.normalize_date(exp_match.group(1))
            if norm_exp:
                contract_data["expiry_date"] = norm_exp["value"]

        # 4. Parties (Bên A, Bên B)
        parties = []
        party_a_match = re.search(r'(?:Bên A|Bên Thuê|Bên Sử Dụng|Party A)\s*(?:\(Bên A\))?\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if party_a_match:
            name_a = party_a_match.group(1).split("\n")[0].strip(" :-")
            tax_a = re.search(r'(?:MST|Mã số thuế)\s*[\:\-]?\s*(\d{10}(?:\-\d{3})?)', full_text, re.IGNORECASE)
            parties.append({
                "role": "Bên A (Bên thuê/mua)",
                "name": name_a,
                "tax_id": tax_a.group(1) if tax_a else ""
            })

        party_b_match = re.search(r'(?:Bên B|Bên Cung Cấp|Bên Bán|Party B)\s*(?:\(Bên B\))?\s*[\:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if party_b_match:
            name_b = party_b_match.group(1).split("\n")[0].strip(" :-")
            parties.append({
                "role": "Bên B (Bên cung cấp/bán)",
                "name": name_b,
                "tax_id": ""
            })
        contract_data["parties"] = parties

        # 5. Contract Value
        total_match = re.search(r'(?:Tổng cộng thanh toán|Tổng giá trị thanh toán|Tổng giá trị|Tổng tiền thanh toán|Tổng giá trị hợp đồng)\s*(?:\(VND\))?\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
        if total_match:
            parsed = self.parse_amount(total_match.group(1), source_type="ocr")
            if parsed:
                contract_data["contract_value"]["total"] = parsed["value"]
                contract_data["contract_value"]["currency"] = "VND"

        vat_match = re.search(r'(?:Tiền thuế GTGT|VAT)\s*[\:\-]?\s*([\d[\.\,]+)', full_text, re.IGNORECASE)
        if vat_match:
            parsed_vat = self.parse_amount(vat_match.group(1), source_type="ocr")
            if parsed_vat:
                contract_data["contract_value"]["vat"] = parsed_vat["value"]

        # 6. Services & Tables
        services = []
        for tbl in doc_result.get("tables", []):
            markdown_tbl = tbl.get("markdown", "")
            if "tên" in markdown_tbl.lower() or "dịch vụ" in markdown_tbl.lower() or "sản phẩm" in markdown_tbl.lower():
                services.append({"description": "Danh mục dịch vụ/sản phẩm theo bảng chi tiết", "details": markdown_tbl})
        
        # Nếu chưa có dịch vụ từ bảng, lọc qua text
        if not services:
            for l in lines:
                if any(kw in l.lower() for kw in ["tên miền", "co-location", "hệ thống", "gói dịch vụ", "cho thuê"]):
                    services.append({"name": l})
        contract_data["services"] = services

        # 7. Articles & Clauses (Quyền & Nghĩa vụ, Chấm dứt, Gia hạn, Tranh chấp...)
        rights_a = []
        rights_b = []
        special_terms = []

        for line in lines:
            if re.match(r'^(?:ĐIỀU|Điều)\s+\d+', line):
                special_terms.append(line)
            if "bên a có quyền" in line.lower() or "trách nhiệm bên a" in line.lower():
                rights_a.append(line)
            if "bên b có quyền" in line.lower() or "trách nhiệm bên b" in line.lower():
                rights_b.append(line)

        contract_data["rights_and_obligations"]["party_a"] = rights_a
        contract_data["rights_and_obligations"]["party_b"] = rights_b
        contract_data["special_terms"] = special_terms

        # 8. Renewal, Suspension, Termination, Dispute
        if "gia hạn" in full_text.lower():
            contract_data["renewal"]["conditions"] = "Hợp đồng có điều khoản về gia hạn tự động hoặc thỏa thuận gia hạn bằng văn bản."
        if "chấm dứt" in full_text.lower() or "hủy bỏ" in full_text.lower():
            contract_data["termination"]["conditions"] = "Hợp đồng quy định chấm dứt khi vi phạm nghĩa vụ hoặc theo thỏa thuận 2 bên."
        if "tranh chấp" in full_text.lower() or "tòa án" in full_text.lower():
            contract_data["dispute_resolution"]["method"] = "Thương lượng, hòa giải hoặc giải quyết tại Tòa án có thẩm quyền tại Việt Nam."

        return schema

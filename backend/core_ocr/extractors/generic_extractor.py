import re
from base_extractor import BaseExtractor
from schemas.generic_schema import get_empty_generic_schema

class GenericExtractor(BaseExtractor):
    """
    Extractor bóc tách dữ liệu cấu trúc cho tài liệu không rõ chủng loại (unknown / generic).
    """

    def extract(self, doc_result: dict) -> dict:
        schema = get_empty_generic_schema()
        g_data = schema["generic"]

        full_text = doc_result.get("full_text", "")
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        if lines:
            g_data["title"] = lines[0]

        # 1. Dates
        dates = re.findall(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', full_text)
        if dates:
            g_data["dates"] = list(set(dates))
            norm = self.normalize_date(dates[0])
            if norm:
                g_data["date"] = norm["value"]

        # 2. Amounts
        amounts = re.findall(r'([\d[\.\,]{4,15})\s*(?:VND|VNĐ|đồng)', full_text, re.IGNORECASE)
        parsed_amts = []
        for amt in set(amounts):
            p = self.parse_amount(amt)
            if p:
                parsed_amts.append(p["value"])
        g_data["amounts"] = parsed_amts

        # 3. Document number
        no_match = re.search(r'(?:Mã tài sản|Mã số|Số hiệu|Số|No\.)\s*[\:\-]?\s*([A-Za-z0-9\/\_\-Đđ]+)', full_text, re.IGNORECASE)
        if no_match:
            g_data["document_number"] = no_match.group(1)

        g_data["description"] = full_text[:200] + ("..." if len(full_text) > 200 else "")

        return schema

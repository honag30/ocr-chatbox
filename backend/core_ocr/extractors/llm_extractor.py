import os
import json
import traceback
from typing import Dict, Any, Tuple

from contract_extractor import ContractExtractor
from invoice_extractor import InvoiceExtractor
from voucher_extractor import VoucherExtractor
from bank_transfer_extractor import BankTransferExtractor
from generic_extractor import GenericExtractor

class LLMExtractor:
    """
    Tích hợp Gemini 2.5 Flash API để phân tích Document Understanding & Structured Extraction.
    Hỗ trợ tự động fallback sang Rule-based Extractors khi không có API Key hoặc gặp sự cố mạng.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.contract_ext = ContractExtractor()
        self.invoice_ext = InvoiceExtractor()
        self.voucher_ext = VoucherExtractor()
        self.bank_ext = BankTransferExtractor()
        self.generic_ext = GenericExtractor()

    def extract(self, doc_result: dict, document_type: str) -> Tuple[dict, dict]:
        """
        Trực tiếp trích xuất dữ liệu cấu trúc dựa theo document_type.
        Trả về tuple: (structured_data, metadata)
        """
        # Nếu có API KEY -> Thử gọi Gemini 2.5 Flash
        if self.api_key:
            try:
                llm_result, meta = self._call_gemini_flash(doc_result, document_type)
                if llm_result:
                    return llm_result, meta
            except Exception as e:
                print(f"⚠️ [LLMExtractor] Lỗi khi gọi Gemini API ({e}). Tự động fallback sang Rule-based Extractor.")

        # Fallback sang Rule-based Engine
        return self._extract_rule_based(doc_result, document_type)

    def _extract_rule_based(self, doc_result: dict, document_type: str) -> Tuple[dict, dict]:
        """
        Engine quy tắc (Rule-based Regex & Parsing) làm fallback đáng tin cậy 100% offline.
        """
        meta = {
            "extractor": "rule_based",
            "model": "rule_based_v1",
            "confidence": 0.90 if document_type != "unknown" else 0.50,
            "warnings": ["Dùng Rule-based Extractor (Offline / Fallback mode)"]
        }

        if document_type == "contract":
            res = self.contract_ext.extract(doc_result)
        elif document_type == "invoice":
            res = self.invoice_ext.extract(doc_result)
        elif document_type == "voucher":
            res = self.voucher_ext.extract(doc_result)
        elif document_type == "bank_transfer":
            res = self.bank_ext.extract(doc_result)
        else:
            res = self.generic_ext.extract(doc_result)

        return res, meta

    def _call_gemini_flash(self, doc_result: dict, document_type: str) -> Tuple[dict, dict]:
        """
        Thực hiện request tới Gemini 2.5 Flash (sử dụng google.genai hoặc google.generativeai nếu được cài đặt).
        """
        full_text = doc_result.get("full_text", "")
        tables = doc_result.get("tables", [])

        prompt = f"""
BẠN LÀ MỘT CHUYÊN GIA TRÍCH XUẤT TÀI LIỆU CHÍNH XÁC (DOCUMENT UNDERSTANDING AGENT).

LOẠI TÀI LIỆU: {document_type.upper()}

NGUYÊN TẮC QUAN TRỌNG NHẤT (HALLUCINATION PREVENTION):
1. CHỈ trích xuất các thông tin CÓ THỰC trong văn bản OCR bên dưới.
2. KHÔNG ĐƯỢC đoán, tự thêm thông tin, tự sửa ngày tháng/mã số thuế/số tiền nếu không có trong văn bản.
3. Nếu một thông tin không xuất hiện trong tài liệu -> Trả về null hoặc "" (hoặc list rỗng []).

NỘI DUNG VĂN BẢN OCR:
{full_text}

DỮ LIỆU BẢNG (NẾU CÓ):
{json.dumps(tables, ensure_ascii=False)}

Hãy trả về kết quả dưới dạng JSON duy nhất đúng theo schema của {document_type}.
"""

        try:
            # Ưu tiên import google.genai hoặc google.generativeai
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt)
                text_resp = response.text
            except ImportError:
                import urllib.request
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    res_json = json.loads(resp.read().decode('utf-8'))
                    text_resp = res_json['candidates'][0]['content']['parts'][0]['text']

            # Clean json output from markdown standard
            clean_json_str = text_resp.replace("```json", "").replace("```", "").strip()
            parsed_json = json.loads(clean_json_str)

            meta = {
                "extractor": "gemini",
                "model": "gemini-2.5-flash",
                "confidence": 0.98,
                "warnings": []
            }
            return parsed_json, meta

        except Exception as e:
            print(f"Lỗi Gemini API execution: {e}")
            return None, {}

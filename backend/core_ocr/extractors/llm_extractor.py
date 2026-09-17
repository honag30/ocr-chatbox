import os
import json
import traceback
from typing import Dict, Any, Tuple

from contract_extractor import ContractExtractor
from invoice_extractor import InvoiceExtractor
from voucher_extractor import VoucherExtractor
from bank_transfer_extractor import BankTransferExtractor
from generic_extractor import GenericExtractor

from schemas.invoice_schema import get_clean_invoice_schema
from schemas.voucher_schema import get_clean_voucher_schema
from schemas.contract_schema import get_clean_contract_schema
from schemas.bank_transfer_schema import get_clean_bank_transfer_schema

class LLMExtractor:
    """
    Tích hợp Gemini Flash API để bóc tách thông tin trọng tâm (Key Information Extraction - KIE)
    xuất ra JSON tinh gọn, chuẩn hóa.
    Hỗ trợ tự động fallback sang Rule-based Extractors khi không có API Key hoặc offline.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")
        self.contract_ext = ContractExtractor()
        self.invoice_ext = InvoiceExtractor()
        self.voucher_ext = VoucherExtractor()
        self.bank_ext = BankTransferExtractor()
        self.generic_ext = GenericExtractor()

    def get_clean_schema_for_type(self, doc_type: str) -> dict:
        """Lấy schema JSON tinh gọn mẫu cho từng loại tài liệu."""
        d = doc_type.lower()
        if d in ["invoice", "hoa_don"]:
            return get_clean_invoice_schema()
        elif d in ["voucher", "chung_tu"]:
            return get_clean_voucher_schema()
        elif d in ["contract", "hop_dong"]:
            return get_clean_contract_schema()
        elif d in ["bank_transfer", "anh_chuyen_khoan"]:
            return get_clean_bank_transfer_schema()
        return {"document_type": doc_type, "data": {}}

    def extract(self, doc_result: dict, document_type: str) -> Tuple[dict, dict]:
        """
        Trực tiếp trích xuất dữ liệu cấu trúc tinh gọn theo document_type.
        Trả về tuple: (clean_structured_data, metadata)
        """
        # Nếu có API KEY -> Thử gọi Gemini Flash
        if self.api_key:
            try:
                llm_result, meta = self._call_gemini_flash(doc_result, document_type)
                if llm_result and "data" in llm_result:
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
            "model": "rule_based_v2_clean",
            "confidence": 0.92 if document_type != "unknown" else 0.50,
            "warnings": ["Sử dụng Rule-based Extractor (Offline / Fallback mode)"]
        }

        d = document_type.lower()
        if d in ["contract", "hop_dong"]:
            res = self.contract_ext.extract(doc_result)
        elif d in ["invoice", "hoa_don"]:
            res = self.invoice_ext.extract(doc_result)
        elif d in ["voucher", "chung_tu"]:
            res = self.voucher_ext.extract(doc_result)
        elif d in ["bank_transfer", "anh_chuyen_khoan"]:
            res = self.bank_ext.extract(doc_result)
        else:
            res = self.generic_ext.extract(doc_result)

        return res, meta

    def _call_gemini_flash(self, doc_result: dict, document_type: str) -> Tuple[dict, dict]:
        """
        Thực hiện trích xuất có cấu trúc qua Gemini Flash API.
        """
        full_text = doc_result.get("full_text", "")
        tables = doc_result.get("tables", [])
        clean_schema = self.get_clean_schema_for_type(document_type)

        system_instruction = (
            "BẠN LÀ MỘT HỆ THỐNG TRÍCH XUẤT DỮ LIỆU TÀI LIỆU DOANH NGHIỆP CỰC KỲ CHÍNH XÁC (KEY INFORMATION EXTRACTION).\n"
            "NHIỆM VỤ: Bóc tách văn bản OCR thành 1 bản JSON duy nhất chỉ chứa các thông tin quan trọng.\n"
            "NGUYÊN TẮC BẮT BUỘC:\n"
            "1. Chỉ trích xuất thông tin CÓ THẬT trong văn bản. Không bịa đặt hoặc tự tính toán sai lệch.\n"
            "2. Chuẩn hóa ngày tháng về định dạng ISO YYYY-MM-DD (nếu có).\n"
            "3. Chuẩn hóa số tiền về kiểu số nguyên hoặc số thực (không để dấu chấm phân cách dạng string, ví dụ: 1540000000).\n"
            "4. Nếu thông tin không có trong tài liệu, để null hoặc chuỗi rỗng \"\" hoặc danh sách rỗng [].\n"
            "5. CHỈ TRẢ VỀ DUY NHẤT MÃ JSON HỢP LỆ, TUÂN THEO SCHEMA ĐƯỢC CHỈ ĐỊNH."
        )

        user_prompt = f"""
LOẠI TÀI LIỆU CẦN TRÍCH XUẤT: {document_type.upper()}

HÃY ĐIỀN DỮ LIỆU VÀO ĐÚNG SCHEMA MẪU SAU ĐÂY:
```json
{json.dumps(clean_schema, ensure_ascii=False, indent=2)}
```

NỘI DUNG VĂN BẢN OCR:
{full_text}

BẢNG BIỂU PHÁT HIỆN ĐƯỢC (NẾU CÓ):
{json.dumps(tables, ensure_ascii=False)}
"""

        text_resp = None
        raw_keys = self.api_key.split(",")
        keys = [k.strip() for k in raw_keys if k.strip()]

        from openai import OpenAI

        for k in keys:
            try:
                client = OpenAI(
                    api_key=k,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                text_resp = response.choices[0].message.content
                if text_resp:
                    break
            except Exception as client_err:
                print(f"⚠️ [LLMExtractor] Key '{k[:8]}...' lỗi ({client_err}). Đang chuyển key tiếp theo...")
                continue

        if not text_resp:
            return None, {}

        # Làm sạch JSON string
        clean_json_str = text_resp.replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(clean_json_str)

        # Đảm bảo có key data và document_type
        if "data" not in parsed_json and any(k in parsed_json for k in ["so_hoa_don", "so_hop_dong", "so_chung_tu", "so_tien"]):
            parsed_json = {
                "document_type": document_type,
                "data": parsed_json
            }

        meta = {
            "extractor": "gemini",
            "model": self.model_name,
            "confidence": 0.98,
            "warnings": []
        }
        return parsed_json, meta

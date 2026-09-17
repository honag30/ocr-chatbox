from openai import OpenAI
try:
    from config import GEMINI_API_KEY, MODEL_NAME
except ImportError:
    from backend.config import GEMINI_API_KEY, MODEL_NAME


class AIService:

    def __init__(self):
        raw_keys = (GEMINI_API_KEY or "").split(",")
        self.keys = [k.strip() for k in raw_keys if k.strip()]
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

    def _call_with_retry(self, messages, temperature=0.2):
        """Thử gọi qua các API Key cho đến khi thành công."""
        last_err = None
        for i, key in enumerate(self.keys):
            try:
                client = OpenAI(api_key=key, base_url=self.base_url)
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    temperature=temperature
                )
                return response.choices[0].message.content
            except Exception as e:
                masked_key = key[:8] + "..." if len(key) > 8 else "***"
                print(f"[AIService] Key {masked_key} gặp lỗi ({e}). Đang thử key tiếp theo...")
                last_err = e
                continue

        # Nếu toàn bộ key đều lỗi (do 429 quota rate limit)
        err_msg = str(last_err) if last_err else "API Gemini lỗi"
        print(f"[AIService] ⚠️ Toàn bộ API keys đều hết quota: {err_msg}")
        return f"⚠️ [Hệ thống tạm thời đạt giới hạn API Gemini (429 Rate Limit)]: Vui lòng thử lại sau ít phút hoặc cấu hình thêm API Key. ({err_msg[:120]})"

    def chat(self, messages, system_instruction=None):
        """Gửi hội thoại tới Gemini API và nhận phản hồi."""
        system_content = system_instruction or (
            "Bạn là trợ lý AI thông minh chuyên nghiệp. "
            "Bạn có khả năng phân tích, tóm tắt tài liệu (PDF, Word, Excel, Ảnh, Hợp đồng, Hóa đơn, Chứng từ) "
            "và trả lời câu hỏi của người dùng một cách chính xác, rõ ràng, bằng tiếng Việt."
        )

        full_messages = [
            {"role": "system", "content": system_content},
            *messages
        ]

        return self._call_with_retry(full_messages)

    def summarize_document(self, doc_context: str, user_instruction: str = None) -> str:
        """Tạo bản tóm tắt chi tiết, có cấu trúc từ nội dung và bảng biểu của tài liệu đã trích xuất."""
        custom_part = ""
        if user_instruction and user_instruction.strip():
            custom_part = f"\n\n[YÊU CẦU ĐẶC BIỆT TỪ NGƯỜI DÙNG]: {user_instruction.strip()}"

        prompt = (
            "Dưới đây là thông tin và toàn bộ nội dung trích xuất (văn bản & bảng biểu) từ một tài liệu upload:\n\n"
            f"{doc_context}\n"
            f"{custom_part}\n\n"
            "Hãy phân tích và tóm tắt tài liệu trên theo cấu trúc Markdown rõ ràng, chuyên nghiệp:\n"
            "1. 📌 **Tổng quan tài liệu**: Tên tài liệu, danh mục/loại văn bản, dung lượng/số trang.\n"
            "2. 🎯 **Mục đích & Nội dung chính**: Tóm tắt ngắn gọn mục đích chính và nội dung bao quát.\n"
            "3. 🔍 **Thông tin quan trọng / Then chốt**:\n"
            "   - Các bên liên quan (Bên A, Bên B, người bán, người mua... nếu có)\n"
            "   - Giá trị hợp đồng / Số tiền thanh toán / Thuế VAT / Tổng cộng (nếu có số liệu tài chính)\n"
            "   - Thời hạn, ngày ký kết, ngày hiệu lực / ngày đến hạn\n"
            "   - Các quyền, nghĩa vụ hoặc điều khoản cốt lõi\n"
            "4. 📊 **Số liệu & Bảng biểu nổi bật** (Tóm tắt lại các mục quan trọng từ bảng nếu tài liệu có bảng)\n"
            "5. ⚠️ **Lưu ý / Ràng buộc quan trọng** (nếu có)\n\n"
            "Lưu ý: Trình bày đẹp mắt, dùng bullet points, in đậm các từ khóa/số liệu quan trọng để người đọc nắm bắt nhanh nhất."
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "Bạn là chuyên gia phân tích và tóm tắt tài liệu doanh nghiệp, pháp lý, kế toán và hành chính. "
                    "Bạn luôn đưa ra bản tóm tắt súc tích, chính xác theo đúng sự thật trong tài liệu, không bịa đặt số liệu."
                )
            },
            {"role": "user", "content": prompt}
        ]

        return self._call_with_retry(messages)

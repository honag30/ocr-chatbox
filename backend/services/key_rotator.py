import os
import re
import time
import json
import logging
import threading
from typing import List, Optional, Callable, Any, Dict, Tuple

logger = logging.getLogger("KeyRotator")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")


def mask_key(key: str) -> str:
    """Ẩn bớt ký tự của key để bảo mật khi log hoặc gửi qua client."""
    if not key:
        return "<empty>"
    clean = key.strip()
    if len(clean) <= 8:
        return clean[:2] + "..." + clean[-2:]
    return clean[:6] + "..." + clean[-4:]


class AllAPIKeysExhaustedError(Exception):
    """Ngoại lệ ném ra khi tất cả các API Key đều không khả dụng (hết hạn hoặc vượt quá quota)."""
    pass


class KeyState:
    """Lưu trữ trạng thái và chỉ số sử dụng của từng API Key."""

    def __init__(self, key: str, index: int):
        self.key = key.strip()
        self.index = index
        self.is_valid = True
        self.cooldown_until = 0.0
        self.success_count = 0
        self.failure_count = 0
        self.last_error = ""
        self.last_used = 0.0

    def is_available(self, now: Optional[float] = None) -> bool:
        if not self.is_valid:
            return False
        if now is None:
            now = time.time()
        return now >= self.cooldown_until

    def to_dict(self) -> dict:
        now = time.time()
        in_cooldown = now < self.cooldown_until
        return {
            "index": self.index,
            "masked_key": mask_key(self.key),
            "is_valid": self.is_valid,
            "in_cooldown": in_cooldown,
            "cooldown_remaining_sec": max(0, int(self.cooldown_until - now)) if in_cooldown else 0,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_error": self.last_error,
            "last_used_timestamp": self.last_used
        }


class KeyManager:
    """
    Trình quản lý và xoay vòng API Key thông minh:
    - Hỗ trợ danh sách nhiều API Keys (từ chuỗi phân cách bởi dấu phẩy, chấm phẩy hoặc mảng).
    - Phân phối yêu cầu theo cơ chế Round-Robin để cân bằng tải (tránh chạm giới hạn RPM).
    - Tự động phát hiện lỗi Key hết hạn / không hợp lệ (400 API_KEY_INVALID, 401, 403) và loại bỏ.
    - Tự động phát hiện lỗi chạm giới hạn quota (429, RESOURCE_EXHAUSTED) và đưa vào thời gian chờ Cooldown (60s).
    - Tự động xoay sang key kế tiếp và retry ngay lập tức khi xảy ra lỗi.
    - An toàn luồng (Thread-safe).
    """

    def __init__(self, raw_keys: Optional[Any] = None, default_cooldown: int = 60):
        self.default_cooldown = default_cooldown
        self._lock = threading.RLock()
        self._current_index = 0
        self.keys: List[KeyState] = []

        self._env_files = [
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        ]
        try:
            from dotenv import load_dotenv
            for env_path in self._env_files:
                if os.path.isfile(env_path):
                    load_dotenv(env_path, override=False)
        except Exception:
            pass

        self._last_env_mtime = 0.0

        self.reload_keys(raw_keys)

    def _check_and_reload_env_if_changed(self):
        """Tự động kiểm tra file .env, nếu người dùng sửa đổi keys thì hot-reload ngay mà không cần khởi động lại server."""
        try:
            for p in self._env_files:
                if os.path.isfile(p):
                    mtime = os.path.getmtime(p)
                    if self._last_env_mtime == 0.0:
                        self._last_env_mtime = mtime
                    elif mtime > self._last_env_mtime:
                        self._last_env_mtime = mtime
                        try:
                            from dotenv import load_dotenv
                            load_dotenv(p, override=True)
                        except Exception:
                            pass
                        logger.info(f"🔄 [KeyManager] Phát hiện thay đổi trong file {p}. Đang hot-reload API keys...")
                        self.reload_keys()
                        return
        except Exception:
            return

    def _parse_keys(self, raw_keys: Any) -> List[str]:
        """Tách và chuẩn hóa danh sách keys từ nhiều định dạng đầu vào."""
        if raw_keys is None:
            raw_keys = (
                os.getenv("GEMINI_API_KEYS")
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or ""
            )

        key_list = []
        if isinstance(raw_keys, (list, tuple, set)):
            candidates = [str(k).strip() for k in raw_keys]
        elif isinstance(raw_keys, str):
            candidates = [k.strip() for k in re.split(r'[,;\n\r]+', raw_keys)]
        else:
            candidates = [str(raw_keys).strip()]

        for c in candidates:
            c = c.strip('\'" \t')
            if c and c not in key_list:
                key_list.append(c)

        return key_list

    def reload_keys(self, raw_keys: Optional[Any] = None):
        """Khởi tạo hoặc tải lại danh sách API Keys."""
        with self._lock:
            key_strings = self._parse_keys(raw_keys)
            self.keys = [KeyState(k, i) for i, k in enumerate(key_strings)]
            self._current_index = 0

            if self.keys:
                masked_list = [mask_key(k.key) for k in self.keys]
                logger.info(f"🔄 [KeyManager] Đã tải {len(self.keys)} API Keys: {masked_list}")
            else:
                logger.warning("⚠️ [KeyManager] Không tìm thấy API Key nào trong cấu hình!")

    def has_available_keys(self) -> bool:
        """Kiểm tra xem còn ít nhất một key hợp lệ hay không."""
        self._check_and_reload_env_if_changed()
        with self._lock:
            return any(k.is_valid for k in self.keys)

    def get_active_key(self, advance: bool = True) -> Optional[str]:
        """
        Lấy API key sẵn sàng hoạt động tiếp theo theo cơ chế Round-Robin.
        Nếu advance=True, con trỏ sẽ dịch chuyển sang key tiếp theo sau khi lấy.
        """
        self._check_and_reload_env_if_changed()
        with self._lock:
            if not self.keys:
                return None

            now = time.time()
            total = len(self.keys)

            for offset in range(total):
                idx = (self._current_index + offset) % total
                candidate = self.keys[idx]
                if candidate.is_available(now):
                    candidate.last_used = now
                    if advance:
                        self._current_index = (idx + 1) % total
                    return candidate.key

            valid_keys = [k for k in self.keys if k.is_valid]
            if not valid_keys:
                logger.error("❌ [KeyManager] Tất cả API Keys đều đã bị đánh dấu vô hiệu / hết hạn!")
                return None

            earliest_key = min(valid_keys, key=lambda k: k.cooldown_until)
            wait_time = max(0.0, earliest_key.cooldown_until - now)
            logger.warning(
                f"⏳ [KeyManager] Toàn bộ {len(valid_keys)} keys hợp lệ đang cooldown. Sử dụng key "
                f"{mask_key(earliest_key.key)} (còn chờ ~{int(wait_time)}s)."
            )
            earliest_key.last_used = now
            return earliest_key.key

    def mark_rate_limited(self, key: str, cooldown_seconds: Optional[int] = None, reason: str = ""):
        """Đánh dấu key bị Rate limit / Quota Exceeded và đưa vào Cooldown."""
        cooldown = cooldown_seconds if cooldown_seconds is not None else self.default_cooldown
        with self._lock:
            for k in self.keys:
                if k.key == key:
                    k.cooldown_until = time.time() + cooldown
                    k.failure_count += 1
                    k.last_error = f"Rate limited: {reason}"
                    active_count = sum(1 for item in self.keys if item.is_available())
                    logger.warning(
                        f"⚠️ [KeyManager] Key [{mask_key(key)}] bị giới hạn (429/Quota: {reason}). Tạm nghỉ "
                        f"{cooldown}s. Còn {active_count}/{len(self.keys)} keys sẵn sàng."
                    )
                    break

    def mark_invalid(self, key: str, reason: str = ""):
        """Đánh dấu key hết hạn hoặc vĩnh viễn không hợp lệ (400, 401, 403)."""
        with self._lock:
            for k in self.keys:
                if k.key == key:
                    k.is_valid = False
                    k.failure_count += 1
                    k.last_error = f"Invalid/Expired: {reason}"
                    valid_remaining = sum(1 for item in self.keys if item.is_valid)
                    logger.error(
                        f"❌ [KeyManager] Key [{mask_key(key)}] hết hạn hoặc không hợp lệ: {reason}. Đã loại bỏ key. Còn "
                        f"{valid_remaining}/{len(self.keys)} keys hợp lệ."
                    )
                    break

    def mark_success(self, key: str):
        """Ghi nhận yêu cầu thành công cho key."""
        with self._lock:
            for k in self.keys:
                if k.key == key:
                    k.success_count += 1
                    k.failure_count = 0
                    k.last_error = ""
                    break

    def classify_error(self, e: Exception) -> Tuple[str, str]:
        """
        Phân loại lỗi từ API:
        - 'INVALID_KEY': key sai, hết hạn, bị thu hồi.
        - 'RATE_LIMITED': chạm quota 429, resource exhausted.
        - 'TRANSIENT': timeout, lỗi kết nối tạm thời.
        - 'OTHER': lỗi khác (logic, prompt, code).
        """
        err_msg = str(e)
        status_code = getattr(e, "status_code", None)
        if status_code is None and hasattr(e, "code"):
            status_code = getattr(e, "code")

        if hasattr(e, "read"):
            try:
                body = e.read().decode("utf-8", errors="ignore")
                err_msg += f" | Body: {body}"
            except Exception:
                pass

        err_lower = err_msg.lower()

        if (
            status_code in (401, 403)
            or "api_key_invalid" in err_lower
            or "api key not valid" in err_lower
            or "permission_denied" in err_lower
            or "key expired" in err_lower
            or "invalid_api_key" in err_lower
            or ("400" in err_lower and ("api key" in err_lower or "api_key" in err_lower))
        ):
            return "INVALID_KEY", err_msg

        if (
            status_code == 429
            or "429" in err_lower
            or "resource_exhausted" in err_lower
            or "quota" in err_lower
            or "rate limit" in err_lower
            or "too many requests" in err_lower
        ):
            return "RATE_LIMITED", err_msg

        if (
            "timed out" in err_lower
            or "timeout" in err_lower
            or "connection reset" in err_lower
            or "temporarily unavailable" in err_lower
            or status_code in (502, 503, 504)
        ):
            return "TRANSIENT", err_msg

        if (
            status_code == 404
            or "not found" in err_lower
            or "no longer available" in err_lower
        ):
            return "MODEL_ERROR", err_msg

        return "OTHER", err_msg

    def execute_with_retry(
        self,
        func: Callable[[str], Any],
        max_attempts: Optional[int] = None,
        cooldown_on_limit: int = 60
    ) -> Any:
        """
        Thực thi một hàm với cơ chế tự động xoay vòng key khi gặp sự cố:
        - Gọi `func(api_key)`
        - Nếu gặp lỗi 429/Quota: Đưa key vào cooldown, tự động chuyển sang key khác và thử lại.
        - Nếu gặp lỗi Key Hết Hạn / Sai: Vô hiệu hóa key, tự động chuyển sang key khác và thử lại.
        - Thử lại cho tới khi thành công hoặc tất cả keys đều thất bại.
        """
        self._check_and_reload_env_if_changed()
        with self._lock:
            total_keys = len(self.keys)

        if total_keys == 0:
            raise AllAPIKeysExhaustedError("Không có API Key nào được cấu hình trong hệ thống.")

        attempts = 0
        limit_attempts = max_attempts if max_attempts else max(total_keys * 2, 3)
        tried_keys = set()
        last_exception = None

        while attempts < limit_attempts:
            key = self.get_active_key(advance=True)
            if not key:
                break

            tried_keys.add(key)
            attempts += 1

            try:
                result = func(key)
                self.mark_success(key)
                return result
            except Exception as e:
                last_exception = e
                err_type, reason = self.classify_error(e)

                if err_type == "INVALID_KEY":
                    self.mark_invalid(key, reason=reason)
                elif err_type == "RATE_LIMITED":
                    self.mark_rate_limited(key, cooldown_seconds=cooldown_on_limit, reason=reason)
                elif err_type == "TRANSIENT":
                    logger.warning(f"⚠️ [KeyManager] Lỗi mạng tạm thời với key [{mask_key(key)}]: {reason}. Thử key khác.")
                elif err_type == "MODEL_ERROR":
                    logger.error(f"❌ [KeyManager] Model không tồn tại hoặc tài khoản không hỗ trợ model này ({reason}).")
                    raise ValueError(
                        f"Model AI không tồn tại hoặc không hỗ trợ tài khoản này ({reason}). "
                        "Vui lòng thiết lập MODEL_NAME=gemini-3.6-flash trong file .env."
                    )
                else:
                    logger.error(f"❌ [KeyManager] Lỗi không liên quan tới key ({type(e).__name__}): {e}")
                    raise

                with self._lock:
                    if not self.has_available_keys():
                        break

        error_details = f"Đã thử qua {len(tried_keys)}/{total_keys} keys. Lỗi cuối cùng: {last_exception}"
        logger.error(f"💥 [KeyManager] Tất cả API Keys đều thất bại! {error_details}")
        raise AllAPIKeysExhaustedError(
            f"Tất cả các API Keys đều đã hết hạn hoặc chạm ngưỡng giới hạn (quota exceeded). {error_details}"
        ) from last_exception

    def get_status(self) -> dict:
        """Trả về thống kê chi tiết trạng thái của toàn bộ API keys."""
        self._check_and_reload_env_if_changed()
        with self._lock:
            now = time.time()
            valid_keys = [k for k in self.keys if k.is_valid]
            available_keys = [k for k in valid_keys if now >= k.cooldown_until]
            cooldown_keys = [k for k in valid_keys if now < k.cooldown_until]
            invalid_keys = [k for k in self.keys if not k.is_valid]

            return {
                "total_keys": len(self.keys),
                "active_keys": len(available_keys),
                "cooldown_keys": len(cooldown_keys),
                "invalid_keys": len(invalid_keys),
                "current_pointer_index": self._current_index,
                "keys": [k.to_dict() for k in self.keys]
            }


key_manager = KeyManager()

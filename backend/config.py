import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

# Load .env từ thư mục gốc dự án hoặc backend
load_dotenv(os.path.join(ROOT_DIR, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

CORE_OCR_DIR = os.path.join(BASE_DIR, "core_ocr")
STORAGE_DIR = os.getenv("STORAGE_DIR", os.path.join(ROOT_DIR, "storage"))

# Thư mục lưu trữ tài liệu duy nhất trong storage/
DOC_DIR = os.getenv("DOC_DIR", os.path.join(STORAGE_DIR, "doc"))

# Alias đảm bảo tương thích ngược
UPLOAD_DIR = DOC_DIR
INPUT_DIR = DOC_DIR
OUTPUT_DIR = DOC_DIR

TEST_OCR_DIR = ROOT_DIR

# Đảm bảo thư mục lưu trữ tồn tại
for d in [STORAGE_DIR, DOC_DIR]:
    os.makedirs(d, exist_ok=True)

# Quản lý và xoay vòng API Keys
try:
    from services.key_rotator import key_manager, KeyManager
except ImportError:
    from backend.services.key_rotator import key_manager, KeyManager

GEMINI_API_KEYS = [k.key for k in key_manager.keys]
GEMINI_API_KEY = key_manager.get_active_key(advance=False) or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
raw_model = os.getenv("MODEL_NAME", "gemini-3.6-flash").strip()
if raw_model in ("gemini-3", "gemini-3-flash", "gemini-3.0-flash", "", "gemini-2.5-flash"):
    MODEL_NAME = "gemini-3.6-flash"
else:
    MODEL_NAME = raw_model

def get_gemini_api_key() -> str:
    """Lấy API key tiếp theo từ KeyManager với cơ chế xoay vòng."""
    return key_manager.get_active_key(advance=True) or GEMINI_API_KEY

# MySQL Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "")

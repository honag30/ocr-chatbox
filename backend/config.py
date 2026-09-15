import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

# Load .env từ thư mục gốc dự án hoặc backend
load_dotenv(os.path.join(ROOT_DIR, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

CORE_OCR_DIR = os.path.join(BASE_DIR, "core_ocr")
STORAGE_DIR = os.getenv("STORAGE_DIR", os.path.join(ROOT_DIR, "storage"))

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(STORAGE_DIR, "uploads"))
DOC_DIR = os.getenv("DOC_DIR", os.path.join(STORAGE_DIR, "doc"))
INPUT_DIR = os.getenv("INPUT_DIR", os.path.join(STORAGE_DIR, "input"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(STORAGE_DIR, "ocr_outputs"))

TEST_OCR_DIR = ROOT_DIR

# Đảm bảo các thư mục tồn tại
for d in [STORAGE_DIR, UPLOAD_DIR, DOC_DIR, INPUT_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")

# MySQL Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "")

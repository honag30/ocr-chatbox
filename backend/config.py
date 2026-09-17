import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

# Load .env từ thư mục gốc dự án hoặc backend
load_dotenv(os.path.join(ROOT_DIR, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

CORE_OCR_DIR = os.path.join(BASE_DIR, "core_ocr")

# Thư mục tiếp nhận upload tạm thời (không lưu trữ cố định trong folder storage)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(ROOT_DIR, "uploads"))
DOC_DIR = UPLOAD_DIR
INPUT_DIR = UPLOAD_DIR
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(ROOT_DIR, "output"))

TEST_OCR_DIR = ROOT_DIR

# Đảm bảo thư mục upload và output cần thiết tồn tại
for d in [UPLOAD_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.6-flash")

# MySQL Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "chatbox")

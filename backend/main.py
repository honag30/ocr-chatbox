import os
import sys

# Đảm bảo console và server luôn encode UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Thêm thư mục backend và root vào sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
for p in (BASE_DIR, ROOT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.health_router import router as health_router
from api.chat_router import router as chat_router
from api.document_router import router as document_router
from db.models import init_db

app = FastAPI(
    title="AI Document Chatbox System API",
    description="Backend Clean Architecture API kết nối Gemini AI & Core OCR Engine",
    version="2.0.0"
)

# Kích hoạt CORS cho Frontend UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(document_router)


@app.on_event("startup")
def on_startup():
    try:
        init_db()
    except Exception as e:
        print(f"[Main] Cảnh báo khởi tạo CSDL: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, timeout_keep_alive=120)

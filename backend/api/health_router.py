from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/api/health")
def health_check():
    return {"status": "ok", "service": "AI Document Chatbox API"}

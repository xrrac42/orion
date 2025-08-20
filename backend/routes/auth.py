from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def auth_status():
    """Status da autenticação"""
    return {"status": "authenticated", "message": "Auth endpoint ready"}

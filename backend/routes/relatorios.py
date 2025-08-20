from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_relatorios():
    """Endpoint de relatórios"""
    return {"message": "Relatórios endpoint ready"}

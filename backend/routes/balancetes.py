from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Modelos Pydantic
class BalanceteCreate(BaseModel):
    cliente_id: str
    ano: int
    mes: int
    total_receitas: float
    total_despesas: float

class BalanceteResponse(BaseModel):
    id: str
    cliente_id: str
    ano: int
    mes: int
    total_receitas: float
    total_despesas: float
    lucro_bruto: float
    created_at: Optional[str] = None

@router.get("/cliente/{cliente_id}", response_model=List[BalanceteResponse])
async def get_balancetes_cliente(cliente_id: str):
    """Buscar balancetes de um cliente"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('balancetes')\
                          .select('*')\
                          .eq('cliente_id', cliente_id)\
                          .order('ano', desc=True)\
                          .order('mes', desc=True)\
                          .execute()
        
        if response.data is None:
            return []
            
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar balancetes do cliente {cliente_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/", response_model=BalanceteResponse)
async def create_balancete(balancete: BalanceteCreate):
    """Criar novo balancete"""
    try:
        supabase = get_supabase_client()
        
        # Verificar se cliente existe
        cliente_response = supabase.table('clientes')\
                                  .select('id')\
                                  .eq('id', balancete.cliente_id)\
                                  .execute()
        
        if not cliente_response.data or len(cliente_response.data) == 0:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        # Verificar se já existe balancete para esse período
        existing = supabase.table('balancetes')\
                          .select('id')\
                          .eq('cliente_id', balancete.cliente_id)\
                          .eq('ano', balancete.ano)\
                          .eq('mes', balancete.mes)\
                          .execute()
        
        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=400, detail="Já existe balancete para este período")
        
        # Calcular lucro bruto
        lucro_bruto = balancete.total_receitas - balancete.total_despesas
        
        # Criar balancete
        balancete_data = balancete.dict()
        balancete_data['lucro_bruto'] = lucro_bruto
        
        response = supabase.table('balancetes')\
                          .insert(balancete_data)\
                          .execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=400, detail="Erro ao criar balancete")
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar balancete: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{balancete_id}", response_model=BalanceteResponse)
async def get_balancete(balancete_id: str):
    """Buscar balancete por ID"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('balancetes')\
                          .select('*')\
                          .eq('id', balancete_id)\
                          .single()\
                          .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Balancete não encontrado")
        
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar balancete {balancete_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.delete("/{balancete_id}")
async def delete_balancete(balancete_id: str):
    """Excluir balancete"""
    try:
        supabase = get_supabase_client()
        
        # Verificar se balancete existe
        existing = supabase.table('balancetes')\
                          .select('id')\
                          .eq('id', balancete_id)\
                          .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="Balancete não encontrado")
        
        # Excluir balancete
        response = supabase.table('balancetes')\
                          .delete()\
                          .eq('id', balancete_id)\
                          .execute()
        
        return {"message": "Balancete excluído com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao excluir balancete {balancete_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

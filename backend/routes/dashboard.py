from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from database import get_supabase_client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/stats")
async def get_dashboard_stats() -> Dict[str, Any]:
    """Buscar estatísticas do dashboard"""
    try:
        supabase = get_supabase_client()
        
        # Contar clientes
        clientes_response = supabase.table('clientes')\
                                   .select('*', count='exact')\
                                   .execute()
        total_clientes = clientes_response.count or 0
        
        # Contar balancetes
        balancetes_response = supabase.table('balancetes')\
                                     .select('*', count='exact')\
                                     .execute()
        total_balancetes = balancetes_response.count or 0
        
        # Calcular receitas e despesas totais
        if total_balancetes > 0:
            balancetes_data = supabase.table('balancetes')\
                                     .select('total_receitas, total_despesas, lucro_bruto')\
                                     .execute()
            
            receitas_totais = sum(b['total_receitas'] for b in balancetes_data.data or [])
            despesas_totais = sum(b['total_despesas'] for b in balancetes_data.data or [])
            lucro_total = sum(b['lucro_bruto'] for b in balancetes_data.data or [])
        else:
            receitas_totais = 0
            despesas_totais = 0
            lucro_total = 0
        
        return {
            "total_clientes": total_clientes,
            "total_balancetes": total_balancetes,
            "receitas_totais": receitas_totais,
            "despesas_totais": despesas_totais,
            "lucro_total": lucro_total
        }
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas do dashboard: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/recent-activity")
async def get_recent_activity():
    """Buscar atividades recentes"""
    try:
        supabase = get_supabase_client()
        
        # Buscar balancetes recentes com dados do cliente
        response = supabase.table('balancetes')\
                          .select('*, clientes(nome)')\
                          .order('created_at', desc=True)\
                          .limit(10)\
                          .execute()
        
        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao buscar atividades recentes: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

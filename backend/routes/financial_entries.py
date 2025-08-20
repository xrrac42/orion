from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging
from datetime import date

router = APIRouter()
logger = logging.getLogger(__name__)

class FinancialEntryResponse(BaseModel):
    id: int
    client_id: str
    report_date: date
    main_group: str
    subgroup_1: Optional[str]
    specific_account: str
    movement_type: str
    period_value: float
    original_data: Optional[dict]
    created_at: Optional[str]

@router.get("/cliente/{client_id}", response_model=List[FinancialEntryResponse])
async def get_financial_entries_cliente(
    client_id: str,
    start_date: Optional[date] = Query(None, description="Data inicial (AAAA-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Data final (AAAA-MM-DD)")
):
    """Buscar lançamentos financeiros detalhados do cliente, com filtro de data"""
    try:
        supabase = get_supabase_client()
        query = supabase.table('financial_entries').select('*').eq('client_id', client_id)
        if start_date:
            query = query.gte('report_date', str(start_date))
        if end_date:
            query = query.lte('report_date', str(end_date))
        response = query.order('report_date', desc=False).execute()
        if response.data is None:
            return []
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar financial_entries do cliente {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

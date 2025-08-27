# backend/routes/dashboard.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging

router = APIRouter(tags=["Dashboard"])
logger = logging.getLogger(__name__)

class DashboardResponse(BaseModel):
    cliente: str
    periodo: str
    kpis: dict
    financial_entries: list

@router.get("/")
def get_dashboard_data(
    client_id: str = Query(...),
    year: int = Query(...),
    month: int = Query(...)
):
    supabase = get_supabase_client()
    try:
        response = supabase.table('monthly_reports')\
            .select('*')\
            .eq('client_id', client_id)\
            .eq('reference_year', year)\
            .eq('reference_month', month)\
            .single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Relatório não encontrado para este período.")
        
        report = response.data
        
        return {
            "cliente": report['client_name'],
            "periodo": f"{report['reference_month']}/{report['reference_year']}",
            "kpis": {
                "receita_total": report['total_receitas'],
                "despesa_total": report['total_despesas'],
                "resultado_periodo": report['lucro_periodo']
            },
            "financial_entries": report['financial_entries']
        }

    except Exception as e:
        logger.exception(f"Erro ao buscar dados do dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
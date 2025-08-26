from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional, List
from pydantic import BaseModel
from database import get_supabase_client
import logging
import traceback
from collections import defaultdict
from datetime import datetime

router = APIRouter(
    # O prefixo /api/dashboard é definido no main.py
    tags=["Dashboard"]
)
logger = logging.getLogger(__name__)

# --- Modelos Pydantic para a resposta ---
class KpiResponse(BaseModel):
    receita_total: float
    despesa_total: float
    resultado_periodo: float

class ChartDataResponse(BaseModel):
    categoria: str
    valor: float

class DashboardResponse(BaseModel):
    cliente: str
    periodo: Optional[str] = None
    kpis: KpiResponse
    grafico_despesas: List[ChartDataResponse]
    grafico_receitas: List[ChartDataResponse]

# --- Funções Auxiliares ---
def _to_float(value: any) -> float:
    """Converte um valor para float de forma segura."""
    if value is None:
        return 0.0
    try:
        # Trata strings com vírgula decimal
        if isinstance(value, str):
            return float(value.replace('.', '').replace(',', '.'))
        return float(value)
    except (ValueError, TypeError):
        return 0.0

# --- Rota Principal e Única do Dashboard ---
@router.get("/", response_model=DashboardResponse)
def get_dashboard_data(
    analysis_id: int = Query(..., description="O ID da análise mensal a ser consultada"),
    client_id: str = Query(..., description="O ID do cliente para validação")
):
    """
    Endpoint principal do dashboard.
    Calcula todos os KPIs e dados para gráficos a partir da tabela 'financial_entries',
    usando o 'analysis_id' como a única fonte da verdade.
    """
    supabase = get_supabase_client()
    try:
        # 1. Buscar os metadados da análise para validação e informações de cabeçalho
        logger.info(f"Buscando análise com ID: {analysis_id} para o cliente: {client_id}")
        analysis_resp = supabase.table('monthly_analyses')\
            .select('id, client_id, client_name, report_date')\
            .eq('id', analysis_id)\
            .eq('client_id', client_id)\
            .single().execute()

        if not hasattr(analysis_resp, 'data') or not analysis_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Análise com ID {analysis_id} não encontrada para este cliente.")
        
        analysis = analysis_resp.data
        logger.info(f"Análise encontrada: {analysis}")

        # 2. Buscar TODOS os lançamentos financeiros ('financial_entries') para esta análise
        entries_resp = supabase.table('financial_entries')\
            .select('movement_type, period_value, subgroup_1')\
            .eq('analysis_id', analysis_id)\
            .execute()

        if not hasattr(entries_resp, 'data'):
             raise HTTPException(status_code=500, detail="Erro ao buscar lançamentos financeiros.")

        entries = entries_resp.data or []
        logger.info(f"Encontrados {len(entries)} lançamentos financeiros para a análise {analysis_id}")

        # 3. Calcular KPIs e agregar dados para os gráficos em Python
        receita_total = 0.0
        despesa_total = 0.0
        receitas_map = defaultdict(float)
        despesas_map = defaultdict(float)

        for entry in entries:
            valor = _to_float(entry.get('period_value'))
            categoria = entry.get('subgroup_1') or 'Não categorizado'
            
            if entry.get('movement_type') == 'Receita':
                receita_total += valor
                receitas_map[categoria] += valor
            elif entry.get('movement_type') == 'Despesa':
                despesa_total += valor
                despesas_map[categoria] += valor
        
        kpis = {
            'receita_total': receita_total,
            'despesa_total': despesa_total,
            'resultado_periodo': receita_total - despesa_total
        }
        logger.info(f"KPIs calculados: {kpis}")

        # 4. Formatar dados para os gráficos
        grafico_receitas = sorted(
            [{'categoria': k, 'valor': v} for k, v in receitas_map.items()],
            key=lambda x: x['valor'], reverse=True
        )
        
        grafico_despesas = sorted(
            [{'categoria': k, 'valor': v} for k, v in despesas_map.items()],
            key=lambda x: x['valor'], reverse=True
        )[:10] # Limita a 10 principais categorias de despesa

        # 5. Montar e retornar a resposta final
        periodo_formatado = None
        if analysis.get('report_date'):
            try:
                periodo_formatado = datetime.fromisoformat(analysis['report_date']).strftime('%d/%m/%Y')
            except (ValueError, TypeError):
                periodo_formatado = analysis['report_date']

        return {
            'cliente': analysis.get('client_name') or client_id,
            'periodo': periodo_formatado,
            'kpis': kpis,
            'grafico_despesas': grafico_despesas,
            'grafico_receitas': grafico_receitas,
        }

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.exception("Erro ao gerar dashboard: %s\n%s", str(e), tb)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro interno: {str(e)}"
        )

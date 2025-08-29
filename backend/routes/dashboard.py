# backend/routes/dashboard.py
from fastapi import APIRouter, HTTPException, Query, status, Body
from typing import List, Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)
logger = logging.getLogger(__name__)

# ... (Mantenha o Pydantic Model 'DashboardResponse') ...
class DashboardResponse(BaseModel):
    cliente: str
    periodo: str
    kpis: dict
    financial_entries: list
    grafico_receitas: Optional[list] = None
    grafico_despesas: Optional[list] = None


@router.post('/aggregate')
def aggregate_dashboard(payload: dict = Body(...)):
    """
    Endpoint de agregação que aceita:
    - { analysis_ids: [1,2,3] }
    OU
    - { client_id: str, periods: [{ year: 2024, month: 12 }, ...] }

    Retorna: { kpis, grafico_receitas, grafico_despesas, financial_entries }
    """
    supabase = get_supabase_client()
    try:
        logger.debug(f"aggregate called with payload: {payload}")
        analysis_ids: List[int] = payload.get('analysis_ids') or []
        client_id: Optional[str] = payload.get('client_id')
        periods = payload.get('periods') or []

        # Resolve analysis_ids from periods if needed
        if not analysis_ids and client_id and periods:
            for p in periods:
                year = p.get('year')
                month = p.get('month')
                if year is None or month is None:
                    continue
                resp = supabase.table('monthly_analyses')\
                    .select('id')\
                    .eq('client_id', client_id)\
                    .eq('reference_year', year)\
                    .eq('reference_month', month)\
                    .limit(1)\
                    .execute()
                logger.debug(f"resolved monthly_analyses query for client={client_id} year={year} month={month} -> resp.error={getattr(resp, 'error', None)} resp.data={getattr(resp, 'data', None)}")
                if getattr(resp, 'data', None):
                    analysis_ids.append(resp.data[0]['id'])

        logger.info(f"aggregate resolved analysis_ids: {analysis_ids}")
        if not analysis_ids:
            raise HTTPException(status_code=400, detail='Nenhum analysis_id encontrado ou informado.')

        # Fetch financial entries for these analyses
        entries_resp = supabase.table('financial_entries')\
            .select('*')\
            .in_('analysis_id', analysis_ids)\
            .execute()
        entries = entries_resp.data if getattr(entries_resp, 'data', None) else []
        logger.info(f"financial_entries fetched: {len(entries)} entries for analyses {analysis_ids}")

        # Helper: determine if an entry is receita
        def _is_receita(movement_raw: Optional[str]) -> bool:
            if not movement_raw:
                return False
            m = str(movement_raw).strip().lower()
            if m == 'r' or m.startswith('r'):
                return True
            return 'receita' in m

        # Aggregate values by specific_account (preferred) and movement_type
        receitas_map = {}
        despesas_map = {}
        total_receitas = 0.0
        total_despesas = 0.0

        for e in entries:
            mt_raw = e.get('movement_type') or ''
            is_rec = _is_receita(mt_raw)
            # prefer specific_account, then subgroup_1, then subgroup
            cat = e.get('specific_account') or e.get('subgroup_1') or e.get('subgrupo') or 'Outros'
            try:
                val = float(e.get('period_value') or 0)
            except Exception:
                # try to coerce from localized formats
                try:
                    sval = str(e.get('period_value') or '0').replace('.', '').replace(',', '.')
                    val = float(sval)
                except Exception:
                    val = 0.0

            if is_rec:
                receitas_map[cat] = receitas_map.get(cat, 0.0) + val
                total_receitas += val
            else:
                despesas_map[cat] = despesas_map.get(cat, 0.0) + val
                total_despesas += val

        # color palette for charts
        colors = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1', '#f97316']

        def map_to_array(m: dict, total: float):
            arr = []
            for k, v in m.items():
                percentual = (v / total * 100) if total > 0 else 0
                arr.append({'categoria': k, 'valor': v, 'percentual': percentual})
            arr.sort(key=lambda x: x['valor'], reverse=True)
            for idx, it in enumerate(arr):
                it['cor'] = colors[idx % len(colors)]
            return arr

        grafico_receitas = map_to_array(receitas_map, total_receitas)
        grafico_despesas = map_to_array(despesas_map, total_despesas)

        # KPIs
        def _to_float(v, fallback=0.0):
            try:
                if v is None:
                    return float(fallback)
                return float(v)
            except Exception:
                try:
                    return float(str(v).replace('.', '').replace(',', '.'))
                except Exception:
                    return float(fallback)

        kpis = {
            'receita_total': total_receitas,
            'despesa_total': total_despesas,
            'resultado_periodo': (total_receitas - total_despesas)
        }

        return {
            'kpis': kpis,
            'grafico_receitas': grafico_receitas,
            'grafico_despesas': grafico_despesas,
            'financial_entries': entries
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f'Erro no aggregate: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=DashboardResponse)
def get_dashboard_data(
    client_id: str = Query(...),
    year: int = Query(...),
    month: int = Query(...)
):
    """
    Busca os dados do dashboard para um cliente e período específicos.
    Lida corretamente com casos onde nenhum relatório é encontrado.
    """
    supabase = get_supabase_client()
    try:
        # Log incoming params for diagnostics
        logger.debug(f"get_dashboard_data called with client_id={client_id} year={year} month={month}")

        # CORREÇÃO: Usamos .maybe_single() que retorna None se não encontrar nada, sem dar erro.
        response = supabase.table('monthly_analyses')\
            .select('*')\
            .eq('client_id', client_id)\
            .eq('reference_year', year)\
            .eq('reference_month', month)\
            .maybe_single()\
            .execute()

        logger.debug(f"monthly_analyses query result: {getattr(response, 'data', None)}")

        if not response.data:
            # Não encontramos relatório: logamos e retornamos 200 com payload vazio para UX mais suave.
            logger.info(f"Nenhum relatório encontrado para client_id={client_id} year={year} month={month}")
            return {
                "cliente": "",
                "periodo": f"{int(month)}/{int(year)}",
                "kpis": {},
                "financial_entries": []
            }

        report = response.data
        
        # Busca os lançamentos associados a essa análise
        entries_response = supabase.table('financial_entries')\
            .select('*')\
            .eq('analysis_id', report['id'])\
            .execute()
        entries = entries_response.data if entries_response and getattr(entries_response, 'data', None) else []
        logger.debug(f"financial_entries count for analysis {report.get('id')}: {len(entries)}")

        return {
            "cliente": report.get('client_name'),
            "periodo": f"{report.get('reference_month')}/{report.get('reference_year')}",
            "kpis": {
                "receita_total": report.get('total_receitas'),
                "despesa_total": report.get('total_despesas'),
                "resultado_periodo": report.get('lucro_bruto')
            },
            "financial_entries": entries
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao buscar dados do dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{analysis_id}', response_model=DashboardResponse)
def get_dashboard_by_analysis(analysis_id: int):
    """Retorna dashboard (KPIs, gráficos e lançamentos) para uma analysis_id específica.
    Endpoint usado pelo frontend que referencia análises por id (ex: /api/dashboard/{analysis_id}).
    """
    supabase = get_supabase_client()
    try:
        resp = supabase.table('monthly_analyses').select('*').eq('id', analysis_id).maybe_single().execute()
        if not getattr(resp, 'data', None):
            raise HTTPException(status_code=404, detail='Analysis não encontrada')
        report = resp.data

        entries_resp = supabase.table('financial_entries').select('*').eq('analysis_id', analysis_id).execute()
        entries = entries_resp.data if getattr(entries_resp, 'data', None) else []

        # build charts from entries, preferring specific_account for categories
        receitas_map = {}
        despesas_map = {}
        total_receitas = 0.0
        total_despesas = 0.0
        for e in entries:
            mt = (e.get('movement_type') or '').strip().lower()
            cat = e.get('specific_account') or e.get('subgroup_1') or 'Outros'
            try:
                val = float(e.get('period_value') or 0)
            except Exception:
                try:
                    sval = str(e.get('period_value') or '0').replace('.', '').replace(',', '.')
                    val = float(sval)
                except Exception:
                    val = 0.0
            if mt == 'receita' or mt == 'r' or 'receita' in mt:
                receitas_map[cat] = receitas_map.get(cat, 0.0) + val
                total_receitas += val
            else:
                despesas_map[cat] = despesas_map.get(cat, 0.0) + val
                total_despesas += val

        colors = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1', '#f97316']

        def map_to_array(m, total):
            arr = []
            for k, v in m.items():
                percentual = (v / total * 100) if total > 0 else 0
                arr.append({ 'categoria': k, 'valor': v, 'percentual': percentual })
            arr.sort(key=lambda x: x['valor'], reverse=True)
            for idx, it in enumerate(arr):
                it['cor'] = colors[idx % len(colors)]
            return arr

        grafico_receitas = map_to_array(receitas_map, total_receitas)
        grafico_despesas = map_to_array(despesas_map, total_despesas)

        kpis = {
            'receita_total': report.get('total_receitas') if report.get('total_receitas') is not None else total_receitas,
            'despesa_total': report.get('total_despesas') if report.get('total_despesas') is not None else total_despesas,
            'resultado_periodo': report.get('lucro_bruto') if report.get('lucro_bruto') is not None else (total_receitas - total_despesas)
        }

        return {
            'cliente': report.get('client_name'),
            'periodo': f"{report.get('reference_month')}/{report.get('reference_year')}",
            'kpis': kpis,
            'grafico_receitas': grafico_receitas,
            'grafico_despesas': grafico_despesas,
            'financial_entries': entries
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f'Erro ao buscar dashboard por analysis_id: {e}')
        raise HTTPException(status_code=500, detail=str(e))
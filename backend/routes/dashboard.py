# backend/routes/dashboard.py
from fastapi import APIRouter, HTTPException, Query, Body, Response
from typing import Optional, List, Dict, Any
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


class AggregateRequest(BaseModel):
    # Either provide analysis_ids OR provide periods (each with year and month and optional client_id)
    analysis_ids: Optional[List[int]] = None
    periods: Optional[List[Dict[str, int]]] = None


class AggregateResponse(BaseModel):
    kpis: dict
    grafico_receitas: List[dict]
    grafico_despesas: List[dict]
    financial_entries: List[dict]

@router.get("/")
def get_dashboard_data(
    client_id: str = Query(...),
    year: int = Query(...),
    month: int = Query(...)
):
    supabase = get_supabase_client()
    try:
            # monthly_analyses is the canonical table used in the schema
            resp = supabase.table('monthly_analyses')\
                .select('*')\
                .eq('client_id', client_id)\
                .eq('reference_year', year)\
                .eq('reference_month', month)\
                .limit(1)\
                .execute()

            if not resp or not getattr(resp, 'data', None) or len(resp.data) == 0:
                # no report found for this period
                raise HTTPException(status_code=404, detail="Relatório não encontrado para este período.")

            report = resp.data[0]

            # load financial entries for the analysis (if any)
            entries = []
            analysis_id = report.get('id')
            if analysis_id:
                eres = supabase.table('financial_entries')\
                    .select('specific_account,subgroup_1,movement_type,period_value')\
                    .eq('analysis_id', analysis_id)\
                    .execute()
                entries = eres.data or []

            # defensive mapping of KPI fields (schema uses total_receitas/total_despesas/lucro_bruto)
            receita = report.get('total_receitas') or 0
            despesa = report.get('total_despesas') or 0
            resultado = report.get('lucro_bruto')
            if resultado is None:
                try:
                    resultado = receita - despesa
                except Exception:
                    resultado = 0

            cliente_name = report.get('client_name') or report.get('client_id')

            return {
                'cliente': cliente_name,
                'periodo': f"{report.get('reference_month')}/{report.get('reference_year')}",
                'kpis': {
                    'receita_total': receita,
                    'despesa_total': despesa,
                    'resultado_periodo': resultado
                },
                'financial_entries': entries
            }

    except Exception as e:
        logger.exception(f"Erro ao buscar dados do dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/aggregate', response_model=AggregateResponse)
def aggregate_dashboards(req: AggregateRequest = Body(...), response: Response = None):
    """Aggregate multiple monthly analyses identified by analysis_ids or by (year,month) pairs.
    Returns summed KPIs and pre-aggregated grafico_receitas/grafico_despesas built from financial_entries.
    """
    supabase = get_supabase_client()
    try:
        analysis_ids: List[int] = []

        # If analysis_ids provided, use them
        if req.analysis_ids:
            analysis_ids = [int(x) for x in req.analysis_ids]
        elif req.periods:
            # periods is list of {"year": 2024, "month": 12, "client_id": "..." (optional)}
            for p in req.periods:
                year = int(p.get('year'))
                month = int(p.get('month'))
                client_id = p.get('client_id')
                q = supabase.table('monthly_analyses').select('id').eq('reference_year', year).eq('reference_month', month)
                if client_id:
                    q = q.eq('client_id', client_id)
                r = q.execute()
                if r and getattr(r, 'data', None):
                    for row in r.data:
                        if row.get('id') is not None:
                            analysis_ids.append(int(row.get('id')))

        logger.debug('aggregate_dashboards called with analysis_ids (pre-dedupe): %s, periods: %s', req.analysis_ids, req.periods)

        if not analysis_ids:
            raise HTTPException(status_code=400, detail='Nenhum analysis_id encontrado para agregar')

        # Deduplicate
        analysis_ids = list(dict.fromkeys(analysis_ids))
        logger.debug('aggregate_dashboards deduped analysis_ids: %s', analysis_ids)

        # set Cache-Control header to allow short-term caching of this aggregation response
        try:
            if response is not None:
                response.headers['Cache-Control'] = 'public, max-age=120'
        except Exception:
            # don't fail aggregation if headers cannot be set for some reason
            logger.exception('Failed to set Cache-Control header on aggregate response')

        # Fetch monthly_analyses rows for metadata and KPIs
        resp = supabase.table('monthly_analyses').select('*').in_('id', analysis_ids).execute()
        rows = resp.data or []
        logger.debug('aggregate_dashboards fetched %d monthly_analyses rows for ids %s', len(rows), analysis_ids)

        agg_receita = 0
        agg_despesa = 0
        agg_resultado = 0
        all_entries: List[Dict[str, Any]] = []

        for r in rows:
            receita = r.get('total_receitas') or 0
            despesa = r.get('total_despesas') or 0
            resultado = r.get('lucro_bruto')
            if resultado is None:
                try:
                    resultado = receita - despesa
                except Exception:
                    resultado = 0

            agg_receita += float(receita)
            agg_despesa += float(despesa)
            agg_resultado += float(resultado)

        # Load financial_entries for all analysis_ids
        entries_resp = supabase.table('financial_entries').select('specific_account,subgroup_1,movement_type,period_value,analysis_id').in_('analysis_id', analysis_ids).execute()
        entries = entries_resp.data or []
        all_entries.extend(entries)
        logger.debug('aggregate_dashboards fetched %d financial_entries across analyses', len(entries))

        # Build grafico_receitas & grafico_despesas by grouping subgroup_1
        receita_map: Dict[str, float] = {}
        despesa_map: Dict[str, float] = {}

        for e in all_entries:
            mv_raw = e.get('movement_type')
            mv = (str(mv_raw).strip().lower() if mv_raw is not None else '')
            sub = e.get('subgroup_1') or 'Outros'
            try:
                val = float(e.get('period_value') or 0)
            except Exception:
                val = 0

            # classify receipts case-insensitively; anything else is treated as expense
            if mv == 'receita':
                receita_map[sub] = receita_map.get(sub, 0) + val
            else:
                despesa_map[sub] = despesa_map.get(sub, 0) + val

        # Convert maps to arrays with percentual and color
        def to_arr(m: Dict[str, float], total: float):
            palette = ['#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6', '#F97316', '#EC4899']
            arr = []
            for i, (cat, v) in enumerate(sorted(m.items(), key=lambda x: x[1], reverse=True)):
                porcent = (v / total * 100) if total and total > 0 else 0
                arr.append({ 'categoria': cat, 'valor': v, 'percentual': porcent, 'cor': palette[i % len(palette)], 'contas_detalhadas': [] })
            return arr

        grafico_r = to_arr(receita_map, agg_receita)
        grafico_d = to_arr(despesa_map, agg_despesa)

        if not grafico_r and all_entries:
            logger.warning('grafico_receitas is empty but financial_entries exist; receita_map=%s, agg_receita=%s', receita_map, agg_receita)
        if not grafico_d and all_entries:
            logger.warning('grafico_despesas is empty but financial_entries exist; despesa_map=%s, agg_despesa=%s', despesa_map, agg_despesa)

        return {
            'kpis': {
                'receita_total': agg_receita,
                'despesa_total': agg_despesa,
                'resultado_periodo': agg_resultado
            },
            'grafico_receitas': grafico_r,
            'grafico_despesas': grafico_d,
            'financial_entries': all_entries
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception('Erro ao agregar dashboards: %s', e)
        raise HTTPException(status_code=500, detail='Erro interno ao agregar dashboards')
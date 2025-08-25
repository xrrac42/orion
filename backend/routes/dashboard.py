from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from database import get_supabase_client
import logging
import traceback

router = APIRouter(
    tags=["Dashboard"]
)


def _resolve_analysis_id(supabase, analysis_id: Optional[int], balancete_id: Optional[int]) -> int:
    """Resolve an analysis id from either analysis_id or balancete_id. Raises HTTPException on error."""
    if analysis_id is not None:
        resp = supabase.table('monthly_analyses').select('*').eq('id', analysis_id).execute()
        if resp and getattr(resp, 'data', None):
            return int(resp.data[0]['id'])
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"analysis_id {analysis_id} não encontrado")

    if balancete_id is not None:
        bal = supabase.table('balancetes').select('analysis_id').eq('id', balancete_id).single().execute()
        if bal and getattr(bal, 'data', None) and bal.data.get('analysis_id'):
            return int(bal.data.get('analysis_id'))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"balancete_id {balancete_id} não vinculado a uma analysis")

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Forneça analysis_id ou balancete_id")


def _to_float(value) -> float:
    """Try to convert various value formats to float. Handles strings with commas/dots."""
    try:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # remove thousands separator and normalize decimal comma
            v = value.replace('.', '').replace(',', '.')
            return float(v)
        return float(value)
    except Exception:
        return 0.0


@router.get("/")
def get_dashboard(
    analysis_id: Optional[int] = Query(None),
    balancete_id: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=1900),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Query-based dashboard endpoint. Accepts analysis_id or balancete_id and optional month/year filters.
    Returns a single payload with analysis meta, KPIs, charts and paginated entries."""
    try:
        supabase = get_supabase_client()

        numeric_analysis_id = _resolve_analysis_id(supabase, analysis_id, balancete_id)

        # Fetch analysis/meta
        analysis_resp = supabase.table('monthly_analyses').select('*').eq('id', numeric_analysis_id).single().execute()
        if not analysis_resp or not getattr(analysis_resp, 'data', None):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada")
        analysis = analysis_resp.data

        # Fetch entries linked to this analysis
        entries_resp = supabase.table('financial_entries').select('*').eq('analysis_id', numeric_analysis_id).execute()
        entries = entries_resp.data or []
        logging.getLogger(__name__).info(f"Dashboard query: found {len(entries)} financial_entries for analysis {numeric_analysis_id}")

        # Optional filter by month/year using report_date if provided
        if month or year:
            from datetime import datetime
            filtered = []
            for e in entries:
                rd = e.get('report_date')
                if not rd:
                    continue
                try:
                    dt = datetime.fromisoformat(rd)
                except Exception:
                    # skip malformed dates
                    continue
                if month and dt.month != month:
                    continue
                if year and dt.year != year:
                    continue
                filtered.append(e)
            entries = filtered

        total = len(entries)
        paged = entries[offset: offset + limit]

        # Aggregations
        receita_total = sum(_to_float(e.get('period_value')) for e in entries if (str(e.get('movement_type') or '').lower() == 'receita'))
        despesa_total = sum(_to_float(e.get('period_value')) for e in entries if (str(e.get('movement_type') or '').lower() == 'despesa'))
        kpis = {
            'receita_total': float(receita_total),
            'despesa_total': float(despesa_total),
            'resultado_periodo': float(receita_total - despesa_total)
        }

        from collections import defaultdict
        despesas_map = defaultdict(float)
        receitas_map = defaultdict(float)
        for e in entries:
            mtype = str(e.get('movement_type') or '').lower()
            cat = e.get('subgroup_1') or ('Receita' if mtype == 'receita' else 'Outras Despesas')
            val = _to_float(e.get('period_value'))
            if mtype == 'despesa':
                despesas_map[cat] += val
            else:
                receitas_map[cat] += val

        despesas_por_categoria = sorted(
            [{'categoria': k, 'valor': v} for k, v in despesas_map.items()],
            key=lambda x: x['valor'], reverse=True
        )[:10]

        receitas_por_categoria = sorted(
            [{'categoria': k, 'valor': v} for k, v in receitas_map.items()],
            key=lambda x: x['valor'], reverse=True
        )

        return {
            'analysis': analysis,
            'kpis': kpis,
            'grafico_despesas': despesas_por_categoria,
            'grafico_receitas': receitas_por_categoria,
            'entries': paged,
            'meta': {'limit': limit, 'offset': offset, 'total': total}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        tb = traceback.format_exc()
        logger.exception("Erro ao gerar dashboard via query: %s\n%s", str(e), tb)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocorreu um erro interno: {str(e)}")

@router.get("/{analysis_id}")
def get_dashboard_data(analysis_id: str):
    """
    Retorna os dados agregados para um balancete específico (analysis_id)
    para popular o dashboard do cliente.
    """
    try:
        # Use Supabase client to fetch analysis and related financial entries
        supabase = get_supabase_client()

        # 1. Resolve analysis_id: accept either numeric analysis id or a client UUID
        numeric_analysis_id = None
        analysis = None

        # If the path param looks like a UUID (contains '-') treat it as a client_id
        if isinstance(analysis_id, str) and ('-' in analysis_id or len(analysis_id) > 16):
            analyses_resp = supabase.table('monthly_analyses')\
                .select('*')\
                .eq('client_id', analysis_id)\
                .order('reference_year', desc=True)\
                .order('reference_month', desc=True)\
                .limit(1)\
                .execute()
            if not analyses_resp.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Nenhuma análise encontrada para o cliente {analysis_id}"
                )
            analysis = analyses_resp.data[0]
            numeric_analysis_id = int(analysis['id'])
        else:
            # Try to use the provided value as an integer analysis id
            try:
                numeric_analysis_id = int(analysis_id)
            except Exception:
                # Last resort: query by id as-is
                analyses_resp = supabase.table('monthly_analyses').select('*').eq('id', analysis_id).execute()
                if not analyses_resp.data:
                    # Try to resolve the provided id as a balancete id that references an analysis
                    try:
                        bal_resp = supabase.table('balancetes').select('analysis_id').eq('id', analysis_id).single().execute()
                        if bal_resp and getattr(bal_resp, 'data', None) and bal_resp.data.get('analysis_id'):
                            resolved = bal_resp.data.get('analysis_id')
                            analyses_resp = supabase.table('monthly_analyses').select('*').eq('id', resolved).execute()
                            if analyses_resp and analyses_resp.data:
                                analysis = analyses_resp.data[0]
                                numeric_analysis_id = int(analysis['id'])
                            else:
                                raise HTTPException(
                                    status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Nenhuma análise encontrada associada ao balancete {analysis_id}"
                                )
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Nenhuma análise encontrada com o ID {analysis_id}"
                            )
                    except HTTPException:
                        raise
                    except Exception:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Nenhuma análise encontrada com o ID {analysis_id}"
                        )
                else:
                    analysis = analyses_resp.data[0]
                    numeric_analysis_id = int(analysis['id'])

        # If we haven't loaded analysis yet, fetch it by numeric id
        if analysis is None:
            analyses_resp = supabase.table('monthly_analyses').select('*').eq('id', numeric_analysis_id).execute()
            if not analyses_resp.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Nenhuma análise encontrada com o ID {analysis_id}"
                )
            analysis = analyses_resp.data[0]

        # 2. Busca lançamentos financeiros relacionados (financial_entries)
        entries_resp = supabase.table('financial_entries').select('*').eq('analysis_id', numeric_analysis_id).execute()
        entries = entries_resp.data or []

        # 3. Calcula KPIs em Python (normalizando tipos e valores)
        receita_total = sum(_to_float(e.get('period_value')) for e in entries if (str(e.get('movement_type') or '').lower() == 'receita'))
        despesa_total = sum(_to_float(e.get('period_value')) for e in entries if (str(e.get('movement_type') or '').lower() == 'despesa'))
        kpis = {
            'receita_total': float(receita_total),
            'despesa_total': float(despesa_total),
            'resultado_periodo': float(receita_total - despesa_total)
        }

        # 4. Agrupa por categoria
        from collections import defaultdict
        despesas_map = defaultdict(float)
        receitas_map = defaultdict(float)
        for e in entries:
            mtype = str(e.get('movement_type') or '').lower()
            cat = e.get('subgroup_1') or ( 'Receita' if mtype == 'receita' else 'Outras Despesas')
            val = _to_float(e.get('period_value'))
            if mtype == 'despesa':
                despesas_map[cat] += val
            else:
                receitas_map[cat] += val

        despesas_por_categoria = sorted(
            [{'categoria': k, 'valor': v} for k, v in despesas_map.items()],
            key=lambda x: x['valor'], reverse=True
        )[:10]

        receitas_por_categoria = sorted(
            [{'categoria': k, 'valor': v} for k, v in receitas_map.items()],
            key=lambda x: x['valor'], reverse=True
        )

        # 5. Monta resposta
        cliente_name = analysis.get('client_name') or analysis.get('client_id')
        periodo = analysis.get('report_date')
        # If periodo exists as ISO string, format it; otherwise leave as-is
        try:
            from datetime import datetime
            periodo_formatted = datetime.fromisoformat(periodo).strftime('%d/%m/%Y') if periodo else None
        except Exception:
            periodo_formatted = periodo

        return {
            'cliente': cliente_name,
            'periodo': periodo_formatted,
            'kpis': kpis,
            'grafico_despesas': despesas_por_categoria,
            'grafico_receitas': receitas_por_categoria
        }

    except Exception as e:
        # Log full traceback for debugging in development
        logger = logging.getLogger(__name__)
        tb = traceback.format_exc()
        logger.exception("Erro ao gerar dashboard para analysis_id=%s:\n%s", analysis_id, tb)
        # Return the exception message in the response detail to surface the real error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro interno ao processar os dados do dashboard: {str(e)}"
        )

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from database import get_supabase_client
import logging

router = APIRouter(prefix='/api/debug', tags=['Debug'])
logger = logging.getLogger(__name__)


@router.get('/analysis/{analysis_id}')
def debug_analysis(analysis_id: int):
    supabase = get_supabase_client()
    try:
        resp = supabase.table('monthly_analyses').select('*').eq('id', analysis_id).maybe_single().execute()
        if not getattr(resp, 'data', None):
            raise HTTPException(status_code=404, detail='Analysis não encontrada')
        report = resp.data

        entries_resp = supabase.table('financial_entries').select('*').eq('analysis_id', analysis_id).execute()
        entries = entries_resp.data if getattr(entries_resp, 'data', None) else []

        # compute sums by main_group
        sums = {}
        for e in entries:
            mg = e.get('main_group') or 'OUTROS'
            try:
                val = float(e.get('period_value') or 0)
            except Exception:
                sval = str(e.get('period_value') or '0').replace('.', '').replace(',', '.')
                try:
                    val = float(sval)
                except Exception:
                    val = 0.0
            sums[mg] = sums.get(mg, 0.0) + val

        total_entries = len(entries)

        return {
            'monthly_analysis': report,
            'financial_entries_count': total_entries,
            'financial_entries_sample': entries[:10],
            'sums_by_main_group': sums
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('Erro no debug_analysis: %s', e)
        raise HTTPException(status_code=500, detail=str(e))

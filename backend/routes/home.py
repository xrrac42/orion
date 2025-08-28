from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging

router = APIRouter(tags=["Home"])
logger = logging.getLogger(__name__)


class RecentUpload(BaseModel):
    id: str
    client_id: str
    analysis_id: Optional[int] = None
    file_name: str
    uploaded_at: str


class HomeStatsResponse(BaseModel):
    total_clientes: int
    total_balancetes: int
    recent_uploads: List[RecentUpload]


@router.get('/stats')
def get_home_stats():
    supabase = get_supabase_client()
    try:
        # total clients
        clients_resp = supabase.table('clients').select('id', count='exact').execute()
        total_clients = 0
        if clients_resp and hasattr(clients_resp, 'count') and clients_resp.count is not None:
            total_clients = clients_resp.count
        else:
            # fallback: length of data
            total_clients = len(clients_resp.data or [])

        # total balancetes (monthly_analyses / monthly_reports table)
        bal_resp = supabase.table('monthly_analyses').select('id', count='exact').execute()
        total_balancetes = 0
        if bal_resp and hasattr(bal_resp, 'count') and bal_resp.count is not None:
            total_balancetes = bal_resp.count
        else:
            total_balancetes = len(bal_resp.data or [])

        # recent uploads from file_uploads
        uploads_resp = supabase.table('file_uploads')\
            .select('id, client_id, analysis_id, file_name, created_at')\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()

        uploads_data = uploads_resp.data or []
        recent = []
        # resolve client names for the client_ids present
        client_ids = list({row.get('client_id') for row in uploads_data if row.get('client_id')})
        clients_map = {}
        if client_ids:
            # The clients table uses 'nome' (Portuguese) for the name column.
            clients_resp = supabase.table('clients').select('id, nome').in_('id', client_ids).execute()
            for c in (clients_resp.data or []):
                # map the Portuguese column to a consistent 'client_name' value
                clients_map[c.get('id')] = c.get('nome')

        for row in uploads_data:
            cid = row.get('client_id')
            recent.append({
                'id': row.get('id'),
                'client_id': cid,
                'analysis_id': row.get('analysis_id'),
                'client_name': clients_map.get(cid) or cid,
                'file_name': row.get('file_name'),
                'uploaded_at': row.get('created_at')
            })

        return {
            'total_clientes': total_clients,
            'total_balancetes': total_balancetes,
            'recent_uploads': recent
        }

    except Exception as e:
        logger.exception('Erro ao buscar estatísticas da home: %s', e)
        raise HTTPException(status_code=500, detail=str(e))

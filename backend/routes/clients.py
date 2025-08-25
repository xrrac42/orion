from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class ClientCreate(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None

class ClientResponse(BaseModel):
    id: str
    nome: str
    cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    created_at: Optional[str] = None

@router.get("/", response_model=List[ClientResponse])
async def get_clients():
    """Get all clients"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('clients')\
                          .select('*')\
                          .order('created_at', desc=True)\
                          .execute()
        if response.data is None:
            return []
        return response.data
    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/", response_model=ClientResponse)
async def create_client(client: ClientCreate):
    """Create new client"""
    try:
        supabase = get_supabase_client()
        # Verifica se já existe cliente com o mesmo CNPJ
        if client.cnpj:
            existing = supabase.table('clients')\
                             .select('id')\
                             .eq('cnpj', client.cnpj)\
                             .execute()
            if existing.data and len(existing.data) > 0:
                raise HTTPException(status_code=400, detail="Cliente com este CNPJ já existe")
        # Cria cliente
        result = supabase.table('clients').insert(client.dict()).execute()
        if result.data:
            return result.data[0]
        else:
            raise HTTPException(status_code=500, detail="Erro ao criar cliente")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: str):
    """Get client by ID"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('clients').select('*').eq('id', client_id).single().execute()
        logger.debug(f"Supabase response for get_client({client_id}): {getattr(response, 'data', None)}; error={getattr(response, 'error', None)}")
        if response.data:
            return response.data
        else:
            raise HTTPException(status_code=404, detail="Client not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching client: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{client_id}")
async def delete_client(client_id: str):
    """Delete client by ID"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('clients').delete().eq('id', client_id).execute()
        if result.data:
            return {"message": "Client deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Client not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting client: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


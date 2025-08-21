from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class UserProfile(BaseModel):
    id: str
    nome: str
    sobrenome: Optional[str] = None
    telefone: Optional[str] = None
    empresa: Optional[str] = None
    cargo: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = 'user'
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class UserProfileCreate(BaseModel):
    nome: str
    sobrenome: Optional[str] = None
    telefone: Optional[str] = None
    empresa: Optional[str] = None
    cargo: Optional[str] = None
    role: str = 'user'

@router.get("/status")
async def auth_status():
    """Status da autenticação"""
    return {"status": "authenticated", "message": "Auth endpoint ready"}

@router.get("/profile/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: str):
    """Buscar perfil do usuário"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('user_profiles')\
                          .select('*')\
                          .eq('id', user_id)\
                          .execute()
        
        if not response.data or len(response.data) == 0:
            # Se não existe perfil, criar um básico
            profile_data = {
                'id': user_id,
                'nome': 'Usuário',
                'role': 'user'
            }
            
            create_response = supabase.table('user_profiles')\
                                    .insert(profile_data)\
                                    .execute()
            
            if create_response.data:
                return create_response.data[0]
            else:
                raise HTTPException(status_code=404, detail="Perfil não encontrado e não foi possível criar")
        
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Erro ao buscar perfil do usuário {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/profile", response_model=UserProfile)
async def create_user_profile(
    user_id: str,
    profile: UserProfileCreate
):
    """Criar perfil do usuário"""
    try:
        supabase = get_supabase_client()
        
        profile_data = profile.dict()
        profile_data['id'] = user_id
        
        response = supabase.table('user_profiles')\
                          .insert(profile_data)\
                          .execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=400, detail="Erro ao criar perfil")
        
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Erro ao criar perfil do usuário {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.put("/profile/{user_id}", response_model=UserProfile)
async def update_user_profile(
    user_id: str,
    profile: UserProfileCreate
):
    """Atualizar perfil do usuário"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('user_profiles')\
                          .update(profile.dict())\
                          .eq('id', user_id)\
                          .execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Perfil não encontrado")
        
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil do usuário {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Configurações do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xhjvlbkelfiemlymxafv.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
print(f"[DEBUG] SUPABASE_SERVICE_KEY loaded: {SUPABASE_SERVICE_KEY[:8]}... (length: {len(SUPABASE_SERVICE_KEY)})")

def get_supabase_client() -> Client:
    """Retorna cliente Supabase usando as credenciais de serviço"""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

class SupabaseClient:
    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    async def insert(self, table: str, data: Dict) -> Dict:
        """Inserir dados em uma tabela"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/{table}",
                headers=self.headers,
                json=data
            )
            if response.status_code in [200, 201]:
                return response.json()
            else:
                raise Exception(f"Erro ao inserir: {response.text}")
    
    async def select(self, table: str, filters: Optional[Dict] = None, select: str = "*") -> List[Dict]:
        """Buscar dados de uma tabela"""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/{table}?select={select}"
            
            if filters:
                for key, value in filters.items():
                    url += f"&{key}=eq.{value}"
            
            response = await client.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Erro ao buscar: {response.text}")
    
    async def update(self, table: str, filters: Dict, data: Dict) -> Dict:
        """Atualizar dados em uma tabela"""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/{table}"
            
            for key, value in filters.items():
                url += f"?{key}=eq.{value}"
            
            response = await client.patch(
                url,
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Erro ao atualizar: {response.text}")
    
    async def delete(self, table: str, filters: Dict) -> bool:
        """Deletar dados de uma tabela"""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/{table}"
            
            for key, value in filters.items():
                url += f"?{key}=eq.{value}"
            
            response = await client.delete(url, headers=self.headers)
            
            return response.status_code in [200, 204]

# Instância global do cliente
supabase_client = SupabaseClient()

# Funções auxiliares para cada tabela
class UserRepository:
    @staticmethod
    async def create_user(user_data: Dict) -> Dict:
        return await supabase_client.insert("users", user_data)
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict]:
        users = await supabase_client.select("users", {"email": email})
        return users[0] if users else None
    
    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[Dict]:
        users = await supabase_client.select("users", {"id": user_id})
        return users[0] if users else None

class ClienteRepository:
    @staticmethod
    async def create_cliente(cliente_data: Dict) -> Dict:
        return await supabase_client.insert("clientes", cliente_data)
    
    @staticmethod
    async def get_all_clientes() -> List[Dict]:
        return await supabase_client.select("clientes", {"is_active": True})
    
    @staticmethod
    async def get_cliente_by_id(cliente_id: int) -> Optional[Dict]:
        clientes = await supabase_client.select("clientes", {"id": cliente_id})
        return clientes[0] if clientes else None
    
    @staticmethod
    async def update_cliente(cliente_id: int, cliente_data: Dict) -> Dict:
        return await supabase_client.update("clientes", {"id": cliente_id}, cliente_data)

class BalanceteRepository:
    @staticmethod
    async def create_balancete(balancete_data: Dict) -> Dict:
        return await supabase_client.insert("balancetes", balancete_data)
    
    @staticmethod
    async def get_balancetes_by_cliente(cliente_id: int) -> List[Dict]:
        return await supabase_client.select("balancetes", {"cliente_id": cliente_id})
    
    @staticmethod
    async def get_balancete_by_periodo(cliente_id: int, mes: int, ano: int) -> Optional[Dict]:
        balancetes = await supabase_client.select("balancetes", {
            "cliente_id": cliente_id,
            "mes": mes, 
            "ano": ano
        })
        return balancetes[0] if balancetes else None

class FinancialEntryRepository:
    @staticmethod
    async def store_financial_entries(entries: List[Dict]) -> Dict:
        """Armazena entradas financeiras processadas"""
        try:
            result = await supabase_client.insert("financial_entries", entries)
            return {
                "success": True,
                "inserted_count": len(entries),
                "data": result
            }
        except Exception as e:
            logger.error(f"Erro ao armazenar entradas financeiras: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "inserted_count": 0
            }
    
    @staticmethod
    async def get_entries_by_client(client_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """Busca entradas financeiras por cliente e período"""
        filters = {"client_id": client_id}
        
        # TODO: Implementar filtros de data quando necessário
        # if start_date:
        #     filters["report_date.gte"] = start_date
        # if end_date:
        #     filters["report_date.lte"] = end_date
        
        return await supabase_client.select("financial_entries", filters)
    
    @staticmethod
    async def move_to_quarantine(file_path: str, error_info: Dict) -> bool:
        """Move arquivo para quarentena"""
        try:
            quarantine_data = {
                "file_path": file_path,
                "error_message": error_info.get("error", ""),
                "quarantine_date": error_info.get("quarantine_date", ""),
                "original_path": error_info.get("original_path", file_path)
            }
            
            await supabase_client.insert("quarantine_files", quarantine_data)
            return True
            
        except Exception as e:
            logger.error(f"Erro ao mover para quarentena: {str(e)}")
            return False

# Adicionar método para SupabaseClient
async def store_financial_entries(self, entries: List[Dict]) -> Dict:
    """Método conveniente para armazenar entradas financeiras"""
    return await FinancialEntryRepository.store_financial_entries(entries)

async def move_to_quarantine(self, file_path: str, error_info: Dict) -> bool:
    """Método conveniente para mover arquivos para quarentena"""
    return await FinancialEntryRepository.move_to_quarantine(file_path, error_info)

# Adicionar os métodos à classe SupabaseClient
SupabaseClient.store_financial_entries = store_financial_entries
SupabaseClient.move_to_quarantine = move_to_quarantine

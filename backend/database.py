
class AnalysisResult:
    def __init__(self, id):
        self.id = id

async def create_analysis_and_entries(client_id: str, file_upload_id: str, analysis_data: dict, overwrite: bool = False):
    """
    Cria ou atualiza uma análise, valida e limpa os dados da IA, e insere as novas entradas.
    """
    supabase = get_supabase_client()
    
    try:
        now = datetime.utcnow()
        reference_year = analysis_data.get("reference_year") or now.year
        reference_month = analysis_data.get("reference_month") or now.month
        
        existing_analysis_resp = supabase.table("monthly_analyses").select("id").eq("client_id", client_id).eq("reference_year", reference_year).eq("reference_month", reference_month).execute()
        
        existing_analysis = existing_analysis_resp.data[0] if getattr(existing_analysis_resp, 'data', None) else None
        
        if existing_analysis and not overwrite:
            raise Exception("Análise para este período já existe e a sobrescrita não foi permitida.")

        analysis_id = None
        
        file_name = analysis_data.get("file_name", "balancete.pdf")
        client_name = analysis_data.get("client_name")
        if not client_name:
            client_resp = supabase.table("clients").select("nome").eq("id", client_id).single().execute()
            client_name = getattr(client_resp, 'data', {}).get('nome', 'Cliente Desconhecido')
        
        report_date = analysis_data.get("data_final") or now.date().isoformat()
        
        if existing_analysis:
            analysis_id = existing_analysis['id']
            logger.warning(f"Sobrescrevendo análise para o período {reference_month}/{reference_year} (ID: {analysis_id}).")
            supabase.table("financial_entries").delete().eq("analysis_id", analysis_id).execute()
        else:
            # Cria um registro placeholder mais completo para evitar o erro de 'not-null'
            pre_analysis_payload = {
                "client_id": client_id,
                "client_name": client_name,
                "reference_year": reference_year,
                "reference_month": reference_month,
                "status": "processing",
                "report_date": report_date, # Adiciona a data que estava faltando
                "source_file_name": file_name,
                "source_file_path": f"{client_id}/{file_name}"
            }
            analysis_resp = supabase.table("monthly_analyses").insert(pre_analysis_payload).execute()
            if not getattr(analysis_resp, 'data', None):
                raise Exception(f"Falha ao criar registro placeholder em monthly_analyses: {getattr(analysis_resp, 'error', 'sem detalhes')}")
            analysis_id = analysis_resp.data[0]["id"]

        logger.info(f"Registro de análise (ID: {analysis_id}) pronto para receber novas entradas.")

        entries = analysis_data.get("financial_entries", [])
        if not isinstance(entries, list) or not entries:
            logger.warning(f"Nenhuma entrada financeira encontrada na resposta da IA para a análise {analysis_id}.")
            supabase.table('monthly_analyses').update({'status': 'failed', 'error_message': 'IA não retornou entradas financeiras.'}).eq('id', analysis_id).execute()
            return AnalysisResult(id=analysis_id)

        # --- VALIDAÇÃO E LIMPEZA ROBUSTA DOS DADOS DA IA ---
        normalized_entries = []
        total_receitas_calculado = 0.0
        total_despesas_calculado = 0.0
        total_deducoes_calculado = 0.0

        for i, entry in enumerate(entries):
            if not isinstance(entry, dict): continue
            
            specific_account = entry.get('specific_account')
            if not specific_account or not str(specific_account).strip():
                logger.warning(f"Ignorando lançamento {i+1} por falta de 'specific_account'. Dados: {entry}")
                continue

            try:
                value_str = str(entry.get('period_value', '0'))
                cleaned_value_str = value_str.replace('.', '').replace(',', '.')
                period_value = float(cleaned_value_str)
            except (ValueError, TypeError):
                logger.warning(f"Não foi possível converter o valor '{entry.get('period_value')}' para número no lançamento {i+1}. Usando 0.0.")
                period_value = 0.0
            
            if period_value == 0.0:
                logger.info(f"Ignorando lançamento '{specific_account}' por ter valor zero.")
                continue

            movement_type = entry.get('movement_type')
            if movement_type == 'Receita':
                total_receitas_calculado += period_value
            elif movement_type == 'Dedução':
                total_deducoes_calculado += period_value
            elif movement_type in ['Despesa', 'Custo']:
                total_despesas_calculado += period_value

            normalized_entries.append({
                'analysis_id': analysis_id,
                'client_id': client_id,
                'report_date': report_date,
                'main_group': entry.get('main_group'),
                'subgroup_1': entry.get('subgroup_1'),
                'specific_account': specific_account,
                'movement_type': movement_type,
                'period_value': period_value
            })
        
        # --- ATUALIZA O PAYLOAD DA ANÁLISE COM OS TOTAIS RECALCULADOS E CORRETOS ---
        receita_liquida = total_receitas_calculado - total_deducoes_calculado
        
        final_analysis_payload = {
            "client_name": client_name,
            "status": "completed",
            "total_receitas": receita_liquida,
            "total_despesas": total_despesas_calculado,
            # "lucro_bruto" foi REMOVIDO daqui, pois o banco calcula sozinho.
            "report_date": report_date,
            "source_file_path": f"{client_id}/{file_name}",
            "source_file_name": file_name,
            "total_entries": len(normalized_entries)
        }
        
        supabase.table("monthly_analyses").update(final_analysis_payload).eq("id", analysis_id).execute()
        
        if not normalized_entries:
            logger.warning(f"Após a validação, nenhuma entrada financeira restou para a análise {analysis_id}.")
            supabase.table('file_uploads').update({'entries_created': 0, 'status': 'completed', 'analysis_id': analysis_id}).eq('id', file_upload_id).execute()
            return AnalysisResult(id=analysis_id)

        insert_resp = supabase.table('financial_entries').insert(normalized_entries).execute()
        if getattr(insert_resp, 'error', None):
            raise Exception(f"Erro no Supabase ao inserir financial_entries: {insert_resp.error}")

        inserted_count = len(getattr(insert_resp, 'data', []))
        logger.info(f"Inserção de financial_entries: {inserted_count}/{len(normalized_entries)} bem-sucedidas.")

        supabase.table('file_uploads').update({'status': 'completed', 'entries_created': inserted_count, 'analysis_id': analysis_id}).eq('id', file_upload_id).execute()
        
        return AnalysisResult(id=analysis_id)

    except Exception as e:
        logger.exception(f"Erro em create_analysis_and_entries para file_upload_id {file_upload_id}: {e}")
        supabase.table('file_uploads').update({'status': 'failed', 'error_message': str(e)}).eq('id', file_upload_id).execute()
        raise


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

# Alias para compatibilidade com imports antigos
get_db = get_supabase_client

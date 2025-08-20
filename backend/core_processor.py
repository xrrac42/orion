"""
Core do sistema de processamento de balancetes
Responsável por coordenar o fluxo completo de extração, análise e armazenamento
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx
from pathlib import Path

from pdf_processor import PDFProcessor
from llm_analyzer import GeminiAnalyzer
from data_validator import DataValidator
from business_rules import BusinessRuleEngine
from database import SupabaseClient

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BalanceteProcessor:
    """
    Classe principal para processar balancetes enviados
    """
    
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.gemini_analyzer = GeminiAnalyzer()
        self.data_validator = DataValidator()
        self.business_engine = BusinessRuleEngine()
        self.supabase_client = SupabaseClient()
    
    async def process_balancete(self, file_path: str, client_id: str) -> Dict[str, Any]:
        """
        Processa um balancete completo do upload até o armazenamento
        
        Args:
            file_path: Caminho para o arquivo PDF
            client_id: ID do cliente que enviou o balancete
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            logger.info(f"Iniciando processamento do balancete: {file_path}")
            
            # Etapa 1: Extração de texto do PDF
            text_content = await self.pdf_processor.extract_text(file_path)
            if not text_content:
                raise ValueError("Não foi possível extrair texto do PDF")
            
            logger.info("Texto extraído com sucesso do PDF")
            
            # Etapa 2: Análise com LLM (Gemini)
            structured_data = await self.gemini_analyzer.analyze_balancete(text_content)
            if not structured_data:
                raise ValueError("LLM não conseguiu estruturar os dados")
            
            logger.info("Dados estruturados pelo LLM com sucesso")
            
            # Etapa 3: Validação da estrutura de dados
            validation_result = self.data_validator.validate_structure(structured_data)
            if not validation_result.is_valid:
                raise ValueError(f"Dados inválidos: {validation_result.errors}")
            
            logger.info("Validação de dados bem-sucedida")
            
            # Etapa 4: Aplicação das regras de negócio
            processed_entries = self.business_engine.process_accounts(
                structured_data["contas"], 
                client_id,
                structured_data["data_final"]
            )
            
            logger.info(f"Processadas {len(processed_entries)} entradas financeiras")
            
            # Etapa 5: Armazenamento no banco de dados
            storage_result = await self.supabase_client.store_financial_entries(processed_entries)
            
            logger.info("Dados armazenados com sucesso no banco")
            
            # Retornar resultado do processamento
            return {
                "success": True,
                "client_id": client_id,
                "cliente_nome": structured_data.get("cliente"),
                "data_final": structured_data.get("data_final"),
                "total_entries": len(processed_entries),
                "storage_result": storage_result,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento: {str(e)}")
            
            # Mover arquivo para quarentena
            await self._move_to_quarantine(file_path, str(e))
            
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "client_id": client_id,
                "processed_at": datetime.utcnow().isoformat()
            }
    
    async def _move_to_quarantine(self, file_path: str, error_message: str):
        """
        Move arquivo com erro para pasta de quarentena
        """
        try:
            # Implementar lógica de quarentena no Supabase Storage
            quarantine_info = {
                "original_path": file_path,
                "error": error_message,
                "quarantine_date": datetime.utcnow().isoformat()
            }
            
            await self.supabase_client.move_to_quarantine(file_path, quarantine_info)
            logger.info(f"Arquivo movido para quarentena: {file_path}")
            
        except Exception as e:
            logger.error(f"Erro ao mover para quarentena: {str(e)}")

class BalanceteProcessorAPI:
    """
    Interface API para o processador de balancetes
    Usado pela Supabase Edge Function
    """
    
    def __init__(self):
        self.processor = BalanceteProcessor()
    
    async def handle_storage_webhook(self, webhook_data: Dict) -> Dict[str, Any]:
        """
        Manipula webhook do Supabase Storage quando novo arquivo é enviado
        
        Args:
            webhook_data: Dados do webhook contendo informações do arquivo
            
        Returns:
            Resultado do processamento
        """
        try:
            # Extrair informações do webhook
            file_path = webhook_data.get("record", {}).get("name")
            bucket_id = webhook_data.get("record", {}).get("bucket_id")
            
            # Validar se é um arquivo PDF no bucket correto
            if not file_path or not file_path.endswith('.pdf'):
                return {"success": False, "error": "Arquivo não é um PDF válido"}
            
            if bucket_id != "balancetes":
                return {"success": False, "error": "Arquivo não está no bucket correto"}
            
            # Extrair client_id do caminho do arquivo (assumindo estrutura: client_id/filename.pdf)
            path_parts = file_path.split('/')
            if len(path_parts) < 2:
                return {"success": False, "error": "Estrutura de pasta inválida"}
            
            client_id = path_parts[0]
            
            # Processar o balancete
            result = await self.processor.process_balancete(file_path, client_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro no webhook handler: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "webhook_data": webhook_data
            }

# Função principal para Edge Function
async def edge_function_handler(request_data: Dict) -> Dict[str, Any]:
    """
    Função principal para ser chamada pela Supabase Edge Function
    """
    api = BalanceteProcessorAPI()
    return await api.handle_storage_webhook(request_data)

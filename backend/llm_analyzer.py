"""
Módulo responsável pela análise de balancetes usando LLM (Gemini)
Converte texto não estruturado em dados JSON estruturados
"""

import logging
import json
import os
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """
    Classe responsável por analisar balancetes usando a API do Gemini
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = "gemini-1.5-flash"  # ou gemini-pro
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY não configurada")
    
    async def analyze_balancete(self, text_content: str) -> Optional[Dict[str, Any]]:
        """
        Analisa o texto do balancete e retorna dados estruturados
        
        Args:
            text_content: Texto extraído do PDF do balancete
            
        Returns:
            Dicionário com dados estruturados ou None se houver erro
        """
        try:
            if not self.api_key:
                raise ValueError("Chave da API Gemini não configurada")
            
            # Criar prompt especializado
            prompt = self._create_analysis_prompt(text_content)
            
            # Fazer chamada para a API
            response = await self._call_gemini_api(prompt)
            
            if not response:
                return None
            
            # Tentar extrair JSON da resposta
            structured_data = self._extract_json_from_response(response)
            
            if structured_data:
                logger.info("Análise do LLM concluída com sucesso")
                return structured_data
            else:
                logger.error("Não foi possível extrair JSON válido da resposta do LLM")
                return None
                
        except Exception as e:
            logger.error(f"Erro na análise com LLM: {str(e)}")
            return None
    
    def _create_analysis_prompt(self, text_content: str) -> str:
        """
        Cria o prompt especializado para análise de balancetes
        """
        prompt = f"""
Analise o seguinte texto extraído de um balancete contábil brasileiro. Sua tarefa é extrair as seguintes informações:

1. O nome da empresa cliente
2. A data final do período do balancete (formato YYYY-MM-DD)
3. Uma lista de todas as contas de resultado (Receitas, Custos e Despesas) que possuem movimentação no período

INSTRUÇÕES IMPORTANTES:
- Ignore contas do ATIVO, PASSIVO e PATRIMÔNIO LÍQUIDO
- Foque apenas em contas de RESULTADO (Receitas, Custos, Despesas)
- Para cada conta, identifique sua hierarquia de grupos
- Capture valores das colunas "Débito" e "Crédito" (ou equivalentes)
- Se um valor for negativo ou entre parênteses, considere como valor positivo
- Valores podem estar formatados como "1.234,56" ou "1,234.56"

FORMATO DE SAÍDA:
Retorne APENAS um objeto JSON válido com esta estrutura:

{{
  "cliente": "Nome da Empresa",
  "data_final": "YYYY-MM-DD",
  "contas": [
    {{
      "grupo_principal": "RECEITAS" ou "CUSTOS E DESPESAS",
      "subgrupo_1": "Primeiro Subgrupo (se existir)",
      "conta_especifica": "Nome da Conta Final",
      "valor_debito": 0.00,
      "valor_credito": 1234.56
    }}
  ]
}}

EXEMPLOS DE GRUPOS PRINCIPAIS:
- "RECEITAS" para: Receita de Vendas, Receita de Serviços, Outras Receitas, etc.
- "CUSTOS E DESPESAS" para: Custo dos Produtos Vendidos, Despesas Operacionais, Despesas Administrativas, etc.

Texto do balancete:
\"\"\"
{text_content}
\"\"\"

RESPOSTA (apenas JSON):
"""
        return prompt
    
    async def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """
        Faz chamada para a API do Gemini
        """
        try:
            url = f"{self.base_url}/models/{self.model}:generateContent"
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,  # Baixa temperatura para maior precisão
                    "topK": 1,
                    "topP": 0.8,
                    "maxOutputTokens": 8192,
                    "candidateCount": 1
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extrair texto da resposta
                    if "candidates" in result and len(result["candidates"]) > 0:
                        candidate = result["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            return candidate["content"]["parts"][0].get("text", "")
                    
                    logger.error("Estrutura de resposta inesperada da API Gemini")
                    return None
                    
                else:
                    logger.error(f"Erro na API Gemini: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Erro na chamada da API Gemini: {str(e)}")
            return None
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Extrai JSON válido da resposta do LLM
        """
        try:
            # Remover possível formatação markdown
            cleaned_text = response_text.strip()
            
            # Remover ```json e ``` se presentes
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # Tentar fazer parse do JSON
            parsed_json = json.loads(cleaned_text)
            
            # Validar estrutura básica
            if self._validate_basic_structure(parsed_json):
                return parsed_json
            else:
                logger.error("JSON não possui estrutura esperada")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse do JSON: {str(e)}")
            logger.debug(f"Texto que causou erro: {response_text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao extrair JSON: {str(e)}")
            return None
    
    def _validate_basic_structure(self, data: Dict[str, Any]) -> bool:
        """
        Valida se o JSON possui a estrutura básica esperada
        """
        try:
            # Verificar campos obrigatórios
            required_fields = ["cliente", "data_final", "contas"]
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Campo obrigatório ausente: {field}")
                    return False
            
            # Verificar se contas é uma lista
            if not isinstance(data["contas"], list):
                logger.error("Campo 'contas' deve ser uma lista")
                return False
            
            # Verificar estrutura básica de cada conta
            for i, conta in enumerate(data["contas"]):
                if not isinstance(conta, dict):
                    logger.error(f"Conta {i} deve ser um objeto")
                    return False
                
                required_conta_fields = ["grupo_principal", "conta_especifica", "valor_debito", "valor_credito"]
                for field in required_conta_fields:
                    if field not in conta:
                        logger.error(f"Campo obrigatório ausente na conta {i}: {field}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro na validação da estrutura: {str(e)}")
            return False
    
    async def test_api_connection(self) -> bool:
        """
        Testa se a conexão com a API Gemini está funcionando
        """
        try:
            test_prompt = "Responda apenas com: OK"
            response = await self._call_gemini_api(test_prompt)
            
            if response and "OK" in response:
                logger.info("Conexão com API Gemini OK")
                return True
            else:
                logger.error("Teste de conexão com API Gemini falhou")
                return False
                
        except Exception as e:
            logger.error(f"Erro no teste de conexão: {str(e)}")
            return False

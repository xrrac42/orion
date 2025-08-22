# -*- coding: utf-8 -*-
"""
Módulo responsável pela análise de balancetes usando um LLM (Gemini).
Converte o texto não estruturado de um PDF em um JSON estruturado e validado.
"""
import logging
import json
from typing import Dict, Any, Optional
import httpx

from .config import settings # Supondo que a configuração esteja neste caminho

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """
    Classe que encapsula a lógica para analisar balancetes usando a API do Google Gemini.
    """

    def __init__(self):
        """
        Inicializa o analisador, carregando a chave da API e configurando os endpoints.
        """
        if not settings.GEMINI_API_KEY:
            raise ValueError("A variável de ambiente GEMINI_API_KEY não está configurada.")
        
        self.api_key = settings.GEMINI_API_KEY
        self.model = "gemini-1.5-flash-latest"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def analyze_balancete(self, text_content: str) -> Optional[Dict[str, Any]]:
        """
        Orquestra o processo de análise do texto de um balancete.
        """
        try:
            # A única mudança necessária é aqui, no prompt.
            prompt = self._create_analysis_prompt(text_content)
            api_response_text = await self._call_gemini_api(prompt)

            if not api_response_text:
                logger.error("A chamada para a API do Gemini não retornou conteúdo.")
                return None

            structured_data = self._extract_json_from_response(api_response_text)

            if structured_data:
                logger.info("Análise do balancete via LLM concluída e validada com sucesso.")
                return structured_data
            else:
                return None

        except Exception as e:
            logger.exception(f"Erro inesperado durante a análise do balancete: {e}")
            return None

    def _create_analysis_prompt(self, text_content: str) -> str:
        """
        Cria um prompt de alta qualidade, projetado para extrair dados financeiros com precisão.
        """
        # --- PROMPT CORRIGIDO E MAIS RESTRITO ---
        # Esta nova versão força a IA a olhar apenas para as colunas corretas.
        prompt = f"""
Analise o texto de um balancete contábil brasileiro. Sua tarefa é retornar um objeto JSON.

INSTRUÇÕES CRÍTICAS E OBRIGATÓRIAS:
1.  **FOCO NAS COLUNAS CERTAS**: Para os valores `valor_debito` e `valor_credito`, você deve usar APENAS os números das colunas "Débito" e "Crédito" do período. IGNORE COMPLETAMENTE as colunas "Saldo Anterior" e "Saldo Atual". Esta é a regra mais importante.
2.  **DATAS DO PERÍODO**: Encontre a data inicial e final do relatório, que geralmente estão no cabeçalho (ex: 'de 01/01/2024 até 31/12/2024'). Retorne no formato AAAA-MM-DD.
3.  **CONTAS DE RESULTADO**: Extraia APENAS as contas dos grupos "RECEITAS" e "CUSTOS E DESPESAS". Ignore totalmente "ATIVO", "PASSIVO" e "PATRIMONIO LIQUIDO".
4.  **IDENTIFICAR CONTAS VÁLIDAS**: Uma conta válida para extração é uma linha que representa uma despesa ou receita final (ex: "ALUGUEL", "SERVICOS PRESTADOS") e que POSSUI um valor numérico maior que zero nas colunas "Débito" ou "Crédito" do período. Linhas de subtotal de grupo devem ser ignoradas.
5.  **HIERARQUIA**: Para cada conta válida, capture o `grupo_principal` (ex: "CUSTOS E DESPESAS") e o `subgrupo_1` (ex: "DESPESAS OPERACIONAIS") ao qual ela pertence. Se não houver subgrupo, retorne `null`.
6.  **FORMATO DOS NÚMEROS**: Converta todos os valores monetários para o formato float (ex: "1.234,56" se torna 1234.56).

FORMATO DE SAÍDA OBRIGATÓRIO (APENAS O JSON):
{{
  "cliente": "Nome da Empresa Extraído",
  "data_inicial": "AAAA-MM-DD",
  "data_final": "AAAA-MM-DD",
  "contas": [
    {{
      "grupo_principal": "CUSTOS E DESPESAS",
      "subgrupo_1": "DESPESAS OPERACIONAIS",
      "conta_especifica": "ALUGUEL",
      "valor_debito": 6235.12,
      "valor_credito": 0.0
    }}
  ]
}}

Texto do balancete para análise:
---
{text_content}
---
"""
        return prompt

    async def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """
        Realiza a chamada HTTP assíncrona para a API do Gemini.
        """
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0, # Temperatura zero para máxima precisão
                "topK": 1,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                text_response = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                if text_response:
                    return text_response
                else:
                    logger.error(f"Estrutura de resposta da API Gemini inesperada: {result}")
                    return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro na API Gemini: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.exception(f"Erro durante a chamada da API Gemini: {e}")
            return None

    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Extrai um objeto JSON de uma string, limpando possíveis formatações de markdown.
        """
        try:
            cleaned_text = response_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error(f"Erro de decodificação de JSON: {e}")
            logger.debug(f"Texto que causou o erro: {response_text[:500]}...")
            return None

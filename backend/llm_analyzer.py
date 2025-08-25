# -*- coding: utf-8 -*-
"""
Módulo LLM-centric responsável pela análise completa de balancetes.
A IA agora é responsável por extrair, calcular e estruturar toda a análise.
"""
import logging
import json
from typing import Dict, Any, Optional
import httpx
from .config import settings

# Configuração do logger para este módulo
logger = logging.getLogger(__name__)

# Para ver os logs detalhados no seu terminal, configure o logging no main.py
# logging.basicConfig(level=logging.INFO)

class GeminiAnalyzer:
    """
    Classe que encapsula a lógica para analisar, calcular e estruturar dados de balancetes
    usando a API do Google Gemini.
    """
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("A variável de ambiente GEMINI_API_KEY não está configurada.")
        self.api_key = settings.GEMINI_API_KEY
        self.model = "gemini-2.0-flash-latest"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def analyze_and_structure_balancete(self, text_content: str) -> Optional[Dict[str, Any]]:
        """
        Orquestra o processo completo de análise e estruturação via LLM.
        """
        try:
            prompt = self._create_super_prompt(text_content)
            
            # --- LOGGING ADICIONADO ---
            logger.info("Iniciando chamada para a API Gemini com prompt de análise completa.")
            # Para debug, você pode descomentar a linha abaixo para ver o prompt completo
            # logger.debug(f"Prompt enviado para a IA: {prompt[:500]}...")

            api_response_text = await self._call_gemini_api(prompt)

            if not api_response_text:
                # O erro específico já foi logado em _call_gemini_api
                return None

            # --- LOGGING ADICIONADO ---
            logger.info("Resposta recebida da API Gemini. Tentando extrair JSON.")
            # logger.debug(f"Texto bruto recebido: {api_response_text[:500]}...")

            structured_data = self._extract_json_from_response(api_response_text)

            if structured_data:
                # --- LOGGING ADICIONADO ---
                logger.info("JSON extraído e validado com sucesso a partir da resposta da IA.")
                return structured_data
            else:
                return None

        except Exception as e:
            logger.exception(f"Erro inesperado durante a análise completa do balancete: {e}")
            return None

    def _create_super_prompt(self, text_content: str) -> str:
        """
        Cria um prompt detalhado que instrui a IA a realizar a análise completa,
        incluindo cálculos e estruturação final dos dados.
        """
        prompt = f"""
Você é um assistente de contabilidade especialista em analisar balancetes brasileiros. Sua tarefa é analisar o texto de um balancete, extrair os dados financeiros, realizar os cálculos necessários e retornar um único objeto JSON estruturado.

TAREFAS A SEREM EXECUTADAS:
1.  **Extração de Metadados**:
    * `cliente`: O nome completo da empresa cliente.
    * `data_inicial` e `data_final`: As datas de início e fim do período do relatório (formato AAAA-MM-DD).

2.  **Extração de Lançamentos**:
    * Crie uma lista chamada `financial_entries`.
    * Para cada conta de **RESULTADO** ("RECEITAS", "CUSTOS E DESPESAS") que tiver movimentação no período, adicione um objeto a esta lista.
    * Cada objeto deve conter: `main_group`, `subgroup_1`, `specific_account`, `movement_type` ('Receita' ou 'Despesa'), e `period_value` (o valor numérico da movimentação).
    * **REGRA CRÍTICA**: Use o valor da coluna "Crédito" para Receitas e o valor da coluna "Débito" para Despesas. Ignore as colunas de saldo.

3.  **Cálculos Agregados**:
    * `total_receitas`: A soma de `period_value` de todos os lançamentos onde `movement_type` é 'Receita'.
    * `total_despesas`: A soma de `period_value` de todos os lançamentos onde `movement_type` é 'Despesa'.
    * `lucro_bruto`: O resultado de `total_receitas` - `total_despesas`.

FORMATO DE SAÍDA OBRIGATÓRIO (APENAS O JSON):
Retorne um único objeto JSON com a seguinte estrutura. Preencha todos os campos com os dados extraídos e calculados.

{{
  "cliente": "Nome da Empresa",
  "data_inicial": "AAAA-MM-DD",
  "data_final": "AAAA-MM-DD",
  "total_receitas": 1475580.28,
  "total_despesas": 1420776.98,
  "lucro_bruto": 54803.30,
  "financial_entries": [
    {{
      "main_group": "RECEITAS",
      "subgroup_1": "RECEITAS OPERACIONAIS",
      "specific_account": "SERVICOS PRESTADOS",
      "movement_type": "Receita",
      "period_value": 1475579.70
    }},
    {{
      "main_group": "CUSTOS E DESPESAS",
      "subgroup_1": "CUSTOS OPERACIONAIS",
      "specific_account": "CUSTO DOS SERVICOS",
      "movement_type": "Despesa",
      "period_value": 10401.25
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
        # (O restante do código de _call_gemini_api e _extract_json_from_response permanece o mesmo da versão anterior)
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
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
            async with httpx.AsyncClient(timeout=120.0) as client:
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
        try:
            cleaned_text = response_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error(f"Erro de decodificação de JSON: {e}")
            logger.debug(f"Texto que causou o erro: {response_text[:500]}...")
            return None

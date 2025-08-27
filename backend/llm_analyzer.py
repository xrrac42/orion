# -*- coding: utf-8 -*-
"""
Módulo LLM-centric responsável pela análise completa de balancetes.
A IA agora é responsável por extrair, calcular e estruturar toda a análise.
"""
import logging
import json
from typing import Dict, Any, Optional
import httpx
from config import settings

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """
    Classe que encapsula a lógica para analisar, calcular e estruturar dados de balancetes
    usando a API do Google Gemini.
    """
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("A variável de ambiente GEMINI_API_KEY não está configurada.")
        self.api_key = settings.GEMINI_API_KEY
        self.model = "gemini-1.5-pro" 
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def analyze_and_structure_balancete(self, text_content: str) -> Optional[Dict[str, Any]]:
        """
        Orquestra o processo completo de análise e estruturação via LLM.
        """
        try:
            prompt = self._create_super_prompt(text_content)
            
            logger.info(f"Iniciando chamada para a API Gemini (modelo: {self.model}) com prompt refinado.")
            
            api_response_text = await self._call_gemini_api(prompt)

            if not api_response_text:
                return None

            logger.info("Resposta recebida da API Gemini. Tentando extrair e validar o JSON.")
            structured_data = self._extract_json_from_response(api_response_text)

            if structured_data:
                logger.info("JSON extraído com sucesso. Normalizando a chave 'financial_entries'.")
                
                entries = None
                candidate_keys = ["financial_entries", "entries", "contas", "financialEntries", "lancamentos"]
                
                for key in candidate_keys:
                    if key in structured_data and isinstance(structured_data[key], list):
                        entries = structured_data.pop(key)
                        break
                
                if entries is not None:
                    structured_data["financial_entries"] = entries
                    logger.info(f"LLM -> Chave 'financial_entries' normalizada com {len(entries)} itens.")
                else:
                    logger.warning(f"LLM -> Nenhuma lista de lançamentos encontrada. Garantindo que a chave 'financial_entries' exista como lista vazia.")
                    structured_data["financial_entries"] = []

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
Você é um assistente de contabilidade especialista em analisar balancetes brasileiros. Sua tarefa é analisar o texto abaixo, extrair os dados e retornar um único objeto JSON.

**REGRAS CRÍTICAS E INEGOCIÁVEIS:**
1.  **FORMATO DE NÚMERO BRASILEIRO**: Os números no texto usam '.' como separador de milhar e ',' como separador decimal. Ao extrair um valor para o JSON, você DEVE convertê-lo para o formato numérico padrão (ex: "1.475.579,70" deve se tornar o número `1475579.70`). **ESTA É A REGRA MAIS IMPORTANTE.**
2.  **DEDUÇÕES DA RECEITA**: Contas como 'ICMS', 'ISSQN', 'PIS', 'COFINS sobre Vendas', 'Vendas Canceladas' ou 'Devoluções' NÃO SÃO DESPESAS. Elas são deduções da receita. Você deve identificá-las, marcá-las com o `movement_type` 'Dedução', e subtraí-las da receita bruta para calcular a receita líquida.
3.  **FOCO NAS CONTAS DE RESULTADO**: Ignore completamente as contas de "ATIVO" e "PASSIVO". Seu foco são apenas as contas dentro dos grupos "RECEITAS", "DEDUÇÕES DA RECEITA", "CUSTOS" e "DESPESAS".
4.  **VALORES CORRETOS**: Para 'Receita', o `period_value` é o valor da coluna "Crédito". Para 'Custos', 'Despesas' e 'Deduções', o `period_value` é o valor da coluna "Débito". Ignore saldos.
5.  **IGNORAR ZERADOS**: Não inclua na lista `financial_entries` contas cujo valor de Débito ou Crédito no período seja zero.

**TAREFAS A SEREM EXECUTADAS:**
1.  Extraia `cliente`, `data_inicial` e `data_final`.
2.  Crie a lista `financial_entries` com objetos para cada conta de resultado com movimentação, contendo: `main_group`, `subgroup_1`, `specific_account`, `movement_type` ('Receita', 'Dedução', 'Custo' ou 'Despesa'), e `period_value` (o valor numérico CORRIGIDO).
3.  Calcule os totais:
    * `total_receitas_brutas`: Soma de todas as 'Receitas'.
    * `total_deducoes`: Soma de todas as 'Deduções'.
    * `total_custos_despesas`: Soma de todos os 'Custos' e 'Despesas'.
    * **`lucro_bruto`**: Calcule como (`total_receitas_brutas` - `total_deducoes` - `total_custos_despesas`).
4.  No JSON final, use os nomes `total_receitas` (que será a receita líquida: brutas - deduções) e `total_despesas` (que será a soma de custos e despesas).

**FORMATO DE SAÍDA OBRIGATÓRIO (APENAS O JSON):**
```json
{{
  "cliente": "UNITY COMERCIO E SERVICOS AUTOMOTIVOS LTDA",
  "data_inicial": "2024-01-01",
  "data_final": "2024-12-31",
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
      "main_group": "DEDUÇÕES DA RECEITA",
      "subgroup_1": "TRIBUTOS INCIDENTES",
      "specific_account": "ISSQN",
      "movement_type": "Dedução",
      "period_value": 14825.57
    }}
  ]
}}
```

**Texto do balancete para análise:**
---
{text_content}
---
"""
        return prompt

    async def _call_gemini_api(self, prompt: str) -> Optional[str]:
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
            return None

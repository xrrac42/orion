# -*- coding: utf-8 -*-
"""
Módulo responsável pela análise de balancetes usando um LLM (Gemini).
Converte o texto não estruturado de um PDF em um JSON estruturado e validado.
"""

import logging
import json
import os
from typing import Dict, Any, Optional
import httpx

# Configura um logger para este módulo para facilitar o debug
logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """
    Classe que encapsula a lógica para analisar balancetes usando a API do Google Gemini.
    """

    def __init__(self):
        """
        Inicializa o analisador, carregando a chave da API e configurando os endpoints.
        """
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = "gemini-1.5-flash-latest"  # Usar a versão mais recente para melhor performance
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

        if not self.api_key:
            # Em vez de apenas avisar, é melhor levantar um erro se a chave não existir,
            # pois a classe não pode funcionar sem ela.
            raise ValueError("A variável de ambiente GEMINI_API_KEY não está configurada.")

    async def analyze_balancete(self, text_content: str) -> Optional[Dict[str, Any]]:
        """
        Orquestra o processo de análise do texto de um balancete.

        Args:
            text_content: O conteúdo textual completo extraído do arquivo PDF.

        Returns:
            Um dicionário com os dados estruturados do balancete, ou None em caso de falha.
        """
        try:
            # 1. Cria o prompt detalhado para a IA
            prompt = self._create_analysis_prompt(text_content)

            # 2. Chama a API do Gemini de forma assíncrona
            api_response_text = await self._call_gemini_api(prompt)

            if not api_response_text:
                logger.error("A chamada para a API do Gemini não retornou conteúdo.")
                return None

            # 3. Extrai e limpa o JSON da resposta de texto da IA
            structured_data = self._extract_json_from_response(api_response_text)

            if structured_data:
                logger.info("Análise do balancete via LLM concluída e validada com sucesso.")
                return structured_data
            else:
                # O erro específico já foi logado dentro de _extract_json_from_response
                return None

        except Exception as e:
            logger.exception(f"Erro inesperado durante a análise do balancete: {e}")
            return None

    def _create_analysis_prompt(self, text_content: str) -> str:
        """
        Cria um prompt de alta qualidade, projetado para extrair dados financeiros com precisão.
        """
        # Este prompt foi refinado para ser mais específico e reduzir a chance de erros da IA.
        prompt = f"""
Analise o seguinte texto extraído de um balancete contábil brasileiro. Sua tarefa é extrair as seguintes informações com máxima precisão, correspondendo exatamente ao documento:

1. O nome da empresa cliente.
2. A data inicial e a data final do período do balancete (ambas no formato AAAA-MM-DD).
3. Uma lista de todas as contas de resultado (Receitas, Custos e Despesas) que possuem movimentação no período.

INSTRUÇÕES CRÍTICAS:
- IGNORE completamente as seções de ATIVO, PASSIVO e PATRIMÔNIO LÍQUIDO.
- FOQUE EXCLUSIVAMENTE nas contas de RESULTADO (geralmente começam após o Patrimônio Líquido).
- Para cada conta, identifique sua hierarquia de grupos (grupo principal e subgrupo).
- Capture os valores numéricos das colunas de movimentação do período, tipicamente chamadas "Débito" e "Crédito".
- Converta todos os valores numéricos para o formato float (ex: "1.234,56" se torna 1234.56).
- Não invente dados. Se uma informação não for encontrada, retorne `null`.
- Os nomes dos grupos e contas devem ser extraídos exatamente como aparecem no texto.

FORMATO DE SAÍDA OBRIGATÓRIO:
Responda APENAS com um objeto JSON válido, sem nenhum texto ou formatação adicional. A estrutura deve ser:

{{
  "cliente": "Nome da Empresa Extraído",
  "data_inicial": "AAAA-MM-DD",
  "data_final": "AAAA-MM-DD",
  "contas": [
    {{
      "grupo_principal": "RECEITAS" ou "CUSTOS E DESPESAS",
      "subgrupo_1": "Nome do Primeiro Subgrupo (ou null se não houver)",
      "conta_especifica": "Nome da Conta Final com Movimentação",
      "valor_debito": 0.00,
      "valor_credito": 1475579.99
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
                "responseMimeType": "application/json", # Forçar a saída em JSON
                "temperature": 0.1,
                "topP": 0.8,
                "topK": 1,
                "maxOutputTokens": 8192,
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
                response.raise_for_status()  # Lança uma exceção para status de erro (4xx ou 5xx)

                result = response.json()
                
                # Navegação segura pela estrutura da resposta
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
            # Remove ```json, ``` e espaços em branco extras
            cleaned_text = response_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            
            parsed_json = json.loads(cleaned_text)
            
            # Valida a estrutura do JSON antes de retorná-lo
            if self._validate_basic_structure(parsed_json):
                return parsed_json
            else:
                logger.error(f"O JSON retornado pela IA falhou na validação de estrutura. Conteúdo: {parsed_json}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Erro de decodificação de JSON: {e}")
            logger.debug(f"Texto que causou o erro: {response_text[:500]}...")
            return None
        except Exception as e:
            logger.exception(f"Erro inesperado ao extrair JSON: {e}")
            return None

    def _validate_basic_structure(self, data: Dict[str, Any]) -> bool:
        """
        Valida se o dicionário JSON possui os campos e tipos essenciais.
        """
        # CORREÇÃO: Adicionado 'data_inicial' na validação
        required_fields = ["cliente", "data_inicial", "data_final", "contas"]
        for field in required_fields:
            if field not in data:
                logger.error(f"Validação falhou: Campo obrigatório '{field}' ausente no JSON.")
                return False

        if not isinstance(data["contas"], list):
            logger.error("Validação falhou: O campo 'contas' deve ser uma lista.")
            return False

        required_conta_fields = ["grupo_principal", "conta_especifica", "valor_debito", "valor_credito"]
        for i, conta in enumerate(data["contas"]):
            if not isinstance(conta, dict):
                logger.error(f"Validação falhou: O item {i} em 'contas' não é um objeto.")
                return False
            for field in required_conta_fields:
                if field not in conta:
                    logger.error(f"Validação falhou: Campo obrigatório '{field}' ausente na conta {i}.")
                    return False
        
        return True

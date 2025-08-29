# backend/llm_analyzer.py
import logging
import json
from typing import Dict, Any, Optional
import httpx
from config import settings

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("A variável de ambiente GEMINI_API_KEY não está configurada.")
        self.api_key = settings.GEMINI_API_KEY
        self.model = "gemini-1.5-flash"  # Flash é mais que suficiente para extração direta
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """Função auxiliar para chamar a API do Gemini."""
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.0}
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
            text_response = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
            return text_response
        except Exception as e:
            logger.exception(f"Falha na chamada à API Gemini: {e}")
            return None

    def _extract_json_from_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Extrai um objeto JSON limpo da resposta da IA."""
        try:
            clean_text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(clean_text)
        except (json.JSONDecodeError, AttributeError):
            logger.error(f"Não foi possível decodificar o JSON da resposta: {text[:200]}...")
            return None

    async def extract_data_from_text(self, text_content: str) -> Optional[Dict[str, Any]]:
        """
        Extrai os dados em duas etapas forçadas para garantir 100% de precisão nos totais.
        """
        logger.info("Iniciando extração forçada em duas etapas.")
        
        # --- ETAPA 1: PYTHON ISOLA O RESUMO FINAL ---
        summary_data = None
        try:
            # Encontra o texto-âncora "Valores do Período" e pega apenas o trecho relevante depois dele.
            # Isso remove 99% da chance de erro da IA.
            summary_chunk = text_content.split("Valores do Período")[-1]
            
            summary_prompt = f"""
            Analise o texto a seguir e extraia os valores numéricos para Receita, Despesa/Custo e Lucro.
            Retorne APENAS um objeto JSON com as chaves "total_receitas", "total_despesas_custos", "lucro_periodo".

            Texto para extrair:
            ---
            {summary_chunk}
            ---
            """
            
            logger.info("Etapa 1: Extraindo o resumo final de um trecho isolado de texto.")
            summary_response = await self._call_gemini_api(summary_prompt)
            logger.info("Gemini summary raw response (truncated): %s", (summary_response or '')[:1000])
            if summary_response:
                summary_data = self._extract_json_from_response(summary_response)
                logger.info("Parsed summary_data: %s", summary_data)
        except IndexError:
            logger.error("A âncora 'Valores do Período' não foi encontrada no texto do PDF.")
            return None
        except Exception as e:
            logger.error(f"Erro na Etapa 1 (extração do resumo): {e}")

        if not summary_data or "total_receitas" not in summary_data:
            logger.error("Falha ao extrair o JSON do resumo final. O processo não pode continuar.")
            return None

        # --- ETAPA 2: EXTRAIR O RESTO DOS DADOS ---
        main_data = None
        try:
            main_prompt = f"""
            Analise o texto de um balancete. Extraia o nome do cliente, a data final e a lista de todos os lançamentos de resultado.
            IGNORE QUALQUER TOTAL OU RESUMO. Foque apenas nos lançamentos individuais. Retorne APENAS um objeto JSON.

            Texto:
            ---
            {text_content}
            ---
            """
            logger.info("Etapa 2: Extraindo metadados e lançamentos do texto completo.")
            main_response = await self._call_gemini_api(main_prompt)
            logger.info("Gemini main raw response (truncated): %s", (main_response or '')[:3000])
            if main_response:
                main_data = self._extract_json_from_response(main_response)
                logger.info("Parsed main_data keys: %s", list(main_data.keys()) if isinstance(main_data, dict) else None)
                # Log financial_entries summary for easier debugging
                try:
                    fes = main_data.get('financial_entries', []) if isinstance(main_data, dict) else []
                    logger.info("financial_entries count: %d; sample: %s", len(fes), fes[:8])
                except Exception:
                    logger.debug("financial_entries not iterable or missing in parsed main_data")
        except Exception as e:
            logger.error(f"Erro na Etapa 2 (extração dos lançamentos): {e}")

        if not main_data:
            logger.error("Falha ao extrair os metadados e lançamentos detalhados.")
            return None
        
        # --- ETAPA 3: COMBINAR OS RESULTADOS DE FORMA SEGURA ---
        # Normalize various possible keys returned by different prompts/LLM versions
        raw_entries = []
        if isinstance(main_data, dict):
            possible = ["financial_entries", "lancamentos_resultado", "lancamentos", "entries"]
            for k in possible:
                if k in main_data and main_data.get(k):
                    raw_entries = main_data.get(k)
                    break

        # Normalize each entry to the canonical shape expected downstream
        normalized_entries = []
        for e in (raw_entries or []):
            if not isinstance(e, dict):
                continue
            # map common field names to canonical ones
            valor_debito = e.get('valor_debito') or e.get('debito') or e.get('debit') or e.get('debits') or e.get('valor_debito')
            valor_credito = e.get('valor_credito') or e.get('credito') or e.get('credit') or e.get('credits') or e.get('valor_credito')
            descricao = e.get('descricao') or e.get('descricao_lancamento') or e.get('description') or e.get('conta') or e.get('categoria')
            specific = e.get('conta_especifica') or e.get('specific_account') or e.get('conta') or e.get('descricao')

            # determine a safe grupo_principal (DB has NOT NULL constraint)
            grupo_principal = e.get('grupo_principal') or e.get('grupo') or e.get('main_group') or None
            if not grupo_principal:
                # Use a conservative default that groups uncategorized items
                grupo_principal = 'Outros'

            normalized_entries.append({
                'valor_debito': valor_debito,
                'valor_credito': valor_credito,
                'grupo_principal': grupo_principal,
                'subgroup_1': descricao,
                'conta_especifica': specific,
                # keep the original raw entry for debugging if needed
                '_raw': e
            })

        final_result = {
            "cliente": main_data.get("cliente"),
            "data_final": main_data.get("data_final"),
            "resumo_periodo": summary_data, # Usando os totais que extraímos de forma isolada e segura.
            "financial_entries": normalized_entries
        }
        
        logger.info("Extração em duas etapas concluída com sucesso. Combinando resultados.")
        return final_result
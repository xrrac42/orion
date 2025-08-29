# backend/core_processor.py
import logging
import tempfile
import os
import json
from pdf_processor import extract_structured_text_from_pdf
# Use the standalone parsers (local test scripts)
from parser_test import parse_balancete_for_db
from parser_test2 import extrair_analise_balancete
from database import create_analysis_and_entries

logger = logging.getLogger(__name__)

class CoreProcessor:
    def __init__(self):
        # Não precisamos mais do GeminiAnalyzer aqui
        pass

    async def process_pdf_file(self, file_content: bytes, client_id: str, file_upload_id: str, file_name: str = None, reference_year: int = None, reference_month: int = None):
        try:
            # Save bytes to a temp file so existing parsers (which accept path) can use it
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tf:
                tf.write(file_content)
                tmp_path = tf.name

            try:
                # 1) Extract financial entries using parser_test
                logger.info("Executando parser de financial_entries (parser_test)")
                fin_data = parse_balancete_for_db(tmp_path)

                # 2) Extract monthly analysis (raw) using parser_test2
                logger.info("Executando parser de monthly_analysis (parser_test2)")
                raw_analysis_json = extrair_analise_balancete(tmp_path)
                try:
                    raw_analysis = json.loads(raw_analysis_json) if isinstance(raw_analysis_json, str) else raw_analysis_json
                except Exception:
                    # If parser_test2 returns already a dict or fails to parse, keep raw string
                    raw_analysis = raw_analysis_json

                # 3) Build canonical analysis_data expected by create_analysis_and_entries
                resumo = {}
                # Try to read totals from raw_analysis (various keys depending on parser)
                if isinstance(raw_analysis, dict):
                    # Various parser versions may use different keys
                    resumo['total_receitas'] = raw_analysis.get('valores_periodo', {}).get('receita') or raw_analysis.get('total_receitas') or 0
                    resumo['total_despesas_custos'] = raw_analysis.get('valores_periodo', {}).get('despesa_custo') or raw_analysis.get('total_despesas') or 0
                    # include lucro if available so DB can persist lucro_bruto
                    if raw_analysis.get('valores_periodo', {}).get('lucro') is not None:
                        resumo['lucro'] = raw_analysis.get('valores_periodo', {}).get('lucro')
                else:
                    resumo['total_receitas'] = 0
                    resumo['total_despesas_custos'] = 0

                analysis_payload = {
                    'cliente': fin_data.get('empresa') or None,
                    'data_final': (raw_analysis.get('periodo_fim') if isinstance(raw_analysis, dict) else None) or (fin_data.get('periodo', {}).get('fim') if isinstance(fin_data.get('periodo'), dict) else None),
                    'file_name': file_name or '',
                    'resumo_periodo': resumo,
                    'financial_entries': fin_data.get('financial_entries', []),
                    'raw_analysis': raw_analysis,
                    'source_raw_text': None,
                    'reference_year': reference_year,
                    'reference_month': reference_month
                }

                # 4) Persist
                new_analysis = await create_analysis_and_entries(
                    client_id=client_id,
                    file_upload_id=file_upload_id,
                    analysis_data=analysis_payload
                )

                logger.info(f"Processamento com Python concluído para a análise {new_analysis.id}.")
                return {"status": "success", "analysis_id": new_analysis.id}
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except Exception as e:
            logger.exception(f"Falha no processamento do arquivo: {e}")
            return {"status": "error", "message": str(e)}
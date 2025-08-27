# -*- coding: utf-8 -*-
"""
Módulo central que orquestra o processo de análise de um PDF.
Agora simplificado para confiar na análise completa do LLM.
"""
import logging
# Evita import circular: a função de extração vive em routes.pdf_processor
from routes.pdf_processor import extract_structured_text_from_pdf
from llm_analyzer import GeminiAnalyzer
from database import create_analysis_and_entries

logger = logging.getLogger(__name__)

class CoreProcessor:
    def __init__(self):
        self.llm_analyzer = GeminiAnalyzer()

    async def process_pdf_file(self, file_content: bytes, client_id: str, file_upload_id: str, file_name: str):
        """
        Processa um arquivo PDF do início ao fim usando a abordagem LLM-centric.
        """
        try:
            logger.info(f"Iniciando processamento para file_upload_id: {file_upload_id}")
            # 1. Extrair texto estruturado do PDF
            text_content = extract_structured_text_from_pdf(file_content)
            if not text_content:
                raise ValueError("Não foi possível extrair texto estruturado do PDF.")

            # --- ADICIONADO LOG DE DEBUG CRÍTICO ---
            # Esta linha vai mostrar no seu terminal o texto exato que a IA está recebendo.
            logger.debug(f"Texto extraído do PDF para análise da IA:\\n{text_content}")

            # 2. IA analisa, calcula e estrutura TUDO
            logger.info("Enviando texto para análise da IA...")
            analysis_data = await self.llm_analyzer.extract_data_from_text(text_content)
            if not analysis_data:
                raise ValueError("A análise completa com IA falhou ou retornou dados vazios.")

            analysis_data["file_name"] = file_name
            
            logger.info("Dados recebidos da IA, iniciando inserção no banco de dados...")
            # 3. Salva a análise e suas entradas no banco de dados
            new_analysis = await create_analysis_and_entries(
                client_id=client_id,
                file_upload_id=file_upload_id,
                analysis_data=analysis_data
            )
            
            logger.info(f"Processamento e salvamento concluídos com sucesso para a análise {new_analysis.id}.")
            return {"status": "success", "analysis_id": new_analysis.id}

        except Exception as e:
            logger.exception(f"Falha no processamento do arquivo para o upload {file_upload_id}: {e}")
            return {"status": "error", "message": str(e)}